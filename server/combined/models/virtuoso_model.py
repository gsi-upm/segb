import os
import re
import uuid
import time
import logging
import threading
from datetime import datetime
from typing import Optional

import requests
from requests.auth import HTTPDigestAuth
from rdflib import Graph, Literal, Namespace, URIRef, BNode
from rdflib.namespace import RDF

from combined.utils.prefix_utils import (
    extract_prefixes,
    save_prefixes,
    load_prefixes,
    clean_prefixes_with_numbers,
    save_prefixes_and_entities
)

logger = logging.getLogger("mod_history_virt")
os.makedirs("/logs", exist_ok=True)
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler("/logs/modelV.log", mode="a", encoding="utf-8")
file_handler.setFormatter(
    logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s -> %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
)
logger.addHandler(file_handler)
logger.info("Starting model_V...")

class VirtuosoModel:
    _instance: Optional["VirtuosoModel"] = None
    _session: Optional[requests.Session] = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.session: Optional[requests.Session] = VirtuosoModel._session
        self.endpoint: str = self._get_env_var("VIRTUOSO_ENDPOINT", "http://amor-segb-virtuoso:8890/sparql-auth")
        self.graph_uri: str = self._get_env_var("VIRTUOSO_GRAPH_URI", "http://amor-segb/events")
        self.user: str = self._get_env_var("VIRTUOSO_USER", "dba")
        self.password: str = self._get_env_var("DBA_PASSWORD", "viryourbear")

    @staticmethod
    def _get_env_var(var_name: str, default_value: str) -> str:
        if not isinstance(var_name, str) or not var_name:
            raise ValueError("Environment variable name must be a non-empty string.")
        value = os.getenv(var_name, default_value)
        if not value or not value.strip():
            raise EnvironmentError(f"Missing or invalid environment variable: {var_name}")
        return value.strip()

    def connect_to_db(self, retries: int = 10, delay: int = 5) -> requests.Session:
        if not isinstance(retries, int) or retries <= 0:
            raise ValueError("Parameter 'retries' must be a positive integer.")
        if not isinstance(delay, (int, float)) or delay < 0:
            raise ValueError("Parameter 'delay' must be a non-negative number.")
        return self._connect_to_db(retries, delay)

    def _connect_to_db(self, retries: int = 10, delay: int = 5) -> requests.Session:
        with VirtuosoModel._lock:
            if VirtuosoModel._session is not None:
                raise RuntimeError("Virtuoso session already established. Use get_session().")

            session = requests.Session()
            session.auth = HTTPDigestAuth(self.user, self.password)
            session.headers.update({"Accept": "application/sparql-results+json"})

            last_error: Optional[BaseException] = None
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
                    last_error = requests.HTTPError(f"HTTP {response.status_code}: {response.text[:200]}")
                except Exception as error:
                    last_error = error
                if delay:
                    time.sleep(delay)

            raise ConnectionError(f"Could not connect to Virtuoso at '{self.endpoint}' with user '{self.user}'.") from last_error

    @classmethod
    def get_instance(cls) -> "VirtuosoModel":
        return cls()

    @classmethod
    def get_session(cls) -> requests.Session:
        if cls._session is None:
            raise RuntimeError("No active Virtuoso session. Call connect_to_db() first.")
        return cls._session

    def close_connection(self) -> None:
        self._close_connection()

    def _close_connection(self) -> None:
        with VirtuosoModel._lock:
            if VirtuosoModel._session:
                try:
                    VirtuosoModel._session.close()
                except Exception as error:
                    raise RuntimeError("Error while closing Virtuoso session.") from error
                finally:
                    VirtuosoModel._session = None
                    if VirtuosoModel._instance:
                        VirtuosoModel._instance.session = None
                        
                        
                        
    def ping(self, timeout_s: float = 1.0) -> bool:
        try:
            params = {
                "query": "ASK {}",
                "format": "application/sparql-results+json"
            }
            headers = {"Accept": "application/sparql-results+json"}
            r = self.get_session().get(self.endpoint, 
                             params=params, 
                             headers=headers,
                             timeout=timeout_s
                            )
            if r.status_code != 200:
                logger.warning(f"Virtuoso ping HTTP {r.status_code}")
                return False
            data = r.json()
            return bool(data.get("boolean") is True)
        except Exception as e:
            logger.warning(f"Virtuoso ping failed: {e}")
            return False

    def insert_ttl(self, ttl_content: str) -> str:
        if not isinstance(ttl_content, str) or ttl_content == "":
            raise ValueError("Parameter 'ttl_content' must be a non-empty string.")

        log_id = str(uuid.uuid4())
        rdf_graph = Graph()
        try:
            rdf_graph.parse(data=ttl_content, format="turtle")
        except Exception as error:
            logger.error("Failed to parse TTL content: %s", error)
            raise ValueError(f"Error parsing TTL content: {error}") from error

        prefixes = extract_prefixes(ttl_content)
        save_prefixes(prefixes)
        save_prefixes_and_entities(prefixes, ttl_content)

        for prefix, namespace_uri in load_prefixes().items():
            rdf_graph.bind(prefix, Namespace(namespace_uri))

        ntriples_data = rdf_graph.serialize(format="nt")
        if isinstance(ntriples_data, bytes):
            ntriples_data = ntriples_data.decode()

        logger.info("Parsed TTL content in NT format: %s", ntriples_data)

        sparql_update = f"""
        INSERT DATA {{
          GRAPH <{self.graph_uri}> {{
            {ntriples_data}
          }}
        }}
        """

        try:
            response = self.get_session().post(
                self.endpoint,
                data=sparql_update.encode("utf-8"),
                headers={"Content-Type": "application/sparql-update"},
                timeout=30,
            )
            response.raise_for_status()
            logger.info("TTL inserted successfully with log_id: %s", log_id)
        except requests.exceptions.RequestException as error:
            logger.error("Failed to insert TTL: %s", error)
            logger.error("Virtuoso response: %s", response.text if "response" in locals() else "No response")
            raise RuntimeError(f"Error inserting TTL into Virtuoso: {error}") from error

        return log_id

    def get_ttls(self) -> str:
        construct_query = f"""
        CONSTRUCT {{
            ?s ?p ?o .
        }}
        FROM <{self.graph_uri}>
        WHERE {{
            ?s ?p ?o .
        }}
        """
        try:
            response = self.get_session().get(
                self.endpoint,
                params={"query": construct_query, "format": "application/rdf+xml"},
                headers={"Accept": "application/rdf+xml"},
                timeout=30,
            )
        except requests.exceptions.RequestException as error:
            raise RuntimeError("Network error fetching TTLs from Virtuoso.") from error

        if response.status_code != 200:
            raise RuntimeError(f"Error fetching TTLs: {response.text}")

        rdf_graph = Graph()
        rdf_graph.parse(data=response.text, format="xml")

        for prefix, namespace_uri in load_prefixes().items():
            logger.debug("Binding prefix: %s to URI: %s", prefix, namespace_uri)
            rdf_graph.bind(prefix, Namespace(namespace_uri))

        turtle_data = rdf_graph.serialize(format="turtle")
        if isinstance(turtle_data, bytes):
            turtle_data = turtle_data.decode()

        logger.info("TTL result: %s", turtle_data)
        return clean_prefixes_with_numbers(turtle_data)

    def run_custom_query(self, query: str) -> str:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("Parameter 'query' must be a non-empty string.")

        logger.info("Executing custom SPARQL query: %s", query)

        forbidden_keywords = ["INSERT", "DELETE", "LOAD", "CLEAR", "DROP", "CREATE", "COPY", "MOVE", "ADD"]
        if re.search(r"(?i)^\s*(" + "|".join(forbidden_keywords) + r")\b", query.strip()):
            logger.warning("Blocked unsafe SPARQL query attempt.")
            raise PermissionError("Only read-only SPARQL queries are allowed.")

        is_construct = bool(re.match(r"(?i)^\s*CONSTRUCT\b", query.strip()))
        accept_header = "text/turtle" if is_construct else "application/sparql-results+json"

        try:
            response = self.get_session().get(
                self.endpoint,
                params={"query": query, "format": accept_header},
                headers={"Accept": accept_header},
                timeout=60,
            )
        except requests.exceptions.RequestException as error:
            raise RuntimeError("Network error executing SPARQL query.") from error

        if response.status_code != 200:
            logger.error("SPARQL query failed: %s", response.text)
            raise RuntimeError(f"Virtuoso error: {response.text}")

        rdf_graph = Graph()

        def _parse_binding_term(binding_value: dict):
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
            rdf_graph.parse(data=response.text, format="turtle")
        else:
            data_json = response.json()
            result_rows = data_json.get("results", {}).get("bindings", [])
            variables = data_json.get("head", {}).get("vars", [])
            for row in result_rows:
                if all(var in row for var in ["s", "p", "o"]):
                    subject = _parse_binding_term(row["s"])
                    predicate = _parse_binding_term(row["p"])
                    obj = _parse_binding_term(row["o"])
                    rdf_graph.add((subject, predicate, obj))
                else:
                    example_ns = Namespace("http://example.org/")
                    rdf_graph.bind("nocolision", example_ns)
                    node = BNode()
                    rdf_graph.add((node, RDF.type, example_ns.Result))
                    for var in variables:
                        if var in row:
                            rdf_graph.add((node, example_ns[var], _parse_binding_term(row[var])))

        for prefix, namespace_uri in load_prefixes().items():
            logger.debug("Binding prefix: %s -> %s", prefix, namespace_uri)
            rdf_graph.bind(prefix, Namespace(namespace_uri))

        turtle_result = rdf_graph.serialize(format="turtle", encoding="utf-8")
        if isinstance(turtle_result, bytes):
            turtle_result = turtle_result.decode()

        return clean_prefixes_with_numbers(turtle_result)

    def delete_all_triples(self) -> None:
        sparql_update = f"CLEAR GRAPH <{self.graph_uri}>"
        try:
            response = self.get_session().post(
                self.endpoint,
                data=sparql_update.encode("utf-8"),
                headers={"Content-Type": "application/sparql-update"},
                timeout=30,
            )
            response.raise_for_status()
            logger.info("All triples deleted from graph.")
        except requests.exceptions.RequestException as error:
            logger.error("Failed to clear graph: %s", error)
            raise RuntimeError(f"Error clearing graph in Virtuoso: {error}") from error
