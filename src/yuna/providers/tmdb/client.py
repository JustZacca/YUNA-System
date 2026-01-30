"""
TMDB (The Movie Database) API Client.
Provides rich metadata for films and TV series.

API Docs: https://developer.themoviedb.org/docs
"""

import os
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

import httpx

from yuna.utils.logging import get_logger

logger = get_logger(__name__)

# TMDB API Configuration
TMDB_API_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_URL = "https://image.tmdb.org/t/p"


@dataclass
class TMDBMovie:
    """TMDB Movie metadata."""
    id: int
    title: str
    original_title: str = ""
    overview: str = ""
    release_date: str = ""
    year: str = ""
    poster_path: Optional[str] = None
    backdrop_path: Optional[str] = None
    vote_average: float = 0.0
    vote_count: int = 0
    popularity: float = 0.0
    genre_ids: List[int] = field(default_factory=list)
    genres: List[str] = field(default_factory=list)
    runtime: Optional[int] = None
    # Additional details (from /movie/{id})
    imdb_id: Optional[str] = None
    tagline: Optional[str] = None
    budget: Optional[int] = None
    revenue: Optional[int] = None
    status: Optional[str] = None

    @property
    def poster_url(self) -> Optional[str]:
        """Get full poster URL (w500 size)."""
        if self.poster_path:
            return f"{TMDB_IMAGE_URL}/w500{self.poster_path}"
        return None

    @property
    def poster_url_hd(self) -> Optional[str]:
        """Get HD poster URL (original size)."""
        if self.poster_path:
            return f"{TMDB_IMAGE_URL}/original{self.poster_path}"
        return None

    @property
    def backdrop_url(self) -> Optional[str]:
        """Get backdrop URL (w1280 size)."""
        if self.backdrop_path:
            return f"{TMDB_IMAGE_URL}/w1280{self.backdrop_path}"
        return None


@dataclass
class TMDBSeries:
    """TMDB TV Series metadata."""
    id: int
    name: str
    original_name: str = ""
    overview: str = ""
    first_air_date: str = ""
    year: str = ""
    poster_path: Optional[str] = None
    backdrop_path: Optional[str] = None
    vote_average: float = 0.0
    vote_count: int = 0
    popularity: float = 0.0
    genre_ids: List[int] = field(default_factory=list)
    genres: List[str] = field(default_factory=list)
    # Series-specific
    number_of_seasons: int = 0
    number_of_episodes: int = 0
    episode_run_time: List[int] = field(default_factory=list)
    status: Optional[str] = None  # Returning Series, Ended, etc.
    in_production: bool = False
    networks: List[str] = field(default_factory=list)

    @property
    def poster_url(self) -> Optional[str]:
        """Get full poster URL."""
        if self.poster_path:
            return f"{TMDB_IMAGE_URL}/w500{self.poster_path}"
        return None

    @property
    def poster_url_hd(self) -> Optional[str]:
        """Get HD poster URL."""
        if self.poster_path:
            return f"{TMDB_IMAGE_URL}/original{self.poster_path}"
        return None

    @property
    def backdrop_url(self) -> Optional[str]:
        """Get backdrop URL."""
        if self.backdrop_path:
            return f"{TMDB_IMAGE_URL}/w1280{self.backdrop_path}"
        return None


