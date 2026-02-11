"""Prefix persistence helpers for TTL ingestion and retrieval."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from rdflib import Graph, Literal
from rdflib.namespace import RDF

PREFIX_FILE = Path(os.getenv("PREFIX_FILE_PATH", "prefixes.json"))
RAG_OUTPUT_FILE = Path(os.getenv("RAG_PREFIX_OUTPUT_PATH", "/logs/for_RAG.json"))


def clean_prefixes_with_numbers(ttl_text: str) -> str:
    """Removes trailing digits from prefix labels while keeping namespace URIs intact."""
    prefix_pattern = re.compile(r"^@prefix\s+([a-zA-Z_]+[0-9]+):\s+<([^>]+)>\s+\.")

    replacements: dict[str, str] = {}
    lines: list[str] = []
    for line in ttl_text.splitlines():
        match = prefix_pattern.match(line)
        if not match:
            lines.append(line)
            continue
        original_prefix = match.group(1)
        uri = match.group(2)
        clean_prefix = re.sub(r"\d+", "", original_prefix)
        replacements[original_prefix] = clean_prefix
        lines.append(f"@prefix {clean_prefix}: <{uri}> .")

    cleaned = "\n".join(lines)
    for original, normalized in replacements.items():
        cleaned = re.sub(rf"\b{original}:", f"{normalized}:", cleaned)
    return cleaned


def save_prefixes(new_prefixes: dict[str, str]) -> None:
    existing = load_prefixes()
    existing.update(new_prefixes)
    PREFIX_FILE.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")


def load_prefixes() -> dict[str, str]:
    if not PREFIX_FILE.exists():
        return {}
    return json.loads(PREFIX_FILE.read_text(encoding="utf-8"))


def extract_prefixes(ttl_text: str) -> dict[str, str]:
    matches = re.findall(r"@prefix\s+([a-zA-Z0-9\-_]+):\s+<([^>]+)>", ttl_text)
    return {prefix: namespace for prefix, namespace in matches}


def extract_classes(ttl_text: str) -> list[str]:
    return sorted(set(re.findall(r"\s+a\s+([\w\-]+:[\w\-]+)\s*[,;.]", ttl_text)))


def extract_properties(ttl_text: str) -> list[str]:
    return sorted(set(re.findall(r"^\s*([\w\-]+:[\w\-]+)\s+", ttl_text, flags=re.MULTILINE)))


def save_prefixes_and_entities(prefixes: dict[str, str], ttl_text: str) -> None:
    """Stores lightweight RAG hints (prefixes, classes, predicates, patterns)."""
    graph = Graph()
    patterns: dict[str, set[str]] = {}

    try:
        graph.parse(data=ttl_text, format="turtle")
    except Exception:
        # RAG cache should not block ingestion.
        return

    subject_classes: dict[object, set[object]] = {}
    for subject, _, obj in graph.triples((None, RDF.type, None)):
        subject_classes.setdefault(subject, set()).add(obj)

    for subject, predicate, obj in graph:
        if predicate == RDF.type:
            continue
        for cls in subject_classes.get(subject, set()):
            patterns.setdefault(str(cls), set()).add(str(predicate))
        if isinstance(obj, Literal) and obj.datatype:
            patterns.setdefault(str(predicate), set()).add(str(obj.datatype))

    def to_prefixed(uri: str) -> str:
        for prefix, namespace in graph.namespaces():
            namespace_str = str(namespace)
            if uri.startswith(namespace_str):
                return f"{prefix}:{uri[len(namespace_str):]}"
        return uri

    serialized_patterns = {
        to_prefixed(key): sorted(to_prefixed(value) for value in values)
        for key, values in patterns.items()
    }

    payload = {
        "prefixes": prefixes,
        "classes": extract_classes(ttl_text),
        "properties": extract_properties(ttl_text),
        "patterns": serialized_patterns,
    }

    RAG_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    RAG_OUTPUT_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
