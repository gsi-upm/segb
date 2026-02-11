"""Application service for TTL and modification workflows."""

from __future__ import annotations

from dataclasses import dataclass

from rdflib import Graph

from ..models.neo4j_model import Neo4jModel
from ..models.virtuoso_model import VirtuosoModel


@dataclass(slots=True)
class LogService:
    neo4j: Neo4jModel
    virtuoso: VirtuosoModel

    def insert_ttl(self, *, ttl_content: str, actor: str, origin_ip: str) -> dict:
        """Persists TTL data in Virtuoso and writes audit trail in Neo4j."""
        log_id = self.virtuoso.insert_ttl(ttl_content)
        self.neo4j.store_modification("insertion", origin_ip, actor, ttl_content)
        return {"message": "TTL inserted into both Virtuoso and Neo4j", "log_id": log_id}

    def get_events_ttl(self) -> str:
        return self.virtuoso.get_ttls()

    def execute_query(self, query: str) -> str:
        return self.virtuoso.run_custom_query(query)

    def get_modifications(self, limit: int):
        return self.neo4j.get_recent_logs(limit)

    def get_modifications_by_date(self, start_date: str, end_date: str):
        return self.neo4j.get_logs_by_date(start_date, end_date)

    def delete_all_ttls(self, *, actor: str, origin_ip: str) -> dict:
        """Deletes graph content and logs each removed triple as deletion audit."""
        ttl_text = self.virtuoso.get_ttls()
        if not ttl_text:
            return {"message": "No TTLs to delete"}

        graph = Graph()
        graph.parse(data=ttl_text, format="turtle")
        ttl_lines = [f"{s.n3()} {p.n3()} {o.n3()} ." for s, p, o in graph]

        if ttl_lines:
            self.neo4j.store_bulk_deletion(origin_ip, actor, ttl_lines)
        self.virtuoso.delete_all_triples()
        return {"message": "Graph cleared and deletions logged."}
