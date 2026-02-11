"""Virtuoso adapter used by application services."""

from __future__ import annotations

import os
import re
import threading
import time
import uuid
from typing import Any

import requests
from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF
from requests.auth import HTTPDigestAuth

from ..utils.prefix_utils import (
    clean_prefixes_with_numbers,
    extract_prefixes,
    load_prefixes,
    save_prefixes,
    save_prefixes_and_entities,
)


class VirtuosoModel:
    """Thread-safe singleton wrapper around Virtuoso HTTP API."""

    _instance: "VirtuosoModel | None" = None
    _session: requests.Session | None = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        self.session = VirtuosoModel._session
        self.endpoint = os.getenv("VIRTUOSO_ENDPOINT", "http://amor-segb-virtuoso:8890/sparql-auth")
        self.graph_uri = os.getenv("VIRTUOSO_GRAPH_URI", "http://amor-segb/events")
        self.user = os.getenv("VIRTUOSO_USER", "dba")
        self.password = os.getenv("DBA_PASSWORD", "viryourbear")

    @classmethod
    def get_instance(cls) -> "VirtuosoModel":
        return cls()

    @classmethod
    def get_session(cls) -> requests.Session:
        if cls._session is None:
            raise RuntimeError("Virtuoso session is not initialized.")
        return cls._session

    def connect_to_db(self, retries: int = 10, delay: float = 5.0) -> requests.Session:
        with VirtuosoModel._lock:
            if VirtuosoModel._session is not None:
                self.session = VirtuosoModel._session
                return self.session

            session = requests.Session()
            session.auth = HTTPDigestAuth(self.user, self.password)
            session.headers.update({"Accept": "application/sparql-results+json"})

            last_error: Exception | None = None
            for _ in range(retries):
                try:
                    response = session.get(
                        self.endpoint,
                        params={"query": "ASK { ?s ?p ?o }", "timeout": 10000},
                        timeout=15,
                    )
                    if response.status_code == 200:
                        VirtuosoModel._session = session
                        self.session = session
                        return session
                    last_error = RuntimeError(f"HTTP {response.status_code}: {response.text[:120]}")
                except Exception as error:  # pragma: no cover - depends on external DB
                    last_error = error
                time.sleep(delay)

        raise ConnectionError(f"Could not connect to Virtuoso endpoint '{self.endpoint}'.") from last_error

    def close_connection(self) -> None:
        with VirtuosoModel._lock:
            if VirtuosoModel._session:
                VirtuosoModel._session.close()
            VirtuosoModel._session = None
            self.session = None

    def ping(self, timeout_s: float = 1.0) -> bool:
        try:
            response = self.get_session().get(
                self.endpoint,
                params={"query": "ASK {}", "format": "application/sparql-results+json"},
                headers={"Accept": "application/sparql-results+json"},
                timeout=timeout_s,
            )
            if response.status_code != 200:
                return False
            return bool(response.json().get("boolean") is True)
        except Exception:
            return False

    def insert_ttl(self, ttl_content: str) -> str:
        """Parses TTL once and inserts its canonical N-Triples into target graph."""
        log_id = str(uuid.uuid4())
        graph = Graph()
        graph.parse(data=ttl_content, format="turtle")

        prefixes = extract_prefixes(ttl_content)
        save_prefixes(prefixes)
        save_prefixes_and_entities(prefixes, ttl_content)

        for prefix, namespace_uri in load_prefixes().items():
            graph.bind(prefix, Namespace(namespace_uri))

        nt_data = graph.serialize(format="nt")
        if isinstance(nt_data, bytes):
            nt_data = nt_data.decode()

        sparql_update = f"""
        INSERT DATA {{
          GRAPH <{self.graph_uri}> {{
            {nt_data}
          }}
        }}
        """

        response = self.get_session().post(
            self.endpoint,
            data=sparql_update.encode("utf-8"),
            headers={"Content-Type": "application/sparql-update"},
            timeout=30,
        )
        response.raise_for_status()
        return log_id

    def get_ttls(self) -> str:
        query = f"""
        CONSTRUCT {{ ?s ?p ?o . }}
        FROM <{self.graph_uri}>
        WHERE {{ ?s ?p ?o . }}
        """

        response = self.get_session().get(
            self.endpoint,
            params={"query": query, "format": "application/rdf+xml"},
            headers={"Accept": "application/rdf+xml"},
            timeout=30,
        )
        response.raise_for_status()

        graph = Graph()
        graph.parse(data=response.text, format="xml")

        for prefix, namespace_uri in load_prefixes().items():
            graph.bind(prefix, Namespace(namespace_uri))

        turtle_data = graph.serialize(format="turtle")
        if isinstance(turtle_data, bytes):
            turtle_data = turtle_data.decode()
        return clean_prefixes_with_numbers(turtle_data)

    def run_custom_query(self, query: str) -> str:
        forbidden = ["INSERT", "DELETE", "LOAD", "CLEAR", "DROP", "CREATE", "COPY", "MOVE", "ADD"]
        if re.search(r"(?i)^\s*(" + "|".join(forbidden) + r")\b", query.strip()):
            raise PermissionError("Only read-only SPARQL queries are allowed.")

        is_construct = bool(re.match(r"(?i)^\s*CONSTRUCT\b", query.strip()))
        accept_header = "text/turtle" if is_construct else "application/sparql-results+json"

        response = self.get_session().get(
            self.endpoint,
            params={"query": query, "format": accept_header},
            headers={"Accept": accept_header},
            timeout=60,
        )
        response.raise_for_status()

        graph = Graph()

        def parse_binding_term(binding_value: dict[str, Any]):
            value_type = binding_value.get("type")
            value = binding_value.get("value")
            if value_type == "uri":
                return URIRef(value)
            if value_type == "literal":
                return Literal(value, lang=binding_value.get("xml:lang"), datatype=binding_value.get("datatype"))
            if value_type == "bnode":
                return BNode(value)
            return Literal(value)

        if is_construct:
            graph.parse(data=response.text, format="turtle")
        else:
            data_json = response.json()
            rows = data_json.get("results", {}).get("bindings", [])
            variables = data_json.get("head", {}).get("vars", [])
            for row in rows:
                if all(var in row for var in ["s", "p", "o"]):
                    graph.add((parse_binding_term(row["s"]), parse_binding_term(row["p"]), parse_binding_term(row["o"])))
                else:
                    result_ns = Namespace("http://example.org/")
                    node = BNode()
                    graph.add((node, RDF.type, result_ns.Result))
                    for var in variables:
                        if var in row:
                            graph.add((node, result_ns[var], parse_binding_term(row[var])))

        for prefix, namespace_uri in load_prefixes().items():
            graph.bind(prefix, Namespace(namespace_uri))

        turtle_result = graph.serialize(format="turtle", encoding="utf-8")
        if isinstance(turtle_result, bytes):
            turtle_result = turtle_result.decode()
        return clean_prefixes_with_numbers(turtle_result)

    def delete_all_triples(self) -> None:
        response = self.get_session().post(
            self.endpoint,
            data=f"CLEAR GRAPH <{self.graph_uri}>".encode("utf-8"),
            headers={"Content-Type": "application/sparql-update"},
            timeout=30,
        )
        response.raise_for_status()
