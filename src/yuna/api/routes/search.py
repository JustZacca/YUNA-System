"""
Search API Routes.
Unified search using TMDB for metadata + providers for download links.
"""

from typing import List, Optional, Any
from enum import Enum

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from yuna.providers.tmdb import TMDBClient
from yuna.providers.anilist import AniListClient
from yuna.config import config

# Global instances
_miko_sc: Optional[Any] = None
from yuna.services.media_service import Miko, MikoSC
from yuna.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/search", tags=["Search"])

# Shared client instances
_tmdb_client: Optional[TMDBClient] = None
_anilist_client: Optional[AniListClient] = None


def get_tmdb() -> TMDBClient:
    """Get TMDB client singleton."""
    global _tmdb_client
    if _tmdb_client is None:
        _tmdb_client = TMDBClient()
    return _tmdb_client


def get_anilist() -> AniListClient:
    """Get AniList client singleton."""
    global _anilist_client
    if _anilist_client is None:
        _anilist_client = AniListClient(access_token=config.anilist_access_token)
    return _anilist_client


def get_miko_sc() -> MikoSC:
    """Get MikoSC singleton."""
    global _miko_sc
    if _miko_sc is None:
        _miko_sc = MikoSC()
    return _miko_sc


# ==================== Schemas ====================

class MediaType(str, Enum):
    """Media type filter."""
    anime = "anime"
    series = "series"
    film = "film"
    all = "all"


class SearchResult(BaseModel):
    """Rich search result with TMDB metadata."""
    # Basic info
    name: str
    type: str  # anime, series, film
    year: Optional[str] = None

    # TMDB metadata
    tmdb_id: Optional[int] = None
    
    # Jikan metadata (for anime)
    mal_id: Optional[int] = None
    overview: Optional[str] = None
    poster: Optional[str] = None
    backdrop: Optional[str] = None
    rating: Optional[float] = None
    vote_count: Optional[int] = None
    genres: List[str] = []

    # Series-specific
    seasons: Optional[int] = None
    episodes: Optional[int] = None
    status: Optional[str] = None

    # Film-specific
    runtime: Optional[int] = None

    # Download provider info
    provider: Optional[str] = None  # animeworld, streamingcommunity
    provider_url: Optional[str] = None
    provider_id: Optional[int] = None
    provider_slug: Optional[str] = None


class SearchResponse(BaseModel):
    """Search response grouped by type."""
    query: str
    total: int
    anime: List[SearchResult] = []
    series: List[SearchResult] = []
    films: List[SearchResult] = []
    tmdb_available: bool = True
    anilist_available: bool = True


class TrendingResponse(BaseModel):
    """Trending content response."""
    movies: List[SearchResult] = []
    series: List[SearchResult] = []


# ==================== Routes ====================

