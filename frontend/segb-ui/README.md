# SEGB UI (Vue 3)

Production-oriented frontend aligned with the current backend API.

## Goals

- Keep a clean, modular structure (`app`, `core`, `features`, `shared`).
- Prioritize report-oriented analysis views from the notebook.
- Remove historical graph UI paths.
- Keep API integration explicit and typed.

## Project Structure

```text
src/
  app/
    layout/
    router.ts
  core/
    api/
    auth/
    config/
  features/
    reports/
    logs/
    modifications/
    query/
    shared-context/
    health/
    session/
  shared/
    charts/
    rdf/
    ui/
    utils/
```

## Main Routes

- `/reports`: notebook-style analytics dashboard
- `/logs/insert`: insert TTL and inspect KG snapshot
- `/logs/modifications`: audit logs and delete-all admin action
- `/query`: read-only SPARQL workbench
- `/shared-context`: resolver/reconcile/stats console
- `/health`: backend probes
- `/session`: bearer token setup

## Backend Match

The UI maps directly to these backend endpoints:

- `GET /healthz/live`
- `GET /healthz/ready`
- `POST /ttl`
- `GET /events`
- `GET /query`
- `GET /modifications`
- `GET /modifications_date`
- `POST /ttl/delete_all`
- `POST /shared-context/resolve`
- `POST /shared-context/reconcile`
- `GET /shared-context/stats`

## Security Notes

- Token is stored in `sessionStorage` (not persisted across browser restarts).
- Authorization header is attached only when token exists.
- Query workbench blocks non-read-only verbs client-side; backend still enforces policy.
- No HTML injection rendering is used in report/result components.

## Dev

```bash
npm install
npm run dev
```

## Build

```bash
npm run build
```
