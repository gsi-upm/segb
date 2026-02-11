"""Shared-context resolution utilities for cross-robot event linking.

The resolver is deterministic and rule-based (no ML requirement):
- each robot sends one independent observation payload,
- backend scores candidates and returns one canonical shared-context URI,
- optional reconciliation can merge previously ambiguous contexts.
"""

from __future__ import annotations

import re
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Literal

from pydantic import BaseModel, Field


@dataclass(slots=True)
class SharedContextPolicy:
    """Deterministic scoring and decision policy."""

    namespace: str = "https://gsi.upm.es/segb/shared-context/"
    resolver_version: str = "shared-context-v1-rules"
    time_window_seconds: float = 3.0
    candidate_window_multiplier: float = 2.0
    match_threshold: float = 0.85
    ambiguous_threshold: float = 0.70
    close_score_margin: float = 0.05
    strict_subject_mismatch: bool = True
    strict_experiment_mismatch: bool = True
    weight_time: float = 0.30
    weight_text: float = 0.35
    weight_subject: float = 0.20
    weight_modality: float = 0.10
    weight_context: float = 0.05


class SharedContextResolveRequest(BaseModel):
    """One independent robot observation that should map to a shared context."""

    event_kind: str
    observed_at: datetime
    experiment_uri: str | None = None
    subject_uri: str | None = None
    modality: str | None = None
    text: str | None = None
    observation_uri: str | None = None
    robot_uri: str | None = None
    time_window_seconds: float | None = None


class SharedContextResolveResponse(BaseModel):
    """Resolution result for a robot observation."""

    shared_context_uri: str
    status: Literal["matched", "created", "ambiguous"]
    confidence: float
    resolver_version: str
    candidate_count: int
    matched_candidate_uri: str | None = None
    close_candidates: list[str] = Field(default_factory=list)
    score_breakdown: dict[str, float] = Field(default_factory=dict)


class SharedContextReconcileResponse(BaseModel):
    """Result report for one reconciliation run."""

    scanned_ambiguous: int
    merged_count: int
    mappings: dict[str, str]
    resolver_version: str


@dataclass(slots=True)
class SharedContextRecord:
    """Stored shared-context candidate in resolver memory."""

    uri: str
    event_kind: str
    observed_at: datetime
    experiment_uri: str | None
    subject_uri: str | None
    modality: str | None
    canonical_text: str
    status: Literal["active", "ambiguous", "merged"]
    created_at: datetime
    updated_at: datetime
    observation_count: int = 1


