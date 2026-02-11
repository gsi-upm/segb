# Shared Context Resolution

This document explains exactly how `SharedContext` works in the SEGB backend.

## Goal

The resolver links **independent robot observations** to one canonical external event without robot-to-robot communication.

- Robots do not talk to each other.
- Each robot sends its own local observation to the backend.
- The backend decides whether observations belong to the same external event.

## Components

- Resolver implementation: `backend/combined/utils/shared_context.py`
- Resolve API endpoint: `POST /shared-context/resolve`
- Reconciliation endpoint: `POST /shared-context/reconcile`
- Stats endpoint: `GET /shared-context/stats`

Naming note:
- Backend API uses the term `shared_context`.
- Logger methods use the term `shared_event`.
- In this prototype they refer to the same canonical cross-robot event node.

## Request Contract

`POST /shared-context/resolve`

```json
{
  "event_kind": "human_utterance",
  "observed_at": "2026-02-11T09:12:13.150Z",
  "experiment_uri": "https://.../experiment/exp_001",
  "subject_uri": "https://.../human/maria",
  "modality": "speech",
  "text": "Could you show me climate news?",
  "observation_uri": "https://.../message/user_msg_1",
  "robot_uri": "https://.../robot/ari1",
  "time_window_seconds": 3.0
}
```

Only `event_kind` and `observed_at` are mandatory.

`observation_uri` and `robot_uri` are accepted for traceability, but the current resolver version does not use them for scoring.

## Resolution Pipeline

### 1. Normalize input

The resolver normalizes:

- `event_kind`, `subject_uri`, `experiment_uri`, `modality` to lowercase/trimmed strings
- `text` to lowercase, compact spaces, punctuation removed
- `observed_at` to UTC

### 2. Candidate retrieval

A context is considered a candidate only if:

- `event_kind` matches exactly
- time difference is within `time_window_seconds * candidate_window_multiplier`
- if strict subject check is enabled and both subjects exist, they must match
- if strict experiment check is enabled and both experiment URIs exist, they must match

### 3. Candidate scoring

For each candidate, score components are computed:

- `S_time`: linear decay by temporal distance
- `S_text`: lexical similarity (`Jaccard(tokens)` + `SequenceMatcher`) when text exists
- `S_subject`: 1.0 same subject, 0.0 different, 0.5 unknown
- `S_modality`: 1.0 same modality, 0.0 different, 0.5 unknown
- `S_context`: 1.0 same experiment, 0.0 different, 0.5 unknown

Weighted score:

```text
S = w_time*S_time + w_text*S_text + w_subject*S_subject + w_modality*S_modality + w_context*S_context
```

If text is missing, weights are renormalized over available components.

### 4. Decision (exact order)

Given best candidate score `S_best` and optional second score `S_second`:

1. Return `matched` if:
   - `S_best >= match_threshold`
   - and either there is no second candidate or `(S_best - S_second) >= close_score_margin`
2. Else return `ambiguous` if:
   - `S_best >= ambiguous_threshold`
3. Else return `created`

### 5. State updates

- `matched`: existing context observation count is incremented
- `ambiguous`: new context created with status `ambiguous`
- `created`: new context created with status `active`

## Response Contract

```json
{
  "shared_context_uri": "https://gsi.upm.es/segb/shared-context/human_utterance_abcd1234",
  "status": "matched",
  "confidence": 0.91,
  "resolver_version": "shared-context-v1-rules",
  "candidate_count": 3,
  "matched_candidate_uri": "https://...",
  "close_candidates": [],
  "score_breakdown": {
    "time": 0.96,
    "text": 0.93,
    "subject": 1.0,
    "modality": 1.0,
    "context": 1.0
  }
}
```

## Reconciliation Flow

`POST /shared-context/reconcile` scans ambiguous contexts and tries to merge them into active contexts.

A merge happens only if:

- best candidate score is above `match_threshold`
- best-vs-second margin is at least `close_score_margin`

When merged, an alias mapping is recorded:

- `ambiguous_uri -> canonical_active_uri`

## Determinism and Auditability

The resolver is fully rule-based and deterministic for a fixed policy.

Key audit fields:

- `resolver_version`
- `confidence`
- `score_breakdown`
- `status`

## Configuration

Policy can be tuned through environment variables:

