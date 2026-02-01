"""
Anime API Routes.
CRUD operations and download management for anime library.
"""

import asyncio
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, HttpUrl

from yuna.api.deps import DbDep, CurrentUser
from yuna.services.media_service import Miko
from yuna.providers.anilist import AniListClient
from yuna.config import config
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
    # AniList metadata
    anilist_id: Optional[int] = None
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
    episodes_available: Optional[int] = None  # Episodes available on AnimeWorld
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

# AniList client singleton
_anilist_client: Optional[AniListClient] = None


def get_anilist() -> AniListClient:
    """Get AniList client singleton."""
    global _anilist_client
    if _anilist_client is None:
        _anilist_client = AniListClient(access_token=config.anilist_access_token)
    return _anilist_client


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
            # Try to get AniList metadata from database
            anilist_id=a.get("anilist_id"),
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

    Includes missing episodes list and AniList metadata.
    Uses AnimeWorld to determine available episodes.
    """
    anime = db.get_anime_by_name(name)

    if not anime:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anime '{name}' not found"
        )

    # Get downloaded count from DB
    downloaded = anime.get("episodi_scaricati", 0)
    total_anilist = anime.get("numero_episodi", 0)
    episodes_available = anime.get("episodi_disponibili", 0) or None
    
    # Calculate missing episodes based on available vs downloaded
    missing = []
    if episodes_available and episodes_available > 0:
        # We know how many are available, calculate missing
        missing = [n for n in range(1, episodes_available + 1) if n > downloaded]
    elif total_anilist > downloaded:
        # Fallback: use total from AniList
        missing = list(range(downloaded + 1, total_anilist + 1))

    return AnimeDetail(
        name=anime["name"],
        link=anime.get("link", ""),
        episodes_downloaded=downloaded,
        episodes_total=total_anilist,  # Total from AniList (includes not yet aired)
        episodes_available=episodes_available,  # Available from DB (or None)
        last_update=anime.get("last_update"),
        missing_episodes=missing,  # Only available but not downloaded
        folder_path=None,
        # AniList metadata
        anilist_id=anime.get("anilist_id"),
        synopsis=anime.get("synopsis"),
        rating=anime.get("rating"),
        year=anime.get("year"),
        genres=anime.get("genres", "").split(",") if anime.get("genres") else [],
        status=anime.get("status"),
        poster_url=anime.get("poster_url"),
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
        # Extract anime name from URL for AniList search
        from urllib.parse import urlparse
        import re
        
        parsed_url = urlparse(url)
        path_parts = parsed_url.path.strip('/').split('/')
        
        # Try to extract anime name from URL path
        anime_name = None
        if len(path_parts) > 1:
            potential_name = path_parts[-1].replace('-', ' ').title()
            anime_name = potential_name
        
        # Initialize AniList metadata
        anilist_metadata = {}
        
        # Try to get AniList metadata
        if anime_name:
            try:
                anilist = get_anilist()
                anilist_results = await anilist.search_anime(anime_name, limit=1)
                
                if anilist_results:
                    anime = anilist_results[0]
                    anilist_metadata = {
                        "anilist_id": anime.get("anilist_id"),
                        "synopsis": anime.get("synopsis", "")[:500] if anime.get("synopsis") else "",
                        "rating": anime.get("rating", 0),
                        "year": anime.get("year"),
                        "genres": ",".join(anime.get("genres", [])),
                        "status": anime.get("status", ""),
                        "poster_url": anime.get("poster_url", ""),
                    }
                    logger.info(f"Found AniList metadata for {anime_name}: AniList ID {anime.get('anilist_id')}")
                
            except Exception as e:
                logger.warning(f"AniList metadata fetch failed for {anime_name}: {e}")

        # Use Miko to add anime
        miko = Miko()
        result = await miko.addAnime(url)

        if result:
            # Update database with AniList metadata if available
            if anilist_metadata and miko.anime_name:
                try:
                    db.update_anime(miko.anime_name, **anilist_metadata)
                    logger.info(f"Updated {miko.anime_name} with AniList metadata")
                except Exception as e:
                    logger.warning(f"Failed to update anime with AniList metadata: {e}")

            return AnimeAddResponse(
                success=True,
                name=miko.anime_name or "Unknown",
                message=f"Anime '{miko.anime_name}' added successfully" + (" with AniList metadata" if anilist_metadata else "")
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


class AnimeMetadataUpdate(BaseModel):
    """Update anime metadata from AniList."""
    anilist_id: Optional[int] = None
    synopsis: Optional[str] = None
    rating: Optional[float] = None
    year: Optional[int] = None
    genres: Optional[str] = None  # Comma-separated
    status: Optional[str] = None
    poster_url: Optional[str] = None


class AddFromAnilistRequest(BaseModel):
    """Request to add anime from AniList without provider."""
    anilist_id: int


class AssociateProviderRequest(BaseModel):
    """Request to associate provider to existing anime."""
    provider_url: str


@router.patch("/{name}", response_model=AnimeDetail)
async def update_anime_metadata(name: str, request: AnimeMetadataUpdate, db: DbDep, user: CurrentUser):
    """
    Update anime metadata from AniList.
    
    Requires authentication.
    """
    anime = db.get_anime_by_name(name)

    if not anime:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anime '{name}' not found"
        )

    try:
        update_data = {}
        
        # If anilist_id is provided, fetch metadata from AniList
        if request.anilist_id is not None:
            anilist = get_anilist()
            try:
                anilist_data = await anilist.get_anime_by_id(request.anilist_id)
                if anilist_data:
                    # Merge AniList data into update_data
                    update_data["anilist_id"] = request.anilist_id
                    update_data["synopsis"] = anilist_data.get("synopsis")
                    update_data["rating"] = anilist_data.get("rating")
                    update_data["year"] = anilist_data.get("year")
                    update_data["genres"] = ','.join(anilist_data.get("genres", []))
                    update_data["status"] = anilist_data.get("status")
                    update_data["poster_url"] = anilist_data.get("poster_url")
                    # Update total episodes if available
                    if anilist_data.get("episodes"):
                        update_data["numero_episodi"] = anilist_data["episodes"]
                    logger.info(f"Fetched metadata from AniList for anime '{name}'")
                else:
                    update_data["anilist_id"] = request.anilist_id
            except Exception as e:
                logger.error(f"Error fetching AniList data: {e}")
                update_data["anilist_id"] = request.anilist_id
        
        # Allow manual overrides
        if request.synopsis is not None:
            update_data["synopsis"] = request.synopsis
        if request.rating is not None:
            update_data["rating"] = request.rating
        if request.year is not None:
            update_data["year"] = request.year
        if request.genres is not None:
            update_data["genres"] = request.genres
        if request.status is not None:
            update_data["status"] = request.status
        if request.poster_url is not None:
            update_data["poster_url"] = request.poster_url

        db.update_anime(name, **update_data)
        logger.info(f"Updated metadata for anime '{name}' with fields: {list(update_data.keys())}")

        # Return updated anime detail
        updated_anime = db.get_anime_by_name(name)
        
        # Calculate missing episodes
        downloaded = updated_anime.get("episodi_scaricati", 0)
        total = updated_anime.get("numero_episodi", 0)
        missing = list(range(downloaded + 1, total + 1)) if total > downloaded else []

        return AnimeDetail(
            name=updated_anime["name"],
            link=updated_anime.get("link", ""),
            episodes_downloaded=downloaded,
            episodes_total=total,
            last_update=updated_anime.get("last_update"),
            missing_episodes=missing,
            folder_path=None,
            anilist_id=updated_anime.get("anilist_id"),
            synopsis=updated_anime.get("synopsis"),
            rating=updated_anime.get("rating"),
            year=updated_anime.get("year"),
            genres=updated_anime.get("genres", "").split(",") if updated_anime.get("genres") else [],
            status=updated_anime.get("status"),
            poster_url=updated_anime.get("poster_url"),
        )
    except Exception as e:
        logger.error(f"Error updating anime metadata: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/{name}/refresh-episodes")
async def refresh_available_episodes(name: str, db: DbDep, user: CurrentUser):
    """
    Refresh available episodes count from AnimeWorld.
    
    Updates the episodi_disponibili field in database.
    Requires authentication.
    """
    anime = db.get_anime_by_name(name)

    if not anime:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anime '{name}' not found"
        )

    try:
        miko = Miko()
        anime_link = anime.get("link", "")
        
        if not anime_link:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Anime has no AnimeWorld link"
            )

        # Load anime from AnimeWorld
        await miko.loadAnime(anime_link)
        
        # Get episodes
        available_episodes = await miko.getEpisodes()
        
        if available_episodes and len(available_episodes) > 0:
            # Get max episode number
            max_available = max(int(ep.number) for ep in available_episodes if hasattr(ep, 'number'))
            
            # Update database
            db.update_anime_available_episodes(name, max_available)
            logger.info(f"Updated available episodes for '{name}': {max_available}")
            
            return {
                "success": True,
                "episodes_available": max_available,
                "message": f"Trovati {max_available} episodi disponibili"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Nessun episodio trovato su AnimeWorld"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing episodes for '{name}': {e}")
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


@router.delete("/{name}")
async def delete_anime(
    name: str,
    db: DbDep,
    current_user: CurrentUser
):
    """
    Delete anime completely.
    
    Removes:
    - Database entry
    - All downloaded files and folders
    """
    import shutil
    import os
    
    # Verify anime exists
    anime = db.get_anime_by_name(name)
    if not anime:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anime '{name}' not found"
        )
    
    # Get anime folder path
    anime_folder = os.getenv("ANIME_FOLDER", "/downloads/anime")
    anime_path = os.path.join(anime_folder, name)
    
    logger.info(f"Attempting to delete anime '{name}'")
    logger.info(f"Anime folder: {anime_folder}")
    logger.info(f"Full path: {anime_path}")
    logger.info(f"Path exists: {os.path.exists(anime_path)}")
    
    # Delete files if folder exists
    deleted_files = False
    if os.path.exists(anime_path):
        try:
            shutil.rmtree(anime_path)
            deleted_files = True
            logger.info(f"Deleted files for anime '{name}' at {anime_path}")
        except Exception as e:
            logger.error(f"Error deleting files for anime '{name}': {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error deleting files: {str(e)}"
            )
    else:
        logger.warning(f"Anime folder does not exist at {anime_path}")
    
    # Delete from database
    try:
        success = db.delete_anime(name)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete anime from database"
            )
        logger.info(f"Deleted anime '{name}' from database")
    except Exception as e:
        logger.error(f"Error deleting anime '{name}' from database: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
    
    return {
        "success": True,
        "message": f"Anime '{name}' deleted successfully",
        "files_deleted": deleted_files
    }


@router.post("/from-anilist", response_model=AnimeDetail)
async def add_anime_from_anilist(
    request: AddFromAnilistRequest,
    db: DbDep,
    user: CurrentUser
):
    """
    Add anime from AniList without provider.
    Creates entry with metadata only, provider can be associated later.
    """
    try:
        # Fetch metadata from AniList
        anilist = get_anilist()
        anilist_data = await anilist.get_anime_by_id(request.anilist_id)
        
        if not anilist_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Anime with AniList ID {request.anilist_id} not found"
            )
        
        anime_name = anilist_data.get("name", "Unknown")
        
        # Check if anime already exists
        existing = db.get_anime_by_name(anime_name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Anime '{anime_name}' already exists in library"
            )
        
        # Create anime entry without provider link
        # First add basic fields
        db.add_anime(
            name=anime_name,
            link="",  # No provider yet
            last_update=datetime.now(),
            numero_episodi=anilist_data.get("episodes", 0)
        )
        
        # Then update with metadata fields
        db.update_anime(
            name=anime_name,
            anilist_id=request.anilist_id,
            synopsis=anilist_data.get("synopsis", "")[:500] if anilist_data.get("synopsis") else "",
            rating=anilist_data.get("rating"),
            year=anilist_data.get("year"),
            genres=",".join(anilist_data.get("genres", [])),
            status=anilist_data.get("status", ""),
            poster_url=anilist_data.get("poster_url", "")
        )
        
        logger.info(f"Added anime '{anime_name}' from AniList (ID: {request.anilist_id}) without provider")

        return AnimeDetail(
            name=anime_name,
            link="",
            episodes_downloaded=0,
            episodes_total=anilist_data.get("episodes", 0),
            missing_episodes=[],
            anilist_id=request.anilist_id,
            synopsis=anilist_data.get("synopsis", ""),
            rating=anilist_data.get("rating"),
            year=anilist_data.get("year"),
            genres=anilist_data.get("genres", []),
            status=anilist_data.get("status", ""),
            poster_url=anilist_data.get("poster_url", ""),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding anime from AniList: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/{name}/associate-provider", response_model=AnimeDetail)
async def associate_anime_provider(
    name: str,
    request: AssociateProviderRequest,
    db: DbDep,
    user: CurrentUser
):
    """
    Associate provider (AnimeWorld) to existing anime.
    Updates anime with provider link and refreshes episode info.
    """
    # Verify anime exists
    anime = db.get_anime_by_name(name)
    if not anime:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anime '{name}' not found"
        )
    
    # Validate URL
    url = request.provider_url.strip()
    if not any(domain in url.lower() for domain in ["animeworld.tv", "animeworld.so", "animeworld.ac"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL must be from AnimeWorld"
        )
    
    try:
        # Use Miko to get episode info from provider
        miko = Miko()
        await miko.loadAnime(url)
        
        if not miko.anime:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not load anime from provider URL"
            )
        
        # Get episodes
        episodes = await miko.getEpisodes()
        if not episodes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not fetch episodes from provider"
            )
        
        # Update anime with provider link and episodes available
        update_data = {
            "link": url,
            "episodi_disponibili": len(episodes)
        }
        
        db.update_anime(name, **update_data)
        logger.info(f"Associated provider for anime '{name}': {len(episodes)} episodes available")
        
        # Return updated anime
        updated = db.get_anime_by_name(name)
        downloaded = updated.get("episodi_scaricati", 0)
        available = len(episodes)
        total = updated.get("numero_episodi", 0)
        
        missing = [n for n in range(1, available + 1) if n > downloaded]
        
        return AnimeDetail(
            name=updated["name"],
            link=url,
            episodes_downloaded=downloaded,
            episodes_total=total,
            episodes_available=available,
            missing_episodes=missing,
            anilist_id=updated.get("anilist_id"),
            synopsis=updated.get("synopsis"),
            rating=updated.get("rating"),
            year=updated.get("year"),
            genres=updated.get("genres", "").split(",") if updated.get("genres") else [],
            status=updated.get("status"),
            poster_url=updated.get("poster_url"),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error associating provider for anime '{name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
