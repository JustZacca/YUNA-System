"""
Tests for miko.py - Media Indexing and Kapturing Operator for YUNA-System.

This module tests:
    - Miko initialization
    - Name normalization
    - Folder setup and creation
    - Episode download with mocked animeworld
    - Missing episode detection
    - Episode counting and updates
"""

import os
import sys
import asyncio
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestMikoInitialization:
    """Tests for Miko class initialization."""

    def test_miko_initialization(self, mock_env, temp_db, mock_httpx):
        """Verify that Miko initializes with correct default values."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()

                from miko import Miko

                miko = Miko()

                assert miko.name == "Miko"
                assert miko.version == "1.0.0"
                assert miko.anime is None
                assert miko.anime_folder is None
                assert miko.anime_name is None

    def test_miko_has_download_semaphore(self, mock_env, temp_db, mock_httpx):
        """Verify that Miko has a download semaphore for parallel downloads."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()

                from miko import Miko

                miko = Miko()

                assert miko.download_semaphore is not None
                assert isinstance(miko.download_semaphore, asyncio.Semaphore)


class TestNormalizeName:
    """Tests for the normalize_name method."""

    def test_normalize_name_removes_special_chars(self, mock_env, temp_db, mock_httpx):
        """Verify that normalize_name removes special characters."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()

                from miko import Miko

                miko = Miko()

                result = miko.normalize_name("Test-Anime_Name!")
                assert result == "testanimename"

    def test_normalize_name_converts_to_lowercase(self, mock_env, temp_db, mock_httpx):
        """Verify that normalize_name converts to lowercase."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()

                from miko import Miko

                miko = Miko()

                result = miko.normalize_name("UPPERCASE NAME")
                assert result == "uppercasename"

    def test_normalize_name_preserves_alphanumeric(self, mock_env, temp_db, mock_httpx):
        """Verify that normalize_name preserves alphanumeric characters."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()

                from miko import Miko

                miko = Miko()

                result = miko.normalize_name("Anime123")
                assert result == "anime123"

    def test_normalize_name_handles_spaces(self, mock_env, temp_db, mock_httpx):
        """Verify that normalize_name removes spaces."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()

                from miko import Miko

                miko = Miko()

                result = miko.normalize_name("Test Anime Name")
                assert result == "testanimename"


