"""
Anime API Routes.
CRUD operations and download management for anime library.
"""

import asyncio
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, HttpUrl

from yuna.api.deps import DbDep, CurrentUser
from yuna.services.media_service import Miko
from yuna.providers.jikan import JikanClient
from yuna.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/anime", tags=["Anime"])


# ==================== Schemas ====================

class AnimeBase(BaseModel):
    """Base anime schema."""
    name: str
    link: str
    episodes_downloaded: int = 0
    episodes_total: int = 0
    last_update: Optional[str] = None
    # Jikan metadata
    mal_id: Optional[int] = None
    synopsis: Optional[str] = None
    rating: Optional[float] = None
    year: Optional[int] = None
    genres: List[str] = []
    status: Optional[str] = None
    poster_url: Optional[str] = None


class AnimeListResponse(BaseModel):
    """Response for anime list."""
    items: List[AnimeBase]
    total: int


class AnimeDetail(AnimeBase):
    """Detailed anime info."""
    missing_episodes: List[int] = []
    folder_path: Optional[str] = None


class AnimeAddRequest(BaseModel):
    """Request to add anime."""
    url: str  # AnimeWorld URL


class AnimeAddResponse(BaseModel):
    """Response after adding anime."""
    success: bool
    name: str
    message: str


class DownloadRequest(BaseModel):
    """Request to download episodes."""
    episodes: Optional[List[int]] = None  # None = all missing


class DownloadResponse(BaseModel):
    """Response for download request."""
    success: bool
    message: str
    task_id: Optional[str] = None
    episodes_queued: int = 0


class EpisodeInfo(BaseModel):
    """Episode information."""
    number: int
    downloaded: bool


class EpisodesResponse(BaseModel):
    """Response for episodes list."""
    anime_name: str
    total: int
    downloaded: int
    missing: List[int]
    episodes: List[EpisodeInfo]


# ==================== Active Downloads Tracking ====================

# Simple in-memory tracking of active downloads
_active_downloads: dict = {}

# Jikan client singleton
_jikan_client: Optional[JikanClient] = None


def get_jikan() -> JikanClient:
    """Get Jikan client singleton."""
    global _jikan_client
    if _jikan_client is None:
        _jikan_client = JikanClient()
    return _jikan_client


def get_download_status(anime_name: str) -> Optional[dict]:
    """Get status of active download."""
    return _active_downloads.get(anime_name)


def set_download_status(anime_name: str, status: dict):
    """Set download status."""
    _active_downloads[anime_name] = status


def clear_download_status(anime_name: str):
    """Clear download status."""
    _active_downloads.pop(anime_name, None)


# ==================== Routes ====================

@router.get("", response_model=AnimeListResponse)
async def list_anime(db: DbDep):
    """
    Get all anime in library.

    Returns list of anime with basic info.
    """
    anime_list = db.get_all_anime()

    items = []
    for a in anime_list:
        base = AnimeBase(
            name=a["name"],
            link=a.get("link", ""),
            episodes_downloaded=a.get("episodi_scaricati", 0),
            episodes_total=a.get("numero_episodi", 0),
            last_update=a.get("last_update"),
            # Try to get Jikan metadata from database
            mal_id=a.get("mal_id"),
            synopsis=a.get("synopsis"),
            rating=a.get("rating"),
            year=a.get("year"),
            genres=a.get("genres", "").split(",") if a.get("genres") else [],
            status=a.get("status"),
            poster_url=a.get("poster_url"),
        )
        items.append(base)

    return AnimeListResponse(items=items, total=len(items))


@router.get("/{name}", response_model=AnimeDetail)
async def get_anime(name: str, db: DbDep):
    """
    Get detailed info for a specific anime.

    Includes missing episodes list.
    """
    anime = db.get_anime_by_name(name)

    if not anime:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anime '{name}' not found"
        )

    # Calculate missing episodes (using Italian field names from DB)
    downloaded = anime.get("episodi_scaricati", 0)
    total = anime.get("numero_episodi", 0)

    # Simple missing calculation (assumes sequential episodes)
    missing = list(range(downloaded + 1, total + 1)) if total > downloaded else []

    return AnimeDetail(
        name=anime["name"],
        link=anime.get("link", ""),
        episodes_downloaded=downloaded,
        episodes_total=total,
        last_update=anime.get("last_update"),
        missing_episodes=missing,
        folder_path=None,  # Could be populated from Airi
    )


