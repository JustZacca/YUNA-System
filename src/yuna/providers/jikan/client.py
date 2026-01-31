"""
Jikan.moe API Client.
Provides anime metadata from MyAnimeList via Jikan API.

API Docs: https://docs.api.jikan.moe/
"""

import os
import asyncio
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

import httpx

from yuna.utils.logging import get_logger

logger = get_logger(__name__)

# Jikan API Configuration
JIKAN_API_URL = "https://api.jikan.moe/v4"


@dataclass
class JikanAnime:
    """Jikan anime metadata."""
    mal_id: int
    title: str
    title_english: Optional[str] = ""
    title_japanese: Optional[str] = ""
    synopsis: str = ""
    episodes: Optional[int] = None
    rating: Optional[str] = None
    score: float = 0.0
    scored_by: int = 0
    rank: Optional[int] = None
    popularity: int = 0
    members: int = 0
    favorites: int = 0
    status: Optional[str] = None  # Airing, Complete, etc.
    year: Optional[int] = None
    season: Optional[str] = None
    genres: List[Dict[str, Any]] = field(default_factory=list)
    studios: List[Dict[str, Any]] = field(default_factory=list)
    producers: List[Dict[str, Any]] = field(default_factory=list)
    source: Optional[str] = None
    duration: Optional[str] = None
    airing: bool = False
    type: Optional[str] = None  # TV, Movie, OVA, etc.
    # Images
    images: Dict[str, Any] = field(default_factory=dict)
    trailer: Dict[str, Any] = field(default_factory=dict)
    # Broadcast info
    broadcast: Dict[str, Any] = field(default_factory=dict)

    @property
    def poster_url(self) -> Optional[str]:
        """Get main poster URL (webp)."""
        if self.images.get("webp"):
            return self.images["webp"].get("image_url")
        return None

    @property
    def poster_url_jpg(self) -> Optional[str]:
        """Get JPG poster URL."""
        if self.images.get("jpg"):
            return self.images["jpg"].get("image_url")
        return None

    @property
    def main_title(self) -> str:
        """Get the best available title."""
        return self.title or self.title_english or self.title_japanese or ""

    @property
    def genre_names(self) -> List[str]:
        """Get list of genre names."""
        return [genre.get("name", "") for genre in self.genres if genre.get("name")]

    @property
    def studio_names(self) -> List[str]:
        """Get list of studio names."""
        return [studio.get("name", "") for studio in self.studios if studio.get("name")]