class TestSetupAnimeFolder:
    """Tests for setupAnimeFolder method."""

    @pytest.mark.asyncio
    async def test_setup_anime_folder_creates_directory(
        self, mock_env, temp_db, temp_download_folder, mock_httpx, monkeypatch
    ):
        """Verify that setupAnimeFolder creates the anime directory."""
        monkeypatch.setenv("DESTINATION_FOLDER", temp_download_folder)

        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()

                # Mock anime object
                mock_anime = MagicMock()
                mock_anime.getName.return_value = "Test Anime"
                mock_anime.getCover.return_value = "https://example.com/cover.jpg"

                from miko import Miko

                miko = Miko()
                miko.anime = mock_anime
                miko.anime_name = "Test Anime"

                # Mock requests for cover download
                with patch("miko.requests") as mock_requests:
                    mock_response = MagicMock()
                    mock_response.status_code = 200
                    mock_response.iter_content.return_value = [b"fake_image"]
                    mock_response.raise_for_status = MagicMock()
                    mock_requests.get.return_value = mock_response

                    result = await miko.setupAnimeFolder()

                expected_folder = os.path.join(temp_download_folder, "Test Anime")
                assert os.path.exists(expected_folder), "Anime folder should be created"
                assert result is True

    @pytest.mark.asyncio
    async def test_setup_anime_folder_returns_false_no_anime(
        self, mock_env, temp_db, mock_httpx
    ):
        """Verify that setupAnimeFolder returns False when no anime is loaded."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()

                from miko import Miko

                miko = Miko()
                result = await miko.setupAnimeFolder()

                assert result is False

    @pytest.mark.asyncio
    async def test_setup_anime_folder_existing_folder(
        self, mock_env, temp_db, temp_download_folder, mock_httpx, monkeypatch
    ):
        """Verify that setupAnimeFolder handles existing folder."""
        monkeypatch.setenv("DESTINATION_FOLDER", temp_download_folder)

        # Pre-create the folder
        existing_folder = os.path.join(temp_download_folder, "Existing Anime")
        os.makedirs(existing_folder, exist_ok=True)

        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()

                mock_anime = MagicMock()
                mock_anime.getName.return_value = "Existing Anime"

                from miko import Miko

                miko = Miko()
                miko.anime = mock_anime
                miko.anime_name = "Existing Anime"

                result = await miko.setupAnimeFolder()

                assert result is True
                assert os.path.exists(existing_folder)


class TestDownloadEpisodes:
    """Tests for downloadEpisodes method with mocked animeworld."""

    @pytest.mark.asyncio
    async def test_download_episodes_success(
        self, mock_env, temp_db, temp_download_folder, mock_httpx, monkeypatch
    ):
        """Verify that downloadEpisodes downloads episodes with parallel semaphore."""
        monkeypatch.setenv("DESTINATION_FOLDER", temp_download_folder)

        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()

                # Create mock episodes
                mock_ep1 = MagicMock()
                mock_ep1.number = 1
                mock_ep1.download = MagicMock(return_value=None)
                mock_ep1.fileInfo.return_value = {"last_modified": "2024-01-15 10:30:00"}

                mock_ep2 = MagicMock()
                mock_ep2.number = 2
                mock_ep2.download = MagicMock(return_value=None)
                mock_ep2.fileInfo.return_value = {"last_modified": "2024-01-16 10:30:00"}

                mock_anime = MagicMock()
                mock_anime.getName.return_value = "Test Anime"
                mock_anime.getEpisodes.return_value = [mock_ep1, mock_ep2]

                from miko import Miko

                miko = Miko()
                miko.anime = mock_anime
                miko.anime_name = "Test Anime"
                miko.anime_folder = os.path.join(temp_download_folder, "Test Anime")

                # Create anime folder
                os.makedirs(miko.anime_folder, exist_ok=True)

                result = await miko.downloadEpisodes([1, 2])

                # Downloads should have been called
                assert mock_anime.getEpisodes.called

    @pytest.mark.asyncio
    async def test_download_episodes_no_anime_loaded(self, mock_env, temp_db, mock_httpx):
        """Verify that downloadEpisodes returns False when no anime is loaded."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()

                from miko import Miko

                miko = Miko()
                result = await miko.downloadEpisodes([1, 2, 3])

                assert result is False

    @pytest.mark.asyncio
    async def test_download_episodes_semaphore_limits_parallel(
        self, mock_env, temp_db, temp_download_folder, mock_httpx, monkeypatch
    ):
        """Verify that download semaphore limits parallel downloads to 3."""
        monkeypatch.setenv("DESTINATION_FOLDER", temp_download_folder)

        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()

                concurrent_downloads = []
                max_concurrent = [0]

                async def track_concurrent(*args, **kwargs):
                    concurrent_downloads.append(1)
                    current = len(concurrent_downloads)
                    max_concurrent[0] = max(max_concurrent[0], current)
                    await asyncio.sleep(0.1)  # Simulate download time
                    concurrent_downloads.pop()

                # Create 5 mock episodes
                mock_episodes = []
                for i in range(1, 6):
                    mock_ep = MagicMock()
                    mock_ep.number = i
                    mock_ep.download = MagicMock(return_value=None)
                    mock_ep.fileInfo.return_value = {"last_modified": "2024-01-15 10:30:00"}
                    mock_episodes.append(mock_ep)

                mock_anime = MagicMock()
                mock_anime.getName.return_value = "Test Anime"
                mock_anime.getEpisodes.return_value = mock_episodes

                from miko import Miko

                miko = Miko()
                miko.anime = mock_anime
                miko.anime_name = "Test Anime"
                miko.anime_folder = os.path.join(temp_download_folder, "Test Anime")
                os.makedirs(miko.anime_folder, exist_ok=True)

                # Verify semaphore is configured for max 3 concurrent
                assert miko.download_semaphore._value == 3


