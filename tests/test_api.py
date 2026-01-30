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


# ==================== Anime API Tests ====================

@pytest.fixture
def test_db(tmp_path):
    """Create a test database with sample data."""
    from datetime import datetime
    from yuna.data.database import Database
    from yuna.api import deps

    db = Database(str(tmp_path / "test.db"))

    # Add sample anime (using correct DB field names)
    db.add_anime(
        name="Test Anime",
        link="/anime/test-anime",
        last_update=datetime.now(),
        numero_episodi=12,
    )
    db.update_anime_episodes("Test Anime", 5)

    db.add_anime(
        name="Another Anime",
        link="/anime/another",
        last_update=datetime.now(),
        numero_episodi=10,
    )
    db.update_anime_episodes("Another Anime", 10)

    deps._db = db
    yield db
    deps._db = None


class TestAnimeList:
    """Tests for anime list endpoint."""

    def test_list_anime_empty(self, client, tmp_path):
        """Test listing anime when library is empty."""
        from yuna.data.database import Database
        from yuna.api import deps

        deps._db = Database(str(tmp_path / "empty.db"))

        response = client.get("/api/anime")
        assert response.status_code == 200

        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

        deps._db = None

    def test_list_anime_with_data(self, client, test_db):
        """Test listing anime with data."""
        response = client.get("/api/anime")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

        names = [a["name"] for a in data["items"]]
        assert "Test Anime" in names
        assert "Another Anime" in names


class TestAnimeDetail:
    """Tests for anime detail endpoint."""

    def test_get_anime_found(self, client, test_db):
        """Test getting anime details."""
        response = client.get("/api/anime/Test Anime")
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "Test Anime"
        assert data["episodes_downloaded"] == 5
        assert data["episodes_total"] == 12
        assert len(data["missing_episodes"]) == 7  # 6-12

    def test_get_anime_not_found(self, client, test_db):
        """Test getting non-existent anime."""
        response = client.get("/api/anime/NonExistent")
        assert response.status_code == 404


class TestAnimeEpisodes:
    """Tests for anime episodes endpoint."""

    def test_get_episodes(self, client, test_db):
        """Test getting episode list."""
        response = client.get("/api/anime/Test Anime/episodes")
        assert response.status_code == 200

        data = response.json()
        assert data["anime_name"] == "Test Anime"
        assert data["total"] == 12
        assert data["downloaded"] == 5
        assert len(data["missing"]) == 7
        assert len(data["episodes"]) == 12

    def test_get_episodes_not_found(self, client, test_db):
        """Test getting episodes for non-existent anime."""
        response = client.get("/api/anime/NonExistent/episodes")
        assert response.status_code == 404


class TestAnimeAdd:
    """Tests for adding anime."""

    def test_add_anime_invalid_url(self, client, auth_headers, test_db):
        """Test adding anime with invalid URL."""
        response = client.post(
            "/api/anime",
            json={"url": "https://example.com/not-animeworld"},
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "AnimeWorld" in response.json()["detail"]

    def test_add_anime_unauthorized(self, client, test_db):
        """Test adding anime without auth."""
        response = client.post(
            "/api/anime",
            json={"url": "https://www.animeworld.tv/play/test-anime"}
        )
        assert response.status_code == 401


class TestAnimeRemove:
    """Tests for removing anime."""

    def test_remove_anime_success(self, client, auth_headers, test_db):
        """Test removing anime."""
        response = client.delete(
            "/api/anime/Test Anime",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify removed
        response = client.get("/api/anime/Test Anime")
        assert response.status_code == 404

    def test_remove_anime_not_found(self, client, auth_headers, test_db):
        """Test removing non-existent anime."""
        response = client.delete(
            "/api/anime/NonExistent",
            headers=auth_headers
        )
        assert response.status_code == 404

    def test_remove_anime_unauthorized(self, client, test_db):
        """Test removing anime without auth."""
        response = client.delete("/api/anime/Test Anime")
        assert response.status_code == 401


class TestAnimeDownload:
    """Tests for download endpoint."""

    def test_download_unauthorized(self, client, test_db):
        """Test download without auth."""
        response = client.post(
            "/api/anime/Test Anime/download",
            json={}
        )
        assert response.status_code == 401

    def test_download_not_found(self, client, auth_headers, test_db):
        """Test download for non-existent anime."""
        response = client.post(
            "/api/anime/NonExistent/download",
            json={},
            headers=auth_headers
        )
        assert response.status_code == 404

    def test_download_status_no_active(self, client, test_db):
        """Test getting download status when none active."""
        response = client.get("/api/anime/Test Anime/download/status")
        assert response.status_code == 200
        assert response.json()["active"] is False