@router.post("", response_model=AnimeAddResponse)
async def add_anime(request: AnimeAddRequest, db: DbDep, user: CurrentUser):
    """
    Add a new anime to library.

    Requires AnimeWorld URL. Will fetch anime info and add to database.
    Requires authentication.
    """
    url = request.url.strip()

    # Validate URL - must be an AnimeWorld URL
    if not any(domain in url.lower() for domain in ["animeworld.tv", "animeworld.so", "animeworld.ac"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL must be from AnimeWorld (animeworld.tv, animeworld.so, or animeworld.ac)"
        )

    try:
        # Extract anime name from URL for Jikan search
        from urllib.parse import urlparse
        import re
        
        parsed_url = urlparse(url)
        path_parts = parsed_url.path.strip('/').split('/')
        
        # Try to extract anime name from URL path
        anime_name = None
        if len(path_parts) > 1:
            potential_name = path_parts[-1].replace('-', ' ').title()
            anime_name = potential_name
        
        # Initialize Jikan metadata
        jikan_metadata = {}
        
        # Try to get Jikan metadata
        if anime_name:
            try:
                jikan = get_jikan()
                jikan_results = await jikan.search_anime(anime_name, limit=1)
                
                if jikan_results:
                    anime = jikan_results[0]
                    jikan_metadata = {
                        "mal_id": anime.mal_id,
                        "synopsis": anime.synopsis[:500],  # Limit length
                        "rating": anime.score,
                        "year": anime.year,
                        "genres": ",".join(anime.genre_names),
                        "status": anime.status,
                        "poster_url": anime.poster_url,
                    }
                    logger.info(f"Found Jikan metadata for {anime_name}: MAL ID {anime.mal_id}")
                
            except Exception as e:
                logger.warning(f"Jikan metadata fetch failed for {anime_name}: {e}")

        # Use Miko to add anime
        miko = Miko()
        result = await miko.addAnime(url)

        if result:
            # Update database with Jikan metadata if available
            if jikan_metadata and miko.anime_name:
                try:
                    db.update_anime(miko.anime_name, **jikan_metadata)
                    logger.info(f"Updated {miko.anime_name} with Jikan metadata")
                except Exception as e:
                    logger.warning(f"Failed to update anime with Jikan metadata: {e}")

            return AnimeAddResponse(
                success=True,
                name=miko.anime_name or "Unknown",
                message=f"Anime '{miko.anime_name}' added successfully" + (" with Jikan metadata" if jikan_metadata else "")
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to add anime. Check URL and try again."
            )

    except Exception as e:
        logger.error(f"Error adding anime: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/{name}")
async def remove_anime(name: str, db: DbDep, user: CurrentUser):
    """
    Remove anime from library.

    Does NOT delete downloaded files.
    Requires authentication.
    """
    anime = db.get_anime_by_name(name)

    if not anime:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anime '{name}' not found"
        )

    try:
        # Remove from database only (not files)
        db.remove_anime(name)

        return {
            "success": True,
            "message": f"Anime '{name}' removed from library"
        }

    except Exception as e:
        logger.error(f"Error removing anime: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{name}/episodes", response_model=EpisodesResponse)
async def get_episodes(name: str, db: DbDep):
    """
    Get episode list for an anime.

    Shows which episodes are downloaded and which are missing.
    """
    anime = db.get_anime_by_name(name)

    if not anime:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anime '{name}' not found"
        )

    downloaded = anime.get("episodi_scaricati", 0)
    total = anime.get("numero_episodi", 0)

    # Build episode list
    episodes = []
    missing = []

    for i in range(1, total + 1):
        is_downloaded = i <= downloaded
        episodes.append(EpisodeInfo(number=i, downloaded=is_downloaded))
        if not is_downloaded:
            missing.append(i)

    return EpisodesResponse(
        anime_name=name,
        total=total,
        downloaded=downloaded,
        missing=missing,
        episodes=episodes,
    )


