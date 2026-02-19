"""HTTP publisher to send semantic logs to a central SEGB API."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import requests
from rdflib import Graph


class SEGBPublisher:
    """Publishes Turtle logs to the `/ttl` endpoint of a SEGB API."""

    def __init__(
        self,
        *,
        base_url: str,
        token: str | None = None,
        default_user: str | None = None,
        timeout_seconds: float = 20.0,
        verify_tls: bool = True,
        queue_file: str | None = None,
    ) -> None:
        if not isinstance(base_url, str) or not base_url.strip():
            raise ValueError("Parameter 'base_url' must be a non-empty string.")
        if timeout_seconds <= 0:
            raise ValueError("Parameter 'timeout_seconds' must be > 0.")
        self.base_url = base_url.rstrip("/")
        self.endpoint = f"{self.base_url}/ttl"
        self.token = token
        self.default_user = default_user
        self.timeout_seconds = timeout_seconds
        self.verify_tls = verify_tls
        self.queue_file = Path(queue_file).expanduser() if queue_file else None

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _post_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = requests.post(
            self.endpoint,
            json=payload,
            headers=self._headers(),
            timeout=self.timeout_seconds,
            verify=self.verify_tls,
        )
        if response.status_code >= 400:
            raise RuntimeError(f"SEGB API responded with HTTP {response.status_code}: {response.text}")
        if not response.content:
            return {"status_code": response.status_code}
        try:
            return response.json()
        except ValueError:
            return {"status_code": response.status_code, "body": response.text}

    def _post_json_endpoint(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = requests.post(
            endpoint,
            json=payload,
            headers=self._headers(),
            timeout=self.timeout_seconds,
            verify=self.verify_tls,
        )
        if response.status_code >= 400:
            raise RuntimeError(f"SEGB API responded with HTTP {response.status_code}: {response.text}")
        if not response.content:
            return {"status_code": response.status_code}
        try:
            return response.json()
        except ValueError:
            return {"status_code": response.status_code, "body": response.text}

    def _enqueue(self, payload: dict[str, Any]) -> None:
        if self.queue_file is None:
            return
        self.queue_file.parent.mkdir(parents=True, exist_ok=True)
        with self.queue_file.open("a", encoding="utf-8") as file_pointer:
            file_pointer.write(json.dumps(payload, ensure_ascii=True) + "\n")

    def publish_turtle(self, ttl_content: str, *, user: str | None = None) -> dict[str, Any]:
        """Publishes a turtle document. Optionally enqueues on failure."""
        if not isinstance(ttl_content, str) or not ttl_content.strip():
            raise ValueError("Parameter 'ttl_content' must be a non-empty string.")
        payload = {"ttl_content": ttl_content, "user": user or self.default_user}
        try:
            return self._post_payload(payload)
        except Exception:
            self._enqueue(payload)
            raise

    def publish_graph(self, graph: Graph, *, user: str | None = None) -> dict[str, Any]:
        """Serializes an RDF graph to turtle and publishes it."""
        ttl = graph.serialize(format="turtle")
        ttl_text = ttl.decode("utf-8") if isinstance(ttl, bytes) else ttl
        return self.publish_turtle(ttl_text, user=user)

    def delete_all_ttls(self, *, user: str | None = None) -> dict[str, Any]:
        """Clears backend triples through `/ttl/delete_all`."""
        payload = {"user": user or self.default_user}
        endpoint = f"{self.base_url}/ttl/delete_all"
        return self._post_json_endpoint(endpoint, payload)

    def flush_queue(self) -> list[dict[str, Any]]:
        """
        Tries to publish pending queued payloads.
        Returns the list of successful API responses.
        """
        if self.queue_file is None or not self.queue_file.exists():
            return []

        successful_responses: list[dict[str, Any]] = []
        remaining_payloads: list[dict[str, Any]] = []
        with self.queue_file.open("r", encoding="utf-8") as file_pointer:
            lines = [line.strip() for line in file_pointer if line.strip()]

        for line in lines:
            try:
                payload = json.loads(line)
                result = self._post_payload(payload)
                successful_responses.append(result)
            except Exception:
                try:
                    parsed_payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                remaining_payloads.append(parsed_payload)

        if remaining_payloads:
            with self.queue_file.open("w", encoding="utf-8") as file_pointer:
                for payload in remaining_payloads:
                    file_pointer.write(json.dumps(payload, ensure_ascii=True) + "\n")
        else:
            self.queue_file.unlink(missing_ok=True)

        return successful_responses
