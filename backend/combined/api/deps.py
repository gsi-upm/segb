"""FastAPI dependencies for accessing runtime services."""

from __future__ import annotations

from fastapi import HTTPException, Request, status

from ..services.runtime import RuntimeServices


def get_services(request: Request) -> RuntimeServices:
    services: RuntimeServices = request.app.state.services
    return services


def require_neo4j_ready(request: Request) -> None:
    services = get_services(request)
    if not services.neo4j_ok:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Neo4j is unavailable")


def require_virtuoso_ready(request: Request) -> None:
    services = get_services(request)
    if not services.virtuoso_ok:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Virtuoso is unavailable")
