# ==============================
# IMPORTS 
# ==============================

import asyncio
import contextlib
import json
import logging
import os
from asyncio import Lock  # atomic transactions
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Annotated, Optional


# Third-Party Libraries
from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Query,
    Request,
    status
)
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from rdflib import Graph


# Internal Utilities
# from server.utils.main_combined import DeleteRequest, TTLContent
# from utils.credentials import User, validate_token, Role

# from utils.Neo4j.model_N import (
#     connect_to_db,
#     get_logs_by_date,
#     get_recent_logs,
#     store_bulk_deletion,
#     store_modification
# )
# from utils.Virtuoso.model_V import (
#     delete_all_triples,
#     get_ttls,
#     insert_ttl,
#     run_custom_query
# )





# Data Models
from models.neo4j_model import Neo4jModel
from models.virtuoso_model import VirtuosoModel




# ==============================
# Global Locks
# ==============================
transaction_lock = Lock()


# ==============================
# Logging
# ==============================
LOG_LEVEL = os.getenv("LOGGING_LEVEL", "INFO").upper()
LOG_FILE = os.getenv("SERVER_LOG_FILE", "segb.log")
os.makedirs("/logs", exist_ok=True)

logger = logging.getLogger("segb.server")
logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

fh = logging.FileHandler(f"/logs/{LOG_FILE}", mode="a", encoding="utf-8")
fh.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s -> %(message)s",
                                  "%Y-%m-%d %H:%M:%S"))
ch = logging.StreamHandler()
ch.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s -> %(message)s",
                                  "%Y-%m-%d %H:%M:%S"))
logger.addHandler(fh)
logger.addHandler(ch)





# ==============================
# Config API doc
# ==============================
api_info_json_file = os.getenv("DESCRIPTION_FILE_PATH", "./api_info.json")
try:
    with open(api_info_json_file, "r", encoding="utf-8") as f:
        api_info = json.load(f)
except Exception as e:
    logger.warning("Error reading %s, using defaults. %s", api_info_json_file, e)
    api_info = {
        "title": "SEGB",
        "contact": {"name": "GSI-UPM", "url": "https://www.gsi.upm.es", "email": "gsi@autolistas.upm.es"},
        "license": {"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
    }

try:
    with open("./api_description.md", "r", encoding="utf-8") as f:
        api_description = f.read()
except Exception as e:
    logger.warning("Error reading api_description.md, using default. %s", e)
    api_description = "Semantic Ethical Glass Box (SEGB) API. See <https://segb.readthedocs.io/en/latest/>."

version = os.getenv("VERSION", "") or "stable"





# ==============================
# Start-Up parameters
# ==============================
MAX_STARTUP_RETRIES = int(os.getenv("MAX_STARTUP_RETRIES", "6"))   # ~63 s total con 1,2,4,8,16,32
MAX_BACKOFF_SECONDS = int(os.getenv("MAX_BACKOFF_SECONDS", "16"))
RUNTIME_PING_INTERVAL = int(os.getenv("RUNTIME_PING_INTERVAL", "5"))






# ==============================
# Lifespan: connecting with DB's before serving requests (https://fastapi.tiangolo.com/advanced/events/#async-context-manager)
# ==============================

def init_state(app: FastAPI):
    app.state.neo4j = Neo4jModel.get_instance()
    app.state.virtuoso = VirtuosoModel.get_instance()
    app.state.neo4j_ok = False
    app.state.virtuoso_ok = False
    app.state.db_monitor_task = None

async def _retry_connect(name: str, fn):
    delay = 1
    for attempt in range(1, MAX_STARTUP_RETRIES + 1):
        try:
            fn() 
            logger.info("%s conectado.", name)
            return
        except Exception as e:
            logger.warning("%s intento %d falló: %s", name, attempt, e)
            if attempt == MAX_STARTUP_RETRIES:
                raise
            await asyncio.sleep(delay)
            delay = min(delay * 2, MAX_BACKOFF_SECONDS)
            

async def reconnection_loop(app: FastAPI):
    while True:
        await asyncio.sleep(RUNTIME_PING_INTERVAL)

        # --- Neo4j ---
        try:
            ok = bool(app.state.neo4j.ping())
        except Exception:
            ok = False
        if not ok:
            try:
                app.state.neo4j.close_connection()
            except Exception:
                pass
            logger.warning("Neo4j caído. Reintentando conexión...")
            delay = 1
            while True:
                try:
                    app.state.neo4j.connect_to_db(logger=None)
                    if app.state.neo4j.ping():
                        logger.info("Neo4j reconectado.")
                        ok = True
                        break
                except Exception as e:
                    logger.warning("Fallo reconexión Neo4j: %s", e)
                await asyncio.sleep(delay)
                delay = min(delay * 2, MAX_BACKOFF_SECONDS)
        app.state.neo4j_ok = ok

        # --- Virtuoso ---
        try:
            ok = bool(app.state.virtuoso.ping())
        except Exception:
            ok = False
        if not ok:
            try:
                app.state.virtuoso.close_connection()
            except Exception:
                pass
            logger.warning("Virtuoso caído. Reintentando conexión...")
            delay = 1
            while True:
                try:
                    app.state.virtuoso.connect_to_db()
                    if app.state.virtuoso.ping():
                        logger.info("Virtuoso reconectado.")
                        ok = True
                        break
                except Exception as e:
                    logger.warning("Fallo reconexión Virtuoso: %s", e)
                await asyncio.sleep(delay)
                delay = min(delay * 2, MAX_BACKOFF_SECONDS)
        app.state.virtuoso_ok = ok



# --------- FastAPI's lifespan ---------- # 

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    
    # Before FastAPI starts serving requests
    
    logger.info("Arrancando SEGB... nivel=%s", LOG_LEVEL)
    init_state(app)

    try:
        await _retry_connect("Neo4j",    lambda: app.state.neo4j.connect_to_db(logger=None))
        await _retry_connect("Virtuoso", lambda: app.state.virtuoso.connect_to_db())
        app.state.neo4j_ok = bool(app.state.neo4j.ping())
        app.state.virtuoso_ok = bool(app.state.virtuoso.ping())
    except Exception as e:
        logger.error("No se pudo conectar en arranque: %s. Saliendo.", e)
        raise SystemExit(1)

    
    app.state.db_monitor_task = asyncio.create_task(reconnection_loop(app)) # Monitoring connection during FastAPI runtime
    
    logger.info("SEGB listo para recibir tráfico.")
    
    # After FastAPI has stopped serving requests

    try:
        yield
        
    finally:
        task = app.state.db_monitor_task
        if task:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        with contextlib.suppress(Exception):
            app.state.neo4j.close_connection()
        with contextlib.suppress(Exception):
            app.state.virtuoso.close_connection()
        logger.info("Apagado completo.")


# --------- Endpoints' database dependency functions ---------- # 

def require_neo4j(request: Request):
    if not request.app.state.neo4j_ok:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="Neo4j no disponible")
    return request.app.state.neo4j

