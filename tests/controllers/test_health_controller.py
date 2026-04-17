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
        assert "successful" in result["message"].lower()


@pytest.mark.anyio
async def test_health_checks_database_failure():
    """Test database connectivity check on failure."""
    from src.controllers.health_controller import check_database

    with patch("src.controllers.health_controller.engine") as mock_engine:
        mock_engine.connect = MagicMock(side_effect=Exception("Connection failed"))

        result = await check_database()

        assert result["status"] == "unhealthy"
        assert "failed" in result["message"].lower()


@pytest.mark.anyio
async def test_health_checks_axiom_success():
    """Test successful Axiom connectivity check."""
    from src.controllers.health_controller import check_axiom

    with patch("os.environ.get") as mock_getenv:
        mock_getenv.side_effect = lambda key: {
            "AXIOM_INGEST_TOKEN": "test-token",
            "AXIOM_INGEST_DATASET": "test-dataset",
        }.get(key)

        with patch("axiom_py.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.apl.query = AsyncMock()

            result = await check_axiom()

            assert result["status"] == "healthy"
            assert "successful" in result["message"].lower()


@pytest.mark.anyio
async def test_health_checks_axiom_missing_credentials():
    """Test Axiom connectivity check with missing credentials."""
    from src.controllers.health_controller import check_axiom

    with patch("os.environ.get") as mock_getenv:
        mock_getenv.return_value = None

        result = await check_axiom()

        assert result["status"] == "unhealthy"
        assert "not configured" in result["message"].lower()


@pytest.mark.anyio
async def test_health_checks_axiom_connection_failure():
    """Test Axiom connectivity check on connection failure."""
    from src.controllers.health_controller import check_axiom

    with patch("os.environ.get") as mock_getenv:
        mock_getenv.side_effect = lambda key: {
            "AXIOM_INGEST_TOKEN": "test-token",
            "AXIOM_INGEST_DATASET": "test-dataset",
        }.get(key)

        with patch("axiom_py.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.apl.query = AsyncMock(side_effect=Exception("Query failed"))

            result = await check_axiom()

            assert result["status"] == "unhealthy"
            assert "failed" in result["message"].lower()


def test_health_checks_endpoint_all_healthy():
    """Test /health/checks endpoint when all checks pass."""
    client = TestClient(app)

    with patch("src.controllers.health_controller.check_database") as mock_db:
        mock_db.return_value = {"status": "healthy", "message": "DB OK"}

        with patch("src.controllers.health_controller.check_axiom") as mock_axiom:
            mock_axiom.return_value = {"status": "healthy", "message": "Axiom OK"}

            response = client.get("/health/checks")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["checks"]["database"]["status"] == "healthy"
            assert data["checks"]["axiom"]["status"] == "healthy"


def test_health_checks_endpoint_database_unhealthy():
    """Test /health/checks endpoint when database check fails."""
    client = TestClient(app)

    with patch("src.controllers.health_controller.check_database") as mock_db:
        mock_db.return_value = {"status": "unhealthy", "message": "DB failed"}

        with patch("src.controllers.health_controller.check_axiom") as mock_axiom:
            mock_axiom.return_value = {"status": "healthy", "message": "Axiom OK"}

            response = client.get("/health/checks")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "unhealthy"
            assert data["checks"]["database"]["status"] == "unhealthy"
            assert data["checks"]["axiom"]["status"] == "healthy"


def test_health_checks_endpoint_axiom_unhealthy():
    """Test /health/checks endpoint when Axiom check fails."""
    client = TestClient(app)

    with patch("src.controllers.health_controller.check_database") as mock_db:
        mock_db.return_value = {"status": "healthy", "message": "DB OK"}

        with patch("src.controllers.health_controller.check_axiom") as mock_axiom:
            mock_axiom.return_value = {"status": "unhealthy", "message": "Axiom failed"}

            response = client.get("/health/checks")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "unhealthy"
            assert data["checks"]["database"]["status"] == "healthy"
            assert data["checks"]["axiom"]["status"] == "unhealthy"


def test_health_checks_endpoint_all_unhealthy():
    """Test /health/checks endpoint when all checks fail."""
    client = TestClient(app)

    with patch("src.controllers.health_controller.check_database") as mock_db:
        mock_db.return_value = {"status": "unhealthy", "message": "DB failed"}

        with patch("src.controllers.health_controller.check_axiom") as mock_axiom:
            mock_axiom.return_value = {"status": "unhealthy", "message": "Axiom failed"}

            response = client.get("/health/checks")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "unhealthy"
            assert data["checks"]["database"]["status"] == "unhealthy"
            assert data["checks"]["axiom"]["status"] == "unhealthy"
