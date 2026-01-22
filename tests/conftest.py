"""
Pytest configuration and fixtures for YUNA-System tests.

This module provides reusable fixtures for database testing, environment mocking,
temporary file operations, and sample data generation.
"""

import os
import sys
import tempfile
import shutil
from datetime import datetime
from typing import Dict, Any, Generator
from unittest.mock import patch, MagicMock

import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def temp_db(tmp_path) -> Generator[str, None, None]:
    """
    Creates a temporary SQLite database file for testing.

    The database is automatically cleaned up after the test completes.

    Yields:
        str: Path to the temporary database file.
    """
    db_path = tmp_path / "test_yuna.db"
    yield str(db_path)
    # Cleanup is automatic with tmp_path


@pytest.fixture
def mock_env(monkeypatch) -> Dict[str, str]:
    """
    Mocks environment variables required by the YUNA-System.

    Sets up:
        - TELEGRAM_TOKEN: Mock Telegram bot token
        - TELEGRAM_CHAT_ID: Mock authorized user ID
        - DESTINATION_FOLDER: Temporary folder for downloads
        - UPDATE_TIME: Update interval in seconds
        - BASE_URL_SC: Mock streaming URL

    Also patches load_dotenv to prevent loading from .env file.

    Returns:
        Dict[str, str]: Dictionary of mocked environment variables.
    """
    env_vars = {
        "TELEGRAM_TOKEN": "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz",
        "TELEGRAM_CHAT_ID": "123456789",
        "DESTINATION_FOLDER": "/tmp/yuna_test_downloads",
        "UPDATE_TIME": "60",
        "BASE_URL_SC": "https://test.streamingunity.shop",
    }

    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

    return env_vars


@pytest.fixture
def temp_download_folder(tmp_path) -> Generator[str, None, None]:
    """
    Creates a temporary folder for download operations.

    This fixture creates a clean temporary directory that simulates
    the anime download destination folder.

    Yields:
        str: Path to the temporary download folder.
    """
    download_folder = tmp_path / "downloads"
    download_folder.mkdir(parents=True, exist_ok=True)
    yield str(download_folder)
    # Cleanup is automatic with tmp_path


@pytest.fixture
def sample_anime_data() -> Dict[str, Any]:
    """
    Provides sample anime data for testing.

    Returns:
        Dict[str, Any]: A dictionary containing sample anime information
        with all required fields for database operations.
    """
    return {
        "name": "Test Anime",
        "link": "/play/test-anime.12345",
        "last_update": "2024-01-15 10:30:00",
        "episodi_scaricati": 5,
        "numero_episodi": 12,
    }


@pytest.fixture
def sample_anime_list() -> list:
    """
    Provides a list of sample anime data for batch testing.

    Returns:
        list: List of dictionaries with anime information.
    """
    return [
        {
            "name": "Anime One",
            "link": "/play/anime-one.11111",
            "last_update": "2024-01-10 08:00:00",
            "episodi_scaricati": 10,
            "numero_episodi": 24,
        },
        {
            "name": "Anime Two",
            "link": "/play/anime-two.22222",
            "last_update": "2024-01-12 14:30:00",
            "episodi_scaricati": 3,
            "numero_episodi": 12,
        },
        {
            "name": "Anime Three",
            "link": "/play/anime-three.33333",
            "last_update": "2024-01-14 20:00:00",
            "episodi_scaricati": 0,
            "numero_episodi": 6,
        },
    ]


@pytest.fixture
def sample_tv_data() -> Dict[str, Any]:
    """
    Provides sample TV show data for testing.

    Returns:
        Dict[str, Any]: A dictionary containing sample TV show information.
    """
    return {
        "name": "Test TV Show",
        "link": "/play/test-tv-show.67890",
        "last_update": "2024-01-16 15:45:00",
        "episodi_scaricati": 8,
        "numero_episodi": 10,
    }


@pytest.fixture
def sample_movie_data() -> Dict[str, Any]:
    """
    Provides sample movie data for testing.

    Returns:
        Dict[str, Any]: A dictionary containing sample movie information.
    """
    return {
        "name": "Test Movie",
        "link": "/play/test-movie.99999",
        "last_update": "2024-01-17 12:00:00",
        "scaricato": 1,
    }


@pytest.fixture
def sample_config_json(tmp_path) -> str:
    """
    Creates a sample config.json file for migration testing.

    Args:
        tmp_path: Pytest's temporary path fixture.

    Returns:
        str: Path to the created config.json file.
    """
    import json

    config_data = {
        "anime": [
            {
                "name": "Migration Anime 1",
                "link": "/play/migration-anime-1.11111",
                "last_update": "2024-01-01 00:00:00",
                "episodi_scaricati": 5,
                "numero_episodi": 10,
            },
            {
                "name": "Migration Anime 2",
                "link": "/play/migration-anime-2.22222",
                "last_update": "2024-01-02 00:00:00",
                "episodi_scaricati": 12,
                "numero_episodi": 24,
            },
        ],
        "tv": [
            {
                "name": "Migration TV 1",
                "link": "/play/migration-tv-1.33333",
                "last_update": "2024-01-03 00:00:00",
                "episodi_scaricati": 3,
                "numero_episodi": 8,
            },
        ],
        "movies": [
            {
                "name": "Migration Movie 1",
                "link": "/play/migration-movie-1.44444",
                "last_update": "2024-01-04 00:00:00",
                "scaricato": True,
            },
        ],
    }

    config_path = tmp_path / "config.json"
    with open(config_path, "w") as f:
        json.dump(config_data, f)

    return str(config_path)