class SharedContextResolver:
    """In-memory deterministic resolver for canonical shared-context URIs."""

    def __init__(self, *, policy: SharedContextPolicy | None = None) -> None:
        self.policy = policy if policy is not None else SharedContextPolicy()
        self._contexts: dict[str, SharedContextRecord] = {}
        self._aliases: dict[str, str] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _to_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _normalize_text(value: str | None) -> str:
        if not value:
            return ""
        lowered = value.lower().strip()
        lowered = re.sub(r"[^\w\s]", " ", lowered)
        return re.sub(r"\s+", " ", lowered).strip()

    @staticmethod
    def _normalize_atom(value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip().lower()
        return text or None

    def _resolve_alias(self, uri: str) -> str:
        current = uri
        while current in self._aliases:
            current = self._aliases[current]
        return current

    def _make_context_uri(self, event_kind: str) -> str:
        base = self.policy.namespace.rstrip("/")
        slug = re.sub(r"[^a-z0-9]+", "_", event_kind.lower().strip()).strip("_") or "event"
        return f"{base}/{slug}_{uuid.uuid4().hex[:16]}"

    def _subject_score(self, a: str | None, b: str | None) -> float:
        if a and b:
            return 1.0 if a == b else 0.0
        return 0.5

    def _modality_score(self, a: str | None, b: str | None) -> float:
        if a and b:
            return 1.0 if a == b else 0.0
        return 0.5

    def _context_score(self, a: str | None, b: str | None) -> float:
        if a and b:
            return 1.0 if a == b else 0.0
        return 0.5

    def _text_score(self, a: str, b: str) -> float | None:
        if not a or not b:
            return None
        tokens_a = set(a.split())
        tokens_b = set(b.split())
        token_union = tokens_a | tokens_b
        token_jaccard = 1.0 if not token_union else len(tokens_a & tokens_b) / len(token_union)
        sequence_similarity = SequenceMatcher(a=a, b=b).ratio()
        return 0.5 * token_jaccard + 0.5 * sequence_similarity

    def _time_score(self, delta_seconds: float, *, window_seconds: float) -> float:
        if delta_seconds >= window_seconds:
            return 0.0
        return max(0.0, 1.0 - (delta_seconds / window_seconds))

    def _score_candidate(
        self,
        *,
        request_observed_at: datetime,
        request_experiment_uri: str | None,
        request_subject_uri: str | None,
        request_modality: str | None,
        request_text: str,
        record: SharedContextRecord,
        window_seconds: float,
    ) -> tuple[float, dict[str, float]]:
        delta_seconds = abs((request_observed_at - record.observed_at).total_seconds())
        score_time = self._time_score(delta_seconds, window_seconds=window_seconds)
        score_text = self._text_score(request_text, record.canonical_text)
        score_subject = self._subject_score(request_subject_uri, record.subject_uri)
        score_modality = self._modality_score(request_modality, record.modality)
        score_context = self._context_score(request_experiment_uri, record.experiment_uri)

        weighted_values: list[tuple[str, float, float]] = [
            ("time", self.policy.weight_time, score_time),
            ("subject", self.policy.weight_subject, score_subject),
            ("modality", self.policy.weight_modality, score_modality),
            ("context", self.policy.weight_context, score_context),
        ]
        if score_text is not None:
            weighted_values.append(("text", self.policy.weight_text, score_text))

        weight_sum = sum(weight for _, weight, _ in weighted_values)
        if weight_sum <= 0:
            return 0.0, {}

        breakdown: dict[str, float] = {}
        total = 0.0
        for name, weight, score in weighted_values:
            normalized_weight = weight / weight_sum
            breakdown[name] = score
            total += normalized_weight * score
        return total, breakdown

    def _candidate_records(
        self,
        *,
        request_observed_at: datetime,
        request_event_kind: str,
        request_experiment_uri: str | None,
        request_subject_uri: str | None,
        request_modality: str | None,
        request_time_window: float,
    ) -> list[SharedContextRecord]:
        max_candidate_delta = request_time_window * self.policy.candidate_window_multiplier
        candidates: list[SharedContextRecord] = []
        for record in self._contexts.values():
            if record.status == "merged":
                continue
            if record.event_kind != request_event_kind:
                continue
            delta_seconds = abs((request_observed_at - record.observed_at).total_seconds())
            if delta_seconds > max_candidate_delta:
                continue
            if (
                self.policy.strict_experiment_mismatch
                and request_experiment_uri is not None
                and record.experiment_uri is not None
                and request_experiment_uri != record.experiment_uri
            ):
                continue
            if (
                self.policy.strict_subject_mismatch
                and request_subject_uri is not None
                and record.subject_uri is not None
                and request_subject_uri != record.subject_uri
            ):
                continue
            if request_modality and record.modality and request_modality != record.modality:
                # Keep as candidate; modality contributes via score.
                pass
            candidates.append(record)
        return candidates

    def _create_record(
        self,
        *,
        uri: str,
        request_observed_at: datetime,
        request_event_kind: str,
        request_experiment_uri: str | None,
        request_subject_uri: str | None,
        request_modality: str | None,
        request_text: str,
        status: Literal["active", "ambiguous"],
    ) -> SharedContextRecord:
        now = datetime.now(tz=timezone.utc)
        return SharedContextRecord(
            uri=uri,
            event_kind=request_event_kind,
            observed_at=request_observed_at,
            experiment_uri=request_experiment_uri,
            subject_uri=request_subject_uri,
            modality=request_modality,
            canonical_text=request_text,
            status=status,
            created_at=now,
            updated_at=now,
        )

    def resolve(self, request: SharedContextResolveRequest) -> SharedContextResolveResponse:
        request_observed_at = self._to_utc(request.observed_at)
        request_event_kind = self._normalize_atom(request.event_kind)
        if request_event_kind is None:
            raise ValueError("Parameter 'event_kind' must be a non-empty string.")

        request_experiment_uri = self._normalize_atom(request.experiment_uri)
        request_subject_uri = self._normalize_atom(request.subject_uri)
        request_modality = self._normalize_atom(request.modality)
        request_text = self._normalize_text(request.text)
        request_time_window = float(request.time_window_seconds or self.policy.time_window_seconds)

        with self._lock:
            candidates = self._candidate_records(
                request_observed_at=request_observed_at,
                request_event_kind=request_event_kind,
                request_experiment_uri=request_experiment_uri,
                request_subject_uri=request_subject_uri,
                request_modality=request_modality,
                request_time_window=request_time_window,
            )

            ranked: list[tuple[float, SharedContextRecord, dict[str, float]]] = []
            for candidate in candidates:
                score, breakdown = self._score_candidate(
                    request_observed_at=request_observed_at,
                    request_experiment_uri=request_experiment_uri,
                    request_subject_uri=request_subject_uri,
                    request_modality=request_modality,
                    request_text=request_text,
                    record=candidate,
                    window_seconds=request_time_window,
                )
                ranked.append((score, candidate, breakdown))

            # Highest score first; decision logic only inspects best and second-best matches.
            ranked.sort(key=lambda item: item[0], reverse=True)
            best = ranked[0] if ranked else None
            second = ranked[1] if len(ranked) > 1 else None

            # Strict match requires both absolute quality and enough separation from runner-up.
            if (
                best is not None
                and best[0] >= self.policy.match_threshold
                and (
                    second is None
                    or (best[0] - second[0]) >= self.policy.close_score_margin
                )
            ):
                _, record, breakdown = best
                record.observation_count += 1
                record.updated_at = datetime.now(tz=timezone.utc)
                record.observed_at = request_observed_at
                if record.subject_uri is None and request_subject_uri is not None:
                    record.subject_uri = request_subject_uri
                if record.experiment_uri is None and request_experiment_uri is not None:
                    record.experiment_uri = request_experiment_uri
                return SharedContextResolveResponse(
                    shared_context_uri=self._resolve_alias(record.uri),
                    status="matched",
                    confidence=best[0],
                    resolver_version=self.policy.resolver_version,
                    candidate_count=len(ranked),
                    matched_candidate_uri=record.uri,
                    score_breakdown=breakdown,
                )

            # Below strict match but still plausible -> keep as explicit ambiguous context.
            if best is not None and best[0] >= self.policy.ambiguous_threshold:
                uri = self._make_context_uri(request_event_kind)
                record = self._create_record(
                    uri=uri,
                    request_observed_at=request_observed_at,
                    request_event_kind=request_event_kind,
                    request_experiment_uri=request_experiment_uri,
                    request_subject_uri=request_subject_uri,
                    request_modality=request_modality,
                    request_text=request_text,
                    status="ambiguous",
                )
                self._contexts[uri] = record
                close_candidates = [best[1].uri]
                if second is not None:
                    close_candidates.append(second[1].uri)
                return SharedContextResolveResponse(
                    shared_context_uri=uri,
                    status="ambiguous",
                    confidence=best[0],
                    resolver_version=self.policy.resolver_version,
                    candidate_count=len(ranked),
                    matched_candidate_uri=best[1].uri,
                    close_candidates=close_candidates,
                    score_breakdown=best[2],
                )

            uri = self._make_context_uri(request_event_kind)
            record = self._create_record(
                uri=uri,
                request_observed_at=request_observed_at,
                request_event_kind=request_event_kind,
                request_experiment_uri=request_experiment_uri,
                request_subject_uri=request_subject_uri,
                request_modality=request_modality,
                request_text=request_text,
                status="active",
            )
            self._contexts[uri] = record
            return SharedContextResolveResponse(
                shared_context_uri=uri,
                status="created",
                confidence=0.0 if best is None else best[0],
                resolver_version=self.policy.resolver_version,
                candidate_count=len(ranked),
                matched_candidate_uri=None if best is None else best[1].uri,
                score_breakdown={} if best is None else best[2],
            )

    def reconcile_pending(self) -> SharedContextReconcileResponse:
        """Attempts to merge ambiguous contexts into active contexts."""
        with self._lock:
            ambiguous_records = [record for record in self._contexts.values() if record.status == "ambiguous"]
            merged_map: dict[str, str] = {}

            for record in ambiguous_records:
                candidates = [
                    candidate
                    for candidate in self._candidate_records(
                        request_observed_at=record.observed_at,
                        request_event_kind=record.event_kind,
                        request_experiment_uri=record.experiment_uri,
                        request_subject_uri=record.subject_uri,
                        request_modality=record.modality,
                        request_time_window=self.policy.time_window_seconds,
                    )
                    if candidate.uri != record.uri and candidate.status == "active"
                ]
                if not candidates:
                    continue

                ranked: list[tuple[float, SharedContextRecord]] = []
                for candidate in candidates:
                    score, _ = self._score_candidate(
                        request_observed_at=record.observed_at,
                        request_experiment_uri=record.experiment_uri,
                        request_subject_uri=record.subject_uri,
                        request_modality=record.modality,
                        request_text=record.canonical_text,
                        record=candidate,
                        window_seconds=self.policy.time_window_seconds,
                    )
                    ranked.append((score, candidate))
                ranked.sort(key=lambda item: item[0], reverse=True)
                best = ranked[0]
                second = ranked[1] if len(ranked) > 1 else None

                if best[0] < self.policy.match_threshold:
                    continue
                if second is not None and (best[0] - second[0]) < self.policy.close_score_margin:
                    continue

                canonical_uri = self._resolve_alias(best[1].uri)
                self._aliases[record.uri] = canonical_uri
                record.status = "merged"
                record.updated_at = datetime.now(tz=timezone.utc)
                merged_map[record.uri] = canonical_uri

            return SharedContextReconcileResponse(
                scanned_ambiguous=len(ambiguous_records),
                merged_count=len(merged_map),
                mappings=merged_map,
                resolver_version=self.policy.resolver_version,
            )

    def stats(self) -> dict[str, int | str]:
        with self._lock:
            active = sum(1 for record in self._contexts.values() if record.status == "active")
            ambiguous = sum(1 for record in self._contexts.values() if record.status == "ambiguous")
            merged = sum(1 for record in self._contexts.values() if record.status == "merged")
            aliases = len(self._aliases)
        return {
            "resolver_version": self.policy.resolver_version,
            "active_contexts": active,
            "ambiguous_contexts": ambiguous,
            "merged_contexts": merged,
            "aliases": aliases,
        }
