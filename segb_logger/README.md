# SEGB Semantic Logger

Production Python library to generate SEGB-compliant RDF logs and publish them to the SEGB backend.

## Scope

- Convert robot runtime facts into RDF triples.
- Keep RDF vocabulary aligned with SEGB, PROV, ORO, ONYX, EmotionML, MLS.
- Provide high-level logging APIs for activities, messages, emotions, robot state and model usage.
- Optionally publish RDF payloads to backend (`POST /ttl`) with `SEGBPublisher`.

## Non-goals

- No direct sensor acquisition.
- No ROS2 transport management.
- No autonomous decision-making.
- No KG querying/inference by itself.

The caller (robot software stack) obtains observations and passes them to this library.

## Public APIs

- `SemanticSEGBLogger`: build RDF logs.
- `SEGBPublisher`: publish logs to backend API.
- `HTTPSharedContextResolver`: request canonical shared-context URI from backend.
- `SharedEventPolicy`, `SharedEventRequest`: control and describe shared-event resolution inputs.

## SharedContext in production

For the "same external event observed by different robots" pattern:

1. Call `get_shared_event_uri(...)`.
2. Link local observation with `link_observation_to_shared_event(...)`.
3. Use that shared URI in triggers (`triggered_by_entity` / `triggered_by_entities`).
4. Publish the graph.

Resolution strategy:

- Preferred: backend resolution via `HTTPSharedContextResolver` (`POST /shared-context/resolve`).
- Fallback: deterministic local URI generation (`resolve_shared_event(...)`) when resolver is not available.

## Minimal production snippet

```python
from datetime import datetime, timezone

from segb_logger import SemanticSEGBLogger

logger = SemanticSEGBLogger(
    base_namespace="https://example.org/segb/robots/r1/",
    robot_id="r1",
    robot_name="Robot-1",
)

exp = logger.start_experiment(
    "exp_001",
    label="Production run",
    started_at=datetime.now(timezone.utc),
)

activity = logger.log_activity(
    activity_id="perception_1",
    activity_types=["oro:ListeningEvent"],
    experiment=exp,
    started_at=datetime.now(timezone.utc),
)

ttl = logger.serialize(format="turtle")
```

## Examples

Tutorials and learning-oriented demos are intentionally kept outside this package in `examples/`.