@router.get("", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=2, description="Search query"),
    type: MediaType = Query(MediaType.all, description="Filter by media type"),
):
    """
    Search for anime, series, and films.

    Uses TMDB for rich metadata (poster, rating, description).
    Then matches with download providers (AnimeWorld, StreamingCommunity).
    """
    results = SearchResponse(query=q, total=0)
    tmdb = get_tmdb()
    anilist = get_anilist()

    results.tmdb_available = tmdb.is_available()
    results.anilist_available = anilist.is_available()

    # Search anime if requested
    if type in (MediaType.all, MediaType.anime):
        anime_results = await _search_anime(q)
        results.anime = anime_results
        results.total += len(anime_results)

    # Search movies/series via TMDB if requested
    if type in (MediaType.all, MediaType.series, MediaType.film):
        if tmdb.is_available():
            # Use TMDB for rich metadata
            tmdb_results = await tmdb.search_multi(q)

            # Process movies
            if type in (MediaType.all, MediaType.film):
                for movie in tmdb_results.get("movies", []):
                    result = SearchResult(
                        name=movie.title,
                        type="film",
                        year=movie.year,
                        tmdb_id=movie.id,
                        overview=movie.overview,
                        poster=movie.poster_url,
                        backdrop=movie.backdrop_url,
                        rating=movie.vote_average,
                        vote_count=movie.vote_count,
                        genres=movie.genres,
                        runtime=movie.runtime,
                    )
                    # Try to find on StreamingCommunity
                    await _enrich_with_provider(result)
                    results.films.append(result)

            # Process series
            if type in (MediaType.all, MediaType.series):
                for series in tmdb_results.get("series", []):
                    result = SearchResult(
                        name=series.name,
                        type="series",
                        year=series.year,
                        tmdb_id=series.id,
                        overview=series.overview,
                        poster=series.poster_url,
                        backdrop=series.backdrop_url,
                        rating=series.vote_average,
                        vote_count=series.vote_count,
                        genres=series.genres,
                        seasons=series.number_of_seasons,
                        episodes=series.number_of_episodes,
                        status=series.status,
                    )
                    # Try to find on StreamingCommunity
                    await _enrich_with_provider(result)
                    results.series.append(result)

            results.total += len(results.films) + len(results.series)
        else:
            # Fallback to direct StreamingCommunity search
            sc_results = await _search_streamingcommunity_direct(q, type)
            for item in sc_results:
                if item.type == "film":
                    results.films.append(item)
                else:
                    results.series.append(item)
            results.total += len(sc_results)

    logger.info(f"Search '{q}' returned {results.total} results")
    return results


@router.get("/anime", response_model=List[SearchResult])
async def search_anime_only(
    q: str = Query(..., min_length=2, description="Search query"),
):
    """Search for anime only (AnimeWorld)."""
    return await _search_anime(q)


@router.get("/movies", response_model=List[SearchResult])
async def search_movies(
    q: str = Query(..., min_length=2, description="Search query"),
):
    """Search for movies with TMDB metadata."""
    tmdb = get_tmdb()
    results = []

    if tmdb.is_available():
        movies = await tmdb.search_movie(q)
        for movie in movies:
            result = SearchResult(
                name=movie.title,
                type="film",
                year=movie.year,
                tmdb_id=movie.id,
                overview=movie.overview,
                poster=movie.poster_url,
                backdrop=movie.backdrop_url,
                rating=movie.vote_average,
                vote_count=movie.vote_count,
                runtime=movie.runtime,
            )
            await _enrich_with_provider(result)
            results.append(result)
    else:
        results = await _search_streamingcommunity_direct(q, MediaType.film)

    return results


@router.get("/series", response_model=List[SearchResult])
async def search_series_only(
    q: str = Query(..., min_length=2, description="Search query"),
):
    """Search for TV series with TMDB metadata."""
    tmdb = get_tmdb()
    results = []

    if tmdb.is_available():
        series_list = await tmdb.search_tv(q)
        for series in series_list:
            result = SearchResult(
                name=series.name,
                type="series",
                year=series.year,
                tmdb_id=series.id,
                overview=series.overview,
                poster=series.poster_url,
                backdrop=series.backdrop_url,
                rating=series.vote_average,
                vote_count=series.vote_count,
                seasons=series.number_of_seasons,
                episodes=series.number_of_episodes,
                status=series.status,
            )
            await _enrich_with_provider(result)
            results.append(result)
    else:
        results = await _search_streamingcommunity_direct(q, MediaType.series)

    return results


