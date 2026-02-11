# AMOR-SEGB Monorepo

This repository is organized as a professional multi-component architecture:

- `backend/`: SEGB API service (FastAPI) and backend Docker image.
- `frontend/`: SEGB-UI application (Vue + Nginx) and frontend Docker image.
- `segb_logger/`: Python semantic logging library for robots.
- `examples/`: tutorial and mock integration examples for the logger.
- `ontology/`: SEGB ontology, examples, queries and generated docs.
- `tests/`: automated tests for the logger and examples.

## Runtime layout

- Backend API entrypoint: `backend/combined/main.py`
- Backend image definition: `backend/Dockerfile`
- Frontend UI source: `frontend/segb-ui`
- Frontend image definition: `frontend/Dockerfile`

## Docker Compose

`docker-compose.yaml` wires all services:

- `amor-segb` (backend API)
- `segb-ui` (frontend)
- `amor-segb-neo4j`
- `amor-segb-virtuoso`

Run:

```bash
docker compose up --build
```

## Logger demo

Run the minimal two-robot demo:

```bash
PYTHONPATH=. python -m examples.run_simulation
```
