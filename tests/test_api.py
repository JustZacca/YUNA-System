"""
Tests for YUNA API.
"""

import os
import pytest
from unittest.mock import patch, MagicMock

# Set test environment before imports
os.environ["YUNA_USERNAME"] = "testuser"
os.environ["YUNA_PASSWORD"] = "testpass"
os.environ["JWT_SECRET"] = "test-secret-key"

from fastapi.testclient import TestClient
from yuna.api.main import create_app
from yuna.api.auth import create_access_token, decode_token, authenticate_user


# ==================== Auth Tests ====================

class TestAuth:
    """Tests for authentication module."""

    def test_create_access_token(self):
        """Test JWT token creation."""
        token = create_access_token("testuser")
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_valid_token(self):
        """Test decoding a valid token."""
        token = create_access_token("testuser")
        data = decode_token(token)

        assert data is not None
        assert data.username == "testuser"

    def test_decode_invalid_token(self):
        """Test decoding an invalid token."""
        data = decode_token("invalid-token")
        assert data is None

    def test_authenticate_user_valid(self):
        """Test authentication with valid credentials."""
        with patch.dict(os.environ, {"YUNA_USERNAME": "admin", "YUNA_PASSWORD": "secret"}):
            result = authenticate_user("admin", "secret")
            assert result == "admin"

    def test_authenticate_user_invalid(self):
        """Test authentication with invalid credentials."""
        with patch.dict(os.environ, {"YUNA_USERNAME": "admin", "YUNA_PASSWORD": "secret"}):
            result = authenticate_user("admin", "wrong")
            assert result is None


# ==================== API Tests ====================

@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Create authorization headers with valid token."""
    token = create_access_token("testuser")
    return {"Authorization": f"Bearer {token}"}


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self, client):
        """Test health check returns 200."""
        response = client.get("/api/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "timestamp" in data


class TestVersionEndpoint:
    """Tests for version endpoint."""

    def test_get_version(self, client):
        """Test version endpoint returns version info."""
        response = client.get("/api/version")
        assert response.status_code == 200

        data = response.json()
        assert "version" in data
        assert data["name"] == "YUNA API"


class TestLoginEndpoint:
    """Tests for login endpoint."""

    def test_login_valid_credentials(self, client):
        """Test login with valid credentials."""
        response = client.post(
            "/api/login",
            json={"username": "testuser", "password": "testpass"}
        )
        assert response.status_code == 200

        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data

    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials."""
        response = client.post(
            "/api/login",
            json={"username": "wrong", "password": "wrong"}
        )
        assert response.status_code == 401

    def test_login_missing_fields(self, client):
        """Test login with missing fields."""
        response = client.post("/api/login", json={})
        assert response.status_code == 422  # Validation error


class TestMeEndpoint:
    """Tests for /me endpoint."""

    def test_me_authenticated(self, client, auth_headers):
        """Test /me with valid token."""
        response = client.get("/api/me", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert data["username"] == "testuser"
        assert data["is_authenticated"] is True

    def test_me_unauthenticated(self, client):
        """Test /me without token."""
        response = client.get("/api/me")
        assert response.status_code == 401

    def test_me_invalid_token(self, client):
        """Test /me with invalid token."""
        response = client.get(
            "/api/me",
            headers={"Authorization": "Bearer invalid-token"}
        )
        assert response.status_code == 401


class TestStatsEndpoint:
    """Tests for stats endpoint."""

    def test_stats_returns_counts(self, client, tmp_path):
        """Test stats endpoint returns library counts."""
        # Use a temp database
        from yuna.data.database import Database
        from yuna.api import deps

        test_db = Database(str(tmp_path / "test.db"))
        deps._db = test_db

        response = client.get("/api/stats")
        assert response.status_code == 200

        data = response.json()
        assert "anime_count" in data
        assert "series_count" in data
        assert "films_count" in data
        assert "version" in data

        # Cleanup
        deps._db = None
