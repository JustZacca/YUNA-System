"""
Configuration loader for YUNA-System.
Handles environment variables and settings.
"""

import os
from typing import Optional


class YunaConfig:
    """YUNA-System configuration from environment variables."""
    
    def __init__(self):
        # Load N_m3u8DL-RE settings
        self.prefer_nm3u8 = self._get_bool("PREFER_NM3U8", True)
        self.nm3u8_thread_count = self._get_int("NM3U8_THREAD_COUNT", 16)
        self.nm3u8_timeout = self._get_int("NM3U8_TIMEOUT", 100)
        self.nm3u8_max_speed = os.getenv("NM3U8_MAX_SPEED")
        self.nm3u8_binary_path = os.getenv("NM3U8_BINARY_PATH")
        self.nm3u8_temp_dir = os.getenv("NM3U8_TEMP_DIR")
        
        # Load AniList settings
        self.anilist_access_token = os.getenv("ANILIST_ACCESS_TOKEN", "e2jKyArZWW10PCqEbRzabasjtiJAKY6yxpYBe3oY")
        
    def _get_bool(self, key: str, default: bool = False) -> bool:
        """Get boolean from environment variable."""
        value = os.getenv(key, "").lower()
        return value in ("true", "1", "yes", "on") if value else default
        
    def _get_int(self, key: str, default: int) -> int:
        """Get integer from environment variable."""
        try:
            return int(os.getenv(key, str(default)))
        except ValueError:
            return default
            
    @property
    def nm3u8_config_dict(self) -> dict:
        """Get N_m3u8DL-RE configuration as dictionary."""
        return {
            "prefer_nm3u8": self.prefer_nm3u8,
            "thread_count": self.nm3u8_thread_count,
            "timeout": self.nm3u8_timeout,
            "max_speed": self.nm3u8_max_speed,
            "binary_path": self.nm3u8_binary_path,
            "temp_dir": self.nm3u8_temp_dir,
        }


# Global configuration instance
config = YunaConfig()