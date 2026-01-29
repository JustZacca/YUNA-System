"""
Tests for streamingcommunity.py - StreamingCommunity client for YUNA-System.

This module tests:
    - Data classes (MediaItem, Episode, Season, SeriesInfo)
    - StreamingCommunityClient initialization and URL detection
    - Search functionality
    - Series info retrieval
    - VideoSource extraction
    - HLSDownloader operations
    - StreamingCommunity manager class
"""

import os
import sys
import asyncio
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestMediaItem:
    """Tests for MediaItem dataclass."""

    def test_media_item_creation(self):
        """Verify that MediaItem is created with correct fields."""
        from streamingcommunity import MediaItem

        item = MediaItem(
            id=123,
            name="Test Movie",
            slug="test-movie",
            type="movie",
            year="2024",
            image="https://example.com/poster.jpg",
            provider_language="it"
        )

        assert item.id == 123
        assert item.name == "Test Movie"
        assert item.slug == "test-movie"
        assert item.type == "movie"
        assert item.year == "2024"
        assert item.provider_language == "it"

    def test_media_item_str(self):
        """Verify that MediaItem string representation is correct."""
        from streamingcommunity import MediaItem

        item = MediaItem(
            id=123,
            name="Breaking Bad",
            slug="breaking-bad",
            type="tv",
            year="2008"
        )

        str_repr = str(item)
        assert "Breaking Bad" in str_repr
        assert "2008" in str_repr
        assert "tv" in str_repr

    def test_media_item_default_values(self):
        """Verify that MediaItem has correct default values."""
        from streamingcommunity import MediaItem

        item = MediaItem(
            id=1,
            name="Test",
            slug="test",
            type="movie"
        )

        assert item.year == ""
        assert item.date == ""
        assert item.image is None
        assert item.provider_language == "it"


class TestEpisode:
    """Tests for Episode dataclass."""

    def test_episode_creation(self):
        """Verify that Episode is created correctly."""
        from streamingcommunity import Episode

        episode = Episode(
            id=101,
            number=5,
            name="The One Where...",
            plot="Episode description",
            duration=45
        )

        assert episode.id == 101
        assert episode.number == 5
        assert episode.name == "The One Where..."
        assert episode.duration == 45

    def test_episode_str(self):
        """Verify Episode string representation."""
        from streamingcommunity import Episode

        episode = Episode(id=1, number=3, name="Pilot Episode")
        str_repr = str(episode)

        assert "E3" in str_repr
        assert "Pilot Episode" in str_repr


class TestSeason:
    """Tests for Season dataclass."""

    def test_season_creation(self):
        """Verify that Season is created correctly."""
        from streamingcommunity import Season

        season = Season(
            id=1,
            number=2,
            name="Season 2",
            slug="season-2"
        )

        assert season.id == 1
        assert season.number == 2
        assert season.name == "Season 2"
        assert season.episodes == []

    def test_season_str(self):
        """Verify Season string representation."""
        from streamingcommunity import Season, Episode

        season = Season(id=1, number=1, name="Season 1")
        season.episodes = [
            Episode(id=1, number=1),
            Episode(id=2, number=2),
        ]

        str_repr = str(season)
        assert "Season 1" in str_repr
        assert "2 episodes" in str_repr


class TestSeriesInfo:
    """Tests for SeriesInfo dataclass."""

    def test_series_info_creation(self, mock_sc_series_info):
        """Verify that SeriesInfo is created correctly."""
        info = mock_sc_series_info

        assert info.id == 123
        assert info.name == "Test Series"
        assert info.slug == "test-series"
        assert len(info.seasons) == 2

    def test_series_info_get_season(self, mock_sc_series_info):
        """Verify that get_season returns correct season."""
        info = mock_sc_series_info

        season1 = info.get_season(1)
        assert season1 is not None
        assert season1.number == 1

        season2 = info.get_season(2)
        assert season2 is not None
        assert season2.number == 2

    def test_series_info_get_season_not_found(self, mock_sc_series_info):
        """Verify that get_season returns None for non-existent season."""
        info = mock_sc_series_info

        season = info.get_season(99)
        assert season is None


class TestStreamingCommunityClient:
    """Tests for StreamingCommunityClient class."""

    def test_client_initialization(self):
        """Verify that client initializes correctly."""
        from streamingcommunity import StreamingCommunityClient

        client = StreamingCommunityClient()

        assert client.base_url is None
        assert client._version is None

    def test_client_with_base_url(self):
        """Verify that client accepts custom base URL."""
        from streamingcommunity import StreamingCommunityClient

        client = StreamingCommunityClient(base_url="https://custom.domain.com")

        assert client.base_url == "https://custom.domain.com"

    def test_get_headers(self):
        """Verify that headers are generated correctly."""
        from streamingcommunity import StreamingCommunityClient

        client = StreamingCommunityClient()
        headers = client._get_headers()

        assert "User-Agent" in headers
        assert "Accept" in headers
        assert "Accept-Language" in headers

    def test_get_inertia_headers(self):
        """Verify that Inertia headers include X-Inertia."""
        from streamingcommunity import StreamingCommunityClient

        client = StreamingCommunityClient()
        client._version = "test-version"
        headers = client._get_inertia_headers()

        assert "X-Inertia" in headers
        assert headers["X-Inertia"] == "true"
        assert headers["X-Inertia-Version"] == "test-version"


