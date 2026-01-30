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

# Add src directory to path for imports
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_project_root, 'src'))
sys.path.insert(0, _project_root)  # Keep for backward compatibility


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
def mock_env(monkeypatch, tmp_path) -> Dict[str, str]:
    """
    Mocks environment variables required by the YUNA-System.

    Sets up:
        - TELEGRAM_TOKEN: Mock Telegram bot token
        - TELEGRAM_CHAT_ID: Mock authorized user ID
        - DESTINATION_FOLDER: Temporary folder for downloads
        - UPDATE_TIME: Update interval in seconds
        - BASE_URL_SC: Mock streaming URL
        - DATABASE_PATH: Temporary database path

    Also patches load_dotenv to prevent loading from .env file.

    Returns:
        Dict[str, str]: Dictionary of mocked environment variables.
    """
    db_path = str(tmp_path / "test_yuna.db")
    download_folder = str(tmp_path / "downloads")
    movies_folder = str(tmp_path / "downloads" / "movies")
    series_folder = str(tmp_path / "downloads" / "series")
    os.makedirs(download_folder, exist_ok=True)
    os.makedirs(movies_folder, exist_ok=True)
    os.makedirs(series_folder, exist_ok=True)

    env_vars = {
        "TELEGRAM_TOKEN": "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz",
        "TELEGRAM_CHAT_ID": "123456789",
        "DESTINATION_FOLDER": download_folder,
        "MOVIES_FOLDER": movies_folder,
        "SERIES_FOLDER": series_folder,
        "UPDATE_TIME": "60",
        "BASE_URL_SC": "https://test.streamingunity.shop",
        "DATABASE_PATH": db_path,
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
    with patch("yuna.services.media_service.aw") as mock_aw:
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
    with patch("yuna.providers.animeworld.client.httpx") as mock:
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
    from yuna.providers.animeworld import client as airi_client
    airi_client._animeworld_url_cache = None
    yield
    airi_client._animeworld_url_cache = None


@pytest.fixture(autouse=True)
def cleanup_default_db(tmp_path, monkeypatch):
    """
    Sets DATABASE_PATH to a temporary location and cleans up after tests.

    This prevents tests from trying to create /data/yuna.db which requires
    root permissions.
    """
    import os

    # Set DATABASE_PATH to temp location BEFORE any imports
    db_path = str(tmp_path / "test_yuna.db")
    monkeypatch.setenv("DATABASE_PATH", db_path)

    # Also set DESTINATION_FOLDER to temp
    download_folder = str(tmp_path / "downloads")
    os.makedirs(download_folder, exist_ok=True)
    monkeypatch.setenv("DESTINATION_FOLDER", download_folder)

    # Reload database module to pick up new env var
    from yuna.data import database
    database.DEFAULT_DB_PATH = db_path

    yield

    # Cleanup
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture
def mock_requests():
    """
    Mocks requests library for testing HTTP operations.

    Yields:
        MagicMock: Mocked requests module.
    """
    with patch("yuna.services.media_service.requests") as mock:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_content.return_value = [b"fake_image_data"]
        mock_response.raise_for_status = MagicMock()
        mock.get.return_value = mock_response
        yield mock


# ==================== STREAMINGCOMMUNITY FIXTURES ====================

@pytest.fixture
def sample_sc_series_data() -> Dict[str, Any]:
    """
    Provides sample StreamingCommunity TV series data for testing.

    Returns:
        Dict containing sample series information with SC-specific fields.
    """
    return {
        "name": "Breaking Bad",
        "link": "https://streamingcommunity.computer/it/titles/123-breaking-bad",
        "last_update": "2024-01-15 10:30:00",
        "episodi_scaricati": 10,
        "numero_episodi": 62,
        "provider": "streamingcommunity",
        "slug": "breaking-bad",
        "media_id": 123,
        "provider_language": "it",
        "year": "2008",
        "seasons_data": '{"1": {"total": 7, "downloaded": [1, 2, 3]}}',
    }


@pytest.fixture
def sample_sc_movie_data() -> Dict[str, Any]:
    """
    Provides sample StreamingCommunity movie data for testing.

    Returns:
        Dict containing sample movie information with SC-specific fields.
    """
    return {
        "name": "The Matrix",
        "link": "https://streamingcommunity.computer/it/titles/456-the-matrix",
        "last_update": "2024-01-20 14:00:00",
        "provider": "streamingcommunity",
        "slug": "the-matrix",
        "media_id": 456,
        "provider_language": "it",
        "year": "1999",
    }


@pytest.fixture
def mock_streamingcommunity():
    """
    Mocks the StreamingCommunity client for testing without network calls.

    Yields:
        MagicMock: Mocked StreamingCommunity module components.
    """
    with patch("yuna.providers.streamingcommunity.client.httpx") as mock_httpx:
        # Mock HTTP client
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
        <div id="app" data-page='{"version": "abc123", "props": {"titles": []}}'>
        </div>
        </html>
        """
        mock_response.json.return_value = {
            "props": {
                "titles": [
                    {
                        "id": 123,
                        "name": "Test Series",
                        "slug": "test-series",
                        "type": "tv",
                        "images": [],
                        "translations": [{"key": "release_date", "value": "2020-01-01"}],
                    }
                ]
            }
        }
        mock_client.get.return_value = mock_response
        mock_httpx.Client.return_value = mock_client

        yield mock_httpx


@pytest.fixture
def mock_sc_media_item():
    """
    Creates a sample MediaItem for testing.

    Returns:
        MediaItem: A sample media item object.
    """
    from yuna.providers.streamingcommunity.client import MediaItem

    return MediaItem(
        id=123,
        name="Test Series",
        slug="test-series",
        type="tv",
        year="2020",
        image=None,
        provider_language="it"
    )


@pytest.fixture
def mock_sc_series_info():
    """
    Creates a sample SeriesInfo for testing.

    Returns:
        SeriesInfo: A sample series info object with seasons.
    """
    from yuna.providers.streamingcommunity.client import SeriesInfo, Season, Episode

    season1 = Season(id=1, number=1, name="Season 1", slug="season-1")
    season1.episodes = [
        Episode(id=101, number=1, name="Pilot"),
        Episode(id=102, number=2, name="Episode 2"),
        Episode(id=103, number=3, name="Episode 3"),
    ]

    season2 = Season(id=2, number=2, name="Season 2", slug="season-2")
    season2.episodes = [
        Episode(id=201, number=1, name="Season 2 Premiere"),
        Episode(id=202, number=2, name="Episode 2"),
    ]

    return SeriesInfo(
        id=123,
        name="Test Series",
        slug="test-series",
        year="2020",
        plot="A test series for unit testing.",
        seasons=[season1, season2]
    )


@pytest.fixture
def series_folder_with_episodes(tmp_path) -> str:
    """
    Creates a temporary series folder with sample episode files.

    Returns:
        str: Path to the series folder with episodes.
    """
    series_folder = tmp_path / "Test Series" / "S01"
    series_folder.mkdir(parents=True, exist_ok=True)

    # Create sample episode files
    for ep_num in [1, 2, 3]:
        episode_file = series_folder / f"Test Series - S01E0{ep_num} - Episode {ep_num}.mp4"
        episode_file.touch()

    return str(tmp_path / "Test Series")


@pytest.fixture
def mock_miko_sc_database(temp_db, monkeypatch):
    """
    Patches MikoSC to use a temporary database.

    This prevents MikoSC from trying to create /data/yuna.db.
    """
    monkeypatch.setenv("DATABASE_PATH", temp_db)

    with patch("yuna.services.media_service.Database") as mock_db:
        # Create mock database with all required methods
        mock_instance = MagicMock()
        mock_instance.get_all_tv.return_value = []
        mock_instance.get_all_movies.return_value = []
        mock_instance.get_tv_by_name.return_value = None
        mock_instance.get_movie_by_name.return_value = None
        mock_instance.add_tv.return_value = True
        mock_instance.add_movie.return_value = True
        mock_instance.remove_tv.return_value = True
        mock_instance.remove_movie.return_value = True
        mock_db.return_value = mock_instance
        yield mock_instance