def require_virtuoso(request: Request):
    if not request.app.state.virtuoso_ok:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="Virtuoso no disponible")
    return request.app.state.virtuoso
        
        

# ==============================
# FastAPI app
# ==============================
app = FastAPI(
    title=api_info["title"],
    description=api_description,
    version=version,
    contact=api_info["contact"],
    license_info=api_info["license"],
    lifespan=lifespan
)




# ==============================
# ENDPOINTS
# ==============================



# ---------- Healthz endpoints ---------- # 

@app.get("/healthz/live")
def live():
    """
        Checks if the server is running
    """
    return {
        "live": True
    }

@app.get("/healthz/ready")
def ready():
    """
    Checks if the server is ready to accept requests (i.e. databases are working).
    """
    neo_ok = app.state.neo4j.ping()
    vir_ok = app.state.virtuoso.ping()
    return {
        "ready": neo_ok and vir_ok,
        "neo4j": neo_ok,
        "virtuoso": vir_ok
    }



# ---------- Main endpoints ------------- # 


# @app.post("/ttl")
# async def insert_ttl_combined(
#     request: Request,
#     data: TTLContent,
#     user: Annotated[User, Depends(validate_token)]
# ):
#     logger.info(f"Received post for log from IP: {request.client.host} from user {user.name} (username: {user.username} - roles: {user.roles})")
#     if not (Role.LOGGER.value in user.roles or Role.ADMIN.value in user.roles):
#         logger.info(f"User {user.name} (username: {user.username} - roles: {user.roles}) does not have permission to perform this action")
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="User does not have permission to perform this action"
#         )
    
#     if transaction_lock.locked():
#         raise HTTPException(
#             status_code=429,
#             detail="Another transaction is in progress. Please try again later."
#         )
    
#     async with transaction_lock:    
#         try:
#             origin_ip = request.client.host
#             actor = data.user or user.username or "anonymous"

#             # Insert into Virtuoso
#             log_id = insert_ttl(data.ttl_content)