@router.post("/{name}/download", response_model=DownloadResponse)
async def download_episodes(
    name: str,
    request: DownloadRequest,
    background_tasks: BackgroundTasks,
    db: DbDep,
    user: CurrentUser
):
    """
    Start downloading episodes for an anime.

    If episodes list is provided, downloads those specific episodes.
    If not provided, downloads all missing episodes.

    Download runs in background. Use GET /api/downloads to check status.
    Requires authentication.
    """
    anime = db.get_anime_by_name(name)

    if not anime:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anime '{name}' not found"
        )

    # Check if already downloading
    if get_download_status(name):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Download already in progress for '{name}'"
        )

    link = anime.get("link")
    if not link:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No AnimeWorld link found for '{name}'"
        )

    # Determine which episodes to download
    episodes_to_download = request.episodes

    if not episodes_to_download:
        # Get missing episodes
        downloaded = anime.get("episodi_scaricati", 0)
        total = anime.get("numero_episodi", 0)
        episodes_to_download = list(range(downloaded + 1, total + 1))

    if not episodes_to_download:
        return DownloadResponse(
            success=True,
            message="No episodes to download",
            episodes_queued=0
        )

    # Start background download
    task_id = f"anime_{name}"
    set_download_status(name, {
        "status": "starting",
        "episodes": episodes_to_download,
        "progress": 0,
        "current_episode": None,
    })

    background_tasks.add_task(
        _download_anime_task,
        name=name,
        link=link,
        episodes=episodes_to_download,
    )

    return DownloadResponse(
        success=True,
        message=f"Download started for {len(episodes_to_download)} episodes",
        task_id=task_id,
        episodes_queued=len(episodes_to_download),
    )


@router.get("/{name}/download/status")
async def get_download_progress(name: str):
    """
    Get download progress for an anime.

    Returns current download status if active.
    """
    status = get_download_status(name)

    if not status:
        return {
            "active": False,
            "message": "No active download"
        }

    return {
        "active": True,
        **status
    }


@router.delete("/{name}/download")
async def cancel_download(name: str, user: CurrentUser):
    """
    Cancel active download for an anime.

    Note: May not stop immediately if episode is mid-download.
    Requires authentication.
    """
    status = get_download_status(name)

    if not status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active download to cancel"
        )

    # Mark as cancelled
    set_download_status(name, {**status, "status": "cancelled"})

    return {
        "success": True,
        "message": f"Download cancelled for '{name}'"
    }


# ==================== Background Tasks ====================

async def _download_anime_task(name: str, link: str, episodes: List[int]):
    """
    Background task to download anime episodes.
    """
    try:
        logger.info(f"Starting download task for {name}: {len(episodes)} episodes")

        # Create Miko instance
        miko = Miko()
        await miko.loadAnime(link)

        if not miko.anime:
            logger.error(f"Failed to load anime: {name}")
            set_download_status(name, {
                "status": "failed",
                "error": "Failed to load anime from AnimeWorld"
            })
            return

        set_download_status(name, {
            "status": "downloading",
            "episodes": episodes,
            "progress": 0,
            "completed": 0,
            "failed": 0,
            "current_episode": None,
        })

        # Progress callback
        completed = 0
        failed = 0

        async def progress_callback(ep_num, progress, done=False):
            nonlocal completed, failed

            current_status = get_download_status(name)
            if current_status and current_status.get("status") == "cancelled":
                raise asyncio.CancelledError("Download cancelled by user")

            if done and progress >= 1.0:
                completed += 1

            overall_progress = (completed / len(episodes)) * 100 if episodes else 0

            set_download_status(name, {
                "status": "downloading",
                "episodes": episodes,
                "progress": overall_progress,
                "completed": completed,
                "failed": failed,
                "current_episode": ep_num,
            })

        # Download episodes
        await miko.downloadEpisodes(episodes, progress_callback=progress_callback)

        # Mark complete
        final_status = get_download_status(name)
        completed = final_status.get("completed", 0) if final_status else 0

        set_download_status(name, {
            "status": "completed",
            "episodes": episodes,
            "progress": 100,
            "completed": completed,
            "failed": len(episodes) - completed,
        })

        logger.info(f"Download complete for {name}: {completed}/{len(episodes)} episodes")

        # Clear status after delay
        await asyncio.sleep(60)
        clear_download_status(name)

    except asyncio.CancelledError:
        logger.info(f"Download cancelled for {name}")
        clear_download_status(name)

    except Exception as e:
        logger.error(f"Download error for {name}: {e}")
        set_download_status(name, {
            "status": "failed",
            "error": str(e),
        })

        # Clear after delay
        await asyncio.sleep(60)
        clear_download_status(name)
