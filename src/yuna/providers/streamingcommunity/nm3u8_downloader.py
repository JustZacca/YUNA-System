"""
N_m3u8DL-RE downloader for YUNA-System.
Provides faster and more reliable HLS downloads using N_m3u8DL-RE.
"""

import os
import re
import json
import time
import logging
import subprocess
import asyncio
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from pathlib import Path

from yuna.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class Nm3u8Config:
    """Configuration for N_m3u8DL-RE downloader."""
    binary_path: Optional[str] = None  # Path to N_m3u8DL-RE binary
    thread_count: int = 16  # Download threads
    retry_count: int = 3   # Download retry count
    timeout: int = 100     # HTTP timeout
    headers: Optional[Dict[str, str]] = None  # Custom headers
    temp_dir: Optional[str] = None   # Temp directory
    force_ansi: bool = False  # Force ANSI console
    auto_select: bool = True   # Auto-select best quality
    concurrent_download: bool = True  # Concurrent audio/video download
    max_speed: Optional[str] = None  # Speed limit (e.g., "15M", "100K")
    live_as_vod: bool = False  # Download live as VOD
    
    def __post_init__(self):
        if self.headers is None:
            self.headers = {}


class Nm3u8ProgressParser:
    """Parses N_m3u8DL-RE progress output."""
    
    def __init__(self):
        self.total_segments = 0
        self.downloaded_segments = 0
        self.speed = ""
        self.size = ""
        self.total_size = ""
        self.progress = 0.0
        
    def parse_line(self, line: str) -> Optional[float]:
        """Parse progress line from N_m3u8DL-RE."""
        line = line.strip()
        
        # Pattern 1: Main progress bar format
        # [████████████████████████████████████] 100.00% (100/100) 10.2 MB/10.2 MB/s ETA: 0:00:00
        pattern = re.compile(r'\[(█░+]+)\s+(\d+\.\d+)%\s+\((\d+)/(\d+)\)')
        match = pattern.search(line)
        if match:
            self.progress = float(match.group(2)) / 100
            # Extract speed and size from the rest of the line
            speed_match = re.search(r'([\d.]+)\s*MB/s', line)
            if speed_match:
                self.speed = f"{speed_match.group(1)} MB/s"
            
        # Pattern 2: Percentage only
        perc_match = re.search(r'(\d+\.\d+)%', line)
        if perc_match:
            self.progress = float(perc_match.group(1)) / 100
            speed_match = re.search(r'([\d.]+)\s*MB/s', line)
            if speed_match:
                self.speed = f"{speed_match.group(1)} MB/s"
            size_match = re.search(r'([\d.]+)\s*MB', line)
            if size_match:
                current_mb = float(size_match.group(1))
                self.size = f"{current_mb:.1f} MB"
            return self.progress
                
        # Pattern 3: Compressed format (common in N_m3u8DL-RE)
        # [████████████████████████████████] 100.00% (100/100) 10.2 MB/s ETA: 00:00
        # Pattern 4: Advanced multi-format
        # [\████████████████████████████] 99.75% (40/40 MB/3.8 MB/s ETA: 00:07:15)
        # [████████████████████████] 99.75% (40/40 MB/3.8 MB/s ETA: 00:07:15)
        pattern4a = re.compile(r'\[(█░+░+]+)\s+(\d+\.\d+)%\s+\]\s+(\d+)/(\d+)\s+[A-Z/]+\s+[\d.]+/[A-Z]+\s+ETA:\s+[\d:]+')
        
        match = pattern4a.search(line)
        if match:
            # Estrai numeri tra parentesi e parentesi
            progress = float(match.group(1)) / 100
            
        # Pattern 5: Speed and size pattern
        speed_size_match = re.search(r'(\d+(?:\.\d+)?)\s*/s', line)
        size_match = re.search(r'(\d+(?:\.\d+)?)\s*/\s*([\d.]+)\s*MB', line)
        if speed_size_match:
            self.speed = f"{speed_size_match.group(1)}/s"  # MB/s
            current_mb = float(speed_size_match.group(1))
            if size_match:
                total_mb = float(size_match.group(2))
                self.size = f"{current_mb:.1f} MB/{total_mb:.1f} MB"
                self.progress = current_mb / total_mb if total_mb > 0 else 0
            
            return self.progress
            
        # Pattern 6: Compact format (fallback)
        perc_match = re.search(r'(\d+(?:\.\d+)?)%', line)
        if perc_match:
            self.progress = float(perc_match.group(1)) / 100
            speed_match = re.search(r'(\d+(?:\.\d+)?\s*/s)', line)
            if speed_match:
                self.speed = f"{speed_match.group(1)}/s"
        else:
            # Try to extract speed from progress bar
            speed_match = re.search(r'(\d+(?:\.\d+)?\s*/s)', line)
            if speed_match:
                self.speed = f"{speed_match.group(1)}/s"
                
            # Try to extract size from compact bar
            size_match = re.search(r'\((\d+(?:\.\d+)?)\s*MB', line)
            if size_match:
                size_mb = float(size_match.group(1))
                self.size = f"{size_mb:.1f} MB"
                if perc_match:
                    self.total_mb = float(perc_match.group(1))
                    self.progress = self.downloaded_segments / self.total_segments
                    self.progress = self.downloaded_segments / self.total_segments
                self.downloaded_segments += 1
            return self.progress
                
        return self.progress
            
        # Alternative percentage format
        alt_percent_match = re.search(r'([\d.]+)%', line)
        if alt_percent_match:
            self.progress = float(alt_percent_match.group(1)) / 100
            
        # Parse segments (40/100)
        segment_match = re.search(r'\((\d+)/(\d+)\)', line)
        if segment_match:
            self.downloaded_segments = int(segment_match.group(1))
            self.total_segments = int(segment_match.group(2))
            if self.total_segments > 0:
                self.progress = self.downloaded_segments / self.total_segments
                return self.progress
                
        # Parse speed patterns (MB/s, KB/s)
        speed_match = re.search(r'([\d.]+)\s*(MB|KB)/s', line, re.IGNORECASE)
        if speed_match:
            speed_val = speed_match.group(1)
            speed_unit = speed_match.group(2).upper()
            self.speed = f"{speed_val}{speed_unit}/s"
            
        # Parse size (current/total)
        size_match = re.search(r'([\d.]+)\s*(MB|KB)/([\d.]+)\s*(MB|KB)', line, re.IGNORECASE)
        if size_match:
            current_size = size_match.group(1)
            current_unit = size_match.group(2).upper()
            total_size = size_match.group(3)
            total_unit = size_match.group(4).upper()
            self.size = f"{current_size}{current_unit}"
            self.total_size = f"{total_size}{total_unit}"
            
        return self.progress if hasattr(self, 'progress') else None