#             # Store in Neo4j as insertion
#             store_modification("insertion", origin_ip, actor, data.ttl_content)

#             return JSONResponse(
#                 content={"message": "TTL inserted into both Virtuoso and Neo4j", "log_id": log_id},
#                 status_code=201
#             )
#         except Exception as e:
#             logger.exception("Insertion failed")
#             raise HTTPException(status_code=500, detail=f"Error inserting TTL: {str(e)}")



# @app.get("/events", response_class=PlainTextResponse) 
# async def get_events(user: Annotated[User, Depends(validate_token)]):
#     logger.info(f"Received request for log from user {user.name} (username: {user.username} - roles: {user.roles})")
#     if not (Role.AUDITOR.value in user.roles or Role.ADMIN.value in user.roles):
#         logger.info(f"User {user.name} (username: {user.username} - roles: {user.roles}) does not have permission to perform this action")
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="User does not have permission to perform this action"
#         )
#     try:
#         ttl_data = get_ttls()       
#         return PlainTextResponse(content=ttl_data, media_type="text/turtle") # so that it returns in TTL format instead of serialized JSON
#     except Exception as e:
#         logger.exception("Failed fetching events")
#         raise HTTPException(status_code=500, detail="Error fetching events")


# @app.get("/query")
# async def execute_query(user: Annotated[User, Depends(validate_token)], query: str):
#     logger.info(f"Received request for query from user {user.name} (username: {user.username} - roles: {user.roles})")
#     if Role.ADMIN.value not in user.roles:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="User does not have permission to perform this action"
#         )
#     try:
#         return run_custom_query(query)
#     except Exception as e:
#         logger.exception("SPARQL query failed")
#         raise HTTPException(status_code=500, detail=f"SPARQL error: {str(e)}")


# @app.get("/modifications")
# async def get_modifications(limit: int, request: Request, user: Annotated[User, Depends(validate_token)]):
#     logger.info(f"Received request for history from IP: {request.client.host} from user {user.name} (username: {user.username} - roles: {user.roles})")
#     if not (Role.AUDITOR.value in user.roles or Role.ADMIN.value in user.roles):
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="User does not have permission to perform this action"
#         )
#     try:
#         return get_recent_logs(limit)
#     except Exception as e:
#         logger.error(f"Error fetching logs: {e}")
#         raise HTTPException(status_code=500, detail="Error retrieving logs")


# @app.get("/modifications_date")
# async def get_modifications_by_date(start_date: str, end_date: str, request: Request, user: Annotated[User, Depends(validate_token)]):
#     logger.info(f"Received request for history by date from IP: {request.client.host} from user {user.name} (username: {user.username} - roles: {user.roles})")
#     if not (Role.AUDITOR.value in user.roles or Role.ADMIN.value in user.roles):
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="User does not have permission to perform this action"
#         )
    
#     try:
#         return get_logs_by_date(start_date, end_date)
#     except Exception as e:
#         logger.error(f"Error fetching logs by date: {e}")
#         raise HTTPException(status_code=500, detail="Error retrieving logs by date")
    
# @app.post("/ttl/delete_all")
# async def delete_all_ttls(request: Request, data: DeleteRequest, user: Annotated[User, Depends(validate_token)]):
#     logger.info(f"Received post for delete all log from user {user.name} (username: {user.username} - roles: {user.roles})")
#     if Role.ADMIN.value not in user.roles:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="User does not have permission to perform this action"
#         )

#     try:
#         origin_ip = request.client.host
#         actor = data.user or user.username or "anonymous"

#         # Get all TTLs from Virtuoso
#         ttl_text = get_ttls()
#         if not ttl_text:
#             return JSONResponse(content={"message": "No TTLs to delete"}, status_code=200)

#         # Convert TTL to RDF graph
#         g = Graph()
#         g.parse(data=ttl_text, format="turtle")

#         # Convert to TTL lines
#         ttl_lines = []
#         for s, p, o in g:
#             line = f"{s.n3()} {p.n3()} {o.n3()} ."
#             ttl_lines.append(line)

#         # Save in Neo4j as deletion
#         store_bulk_deletion(origin_ip, actor, ttl_lines)

#         # Delete graph
#         delete_all_triples()

#         return JSONResponse(content={"message": "Graph cleared and deletions logged."}, status_code=200)

#     except Exception as e:
#         logger.exception("Deletion failed")
#         raise HTTPException(status_code=500, detail=f"Error deleting TTLs: {str(e)}")
    






    

















