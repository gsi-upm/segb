# Tests for SEGB Server

This section contains all the tests for the SEGB server implemented using pytest.

## Running the Tests

The standalone authentication unit tests need no Docker, MongoDB or `test.env`.
Run only this file from the repository root:

```bash
.venv/bin/python -m pytest -q test/test_credentials_unit.py
```

### Security and dependency checks (no Docker)

These files are self-contained: no Docker, MongoDB, shared `testing_utils.py` or `test.env`; secrets are synthetic.

- `test_http_security_unit.py`: h11 rejects a malformed chunked-body terminator, plus a well-formed control.
- `test_app_smoke_unit.py`: imports the real `server/main.py` and routes with only DB access stubbed (any unstubbed DB call fails the test). Covers `/health`, valid/invalid/expired/missing token and a forbidden role.
- `test_driver_security_unit.py`: installed-version floors, MongoEngine/BSON round trips, `idna` and `python-dotenv` regressions (details below).
- `test_credentials_unit.py`: JWT validator unit tests.

```bash
uv lock --check
uv run --no-sync python -m pytest -q test/test_http_security_unit.py test/test_app_smoke_unit.py test/test_driver_security_unit.py test/test_credentials_unit.py
```

Never run bare `pytest` to verify dependencies: the integration suite removes the shared `segb-db-test` Docker volume and uses port 5000.

### Dependency versions

HTTP pins (validated compatible set, not proven to be the minimum): `fastapi[standard-no-fastapi-cloud-cli] 0.133.0`, `starlette 1.3.1`, `anyio 4.14.2`, `h11 0.16.0`, `python-multipart 0.0.31`, `uvicorn 0.34.0`. The `standard-no-fastapi-cloud-cli` extra avoids the FastAPI Cloud CLI chain, which the app does not need.

Driver stack, locked in `uv.lock`: `pymongo 4.18.2`, `idna 3.15`, `python-dotenv 1.2.2`, `pygments 2.20.0`.

The h11 regression was compared only on h11 0.14.0 (fails) and 0.16.0 (passes); 0.16.0 is the fixed version from the audit (GHSA-vqfr-h8mv-ghfj). Behaviour change: a request without a Bearer token now returns 401 with `WWW-Authenticate: Bearer` instead of 403.

### Driver security tests

`test_driver_security_unit.py` inspects the **installed** environment, not `uv.lock`. It covers version floors for the four driver packages above, compared with PEP 440 (`packaging.version.Version`, so release candidates do not satisfy a final floor), and these checks:

- **MongoEngine/BSON (offline):** loads the real `server/utils` and `server/model.py` in an isolated context that restores `sys.modules`, `sys.path` and MongoEngine's global document registry afterwards. It validates and encodes `Graph`, `Log`, `Insertion` and `Deletion` with the installed native `bson`, compares the decoded BSON documents field by field and, after `_from_son()`, compares the reconstructed fields read from `_data` (so no database dereference happens). Controls build altered or incomplete documents and require the check to fail. RDF isomorphism is checked for Turtle to JSON-LD to BSON to graph to Turtle and for the stored `Insertion` and `Deletion` Turtle. This covers only these four document shapes with synthetic data.
- **idna (GHSA-65pc-fj4g-8rjx):** instruments the contextual validators and asserts that overlong input (300 characters) is rejected before they run, in `encode`, `check_label`, `alabel` and `ulabel`. Controls: valid katakana middle dot and Arabic-digit domains must still reach the contextual rules, encode and decode.
- **python-dotenv (GHSA-mf9w-mj56-hr94):** calls `set_key` on a synthetic symlink in a temporary directory, forcing `EXDEV` only for that link inside `shutil.move`. It requires `set_key` to succeed, the link target to stay unchanged, and evidence that the vulnerable branch (or the `os.replace` path) ran. An injected `EACCES` is a negative control and never counts as success.

### Verification record (parent-run, not CI)

- Combined host run of the four unit files: 56 passed, 2 deprecation warnings.
- `pip-audit`: no known vulnerabilities reported for the locked graph.
- The original `Dockerfile` builds (uv 0.6.12, Python 3.12.7). The same 56 tests passed inside the image, with pytest tools mounted read-only and the image's production source files copied unchanged into a tmpfs layout.

### Limits

- Real MongoDB CRUD and proxy integration were not verified. No deployment was done.
- There is no behavioural security regression test for `pymongo` or `pygments`; their fixes are covered only by the installed-version floor.
- The BSON tests do not replace MongoDB integration tests. Exploitation of the native overflow was not run.
- The tests use synthetic secrets and global-state isolation, not a production-like environment.

To run the full integration tests, use the `pytest` command. The tests are designed to utilize the `./test/compose_test.yaml` file to set up the necessary Docker environment. Ensure that Docker is running and the `./test/compose_test.yaml` file is correctly configured before executing the tests.

```bash
pytest
```

### Explanation of Files

- **compose_test.yaml**: This Docker Compose file is specifically configured to set up the testing environment for the SEGB server. It ensures that the necessary services and dependencies are properly initialized for testing.
- **test.env**: This environment file contains the configuration variables required for the testing environment. It allows you to customize the behavior of the tests without modifying the code.

### Docker Image Version

The tests use the `:testing` version of the Docker image. This version is expected to be built when you want to test a specific version of the application. Ensure that the `:testing` image is up-to-date before running the tests.