class JikanClient:
    """
    Jikan.moe API Client for searching and fetching anime metadata.
    
    This is an unofficial MyAnimeList API that provides access to anime data.
    Free to use with rate limiting: 60 requests/minute, 3 requests/second.
    
    API Docs: https://docs.api.jikan.moe/
    """

    def __init__(self, base_url: str = JIKAN_API_URL):
        """
        Initialize Jikan client.
        
        Args:
            base_url: Jikan API base URL
        """
        self.base_url = base_url
        self._client: Optional[httpx.AsyncClient] = None
        self._rate_limiter = asyncio.Semaphore(3)  # 3 concurrent requests
        self._last_request_time = 0.0
        self._min_request_interval = 0.33  # ~3 requests per second

    def is_available(self) -> bool:
        """Check if Jikan client is configured (always true for Jikan)."""
        return True

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=30.0,
                headers={"Accept": "application/json"},
            )
        return self._client

    async def _rate_limit(self):
        """Simple rate limiting to respect API limits."""
        current_time = asyncio.get_event_loop().time()
        elapsed = current_time - self._last_request_time
        
        if elapsed < self._min_request_interval:
            await asyncio.sleep(self._min_request_interval - elapsed)
        
        self._last_request_time = asyncio.get_event_loop().time()

    async def _request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Make API request with rate limiting."""
        await self._rate_limit()
        
        async with self._rate_limiter:
            client = await self._get_client()
            
            try:
                response = await client.get(endpoint, params=params)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Jikan API error: {e.response.status_code} - {e.response.text}")
                return None
            except Exception as e:
                logger.error(f"Jikan request error: {e}")
                return None

    def _parse_anime_data(self, data: Dict[str, Any]) -> JikanAnime:
        """Parse anime data from API response."""
        # Handle synopsis safely - API can return None
        raw_synopsis = data.get("synopsis") or ""
        synopsis = raw_synopsis[:500] if len(raw_synopsis) > 500 else raw_synopsis

        # Handle score safely - API can return None
        score = data.get("score")
        if score is None:
            score = 0.0

        return JikanAnime(
            mal_id=data.get("mal_id", 0),
            title=data.get("title", ""),
            title_english=data.get("title_english"),
            title_japanese=data.get("title_japanese"),
            synopsis=synopsis,
            episodes=data.get("episodes"),
            rating=data.get("rating"),
            score=score,
            scored_by=data.get("scored_by", 0),
            rank=data.get("rank"),
            popularity=data.get("popularity", 0),
            members=data.get("members", 0),
            favorites=data.get("favorites", 0),
            status=data.get("status"),
            year=data.get("year"),
            season=data.get("season"),
            genres=data.get("genres") or [],
            studios=data.get("studios") or [],
            producers=data.get("producers") or [],
            source=data.get("source"),
            duration=data.get("duration"),
            airing=data.get("airing", False),
            type=data.get("type"),
            images=data.get("images") or {},
            trailer=data.get("trailer") or {},
            broadcast=data.get("broadcast") or {},
        )

    # ==================== Search ====================

    async def search_anime(self, query: str, limit: int = 10, page: int = 1) -> List[JikanAnime]:
        """
        Search for anime.
        
        Args:
            query: Search query
            limit: Maximum number of results
            page: Page number for pagination
            
        Returns:
            List of JikanAnime results
        """
        if not query:
            return []
            
        params = {
            "q": query,
            "limit": min(limit, 25),  # API limit is 25
            "page": page,
            "order_by": "popularity",
            "sort": "desc",
        }

        data = await self._request("/anime", params)
        if not data:
            return []

        results = []
        for item in data.get("data", [])[:limit]:
            anime = self._parse_anime_data(item)
            results.append(anime)

        logger.info(f"Jikan anime search '{query}': {len(results)} results")
        return results

    # ==================== Details ====================

    async def get_anime(self, mal_id: int) -> Optional[JikanAnime]:
        """
        Get detailed anime info.
        
        Args:
            mal_id: MyAnimeList anime ID
            
        Returns:
            JikanAnime with full details
        """
        data = await self._request(f"/anime/{mal_id}")
        if not data:
            return None

        return self._parse_anime_data(data.get("data", {}))

    # ==================== Discover/Trending ====================

    async def get_top_anime(self, type_filter: Optional[str] = None, limit: int = 10) -> List[JikanAnime]:
        """
        Get top anime.
        
        Args:
            type_filter: Filter by type (tv, movie, ova, etc.)
            limit: Maximum number of results
            
        Returns:
            List of top anime
        """
        params = {"limit": min(limit, 25)}
        if type_filter:
            params["type"] = type_filter

        data = await self._request("/top/anime", params)
        if not data:
            return []

        results = []
        for item in data.get("data", [])[:limit]:
            anime = self._parse_anime_data(item)
            results.append(anime)

        return results

    async def get_seasonal_anime(self, year: Optional[int] = None, season: Optional[str] = None, limit: int = 10) -> List[JikanAnime]:
        """
        Get seasonal anime.
        
        Args:
            year: Year (defaults to current)
            season: Season (winter, spring, summer, fall)
            limit: Maximum number of results
            
        Returns:
            List of seasonal anime
        """
        if year and season:
            data = await self._request(f"/seasons/{year}/{season}", {"limit": min(limit, 25)})
        else:
            data = await self._request("/seasons/now", {"limit": min(limit, 25)})
            
        if not data:
            return []

        results = []
        for item in data.get("data", [])[:limit]:
            anime = self._parse_anime_data(item)
            results.append(anime)

        return results

    # ==================== Recommendations ====================

    async def get_anime_recommendations(self, mal_id: int, limit: int = 5) -> List[JikanAnime]:
        """
        Get anime recommendations.
        
        Args:
            mal_id: MyAnimeList anime ID
            limit: Maximum number of recommendations
            
        Returns:
            List of recommended anime
        """
        data = await self._request(f"/anime/{mal_id}/recommendations", {"limit": min(limit, 25)})
        if not data:
            return []

        results = []
        for item in data.get("data", [])[:limit]:
            # Recommendation items have the anime data nested
            anime_data = item.get("entry", {})
            if anime_data:
                anime = self._parse_anime_data(anime_data)
                results.append(anime)

        return results

    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None