class TestVideoSource:
    """Tests for VideoSource class."""

    def test_video_source_initialization(self):
        """Verify that VideoSource initializes correctly."""
        from streamingcommunity import VideoSource

        source = VideoSource(
            base_url="https://streamingcommunity.computer",
            media_id=123,
            is_series=True,
            lang="it"
        )

        assert source.base_url == "https://streamingcommunity.computer"
        assert source.media_id == 123
        assert source.is_series is True
        assert source.lang == "it"
        assert source.iframe_src is None
        assert source.master_playlist is None

    def test_parse_window_vars_extracts_playlist(self):
        """Verify that window variables are parsed correctly."""
        from streamingcommunity import VideoSource

        source = VideoSource("https://test.com", 1)

        script = """
        window.video = {id: 123, name: 'test'};
        window.masterPlaylist = {url: 'https://vixcloud.co/playlist.m3u8', token: 'abc123', expires: '1234567890'};
        window.canPlayFHD = true;
        """

        result = source._parse_window_vars(script)

        assert 'playlist_url' in result
        assert 'vixcloud.co/playlist.m3u8' in result['playlist_url']
        assert source._token == 'abc123'
        assert source._can_play_fhd is True


class TestHLSDownloader:
    """Tests for HLSDownloader class."""

    def test_downloader_initialization(self, temp_download_folder):
        """Verify that HLSDownloader initializes correctly."""
        from streamingcommunity import HLSDownloader

        with patch("streamingcommunity.subprocess.run"):
            downloader = HLSDownloader(temp_download_folder)

        assert downloader.output_folder == temp_download_folder

    def test_sanitize_filename(self, temp_download_folder):
        """Verify that filenames are sanitized correctly."""
        from streamingcommunity import HLSDownloader

        with patch("streamingcommunity.subprocess.run"):
            downloader = HLSDownloader(temp_download_folder)

        # Test various problematic characters
        result = downloader._sanitize_filename('Test: Movie/Show "Title"')
        assert ":" not in result
        assert "/" not in result
        assert '"' not in result

    def test_sanitize_filename_preserves_normal_chars(self, temp_download_folder):
        """Verify that normal characters are preserved."""
        from streamingcommunity import HLSDownloader

        with patch("streamingcommunity.subprocess.run"):
            downloader = HLSDownloader(temp_download_folder)

        result = downloader._sanitize_filename("Normal Movie Title 2024")
        assert result == "Normal Movie Title 2024"

    @pytest.mark.asyncio
    async def test_download_creates_directory(self, temp_download_folder):
        """Verify that download creates output directory."""
        from streamingcommunity import HLSDownloader

        with patch("streamingcommunity.subprocess.run"):
            downloader = HLSDownloader(os.path.join(temp_download_folder, "newdir"))

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = MagicMock()
            mock_process.communicate = AsyncMock(return_value=(b"", b""))
            mock_process.returncode = 0
            mock_exec.return_value = mock_process

            # Create a dummy file to simulate successful download
            os.makedirs(downloader.output_folder, exist_ok=True)
            dummy_file = os.path.join(downloader.output_folder, "Test.mp4")
            with open(dummy_file, "w") as f:
                f.write("dummy content")

            success, result = await downloader.download(
                "https://example.com/playlist.m3u8",
                "Test"
            )

            assert os.path.exists(downloader.output_folder)


class TestStreamingCommunityManager:
    """Tests for StreamingCommunity manager class."""

    def test_manager_initialization(self, mock_env, temp_db, mock_httpx):
        """Verify that manager initializes correctly."""
        with patch("airi.httpx", mock_httpx):
            with patch("streamingcommunity.httpx"):
                from streamingcommunity import StreamingCommunity

                manager = StreamingCommunity(
                    movies_folder="/tmp/movies",
                    series_folder="/tmp/series"
                )

                assert manager.movies_folder == "/tmp/movies"
                assert manager.series_folder == "/tmp/series"
                assert manager.client is not None

    def test_search_films_filters_correctly(self, mock_env, temp_db, mock_httpx):
        """Verify that search_films returns only movies."""
        with patch("airi.httpx", mock_httpx):
            with patch("streamingcommunity.httpx"):
                from streamingcommunity import StreamingCommunity, MediaItem

                manager = StreamingCommunity()

                # Mock search results
                mock_results = [
                    MediaItem(id=1, name="Movie 1", slug="movie-1", type="movie"),
                    MediaItem(id=2, name="Series 1", slug="series-1", type="tv"),
                    MediaItem(id=3, name="Movie 2", slug="movie-2", type="movie"),
                ]

                with patch.object(manager.client, "search", return_value=mock_results):
                    films = manager.search_films("test")

                assert len(films) == 2
                assert all(f.type == "movie" for f in films)

    def test_search_series_filters_correctly(self, mock_env, temp_db, mock_httpx):
        """Verify that search_series returns only TV shows."""
        with patch("airi.httpx", mock_httpx):
            with patch("streamingcommunity.httpx"):
                from streamingcommunity import StreamingCommunity, MediaItem

                manager = StreamingCommunity()

                mock_results = [
                    MediaItem(id=1, name="Movie 1", slug="movie-1", type="movie"),
                    MediaItem(id=2, name="Series 1", slug="series-1", type="tv"),
                    MediaItem(id=3, name="Series 2", slug="series-2", type="tv"),
                ]

                with patch.object(manager.client, "search", return_value=mock_results):
                    series = manager.search_series("test")

                assert len(series) == 2
                assert all(s.type == "tv" for s in series)


