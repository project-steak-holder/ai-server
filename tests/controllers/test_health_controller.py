"""Unit tests for health controller."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.mark.anyio
async def test_health_checks_database_success():
    """Test successful database connectivity check."""
    from src.controllers.health_controller import check_database

    with patch("src.controllers.health_controller.engine") as mock_engine:
        mock_conn = AsyncMock()
        mock_engine.connect = MagicMock(return_value=mock_conn)
        mock_conn.execute = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock()

        result = await check_database()

        assert result["status"] == "healthy"


@pytest.mark.anyio
async def test_health_checks_database_failure():
    """Test database connectivity check on failure."""
    from src.controllers.health_controller import check_database

    with patch("src.controllers.health_controller.engine") as mock_engine:
        mock_engine.connect = MagicMock(side_effect=Exception("Connection failed"))

        result = await check_database()

        assert result["status"] == "unhealthy"


@pytest.mark.anyio
async def test_health_checks_axiom_success():
    """Test successful observability connectivity check."""
    from src.controllers.health_controller import check_observability

    with patch("os.environ.get") as mock_getenv:
        mock_getenv.side_effect = lambda key, _default=None: {
            "AXIOM_INGEST_TOKEN": "test-token",
            "AXIOM_INGEST_DATASET": "test-dataset",
        }.get(key)

        with patch("axiom_py.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.query = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            result = await check_observability()

            assert result["status"] == "healthy"


@pytest.mark.anyio
async def test_health_checks_axiom_missing_credentials():
    """Test observability connectivity check with missing credentials."""
    from src.controllers.health_controller import check_observability

    with patch("os.environ.get") as mock_getenv:
        mock_getenv.return_value = None

        result = await check_observability()

        assert result["status"] == "unhealthy"


@pytest.mark.anyio
async def test_health_checks_axiom_connection_failure():
    """Test observability connectivity check on connection failure."""
    from src.controllers.health_controller import check_observability

    with patch("os.environ.get") as mock_getenv:
        mock_getenv.side_effect = lambda key, _default=None: {
            "AXIOM_INGEST_TOKEN": "test-token",
            "AXIOM_INGEST_DATASET": "test-dataset",
        }.get(key)

        with patch("axiom_py.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.query = AsyncMock(side_effect=Exception("Query failed"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            result = await check_observability()

            assert result["status"] == "unhealthy"


@pytest.mark.anyio
async def test_health_checks_neon_auth_success():
    """Test successful auth service connectivity check."""
    from src.controllers.health_controller import check_auth

    with patch("os.environ.get") as mock_getenv:
        mock_getenv.side_effect = lambda key: {
            "AUTH_URL": "https://auth.example.com"
        }.get(key)

        with patch("src.controllers.health_controller.get_jwks") as mock_get_jwks:
            mock_get_jwks.return_value = {"keys": []}

            result = await check_auth()
            assert result["status"] == "healthy"


@pytest.mark.anyio
async def test_health_checks_neon_auth_missing_url():
    """Test auth service connectivity check with missing AUTH_URL."""
    from src.controllers.health_controller import check_auth

    with patch("os.environ.get") as mock_getenv:
        mock_getenv.return_value = None

        result = await check_auth()
        assert result["status"] == "unhealthy"


def test_health_dependencies_endpoint_all_healthy():
    """Test /health/dependencies endpoint when all checks pass."""
    client = TestClient(app)

    with patch("src.controllers.health_controller.check_database") as mock_db:
        mock_db.return_value = {"status": "healthy"}

        with patch(
            "src.controllers.health_controller.check_observability"
        ) as mock_observability:
            mock_observability.return_value = {"status": "healthy"}

            with patch("src.controllers.health_controller.check_auth") as mock_auth:
                mock_auth.return_value = {"status": "healthy"}

                response = client.get("/health/dependencies")

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "healthy"
                assert data["checks"]["database"]["status"] == "healthy"
                assert data["checks"]["observability"]["status"] == "healthy"
                assert data["checks"]["auth"]["status"] == "healthy"


def test_health_dependencies_endpoint_database_unhealthy_returns_503():
    """Test /health/dependencies endpoint returns 503 when database check fails."""
    client = TestClient(app)

    with patch("src.controllers.health_controller.check_database") as mock_db:
        mock_db.return_value = {"status": "unhealthy"}

        with patch(
            "src.controllers.health_controller.check_observability"
        ) as mock_observability:
            mock_observability.return_value = {"status": "healthy"}

            with patch("src.controllers.health_controller.check_auth") as mock_auth:
                mock_auth.return_value = {"status": "healthy"}

                response = client.get("/health/dependencies")

                assert response.status_code == 503
                data = response.json()
                assert data["status"] == "unhealthy"
                assert data["checks"]["database"]["status"] == "unhealthy"
                assert data["checks"]["observability"]["status"] == "healthy"
                assert data["checks"]["auth"]["status"] == "healthy"


def test_health_dependencies_endpoint_observability_unhealthy_returns_503():
    """Test /health/dependencies endpoint returns 503 when observability check fails."""
    client = TestClient(app)

    with patch("src.controllers.health_controller.check_database") as mock_db:
        mock_db.return_value = {"status": "healthy"}

        with patch(
            "src.controllers.health_controller.check_observability"
        ) as mock_observability:
            mock_observability.return_value = {"status": "unhealthy"}

            with patch("src.controllers.health_controller.check_auth") as mock_auth:
                mock_auth.return_value = {"status": "healthy"}

                response = client.get("/health/dependencies")

                assert response.status_code == 503
                data = response.json()
                assert data["status"] == "unhealthy"
                assert data["checks"]["database"]["status"] == "healthy"
                assert data["checks"]["observability"]["status"] == "unhealthy"
                assert data["checks"]["auth"]["status"] == "healthy"


def test_health_dependencies_endpoint_all_unhealthy_returns_503():
    """Test /health/dependencies endpoint returns 503 when all checks fail."""
    client = TestClient(app)

    with patch("src.controllers.health_controller.check_database") as mock_db:
        mock_db.return_value = {"status": "unhealthy"}

        with patch(
            "src.controllers.health_controller.check_observability"
        ) as mock_observability:
            mock_observability.return_value = {"status": "unhealthy"}

            with patch("src.controllers.health_controller.check_auth") as mock_auth:
                mock_auth.return_value = {"status": "unhealthy"}

                response = client.get("/health/dependencies")

                assert response.status_code == 503
                data = response.json()
                assert data["status"] == "unhealthy"
                assert data["checks"]["database"]["status"] == "unhealthy"
                assert data["checks"]["observability"]["status"] == "unhealthy"
                assert data["checks"]["auth"]["status"] == "unhealthy"
