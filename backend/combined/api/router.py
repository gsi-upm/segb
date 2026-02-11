"""Main API router with endpoint handlers."""

from __future__ import annotations

from asyncio import Lock
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse, PlainTextResponse

from .deps import get_services
from .schemas import DeleteRequest, TTLContent
from ..core.security import Role, User, require_roles, validate_token
from ..services.log_service import LogService
from ..services.runtime import RuntimeServices
from ..services.shared_context_service import SharedContextService
from ..utils.shared_context import (
    SharedContextReconcileResponse,
    SharedContextResolveRequest,
    SharedContextResolveResponse,
)

router = APIRouter()
transaction_lock = Lock()


@router.get("/healthz/live")
def live() -> dict[str, bool]:
    return {"live": True}


@router.get("/healthz/ready")
def ready(request: Request) -> dict[str, bool]:
    services: RuntimeServices = get_services(request)
    return {
        "ready": services.neo4j_ok and services.virtuoso_ok,
        "neo4j": services.neo4j_ok,
        "virtuoso": services.virtuoso_ok,
    }


@router.post("/ttl")
async def insert_ttl(
    request: Request,
    data: TTLContent,
    user: Annotated[User, Depends(validate_token)],
):
    require_roles(user, allowed=(Role.LOGGER, Role.ADMIN))

    if transaction_lock.locked():
        raise HTTPException(status_code=429, detail="Another transaction is in progress. Please try again later.")

    services: RuntimeServices = get_services(request)
    service = LogService(neo4j=services.neo4j, virtuoso=services.virtuoso)

    async with transaction_lock:
        response = service.insert_ttl(
            ttl_content=data.ttl_content,
            actor=data.user or user.username or "anonymous",
            origin_ip=request.client.host,
        )
        return JSONResponse(content=response, status_code=201)


@router.get("/events", response_class=PlainTextResponse)
async def get_events(
    request: Request,
    user: Annotated[User, Depends(validate_token)],
):
    require_roles(user, allowed=(Role.AUDITOR, Role.ADMIN))
    services: RuntimeServices = get_services(request)
    service = LogService(neo4j=services.neo4j, virtuoso=services.virtuoso)
    return PlainTextResponse(content=service.get_events_ttl(), media_type="text/turtle")


@router.get("/query")
async def execute_query(
    request: Request,
    query: str,
    user: Annotated[User, Depends(validate_token)],
):
    require_roles(user, allowed=(Role.ADMIN,))
    services: RuntimeServices = get_services(request)
    service = LogService(neo4j=services.neo4j, virtuoso=services.virtuoso)
    return service.execute_query(query)


@router.get("/modifications")
async def get_modifications(
    request: Request,
    user: Annotated[User, Depends(validate_token)],
    limit: int = Query(gt=0),
):
    require_roles(user, allowed=(Role.AUDITOR, Role.ADMIN))
    services: RuntimeServices = get_services(request)
    service = LogService(neo4j=services.neo4j, virtuoso=services.virtuoso)
    return service.get_modifications(limit)


@router.get("/modifications_date")
async def get_modifications_by_date(
    request: Request,
    start_date: str,
    end_date: str,
    user: Annotated[User, Depends(validate_token)],
):
    require_roles(user, allowed=(Role.AUDITOR, Role.ADMIN))
    services: RuntimeServices = get_services(request)
    service = LogService(neo4j=services.neo4j, virtuoso=services.virtuoso)
    return service.get_modifications_by_date(start_date, end_date)


@router.post("/ttl/delete_all")
async def delete_all_ttls(
    request: Request,
    data: DeleteRequest,
    user: Annotated[User, Depends(validate_token)],
):
    require_roles(user, allowed=(Role.ADMIN,))
    services: RuntimeServices = get_services(request)
    service = LogService(neo4j=services.neo4j, virtuoso=services.virtuoso)
    result = service.delete_all_ttls(
        actor=data.user or user.username or "anonymous",
        origin_ip=request.client.host,
    )
    return JSONResponse(content=result, status_code=200)


@router.post("/shared-context/resolve", response_model=SharedContextResolveResponse)
async def resolve_shared_context(
    request: Request,
    data: SharedContextResolveRequest,
    user: Annotated[User, Depends(validate_token)],
):
    require_roles(user, allowed=(Role.LOGGER, Role.ADMIN))
    services: RuntimeServices = get_services(request)
    service = SharedContextService(resolver=services.shared_context)
    try:
        return service.resolve(data)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/shared-context/reconcile", response_model=SharedContextReconcileResponse)
async def reconcile_shared_context(
    request: Request,
    user: Annotated[User, Depends(validate_token)],
):
    require_roles(user, allowed=(Role.ADMIN,))
    services: RuntimeServices = get_services(request)
    service = SharedContextService(resolver=services.shared_context)
    return service.reconcile()


@router.get("/shared-context/stats")
async def shared_context_stats(
    request: Request,
    user: Annotated[User, Depends(validate_token)],
):
    require_roles(user, allowed=(Role.AUDITOR, Role.ADMIN))
    services: RuntimeServices = get_services(request)
    service = SharedContextService(resolver=services.shared_context)
    return service.stats()