class TestGetMissingEpisodes:
    """Tests for getMissingEpisodes method."""

    @pytest.mark.asyncio
    async def test_get_missing_episodes_detects_missing(
        self, mock_env, temp_db, anime_folder_with_episodes, mock_httpx, monkeypatch
    ):
        """Verify that getMissingEpisodes correctly identifies missing episodes."""
        # Set destination folder to parent of anime_folder_with_episodes
        parent_folder = os.path.dirname(anime_folder_with_episodes)
        monkeypatch.setenv("DESTINATION_FOLDER", parent_folder)

        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()

                # Create mock episodes (1-7)
                mock_episodes = []
                for i in range(1, 8):
                    mock_ep = MagicMock()
                    mock_ep.number = str(i)
                    mock_episodes.append(mock_ep)

                mock_anime = MagicMock()
                mock_anime.getName.return_value = "Test Anime"
                mock_anime.getEpisodes.return_value = mock_episodes

                from miko import Miko

                miko = Miko()
                miko.anime = mock_anime
                miko.anime_name = "Test Anime"
                miko.anime_folder = anime_folder_with_episodes

                missing = await miko.getMissingEpisodes()

                # Folder has episodes 1, 2, 3, 5, 7 - missing 4 and 6
                assert 4 in missing
                assert 6 in missing
                assert 1 not in missing
                assert 2 not in missing

    @pytest.mark.asyncio
    async def test_get_missing_episodes_no_anime(self, mock_env, temp_db, mock_httpx):
        """Verify that getMissingEpisodes returns empty list when no anime loaded."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()

                from miko import Miko

                miko = Miko()
                missing = await miko.getMissingEpisodes()

                assert missing == []

    @pytest.mark.asyncio
    async def test_get_missing_episodes_handles_decimal_numbers(
        self, mock_env, temp_db, temp_download_folder, mock_httpx, monkeypatch
    ):
        """Verify that getMissingEpisodes handles decimal episode numbers."""
        monkeypatch.setenv("DESTINATION_FOLDER", temp_download_folder)

        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()

                # Create mock episodes with decimal numbers
                mock_episodes = []
                for num in ["1", "2", "2.5", "3"]:
                    mock_ep = MagicMock()
                    mock_ep.number = num
                    mock_episodes.append(mock_ep)

                mock_anime = MagicMock()
                mock_anime.getName.return_value = "Test Anime"
                mock_anime.getEpisodes.return_value = mock_episodes

                from miko import Miko

                miko = Miko()
                miko.anime = mock_anime
                miko.anime_name = "Test Anime"
                miko.anime_folder = os.path.join(temp_download_folder, "Test Anime")
                os.makedirs(miko.anime_folder, exist_ok=True)

                # Create episode 1 file
                ep1_file = os.path.join(miko.anime_folder, "Test Anime - Episode 1.mp4")
                with open(ep1_file, "w") as f:
                    f.write("")

                missing = await miko.getMissingEpisodes()

                # Episode 1 exists, 2 and 3 are missing (2.5 truncated to 2)
                assert 1 not in missing
                assert 2 in missing or 3 in missing


class TestCountAndUpdateEpisodes:
    """Tests for count_and_update_episodes method."""

    def test_count_and_update_episodes_success(
        self, mock_env, temp_db, anime_folder_with_episodes, mock_httpx, monkeypatch
    ):
        """Verify that count_and_update_episodes counts and updates correctly."""
        parent_folder = os.path.dirname(anime_folder_with_episodes)
        monkeypatch.setenv("DESTINATION_FOLDER", parent_folder)

        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()

                from miko import Miko

                miko = Miko()

                # anime_folder_with_episodes has episodes 1, 2, 3, 5, 7 (5 episodes)
                result = miko.count_and_update_episodes("Test Anime", 3)

                assert result is True

    def test_count_and_update_episodes_folder_not_exists(
        self, mock_env, temp_db, mock_httpx
    ):
        """Verify that count_and_update_episodes returns False for missing folder."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()

                from miko import Miko

                miko = Miko()
                result = miko.count_and_update_episodes("Non Existent Anime", 0)

                assert result is False

    def test_count_and_update_episodes_already_updated(
        self, mock_env, temp_db, anime_folder_with_episodes, mock_httpx, monkeypatch
    ):
        """Verify that count_and_update_episodes skips update when counts match."""
        parent_folder = os.path.dirname(anime_folder_with_episodes)
        monkeypatch.setenv("DESTINATION_FOLDER", parent_folder)

        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()

                from miko import Miko

                miko = Miko()

                # anime_folder_with_episodes has 5 episodes
                result = miko.count_and_update_episodes("Test Anime", 5)

                assert result is True


