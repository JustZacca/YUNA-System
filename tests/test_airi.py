"""
Tests for airi.py - Configuration and database wrapper for YUNA-System.

This module tests:
    - Airi initialization with database
    - CRUD operations through Airi interface
    - Environment variable handling
    - Auto-migration from config.json
    - URL normalization and link retrieval
"""

import os
import sys
import json
import shutil
from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestAiriInitialization:
    """Tests for Airi class initialization."""

    def test_airi_initialization_success(self, mock_env, temp_db, mock_httpx):
        """Verify that Airi initializes correctly with valid environment."""
        with patch("yuna.providers.animeworld.client.httpx", mock_httpx):
            from yuna.providers.animeworld.client import Airi

            airi = Airi(db_path=temp_db)

            assert airi.destination_folder == mock_env["DESTINATION_FOLDER"]
            assert airi.telegram_token == mock_env["TELEGRAM_TOKEN"]
            assert airi.TELEGRAM_CHAT_ID == int(mock_env["TELEGRAM_CHAT_ID"])
            assert airi.UPDATE_TIME == int(mock_env["UPDATE_TIME"])

    def test_airi_initialization_missing_chat_id(self, monkeypatch, temp_db, mock_httpx):
        """Verify that Airi raises error when TELEGRAM_CHAT_ID is missing."""
        monkeypatch.setenv("TELEGRAM_TOKEN", "test_token")
        monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
        monkeypatch.setenv("DESTINATION_FOLDER", "/tmp/test")

        # Patch load_dotenv in the airi module to prevent loading .env file
        with patch("yuna.providers.animeworld.client.load_dotenv"):
            with patch("yuna.providers.animeworld.client.httpx", mock_httpx):
                from yuna.providers.animeworld.client import Airi

                with pytest.raises(ValueError, match="TELEGRAM_CHAT_ID non configurato"):
                    Airi(db_path=temp_db)

    def test_airi_initialization_invalid_chat_id(self, monkeypatch, temp_db, mock_httpx):
        """Verify that Airi raises error when TELEGRAM_CHAT_ID is not a number."""
        monkeypatch.setenv("TELEGRAM_TOKEN", "test_token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "not_a_number")
        monkeypatch.setenv("DESTINATION_FOLDER", "/tmp/test")

        with patch("yuna.providers.animeworld.client.httpx", mock_httpx):
            from yuna.providers.animeworld.client import Airi

            with pytest.raises(ValueError, match="deve essere un numero intero"):
                Airi(db_path=temp_db)

    def test_airi_default_update_time(self, monkeypatch, temp_db, mock_httpx):
        """Verify that Airi uses default UPDATE_TIME when not set."""
        monkeypatch.setenv("TELEGRAM_TOKEN", "test_token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "123456789")
        monkeypatch.setenv("DESTINATION_FOLDER", "/tmp/test")
        monkeypatch.delenv("UPDATE_TIME", raising=False)

        # Patch load_dotenv in the airi module to prevent loading .env file
        with patch("yuna.providers.animeworld.client.load_dotenv"):
            with patch("yuna.providers.animeworld.client.httpx", mock_httpx):
                from yuna.providers.animeworld.client import Airi

                airi = Airi(db_path=temp_db)
                assert airi.UPDATE_TIME == 60, "Default UPDATE_TIME should be 60"

    def test_airi_database_initialized(self, mock_env, temp_db, mock_httpx):
        """Verify that Airi initializes the database correctly."""
        with patch("yuna.providers.animeworld.client.httpx", mock_httpx):
            from yuna.providers.animeworld.client import Airi

            airi = Airi(db_path=temp_db)

            assert airi.db is not None, "Database should be initialized"
            assert os.path.exists(temp_db), "Database file should exist"


class TestAiriAnimeOperations:
    """Tests for anime CRUD operations through Airi."""

    def test_get_anime_empty(self, mock_env, temp_db, mock_httpx):
        """Verify that get_anime returns empty list for new database."""
        with patch("yuna.providers.animeworld.client.httpx", mock_httpx):
            from yuna.providers.animeworld.client import Airi

            airi = Airi(db_path=temp_db)
            anime_list = airi.get_anime()

            assert anime_list == [], "Should return empty list"

    def test_add_anime_success(self, mock_env, temp_db, mock_httpx):
        """Verify that add_anime adds anime correctly."""
        with patch("yuna.providers.animeworld.client.httpx", mock_httpx):
            from yuna.providers.animeworld.client import Airi

            airi = Airi(db_path=temp_db)
            airi.add_anime(
                name="Test Anime",
                link="https://animeworld.tv/play/test-anime.12345",
                last_update="2024-01-15 10:30:00",
                numero_episodi=12,
            )

            anime_list = airi.get_anime()
            assert len(anime_list) == 1
            assert anime_list[0]["name"] == "Test Anime"

    def test_add_anime_extracts_path_from_url(self, mock_env, temp_db, mock_httpx):
        """Verify that add_anime extracts path from full URL."""
        with patch("yuna.providers.animeworld.client.httpx", mock_httpx):
            from yuna.providers.animeworld.client import Airi

            airi = Airi(db_path=temp_db)
            airi.add_anime(
                name="Test Anime",
                link="https://animeworld.tv/play/test-anime.12345",
                last_update="2024-01-15 10:30:00",
                numero_episodi=12,
            )

            anime_list = airi.get_anime()
            # Link should be just the path, not full URL
            assert anime_list[0]["link"] == "/play/test-anime.12345"

    def test_add_anime_duplicate_link_skipped(self, mock_env, temp_db, mock_httpx):
        """Verify that adding anime with duplicate link is skipped."""
        with patch("yuna.providers.animeworld.client.httpx", mock_httpx):
            from yuna.providers.animeworld.client import Airi

            airi = Airi(db_path=temp_db)

            # Add first anime
            airi.add_anime(
                name="Anime One",
                link="https://animeworld.tv/play/test.12345",
                last_update="2024-01-15 10:30:00",
                numero_episodi=12,
            )

            # Try to add anime with same link (different name)
            airi.add_anime(
                name="Anime Two",
                link="https://animeworld.tv/play/test.12345",
                last_update="2024-01-16 10:30:00",
                numero_episodi=24,
            )

            anime_list = airi.get_anime()
            assert len(anime_list) == 1, "Duplicate link should be skipped"

    def test_add_anime_with_datetime_object(self, mock_env, temp_db, mock_httpx):
        """Verify that add_anime accepts datetime object for last_update."""
        with patch("yuna.providers.animeworld.client.httpx", mock_httpx):
            from yuna.providers.animeworld.client import Airi

            airi = Airi(db_path=temp_db)
            airi.add_anime(
                name="Test Anime",
                link="/play/test-anime.12345",
                last_update=datetime(2024, 1, 15, 10, 30, 0),
                numero_episodi=12,
            )

            anime_list = airi.get_anime()
            assert len(anime_list) == 1

    def test_remove_anime_success(self, mock_env, temp_db, temp_download_folder, mock_httpx, monkeypatch):
        """Verify that remove_anime removes from database and disk."""
        monkeypatch.setenv("DESTINATION_FOLDER", temp_download_folder)

        with patch("yuna.providers.animeworld.client.httpx", mock_httpx):
            from yuna.providers.animeworld.client import Airi

            airi = Airi(db_path=temp_db)

            # Add anime
            airi.add_anime(
                name="Test Anime",
                link="/play/test-anime.12345",
                last_update="2024-01-15 10:30:00",
                numero_episodi=12,
            )

            # Create folder for anime
            anime_folder = os.path.join(temp_download_folder, "Test Anime")
            os.makedirs(anime_folder, exist_ok=True)

            # Remove anime
            success, message = airi.remove_anime("Test Anime")

            assert success is True
            assert "rimosso completamente" in message

            # Verify removed from database
            anime_list = airi.get_anime()
            assert len(anime_list) == 0

            # Verify folder deleted
            assert not os.path.exists(anime_folder)

    def test_remove_anime_not_found(self, mock_env, temp_db, mock_httpx):
        """Verify that remove_anime handles non-existent anime."""
        with patch("yuna.providers.animeworld.client.httpx", mock_httpx):
            from yuna.providers.animeworld.client import Airi

            airi = Airi(db_path=temp_db)
            success, message = airi.remove_anime("Non Existent")

            assert success is False
            assert "non trovato" in message

    def test_remove_anime_folder_not_exists(self, mock_env, temp_db, temp_download_folder, mock_httpx, monkeypatch):
        """Verify that remove_anime handles missing folder gracefully."""
        monkeypatch.setenv("DESTINATION_FOLDER", temp_download_folder)

        with patch("yuna.providers.animeworld.client.httpx", mock_httpx):
            from yuna.providers.animeworld.client import Airi

            airi = Airi(db_path=temp_db)

            # Add anime without creating folder
            airi.add_anime(
                name="Test Anime",
                link="/play/test-anime.12345",
                last_update="2024-01-15 10:30:00",
                numero_episodi=12,
            )

            success, message = airi.remove_anime("Test Anime")

            assert success is True
            assert "Cartella non esisteva" in message


class TestAiriUpdateMethods:
    """Tests for update methods in Airi."""

    def test_update_downloaded_episodes(self, mock_env, temp_db, mock_httpx):
        """Verify that update_downloaded_episodes works correctly."""
        with patch("yuna.providers.animeworld.client.httpx", mock_httpx):
            from yuna.providers.animeworld.client import Airi

            airi = Airi(db_path=temp_db)
            airi.add_anime(
                name="Test Anime",
                link="/play/test.12345",
                last_update="2024-01-15 10:30:00",
                numero_episodi=12,
            )

            airi.update_downloaded_episodes("Test Anime", 8)

            anime = airi.db.get_anime_by_name("Test Anime")
            assert anime["episodi_scaricati"] == 8

    def test_update_episodes_number(self, mock_env, temp_db, mock_httpx):
        """Verify that update_episodes_number works correctly."""
        with patch("yuna.providers.animeworld.client.httpx", mock_httpx):
            from yuna.providers.animeworld.client import Airi

            airi = Airi(db_path=temp_db)
            airi.add_anime(
                name="Test Anime",
                link="/play/test.12345",
                last_update="2024-01-15 10:30:00",
                numero_episodi=12,
            )

            airi.update_episodes_number("Test Anime", 24)

            anime = airi.db.get_anime_by_name("Test Anime")
            assert anime["numero_episodi"] == 24

    def test_update_last_update(self, mock_env, temp_db, mock_httpx):
        """Verify that update_last_update works correctly."""
        with patch("yuna.providers.animeworld.client.httpx", mock_httpx):
            from yuna.providers.animeworld.client import Airi

            airi = Airi(db_path=temp_db)
            airi.add_anime(
                name="Test Anime",
                link="/play/test.12345",
                last_update="2024-01-15 10:30:00",
                numero_episodi=12,
            )

            airi.update_last_update("Test Anime", "2024-06-15 15:00:00")

            anime = airi.db.get_anime_by_name("Test Anime")
            assert "2024-06-15" in anime["last_update"]

    def test_update_last_update_with_datetime(self, mock_env, temp_db, mock_httpx):
        """Verify that update_last_update accepts datetime object."""
        with patch("yuna.providers.animeworld.client.httpx", mock_httpx):
            from yuna.providers.animeworld.client import Airi

            airi = Airi(db_path=temp_db)
            airi.add_anime(
                name="Test Anime",
                link="/play/test.12345",
                last_update="2024-01-15 10:30:00",
                numero_episodi=12,
            )

            airi.update_last_update("Test Anime", datetime(2024, 6, 15, 15, 0, 0))

            anime = airi.db.get_anime_by_name("Test Anime")
            assert "2024-06-15" in anime["last_update"]


class TestAiriLinkRetrieval:
    """Tests for get_anime_link with partial matching."""

    def test_get_anime_link_exact_match(self, mock_env, temp_db, mock_httpx):
        """Verify that get_anime_link works with exact name."""
        with patch("yuna.providers.animeworld.client.httpx", mock_httpx):
            from yuna.providers.animeworld.client import Airi

            airi = Airi(db_path=temp_db)
            airi.add_anime(
                name="Test Anime",
                link="/play/test-anime.12345",
                last_update="2024-01-15 10:30:00",
                numero_episodi=12,
            )

            link = airi.get_anime_link("Test Anime")
            assert link == "/play/test-anime.12345"

    def test_get_anime_link_partial_match(self, mock_env, temp_db, mock_httpx):
        """Verify that get_anime_link works with partial name."""
        with patch("yuna.providers.animeworld.client.httpx", mock_httpx):
            from yuna.providers.animeworld.client import Airi

            airi = Airi(db_path=temp_db)
            airi.add_anime(
                name="My Favorite Anime",
                link="/play/my-favorite-anime.12345",
                last_update="2024-01-15 10:30:00",
                numero_episodi=12,
            )

            link = airi.get_anime_link("Favorite")
            assert link == "/play/my-favorite-anime.12345"

    def test_get_anime_link_case_insensitive(self, mock_env, temp_db, mock_httpx):
        """Verify that get_anime_link is case insensitive."""
        with patch("yuna.providers.animeworld.client.httpx", mock_httpx):
            from yuna.providers.animeworld.client import Airi

            airi = Airi(db_path=temp_db)
            airi.add_anime(
                name="Test Anime",
                link="/play/test-anime.12345",
                last_update="2024-01-15 10:30:00",
                numero_episodi=12,
            )

            link = airi.get_anime_link("test anime")
            assert link == "/play/test-anime.12345"

    def test_get_anime_link_not_found(self, mock_env, temp_db, mock_httpx):
        """Verify that get_anime_link returns proper message when not found."""
        with patch("yuna.providers.animeworld.client.httpx", mock_httpx):
            from yuna.providers.animeworld.client import Airi

            airi = Airi(db_path=temp_db)
            link = airi.get_anime_link("Non Existent")

            assert link == "Anime non trovato."

    def test_get_anime_link_strips_whitespace(self, mock_env, temp_db, mock_httpx):
        """Verify that get_anime_link handles whitespace in input."""
        with patch("yuna.providers.animeworld.client.httpx", mock_httpx):
            from yuna.providers.animeworld.client import Airi

            airi = Airi(db_path=temp_db)
            airi.add_anime(
                name="Test Anime",
                link="/play/test-anime.12345",
                last_update="2024-01-15 10:30:00",
                numero_episodi=12,
            )

            link = airi.get_anime_link("  Test Anime  ")
            assert link == "/play/test-anime.12345"


class TestAiriAutoMigration:
    """Tests for automatic migration from config.json."""

    def test_auto_migration_when_config_exists(self, mock_env, temp_db, tmp_path, mock_httpx, monkeypatch):
        """Verify that Airi auto-migrates from config.json if it exists."""
        # Create config.json in the working directory
        config_data = {
            "anime": [
                {
                    "name": "Auto Migrate Anime",
                    "link": "/play/auto-migrate.12345",
                    "last_update": "2024-01-15 10:30:00",
                    "episodi_scaricati": 5,
                    "numero_episodi": 12,
                }
            ],
            "tv": [],
            "movies": [],
        }

        # Change to tmp_path for config.json
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            config_path = tmp_path / "config.json"
            with open(config_path, "w") as f:
                json.dump(config_data, f)

            with patch("yuna.providers.animeworld.client.httpx", mock_httpx):
                from yuna.providers.animeworld.client import Airi

                airi = Airi(db_path=temp_db)

                # Verify anime was migrated
                anime_list = airi.get_anime()
                assert len(anime_list) == 1
                assert anime_list[0]["name"] == "Auto Migrate Anime"

        finally:
            os.chdir(original_cwd)

    def test_no_migration_without_config(self, mock_env, temp_db, mock_httpx):
        """Verify that Airi works fine without config.json."""
        with patch("yuna.providers.animeworld.client.httpx", mock_httpx):
            from yuna.providers.animeworld.client import Airi

            airi = Airi(db_path=temp_db)

            # Should initialize successfully without errors
            anime_list = airi.get_anime()
            assert anime_list == []


class TestAiriDestinationFolder:
    """Tests for destination folder handling."""

    def test_get_destination_folder_success(self, mock_env, temp_db, mock_httpx):
        """Verify that get_destination_folder returns correct path."""
        with patch("yuna.providers.animeworld.client.httpx", mock_httpx):
            from yuna.providers.animeworld.client import Airi

            airi = Airi(db_path=temp_db)
            folder = airi.get_destination_folder()

            assert folder == mock_env["DESTINATION_FOLDER"]

    def test_get_destination_folder_not_set(self, monkeypatch, temp_db, mock_httpx):
        """Verify that get_destination_folder raises error when not set."""
        monkeypatch.setenv("TELEGRAM_TOKEN", "test_token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "123456789")
        monkeypatch.delenv("DESTINATION_FOLDER", raising=False)

        with patch("yuna.providers.animeworld.client.httpx", mock_httpx):
            from yuna.providers.animeworld.client import Airi

            airi = Airi(db_path=temp_db)
            airi.destination_folder = None  # Force None

            with pytest.raises(ValueError, match="cartella di destinazione"):
                airi.get_destination_folder()


class TestAiriTVOperations:
    """Tests for TV show operations through Airi."""

    def test_get_tv_empty(self, mock_env, temp_db, mock_httpx):
        """Verify that get_tv returns empty list for new database."""
        with patch("yuna.providers.animeworld.client.httpx", mock_httpx):
            from yuna.providers.animeworld.client import Airi

            airi = Airi(db_path=temp_db)
            tv_list = airi.get_tv()

            assert tv_list == []

    def test_add_tv_success(self, mock_env, temp_db, mock_httpx):
        """Verify that add_tv works correctly."""
        with patch("yuna.providers.animeworld.client.httpx", mock_httpx):
            from yuna.providers.animeworld.client import Airi

            airi = Airi(db_path=temp_db)
            airi.add_tv(
                name="Test TV Show",
                link="https://streamingsite.com/tv/test-show",
                last_update="2024-01-15 10:30:00",
                numero_episodi=10,
            )

            tv_list = airi.get_tv()
            assert len(tv_list) == 1
            assert tv_list[0]["name"] == "Test TV Show"


class TestAiriMovieOperations:
    """Tests for movie operations through Airi."""

    def test_get_movies_empty(self, mock_env, temp_db, mock_httpx):
        """Verify that get_movies returns empty list for new database."""
        with patch("yuna.providers.animeworld.client.httpx", mock_httpx):
            from yuna.providers.animeworld.client import Airi

            airi = Airi(db_path=temp_db)
            movies_list = airi.get_movies()

            assert movies_list == []

    def test_add_movie_success(self, mock_env, temp_db, mock_httpx):
        """Verify that add_movie works correctly."""
        with patch("yuna.providers.animeworld.client.httpx", mock_httpx):
            from yuna.providers.animeworld.client import Airi

            airi = Airi(db_path=temp_db)
            airi.add_movie(
                name="Test Movie",
                link="https://streamingsite.com/movie/test-movie",
                last_update="2024-01-15 10:30:00",
            )

            movies_list = airi.get_movies()
            assert len(movies_list) == 1
            assert movies_list[0]["name"] == "Test Movie"


class TestAiriLegacyMethods:
    """Tests for backward compatibility methods."""

    def test_load_or_create_config(self, mock_env, temp_db, mock_httpx):
        """Verify that load_or_create_config returns database data."""
        with patch("yuna.providers.animeworld.client.httpx", mock_httpx):
            from yuna.providers.animeworld.client import Airi

            airi = Airi(db_path=temp_db)

            # Add some data
            airi.add_anime(
                name="Test Anime",
                link="/play/test.12345",
                last_update="2024-01-15 10:30:00",
                numero_episodi=12,
            )

            config = airi.load_or_create_config()

            assert "anime" in config
            assert "tv" in config
            assert "movies" in config
            assert len(config["anime"]) == 1

    def test_invalidate_config_no_error(self, mock_env, temp_db, mock_httpx):
        """Verify that invalidate_config runs without error."""
        with patch("yuna.providers.animeworld.client.httpx", mock_httpx):
            from yuna.providers.animeworld.client import Airi

            airi = Airi(db_path=temp_db)

            # Should not raise any exception
            airi.invalidate_config()


class TestAnimeWorldURLFetching:
    """Tests for AnimeWorld URL auto-detection."""

    def test_get_animeworld_url_success(self, mock_httpx, mock_env, temp_db):
        """Verify that AnimeWorld URL is fetched automatically."""
        with patch("yuna.providers.animeworld.client.httpx", mock_httpx):
            from yuna.providers.animeworld.client import get_animeworld_url, Airi

            # Reset cache
            from yuna.providers.animeworld import client as airi
            airi._animeworld_url_cache = None

            url = get_animeworld_url()
            assert url == "https://www.animeworld.ac"

    def test_get_animeworld_url_caching(self, mock_httpx, mock_env, temp_db):
        """Verify that AnimeWorld URL is cached."""
        with patch("yuna.providers.animeworld.client.httpx", mock_httpx):
            from yuna.providers.animeworld.client import get_animeworld_url
            from yuna.providers.animeworld import client as airi

            # Reset cache
            airi._animeworld_url_cache = None

            # First call
            url1 = get_animeworld_url()

            # Modify mock to verify caching
            mock_httpx.get.return_value.url = "https://different-url.com"

            # Second call should return cached value
            url2 = get_animeworld_url()

            assert url1 == url2, "Cached URL should be returned"

    def test_get_animeworld_url_fallback(self, monkeypatch, mock_env, temp_db):
        """Verify that fallback URL is used when all requests fail."""
        from yuna.providers.animeworld import client as airi
        airi._animeworld_url_cache = None

        mock_httpx = MagicMock()
        mock_httpx.get.side_effect = Exception("Network error")

        with patch("yuna.providers.animeworld.client.httpx", mock_httpx):
            from yuna.providers.animeworld.client import get_animeworld_url

            url = get_animeworld_url()
            assert url == "https://www.animeworld.ac", "Should use fallback URL"