@router.get("/trending", response_model=TrendingResponse)
async def get_trending():
    """Get trending movies and series from TMDB."""
    tmdb = get_tmdb()

    if not tmdb.is_available():
        return TrendingResponse()

    movies = []
    series = []

    # Get trending movies
    trending_movies = await tmdb.get_trending_movies()
    for movie in trending_movies:
        result = SearchResult(
            name=movie.title,
            type="film",
            year=movie.year,
            tmdb_id=movie.id,
            overview=movie.overview,
            poster=movie.poster_url,
            backdrop=movie.backdrop_url,
            rating=movie.vote_average,
            vote_count=movie.vote_count,
        )
        movies.append(result)

    # Get trending series
    trending_series = await tmdb.get_trending_tv()
    for tv in trending_series:
        result = SearchResult(
            name=tv.name,
            type="series",
            year=tv.year,
            tmdb_id=tv.id,
            overview=tv.overview,
            poster=tv.poster_url,
            backdrop=tv.backdrop_url,
            rating=tv.vote_average,
            vote_count=tv.vote_count,
        )
        series.append(result)

    return TrendingResponse(movies=movies, series=series)


@router.get("/tmdb/movie/{movie_id}", response_model=SearchResult)
async def get_movie_details(movie_id: int):
    """Get detailed movie info from TMDB."""
    tmdb = get_tmdb()

    if not tmdb.is_available():
        return SearchResult(name="TMDB not configured", type="film")

    movie = await tmdb.get_movie(movie_id)
    if not movie:
        return SearchResult(name="Movie not found", type="film")

    result = SearchResult(
        name=movie.title,
        type="film",
        year=movie.year,
        tmdb_id=movie.id,
        overview=movie.overview,
        poster=movie.poster_url,
        backdrop=movie.backdrop_url,
        rating=movie.vote_average,
        vote_count=movie.vote_count,
        genres=movie.genres,
        runtime=movie.runtime,
        status=movie.status,
    )

    # Try to find on provider
    await _enrich_with_provider(result)

    return result


@router.get("/tmdb/series/{series_id}", response_model=SearchResult)
async def get_series_details(series_id: int):
    """Get detailed series info from TMDB."""
    tmdb = get_tmdb()

    if not tmdb.is_available():
        return SearchResult(name="TMDB not configured", type="series")

    series = await tmdb.get_tv(series_id)
    if not series:
        return SearchResult(name="Series not found", type="series")

    result = SearchResult(
        name=series.name,
        type="series",
        year=series.year,
        tmdb_id=series.id,
        overview=series.overview,
        poster=series.poster_url,
        backdrop=series.backdrop_url,
        rating=series.vote_average,
        vote_count=series.vote_count,
        genres=series.genres,
        seasons=series.number_of_seasons,
        episodes=series.number_of_episodes,
        status=series.status,
    )

    # Try to find on provider
    await _enrich_with_provider(result)

    return result


# ==================== Search Helpers ====================

async def _search_anime(query: str) -> List[SearchResult]:
    """Search for anime with AniList metadata + AnimeWorld download links."""
    results = []
    anilist = get_anilist()

    try:
        # Search AniList for rich metadata
        anilist_results = await anilist.search_anime(query, limit=10)

        for anime in anilist_results:
            synopsis = anime.get("synopsis", "") or ""
            results.append(SearchResult(
                name=anime.get("name", ""),
                type="anime",
                year=str(anime.get("year")) if anime.get("year") else None,
                mal_id=anime.get("anilist_id"),
                overview=synopsis[:300] + "..." if len(synopsis) > 300 else synopsis,
                poster=anime.get("poster_url", ""),
                rating=anime.get("rating", 0),
                genres=anime.get("genres", []),
                episodes=anime.get("episodes"),
                status=anime.get("status", ""),
            ))

    except Exception as e:
        logger.error(f"AniList anime search error: {e}")

    # Fallback to AnimeWorld if Jikan fails or as supplement
    try:
        miko = Miko()
        anime_list = await miko.findAnime(query)

        for anime in anime_list[:10]:
            name = anime.getName() if hasattr(anime, 'getName') else str(anime)
            link = anime.getLink() if hasattr(anime, 'getLink') else None
            cover = anime.getCover() if hasattr(anime, 'getCover') else None

            # Check if we already have this anime from Jikan
            existing = next((r for r in results if r.name.lower() == name.lower()), None)
            
            if not existing:
                results.append(SearchResult(
                    name=name,
                    type="anime",
                    poster=cover,
                    provider="animeworld",
                    provider_url=link,
                ))
            else:
                # Update existing result with download info
                existing.provider = "animeworld"
                existing.provider_url = link
                if not existing.poster and cover:
                    existing.poster = cover

    except Exception as e:
        logger.error(f"AnimeWorld search error: {e}")

    return results