- `SHARED_CONTEXT_NAMESPACE`
- `SHARED_CONTEXT_TIME_WINDOW_SECONDS`
- `SHARED_CONTEXT_MATCH_THRESHOLD`
- `SHARED_CONTEXT_AMBIGUOUS_THRESHOLD`
- `SHARED_CONTEXT_CLOSE_MARGIN`

## How robots use it

### Three direct answers

- When is SharedContext created?
  - During `POST /shared-context/resolve` when there is no strong existing match.
  - Resolver returns `status=created` (new active context) or `status=ambiguous` (new ambiguous context).

- Who creates the URI?
  - If robot uses backend resolver: backend creates/chooses the canonical URI and returns it.
  - If robot falls back to local mode: robot computes URI locally with deterministic hashing.

- Who inserts SharedContext triples into the KG?
  - Robot logger inserts SharedContext triples into its local RDF graph.
  - Robot publishes that graph with `POST /ttl`.
  - Backend persists those triples into the global KG.

### Endpoint usage by actor

- `POST /shared-context/resolve`
  - Called online by each robot for each relevant observation.
  - Typical caller: `HTTPSharedContextResolver` in `segb_logger/shared_context.py`.
  - Auth role: `logger` or `admin`.
  - Purpose: get one canonical `shared_context_uri` now.

- `POST /shared-context/reconcile`
  - Called by backend operations, not by robots in the hot path.
  - Typical caller: admin endpoint trigger, scheduled job, or maintenance script.
  - Auth role: `admin`.
  - Purpose: merge previously ambiguous contexts into active canonical contexts.

- `GET /shared-context/stats`
  - Called by monitoring/ops dashboards.
  - Auth role: `auditor` or `admin`.
  - Purpose: inspect resolver health and volume (`active`, `ambiguous`, `merged`, `aliases`).

### Robot-side integration flow (online)

1. Robot perceives a local event (for example: user utterance captured by robot microphone).
2. Robot logs/creates its local observation entity in RDF (robot-local fact).
3. Robot asks for canonical context URI via:
   - `SemanticSEGBLogger.get_shared_event_uri(...)`, optionally with `shared_event_resolver=HTTPSharedContextResolver(...)`.
4. Inside `get_shared_event_uri(...)`:
   - Build a normalized request (`event_kind`, `observed_at`, `subject`, `text`, `modality`, `experiment`).
   - If resolver exists, call `POST /shared-context/resolve`.
   - If API returns `shared_context_uri`, use that URI and add local SharedContext metadata triples.
   - If API call fails and `raise_on_error=False`, fallback to local deterministic `resolve_shared_event(...)`.
5. Robot links local observation to canonical event:
   - `link_observation_to_shared_event(observation_entity, shared_event_uri)`
   - This writes `prov:specializationOf` from local observation to shared event node.
6. Robot logs activities triggered by that observation and publishes TTL (`POST /ttl`).
7. Backend stores these triples in the central KG.

### Exact creation/matching flow in resolver

For each `POST /shared-context/resolve` request:

1. Normalize input and collect candidate contexts.
2. Score candidates.
3. Decide:
   - `matched`: no new context URI; existing context reused.
   - `ambiguous`: new context URI created with status `ambiguous`.
   - `created`: new context URI created with status `active`.
4. Return response with:
   - `shared_context_uri`
   - `status`
   - `confidence`
   - `score_breakdown`

Important detail: both `ambiguous` and `created` produce a **new URI**. `matched` reuses an existing URI.

### Cross-robot timeline examples

- Case A: clear match
  1. ARI sends resolve request first -> status `created`, URI `ctx_1`.
  2. TIAGo sends similar request shortly after -> status `matched`, URI `ctx_1`.
  3. Both robots keep independent local logs, linked to same canonical context.

- Case B: uncertain match
  1. ARI sends request -> status `ambiguous`, URI `ctx_a`.
  2. TIAGo sends request with partial mismatch -> status `ambiguous`, URI `ctx_b`.
  3. Later admin runs `POST /shared-context/reconcile`.
  4. Resolver may merge `ctx_b -> ctx_a` (alias mapping) if confidence/margin become sufficient.

### Operational recommendation

- Robots should call only `POST /shared-context/resolve` in normal runtime.
- Reconciliation should run out-of-band (periodic or manual) to keep robot runtime simple.
- If strong global consistency is required, avoid local fallback by setting `raise_on_error=True` in `HTTPSharedContextResolver`.
