# AGENTS.md

Guidance for AI coding agents (Codex, Claude Code and others) working in this repository.

## What this is

Semantic Ethical Glass Box (SEGB): a semantic logging stack for human-robot interaction. Robots or simulators build RDF
logs, the backend stores them in a Virtuoso triple store, and a web UI offers reports, graph views, SPARQL queries and
audit workflows. This is a monorepo (version 1.3.1) that unifies what used to be separate repos.

| Path | Content |
|---|---|
| `apps/backend` | FastAPI API (port 5000) over Virtuoso |
| `apps/frontend/segb-ui` | Vue 3 + Vite + Pinia UI (TypeScript, Vitest) |
| `packages/semantic_log_generator` | Reusable Python package to build and publish semantic logs (own `pyproject.toml`, `uv.lock`) |
| `examples/simulations` | Demo use cases (`run_use_case_0N_*.py`), plus `examples/notebooks` and `examples/mocks` |
| `eval/` | Benchmark and capture scripts (`segb_bench`) |
| `ontology/` | SEGB OWL ontology and examples |
| `docs/` | MkDocs site (`mkdocs.yml`, published to ReadTheDocs). `docs/backup/` is an archived old layout, do not edit |
| `tests/` | Only cross-project suites (`test_naming.py`). Project tests live next to their project |

## Commands

Python is `>=3.11,<3.13` (backend image uses 3.12), managed with `uv` (`pyproject.toml` + `uv.lock` at the root).

```bash
uv sync                                                  # root env
cp .env.example .env                                     # then set VIRTUOSO_PASSWORD and VIRTUOSO_READER_PASSWORD
docker compose -f docker-compose.yaml up -d              # production-like stack (pulls GHCR images)
docker compose -f docker-compose.dev.yml up -d --build   # dev stack, backend with --reload
```

Ruff (line length 120) and mypy are configured in `pyproject.toml` but are not declared as dependencies; install them with `uvx ruff check .` / `uvx mypy .` if needed.

### Tests

Code is imported via `PYTHONPATH`, not installed. Use `unittest discover` (pytest also works: `pytest` uses the `testpaths` in `pyproject.toml`).

```bash
PYTHONPATH=apps/backend/src:packages/semantic_log_generator/src \
  python -m unittest discover -s apps/backend/tests/unit -p 'test_*.py'
PYTHONPATH=packages/semantic_log_generator/src:apps/backend/src \
  python -m unittest discover -s packages/semantic_log_generator/tests/unit -p 'test_*.py'
PYTHONPATH=packages/semantic_log_generator/src:apps/backend/src \
  python -m unittest discover -s examples/simulations/tests/integration -p 'test_*.py'
cd apps/frontend/segb-ui && npm run test:run             # frontend; also `npm run type-check`, `npm run build`
```

Backend integration tests that need a real Virtuoso are skipped unless `SEGB_INTEGRATION=1` (needs a working `docker`
CLI; pulls a digest-pinned Virtuoso image). Never replace database privilege tests with mocks. Details in `tests/README.md`.

### Docs

`mkdocs` builds from `mkdocs.yml` (deps in `docs/requirements.txt`). Ontology HTML via Widoco: `./generate_widoco_documentation.sh` and `./generate_examples_widoco_documentation.sh`.

## Backend architecture (`apps/backend/src`)

Entry point `main.py`; layers (see `apps/backend/README.md` for the full endpoint table):

- `api/` — FastAPI app, `routers/`, `deps.py` (auth dependencies), `schemas.py`
- `services/` — use cases (`LogService`, `SharedContextService`, `SystemLogService`), `ttl_validation.py`, `ports.py`
- `models/` — Virtuoso adapters (`virtuoso_model.py`, `virtuoso_graph_store.py`)
- `core/` — `settings.py`, `security.py`, `logging.py`
- `utils/` — shared-context engine, audit, prefix and query-scope helpers
- `tools/generate_jwt.py` — CLI to create JWTs

Key behaviour:

- `POST /ttl` inserts Turtle. Send small logs per event; large uploads hit Virtuoso SPARQL compiler limits. Legacy routes (`/log`, ...) are documented in `docs/reference/legacy-api.md`.
- `GET /query` is read-only SPARQL. It runs on a **second Virtuoso session** with a dedicated reader account (`VIRTUOSO_READER_USER`) that only has `SPARQL_SELECT` plus read on the events graph. A lexical filter and dataset pin stay in front of it. Never retry a user query with the writer account, and never widen the reader's privileges.
- The reader's SQL privileges are checked against `apps/backend/virtuoso/reader-sql-policy.manifest`. The backend refuses to start on drift. Updating the Virtuoso image means regenerating and reviewing that manifest (`docs/operations/centralized-deployment.md`).
- Graphs: events in `VIRTUOSO_GRAPH_URI` (default `http://segb/events`), audit trail in `VIRTUOSO_AUDIT_GRAPH_URI` (default `http://segb/audit`).
- Shared context: `/shared-context/*` resolves canonical URIs, with admin review of ambiguous matches.

## Auth

`SECRET_KEY` empty or unset: auth disabled, every request has all roles (local demos only). Set: HS256 JWT required, roles `logger`, `auditor`, `admin` enforced per route. Generate tokens with `apps/backend/src/tools/generate_jwt.py`; see `docs/operations/authentication-and-jwt.md`.

Never commit `.env`, `*.env` (gitignored), `SECRET_KEY` or real tokens, and never print them in output.

## Conventions

- Keep versions in sync on release: `pyproject.toml`, `apps/frontend/segb-ui/package.json`, `.env.example` (`VERSION`), `CHANGELOG.md`.
- Work goes through PRs into `main`.
- Docs are part of the change: update `docs/` and `CHANGELOG.md` when behaviour, env vars or endpoints change.