class TestDatabaseTVOperations:
    """Tests for TV-specific database operations with SC fields."""

    def test_add_tv_with_sc_fields(self, temp_db, sample_sc_series_data):
        """Verify that TV shows can be added with StreamingCommunity fields."""
        from database import Database

        db = Database(temp_db)
        last_update = datetime.strptime(
            sample_sc_series_data["last_update"], "%Y-%m-%d %H:%M:%S"
        )

        result = db.add_tv(
            name=sample_sc_series_data["name"],
            link=sample_sc_series_data["link"],
            last_update=last_update,
            numero_episodi=sample_sc_series_data["numero_episodi"],
            slug=sample_sc_series_data["slug"],
            media_id=sample_sc_series_data["media_id"],
            provider_language=sample_sc_series_data["provider_language"],
            year=sample_sc_series_data["year"],
            provider=sample_sc_series_data["provider"]
        )

        assert result is True

        # Verify fields are stored correctly
        tv = db.get_tv_by_name(sample_sc_series_data["name"])
        assert tv is not None
        assert tv["slug"] == "breaking-bad"
        assert tv["media_id"] == 123
        assert tv["provider"] == "streamingcommunity"
        assert tv["year"] == "2008"

    def test_update_tv_seasons_data(self, temp_db, sample_sc_series_data):
        """Verify that seasons_data can be updated."""
        from database import Database
        import json

        db = Database(temp_db)
        last_update = datetime.strptime(
            sample_sc_series_data["last_update"], "%Y-%m-%d %H:%M:%S"
        )

        db.add_tv(
            name=sample_sc_series_data["name"],
            link=sample_sc_series_data["link"],
            last_update=last_update,
            numero_episodi=sample_sc_series_data["numero_episodi"],
        )

        # Update seasons data
        seasons_data = json.dumps({
            "1": {"total": 10, "downloaded": [1, 2, 3, 4, 5]},
            "2": {"total": 8, "downloaded": [1, 2]}
        })

        result = db.update_tv_seasons_data(sample_sc_series_data["name"], seasons_data)
        assert result is True

        # Verify update
        tv = db.get_tv_by_name(sample_sc_series_data["name"])
        stored_data = json.loads(tv["seasons_data"])
        assert "1" in stored_data
        assert len(stored_data["1"]["downloaded"]) == 5


class TestDatabaseMovieOperations:
    """Tests for movie-specific database operations with SC fields."""

    def test_add_movie_with_sc_fields(self, temp_db, sample_sc_movie_data):
        """Verify that movies can be added with StreamingCommunity fields."""
        from database import Database

        db = Database(temp_db)
        last_update = datetime.strptime(
            sample_sc_movie_data["last_update"], "%Y-%m-%d %H:%M:%S"
        )

        result = db.add_movie(
            name=sample_sc_movie_data["name"],
            link=sample_sc_movie_data["link"],
            last_update=last_update,
            slug=sample_sc_movie_data["slug"],
            media_id=sample_sc_movie_data["media_id"],
            provider_language=sample_sc_movie_data["provider_language"],
            year=sample_sc_movie_data["year"],
            provider=sample_sc_movie_data["provider"]
        )

        assert result is True

        # Verify fields
        movie = db.get_movie_by_name(sample_sc_movie_data["name"])
        assert movie is not None
        assert movie["slug"] == "the-matrix"
        assert movie["media_id"] == 456
        assert movie["provider"] == "streamingcommunity"

    def test_get_pending_movies(self, temp_db):
        """Verify that pending movies (not downloaded) are returned."""
        from database import Database

        db = Database(temp_db)
        now = datetime.now()

        # Add downloaded movie
        db.add_movie("Downloaded Movie", "/link1", now)
        db.update_movie_downloaded("Downloaded Movie", 1)

        # Add pending movie
        db.add_movie("Pending Movie", "/link2", now)

        pending = db.get_pending_movies()

        assert len(pending) == 1
        assert pending[0]["name"] == "Pending Movie"

    def test_update_movie_downloaded(self, temp_db):
        """Verify that movie download status can be updated."""
        from database import Database

        db = Database(temp_db)
        now = datetime.now()

        db.add_movie("Test Movie", "/link", now)

        # Initially not downloaded
        movie = db.get_movie_by_name("Test Movie")
        assert movie["scaricato"] == 0

        # Mark as downloaded
        result = db.update_movie_downloaded("Test Movie", 1)
        assert result is True

        movie = db.get_movie_by_name("Test Movie")
        assert movie["scaricato"] == 1
