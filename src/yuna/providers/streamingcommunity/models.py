"""
Data models for StreamingCommunity provider.
"""

from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class MediaItem:
    """Represents a media item (film or TV series)."""
    id: int
    name: str
    slug: str
    type: str  # 'movie' or 'tv'
    year: str = ""
    date: str = ""
    image: Optional[str] = None
    provider_language: str = "it"

    def __str__(self):
        return f"{self.name} ({self.year}) [{self.type}]"


@dataclass
class Episode:
    """Represents a TV episode."""
    id: int
    number: int
    name: str = ""
    plot: str = ""
    duration: int = 0

    def __str__(self):
        return f"E{self.number}: {self.name}"


@dataclass
class Season:
    """Represents a TV season."""
    id: int
    number: int
    name: str = ""
    slug: str = ""
    episodes: List[Episode] = field(default_factory=list)

    def __str__(self):
        return f"Season {self.number} ({len(self.episodes)} episodes)"


@dataclass
class SeriesInfo:
    """Complete series information."""
    id: int
    name: str
    slug: str
    year: str = ""
    plot: str = ""
    seasons: List[Season] = field(default_factory=list)

    def get_season(self, number: int) -> Optional[Season]:
        """Get a season by number."""
        for s in self.seasons:
            if s.number == number:
                return s
        return None