class TMDBClient:
    """
    TMDB API Client for searching and fetching metadata.

    Requires TMDB_API_KEY environment variable.
    Get free API key at: https://www.themoviedb.org/settings/api
    """

    def __init__(self, api_key: Optional[str] = None, language: str = "it-IT"):
        """
        Initialize TMDB client.

        Args:
            api_key: TMDB API key (or uses TMDB_API_KEY env var)
            language: Language for results (default: Italian)
        """
        self.api_key = api_key or os.getenv("TMDB_API_KEY")
        self.language = language
        self._client: Optional[httpx.AsyncClient] = None

        if not self.api_key:
            logger.warning("TMDB_API_KEY not set - TMDB search will not work")

    def is_available(self) -> bool:
        """Check if TMDB client is configured."""
        return self.api_key is not None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=TMDB_API_URL,
                timeout=30.0,
                headers={"Accept": "application/json"},
            )
        return self._client

    async def _request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Make API request."""
        if not self.api_key:
            return None

        client = await self._get_client()

        request_params = {
            "api_key": self.api_key,
            "language": self.language,
            **(params or {}),
        }

        try:
            response = await client.get(endpoint, params=request_params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"TMDB API error: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"TMDB request error: {e}")
            return None

    # ==================== Search ====================

    async def search_movie(self, query: str, year: Optional[int] = None) -> List[TMDBMovie]:
        """
        Search for movies.

        Args:
            query: Search query
            year: Optional year filter

        Returns:
            List of TMDBMovie results
        """
        params = {"query": query}
        if year:
            params["year"] = str(year)

        data = await self._request("/search/movie", params)
        if not data:
            return []

        results = []
        for item in data.get("results", [])[:10]:
            movie = TMDBMovie(
                id=item["id"],
                title=item.get("title", ""),
                original_title=item.get("original_title", ""),
                overview=item.get("overview", ""),
                release_date=item.get("release_date", ""),
                year=item.get("release_date", "")[:4] if item.get("release_date") else "",
                poster_path=item.get("poster_path"),
                backdrop_path=item.get("backdrop_path"),
                vote_average=item.get("vote_average", 0),
                vote_count=item.get("vote_count", 0),
                popularity=item.get("popularity", 0),
                genre_ids=item.get("genre_ids", []),
            )
            results.append(movie)

        logger.info(f"TMDB movie search '{query}': {len(results)} results")
        return results

    async def search_tv(self, query: str, year: Optional[int] = None) -> List[TMDBSeries]:
        """
        Search for TV series.

        Args:
            query: Search query
            year: Optional first air year filter

        Returns:
            List of TMDBSeries results
        """
        params = {"query": query}
        if year:
            params["first_air_date_year"] = str(year)

        data = await self._request("/search/tv", params)
        if not data:
            return []

        results = []
        for item in data.get("results", [])[:10]:
            series = TMDBSeries(
                id=item["id"],
                name=item.get("name", ""),
                original_name=item.get("original_name", ""),
                overview=item.get("overview", ""),
                first_air_date=item.get("first_air_date", ""),
                year=item.get("first_air_date", "")[:4] if item.get("first_air_date") else "",
                poster_path=item.get("poster_path"),
                backdrop_path=item.get("backdrop_path"),
                vote_average=item.get("vote_average", 0),
                vote_count=item.get("vote_count", 0),
                popularity=item.get("popularity", 0),
                genre_ids=item.get("genre_ids", []),
            )
            results.append(series)

        logger.info(f"TMDB TV search '{query}': {len(results)} results")
        return results

    async def search_multi(self, query: str) -> Dict[str, List]:
        """
        Search for both movies and TV series.

        Args:
            query: Search query

        Returns:
            Dict with 'movies' and 'series' lists
        """
        data = await self._request("/search/multi", {"query": query})
        if not data:
            return {"movies": [], "series": []}

        movies = []
        series = []

        for item in data.get("results", [])[:20]:
            media_type = item.get("media_type")

            if media_type == "movie":
                movie = TMDBMovie(
                    id=item["id"],
                    title=item.get("title", ""),
                    original_title=item.get("original_title", ""),
                    overview=item.get("overview", ""),
                    release_date=item.get("release_date", ""),
                    year=item.get("release_date", "")[:4] if item.get("release_date") else "",
                    poster_path=item.get("poster_path"),
                    backdrop_path=item.get("backdrop_path"),
                    vote_average=item.get("vote_average", 0),
                    vote_count=item.get("vote_count", 0),
                    popularity=item.get("popularity", 0),
                    genre_ids=item.get("genre_ids", []),
                )
                movies.append(movie)

            elif media_type == "tv":
                tv = TMDBSeries(
                    id=item["id"],
                    name=item.get("name", ""),
                    original_name=item.get("original_name", ""),
                    overview=item.get("overview", ""),
                    first_air_date=item.get("first_air_date", ""),
                    year=item.get("first_air_date", "")[:4] if item.get("first_air_date") else "",
                    poster_path=item.get("poster_path"),
                    backdrop_path=item.get("backdrop_path"),
                    vote_average=item.get("vote_average", 0),
                    vote_count=item.get("vote_count", 0),
                    popularity=item.get("popularity", 0),
                    genre_ids=item.get("genre_ids", []),
                )
                series.append(tv)

        logger.info(f"TMDB multi search '{query}': {len(movies)} movies, {len(series)} series")
        return {"movies": movies, "series": series}

    # ==================== Details ====================

    async def get_movie(self, movie_id: int) -> Optional[TMDBMovie]:
        """
        Get detailed movie info.

        Args:
            movie_id: TMDB movie ID

        Returns:
            TMDBMovie with full details
        """
        data = await self._request(f"/movie/{movie_id}")
        if not data:
            return None

        return TMDBMovie(
            id=data["id"],
            title=data.get("title", ""),
            original_title=data.get("original_title", ""),
            overview=data.get("overview", ""),
            release_date=data.get("release_date", ""),
            year=data.get("release_date", "")[:4] if data.get("release_date") else "",
            poster_path=data.get("poster_path"),
            backdrop_path=data.get("backdrop_path"),
            vote_average=data.get("vote_average", 0),
            vote_count=data.get("vote_count", 0),
            popularity=data.get("popularity", 0),
            genres=[g["name"] for g in data.get("genres", [])],
            runtime=data.get("runtime"),
            imdb_id=data.get("imdb_id"),
            tagline=data.get("tagline"),
            budget=data.get("budget"),
            revenue=data.get("revenue"),
            status=data.get("status"),
        )

    async def get_tv(self, tv_id: int) -> Optional[TMDBSeries]:
        """
        Get detailed TV series info.

        Args:
            tv_id: TMDB TV series ID

        Returns:
            TMDBSeries with full details
        """
        data = await self._request(f"/tv/{tv_id}")
        if not data:
            return None

        return TMDBSeries(
            id=data["id"],
            name=data.get("name", ""),
            original_name=data.get("original_name", ""),
            overview=data.get("overview", ""),
            first_air_date=data.get("first_air_date", ""),
            year=data.get("first_air_date", "")[:4] if data.get("first_air_date") else "",
            poster_path=data.get("poster_path"),
            backdrop_path=data.get("backdrop_path"),
            vote_average=data.get("vote_average", 0),
            vote_count=data.get("vote_count", 0),
            popularity=data.get("popularity", 0),
            genres=[g["name"] for g in data.get("genres", [])],
            number_of_seasons=data.get("number_of_seasons", 0),
            number_of_episodes=data.get("number_of_episodes", 0),
            episode_run_time=data.get("episode_run_time", []),
            status=data.get("status"),
            in_production=data.get("in_production", False),
            networks=[n["name"] for n in data.get("networks", [])],
        )

    # ==================== Discover/Trending ====================

    async def get_trending_movies(self, time_window: str = "week") -> List[TMDBMovie]:
        """
        Get trending movies.

        Args:
            time_window: 'day' or 'week'

        Returns:
            List of trending movies
        """
        data = await self._request(f"/trending/movie/{time_window}")
        if not data:
            return []

        results = []
        for item in data.get("results", [])[:10]:
            movie = TMDBMovie(
                id=item["id"],
                title=item.get("title", ""),
                original_title=item.get("original_title", ""),
                overview=item.get("overview", ""),
                release_date=item.get("release_date", ""),
                year=item.get("release_date", "")[:4] if item.get("release_date") else "",
                poster_path=item.get("poster_path"),
                backdrop_path=item.get("backdrop_path"),
                vote_average=item.get("vote_average", 0),
                vote_count=item.get("vote_count", 0),
                popularity=item.get("popularity", 0),
            )
            results.append(movie)

        return results

    async def get_trending_tv(self, time_window: str = "week") -> List[TMDBSeries]:
        """
        Get trending TV series.

        Args:
            time_window: 'day' or 'week'

        Returns:
            List of trending TV series
        """
        data = await self._request(f"/trending/tv/{time_window}")
        if not data:
            return []

        results = []
        for item in data.get("results", [])[:10]:
            series = TMDBSeries(
                id=item["id"],
                name=item.get("name", ""),
                original_name=item.get("original_name", ""),
                overview=item.get("overview", ""),
                first_air_date=item.get("first_air_date", ""),
                year=item.get("first_air_date", "")[:4] if item.get("first_air_date") else "",
                poster_path=item.get("poster_path"),
                backdrop_path=item.get("backdrop_path"),
                vote_average=item.get("vote_average", 0),
                vote_count=item.get("vote_count", 0),
                popularity=item.get("popularity", 0),
            )
            results.append(series)

        return results

    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
