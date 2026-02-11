"""Neo4j adapter used by application services."""

from __future__ import annotations

import os
import threading
import time
import uuid
from datetime import datetime
from typing import Any

from neo4j import GraphDatabase


class Neo4jModel:
    """Small singleton wrapper around Neo4j driver.

    This adapter keeps all Cypher operations in one place so services stay focused
    on use-cases instead of database specifics.
    """

    _instance: "Neo4jModel | None" = None
    _driver: Any | None = None
    _lock = threading.Lock()
    _schema_initialized = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        self.driver = Neo4jModel._driver

    @classmethod
    def get_instance(cls) -> "Neo4jModel":
        return cls()

    @classmethod
    def get_driver(cls):
        if cls._driver is None:
            raise RuntimeError("Neo4j connection is not initialized.")
        return cls._driver

    def connect_to_db(self, retries: int = 10, delay: float = 5.0, logger=None):
        """Connects driver once and ensures minimal n10s schema."""
        uri = os.getenv("NEO4J_URI")
        user = os.getenv("NEO4J_USER")
        password = os.getenv("NEO4J_PASSWORD")
        if not uri or not user or not password:
            raise EnvironmentError("NEO4J_URI, NEO4J_USER and NEO4J_PASSWORD must be configured.")

        with Neo4jModel._lock:
            if Neo4jModel._driver is not None:
                self.driver = Neo4jModel._driver
                return self.driver

            last_error: Exception | None = None
            for _ in range(retries):
                try:
                    driver = GraphDatabase.driver(uri, auth=(user, password))
                    driver.verify_connectivity()
                    Neo4jModel._driver = driver
                    self.driver = driver
                    break
                except Exception as error:  # pragma: no cover - depends on external DB
                    last_error = error
                    time.sleep(delay)
            else:
                raise ConnectionError(f"Could not connect to Neo4j at '{uri}'.") from last_error

        if not Neo4jModel._schema_initialized:
            self._initialize_schema(logger=logger)
            Neo4jModel._schema_initialized = True

        return self.driver

    def _initialize_schema(self, logger=None) -> None:
        """Creates uniqueness constraint and initializes n10s config once."""
        log = logger
        with self.get_driver().session() as session:
            try:
                session.run(
                    """
                    CREATE CONSTRAINT n10s_unique_uri
                    IF NOT EXISTS
                    FOR (r:Resource)
                    REQUIRE r.uri IS UNIQUE
                    """
                )
            except Exception:
                # Keep backward compatibility with older Neo4j syntax.
                session.run("CREATE CONSTRAINT ON (r:Resource) ASSERT r.uri IS UNIQUE")

            try:
                if session.run("CALL n10s.graphconfig.show()").peek() is None:
                    session.run("CALL n10s.graphconfig.init()")
            except Exception:
                # graphconfig may already exist or plugin may differ by deployment.
                pass

            if log:
                log.info("Neo4j schema ensured.")

    def close_connection(self) -> None:
        with Neo4jModel._lock:
            if Neo4jModel._driver is not None:
                Neo4jModel._driver.close()
            Neo4jModel._driver = None
            Neo4jModel._schema_initialized = False
            self.driver = None

    def ping(self, timeout_ms: int = 1000) -> bool:
        if self.driver is None:
            return False
        try:
            with self.driver.session() as session:
                session.run("RETURN 1 AS ok", timeout=timeout_ms).consume()
            return True
        except Exception:
            return False

    def store_modification(self, action: str, origin_ip: str, user: str, ttl_content: str) -> str:
        log_id = str(uuid.uuid4())
        timestamp = datetime.now()

        def _write(tx):
            tx.run(
                """
                CREATE (log:Log {
                    log_id: $log_id,
                    user: $user,
                    action: $action,
                    timestamp: $timestamp,
                    origin_ip: $origin_ip
                })
                CREATE (change:Change { ttl_content: $ttl_content })
                CREATE (log)-[:MODIFIED]->(change)
                """,
                log_id=log_id,
                user=user,
                action=action,
                timestamp=timestamp,
                origin_ip=origin_ip,
                ttl_content=ttl_content,
            )

        with self.get_driver().session() as session:
            session.execute_write(_write)
        return log_id

    def get_recent_logs(self, limit: int):
        def _read(tx):
            result = tx.run(
                """
                MATCH (log:Log)-[:MODIFIED]->(change:Change)
                RETURN log.log_id AS log_id, log.user AS user, log.action AS action,
                       log.timestamp AS timestamp, log.origin_ip AS origin_ip,
                       change.ttl_content AS ttl_content
                ORDER BY log.timestamp DESC
                LIMIT $limit
                """,
                limit=limit,
            )
            rows = []
            for record in result:
                row = record.data()
                if hasattr(row.get("timestamp"), "isoformat"):
                    row["timestamp"] = row["timestamp"].isoformat()
                rows.append(row)
            return rows

        with self.get_driver().session() as session:
            return session.execute_read(_read)

    def get_logs_by_date(self, start_date: str, end_date: str):
        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date)

        def _read(tx):
            result = tx.run(
                """
                MATCH (log:Log)-[:MODIFIED]->(change:Change)
                WHERE log.timestamp >= $start_dt AND log.timestamp <= $end_dt
                RETURN log.log_id AS log_id, log.user AS user, log.action AS action,
                       log.timestamp AS timestamp, log.origin_ip AS origin_ip,
                       change.ttl_content AS ttl_content
                ORDER BY log.timestamp DESC
                """,
                start_dt=start_dt,
                end_dt=end_dt,
            )
            rows = []
            for record in result:
                row = record.data()
                if hasattr(row.get("timestamp"), "isoformat"):
                    row["timestamp"] = row["timestamp"].isoformat()
                rows.append(row)
            return rows

        with self.get_driver().session() as session:
            return session.execute_read(_read)

    def store_bulk_deletion(self, origin_ip: str, user: str, ttl_lines: list[str]) -> None:
        timestamp = datetime.now()

        def _write(tx):
            for ttl_content in ttl_lines:
                tx.run(
                    """
                    CREATE (log:Log {
                        log_id: $log_id,
                        user: $user,
                        action: 'deletion',
                        timestamp: $timestamp,
                        origin_ip: $origin_ip
                    })
                    CREATE (change:Change { ttl_content: $ttl_content })
                    CREATE (log)-[:MODIFIED]->(change)
                    """,
                    log_id=str(uuid.uuid4()),
                    user=user,
                    timestamp=timestamp,
                    origin_ip=origin_ip,
                    ttl_content=ttl_content,
                )

        with self.get_driver().session() as session:
            session.execute_write(_write)
