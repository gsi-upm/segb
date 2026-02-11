"""Semantic logger to generate SEGB-compliant RDF logs for robots.

Important operational note:
- This module does not read sensors, ROS topics, databases or the central KG by itself.
- It only converts facts already known by the robot software stack into RDF triples.
- The caller (your ROS nodes/orchestrator) is responsible for acquiring observations
  (ASR output, detection events, emotion scores, telemetry, etc.) and passing them here.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Sequence

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import FOAF, PROV, RDF, RDFS, XSD

from .namespaces import (
    AMOR,
    AMOR_EXP,
    DEFAULT_PREFIXES,
    EMOML,
    MLS,
    OA,
    ONYX,
    ORO,
    SCHEMA,
    SEGB,
)
from .types import (
    EmotionScore,
    ModelUsage,
    RDFTermLike,
    RobotStateSnapshot,
    SharedEventPolicy,
    SharedEventRequest,
    SharedEventResolver,
)


class SemanticSEGBLogger:
    """Builds semantic logs to be published into a SEGB knowledge graph.

    Conceptually this class is a serializer/mapper:
    - Input: already computed events/states from robot components.
    - Output: RDF triples aligned with SEGB, ORO, ONYX, MLS and PROV.

    It does not decide *what happened*; it only records *what the caller says happened*.
    """
    DEFAULT_SHARED_EVENT_NAMESPACE = "https://gsi.upm.es/segb/shared-events/"

    def __init__(
        self,
        *,
        base_namespace: str,
        robot_id: str,
        robot_name: str | None = None,
        default_language: str = "en",
        graph: Graph | None = None,
        shared_event_policy: SharedEventPolicy | None = None,
        shared_event_resolver: SharedEventResolver | None = None,
    ) -> None:
        self.base_namespace = self._normalize_base_namespace(base_namespace)
        self.base = Namespace(self.base_namespace)
        self.default_language = default_language
        self.graph = graph if graph is not None else Graph()
        self.prefixes: dict[str, Namespace] = dict(DEFAULT_PREFIXES)
        self.prefixes["robotlog"] = self.base
        for prefix, namespace in self.prefixes.items():
            self.graph.bind(prefix, namespace)

        self.robot_uri = self.resource_uri("robot", robot_id)
        self.default_experiment_uri: URIRef | None = None
        self.shared_event_policy = shared_event_policy if shared_event_policy is not None else SharedEventPolicy()
        self.shared_event_resolver = shared_event_resolver
        self.register_robot(robot_name=robot_name)

    @staticmethod
    def _normalize_base_namespace(base_namespace: str) -> str:
        if not isinstance(base_namespace, str) or not base_namespace.strip():
            raise ValueError("Parameter 'base_namespace' must be a non-empty string.")
        ns = base_namespace.strip()
        if ns.endswith(("#", "/")):
            return ns
        return ns + "/"

    @staticmethod
    def _slugify(text: str) -> str:
        slug = re.sub(r"[^A-Za-z0-9]+", "_", text.strip()).strip("_").lower()
        return slug or uuid.uuid4().hex

    def resolve_term(self, value: RDFTermLike) -> URIRef:
        """Resolves a URIRef, absolute URI string, prefix:name string, or local identifier."""
        if isinstance(value, URIRef):
            return value
        if not isinstance(value, str) or not value.strip():
            raise ValueError("RDF term must be a non-empty string or URIRef.")
        term = value.strip()
        if term.startswith(("http://", "https://")):
            return URIRef(term)
        if ":" in term:
            prefix, local = term.split(":", 1)
            namespace = self.prefixes.get(prefix)
            if namespace is None:
                raise ValueError(
                    f"Unknown namespace prefix '{prefix}'. "
                    f"Known prefixes: {', '.join(sorted(self.prefixes))}."
                )
            if not local:
                raise ValueError("Invalid prefixed name. Missing local part after ':'.")
            return namespace[local]
        return self.base[term]

    def resource_uri(self, kind: str, resource_id: str | None = None) -> URIRef:
        """Builds a URI inside the robot log namespace."""
        if not isinstance(kind, str) or not kind.strip():
            raise ValueError("Parameter 'kind' must be a non-empty string.")
        suffix = self._slugify(resource_id) if resource_id else uuid.uuid4().hex
        return self.base[f"{kind.strip()}/{suffix}"]

    def _literal(self, value: Any) -> Literal:
        if isinstance(value, Literal):
            return value
        if isinstance(value, datetime):
            dt = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
            return Literal(dt.isoformat(), datatype=XSD.dateTime)
        if isinstance(value, bool):
            return Literal(value, datatype=XSD.boolean)
        if isinstance(value, int):
            return Literal(value, datatype=XSD.long)
        if isinstance(value, float):
            return Literal(value, datatype=XSD.double)
        return Literal(str(value))

    def _iter_terms(self, values: Sequence[RDFTermLike] | None) -> Iterable[URIRef]:
        if values is None:
            return ()
        return (self.resolve_term(value) for value in values)

    @staticmethod
    def _canonicalize_text(value: str | None) -> str:
        if value is None:
            return ""
        return re.sub(r"\s+", " ", value.strip().lower())

    @staticmethod
    def _bucket_datetime_seconds(observed_at: datetime, *, bucket_seconds: int) -> datetime:
        if bucket_seconds <= 0:
            raise ValueError("Parameter 'bucket_seconds' must be a positive integer.")
        utc_value = observed_at if observed_at.tzinfo is not None else observed_at.replace(tzinfo=timezone.utc)
        utc_value = utc_value.astimezone(timezone.utc)
        bucket_epoch = int(utc_value.timestamp()) // bucket_seconds * bucket_seconds
        return datetime.fromtimestamp(bucket_epoch, tz=timezone.utc)

    def register_robot(
        self,
        *,
        robot_uri: RDFTermLike | None = None,
        robot_name: str | None = None,
        owner: RDFTermLike | None = None,
    ) -> URIRef:
        """Registers the robot agent in the local graph."""
        uri = self.resolve_term(robot_uri) if robot_uri is not None else self.robot_uri
        self.graph.add((uri, RDF.type, PROV.SoftwareAgent))
        self.graph.add((uri, RDF.type, ORO.Robot))
        if robot_name:
            self.graph.add((uri, ORO.hasName, Literal(robot_name, lang=self.default_language)))
        if owner:
            self.graph.add((uri, ORO.belongsTo, self.resolve_term(owner)))
        self.robot_uri = uri
        return uri

    def register_human(
        self,
        human_id: str,
        *,
        first_name: str | None = None,
        homepage: str | None = None,
    ) -> URIRef:
        """Registers a human actor often used as interaction subject.

        Usually called when the robot identifies a person for the first time in a session.
        After that, the same URI can be reused in later triples; no need to recreate it.
        """
        human_uri = self.resource_uri("human", human_id)
        self.graph.add((human_uri, RDF.type, PROV.Person))
        self.graph.add((human_uri, RDF.type, FOAF.Person))
        self.graph.add((human_uri, RDF.type, ORO.Human))
        if first_name:
            self.graph.add((human_uri, FOAF.firstName, Literal(first_name, lang=self.default_language)))
        if homepage:
            self.graph.add((human_uri, FOAF.homepage, URIRef(homepage)))
        return human_uri

    def start_experiment(
        self,
        experiment_id: str,
        *,
        label: str | None = None,
        subject: RDFTermLike | None = None,
        started_at: datetime | None = None,
    ) -> URIRef:
        """Creates a new experiment and sets it as default context."""
        experiment_uri = self.resource_uri("experiment", experiment_id)
        self.graph.add((experiment_uri, RDF.type, AMOR_EXP.Experiment))
        self.graph.add((experiment_uri, AMOR_EXP.hasExecutor, self.robot_uri))
        if label:
            self.graph.add((experiment_uri, RDFS.label, Literal(label, lang=self.default_language)))
        if subject:
            self.graph.add((experiment_uri, AMOR_EXP.hasExperimentationSubject, self.resolve_term(subject)))
        if started_at:
            self.graph.add((experiment_uri, PROV.startedAtTime, self._literal(started_at)))
        self.default_experiment_uri = experiment_uri
        return experiment_uri

    def _add_shared_event_metadata(
        self,
        *,
        event_uri: URIRef,
        event_kind: str,
        observed_at: datetime,
        subject_uri: URIRef | None,
        text: str | None,
        modality: str | None,
        experiment_uri: URIRef | None,
        event_types: Sequence[RDFTermLike] | None,
        time_bucket_seconds: int,
        event_key: str | None = None,
    ) -> None:
        canonical_text = self._canonicalize_text(text)
        canonical_modality = self._canonicalize_text(modality)
        canonical_kind = self._canonicalize_text(event_kind)
        bucket_dt = self._bucket_datetime_seconds(observed_at, bucket_seconds=time_bucket_seconds)

        self.graph.add((event_uri, RDF.type, PROV.Entity))
        self.graph.add((event_uri, RDF.type, SEGB.Trigger))
        self.graph.add((event_uri, RDF.type, SCHEMA.Event))
        if event_key:
            self.graph.add((event_uri, SCHEMA.identifier, Literal(event_key)))
        if canonical_kind:
            self.graph.add((event_uri, SCHEMA.eventType, Literal(canonical_kind)))
        self.graph.add((event_uri, PROV.generatedAtTime, self._literal(bucket_dt)))

        if subject_uri is not None:
            self.graph.add((event_uri, SCHEMA.about, subject_uri))
        if experiment_uri is not None:
            self.graph.add((event_uri, SCHEMA.isPartOf, experiment_uri))
        if canonical_modality:
            self.graph.add((event_uri, SCHEMA.measurementTechnique, Literal(canonical_modality)))
        if canonical_text:
            self.graph.add((event_uri, SCHEMA.description, Literal(canonical_text, lang=self.default_language)))

        for event_type in self._iter_terms(event_types):
            self.graph.add((event_uri, RDF.type, event_type))

    def get_shared_event_uri(
        self,
        *,
        event_kind: str,
        observed_at: datetime,
        subject: RDFTermLike | None = None,
        text: str | None = None,
        modality: str | None = None,
        experiment: RDFTermLike | None = None,
        shared_event_namespace: str | None = None,
        event_types: Sequence[RDFTermLike] | None = None,
        event_id: str | None = None,
        time_bucket_seconds: int | None = None,
        resolver: SharedEventResolver | None = None,
        policy: SharedEventPolicy | None = None,
    ) -> URIRef:
        """Gets a shared-event URI via external resolver or deterministic local fallback.

        This is the high-level API for production integration:
        - if a resolver is configured (argument or logger default), it is tried first,
        - if resolver is missing or returns None, local deterministic resolution is used.
        """
        effective_policy = policy if policy is not None else self.shared_event_policy
        effective_namespace = (
            shared_event_namespace
            if shared_event_namespace is not None
            else effective_policy.namespace
        )
        effective_bucket = (
            time_bucket_seconds
            if time_bucket_seconds is not None
            else effective_policy.time_bucket_seconds
        )
        event_types_tuple = tuple(event_types) if event_types is not None else ()
        resolver_request = SharedEventRequest(
            event_kind=event_kind,
            observed_at=observed_at,
            subject=subject,
            text=text,
            modality=modality,
            experiment=experiment,
            shared_event_namespace=effective_namespace,
            event_types=event_types_tuple,
            event_id=event_id,
            time_bucket_seconds=effective_bucket,
        )
        resolver_fn = resolver if resolver is not None else self.shared_event_resolver

        subject_uri = self.resolve_term(subject) if subject is not None else None
        experiment_uri = self.resolve_term(experiment) if experiment is not None else self.default_experiment_uri
        if resolver_fn is not None:
            resolved_event = resolver_fn(resolver_request)
            if resolved_event is not None:
                event_uri = self.resolve_term(resolved_event)
                if effective_namespace:
                    shared_ns = Namespace(self._normalize_base_namespace(effective_namespace))
                    self.graph.bind("shared-event", shared_ns)
                self._add_shared_event_metadata(
                    event_uri=event_uri,
                    event_kind=event_kind,
                    observed_at=observed_at,
                    subject_uri=subject_uri,
                    text=text,
                    modality=modality,
                    experiment_uri=experiment_uri,
                    event_types=event_types_tuple,
                    time_bucket_seconds=effective_bucket,
                    event_key=self._slugify(event_id) if event_id else None,
                )
                return event_uri

        return self.resolve_shared_event(
            event_kind=event_kind,
            observed_at=observed_at,
            subject=subject_uri,
            text=text,
            modality=modality,
            experiment=experiment_uri,
            shared_event_namespace=effective_namespace,
            event_types=event_types_tuple,
            event_id=event_id,
            time_bucket_seconds=effective_bucket,
        )

    def resolve_shared_event(
        self,
        *,
        event_kind: str,
        observed_at: datetime,
        subject: RDFTermLike | None = None,
        text: str | None = None,
        modality: str | None = None,
        experiment: RDFTermLike | None = None,
        shared_event_namespace: str | None = None,
        event_types: Sequence[RDFTermLike] | None = None,
        event_id: str | None = None,
        time_bucket_seconds: int = 1,
    ) -> URIRef:
        """Returns a canonical SharedEvent URI and registers it as an RDF node.

        SharedEvent pattern:
        - one global event URI represents the "same real-world event",
        - each robot may attach its local observation as a specialization.
        """
        if not isinstance(event_kind, str) or not event_kind.strip():
            raise ValueError("Parameter 'event_kind' must be a non-empty string.")
        if not isinstance(observed_at, datetime):
            raise TypeError("Parameter 'observed_at' must be a datetime.")

        namespace_text = self._normalize_base_namespace(
            shared_event_namespace or self.DEFAULT_SHARED_EVENT_NAMESPACE
        )
        shared_ns = Namespace(namespace_text)

        subject_uri = self.resolve_term(subject) if subject is not None else None
        experiment_uri = self.resolve_term(experiment) if experiment is not None else self.default_experiment_uri
        bucket_dt = self._bucket_datetime_seconds(observed_at, bucket_seconds=time_bucket_seconds)
        canonical_text = self._canonicalize_text(text)
        canonical_modality = self._canonicalize_text(modality)
        canonical_kind = self._canonicalize_text(event_kind)

        if event_id is None:
            fingerprint_source = "|".join(
                (
                    canonical_kind,
                    bucket_dt.isoformat(),
                    str(subject_uri) if subject_uri is not None else "",
                    canonical_modality,
                    canonical_text,
                    str(experiment_uri) if experiment_uri is not None else "",
                )
            )
            digest = hashlib.sha256(fingerprint_source.encode("utf-8")).hexdigest()[:20]
            event_key = f"{self._slugify(event_kind)}_{digest}"
        else:
            event_key = self._slugify(event_id)

        event_uri = shared_ns[event_key]
        self.graph.bind("shared-event", shared_ns)
        self._add_shared_event_metadata(
            event_uri=event_uri,
            event_kind=canonical_kind,
            observed_at=bucket_dt,
            subject_uri=subject_uri,
            text=canonical_text,
            modality=canonical_modality,
            experiment_uri=experiment_uri,
            event_types=event_types,
            time_bucket_seconds=time_bucket_seconds,
            event_key=event_key,
        )

        return event_uri

    def link_observation_to_shared_event(
        self,
        observation_entity: RDFTermLike,
        shared_event: RDFTermLike,
        *,
        confidence: float | None = None,
    ) -> None:
        """Links one local observation entity to a canonical shared event."""
        observation_uri = self.resolve_term(observation_entity)
        shared_event_uri = self.resolve_term(shared_event)
        self.graph.add((observation_uri, PROV.specializationOf, shared_event_uri))
        self.graph.add((shared_event_uri, RDF.type, PROV.Entity))
        self.graph.add((shared_event_uri, RDF.type, SEGB.Trigger))
        if confidence is not None:
            self.graph.add((observation_uri, SCHEMA.confidence, self._literal(float(confidence))))

    def end_experiment(
        self,
        *,
        experiment_uri: RDFTermLike | None = None,
        ended_at: datetime | None = None,
    ) -> URIRef:
        """Ends an experiment by adding prov:endedAtTime."""
        uri = self.resolve_term(experiment_uri) if experiment_uri else self.default_experiment_uri
        if uri is None:
            raise ValueError("No experiment URI was provided and no default experiment exists.")
        self.graph.add((uri, PROV.endedAtTime, self._literal(ended_at or datetime.now(tz=timezone.utc))))
        return uri

    def register_ml_model(
        self,
        model_id: str,
        *,
        label: str | None = None,
        version: str | None = None,
        provider: RDFTermLike | str | None = None,
        endpoint: str | None = None,
        comment: str | None = None,
        characteristics: Mapping[str, Any] | None = None,
    ) -> URIRef:
        """Registers a machine learning model with optional metadata."""
        model_uri = self.resource_uri("model", model_id)
        self.graph.add((model_uri, RDF.type, MLS.Model))
        self.graph.add((model_uri, RDF.type, PROV.Entity))
        self.graph.add((model_uri, RDF.type, SEGB.Result))
        if label:
            self.graph.add((model_uri, RDFS.label, Literal(label, lang=self.default_language)))
        if version:
            self.graph.add((model_uri, SCHEMA.version, Literal(version)))
        if provider:
            if isinstance(provider, URIRef):
                self.graph.add((model_uri, SCHEMA.provider, provider))
            elif isinstance(provider, str) and provider.startswith(("http://", "https://")):
                self.graph.add((model_uri, SCHEMA.provider, URIRef(provider)))
            else:
                self.graph.add((model_uri, SCHEMA.provider, Literal(str(provider))))
        if endpoint:
            if endpoint.startswith(("http://", "https://")):
                self.graph.add((model_uri, SCHEMA.url, URIRef(endpoint)))
            else:
                self.graph.add((model_uri, SCHEMA.url, Literal(endpoint)))
        if comment:
            self.graph.add((model_uri, RDFS.comment, Literal(comment, lang=self.default_language)))

        for name, value in (characteristics or {}).items():
            characteristic_uri = self.resource_uri(
                "model-characteristic",
                f"{model_id}_{name}",
            )
            self.graph.add((characteristic_uri, RDF.type, MLS.ModelCharacteristic))
            self.graph.add((characteristic_uri, RDFS.label, Literal(name, lang="en")))
            self.graph.add((characteristic_uri, MLS.hasValue, self._literal(value)))
            self.graph.add((model_uri, MLS.hasQuality, characteristic_uri))
        return model_uri

    def _ensure_activity(self, activity_uri: URIRef, activity_types: Sequence[RDFTermLike] | None = None) -> None:
        self.graph.add((activity_uri, RDF.type, SEGB.LoggedActivity))
        for activity_type in self._iter_terms(activity_types):
            self.graph.add((activity_uri, RDF.type, activity_type))

    def _link_model_usage(self, activity_uri: URIRef, usage: ModelUsage) -> None:
        model_uri = self.resolve_term(usage.model)
        self.graph.add((model_uri, RDF.type, MLS.Model))
        self.graph.add((activity_uri, SEGB.usedMLModel, model_uri))

        implementation_uri: URIRef | None = None
        requires_implementation = usage.implementation is not None or bool(usage.parameters) or bool(
            usage.software_label or usage.software_version
        )
        if requires_implementation:
            implementation_uri = (
                self.resolve_term(usage.implementation)
                if usage.implementation is not None
                else self.resource_uri("implementation")
            )
            self.graph.add((implementation_uri, RDF.type, MLS.Implementation))
            self.graph.add((implementation_uri, MLS.implements, model_uri))
            self.graph.add((activity_uri, MLS.executes, implementation_uri))

        if usage.software_label or usage.software_version:
            software_uri = self.resource_uri("software", usage.software_label)
            self.graph.add((software_uri, RDF.type, MLS.Software))
            if usage.software_label:
                self.graph.add((software_uri, RDFS.label, Literal(usage.software_label)))
            if usage.software_version:
                self.graph.add((software_uri, SCHEMA.version, Literal(usage.software_version)))
            if implementation_uri is not None:
                self.graph.add((software_uri, MLS.hasPart, implementation_uri))

        for key, value in usage.parameters.items():
            hyperparameter_uri = self.resource_uri("hyperparameter", key)
            setting_uri = self.resource_uri("hyperparameter-setting")

            self.graph.add((hyperparameter_uri, RDF.type, MLS.HyperParameter))
            self.graph.add((hyperparameter_uri, RDFS.label, Literal(str(key), lang="en")))

            self.graph.add((setting_uri, RDF.type, MLS.HyperParameterSetting))
            self.graph.add((setting_uri, MLS.specifiedBy, hyperparameter_uri))
            self.graph.add((setting_uri, MLS.hasValue, self._literal(value)))

            self.graph.add((activity_uri, MLS.hasInput, setting_uri))
            self.graph.add((activity_uri, PROV.used, setting_uri))
            if implementation_uri is not None:
                self.graph.add((implementation_uri, MLS.hasHyperParameter, hyperparameter_uri))

    def log_activity(
        self,
        *,
        activity_id: str | None = None,
        activity_types: Sequence[RDFTermLike] | None = None,
        label: str | None = None,
        experiment: RDFTermLike | None = None,
        performer: RDFTermLike | None = None,
        started_at: datetime | None = None,
        ended_at: datetime | None = None,
        triggered_by_activity: RDFTermLike | None = None,
        triggered_by_entity: RDFTermLike | None = None,
        triggered_by_entities: Sequence[RDFTermLike] | None = None,
        intermediate_activities: Sequence[RDFTermLike] | None = None,
        used_entities: Sequence[RDFTermLike] | None = None,
        used_models: Sequence[RDFTermLike] | None = None,
        model_usages: Sequence[ModelUsage] | None = None,
        produced_entity_results: Sequence[RDFTermLike] | None = None,
        produced_activity_results: Sequence[RDFTermLike] | None = None,
    ) -> URIRef:
        """Logs one activity and its semantic relations.

        Data provenance expected from the caller:
        - `started_at` / `ended_at`: system clock timestamps when the action/event starts/ends.
        - `triggered_by_activity`: single upstream action trigger.
        - `triggered_by_entity`: preferred single upstream entity trigger (message, detection, file).
        - `triggered_by_entities`: optional additional entity triggers.
        - `used_entities`: concrete inputs consumed by the action.
        - `used_models` / `model_usages`: model identifiers and runtime config known by the
          component that executed inference/decision.
        - `produced_*_results`: outputs emitted by the action.

        This method records those relations explicitly; it does not infer causal links.
        """
        activity_uri = self.resource_uri("activity", activity_id)
        self._ensure_activity(activity_uri, activity_types)

        if label:
            self.graph.add((activity_uri, RDFS.label, Literal(label, lang=self.default_language)))

        exp_uri = self.resolve_term(experiment) if experiment else self.default_experiment_uri
        if exp_uri:
            self.graph.add((activity_uri, AMOR_EXP.isRelatedWithExperiment, exp_uri))

        performer_uri = self.resolve_term(performer) if performer else self.robot_uri
        self.graph.add((activity_uri, SEGB.wasPerformedBy, performer_uri))

        if started_at:
            self.graph.add((activity_uri, PROV.startedAtTime, self._literal(started_at)))
        if ended_at:
            self.graph.add((activity_uri, PROV.endedAtTime, self._literal(ended_at)))

        if triggered_by_activity is not None:
            trigger_uri = self.resolve_term(triggered_by_activity)
            self.graph.add((activity_uri, SEGB.triggeredByActivity, trigger_uri))
            self.graph.add((activity_uri, PROV.wasInfluencedBy, trigger_uri))

        entity_triggers: list[URIRef] = []
        if triggered_by_entity is not None:
            entity_triggers.append(self.resolve_term(triggered_by_entity))
        entity_triggers.extend(self._iter_terms(triggered_by_entities))

        # Causal links from entities (messages, objects, files, detection outputs, etc.).
        for trigger_uri in entity_triggers:
            self.graph.add((activity_uri, SEGB.triggeredByEntity, trigger_uri))
            self.graph.add((activity_uri, PROV.wasInfluencedBy, trigger_uri))
        # Optional decomposition: this activity has internal intermediate steps.
        for intermediate_uri in self._iter_terms(intermediate_activities):
            self.graph.add((activity_uri, SEGB.intermediateActivity, intermediate_uri))
            self.graph.add((activity_uri, PROV.wasInfluencedBy, intermediate_uri))

        # Input entities consumed by the activity.
        for entity_uri in self._iter_terms(used_entities):
            self.graph.add((activity_uri, PROV.used, entity_uri))

        for model_uri in self._iter_terms(used_models):
            self.graph.add((activity_uri, SEGB.usedMLModel, model_uri))
            self.graph.add((model_uri, RDF.type, MLS.Model))

        # Model execution metadata (hyperparameters, software runtime, etc.).
        for usage in model_usages or ():
            self._link_model_usage(activity_uri, usage)

        # Entity outputs directly generated by the activity.
        for result_uri in self._iter_terms(produced_entity_results):
            self.graph.add((activity_uri, SEGB.producedEntityResult, result_uri))
            self.graph.add((activity_uri, PROV.generated, result_uri))

        for result_uri in self._iter_terms(produced_activity_results):
            self.graph.add((activity_uri, SEGB.producedActivityResult, result_uri))

        return activity_uri

    def link_triggered_activity(
        self,
        activity: RDFTermLike,
        trigger_activity: RDFTermLike,
    ) -> None:
        """Adds a causal link where one activity is triggered by another activity."""
        activity_uri = self.resolve_term(activity)
        trigger_uri = self.resolve_term(trigger_activity)
        self.graph.add((activity_uri, SEGB.triggeredByActivity, trigger_uri))
        self.graph.add((activity_uri, PROV.wasInfluencedBy, trigger_uri))

    def link_triggered_entity(
        self,
        activity: RDFTermLike,
        trigger_entity: RDFTermLike,
    ) -> None:
        """Adds a causal link where an entity triggers an activity."""
        activity_uri = self.resolve_term(activity)
        trigger_uri = self.resolve_term(trigger_entity)
        self.graph.add((activity_uri, SEGB.triggeredByEntity, trigger_uri))
        self.graph.add((activity_uri, PROV.wasInfluencedBy, trigger_uri))

    def link_intermediate_activity(
        self,
        activity: RDFTermLike,
        intermediate_activity: RDFTermLike,
    ) -> None:
        """Links an activity to one of its intermediate steps."""
        activity_uri = self.resolve_term(activity)
        intermediate_uri = self.resolve_term(intermediate_activity)
        self.graph.add((activity_uri, SEGB.intermediateActivity, intermediate_uri))
        self.graph.add((activity_uri, PROV.wasInfluencedBy, intermediate_uri))

    def link_influence(
        self,
        activity: RDFTermLike,
        influencer: RDFTermLike,
    ) -> None:
        """Adds an explicit prov:wasInfluencedBy relation."""
        self.graph.add((self.resolve_term(activity), PROV.wasInfluencedBy, self.resolve_term(influencer)))

    def link_entity_result(
        self,
        activity: RDFTermLike,
        entity_result: RDFTermLike,
    ) -> None:
        """Links an activity with an entity result and prov:generated."""
        activity_uri = self.resolve_term(activity)
        entity_uri = self.resolve_term(entity_result)
        self.graph.add((activity_uri, SEGB.producedEntityResult, entity_uri))
        self.graph.add((activity_uri, PROV.generated, entity_uri))

    def log_message(
        self,
        text: str,
        *,
        message_id: str | None = None,
        language: str | None = None,
        message_types: Sequence[RDFTermLike] | None = None,
        generated_by_activity: RDFTermLike | None = None,
        previous_message: RDFTermLike | None = None,
    ) -> URIRef:
        """Logs a message entity and optional conversational relations.

        Typical source of this data:
        - ASR module output (user speech transcribed to text).
        - LLM/NLG module output (robot response text).
        - Coordination/handover channel between robots.
        """
        message_uri = self.resource_uri("message", message_id)
        self.graph.add((message_uri, RDF.type, ORO.Message))
        self.graph.add((message_uri, RDF.type, PROV.Entity))
        for message_type in self._iter_terms(message_types):
            self.graph.add((message_uri, RDF.type, message_type))
        literal_language = language or self.default_language
        self.graph.add((message_uri, ORO.hasText, Literal(text, lang=literal_language)))

        if generated_by_activity:
            activity_uri = self.resolve_term(generated_by_activity)
            self.graph.add((message_uri, PROV.wasGeneratedBy, activity_uri))
            self.graph.add((activity_uri, SEGB.producedEntityResult, message_uri))

        if previous_message:
            previous_uri = self.resolve_term(previous_message)
            self.graph.add((message_uri, ORO.previousMessage, previous_uri))
            self.graph.add((previous_uri, ORO.nextMessage, message_uri))
        return message_uri

    def log_emotion_annotation(
        self,
        *,
        source_activity: RDFTermLike,
        targets: Sequence[RDFTermLike],
        emotions: Sequence[EmotionScore],
        annotation_id: str | None = None,
        emotion_model: RDFTermLike = EMOML.big6,
    ) -> URIRef:
        """Logs emotion analysis results using ONYX and EmotionML categories.

        Expected upstream component:
        - an emotion recognizer that already produced categories + intensity/confidence.
        """
        if not emotions:
            raise ValueError("Parameter 'emotions' cannot be empty.")

        source_activity_uri = self.resolve_term(source_activity)
        self.graph.add((source_activity_uri, RDF.type, SEGB.LoggedActivity))
        self.graph.add((source_activity_uri, RDF.type, ONYX.EmotionAnalysis))
        self.graph.add((source_activity_uri, ONYX.usesEmotionModel, self.resolve_term(emotion_model)))

        annotation_uri = self.resource_uri("emotion-annotation", annotation_id)
        self.graph.add((annotation_uri, RDF.type, AMOR.EmotionAnnotation))
        self.graph.add((annotation_uri, RDF.type, PROV.Entity))
        self.graph.add((annotation_uri, RDF.type, SEGB.Result))
        self.graph.add((source_activity_uri, PROV.generated, annotation_uri))
        self.graph.add((source_activity_uri, SEGB.producedEntityResult, annotation_uri))

        for target in self._iter_terms(targets):
            self.graph.add((annotation_uri, OA.hasTarget, target))

        for emotion in emotions:
            emotion_uri = self.resource_uri("emotion")
            self.graph.add((emotion_uri, RDF.type, ONYX.Emotion))
            self.graph.add((emotion_uri, ONYX.hasEmotionCategory, self.resolve_term(emotion.category)))
            self.graph.add((emotion_uri, ONYX.hasEmotionIntensity, self._literal(float(emotion.intensity))))
            if emotion.confidence is not None:
                self.graph.add((emotion_uri, ONYX.algorithmConfidence, self._literal(float(emotion.confidence))))
            self.graph.add((annotation_uri, ONYX.hasEmotion, emotion_uri))

        return annotation_uri

    def _add_state_property(
        self,
        *,
        state_uri: URIRef,
        property_id: str,
        value: Any,
        unit_code: str | None = None,
    ) -> URIRef:
        property_uri = self.resource_uri("state-property", f"{property_id}_{uuid.uuid4().hex}")
        self.graph.add((property_uri, RDF.type, SCHEMA.PropertyValue))
        self.graph.add((property_uri, SCHEMA.propertyID, Literal(property_id)))
        self.graph.add((property_uri, SCHEMA.value, self._literal(value)))
        if unit_code:
            self.graph.add((property_uri, SCHEMA.unitCode, Literal(unit_code)))
        self.graph.add((state_uri, SCHEMA.additionalProperty, property_uri))
        return property_uri

    def log_robot_state(
        self,
        snapshot: RobotStateSnapshot,
        *,
        state_id: str | None = None,
        source_activity: RDFTermLike | None = None,
    ) -> URIRef:
        """
        Logs one robot state snapshot as an RDF entity.
        Snapshot values are represented with schema:PropertyValue nodes.

        Expected upstream component:
        - telemetry/state estimator node (battery, CPU, memory, network, location, mode).
        This method only records that snapshot; it does not query hardware by itself.
        """
        state_uri = self.resource_uri("state", state_id)
        self.graph.add((state_uri, RDF.type, PROV.Entity))
        self.graph.add((state_uri, RDF.type, SEGB.Result))
        self.graph.add((state_uri, PROV.wasAttributedTo, self.robot_uri))
        self.graph.add((state_uri, PROV.generatedAtTime, self._literal(snapshot.timestamp or datetime.now(timezone.utc))))

        if source_activity:
            source_uri = self.resolve_term(source_activity)
            self.graph.add((source_uri, PROV.generated, state_uri))
            self.graph.add((source_uri, SEGB.producedEntityResult, state_uri))

        if snapshot.location:
            location_value = snapshot.location
            if isinstance(location_value, URIRef):
                self.graph.add((state_uri, SCHEMA.location, location_value))
            elif isinstance(location_value, str) and location_value.startswith(("http://", "https://")):
                self.graph.add((state_uri, SCHEMA.location, URIRef(location_value)))
            else:
                self.graph.add((state_uri, SCHEMA.location, self.resolve_term(location_value)))

        if snapshot.note:
            self.graph.add((state_uri, RDFS.comment, Literal(snapshot.note, lang=self.default_language)))

        if snapshot.battery_level is not None:
            self._add_state_property(
                state_uri=state_uri,
                property_id="battery_level",
                value=float(snapshot.battery_level),
                unit_code="PERCENT",
            )
        if snapshot.autonomy_mode is not None:
            self._add_state_property(
                state_uri=state_uri,
                property_id="autonomy_mode",
                value=snapshot.autonomy_mode,
            )
        if snapshot.mission_phase is not None:
            self._add_state_property(
                state_uri=state_uri,
                property_id="mission_phase",
                value=snapshot.mission_phase,
            )
        if snapshot.cpu_load is not None:
            self._add_state_property(
                state_uri=state_uri,
                property_id="cpu_load",
                value=float(snapshot.cpu_load),
                unit_code="PERCENT",
            )
        if snapshot.memory_load is not None:
            self._add_state_property(
                state_uri=state_uri,
                property_id="memory_load",
                value=float(snapshot.memory_load),
                unit_code="PERCENT",
            )
        if snapshot.network_status is not None:
            self._add_state_property(
                state_uri=state_uri,
                property_id="network_status",
                value=snapshot.network_status,
            )

        for custom_key, custom_value in snapshot.custom.items():
            self._add_state_property(
                state_uri=state_uri,
                property_id=str(custom_key),
                value=custom_value,
            )

        return state_uri

    def merge_turtle(self, ttl_content: str) -> None:
        """Merges existing turtle content into the logger graph."""
        if not isinstance(ttl_content, str) or not ttl_content.strip():
            raise ValueError("Parameter 'ttl_content' must be a non-empty string.")
        self.graph.parse(data=ttl_content, format="turtle")

    def serialize(self, *, format: str = "turtle") -> str:
        data = self.graph.serialize(format=format)
        return data.decode("utf-8") if isinstance(data, bytes) else data

    def publish(self, publisher: Any, *, user: str | None = None) -> dict[str, Any]:
        """
        Publishes the current graph through a publisher object.
        The publisher must expose publish_graph(graph, user=None).
        """
        return publisher.publish_graph(self.graph, user=user)
