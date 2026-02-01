"""
Series/TV API Routes.
CRUD operations for TV series library.
"""

from datetime import datetime
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


class AddFromTmdbRequest(BaseModel):
    """Request to add series from TMDB without provider."""
    tmdb_id: int


class AssociateProviderRequest(BaseModel):
    """Request to associate provider to existing series."""
    provider: str
    media_id: int
    slug: Optional[str] = None


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

@router.post("/from-tmdb", response_model=SeriesDetail)
async def add_series_from_tmdb(
    request: AddFromTmdbRequest,
    db: DbDep,
    user: CurrentUser
):
    """
    Add series from TMDB without provider.
    Creates entry with metadata only, provider can be associated later.
    """
    try:
        # Fetch metadata from TMDB
        tmdb = get_tmdb()
        tmdb_data = await tmdb.get_tv(request.tmdb_id)
        
        if not tmdb_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Series with TMDB ID {request.tmdb_id} not found"
            )
        
        series_name = tmdb_data.name
        year = tmdb_data.first_air_date.split("-")[0] if tmdb_data.first_air_date else None
        
        # Check if series already exists
        existing = db.get_tv_by_name(series_name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Series '{series_name}' already exists in library"
            )
        
        # Use number_of_episodes from TMDB data
        total_episodes = tmdb_data.number_of_episodes
        
        # Create series entry without provider - use db.add_tv() with required params
        db.add_tv(
            name=series_name,
            link="",  # No provider yet
            last_update=datetime.now(),
            numero_episodi=total_episodes,
            slug=None,
            media_id=None,
            provider_language="it",
            year=int(year) if year else None,
            provider=None
        )
        
        # Update with TMDB metadata fields
        db.update_anime(  # Uses the same generic update method
            name=series_name,
            tmdb_id=request.tmdb_id,
            overview=tmdb_data.overview[:500] if tmdb_data.overview else None,
            poster_path=tmdb_data.poster_path,
            backdrop_path=tmdb_data.backdrop_path,
            vote_average=tmdb_data.vote_average,
            genre_ids=json.dumps(tmdb_data.genre_ids) if tmdb_data.genre_ids else None,
            status=tmdb_data.status
        )
        
        logger.info(f"Added series '{series_name}' from TMDB (ID: {request.tmdb_id}) without provider")
        
        return SeriesDetail(
            name=series_name,
            link="",
            episodes_downloaded=0,
            episodes_total=total_episodes,
            provider=None,
            year=int(year) if year else None,
            tmdb_id=request.tmdb_id,
            overview=tmdb_data.overview,
            poster_path=tmdb_data.poster_path,
            backdrop_path=tmdb_data.backdrop_path,
            vote_average=tmdb_data.vote_average,
            genre_ids=tmdb_data.genre_ids,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding series from TMDB: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/{name}/associate-provider", response_model=SeriesDetail)
async def associate_series_provider(
    name: str,
    request: AssociateProviderRequest,
    db: DbDep,
    user: CurrentUser
):
    """
    Associate provider (StreamingCommunity) to existing series.
    Updates series with provider info.
    """
    # Verify series exists
    series = db.get_tv_by_name(name)
    if not series:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Series '{name}' not found"
        )
    
    try:
        # Build link based on provider
        if request.provider.lower() == "streamingcommunity":
            link = f"https://streamingcommunity.dev/watch/{request.media_id}"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported provider: {request.provider}"
            )
        
        # Update series with provider info
        update_data = {
            "link": link,
            "provider": request.provider,
            "media_id": request.media_id,
        }
        
        if request.slug:
            update_data["slug"] = request.slug
        
        db.update_tv(name, **update_data)
        logger.info(f"Associated provider '{request.provider}' for series '{name}' (media_id: {request.media_id})")
        
        # Return updated series
        return await get_series(name, db)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error associating provider for series '{name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