@pytest.fixture
def mock_animeworld():
    """
    Mocks the animeworld library for testing without network calls.

    Provides mock implementations for:
        - Anime class with getName, getEpisodes, getCover methods
        - find function for searching anime
        - Episode objects with download capabilities

    Yields:
        MagicMock: Mocked animeworld module.
    """
    with patch("miko.aw") as mock_aw:
        # Mock Anime class
        mock_anime = MagicMock()
        mock_anime.getName.return_value = "Test Anime"
        mock_anime.getCover.return_value = "https://example.com/cover.jpg"

        # Mock Episode objects
        mock_episode_1 = MagicMock()
        mock_episode_1.number = 1
        mock_episode_1.fileInfo.return_value = {"last_modified": "2024-01-15 10:30:00"}
        mock_episode_1.download.return_value = None

        mock_episode_2 = MagicMock()
        mock_episode_2.number = 2
        mock_episode_2.fileInfo.return_value = {"last_modified": "2024-01-16 10:30:00"}
        mock_episode_2.download.return_value = None

        mock_anime.getEpisodes.return_value = [mock_episode_1, mock_episode_2]

        mock_aw.Anime.return_value = mock_anime
        mock_aw.find.return_value = [
            {"name": "Test Anime", "link": "https://animeworld.tv/play/test-anime.12345"},
            {"name": "Test Anime 2", "link": "https://animeworld.tv/play/test-anime-2.67890"},
        ]

        # Mock SES object for base_url
        mock_aw.SES = MagicMock()
        mock_aw.SES.base_url = "https://www.animeworld.ac"

        yield mock_aw


@pytest.fixture
def mock_telegram_update():
    """
    Creates a mock Telegram Update object for testing bot handlers.

    Returns:
        MagicMock: Mocked Update object with message and user data.
    """
    update = MagicMock()
    update.message = MagicMock()
    update.message.from_user = MagicMock()
    update.message.from_user.id = 123456789
    update.message.text = "Test message"
    update.message.reply_text = MagicMock()
    update.effective_user = MagicMock()
    update.effective_user.id = 123456789
    update.callback_query = MagicMock()
    update.callback_query.from_user = MagicMock()
    update.callback_query.from_user.id = 123456789
    update.callback_query.data = "test_callback"
    update.callback_query.answer = MagicMock()
    update.callback_query.edit_message_text = MagicMock()
    update.callback_query.edit_message_reply_markup = MagicMock()
    return update


@pytest.fixture
def mock_telegram_context():
    """
    Creates a mock Telegram Context object for testing bot handlers.

    Returns:
        MagicMock: Mocked ContextTypes.DEFAULT_TYPE object.
    """
    context = MagicMock()
    context.bot = MagicMock()
    context.bot.send_message = MagicMock()
    context.application = MagicMock()
    context.application.job_queue = MagicMock()
    context.application.job_queue.run_once = MagicMock()
    context.error = None
    return context


@pytest.fixture
def mock_httpx():
    """
    Mocks httpx for testing URL fetching without network calls.

    Yields:
        MagicMock: Mocked httpx module.
    """
    with patch("airi.httpx") as mock:
        mock_response = MagicMock()
        mock_response.url = "https://www.animeworld.ac"
        mock.get.return_value = mock_response
        yield mock


@pytest.fixture
def anime_folder_with_episodes(tmp_path) -> str:
    """
    Creates a temporary anime folder with sample episode files.

    This simulates an existing anime folder with downloaded episodes
    for testing episode counting and missing episode detection.

    Args:
        tmp_path: Pytest's temporary path fixture.

    Returns:
        str: Path to the anime folder with episodes.
    """
    anime_folder = tmp_path / "Test Anime"
    anime_folder.mkdir(parents=True, exist_ok=True)

    # Create sample episode files
    for ep_num in [1, 2, 3, 5, 7]:  # Missing 4 and 6
        episode_file = anime_folder / f"Test Anime - Episode {ep_num}.mp4"
        episode_file.touch()

    # Create cover file
    cover_file = anime_folder / "folder.jpg"
    cover_file.touch()

    return str(anime_folder)


@pytest.fixture(autouse=True)
def reset_animeworld_cache():
    """
    Resets the AnimeWorld URL cache before each test.

    This ensures tests don't interfere with each other through
    the global cache variable.
    """
    import airi
    airi._animeworld_url_cache = None
    yield
    airi._animeworld_url_cache = None


@pytest.fixture(autouse=True)
def cleanup_default_db():
    """
    Removes the default yuna.db file before each test to ensure test isolation.

    This prevents tests from interfering with each other through
    the shared default database file.
    """
    import os
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "yuna.db")
    if os.path.exists(db_path):
        os.remove(db_path)
    yield
    # Also cleanup after test
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture
def mock_requests():
    """
    Mocks requests library for testing HTTP operations.

    Yields:
        MagicMock: Mocked requests module.
    """
    with patch("miko.requests") as mock:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_content.return_value = [b"fake_image_data"]
        mock_response.raise_for_status = MagicMock()
        mock.get.return_value = mock_response
        yield mock