class Nm3u8DLREDownloader:
    """
    N_m3u8DL-RE based HLS downloader.
    Provides faster parallel downloads with better error handling.
    """
    
    def __init__(self, output_folder: str, config: Optional[Nm3u8Config] = None):
        """
        Initialize N_m3u8DL-RE downloader.
        
        Args:
            output_folder: Output directory for downloads
            config: Download configuration options
        """
        self.output_folder = output_folder
        self.config = config or Nm3u8Config()
        self._binary_path = None
        
        # Initialize components
        self._check_binary()
        
    def _check_binary(self):
        """Check if N_m3u8DL-RE binary is available."""
        if self.config.binary_path and os.path.exists(self.config.binary_path):
            self._binary_path = self.config.binary_path
            logger.info(f"Using configured N_m3u8DL-RE: {self._binary_path}")
            return
            
        # Check common locations
        common_names = ["N_m3u8DL-RE", "N_m3u8DL-RE.exe"]
        search_paths = [
            os.getcwd(),
            "/usr/local/bin",
            "/usr/bin",
            os.path.expanduser("~/.local/bin"),
        ]
        
        for name in common_names:
            for path in search_paths:
                full_path = os.path.join(path, name)
                if os.path.exists(full_path) and os.access(full_path, os.X_OK):
                    self._binary_path = full_path
                    logger.info(f"Found N_m3u8DL-RE: {self._binary_path}")
                    return
                    
        # Fallback: check if in PATH
        try:
            result = subprocess.run(
                ["N_m3u8DL-RE", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                self._binary_path = "N_m3u8DL-RE"
                logger.info("N_m3u8DL-RE found in PATH")
                return
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            pass
            
        logger.warning("N_m3u8DL-RE binary not found - falling back to ffmpeg")
        
    def is_available(self) -> bool:
        """Check if N_m3u8DL-RE is available."""
        return self._binary_path is not None
        
    def _sanitize_filename(self, name: str) -> str:
        """Sanitize filename for filesystem."""
        # Remove invalid characters
        name = re.sub(r'[<>:"/\\|?*]', '', name)
        # Replace multiple spaces
        name = re.sub(r'\s+', ' ', name)
        return name.strip()
        
    def _build_command(self, playlist_url: str, output_path: str) -> List[str]:
        """Build N_m3u8DL-RE command with all options."""
        if not self._binary_path:
            raise RuntimeError("N_m3u8DL-RE binary not available")
            
        cmd = [self._binary_path, playlist_url]
        
        # Output options
        cmd.extend([
            "--save-name", os.path.splitext(os.path.basename(output_path))[0],
            "--save-dir", os.path.dirname(output_path),
        ])
        
        # Performance options
        cmd.extend([
            "--thread-count", str(self.config.thread_count),
            "--download-retry-count", str(self.config.retry_count),
            "--http-request-timeout", str(self.config.timeout),
        ])
        
        # Quality and selection
        if self.config.auto_select:
            cmd.append("--auto-select")
            
        # Concurrency
        if self.config.concurrent_download:
            cmd.append("-mt")  # concurrent download
            
        # Headers
        if self.config.headers:
            for key, value in self.config.headers.items():
                cmd.extend(["-H", f"{key}: {value}"])
                
        # Speed limit
        if self.config.max_speed:
            cmd.extend(["-R", self.config.max_speed])
            
        # Live streaming options
        if self.config.live_as_vod:
            cmd.append("--live-perform-as-vod")
            
        # Temp directory
        if self.config.temp_dir:
            cmd.extend(["--tmp-dir", self.config.temp_dir])
            
        # ANSI/console options
        if self.config.force_ansi:
            cmd.append("--force-ansi-console")
        else:
            # Force terminal-style output for better progress parsing
            cmd.extend(["--force-ansi-console"])
            
        # Cleanup options
        cmd.append("--del-after-done")  # Clean temp files
        cmd.append("--no-log")  # Disable log file
        
        # Additional options for better compatibility
        cmd.extend([
            "--check-segments-count",  # Verify download integrity
            "--write-meta-json",       # Write metadata
        ])
        
        return cmd
        
    async def download(self, playlist_url: str, output_name: str,
                       progress_callback=None, total_duration: Optional[float] = None) -> Tuple[bool, str]:
        """
        Download HLS stream using N_m3u8DL-RE.
        
        Args:
            playlist_url: M3U8 playlist URL
            output_name: Output filename (without extension)
            progress_callback: Optional async callback(progress, elapsed, size)
            total_duration: Total duration in seconds (for compatibility)
            
        Returns:
            Tuple of (success, output_path or error message)
        """
        if not self.is_available():
            logger.error("N_m3u8DL-RE not available")
            return (False, "N_m3u8DL-RE binary not found")
            
        output_name = self._sanitize_filename(output_name)
        output_path = os.path.join(self.output_folder, f"{output_name}.mp4")
        
        # Create output directory
        os.makedirs(self.output_folder, exist_ok=True)
        
        # Check if file already exists
        if os.path.exists(output_path):
            logger.info(f"File already exists: {output_path}")
            if progress_callback:
                await progress_callback(1.0, 0, "0 MB", "0 MB/s")
            return (True, output_path)
            
        logger.info(f"Starting N_m3u8DL-RE download: {output_name}")
        start_time = time.time()
        
        try:
            # Build command
            cmd = self._build_command(playlist_url, output_path)
            
            # Add user agent header if not specified
            if not self.config.headers or "User-Agent" not in self.config.headers:
                cmd.extend(["-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"])
                
            logger.debug(f"N_m3u8DL-RE command: {' '.join(cmd)}")
            
            # Start process
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Parse progress
            parser = Nm3u8ProgressParser()
            last_callback = 0
            last_progress_line = ""
            
            last_progress_line = ""
            last_callback = 0.0
            
            async def read_output():
                """Read and parse output from both stdout and stderr."""
                nonlocal last_progress_line, last_callback
                while True:
                    # Try stdout first
                    try:
                        line = await process.stdout.readline() if process.stdout else b""
                    except AttributeError:
                        line = b""
                    if not line:
                        # Try stderr if stdout is done
                        try:
                            line = await process.stderr.readline() if process.stderr else b""
                        except AttributeError:
                            line = b""
                        if not line:
                            break
                            
                    line_str = line.decode('utf-8', errors='ignore').strip()
                    if not line_str:
                        continue
                        
                    # Skip duplicate progress lines (common in N_m3u8DL-RE)
                    if line_str == last_progress_line:
                        continue
                    last_progress_line = line_str
                    
                    logger.debug(f"N_m3u8DL-RE: {line_str}")
                    
                    # Parse progress
                    progress = parser.parse_line(line_str)
                    if progress is not None and progress > 0:
                        # Rate limit progress callbacks
                        now = time.time()
                        if now - last_callback >= 1.5:  # Update every 1.5 seconds
                            last_callback = now
                            elapsed = now - start_time
                            size = parser.size or "0 MB"
                            speed = parser.speed or "0 MB/s"
                            
                            logger.debug(f"Progress: {progress:.1%} | Size: {size} | Speed: {speed}")
                            
                            if progress_callback:
                                await progress_callback(progress, elapsed, size, speed)
                                
            # Start background reader
            reader_task = asyncio.create_task(read_output())
            
            # Wait for completion
            await process.wait()
            reader_task.cancel()
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                # Verify output file
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    file_size = os.path.getsize(output_path) / 1024 / 1024
                    elapsed = time.time() - start_time
                    logger.info(f"N_m3u8DL-RE download complete: {output_path} ({file_size:.1f} MB, {elapsed:.0f}s)")
                    
                    if progress_callback:
                        await progress_callback(1.0, elapsed, f"{file_size:.1f} MB", "Complete")
                        
                    return (True, output_path)
                else:
                    return (False, "Output file not created or empty")
            else:
                error_msg = stderr.decode('utf-8', errors='ignore') if stderr else "Unknown error"
                logger.error(f"N_m3u8DL-RE error (code {process.returncode}): {error_msg}")
                return (False, f"N_m3u8DL-RE failed: {error_msg[:200]}")
                
        except asyncio.TimeoutError:
            logger.error("Download timeout")
            return (False, "Download timeout")
        except Exception as e:
            logger.error(f"Download error: {e}")
            return (False, str(e))
            
    def download_sync(self, playlist_url: str, output_name: str) -> Tuple[bool, str]:
        """Synchronous wrapper for download."""
        return asyncio.get_event_loop().run_until_complete(
            self.download(playlist_url, output_name)
        )
        
    async def get_stream_info(self, playlist_url: str) -> Optional[Dict[str, Any]]:
        """
        Get stream information without downloading.
        
        Args:
            playlist_url: M3U8 playlist URL
            
        Returns:
            Stream information dict or None
        """
        if not self.is_available():
            return None
            
        try:
            # Build command for info only
            cmd = [
                self._binary_path, playlist_url,
                "--skip-download",  # Don't download, just parse
                "--write-meta-json",  # Write metadata
                "--tmp-dir", "/tmp"  # Use temp dir
            ]
            
            # Add headers
            if self.config.headers:
                for key, value in self.config.headers.items():
                    cmd.extend(["-H", f"{key}: {value}"])
                    
            # Run command
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await result.wait()
            
            # Look for generated JSON metadata file
            # (This is a simplified implementation - actual file location may vary)
            return {"status": "success", "url": playlist_url}
            
        except Exception as e:
            logger.error(f"Failed to get stream info: {e}")
            return None


def create_downloader(output_folder: str, prefer_nm3u8: bool = True,
                     config: Optional[Nm3u8Config] = None):
    """
    Factory function to create appropriate downloader.
    
    Args:
        output_folder: Output directory
        prefer_nm3u8: Whether to prefer N_m3u8DL-RE over ffmpeg
        config: Configuration for N_m3u8DL-RE
        
    Returns:
        Downloader instance
    """
    if prefer_nm3u8:
        nm3u8_downloader = Nm3u8DLREDownloader(output_folder, config)
        if nm3u8_downloader.is_available():
            return nm3u8_downloader
        else:
            logger.info("N_m3u8DL-RE not available, will use HLSDownloader (ffmpeg)")
            
    # Fallback to original HLSDownloader
    from yuna.providers.streamingcommunity.client import HLSDownloader
    return HLSDownloader(output_folder)