class TestLoadAnime:
    """Tests for loadAnime method."""

    @pytest.mark.asyncio
    async def test_load_anime_success(
        self, mock_env, temp_db, temp_download_folder, mock_httpx, monkeypatch
    ):
        """Verify that loadAnime loads anime correctly."""
        monkeypatch.setenv("DESTINATION_FOLDER", temp_download_folder)

        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()

                mock_anime = MagicMock()
                mock_anime.getName.return_value = "Loaded Anime"
                mock_anime.getCover.return_value = "https://example.com/cover.jpg"
                mock_aw.Anime.return_value = mock_anime

                from miko import Miko

                miko = Miko()

                with patch("miko.requests") as mock_requests:
                    mock_response = MagicMock()
                    mock_response.iter_content.return_value = [b"image"]
                    mock_response.raise_for_status = MagicMock()
                    mock_requests.get.return_value = mock_response

                    result = await miko.loadAnime("/play/test-anime")

                assert result is not None
                assert miko.anime_name == "Loaded Anime"

    @pytest.mark.asyncio
    async def test_load_anime_failure(self, mock_env, temp_db, mock_httpx):
        """Verify that loadAnime handles errors gracefully."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()
                mock_aw.Anime.side_effect = Exception("Network error")

                from miko import Miko

                miko = Miko()
                result = await miko.loadAnime("/play/invalid-anime")

                assert result is None
                assert miko.anime is None


class TestFindAnime:
    """Tests for findAnime method."""

    def test_find_anime_success(self, mock_env, temp_db, mock_httpx):
        """Verify that findAnime returns search results."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()
                mock_aw.find.return_value = [
                    {"name": "Found Anime 1", "link": "/play/found-1"},
                    {"name": "Found Anime 2", "link": "/play/found-2"},
                ]

                from miko import Miko

                miko = Miko()
                results = miko.findAnime("search term")

                assert len(results) == 2
                assert results[0]["name"] == "Found Anime 1"
                assert results[1]["link"] == "/play/found-2"

    def test_find_anime_no_results(self, mock_env, temp_db, mock_httpx):
        """Verify that findAnime returns empty list when nothing found."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()
                mock_aw.find.return_value = []

                from miko import Miko

                miko = Miko()
                results = miko.findAnime("nonexistent anime")

                assert results == []

    def test_find_anime_handles_exception(self, mock_env, temp_db, mock_httpx):
        """Verify that findAnime handles exceptions gracefully."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()
                mock_aw.find.side_effect = Exception("Search error")

                from miko import Miko

                miko = Miko()
                results = miko.findAnime("search term")

                assert results == []


