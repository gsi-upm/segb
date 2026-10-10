# Tests for SEGB Server

This section contains all the tests for the SEGB server implemented using pytest.

## Running the Tests

The standalone authentication unit tests need no Docker, MongoDB or `test.env`.
Run only this file from the repository root:

```bash
.venv/bin/python -m pytest -q test/test_credentials_unit.py
```

To run the tests, use the `pytest` command. The tests are designed to utilize the `./test/compose_test.yaml` file to set up the necessary Docker environment. Ensure that Docker is running and the `./test/compose_test.yaml` file is correctly configured before executing the tests.

```bash
pytest
```

### Explanation of Files

- **compose_test.yaml**: This Docker Compose file is specifically configured to set up the testing environment for the SEGB server. It ensures that the necessary services and dependencies are properly initialized for testing.
- **test.env**: This environment file contains the configuration variables required for the testing environment. It allows you to customize the behavior of the tests without modifying the code.

### Docker Image Version

The tests use the `:testing` version of the Docker image. This version is expected to be built when you want to test a specific version of the application. Ensure that the `:testing` image is up-to-date before running the tests.
