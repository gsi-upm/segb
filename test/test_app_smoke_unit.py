"""Smoke/role checks for the real FastAPI app with only database access stubbed.

No Docker, MongoDB, shared test helpers or test.env. Secrets are synthetic.
"""

import contextlib
import importlib.metadata
import os
import sys
import time
from pathlib import Path

import jwt
import pytest
from fastapi.testclient import TestClient


SERVER_DIR = Path(__file__).resolve().parents[1] / "server"
TEST_KEY = "synthetic-http-smoke-test-key-" * 2
OTHER_KEY = "different-http-smoke-test-key-" * 2
HISTORY = [{"log_id": "synthetic-log"}]


def forbid_db(name):
    def stub(*args, **kwargs):
        raise AssertionError(f"unexpected database access: {name}")
    return stub


def in_app_namespace(name):
    return name in ("main", "model", "utils") or name.startswith("utils.")


def fastapi_version():
    return tuple(int(part) for part in importlib.metadata.version("fastapi").split(".")[:3])


@contextlib.contextmanager
def isolated_app():
    """Import server/main.py with DB access stubbed; restore all global state on exit."""
    saved = {name: mod for name, mod in sys.modules.items() if in_app_namespace(name)}
    try:
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("SECRET_KEY", TEST_KEY)
            mp.setenv("DESCRIPTION_FILE_PATH", str(SERVER_DIR / "missing_api_info.json"))
            mp.syspath_prepend(str(SERVER_DIR))
            for name in saved:
                del sys.modules[name]

            import model

            # Stub only DB access: startup connection and every data function; fail loudly
            # if a route reaches an unstubbed one. mongoengine.connect is blocked too.
            mp.setattr(model, "connect_to_db", lambda service: None)
            mp.setattr(model, "connect", forbid_db("mongoengine.connect"))
            for name in ("save_json_ld", "get_raw_graph_from_db", "log_ttl_content", "clear_graph", "get_log_info"):
                mp.setattr(model, name, forbid_db(name))
            mp.setattr(model, "get_logs_list", lambda: HISTORY)

            import main

            yield main
    finally:
        # Drop every app module imported here (stubs and synthetic key live in them),
        # then put back whatever was loaded before.
        for name in [n for n in sys.modules if in_app_namespace(n)]:
            del sys.modules[name]
        sys.modules.update(saved)


@pytest.fixture
def app_module():
    with isolated_app() as main:
        yield main


@pytest.fixture
def client(app_module):
    return TestClient(app_module.app)


def test_isolation_restores_global_state(monkeypatch):
    sentinel_model, sentinel_utils = object(), object()
    monkeypatch.setitem(sys.modules, "model", sentinel_model)
    monkeypatch.setitem(sys.modules, "utils", sentinel_utils)
    monkeypatch.delitem(sys.modules, "main", raising=False)
    monkeypatch.delenv("SECRET_KEY", raising=False)
    path_before = list(sys.path)
    modules_before = {n: m for n, m in sys.modules.items() if in_app_namespace(n)}

    with isolated_app() as main:
        assert main.__name__ == "main"
        assert os.environ["SECRET_KEY"] == TEST_KEY

    assert sys.modules["model"] is sentinel_model
    assert sys.modules["utils"] is sentinel_utils
    modules_after = {n: m for n, m in sys.modules.items() if in_app_namespace(n)}
    assert modules_after.keys() == modules_before.keys()
    assert all(modules_after[n] is modules_before[n] for n in modules_before)
    assert "SECRET_KEY" not in os.environ
    assert sys.path == path_before


def test_isolation_cleans_up_when_body_fails(monkeypatch):
    monkeypatch.delitem(sys.modules, "main", raising=False)
    monkeypatch.setenv("SECRET_KEY", "outer-value")

    with pytest.raises(RuntimeError):
        with isolated_app():
            raise RuntimeError("boom")

    assert "main" not in sys.modules
    assert os.environ["SECRET_KEY"] == "outer-value"


def token(roles, key=TEST_KEY, exp_delta=3600):
    payload = {"username": "smoke-user", "name": "Smoke User", "roles": roles, "exp": int(time.time()) + exp_delta}
    return jwt.encode(payload, key, algorithm="HS256")


def bearer(value):
    return {"Authorization": f"Bearer {value}"}


def test_health_needs_no_token(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert "running" in response.text


def test_valid_token_with_role_reaches_route(client):
    response = client.get("/history", headers=bearer(token(["auditor"])))

    assert response.status_code == 200
    assert response.json() == HISTORY


def test_missing_token_is_rejected(client):
    response = client.get("/history")

    # Framework behaviour change: HTTPBearer returned 403 without a challenge on the
    # baseline FastAPI 0.115.12; the locked FastAPI 0.133.0 returns 401 with a challenge.
    if fastapi_version() >= (0, 133, 0):
        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"
    else:
        assert response.status_code == 403
        assert "www-authenticate" not in response.headers


@pytest.mark.parametrize(
    "bad_token",
    [token(["admin"], key=OTHER_KEY), token(["admin"], exp_delta=-10), "not-a-jwt"],
    ids=["wrong-key", "expired", "garbage"],
)
def test_invalid_token_is_unauthorized(client, bad_token):
    response = client.get("/history", headers=bearer(bad_token))

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_token_without_required_role_is_forbidden(client):
    response = client.get("/history", headers=bearer(token(["logger"])))

    assert response.status_code == 403


def test_auditor_cannot_post_log_and_db_untouched(client):
    # Auditor lacks logger/admin role: rejected before any (stubbed-to-fail) DB write.
    response = client.post(
        "/log",
        content="@prefix ex: <http://example.org/> .",
        headers={**bearer(token(["auditor"])), "Content-Type": "text/turtle"},
    )

    assert response.status_code == 403
