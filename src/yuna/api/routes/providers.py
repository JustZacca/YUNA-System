"""
Provider Search API Routes.
Search for content on various provider platforms.
"""

from typing import List, Optional
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from yuna.services.media_service import Miko, MikoSC
from yuna.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/providers", tags=["Providers"])

# Shared client instances
_miko: Optional[Miko] = None
_miko_sc: Optional[MikoSC] = None


def get_miko() -> Miko:
    """Get Miko (AnimeWorld) client singleton."""
    global _miko
    if _miko is None:
        _miko = Miko()
    return _miko


def get_miko_sc() -> MikoSC:
    """Get MikoSC (StreamingCommunity) client singleton."""
    global _miko_sc
    if _miko_sc is None:
        _miko_sc = MikoSC()
    return _miko_sc


# ==================== Schemas ====================

class ProviderSearchResult(BaseModel):
    """Provider search result."""
    title: str
    provider: str
    url: Optional[str] = None
    poster: Optional[str] = None
    slug: Optional[str] = None
    media_id: Optional[int] = None
    episodes: Optional[int] = None
    year: Optional[int] = None
    type: Optional[str] = None


# ==================== Routes ====================

@router.get("/search/anime", response_model=List[ProviderSearchResult])
async def search_anime_providers(
    q: str = Query(..., description="Search query"),
):
    """
    Search for anime across all available providers.
    Currently searches AnimeWorld.
    """
    if not q or not q.strip():
        raise HTTPException(
            status_code=400,
            detail="Search query is required"
        )
    
    results = []
    query = q.strip()
    
    try:
        # Search AnimeWorld using findAnime
        miko = get_miko()
        anime_results = miko.findAnime(query)
        
        if anime_results:
            for anime in anime_results:
                results.append(ProviderSearchResult(
                    title=anime.get("name", ""),
                    provider="AnimeWorld",
                    url=anime.get("link", ""),
                    poster=None,  # findAnime doesn't return poster
                    episodes=None,
                    year=None,
                    type="anime"
                ))
        
        logger.info(f"Found {len(results)} anime results on AnimeWorld for query '{query}'")
        
    except Exception as e:
        logger.error(f"Error searching anime providers: {e}")
        # Don't fail the whole request if one provider fails
    
    return results


@router.get("/search/media", response_model=List[ProviderSearchResult])
async def search_media_providers(
    q: str = Query(..., description="Search query"),
    type: str = Query(..., description="Media type: series or film"),
):
    """
    Search for series/films across all available providers.
    Currently searches StreamingCommunity.
    """
    if not q or not q.strip():
        raise HTTPException(
            status_code=400,
            detail="Search query is required"
        )
    
    if type not in ["series", "film"]:
        raise HTTPException(
            status_code=400,
            detail="Type must be 'series' or 'film'"
        )
    
    results = []
    query = q.strip()
    
    try:
        # Search StreamingCommunity
        miko_sc = get_miko_sc()
        
        # Map type to SC filter
        filter_type = "tv" if type == "series" else "movie"
        
        # Search on StreamingCommunity
        sc_results = miko_sc.search(query, filter_type=filter_type)
        
        if sc_results:
            for item in sc_results:
                results.append(ProviderSearchResult(
                    title=item.name,
                    provider="StreamingCommunity",
                    poster=item.image,
                    slug=item.slug,
                    media_id=item.id,
                    year=int(item.year) if item.year and item.year.isdigit() else None,
                    type=type
                ))
        
        logger.info(f"Found {len(results)} {type} results on StreamingCommunity for query '{query}'")
        
    except Exception as e:
        logger.error(f"Error searching media providers: {e}")
        # Don't fail the whole request if one provider fails
    
    return results
