"""
Films API Routes.
CRUD operations for films library.
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

router = APIRouter(prefix="/films", tags=["Films"])

# Shared TMDB client instance
_tmdb_client: Optional[TMDBClient] = None


def get_tmdb() -> TMDBClient:
    """Get TMDB client singleton."""
    global _tmdb_client
    if _tmdb_client is None:
        _tmdb_client = TMDBClient()
    return _tmdb_client


# ==================== Schemas ====================

class FilmBase(BaseModel):
    """Base film schema."""
    name: str
    link: str
    downloaded: bool = False
    last_update: Optional[str] = None
    provider: Optional[str] = None
    year: Optional[int] = None
    # TMDB metadata for list view
    tmdb_id: Optional[int] = None
    overview: Optional[str] = None
    poster_url: Optional[str] = None
    rating: Optional[float] = None
    genres: List[str] = []
    runtime: Optional[int] = None


class FilmListResponse(BaseModel):
    """Response for film list."""
    items: List[FilmBase]
    total: int


class FilmDetail(FilmBase):
    """Detailed film info."""
    slug: Optional[str] = None
    media_id: Optional[int] = None
    provider_language: Optional[str] = None
    # TMDB metadata
    tmdb_id: Optional[int] = None
    overview: Optional[str] = None
    poster_path: Optional[str] = None
    backdrop_path: Optional[str] = None
    vote_average: Optional[float] = None
    genre_ids: Optional[List[int]] = None


class UpdateMetadataRequest(BaseModel):
    """Request to update film metadata from TMDB."""
    tmdb_id: int


class AddFromTmdbRequest(BaseModel):
    """Request to add film from TMDB without provider."""
    tmdb_id: int


class AssociateProviderRequest(BaseModel):
    """Request to associate provider to existing film."""
    provider: str
    media_id: int
    slug: Optional[str] = None


# ==================== Routes ====================

def _get_poster_url(poster_path: Optional[str]) -> Optional[str]:
    """Convert TMDB poster path to full URL."""
    if poster_path:
        return f"https://image.tmdb.org/t/p/w500{poster_path}"
    return None


@router.get("", response_model=FilmListResponse)
async def list_films(db: DbDep):
    """
    Get all films in library.

    Returns list of films with basic info and TMDB metadata.
    """
    films_list = db.get_all_movies()

    items = []
    for f in films_list:
        # Parse genres if present
        genres = []
        if f.get("genres"):
            try:
                genres = f["genres"].split(",") if isinstance(f["genres"], str) else f["genres"]
            except Exception:
                pass

        base = FilmBase(
            name=f["name"],
            link=f.get("link", ""),
            downloaded=bool(f.get("scaricato", 0)),
            last_update=f.get("last_update"),
            provider=f.get("provider"),
            year=f.get("year"),
            # TMDB metadata
            tmdb_id=f.get("tmdb_id"),
            overview=f.get("overview"),
            poster_url=_get_poster_url(f.get("poster_path")),
            rating=f.get("vote_average"),
            genres=genres,
            runtime=f.get("runtime"),
        )
        items.append(base)

    return FilmListResponse(items=items, total=len(items))


@router.get("/{name}", response_model=FilmDetail)
async def get_film(name: str, db: DbDep):
    """
    Get detailed info for a specific film.
    """
    film = db.get_movie_by_name(name)

    if not film:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Film '{name}' not found"
        )

    # Parse genre_ids if present
    genre_ids = None
    if film.get("genre_ids"):
        try:
            genre_ids = json.loads(film["genre_ids"])
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Failed to parse genre_ids for film {name}")

    return FilmDetail(
        name=film["name"],
        link=film.get("link", ""),
        downloaded=bool(film.get("scaricato", 0)),
        last_update=film.get("last_update"),
        provider=film.get("provider"),
        slug=film.get("slug"),
        media_id=film.get("media_id"),
        provider_language=film.get("provider_language"),
        year=film.get("year"),
        # TMDB metadata
        tmdb_id=film.get("tmdb_id"),
        overview=film.get("overview"),
        poster_path=film.get("poster_path"),
        backdrop_path=film.get("backdrop_path"),
        vote_average=film.get("vote_average"),
        genre_ids=genre_ids,
    )


@router.patch("/{name}/metadata", response_model=FilmDetail)
async def update_film_metadata(
    name: str,
    request: UpdateMetadataRequest,
    db: DbDep
):
    """
    Update film metadata from TMDB.

    Fetches full metadata from TMDB and updates the database.
    """
    # Verify film exists
    film = db.get_movie_by_name(name)
    if not film:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Film '{name}' not found"
        )

    # Fetch metadata from TMDB
    tmdb = get_tmdb()
    tmdb_data = await tmdb.get_movie(request.tmdb_id)

    if not tmdb_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"TMDB film with ID {request.tmdb_id} not found"
        )

    # Update database with TMDB metadata
    with db._get_connection() as conn:
        conn.execute(
            """
            UPDATE movies SET
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
        logger.info(f"Updated TMDB metadata for film '{name}' (TMDB ID: {tmdb_data.id})")

    # Return updated film
    return await get_film(name, db)


