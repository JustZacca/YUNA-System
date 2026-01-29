"""
StreamingCommunity client module for YUNA-System.
Handles search, info retrieval, and video download from StreamingCommunity.
"""

import os
import re
import json
import time
import logging
import subprocess
import asyncio
from typing import Optional, List, Dict, Any, Tuple
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from dataclasses import dataclass, field

import httpx
from bs4 import BeautifulSoup

try:
    from fake_useragent import UserAgent
    ua = UserAgent()
    def get_user_agent():
        return ua.random
except ImportError:
    def get_user_agent():
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

from color_utils import ColoredFormatter

# Configure logging
formatter = ColoredFormatter(
    fmt="\033[34m%(asctime)s\033[0m - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(handler)


# ==================== DATA CLASSES ====================

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
        for s in self.seasons:
            if s.number == number:
                return s
        return None


# ==================== STREAMING COMMUNITY CLIENT ====================

class StreamingCommunityClient:
    """Client for interacting with StreamingCommunity."""

    # URL for fetching current domain
    DOMAINS_API_URL = "https://raw.githubusercontent.com/Arrowar/SC_Domains/main/domains.json"

    # Fallback domains (rarely used, only if API fails)
    FALLBACK_DOMAINS = [
        "https://streamingcommunityz.land",
    ]

    def __init__(self, base_url: str = None):
        self.base_url = base_url
        self._version = None
        self._client = None

    def _get_headers(self) -> Dict[str, str]:
        """Get default headers for requests."""
        return {
            "User-Agent": get_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
        }

    def _get_inertia_headers(self) -> Dict[str, str]:
        """Get headers for Inertia.js requests."""
        headers = self._get_headers()
        headers.update({
            "X-Inertia": "true",
            "X-Inertia-Version": self._version or "",
        })
        return headers

    def _create_client(self) -> httpx.Client:
        """Create HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                headers=self._get_headers(),
                follow_redirects=True,
                timeout=30.0
            )
        return self._client

    def _fetch_domain_from_api(self) -> Optional[str]:
        """Fetch current StreamingCommunity domain from Arrowar's API."""
        try:
            client = httpx.Client(timeout=10)
            response = client.get(self.DOMAINS_API_URL)
            response.raise_for_status()

            data = response.json()
            # Look for streamingcommunity entry
            if "streamingcommunity" in data:
                sc_data = data["streamingcommunity"]
                domain = sc_data.get("full_url", "").rstrip("/")
                if domain:
                    logger.info(f"StreamingCommunity URL from API: {domain}")
                    client.close()
                    return domain
            client.close()
        except Exception as e:
            logger.warning(f"Failed to fetch domain from API: {e}")
        return None

    def _detect_base_url(self) -> str:
        """Auto-detect working base URL."""
        if self.base_url:
            return self.base_url

        # Try to get domain from API first
        api_domain = self._fetch_domain_from_api()
        if api_domain:
            self.base_url = api_domain
            return self.base_url

        # Fallback to hardcoded domains
        for domain in self.FALLBACK_DOMAINS:
            try:
                client = httpx.Client(follow_redirects=False, timeout=10)
                response = client.get(domain)
                # Accept 200 or redirects that stay on same domain
                if response.status_code in (200, 301, 302):
                    self.base_url = domain
                    logger.info(f"StreamingCommunity URL (fallback): {self.base_url}")
                    client.close()
                    return self.base_url
                client.close()
            except Exception as e:
                logger.debug(f"Failed to reach {domain}: {e}")
                continue

        # Last resort fallback
        self.base_url = self.FALLBACK_DOMAINS[0]
        logger.warning(f"Using last resort URL: {self.base_url}")
        return self.base_url

    def _get_version(self, lang: str = "it") -> str:
        """Get Inertia version from page."""
        if self._version:
            return self._version

        try:
            base_url = self._detect_base_url()
            client = self._create_client()
            response = client.get(f"{base_url}/{lang}")
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            app_div = soup.find("div", {"id": "app"})
            if app_div and app_div.get("data-page"):
                data = json.loads(app_div.get("data-page"))
                self._version = data.get("version", "")
                logger.debug(f"Inertia version: {self._version}")
                return self._version
        except Exception as e:
            logger.error(f"Failed to get version: {e}")

        return ""

    def search(self, query: str, languages: List[str] = None) -> List[MediaItem]:
        """
        Search for titles on StreamingCommunity.

        Args:
            query: Search query string
            languages: List of language codes to search (default: ["it", "en"])

        Returns:
            List of MediaItem objects
        """
        if languages is None:
            languages = ["it", "en"]

        results = []
        seen_ids = set()
        base_url = self._detect_base_url()

        for lang in languages:
            try:
                # Get version for this language
                version = self._get_version(lang)

                # Make search request
                headers = self._get_headers()
                headers.update({
                    "X-Inertia": "true",
                    "X-Inertia-Version": version,
                })

                client = self._create_client()
                client.headers.update(headers)

                search_url = f"{base_url}/{lang}/search"
                logger.info(f"Searching: {search_url}?q={query}")

                response = client.get(search_url, params={"q": query})
                response.raise_for_status()

                # Check if response is JSON (Inertia response)
                content_type = response.headers.get("content-type", "")
                if "application/json" not in content_type:
                    # Got HTML response, try to parse Inertia data from page
                    soup = BeautifulSoup(response.text, "html.parser")
                    app_div = soup.find("div", {"id": "app"})
                    if app_div and app_div.get("data-page"):
                        data = json.loads(app_div.get("data-page"))
                    else:
                        logger.warning(f"Non-JSON response for {lang}, skipping")
                        continue
                else:
                    data = response.json()

                titles = data.get("props", {}).get("titles", [])

                for title in titles:
                    title_id = title.get("id")
                    if title_id in seen_ids:
                        continue
                    seen_ids.add(title_id)

                    # Extract image URL
                    image_url = None
                    images = title.get("images", [])
                    for ptype in ["poster", "cover", "cover_mobile", "background"]:
                        for img in images:
                            if img.get("type") == ptype and img.get("filename"):
                                cdn_url = base_url.replace("stream", "cdn.stream")
                                image_url = f"{cdn_url}/images/{img.get('filename')}"
                                break
                        if image_url:
                            break

                    # Extract date
                    date = None
                    for trans in title.get("translations", []):
                        if trans.get("key") in ["first_air_date", "release_date"] and trans.get("value"):
                            date = trans.get("value")
                            break
                    if not date:
                        date = title.get("last_air_date") or title.get("release_date") or ""

                    year = date.split("-")[0] if date and "-" in date else ""

                    results.append(MediaItem(
                        id=title_id,
                        name=title.get("name", ""),
                        slug=title.get("slug", ""),
                        type=title.get("type", "movie"),
                        year=year,
                        date=date,
                        image=image_url,
                        provider_language=lang
                    ))

                logger.info(f"Found {len(titles)} titles in {lang}")

            except Exception as e:
                logger.error(f"Search error ({lang}): {e}")
                continue

        logger.info(f"Total unique results: {len(results)}")
        return results

    def get_series_info(self, media_id: int, slug: str, lang: str = "it") -> Optional[SeriesInfo]:
        """
        Get complete series information including seasons.

        Args:
            media_id: Series ID
            slug: Series slug
            lang: Language code

        Returns:
            SeriesInfo object or None
        """
        base_url = self._detect_base_url()

        try:
            # Use fresh client without Inertia headers for HTML page
            client = httpx.Client(
                headers=self._get_headers(),
                follow_redirects=True,
                timeout=30.0
            )

            # Get series info
            url = f"{base_url}/{lang}/titles/{media_id}-{slug}"
            logger.info(f"Getting series info: {url}")

            response = client.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            app_div = soup.find("div", {"id": "app"})
            if not app_div:
                logger.error("Could not find app data")
                return None

            data = json.loads(app_div.get("data-page"))
            # Update version
            self._version = data.get("version", self._version)

            title_data = data.get("props", {}).get("title", {})

            series = SeriesInfo(
                id=media_id,
                name=title_data.get("name", ""),
                slug=slug,
                year=str(title_data.get("release_date", ""))[:4],
                plot=title_data.get("plot", "")
            )

            # Parse seasons
            seasons_data = title_data.get("seasons", [])
            for s in seasons_data:
                season = Season(
                    id=s.get("id", 0),
                    number=s.get("number", 0),
                    name=f"Season {s.get('number', 0)}",
                    slug=s.get("slug", "")
                )
                series.seasons.append(season)

            logger.info(f"Series '{series.name}' has {len(series.seasons)} seasons")
            return series

        except Exception as e:
            logger.error(f"Failed to get series info: {e}")
            return None

    def get_season_episodes(self, series: SeriesInfo, season_number: int, lang: str = "it") -> List[Episode]:
        """
        Get episodes for a specific season.

        Args:
            series: SeriesInfo object
            season_number: Season number to fetch
            lang: Language code

        Returns:
            List of Episode objects
        """
        base_url = self._detect_base_url()

        season = series.get_season(season_number)
        if not season:
            logger.error(f"Season {season_number} not found")
            return []

        try:
            headers = self._get_inertia_headers()
            client = self._create_client()
            client.headers.update(headers)

            url = f"{base_url}/{lang}/titles/{series.id}-{series.slug}/season-{season_number}"
            logger.info(f"Getting episodes: {url}")

            response = client.get(url)
            response.raise_for_status()

            data = response.json()
            episodes_data = data.get("props", {}).get("loadedSeason", {}).get("episodes", [])

            episodes = []
            for ep in episodes_data:
                episode = Episode(
                    id=ep.get("id", 0),
                    number=ep.get("number", 0),
                    name=ep.get("name", ""),
                    plot=ep.get("plot", ""),
                    duration=ep.get("duration", 0)
                )
                episodes.append(episode)
                season.episodes.append(episode)

            logger.info(f"Season {season_number} has {len(episodes)} episodes")
            return episodes

        except Exception as e:
            logger.error(f"Failed to get episodes: {e}")
            return []


# ==================== VIDEO SOURCE (VIXCLOUD) ====================

class VideoSource:
    """Handles video source extraction from vixcloud player."""

    def __init__(self, base_url: str, media_id: int, is_series: bool = False, lang: str = "it"):
        self.base_url = base_url
        self.media_id = media_id
        self.is_series = is_series
        self.lang = lang
        self.iframe_src = None
        self.master_playlist = None
        self._token = None
        self._expires = None
        self._can_play_fhd = False

    def _get_headers(self) -> Dict[str, str]:
        return {"User-Agent": get_user_agent()}

    def get_iframe(self, episode_id: int = None) -> Optional[str]:
        """
        Get iframe source URL.

        Args:
            episode_id: Episode ID (required for series)

        Returns:
            Iframe URL or None
        """
        try:
            client = httpx.Client(headers=self._get_headers(), follow_redirects=True, timeout=30)

            url = f"{self.base_url}/{self.lang}/iframe/{self.media_id}"
            params = {}
            if self.is_series and episode_id:
                params = {"episode_id": episode_id, "next_episode": "1"}

            logger.info(f"Getting iframe: {url}")
            response = client.get(url, params=params)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            iframe = soup.find("iframe")
            if iframe and iframe.get("src"):
                self.iframe_src = iframe.get("src")
                logger.debug(f"Iframe src: {self.iframe_src}")
                return self.iframe_src

            logger.error("Iframe not found in response")
            return None

        except Exception as e:
            logger.error(f"Failed to get iframe: {e}")
            return None

    def _parse_window_vars(self, script_text: str) -> Dict[str, Any]:
        """Parse window.* variables from JavaScript."""
        result = {}

        # Parse window.video
        video_match = re.search(r'window\.video\s*=\s*(\{[^}]+\})', script_text, re.DOTALL)
        if video_match:
            try:
                video_str = video_match.group(1)
                video_str = re.sub(r"'", '"', video_str)
                video_str = re.sub(r'(\w+):', r'"\1":', video_str)
                result['video'] = json.loads(video_str)
            except:
                pass

        # Parse window.streams (new format)
        streams_match = re.search(r'window\.streams\s*=\s*(\[.+?\]);', script_text, re.DOTALL)
        if streams_match:
            try:
                streams_str = streams_match.group(1).replace("\\/", "/")
                streams = json.loads(streams_str)
                # Get first active stream or first stream
                for stream in streams:
                    if stream.get("active", False):
                        result['playlist_url'] = stream.get("url")
                        break
                if 'playlist_url' not in result and streams:
                    result['playlist_url'] = streams[0].get("url")
                logger.debug(f"Found streams: {len(streams)}")
            except Exception as e:
                logger.debug(f"Failed to parse streams: {e}")

        # Parse window.masterPlaylist.params (new format)
        params_match = re.search(r"window\.masterPlaylist\s*=\s*\{[^}]*params:\s*\{([^}]+)\}", script_text, re.DOTALL)
        if params_match:
            try:
                params_str = params_match.group(1)
                token_match = re.search(r"['\"]token['\"]\s*:\s*['\"]([^'\"]+)['\"]", params_str)
                expires_match = re.search(r"['\"]expires['\"]\s*:\s*['\"]?(\d+)['\"]?", params_str)
                if token_match:
                    self._token = token_match.group(1)
                if expires_match:
                    self._expires = expires_match.group(1)
            except:
                pass

        # Legacy format: Parse window.masterPlaylist with url directly
        if 'playlist_url' not in result:
            playlist_match = re.search(r'window\.masterPlaylist\s*=\s*(\{.+?\});', script_text, re.DOTALL)
            if playlist_match:
                try:
                    playlist_str = playlist_match.group(1)
                    url_match = re.search(r'url:\s*["\']([^"\']+)["\']', playlist_str)
                    token_match = re.search(r'token:\s*["\']([^"\']+)["\']', playlist_str)
                    expires_match = re.search(r'expires:\s*["\']?(\d+)["\']?', playlist_str)

                    if url_match:
                        result['playlist_url'] = url_match.group(1).replace('\\/', '/')
                    if token_match:
                        self._token = token_match.group(1)
                    if expires_match:
                        self._expires = expires_match.group(1)
                except:
                    pass

        # Parse window.canPlayFHD
        fhd_match = re.search(r'window\.canPlayFHD\s*=\s*(true|false)', script_text)
        if fhd_match:
            self._can_play_fhd = fhd_match.group(1) == 'true'

        return result

    def get_content(self) -> bool:
        """
        Fetch and parse video content from iframe.

        Returns:
            True if successful, False otherwise
        """
        if not self.iframe_src:
            logger.error("No iframe source set")
            return False

        try:
            headers = self._get_headers()
            headers["Referer"] = self.base_url + "/"
            client = httpx.Client(headers=headers, follow_redirects=True, timeout=30)

            response = client.get(self.iframe_src)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            body = soup.find("body")
            if body:
                # Collect all script content
                all_scripts = []
                for script_tag in body.find_all("script"):
                    if script_tag.string:
                        all_scripts.append(script_tag.string)

                # Parse combined script content
                combined_scripts = "\n".join(all_scripts)
                vars_data = self._parse_window_vars(combined_scripts)

                if 'playlist_url' in vars_data:
                    self.master_playlist = vars_data['playlist_url']
                    logger.info(f"Found playlist URL: {self.master_playlist}")
                    return True

            logger.error("Could not parse video content")
            return False

        except Exception as e:
            logger.error(f"Failed to get content: {e}")
            return False

    def get_playlist(self) -> Optional[str]:
        """
        Get final playlist URL with authentication params.

        Returns:
            Complete playlist URL or None
        """
        if not self.master_playlist:
            return None

        # Build query params
        params = {}
        if self._can_play_fhd:
            params['h'] = '1'
        if self._token:
            params['token'] = self._token
        if self._expires:
            params['expires'] = self._expires

        # Parse and rebuild URL
        parsed = urlparse(self.master_playlist)
        existing_params = parse_qs(parsed.query)

        # Merge params
        for k, v in existing_params.items():
            if k not in params:
                params[k] = v[0] if len(v) == 1 else v

        query_string = urlencode(params)
        final_url = urlunparse(parsed._replace(query=query_string))

        logger.info(f"Playlist URL ready (FHD: {self._can_play_fhd})")
        return final_url


# ==================== HLS DOWNLOADER ====================

class HLSDownloader:
    """Downloads HLS streams using ffmpeg."""

    def __init__(self, output_folder: str):
        self.output_folder = output_folder
        self._check_ffmpeg()

    def _check_ffmpeg(self):
        """Check if ffmpeg is available."""
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("ffmpeg not found - download functionality may be limited")

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize filename for filesystem."""
        # Remove invalid characters
        name = re.sub(r'[<>:"/\\|?*]', '', name)
        # Replace multiple spaces
        name = re.sub(r'\s+', ' ', name)
        return name.strip()

    async def download(self, playlist_url: str, output_name: str,
                       progress_callback=None, total_duration: float = None) -> Tuple[bool, str]:
        """
        Download HLS stream to file.

        Args:
            playlist_url: M3U8 playlist URL
            output_name: Output filename (without extension)
            progress_callback: Optional async callback(progress, elapsed, size)
            total_duration: Total duration in seconds for progress calculation

        Returns:
            Tuple of (success, output_path or error message)
        """
        output_name = self._sanitize_filename(output_name)
        output_path = os.path.join(self.output_folder, f"{output_name}.mp4")

        # Create output directory
        os.makedirs(self.output_folder, exist_ok=True)

        # Check if file already exists
        if os.path.exists(output_path):
            logger.info(f"File already exists: {output_path}")
            if progress_callback:
                await progress_callback(1.0, 0, "0 MB")
            return (True, output_path)

        logger.info(f"Downloading to: {output_path}")
        start_time = time.time()

        try:
            # Build ffmpeg command with progress output
            cmd = [
                "ffmpeg",
                "-i", playlist_url,
                "-c", "copy",  # Copy streams without re-encoding
                "-bsf:a", "aac_adtstoasc",  # Fix audio for MP4
                "-movflags", "+faststart",  # Enable streaming
                "-y",  # Overwrite output
                "-progress", "pipe:1",  # Progress to stdout
                "-loglevel", "error",
                output_path
            ]

            # Run ffmpeg with progress parsing
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            current_time = 0
            last_callback = 0

            # Read progress from stdout
            while True:
                line = await process.stdout.readline()
                if not line:
                    break

                line = line.decode().strip()

                # Parse out_time
                if line.startswith("out_time="):
                    time_str = line.split("=")[1]
                    if time_str and time_str != "N/A":
                        try:
                            parts = time_str.split(":")
                            if len(parts) == 3:
                                h, m, s = parts
                                current_time = int(h) * 3600 + int(m) * 60 + float(s)
                        except:
                            pass

                # Parse total_size
                size_str = "0 MB"
                if line.startswith("total_size="):
                    try:
                        size_bytes = int(line.split("=")[1])
                        size_str = f"{size_bytes / 1024 / 1024:.1f} MB"
                    except:
                        pass

                # Call progress callback (rate limited)
                now = time.time()
                if now - last_callback >= 3:
                    last_callback = now
                    elapsed = now - start_time

                    # Calculate progress
                    if total_duration and total_duration > 0:
                        progress = min(current_time / total_duration, 0.99)
                    elif current_time > 0:
                        # Estimate based on typical episode length (45 min)
                        progress = min(current_time / 2700, 0.99)
                    else:
                        progress = 0

                    # Log progress for debug
                    logger.debug(f"Download progress: {progress:.1%} | Time: {current_time:.0f}s | Size: {size_str}")

                    if progress_callback:
                        await progress_callback(progress, elapsed, size_str)

            await process.wait()
            stdout, stderr = b"", await process.stderr.read()

            if process.returncode == 0:
                # Verify file was created
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    file_size = os.path.getsize(output_path)
                    elapsed = time.time() - start_time
                    logger.info(f"Download complete: {output_path} ({file_size / 1024 / 1024:.1f} MB)")
                    if progress_callback:
                        await progress_callback(1.0, elapsed, f"{file_size / 1024 / 1024:.1f} MB")
                    return (True, output_path)
                else:
                    logger.error("Output file is empty or missing")
                    return (False, "Output file is empty")
            else:
                error_msg = stderr.decode() if stderr else "Unknown error"
                logger.error(f"ffmpeg error: {error_msg}")
                return (False, error_msg)

        except Exception as e:
            logger.error(f"Download error: {e}")
            return (False, str(e))

    def download_sync(self, playlist_url: str, output_name: str) -> Tuple[bool, str]:
        """Synchronous wrapper for download."""
        return asyncio.get_event_loop().run_until_complete(
            self.download(playlist_url, output_name)
        )


# ==================== MAIN STREAMING COMMUNITY MANAGER ====================

class StreamingCommunity:
    """
    Main manager class for StreamingCommunity operations.
    Provides high-level methods for search, info, and download.
    """

    def __init__(self, base_url: str = None,
                 movies_folder: str = "/downloads/movies",
                 series_folder: str = "/downloads/series"):
        self.client = StreamingCommunityClient(base_url)
        self.movies_folder = movies_folder
        self.series_folder = series_folder
        self._base_url = None

    @property
    def base_url(self) -> str:
        if not self._base_url:
            self._base_url = self.client._detect_base_url()
        return self._base_url

    def search(self, query: str) -> List[MediaItem]:
        """Search for films and series."""
        return self.client.search(query)

    def search_films(self, query: str) -> List[MediaItem]:
        """Search for films only."""
        results = self.client.search(query)
        return [r for r in results if r.type == "movie"]

    def search_series(self, query: str) -> List[MediaItem]:
        """Search for TV series only."""
        results = self.client.search(query)
        return [r for r in results if r.type == "tv"]

    def get_series_info(self, item: MediaItem) -> Optional[SeriesInfo]:
        """Get complete series information."""
        return self.client.get_series_info(
            item.id, item.slug, item.provider_language
        )

    def get_season_episodes(self, series: SeriesInfo, season_number: int) -> List[Episode]:
        """Get episodes for a season."""
        return self.client.get_season_episodes(series, season_number)

    def get_video_url(self, media_id: int, episode_id: int = None,
                      is_series: bool = False, lang: str = "it") -> Optional[str]:
        """
        Get video streaming URL.

        Args:
            media_id: Media ID
            episode_id: Episode ID (for series)
            is_series: True if TV series
            lang: Language code

        Returns:
            Playlist URL or None
        """
        source = VideoSource(self.base_url, media_id, is_series, lang)

        if source.get_iframe(episode_id):
            if source.get_content():
                return source.get_playlist()

        return None

    async def download_film(self, item: MediaItem, progress_callback=None) -> Tuple[bool, str]:
        """
        Download a film.

        Args:
            item: MediaItem object
            progress_callback: Optional progress callback

        Returns:
            Tuple of (success, path or error)
        """
        logger.info(f"Downloading film: {item.name}")

        playlist_url = self.get_video_url(item.id, is_series=False, lang=item.provider_language)
        if not playlist_url:
            return (False, "Could not get video URL")

        # Create folder for film
        film_folder = os.path.join(self.movies_folder, item.name)
        downloader = HLSDownloader(film_folder)

        return await downloader.download(playlist_url, item.name, progress_callback)

    async def download_episode(self, series: SeriesInfo, season_number: int,
                               episode: Episode, lang: str = "it",
                               progress_callback=None) -> Tuple[bool, str]:
        """
        Download a single episode.

        Args:
            series: SeriesInfo object
            season_number: Season number
            episode: Episode object
            lang: Language code
            progress_callback: Optional progress callback

        Returns:
            Tuple of (success, path or error)
        """
        logger.info(f"Downloading: {series.name} S{season_number:02d}E{episode.number:02d}")

        playlist_url = self.get_video_url(
            series.id, episode.id, is_series=True, lang=lang
        )
        if not playlist_url:
            return (False, "Could not get video URL")

        # Create folder structure: series/S01/
        season_folder = os.path.join(
            self.series_folder,
            series.name,
            f"S{season_number:02d}"
        )
        downloader = HLSDownloader(season_folder)

        # Filename: SeriesName - S01E01 - Episode Title
        filename = f"{series.name} - S{season_number:02d}E{episode.number:02d}"
        if episode.name:
            filename += f" - {episode.name}"

        return await downloader.download(playlist_url, filename, progress_callback)

    async def download_season(self, series: SeriesInfo, season_number: int,
                              lang: str = "it", progress_callback=None,
                              max_parallel: int = 3) -> Dict[int, Tuple[bool, str]]:
        """
        Download all episodes of a season with parallel downloads.

        Args:
            series: SeriesInfo object
            season_number: Season number
            lang: Language code
            progress_callback: Optional callback(episode_num, total, success)
            max_parallel: Max parallel downloads (default: 3)

        Returns:
            Dict mapping episode numbers to (success, path or error)
        """
        season = series.get_season(season_number)
        if not season:
            logger.error(f"Season {season_number} not found")
            return {}

        if not season.episodes:
            self.get_season_episodes(series, season_number)

        results = {}
        semaphore = asyncio.Semaphore(max_parallel)
        completed = 0
        total = len(season.episodes)

        async def download_with_semaphore(episode):
            nonlocal completed
            async with semaphore:
                success, result = await self.download_episode(
                    series, season_number, episode, lang
                )
                completed += 1
                if progress_callback:
                    await progress_callback(completed, total, episode.number, success)
                return episode.number, (success, result)

        # Create all download tasks
        tasks = [download_with_semaphore(ep) for ep in season.episodes]

        # Run all tasks concurrently (semaphore limits parallelism)
        completed_tasks = await asyncio.gather(*tasks, return_exceptions=True)

        for task_result in completed_tasks:
            if isinstance(task_result, Exception):
                logger.error(f"Episode download error: {task_result}")
            else:
                ep_num, result = task_result
                results[ep_num] = result

        return results


# ==================== TEST / EXAMPLE USAGE ====================

if __name__ == "__main__":
    import asyncio

    async def test():
        sc = StreamingCommunity()

        # Test search
        print("Searching for 'breaking bad'...")
        results = sc.search("breaking bad")
        for r in results[:5]:
            print(f"  - {r}")

        if results:
            # Test series info
            series_item = next((r for r in results if r.type == "tv"), None)
            if series_item:
                print(f"\nGetting info for: {series_item.name}")
                info = sc.get_series_info(series_item)
                if info:
                    print(f"  Seasons: {len(info.seasons)}")
                    for s in info.seasons:
                        print(f"    - {s}")

    asyncio.run(test())
