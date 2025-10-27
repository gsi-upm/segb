from neo4j import GraphDatabase
import os, uuid, time, threading, logging
from datetime import datetime
from typing import List, Dict, Any, Optional


class Neo4jModel:
    
    _instance: Optional["Neo4jModel"] = None
    _driver: Optional[Any] = None
    _lock = threading.Lock()
    _schema_lock = threading.Lock()
    _schema_ok = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    

    def __init__(self):
        self.driver = Neo4jModel._driver
    

    def connect_to_db(self, retries: int = 10, delay: int = 5, ensure_schema: bool = True, logger: Optional[logging.Logger] = None):
        if not isinstance(retries, int) or retries <= 0:
            raise ValueError("Parameter 'retries' must be a positive integer.")
        if not isinstance(delay, (int, float)) or delay < 0:
            raise ValueError("Parameter 'delay' must be a non-negative number.")
        if not isinstance(ensure_schema, bool):
            raise TypeError("Parameter 'ensure_schema' must be a boolean.")
        driver = self._connect_to_db(retries, delay)
        if ensure_schema and not Neo4jModel._schema_ok:
            with Neo4jModel._schema_lock:
                if not Neo4jModel._schema_ok:
                    try:
                        self.initialize_constraints(logger=logger)
                        Neo4jModel._schema_ok = True
                    except Exception:
                        self.close_connection()
                        raise
        return driver
    
    
    def _connect_to_db(self, retries: int = 10, delay: int = 5):
        uri = self._get_env_var("NEO4J_URI")
        user = self._get_env_var("NEO4J_USER")
        password = self._get_env_var("NEO4J_PASSWORD")
        with Neo4jModel._lock:
            if Neo4jModel._driver is not None:
                raise RuntimeError("Neo4j connection already established. Use get_driver().")
            last_error: Optional[BaseException] = None
            for _ in range(retries):
                try:
                    driver = GraphDatabase.driver(uri, auth=(user, password))
                    driver.verify_connectivity()
                    Neo4jModel._driver = driver
                    self.driver = driver
                    return driver
                except Exception as error:
                    last_error = error
                    if delay:
                        time.sleep(delay)
            raise ConnectionError(f"Could not connect to Neo4j at '{uri}' with user '{user}'.") from last_error
        
        
    
    def ping(self, timeout_ms: int = 1000) -> bool:
        drv = self.driver
        if drv is None:
            return False
        try:
            # 1) handshake TCP and auth covered by driver
            # 2) query-level timeout
            with drv.session() as s:
                # Neo4j Python driver accepts query-level timeout in ms
                s.run("RETURN 1 AS ok", timeout=timeout_ms).consume()
            return True
        except Exception as e:
            # logging.warning(f"Neo4j ping failed: {e}")
            return False


    @staticmethod
    def _get_env_var(var_name: str) -> str:
        if not isinstance(var_name, str) or not var_name:
            raise ValueError("Environment variable name must be a non-empty string.")
        value = os.environ.get(var_name)
        if not value or not value.strip():
            raise EnvironmentError(f"Missing or invalid environment variable: {var_name} with value '{value}'")
        return value.strip()

    
    @classmethod
    def get_instance(cls) -> "Neo4jModel":
        return cls()

    @classmethod
    def get_driver(cls):
        if cls._driver is None:
            raise RuntimeError("No active Neo4j connection. Call init_db() first.")
        return cls._driver
    
    
    def close_connection(self) -> None:
        self._close_connection()

    
    def _close_connection(self) -> None:
        with Neo4jModel._lock:
            if Neo4jModel._driver:
                try:
                    Neo4jModel._driver.close()
                except Exception as error:
                    raise RuntimeError("Error while closing Neo4j connection.") from error
                finally:
                    Neo4jModel._driver = None
                    if Neo4jModel._instance:
                        Neo4jModel._instance.driver = None
                        

    def initialize_constraints(self, logger: Optional[logging.Logger] = None) -> None:
        log = logger or logging.getLogger(__name__)
        driver = self.get_driver()
        log.info("Checking Neo4j constraints and n10s.graphconfig...")
        self._ensure_unique_uri_constraint(driver, log)
        self._init_graphconfig_if_needed(driver, log)
        log.info("Neo4j schema initialization completed.")

    def _constraint_exists(self, driver) -> bool:
        if driver is None:
            raise RuntimeError("Driver is None while checking constraints.")
        try:
            with driver.session() as session:
                records = list(session.run("SHOW CONSTRAINTS"))
        except Exception as error:
            raise RuntimeError("Failed to list constraints.") from error
        for record in records:
            name = record.get("name", "")
            description = (record.get("description") or "").lower()
            if name == "n10s_unique_uri" or (":resource" in description and "uri" in description and "unique" in description):
                return True
        return False

    def _ensure_unique_uri_constraint(self, driver, log: logging.Logger) -> None:
        if self._constraint_exists(driver):
            log.info("Constraint already exists.")
            return
        try:
            with driver.session() as session:
                try:
                    session.run("""
                        CREATE CONSTRAINT n10s_unique_uri
                        IF NOT EXISTS
                        FOR (r:Resource)
                        REQUIRE r.uri IS UNIQUE
                    """)
                    log.info("Constraint ensured (5.x syntax).")
                except Exception as error_5x:
                    log.debug("5.x syntax failed (%s); trying 4.x syntax.", error_5x)
                    try:
                        session.run("CREATE CONSTRAINT ON (r:Resource) ASSERT r.uri IS UNIQUE")
                        log.info("Constraint created (4.x syntax).")
                    except Exception as error_4x:
                        if "exists" in str(error_4x).lower():
                            log.info("Constraint already exists (race).")
                        else:
                            raise RuntimeError("Constraint creation failed.") from error_4x
        except RuntimeError:
            raise
        except Exception as error:
            raise RuntimeError("Unexpected error while ensuring unique URI constraint.") from error

    def _graphconfig_initialized(self, driver) -> bool:
        if driver is None:
            raise RuntimeError("Driver is None while checking graphconfig.")
        try:
            with driver.session() as session:
                return session.run("CALL n10s.graphconfig.show()").peek() is not None
        except Exception:
            return False

    def _init_graphconfig_if_needed(self, driver, log: logging.Logger) -> None:
        if self._graphconfig_initialized(driver):
            log.info("n10s.graphconfig already initialized.")
            return
        try:
            with driver.session() as session:
                session.run("CALL n10s.graphconfig.init()")
                log.info("n10s.graphconfig initialized.")
        except Exception as error:
            raise RuntimeError("Failed to initialize n10s.graphconfig.") from error

    def store_modification(self, action: str, origin_ip: str, user: str, ttl_content: str) -> str:
        if not isinstance(action, str) or not action.strip():
            raise ValueError("Parameter 'action' must be a non-empty string.")
        if not isinstance(origin_ip, str) or not origin_ip.strip():
            raise ValueError("Parameter 'origin_ip' must be a non-empty string.")
        if not isinstance(user, str) or not user.strip():
            raise ValueError("Parameter 'user' must be a non-empty string.")
        if not isinstance(ttl_content, str) or ttl_content == "":
            raise ValueError("Parameter 'ttl_content' must be a string.")
        log_id = str(uuid.uuid4())
        timestamp = datetime.now()

        def _store_log(tx):
            query = """
            CREATE (log:Log {
                log_id: $log_id,
                user: $user,
                action: $action,
                timestamp: $timestamp,
                origin_ip: $origin_ip
            })
            CREATE (change:Change { ttl_content: $ttl_content })
            CREATE (log)-[:MODIFIED]->(change)
            """
            tx.run(
                query,
                log_id=log_id,
                user=user,
                action=action,
                timestamp=timestamp,
                origin_ip=origin_ip,
                ttl_content=ttl_content,
            )

        try:
            with self.get_driver().session() as session:
                session.execute_write(_store_log)
        except Exception as error:
            raise RuntimeError("Failed to store modification log.") from error
        return log_id

    def get_recent_logs(self, limit: int) -> List[Dict[str, Any]]:
        if not isinstance(limit, int) or limit <= 0:
            raise ValueError("Parameter 'limit' must be a positive integer.")

        def _fetch_logs(tx):
            query = """
            MATCH (log:Log)-[:MODIFIED]->(change:Change)
            RETURN log.log_id AS log_id, log.user AS user, log.action AS action, 
                   log.timestamp AS timestamp, log.origin_ip AS origin_ip, 
                   change.ttl_content AS ttl_content
            ORDER BY log.timestamp DESC
            LIMIT $limit
            """
            result = tx.run(query, limit=limit)
            rows: List[Dict[str, Any]] = []
            for record in result:
                row = record.data()
                if "timestamp" in row and hasattr(row["timestamp"], "isoformat"):
                    row["timestamp"] = row["timestamp"].isoformat()
                rows.append(row)
            return rows

        try:
            with self.get_driver().session() as session:
                return session.execute_read(_fetch_logs)
        except Exception as error:
            raise RuntimeError("Failed to fetch recent logs.") from error

    def get_logs_by_date(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        if not isinstance(start_date, str) or not isinstance(end_date, str):
            raise TypeError("Parameters 'start_date' and 'end_date' must be ISO 8601 strings.")
        try:
            start_dt = datetime.fromisoformat(start_date)
            end_dt = datetime.fromisoformat(end_date)
        except Exception as error:
            raise ValueError("Dates must be ISO 8601 format, e.g., '2025-10-22T11:30:00'.") from error
        if end_dt < start_dt:
            raise ValueError("Parameter 'end_date' must be greater than or equal to 'start_date'.")

        def _fetch_logs_by_date(tx):
            query = """
            MATCH (log:Log)-[:MODIFIED]->(change:Change)
            WHERE log.timestamp >= $start_dt AND log.timestamp <= $end_dt
            RETURN log.log_id AS log_id, log.user AS user, log.action AS action, 
                   log.timestamp AS timestamp, log.origin_ip AS origin_ip, 
                   change.ttl_content AS ttl_content
            ORDER BY log.timestamp DESC
            """
            result = tx.run(query, start_dt=start_dt, end_dt=end_dt)
            rows: List[Dict[str, Any]] = []
            for record in result:
                row = record.data()
                if "timestamp" in row and hasattr(row["timestamp"], "isoformat"):
                    row["timestamp"] = row["timestamp"].isoformat()
                rows.append(row)
            return rows

        try:
            with self.get_driver().session() as session:
                return session.execute_read(_fetch_logs_by_date)
        except Exception as error:
            raise RuntimeError("Failed to fetch logs by date range.") from error

    def store_bulk_deletion(self, origin_ip: str, user: str, ttl_lines: List[str]) -> None:
        if not isinstance(origin_ip, str) or not origin_ip.strip():
            raise ValueError("Parameter 'origin_ip' must be a non-empty string.")
        if not isinstance(user, str) or not user.strip():
            raise ValueError("Parameter 'user' must be a non-empty string.")
        if not isinstance(ttl_lines, list):
            raise TypeError("Parameter 'ttl_lines' must be a list of strings.")
        if not ttl_lines:
            raise ValueError("Parameter 'ttl_lines' must not be empty.")
        if not all(isinstance(item, str) for item in ttl_lines):
            raise TypeError("All items in 'ttl_lines' must be strings.")

        timestamp = datetime.now()

        def _store_bulk_log(tx):
            for ttl_content in ttl_lines:
                log_id = str(uuid.uuid4())
                query = """
                CREATE (log:Log {
                    log_id: $log_id,
                    user: $user,
                    action: 'deletion',
                    timestamp: $timestamp,
                    origin_ip: $origin_ip
                })
                CREATE (change:Change { ttl_content: $ttl_content })
                CREATE (log)-[:MODIFIED]->(change)
                """
                tx.run(
                    query,
                    log_id=log_id,
                    user=user,
                    timestamp=timestamp,
                    origin_ip=origin_ip,
                    ttl_content=ttl_content,
                )

        try:
            with self.get_driver().session() as session:
                session.execute_write(_store_bulk_log)
        except Exception as error:
            raise RuntimeError("Failed to store bulk deletion logs.") from error