@router.delete("/{name}")
async def delete_film(
    name: str,
    db: DbDep,
    current_user: CurrentUser
):
    """
    Delete film completely.
    
    Removes:
    - Database entry
    - All downloaded files and folders
    """
    import shutil
    import os
    
    # Verify film exists
    film = db.get_movie_by_name(name)
    if not film:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Film '{name}' not found"
        )
    
    # Get movies folder path
    movies_folder = os.getenv("MOVIES_FOLDER", "/downloads/movies")
    film_path = os.path.join(movies_folder, name)
    
    # Delete files if folder exists
    deleted_files = False
    if os.path.exists(film_path):
        try:
            shutil.rmtree(film_path)
            deleted_files = True
            logger.info(f"Deleted files for film '{name}' at {film_path}")
        except Exception as e:
            logger.error(f"Error deleting files for film '{name}': {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error deleting files: {str(e)}"
            )
    
    # Delete from database
    try:
        success = db.delete_movie(name)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete film from database"
            )
        logger.info(f"Deleted film '{name}' from database")
    except Exception as e:
        logger.error(f"Error deleting film '{name}' from database: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting from database: {str(e)}"
        )
    
    return {
        "success": True,
        "message": f"Film '{name}' deleted successfully",
        "files_deleted": deleted_files
    }


@router.post("/from-tmdb", response_model=FilmDetail)
async def add_film_from_tmdb(
    request: AddFromTmdbRequest,
    db: DbDep,
    user: CurrentUser
):
    """
    Add film from TMDB without provider.
    Creates entry with metadata only, provider can be associated later.
    """
    try:
        # Fetch metadata from TMDB
        tmdb = get_tmdb()
        tmdb_data = await tmdb.get_movie(request.tmdb_id)
        
        if not tmdb_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Film with TMDB ID {request.tmdb_id} not found"
            )
        
        film_name = tmdb_data.title
        year = tmdb_data.release_date.split("-")[0] if tmdb_data.release_date else None
        
        # Check if film already exists
        existing = db.get_movie_by_name(film_name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Film '{film_name}' already exists in library"
            )
        
        # Create film entry without provider - use db.add_movie() with required params
        db.add_movie(
            name=film_name,
            link="",  # No provider yet
            last_update=datetime.now(),
            slug=None,
            media_id=None,
            provider_language="it",
            year=int(year) if year else None,
            provider=None
        )
        
        # Update with TMDB metadata fields
        db.update_anime(  # Uses the same generic update method
            name=film_name,
            tmdb_id=request.tmdb_id,
            overview=tmdb_data.overview[:500] if tmdb_data.overview else None,
            poster_path=tmdb_data.poster_path,
            backdrop_path=tmdb_data.backdrop_path,
            vote_average=tmdb_data.vote_average,
            genre_ids=json.dumps(tmdb_data.genre_ids) if tmdb_data.genre_ids else None,
            runtime=tmdb_data.runtime
        )
        
        logger.info(f"Added film '{film_name}' from TMDB (ID: {request.tmdb_id}) without provider")
        
        return FilmDetail(
            name=film_name,
            link="",
            downloaded=False,
            provider=None,
            year=int(year) if year else None,
            tmdb_id=request.tmdb_id,
            overview=tmdb_data.overview,
            poster_path=tmdb_data.poster_path,
            backdrop_path=tmdb_data.backdrop_path,
            vote_average=tmdb_data.vote_average,
            genre_ids=tmdb_data.genre_ids,
            runtime=tmdb_data.runtime,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding film from TMDB: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/{name}/associate-provider", response_model=FilmDetail)
async def associate_film_provider(
    name: str,
    request: AssociateProviderRequest,
    db: DbDep,
    user: CurrentUser
):
    """
    Associate provider (StreamingCommunity) to existing film.
    Updates film with provider info.
    """
    # Verify film exists
    film = db.get_movie_by_name(name)
    if not film:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Film '{name}' not found"
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
        
        # Update film with provider info
        update_data = {
            "link": link,
            "provider": request.provider,
            "media_id": request.media_id,
        }
        
        if request.slug:
            update_data["slug"] = request.slug
        
        db.update_movie(name, **update_data)
        logger.info(f"Associated provider '{request.provider}' for film '{name}' (media_id: {request.media_id})")
        
        # Return updated film
        return await get_film(name, db)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error associating provider for film '{name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
