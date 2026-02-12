"""Data structures used by the semantic logger."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Mapping

from rdflib import URIRef

RDFTermLike = str | URIRef


class ActivityKind(str, Enum):
    """Controlled activity categories for deterministic logging.

    These values provide a stable, high-level API. The logger maps each kind to one
    or more ontology classes (RDF types). For custom ontological classes, use
    `extra_types` in `log_activity`.
    """

    LISTENING = "listening"
    DECISION = "decision"
    RESPONSE = "response"
    EMOTION_RECOGNITION = "emotion_recognition"
    EMOTION_ANALYSIS = "emotion_analysis"
    HUMAN_DETECTION = "human_detection"
    ML_RUN = "ml_run"


@dataclass(slots=True, frozen=True)
class EmotionScore:
    """One emotion score produced by an emotion recognizer."""

    category: RDFTermLike
    intensity: float
    confidence: float | None = None


@dataclass(slots=True, frozen=True)
class ModelUsage:
    """Model usage details inside a specific logged activity."""

    model: RDFTermLike
    parameters: Mapping[str, Any] = field(default_factory=dict)
    implementation: RDFTermLike | None = None
    software_label: str | None = None
    software_version: str | None = None


@dataclass(slots=True)
class RobotStateSnapshot:
    """Robot operational state captured at one point in time."""

    timestamp: datetime | None = None
    battery_level: float | None = None
    autonomy_mode: str | None = None
    mission_phase: str | None = None
    cpu_load: float | None = None
    memory_load: float | None = None
    network_status: str | None = None
    location: RDFTermLike | None = None
    note: str | None = None
    custom: Mapping[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class SharedEventPolicy:
    """Default policy used to resolve shared-event URIs."""

    namespace: str | None = None
    time_bucket_seconds: int = 1


@dataclass(slots=True, frozen=True)
class SharedEventRequest:
    """Normalized request passed to an optional external shared-event resolver."""

    event_kind: str
    observed_at: datetime
    subject: RDFTermLike | None = None
    text: str | None = None
    modality: str | None = None
    shared_event_namespace: str | None = None
    event_types: tuple[RDFTermLike, ...] = ()
    event_id: str | None = None
    time_bucket_seconds: int = 1


SharedEventResolver = Callable[[SharedEventRequest], RDFTermLike | None]
