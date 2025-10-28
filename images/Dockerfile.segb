FROM python:3.12-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:0.6.12 /uv /uvx /bin/

LABEL org.opencontainers.image.source=https://github.com/gsi-upm/amor-segb
LABEL org.opencontainers.image.description="AMOR-SEGB server"
LABEL org.opencontainers.image.authors="Grupo de Sistemas Inteligentes - Universidad Politécnica de Madrid"
LABEL org.opencontainers.image.documentation="https://amor-segb.readthedocs.io/"
LABEL org.opencontainers.image.licenses=MIT

EXPOSE 5000

WORKDIR /app

ADD uv.lock uv.lock
ADD pyproject.toml pyproject.toml

RUN uv sync --frozen

ADD log_conf.yaml log_conf.yaml
ARG PROJECT="segb"
ADD ./api_info/${PROJECT}/api_info.json api_info.json
ADD ./api_info/${PROJECT}/api_description.md api_description.md

RUN mkdir /logs

COPY ./server /app

# CMD ["uv", "run", "fastapi", "run", "utils/combined/main.py", "--port", "5000", "--lifespan on"]
# CMD ["uv", "run", "uvicorn", "--app-dir", "/app/combined", "main:app", "--host", "0.0.0.0", "--port", "5000", "--lifespan", "on"]
CMD ["uv", "run", "uvicorn", "combined.main:app", "--host", "0.0.0.0", "--port", "5000", "--lifespan", "on"]