class TestAddAnime:
    """Tests for addAnime method."""

    @pytest.mark.asyncio
    async def test_add_anime_success(
        self, mock_env, temp_db, temp_download_folder, mock_httpx, monkeypatch
    ):
        """Verify that addAnime adds anime to configuration."""
        monkeypatch.setenv("DESTINATION_FOLDER", temp_download_folder)

        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()

                mock_episode = MagicMock()
                mock_episode.number = 1
                mock_episode.fileInfo.return_value = {"last_modified": "2024-01-15 10:30:00"}

                mock_anime = MagicMock()
                mock_anime.getName.return_value = "Added Anime"
                mock_anime.getCover.return_value = "https://example.com/cover.jpg"
                mock_anime.getEpisodes.return_value = [mock_episode]
                mock_aw.Anime.return_value = mock_anime

                from miko import Miko

                miko = Miko()

                with patch("miko.requests") as mock_requests:
                    mock_response = MagicMock()
                    mock_response.iter_content.return_value = [b"image"]
                    mock_response.raise_for_status = MagicMock()
                    mock_requests.get.return_value = mock_response

                    result = await miko.addAnime("https://animeworld.tv/play/added-anime")

                assert result == "Added Anime"

    @pytest.mark.asyncio
    async def test_add_anime_failure_load(self, mock_env, temp_db, mock_httpx):
        """Verify that addAnime returns None when loading fails."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()
                mock_aw.Anime.side_effect = Exception("Load error")

                from miko import Miko

                miko = Miko()
                result = await miko.addAnime("https://animeworld.tv/play/invalid")

                assert result is None


class TestGetEpisodes:
    """Tests for getEpisodes method."""

    @pytest.mark.asyncio
    async def test_get_episodes_success(self, mock_env, temp_db, mock_httpx):
        """Verify that getEpisodes returns episode list."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()

                mock_ep1 = MagicMock()
                mock_ep1.number = 1
                mock_ep2 = MagicMock()
                mock_ep2.number = 2

                mock_anime = MagicMock()
                mock_anime.getName.return_value = "Test Anime"
                mock_anime.getEpisodes.return_value = [mock_ep1, mock_ep2]

                from miko import Miko

                miko = Miko()
                miko.anime = mock_anime

                episodes = await miko.getEpisodes()

                assert len(episodes) == 2

    @pytest.mark.asyncio
    async def test_get_episodes_no_anime(self, mock_env, temp_db, mock_httpx):
        """Verify that getEpisodes returns None when no anime loaded."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()

                from miko import Miko

                miko = Miko()
                episodes = await miko.getEpisodes()

                assert episodes is None


class TestSaveAnimeCover:
    """Tests for saveAnimeCover method."""

    @pytest.mark.asyncio
    async def test_save_anime_cover_success(
        self, mock_env, temp_db, temp_download_folder, mock_httpx, monkeypatch
    ):
        """Verify that saveAnimeCover saves the cover image."""
        monkeypatch.setenv("DESTINATION_FOLDER", temp_download_folder)

        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()

                mock_anime = MagicMock()
                mock_anime.getName.return_value = "Cover Test Anime"
                mock_anime.getCover.return_value = "https://example.com/cover.jpg"

                from miko import Miko

                miko = Miko()
                miko.anime = mock_anime
                miko.anime_name = "Cover Test Anime"
                miko.anime_folder = os.path.join(temp_download_folder, "Cover Test Anime")
                os.makedirs(miko.anime_folder, exist_ok=True)

                with patch("miko.requests") as mock_requests:
                    mock_response = MagicMock()
                    mock_response.iter_content.return_value = [b"fake_image_data"]
                    mock_response.raise_for_status = MagicMock()
                    mock_requests.get.return_value = mock_response

                    result = await miko.saveAnimeCover()

                assert result is True
                cover_path = os.path.join(miko.anime_folder, "folder.jpg")
                assert os.path.exists(cover_path)

    @pytest.mark.asyncio
    async def test_save_anime_cover_no_anime(self, mock_env, temp_db, mock_httpx):
        """Verify that saveAnimeCover returns False when no anime loaded."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()

                from miko import Miko

                miko = Miko()
                result = await miko.saveAnimeCover()

                assert result is False


# ==================== MIKO SC TESTS ====================