def get_miko_sc_instance():
    """Get StreamingCommunity Miko instance."""
    global _miko_sc
    if _miko_sc is None:
        from yuna.services.media_service import MikoSC
        _miko_sc = MikoSC()
    return _miko_sc


async def _search_streamingcommunity_direct(query: str, media_type: MediaType) -> List[SearchResult]:
    """Direct search on StreamingCommunity (fallback when TMDB unavailable)."""
    results = []

    try:
        miko_sc = get_miko_sc_instance()
        
        if not miko_sc:
            logger.error("MikoSC not available")
            return []

        if media_type == MediaType.series:
            items = miko_sc.search_series(query)
        elif media_type == MediaType.film:
            items = miko_sc.search_films(query)
        else:
            items = miko_sc.search(query)

        for item in items[:10]:
            item_type = "film" if getattr(item, 'type', '') == 'movie' else "series"

            results.append(SearchResult(
                name=item.name,
                type=item_type,
                year=getattr(item, 'year', None),
                poster=getattr(item, 'poster', None),
                provider="streamingcommunity",
                provider_url=getattr(item, 'url', None),
                provider_id=getattr(item, 'id', None),
                provider_slug=getattr(item, 'slug', None),
            ))

    except Exception as e:
        logger.error(f"StreamingCommunity search error: {e}")

    return results


async def _enrich_with_provider(result: SearchResult):
    """Try to find download link on StreamingCommunity."""
    try:
        miko_sc = get_miko_sc_instance()
        
        if not miko_sc:
            return

        # Search for matching title
        if result.type == "film":
            items = miko_sc.search_films(result.name)
        else:
            items = miko_sc.search_series(result.name)

        if items:
            # Try to find best match by name and year
            best_match = None
            for item in items:
                if item.name.lower() == result.name.lower():
                    # Exact match
                    best_match = item
                    break
                if result.year and getattr(item, 'year', '') == result.year:
                    # Year match
                    best_match = item
                    break

            if not best_match and items:
                # Use first result
                best_match = items[0]

            if best_match:
                result.provider = "streamingcommunity"
                result.provider_url = getattr(best_match, 'url', None)
                result.provider_id = getattr(best_match, 'id', None)
                result.provider_slug = getattr(best_match, 'slug', None)

    except Exception as e:
        logger.debug(f"Provider enrichment failed for '{result.name}': {e}")


@router.get("/anime/jikan", response_model=List[SearchResult])
async def search_anime_jikan(
    q: str = Query(..., min_length=2, description="Search query for Jikan API"),
    limit: int = Query(10, ge=1, le=25, description="Maximum number of results"),
):
    """
    Search anime using Jikan API (MyAnimeList metadata).

    Provides rich anime metadata including:
    - MyAnimeList ID
    - English/Japanese titles
    - Synopsis and description
    - Rating and popularity
    - Genres and studios
    - Episode count and status
    - Poster images
    """
    anilist = get_anilist()
    results = []

    try:
        anilist_results = await anilist.search_anime(q, limit=limit)

        for anime in anilist_results:
            synopsis = anime.get("synopsis") or ""
            results.append(SearchResult(
                name=anime.get("name"),
                type="anime",
                year=str(anime.get("year")) if anime.get("year") else None,
                mal_id=anime.get("anilist_id"),
                overview=synopsis[:300] + "..." if len(synopsis) > 300 else synopsis,
                poster=anime.get("poster_url"),
                rating=anime.get("rating"),
                genres=anime.get("genres", []),
                episodes=anime.get("episodes"),
                status=anime.get("status"),
            ))

    except Exception as e:
        logger.error(f"Jikan anime search error: {e}")
        raise HTTPException(status_code=500, detail=f"Jikan search failed: {str(e)}")

    return results


