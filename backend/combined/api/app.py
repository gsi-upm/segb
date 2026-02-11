"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .router import router
from ..core.logging import configure_server_logger
from ..core.settings import load_api_description, load_api_info, load_settings
from ..services.runtime import create_lifespan

settings = load_settings()
logger = configure_server_logger(name="segb.server", level=settings.log_level, log_file=settings.log_file)
api_info = load_api_info(settings.api_info_file)
api_description = load_api_description(settings.api_description_file)

app = FastAPI(
    title=api_info["title"],
    description=api_description,
    version=settings.version,
    contact=api_info["contact"],
    license_info=api_info["license"],
    lifespan=create_lifespan(settings=settings, logger=logger),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