class TestMikoSCInitialization:
    """Tests for MikoSC class initialization."""

    def test_miko_sc_initialization(self, mock_env, temp_db, mock_httpx):
        """Verify that MikoSC initializes with correct default values."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()
                with patch("streamingcommunity.httpx"):
                    from miko import MikoSC

                    miko_sc = MikoSC()

                    assert miko_sc.name == "MikoSC"
                    assert miko_sc.version == "1.0.0"
                    assert miko_sc.current_series is None
                    assert miko_sc.current_item is None
                    assert miko_sc.search_results == []

    def test_miko_sc_has_download_semaphore(self, mock_env, temp_db, mock_httpx):
        """Verify that MikoSC has a download semaphore."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()
                with patch("streamingcommunity.httpx"):
                    from miko import MikoSC

                    miko_sc = MikoSC()

                    assert miko_sc.download_semaphore is not None
                    assert isinstance(miko_sc.download_semaphore, asyncio.Semaphore)

    def test_miko_sc_custom_folders(self, mock_env, temp_db, temp_download_folder, mock_httpx):
        """Verify that MikoSC accepts custom folder paths."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()
                with patch("streamingcommunity.httpx"):
                    from miko import MikoSC

                    movies_folder = os.path.join(temp_download_folder, "films")
                    series_folder = os.path.join(temp_download_folder, "tv")

                    miko_sc = MikoSC(
                        movies_folder=movies_folder,
                        series_folder=series_folder
                    )

                    assert miko_sc.movies_folder == movies_folder
                    assert miko_sc.series_folder == series_folder


class TestMikoSCSearch:
    """Tests for MikoSC search methods."""

    def test_search_stores_results(self, mock_env, temp_db, mock_httpx):
        """Verify that search stores results in search_results."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()
                with patch("streamingcommunity.httpx"):
                    from miko import MikoSC
                    from streamingcommunity import MediaItem

                    miko_sc = MikoSC()

                    mock_results = [
                        MediaItem(id=1, name="Result 1", slug="result-1", type="movie"),
                        MediaItem(id=2, name="Result 2", slug="result-2", type="tv"),
                    ]

                    with patch.object(miko_sc.sc.client, "search", return_value=mock_results):
                        results = miko_sc.search("test query")

                    assert len(results) == 2
                    assert miko_sc.search_results == results

    def test_search_films_filters_movies(self, mock_env, temp_db, mock_httpx):
        """Verify that search_films returns only movies."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()
                with patch("streamingcommunity.httpx"):
                    from miko import MikoSC
                    from streamingcommunity import MediaItem

                    miko_sc = MikoSC()

                    mock_results = [
                        MediaItem(id=1, name="Movie", slug="movie", type="movie"),
                        MediaItem(id=2, name="Series", slug="series", type="tv"),
                    ]

                    with patch.object(miko_sc.sc.client, "search", return_value=mock_results):
                        results = miko_sc.search_films("test")

                    assert len(results) == 1
                    assert results[0].type == "movie"

    def test_search_series_filters_tv(self, mock_env, temp_db, mock_httpx):
        """Verify that search_series returns only TV shows."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()
                with patch("streamingcommunity.httpx"):
                    from miko import MikoSC
                    from streamingcommunity import MediaItem

                    miko_sc = MikoSC()

                    mock_results = [
                        MediaItem(id=1, name="Movie", slug="movie", type="movie"),
                        MediaItem(id=2, name="Series", slug="series", type="tv"),
                    ]

                    with patch.object(miko_sc.sc.client, "search", return_value=mock_results):
                        results = miko_sc.search_series("test")

                    assert len(results) == 1
                    assert results[0].type == "tv"


class TestMikoSCSelection:
    """Tests for MikoSC selection methods."""

    def test_select_from_results_valid_index(self, mock_env, temp_db, mock_httpx):
        """Verify that valid index selection works."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()
                with patch("streamingcommunity.httpx"):
                    from miko import MikoSC
                    from streamingcommunity import MediaItem

                    miko_sc = MikoSC()
                    miko_sc.search_results = [
                        MediaItem(id=1, name="Item 1", slug="item-1", type="movie"),
                        MediaItem(id=2, name="Item 2", slug="item-2", type="tv"),
                    ]

                    selected = miko_sc.select_from_results(1)

                    assert selected is not None
                    assert selected.name == "Item 2"
                    assert miko_sc.current_item == selected

    def test_select_from_results_invalid_index(self, mock_env, temp_db, mock_httpx):
        """Verify that invalid index returns None."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()
                with patch("streamingcommunity.httpx"):
                    from miko import MikoSC
                    from streamingcommunity import MediaItem

                    miko_sc = MikoSC()
                    miko_sc.search_results = [
                        MediaItem(id=1, name="Item 1", slug="item-1", type="movie"),
                    ]

                    selected = miko_sc.select_from_results(99)

                    assert selected is None