# IMPORTANT: Static routes must come BEFORE parameterized routes in FastAPI
@router.get("/anime/jikan/top", response_model=List[SearchResult])
async def get_top_anime_jikan(
    type_filter: Optional[str] = Query(None, description="Filter by type: tv, movie, ova, special"),
    limit: int = Query(10, ge=1, le=25, description="Maximum number of results"),
):
    """
    Get top anime from MyAnimeList via Jikan API.
    """
    anilist = get_anilist()
    results = []

    try:
        anilist_results = await anilist.get_top_anime(type_filter=type_filter, limit=limit)

        for anime in anilist_results:
            synopsis = anime.get("synopsis") or ""
            results.append(SearchResult(
                name=anime.get("name"),
                type="anime",
                year=str(anime.get("year")) if anime.get("year") else None,
                mal_id=anime.get("anilist_id"),
                overview=synopsis[:300] + "..." if len(synopsis) > 300 else synopsis,
                poster=anime.get("poster_url"),
                rating=anime.get("rating"),
                genres=anime.get("genres", []),
                episodes=anime.get("episodes"),
                status=anime.get("status"),
            ))

    except Exception as e:
        logger.error(f"Jikan top anime error: {e}")
        raise HTTPException(status_code=500, detail=f"Jikan API error: {str(e)}")

    return results


@router.get("/anime/jikan/seasonal", response_model=List[SearchResult])
async def get_seasonal_anime_jikan(
    year: Optional[int] = Query(None, description="Year (defaults to current)"),
    season: Optional[str] = Query(None, description="Season: winter, spring, summer, fall"),
    limit: int = Query(10, ge=1, le=25, description="Maximum number of results"),
):
    """
    Get seasonal anime from MyAnimeList via Jikan API.
    """
    anilist = get_anilist()
    results = []

    try:
        anilist_results = await anilist.get_seasonal_anime(year=year, season=season, limit=limit)

        for anime in anilist_results:
            synopsis = anime.get("synopsis") or ""
            results.append(SearchResult(
                name=anime.get("name"),
                type="anime",
                year=str(anime.get("year")) if anime.get("year") else None,
                mal_id=anime.get("anilist_id"),
                overview=synopsis[:300] + "..." if len(synopsis) > 300 else synopsis,
                poster=anime.get("poster_url"),
                rating=anime.get("rating"),
                genres=anime.get("genres", []),
                episodes=anime.get("episodes"),
                status=anime.get("status"),
            ))

    except Exception as e:
        logger.error(f"Jikan seasonal anime error: {e}")
        raise HTTPException(status_code=500, detail=f"Jikan API error: {str(e)}")

    return results


# Parameterized route MUST come AFTER static routes like /top and /seasonal
@router.get("/anime/jikan/{mal_id}", response_model=SearchResult)
async def get_anime_jikan(mal_id: int):
    """
    Get detailed anime information from Jikan API by MyAnimeList ID.
    """
    anilist = get_anilist()

    try:
        anime = await anilist.get_anime_by_id(mal_id)
        if not anime:
            raise HTTPException(status_code=404, detail="Anime not found")

        return SearchResult(
            name=anime.get("name"),
            type="anime",
            year=str(anime.get("year")) if anime.get("year") else None,
            mal_id=anime.get("anilist_id"),
            overview=anime.get("synopsis") or "",
            poster=anime.get("poster_url"),
            rating=anime.get("rating"),
            genres=anime.get("genres", []),
            episodes=anime.get("episodes"),
            status=anime.get("status"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Jikan anime details error: {e}")
        raise HTTPException(status_code=500, detail=f"Jikan API error: {str(e)}")
