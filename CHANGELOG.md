# Changelog

## 1.3.1 - 2026-11-02

Maintenance release on top of 1.3.0: frontend development-dependency security fixes, a fix for the `segb-ui` container
healthcheck, agent guidance for the repository and a dependency review note. There are no backend application-code or
API changes and no new or changed runtime configuration (environment variables, Virtuoso settings; the only Compose
change is the `segb-ui` healthcheck command); the backend behaves as in 1.3.0 and only announces the new version. The
frontend dependency configuration (`overrides`, one pinned test utility) did change.

### Security

- The `segb-ui` lockfile no longer contains the two advisories `npm audit` reported against development dependencies:
  `glob` is pinned to 14.0.2 ([GHSA-3g3m-2fjr-6pw4](https://github.com/advisories/GHSA-3g3m-2fjr-6pw4)) and
  `minimatch` to 11.0.1 ([GHSA-g3hv-75wg-m249](https://github.com/advisories/GHSA-g3hv-75wg-m249)) through scoped
  `overrides`. Both packages were reached only through `@vue/test-utils`; `npm audit --omit=dev` already reported zero
  vulnerabilities, so the shipped nginx image was not affected by them. No exploit or production assessment was
  performed (#48).

### Fixed

- The `segb-ui` container is no longer reported `unhealthy` while serving correctly: the healthcheck (in
  `apps/frontend/Dockerfile` and in the `segb-ui` service of `docker-compose.yaml`) now probes `http://127.0.0.1:8080/`
  instead of `http://localhost:8080/`, because `localhost` resolved to `::1` inside the image while nginx listens on
  IPv4 only (#50, #51).

### Changed

- `@vue/test-utils` is pinned to 2.4.6 (it was `^2.4.6`): 2.5.1 pulls `nopt` and `abbrev` versions that need Node 22 or
  newer, while the frontend image builder uses Node 20. The overrides cross dependency ranges declared upstream and
  should be revisited when upstream adopts compatible patched versions (#48).
- Versions are bumped to 1.3.1 in `pyproject.toml`, `uv.lock`, the backend default (`apps/backend/src/core/settings.py`),
  `apps/frontend/segb-ui/package.json` and its lockfile, and the environment file example (`VERSION`).

### Documentation

- `AGENTS.md` (imported by `CLAUDE.md`) describes the repository layout, commands, tests, backend architecture and
  conventions for AI coding agents (#46, #47).
- `docs/dependency-review-2026-10-31.md` records the dependency security review of 1.3.0 (frontend findings, the
  remediation above and the verification performed) (#48).
- The `GET /health` example in `docs/reference/legacy-api.md` shows the current version.

### Upgrading from 1.3.0

- Set `VERSION=1.3.1` in your environment file (or remove the line). Compose passes `VERSION` to the backend
  explicitly, so a file copied from the 1.3.0 example keeps announcing `1.3.0` in `/health` and OpenAPI even when the
  1.3.1 image runs.
- Pull the new images (`SEGB_IMAGE_TAG=1.3.1`, or `latest` once published) and update your copy of
  `docker-compose.yaml` if you keep your own: the `segb-ui` healthcheck fix lives in that file as well as in the image.
  No other action is needed: there are no new or changed environment variables, no Virtuoso changes and no
  reader-policy changes.
- Staying on the 1.3.0 images is safe: the 1.3.1 images differ in the announced version (backend default and
  `package.json`), in the frontend development-dependency lock and in the image healthcheck command (the 1.3.0 UI image
  works but is reported `unhealthy`); the production dependency set is unchanged
  (the production entries of the frontend lockfile and the backend lock, apart from the project's own version, are the
  same as in 1.3.0).

### Known limitations

- Unchanged from 1.3.0: uploads of about 5,000 triples or more in one request can still fail in Virtuoso 7.2.16, native
  SQL with the reader's credentials can read audit rows (keep them inside the backend), and blank nodes are duplicated
  on re-upload.
- `overrides` in the frontend lockfile are a workaround for upstream ranges and need a follow-up when upstream releases
  compatible versions.
- The dependency review covered the frontend npm lock and the exported Python locks on one platform; other platforms
  were not audited.

## 1.3.0 - 2026-10-30

`GET /query` now runs on a read-only Virtuoso account, the Virtuoso SQL port is no longer published by default, and all
open Dependabot alerts are cleared. The backend image moves to Python 3.12. Tags `1.0.1` to `1.2.0` are unchanged.

### Security

- `GET /query` runs on a second Virtuoso session authenticated as a dedicated account (`VIRTUOSO_READER_USER`) that holds
  only `SPARQL_SELECT` and read access to the events graph. Writes, audit reads and deletion keep the existing account.
  The lexical filter and the dataset pin from 1.2.0 stay; the account is the barrier behind them (#27, #35). The
  backend refuses to start without verified reader credentials and never retries a user query with the writer account.
- The SQL privileges the reader can hold are checked against a reviewed manifest
  (`apps/backend/virtuoso/reader-sql-policy.manifest`): provisioning fails on any difference, and the backend rechecks
  the live listing at startup and every `VIRTUOSO_READER_POLICY_RECHECK_SECONDS` (default 30), dropping the reader
  session on drift (#27, #35).
- The Virtuoso image is pinned by digest in both Compose files and in the integration harness, so a moving tag cannot
  change the reader policy; the docs explain how to regenerate and review the manifest when updating the image (#33,
  #38).
- Port 1111 (Virtuoso native SQL) is no longer published to the host by default. It stays reachable on the internal
  Compose network and from inside the container (#32, #39).
- Dependencies updated to clear every open Dependabot alert (155 at the time): fastapi 0.162.0 (starlette 1.x), uvicorn
  0.54.0, pyjwt 2.15.1, requests 2.34.2, PyYAML 6.0.3, python-multipart, anyio, h11, certifi, idna, urllib3, dnspython and
  others in the backend; the `semantic_log_generator` lockfile; and the `segb-ui` lockfile (vitest 4.x) (#42, #43, #44).

### Changed

- The backend image is built on `python:3.12-slim-bookworm` and the backend now requires Python 3.11 or newer
  (`requires-python >=3.11,<3.13`), because the dnspython fix needs it. The `semantic_log_generator` package still
  supports Python 3.10 to 3.12 (#42).
- `.zenodo.json` keeps the creators, the contact person and the community on Zenodo releases (#36, #37).

### Documentation

- Guidance to publish small, per-event logs instead of whole sessions: a single `INSERT DATA` of about 5,000 triples or
  more fails in the pinned Virtuoso 7.2.16, with or without more memory, and the API does not enforce a triple limit
  (#24, #40).
- The residual risk of native SQL access and of the built-in routines the reader can still call is documented, with a
  real-Virtuoso characterization test: the reader can invoke `SPARQL_REXEC_TO_ARRAY` and read what a remote endpoint's
  identity can read. Treat the reader credentials as internal to the backend (#34, #41).

### Upgrading from 1.2.x

- Set `VIRTUOSO_READER_PASSWORD` in `.env` (required, different from `VIRTUOSO_PASSWORD`; `VIRTUOSO_READER_USER` defaults
  to `segb_reader`). The new `segb-query-reader-init` service provisions the account before the backend starts. Setting
  up an external Virtuoso is described in `docs/operations/centralized-deployment.md`.
- If something outside Compose connected to the host port 1111, publish it explicitly or run `isql` from the container.
- Set `VERSION=1.3.0` in your environment file (or remove the line). Compose passes `VERSION` to the backend explicitly,
  so a file copied from the 1.2.0 example keeps announcing `1.2.0` in `/health` and OpenAPI even when the 1.3.0 image
  runs.
- The backend now requires Python 3.11+ when run from source.

### Known limitations

- Uploads of about 5,000 triples or more in one request can still fail in Virtuoso 7.2.16 (#24 documents the guidance
  but does not change the behaviour).
- With the reader's credentials, native SQL can read audit rows; keep them inside the backend. The reader policy is tied
  to the pinned image build and fails closed on a different one until the manifest is reviewed and regenerated.
- Blank nodes are duplicated on re-upload; use URIs.

## 1.2.0 - 2026-10-29

SEGB gets an append-only audit trail, keeps the two 0.4.x routes the robots still call, and drops the `amor-` prefix
from its own names. Tags `1.0.1` to `1.1.1` are unchanged.

### Security

- `GET /query` could run Virtuoso internal functions (`bif:`, `sql:`) with the account the backend uses, so a user with
  the `auditor` role could erase any graph from a read-only query, the events graph included. This affects the released
  1.x versions up to `1.1.1`. Queries are now checked before they run and the dataset is pinned to the events graph
  (#26). A read-only Virtuoso account for `/query` is planned for 1.3.0 (#27).

### Added

- Audit graph `http://segb/audit`. Every `POST /ttl` writes an `Insertion` entry in the same SPARQL update as the
  events, and `POST /ttl/delete_all` stores the removed graph in a `Deletion` entry before clearing; the audit graph is
  never cleared. A dump over 4 MiB is kept in the new `audit_dumps` volume, referenced by file name and SHA-256
  (#9, #10, vocabulary in #8).
- `GET /history` and `GET /log?log_id=` for the `auditor` and `admin` roles, with the 0.4.x keys (#11).
- Deprecated legacy routes `POST /log` and `GET /health`, with `Deprecation` and `Link` headers, and `GET /legacy/usage`
  (admin) to measure how much `POST /log` is still used. See `docs/reference/legacy-api.md` (#13).
- Warning `SEM_BLANK_NODES` in `POST /ttl/validate`: blank nodes are not skolemized, so a re-upload stores them again
  (#14).
- Settings `VIRTUOSO_AUDIT_GRAPH_URI`, `AUDIT_BASE_IRI`, `AUDIT_DUMP_DIR` and `AUDIT_INLINE_TTL_MAX_BYTES`.
- Opt-in integration tests against a disposable Virtuoso (`SEGB_INTEGRATION=1`), documented in `tests/README.md` (#7).

### Changed

- Names without the old `amor-` prefix: services `segb` and `segb-virtuoso`, container `segb-server`, image
  `ghcr.io/gsi-upm/semantic_ethical_glass_box/segb`, default event graph `http://segb/events` (#20).
  **Upgrading from 1.1.x:** the old graph has a different name, so set `VIRTUOSO_GRAPH_URI` to keep reading it; see
  "Upgrading From 1.1.x" in `docs/operations/centralized-deployment.md`.
- `POST /ttl/delete_all` answers with the `log_id` of its audit entry and takes the same lock as inserts.
- `/query` rejects queries that name another graph, use `SERVICE`, call `bif:`/`sql:` or call any function that is not an
  XSD cast, with `422`; an RDF collection right after an IRI is read as a function call and rejected.

### Known limitations

- A single upload above about 5,000 triples fails in Virtuoso 7.2.16 (#24, planned for 1.3.0).
- Blank nodes are duplicated on re-upload; use URIs.
- Until #27 lands, the isolation of `/query` is a text check written for Virtuoso 7.2.16.