class TestMikoSCLibrary:
    """Tests for MikoSC library operations."""

    def test_add_series_to_library(self, mock_env, temp_db, mock_httpx, mock_sc_media_item, mock_sc_series_info):
        """Verify that series can be added to library."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()
                with patch("streamingcommunity.httpx"):
                    from miko import MikoSC

                    miko_sc = MikoSC()
                    miko_sc.current_item = mock_sc_media_item

                    with patch.object(miko_sc.sc, "get_series_info", return_value=mock_sc_series_info):
                        with patch.object(miko_sc.sc, "get_season_episodes", return_value=[]):
                            result = miko_sc.add_series_to_library()

                    assert result is True

                    # Verify in database
                    series = miko_sc.db.get_tv_by_name("Test Series")
                    assert series is not None

    def test_add_series_to_library_no_item(self, mock_env, temp_db, mock_httpx):
        """Verify that adding series fails when no item selected."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()
                with patch("streamingcommunity.httpx"):
                    from miko import MikoSC

                    miko_sc = MikoSC()
                    miko_sc.current_item = None

                    result = miko_sc.add_series_to_library()

                    assert result is False

    def test_get_library_series(self, mock_env, temp_db, mock_httpx):
        """Verify that library series are retrieved."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()
                with patch("streamingcommunity.httpx"):
                    from miko import MikoSC
                    from datetime import datetime

                    miko_sc = MikoSC()

                    # Add a series directly to database
                    miko_sc.db.add_tv(
                        name="Library Series",
                        link="/test",
                        last_update=datetime.now(),
                        numero_episodi=10
                    )

                    series_list = miko_sc.get_library_series()

                    assert len(series_list) >= 1
                    names = [s["name"] for s in series_list]
                    assert "Library Series" in names

    def test_remove_series(self, mock_env, temp_db, mock_httpx):
        """Verify that series can be removed from library."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()
                with patch("streamingcommunity.httpx"):
                    from miko import MikoSC
                    from datetime import datetime

                    miko_sc = MikoSC()

                    # Add then remove
                    miko_sc.db.add_tv(
                        name="To Remove",
                        link="/test",
                        last_update=datetime.now(),
                        numero_episodi=5
                    )

                    result = miko_sc.remove_series("To Remove")

                    assert result is True
                    assert miko_sc.db.get_tv_by_name("To Remove") is None


class TestMikoSCMissingEpisodes:
    """Tests for missing episodes detection."""

    def test_get_missing_episodes_no_series(self, mock_env, temp_db, mock_httpx):
        """Verify that missing episodes returns empty for non-existent series."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()
                with patch("streamingcommunity.httpx"):
                    from miko import MikoSC

                    miko_sc = MikoSC()

                    missing = miko_sc.get_missing_episodes("Non Existent Series")

                    assert missing == {}

    def test_update_downloaded_episode(self, mock_env, temp_db, mock_httpx):
        """Verify that downloaded episode is tracked correctly."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()
                with patch("streamingcommunity.httpx"):
                    from miko import MikoSC
                    from datetime import datetime
                    import json

                    miko_sc = MikoSC()

                    # Add series
                    miko_sc.db.add_tv(
                        name="Track Series",
                        link="/test",
                        last_update=datetime.now(),
                        numero_episodi=10
                    )

                    # Update downloaded episodes
                    miko_sc._update_downloaded_episode("Track Series", 1, 1)
                    miko_sc._update_downloaded_episode("Track Series", 1, 2)
                    miko_sc._update_downloaded_episode("Track Series", 1, 3)

                    # Check database
                    series = miko_sc.db.get_tv_by_name("Track Series")
                    seasons_data = json.loads(series["seasons_data"])

                    assert "1" in seasons_data
                    assert seasons_data["1"]["downloaded"] == [1, 2, 3]
                    assert series["episodi_scaricati"] == 3
