# Backend Architecture

This backend follows a simple Clean Architecture split:

- `combined/core/`: configuration, logging, security
- `combined/services/`: use-case orchestration (`LogService`, `SharedContextService`, lifecycle)
- `combined/models/`: infrastructure adapters (Neo4j, Virtuoso)
- `combined/api/`: HTTP contracts and route handlers
- `combined/utils/`: specialized helpers (prefix handling, shared context engine)

## Request flow

1. HTTP request enters `combined/api/router.py`.
2. Router validates user roles via `combined/core/security.py`.
3. Router delegates use-case logic to `combined/services/*`.
4. Services call infrastructure adapters in `combined/models/*`.
5. Response is returned to API layer.

## Entry point

- ASGI entrypoint: `combined/main.py`
- App factory: `combined/api/app.py`

## Shared Context docs

- Detailed behavior: `backend/docs/shared_context.md`
