"""AniList GraphQL API client for anime metadata."""

from typing import List, Optional, Dict, Any
import httpx
from yuna.utils.logging import get_logger

logger = get_logger(__name__)


class AniListClient:
    """Client for AniList GraphQL API."""

    BASE_URL = "https://graphql.anilist.co"

    def __init__(self, access_token: Optional[str] = None):
        """Initialize AniList client.

        Args:
            access_token: Optional OAuth access token for authenticated requests
        """
        self.access_token = access_token
        self.client = httpx.AsyncClient(timeout=10.0)

    def is_available(self) -> bool:
        """Check if AniList client is available (always true for AniList)."""
        return True

    async def search_anime(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for anime by title.

        Args:
            query: Search query string
            limit: Maximum number of results to return

        Returns:
            List of anime results with metadata
        """
        graphql_query = "query ($search: String!, $page: Int, $perPage: Int) { Page(page: $page, perPage: $perPage) { media(search: $search, type: ANIME) { id title { romaji english native } coverImage { large medium } description format status startDate { year month day } endDate { year month day } episodes season seasonYear genres averageScore popularity synonyms source } } }"

        variables = {
            "search": query,
            "page": 1,
            "perPage": limit
        }

        try:
            response = await self.client.post(
                self.BASE_URL,
                json={"query": graphql_query, "variables": variables},
                headers=self._get_headers()
            )

            data = response.json()

            if "errors" in data:
                logger.error(f"AniList API error: {data['errors']}")
                return []

            media_list = data.get("data", {}).get("Page", {}).get("media", [])
            return self._format_results(media_list)

        except Exception as e:
            logger.error(f"Error searching AniList: {e}")
            return []

    async def get_anime_by_id(self, anilist_id: int) -> Optional[Dict[str, Any]]:
        """Get anime by AniList ID.

        Args:
            anilist_id: AniList media ID

        Returns:
            Anime metadata or None if not found
        """
        graphql_query = "query ($id: Int!) { Media(id: $id, type: ANIME) { id title { romaji english native } coverImage { large medium } description format status startDate { year month day } endDate { year month day } episodes season seasonYear genres averageScore popularity synonyms source } }"

        variables = {"id": anilist_id}

        try:
            response = await self.client.post(
                self.BASE_URL,
                json={"query": graphql_query, "variables": variables},
                headers=self._get_headers()
            )

            data = response.json()

            if "errors" in data:
                logger.error(f"AniList API error: {data['errors']}")
                return None

            media = data.get("data", {}).get("Media")
            if media:
                return self._format_result(media)
            return None

        except Exception as e:
            logger.error(f"Error fetching AniList anime: {e}")
            return None

    async def get_top_anime(self, type_filter: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top anime sorted by popularity/rating.

        Args:
            type_filter: Filter by format (TV, MOVIE, OVA, etc.)
            limit: Maximum number of results to return

        Returns:
            List of top anime results
        """
        graphql_query = "query ($format: MediaFormat, $page: Int, $perPage: Int) { Page(page: $page, perPage: $perPage) { media(type: ANIME, format: $format, sort: [POPULARITY_DESC, SCORE_DESC]) { id title { romaji english native } coverImage { large medium } description format status startDate { year month day } endDate { year month day } episodes season seasonYear genres averageScore popularity synonyms source } } }"

        variables = {
            "page": 1,
            "perPage": limit
        }
        
        if type_filter:
            variables["format"] = type_filter.upper()

        try:
            response = await self.client.post(
                self.BASE_URL,
                json={"query": graphql_query, "variables": variables},
                headers=self._get_headers()
            )

            data = response.json()

            if "errors" in data:
                logger.error(f"AniList API error: {data['errors']}")
                return []

            media_list = data.get("data", {}).get("Page", {}).get("media", [])
            return self._format_results(media_list)

        except Exception as e:
            logger.error(f"Error fetching top AniList anime: {e}")
            return []

    async def get_seasonal_anime(self, year: Optional[int] = None, season: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get seasonal anime.

        Args:
            year: Year (defaults to current year)
            season: Season (WINTER, SPRING, SUMMER, FALL)
            limit: Maximum number of results to return

        Returns:
            List of seasonal anime results
        """
        import datetime
        
        if year is None:
            year = datetime.datetime.now().year
        
        if season is None:
            month = datetime.datetime.now().month
            if month <= 3:
                season = "WINTER"
            elif month <= 6:
                season = "SPRING"
            elif month <= 9:
                season = "SUMMER"
            else:
                season = "FALL"
        else:
            season = season.upper()

        graphql_query = "query ($season: MediaSeason, $year: Int, $page: Int, $perPage: Int) { Page(page: $page, perPage: $perPage) { media(type: ANIME, season: $season, seasonYear: $year, sort: [POPULARITY_DESC, SCORE_DESC]) { id title { romaji english native } coverImage { large medium } description format status startDate { year month day } endDate { year month day } episodes season seasonYear genres averageScore popularity synonyms source } } }"

        variables = {
            "season": season,
            "year": year,
            "page": 1,
            "perPage": limit
        }

        try:
            response = await self.client.post(
                self.BASE_URL,
                json={"query": graphql_query, "variables": variables},
                headers=self._get_headers()
            )

            data = response.json()

            if "errors" in data:
                logger.error(f"AniList API error: {data['errors']}")
                return []

            media_list = data.get("data", {}).get("Page", {}).get("media", [])
            return self._format_results(media_list)

        except Exception as e:
            logger.error(f"Error fetching seasonal AniList anime: {e}")
            return []

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers."""
        headers = {
            "Content-Type": "application/json",
        }
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    def _format_results(self, media_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format multiple media results."""
        return [self._format_result(media) for media in media_list]

    def _format_result(self, media: Dict[str, Any]) -> Dict[str, Any]:
        """Format a single media result to match our schema.

        Args:
            media: Raw AniList media object

        Returns:
            Formatted media object
        """
        start_date = media.get("startDate", {})
        year = start_date.get("year")

        return {
            "anilist_id": media.get("id"),
            "name": media.get("title", {}).get("romaji", ""),
            "english_name": media.get("title", {}).get("english", ""),
            "native_name": media.get("title", {}).get("native", ""),
            "poster_url": media.get("coverImage", {}).get("large", ""),
            "poster_medium": media.get("coverImage", {}).get("medium", ""),
            "synopsis": media.get("description", ""),
            "rating": media.get("averageScore", 0) / 10 if media.get("averageScore") else 0,
            "year": year,
            "genres": media.get("genres", []),
            "episodes": media.get("episodes"),
            "status": media.get("status", ""),
            "format": media.get("format", ""),
            "season": media.get("season", ""),
            "season_year": media.get("seasonYear"),
            "synonyms": media.get("synonyms", []),
            "source": media.get("source", ""),
            "popularity": media.get("popularity", 0),
        }
