"""
Series/TV API Routes.
CRUD operations for TV series library.
"""

from typing import List, Optional
import json

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from yuna.api.deps import DbDep, CurrentUser
from yuna.providers.tmdb import TMDBClient
from yuna.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/series", tags=["Series"])

# Shared TMDB client instance
_tmdb_client: Optional[TMDBClient] = None


def get_tmdb() -> TMDBClient:
    """Get TMDB client singleton."""
    global _tmdb_client
    if _tmdb_client is None:
        _tmdb_client = TMDBClient()
    return _tmdb_client


# ==================== Schemas ====================

class SeriesBase(BaseModel):
    """Base series schema."""
    name: str
    link: str
    episodes_downloaded: int = 0
    episodes_total: int = 0
    last_update: Optional[str] = None
    provider: Optional[str] = None
    year: Optional[int] = None
    # TMDB metadata for list view
    tmdb_id: Optional[int] = None
    overview: Optional[str] = None
    poster_url: Optional[str] = None
    rating: Optional[float] = None
    genres: List[str] = []
    status: Optional[str] = None


class SeriesListResponse(BaseModel):
    """Response for series list."""
    items: List[SeriesBase]
    total: int


class SeriesDetail(SeriesBase):
    """Detailed series info."""
    slug: Optional[str] = None
    media_id: Optional[int] = None
    provider_language: Optional[str] = None
    seasons_data: Optional[str] = None
    # TMDB metadata
    tmdb_id: Optional[int] = None
    overview: Optional[str] = None
    poster_path: Optional[str] = None
    backdrop_path: Optional[str] = None
    vote_average: Optional[float] = None
    genre_ids: Optional[List[int]] = None


class UpdateMetadataRequest(BaseModel):
    """Request to update series metadata from TMDB."""
    tmdb_id: int


# ==================== Routes ====================

def _get_poster_url(poster_path: Optional[str]) -> Optional[str]:
    """Convert TMDB poster path to full URL."""
    if poster_path:
        return f"https://image.tmdb.org/t/p/w500{poster_path}"
    return None


@router.get("", response_model=SeriesListResponse)
async def list_series(db: DbDep):
    """
    Get all TV series in library.

    Returns list of series with basic info and TMDB metadata.
    """
    series_list = db.get_all_tv()

    items = []
    for s in series_list:
        # Parse genres if present
        genres = []
        if s.get("genres"):
            try:
                genres = s["genres"].split(",") if isinstance(s["genres"], str) else s["genres"]
            except Exception:
                pass

        base = SeriesBase(
            name=s["name"],
            link=s.get("link", ""),
            episodes_downloaded=s.get("episodi_scaricati", 0),
            episodes_total=s.get("numero_episodi", 0),
            last_update=s.get("last_update"),
            provider=s.get("provider"),
            year=s.get("year"),
            # TMDB metadata
            tmdb_id=s.get("tmdb_id"),
            overview=s.get("overview"),
            poster_url=_get_poster_url(s.get("poster_path")),
            rating=s.get("vote_average"),
            genres=genres,
            status=s.get("status"),
        )
        items.append(base)

    return SeriesListResponse(items=items, total=len(items))


@router.get("/{name}", response_model=SeriesDetail)
async def get_series(name: str, db: DbDep):
    """
    Get detailed info for a specific TV series.
    """
    series = db.get_tv_by_name(name)

    if not series:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Series '{name}' not found"
        )

    # Parse genre_ids if present
    genre_ids = None
    if series.get("genre_ids"):
        try:
            genre_ids = json.loads(series["genre_ids"])
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Failed to parse genre_ids for series {name}")

    return SeriesDetail(
        name=series["name"],
        link=series.get("link", ""),
        episodes_downloaded=series.get("episodi_scaricati", 0),
        episodes_total=series.get("numero_episodi", 0),
        last_update=series.get("last_update"),
        provider=series.get("provider"),
        slug=series.get("slug"),
        media_id=series.get("media_id"),
        provider_language=series.get("provider_language"),
        year=series.get("year"),
        seasons_data=series.get("seasons_data"),
        # TMDB metadata
        tmdb_id=series.get("tmdb_id"),
        overview=series.get("overview"),
        poster_path=series.get("poster_path"),
        backdrop_path=series.get("backdrop_path"),
        vote_average=series.get("vote_average"),
        genre_ids=genre_ids,
    )

@router.patch("/{name}/metadata", response_model=SeriesDetail)
async def update_series_metadata(
    name: str,
    request: UpdateMetadataRequest,
    db: DbDep
):
    """
    Update series metadata from TMDB.

    Fetches full metadata from TMDB and updates the database.
    """
    # Verify series exists
    series = db.get_tv_by_name(name)
    if not series:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Series '{name}' not found"
        )

    # Fetch metadata from TMDB
    tmdb = get_tmdb()
    tmdb_data = await tmdb.get_tv(request.tmdb_id)

    if not tmdb_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"TMDB series with ID {request.tmdb_id} not found"
        )

    # Update database with TMDB metadata
    with db._get_connection() as conn:
        conn.execute(
            """
            UPDATE tv SET
                tmdb_id = ?,
                overview = ?,
                poster_path = ?,
                backdrop_path = ?,
                vote_average = ?,
                genre_ids = ?
            WHERE name = ?
            """,
            (
                tmdb_data.id,
                tmdb_data.overview,
                tmdb_data.poster_path,
                tmdb_data.backdrop_path,
                tmdb_data.vote_average,
                json.dumps(tmdb_data.genre_ids) if tmdb_data.genre_ids else None,
                name,
            )
        )
        conn.commit()
        logger.info(f"Updated TMDB metadata for series '{name}' (TMDB ID: {tmdb_data.id})")

    # Return updated series
    return await get_series(name, db)


@router.delete("/{name}")
async def delete_series(
    name: str,
    db: DbDep,
    current_user: CurrentUser
):
    """
    Delete series completely.
    
    Removes:
    - Database entry
    - All downloaded files and folders
    """
    import shutil
    import os
    
    # Verify series exists
    series = db.get_tv_by_name(name)
    if not series:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Series '{name}' not found"
        )
    
    # Get series folder path
    series_folder = os.getenv("SERIES_FOLDER", "/downloads/series")
    series_path = os.path.join(series_folder, name)
    
    # Delete files if folder exists
    deleted_files = False
    if os.path.exists(series_path):
        try:
            shutil.rmtree(series_path)
            deleted_files = True
            logger.info(f"Deleted files for series '{name}' at {series_path}")
        except Exception as e:
            logger.error(f"Error deleting files for series '{name}': {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error deleting files: {str(e)}"
            )
    
    # Delete from database
    try:
        success = db.delete_tv(name)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete series from database"
            )
        logger.info(f"Deleted series '{name}' from database")
    except Exception as e:
        logger.error(f"Error deleting series '{name}' from database: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting from database: {str(e)}"
        )
    
    return {
        "success": True,
        "message": f"Series '{name}' deleted successfully",
        "files_deleted": deleted_files
    }