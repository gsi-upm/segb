"""Exercise the real JWT validator without Docker, MongoDB or test.env."""

import asyncio
import importlib.util
from pathlib import Path
import time

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
import jwt
import pytest


TEST_KEY = "synthetic-authentication-test-key-" * 2
OTHER_KEY = "different-authentication-test-key-" * 2


@pytest.fixture
def credentials(monkeypatch):
    # Load only this module; avoid application startup and shared test helpers.
    path = Path(__file__).resolve().parents[1] / "server/utils/credentials.py"
    spec = importlib.util.spec_from_file_location("credentials_unit_target", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "SECRET_KEY", TEST_KEY)
    return module


@pytest.fixture
def payload():
    return {
        "username": "unit-user",
        "name": "Synthetic User",
        "roles": ["auditor", "logger"],
        "exp": int(time.time()) + 3600,
    }


def validate(credentials, token):
    auth = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    return asyncio.run(credentials.validate_token(auth))


def assert_unauthorized(credentials, token):
    with pytest.raises(HTTPException) as error:
        validate(credentials, token)
    assert error.value.status_code == 401
    assert error.value.headers == {"WWW-Authenticate": "Bearer"}


@pytest.mark.parametrize("with_exp", [True, False], ids=["with-exp", "without-exp"])
def test_valid_token_preserves_identity_and_roles(credentials, payload, with_exp):
    if not with_exp:
        payload.pop("exp")
    token = jwt.encode(payload, TEST_KEY, algorithm="HS256")

    user = validate(credentials, token)

    assert user.username == payload["username"]
    assert user.name == payload["name"]
    assert user.roles == payload["roles"]
    assert user.exp == payload.get("exp")


def test_unknown_critical_header_is_rejected(credentials, payload):
    # CVE-2026-32597 / GHSA-752w-5fwx-jx9f: 2.10.1 accepts this token.
    token = jwt.encode(
        payload,
        TEST_KEY,
        algorithm="HS256",
        headers={"crit": ["unknown-extension"], "unknown-extension": True},
    )
    assert_unauthorized(credentials, token)


def test_wrong_signature_is_rejected(credentials, payload):
    token = jwt.encode(payload, OTHER_KEY, algorithm="HS256")
    assert_unauthorized(credentials, token)


def test_expired_token_is_rejected(credentials, payload):
    payload["exp"] = int(time.time()) - 3600
    token = jwt.encode(payload, TEST_KEY, algorithm="HS256")
    assert_unauthorized(credentials, token)


@pytest.mark.parametrize("algorithm", ["HS384", "none"])
def test_disallowed_algorithm_is_rejected(credentials, payload, algorithm):
    key = None if algorithm == "none" else TEST_KEY
    token = jwt.encode(payload, key, algorithm=algorithm)
    assert_unauthorized(credentials, token)


def test_unset_secret_preserves_anonymous_access(credentials, monkeypatch):
    monkeypatch.setattr(credentials, "SECRET_KEY", None)

    user = validate(credentials, "invalid-token")

    assert user.username == "anonymous_user"
    assert user.roles == [role.value for role in credentials.Role]
    assert user.exp is None
