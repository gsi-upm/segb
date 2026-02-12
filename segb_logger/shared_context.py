"""Client-side shared-context resolver utilities for robots."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import requests

from .types import SharedEventRequest

logger = logging.getLogger(__name__)


class HTTPSharedContextResolver:
    """Callable resolver that requests canonical shared-context URIs from SEGB backend.

    This can be passed into `SemanticSEGBLogger(shared_event_resolver=...)`.
    If the API call fails and `raise_on_error=False`, it returns `None`, allowing
    `get_shared_event_uri(...)` to fallback to local deterministic resolution.
    """

    def __init__(
        self,
        *,
        base_url: str,
        token: str | None = None,
        timeout_seconds: float = 5.0,
        verify_tls: bool = True,
        raise_on_error: bool = False,
        endpoint_path: str = "/shared-context/resolve",
        session: requests.Session | None = None,
    ) -> None:
        if not base_url or not isinstance(base_url, str):
            raise ValueError("Parameter 'base_url' must be a non-empty string.")
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout_seconds = timeout_seconds
        self.verify_tls = verify_tls
        self.raise_on_error = raise_on_error
        self.endpoint_path = endpoint_path
        self.session = session if session is not None else requests.Session()

    @staticmethod
    def _as_uri_text(value: Any) -> str | None:
        if value is None:
            return None
        return str(value)

    @staticmethod
    def _as_iso_datetime(value: datetime) -> str:
        return value.isoformat()

    def __call__(self, request: SharedEventRequest) -> str | None:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        payload = {
            "event_kind": request.event_kind,
            "observed_at": self._as_iso_datetime(request.observed_at),
            "subject_uri": self._as_uri_text(request.subject),
            "modality": request.modality,
            "text": request.text,
        }

        url = f"{self.base_url}{self.endpoint_path}"
        try:
            response = self.session.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.timeout_seconds,
                verify=self.verify_tls,
            )
            response.raise_for_status()
            body = response.json()
            shared_context_uri = body.get("shared_context_uri")
            if not shared_context_uri:
                raise ValueError("Response does not include 'shared_context_uri'.")
            return str(shared_context_uri)
        except Exception:
            if self.raise_on_error:
                raise
            logger.warning("Shared-context API resolve failed for url=%s. Falling back to local resolver.", url)
            return None

    def close(self) -> None:
        self.session.close()
