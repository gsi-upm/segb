"""Application runtime lifecycle and service container."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from dataclasses import dataclass
from datetime import datetime

from fastapi import FastAPI

from ..core.settings import BackendSettings
from ..models.neo4j_model import Neo4jModel
from ..models.virtuoso_model import VirtuosoModel
from ..utils.shared_context import SharedContextPolicy, SharedContextResolver


@dataclass(slots=True)
class RuntimeServices:
    neo4j: Neo4jModel
    virtuoso: VirtuosoModel
    shared_context: SharedContextResolver
    neo4j_ok: bool = False
    virtuoso_ok: bool = False
    monitor_task: asyncio.Task | None = None


def build_services(settings: BackendSettings) -> RuntimeServices:
    """Builds the service container used by API handlers."""
    shared_context = SharedContextResolver(
        policy=SharedContextPolicy(
            namespace=settings.shared_context.namespace,
            time_window_seconds=settings.shared_context.time_window_seconds,
            match_threshold=settings.shared_context.match_threshold,
            ambiguous_threshold=settings.shared_context.ambiguous_threshold,
            close_score_margin=settings.shared_context.close_score_margin,
        )
    )
    return RuntimeServices(
        neo4j=Neo4jModel.get_instance(),
        virtuoso=VirtuosoModel.get_instance(),
        shared_context=shared_context,
    )


async def _retry_connect(name: str, connect_fn, settings: BackendSettings, logger: logging.Logger) -> None:
    delay_seconds = 1
    for attempt in range(1, settings.max_startup_retries + 1):
        try:
            connect_fn()
            logger.info("%s connected.", name)
            return
        except Exception as error:
            logger.warning("%s connection attempt %d failed: %s", name, attempt, error)
            if attempt >= settings.max_startup_retries:
                raise
            await asyncio.sleep(delay_seconds)
            delay_seconds = min(delay_seconds * 2, settings.max_backoff_seconds)


async def monitor_database_connections(
    app: FastAPI,
    *,
    settings: BackendSettings,
    logger: logging.Logger,
) -> None:
    """Background task that keeps DB readiness flags updated."""
    while True:
        await asyncio.sleep(settings.runtime_ping_interval)
        services: RuntimeServices = app.state.services

        try:
            services.neo4j_ok = bool(services.neo4j.ping())
        except Exception:
            services.neo4j_ok = False

        if not services.neo4j_ok:
            logger.warning("Neo4j seems down, attempting reconnection.")
            with contextlib.suppress(Exception):
                services.neo4j.close_connection()
            await _retry_connect(
                "Neo4j",
                lambda: services.neo4j.connect_to_db(logger=logger),
                settings,
                logger,
            )
            services.neo4j_ok = bool(services.neo4j.ping())

        try:
            services.virtuoso_ok = bool(services.virtuoso.ping())
        except Exception:
            services.virtuoso_ok = False

        if not services.virtuoso_ok:
            logger.warning("Virtuoso seems down, attempting reconnection.")
            with contextlib.suppress(Exception):
                services.virtuoso.close_connection()
            await _retry_connect(
                "Virtuoso",
                lambda: services.virtuoso.connect_to_db(),
                settings,
                logger,
            )
            services.virtuoso_ok = bool(services.virtuoso.ping())


def create_lifespan(*, settings: BackendSettings, logger: logging.Logger):
    """Creates FastAPI lifespan function with startup/shutdown orchestration."""

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info("Starting SEGB backend.")
        app.state.services = build_services(settings)
        services: RuntimeServices = app.state.services

        try:
            await _retry_connect("Neo4j", lambda: services.neo4j.connect_to_db(logger=logger), settings, logger)
            await _retry_connect("Virtuoso", lambda: services.virtuoso.connect_to_db(), settings, logger)
            services.neo4j_ok = bool(services.neo4j.ping())
            services.virtuoso_ok = bool(services.virtuoso.ping())
        except Exception as error:
            logger.error("Failed to initialize databases: %s", error)
            raise SystemExit(1)

        services.monitor_task = asyncio.create_task(
            monitor_database_connections(app, settings=settings, logger=logger)
        )

        try:
            yield
        finally:
            if services.monitor_task:
                services.monitor_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await services.monitor_task
            with contextlib.suppress(Exception):
                services.neo4j.close_connection()
            with contextlib.suppress(Exception):
                services.virtuoso.close_connection()
            logger.info("SEGB backend shutdown complete.")

    return lifespan
