"""
Download Manager for YUNA-System.
Handles download queue, parallel downloads, and Telegram progress updates.
"""

import asyncio
import time
import logging
import re
from dataclasses import dataclass, field
from typing import Optional, Callable, Any
from enum import Enum
from collections import deque

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


class DownloadStatus(Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class DownloadJob:
    """Represents a download job in the queue."""
    id: str
    name: str
    download_func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    status: DownloadStatus = DownloadStatus.PENDING
    progress: float = 0.0
    error: Optional[str] = None
    result: Any = None
    chat_id: Optional[int] = None
    message_id: Optional[int] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None


class TelegramProgress:
    """Handles Telegram progress updates with rate limiting."""

    def __init__(self, bot, chat_id: int, message_id: int, min_interval: float = 3.0):
        """
        Initialize progress handler.

        Args:
            bot: Telegram bot instance
            chat_id: Chat ID to update
            message_id: Message ID to edit
            min_interval: Minimum seconds between updates (rate limiting)
        """
        self.bot = bot
        self.chat_id = chat_id
        self.message_id = message_id
        self.min_interval = min_interval
        self.last_update = 0
        self.last_text = ""

    async def update(self, progress: float, text: str = "",
                     elapsed: float = 0, speed: str = "", size: str = ""):
        """
        Update progress message.

        Args:
            progress: Progress value 0.0 to 1.0
            text: Description text
            elapsed: Elapsed time in seconds
            speed: Download speed string
            size: Downloaded size string
        """
        now = time.time()

        # Rate limiting - skip if too soon (unless complete)
        if now - self.last_update < self.min_interval and progress < 1.0:
            return

        self.last_update = now

        # Build progress bar
        filled = int(10 * progress)
        bar = "█" * filled + "░" * (10 - filled)

        # Build message
        lines = [f"📥 *{text}*"] if text else ["📥 *Downloading...*"]
        lines.append(f"`[{bar}]` {progress:.0%}")

        if elapsed > 0:
            elapsed_str = self._format_time(elapsed)
            if progress > 0 and progress < 1.0:
                eta = (elapsed / progress) * (1 - progress)
                eta_str = self._format_time(eta)
                lines.append(f"⏱️ {elapsed_str} | ETA: ~{eta_str}")
            else:
                lines.append(f"⏱️ {elapsed_str}")

        if speed:
            lines.append(f"📶 {speed}")

        if size:
            lines.append(f"📦 {size}")

        new_text = "\n".join(lines)

        # Only update if text changed
        if new_text == self.last_text:
            return

        self.last_text = new_text

        try:
            await self.bot.edit_message_text(
                chat_id=self.chat_id,
                message_id=self.message_id,
                text=new_text,
                parse_mode="Markdown"
            )
        except Exception as e:
            # Ignore edit errors (message not modified, etc.)
            logger.debug(f"Progress update error: {e}")

    async def complete(self, success: bool, text: str = ""):
        """Show completion message."""
        if success:
            msg = f"✅ *{text}*\nDownload completato!" if text else "✅ Download completato!"
        else:
            msg = f"❌ *{text}*\nDownload fallito!" if text else "❌ Download fallito!"

        try:
            await self.bot.edit_message_text(
                chat_id=self.chat_id,
                message_id=self.message_id,
                text=msg,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.debug(f"Completion update error: {e}")

    def _format_time(self, seconds: float) -> str:
        """Format seconds to MM:SS or HH:MM:SS."""
        seconds = int(seconds)
        if seconds < 3600:
            return f"{seconds // 60}:{seconds % 60:02d}"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            secs = seconds % 60
            return f"{hours}:{minutes:02d}:{secs:02d}"


class FFmpegProgress:
    """Parses ffmpeg progress output."""

    def __init__(self, total_duration: float = None):
        """
        Initialize ffmpeg progress parser.

        Args:
            total_duration: Total duration in seconds (if known)
        """
        self.total_duration = total_duration
        self.current_time = 0
        self.speed = ""
        self.size = ""

    def parse_line(self, line: str) -> Optional[float]:
        """
        Parse a line of ffmpeg output.

        Args:
            line: Line from ffmpeg stderr

        Returns:
            Progress value 0.0-1.0 if parseable, None otherwise
        """
        line = line.strip()

        # Parse time (out_time or time=)
        time_match = re.search(r'(?:out_time|time)=(\d{2}):(\d{2}):(\d{2})\.(\d+)', line)
        if time_match:
            hours, minutes, seconds, ms = time_match.groups()
            self.current_time = int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(ms) / 100

        # Parse speed
        speed_match = re.search(r'speed=\s*([\d.]+)x', line)
        if speed_match:
            self.speed = f"{speed_match.group(1)}x"

        # Parse size
        size_match = re.search(r'size=\s*(\d+)kB', line)
        if size_match:
            size_kb = int(size_match.group(1))
            if size_kb > 1024:
                self.size = f"{size_kb / 1024:.1f} MB"
            else:
                self.size = f"{size_kb} KB"

        # Calculate progress if we have total duration
        if self.total_duration and self.total_duration > 0:
            return min(self.current_time / self.total_duration, 1.0)

        return None


class DownloadManager:
    """
    Manages download queue with parallel execution.
    Downloads run in background, bot stays responsive.
    """

    def __init__(self, max_parallel: int = 2):
        """
        Initialize download manager.

        Args:
            max_parallel: Maximum parallel downloads
        """
        self.max_parallel = max_parallel
        self.queue: deque[DownloadJob] = deque()
        self.active: dict[str, DownloadJob] = {}
        self.completed: dict[str, DownloadJob] = {}
        self.semaphore = asyncio.Semaphore(max_parallel)
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None
        self._job_counter = 0

    def _generate_job_id(self) -> str:
        """Generate unique job ID."""
        self._job_counter += 1
        return f"job_{self._job_counter}_{int(time.time())}"

    async def start(self):
        """Start the download manager worker."""
        if self._running:
            return

        self._running = True
        self._worker_task = asyncio.create_task(self._worker())
        logger.info("Download manager started")

    async def stop(self):
        """Stop the download manager."""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        logger.info("Download manager stopped")

    def add_job(self, name: str, download_func: Callable,
                args: tuple = (), kwargs: dict = None,
                chat_id: int = None, message_id: int = None) -> str:
        """
        Add a download job to the queue.

        Args:
            name: Display name for the download
            download_func: Async function to execute
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function
            chat_id: Telegram chat ID for progress updates
            message_id: Telegram message ID for progress updates

        Returns:
            Job ID
        """
        job_id = self._generate_job_id()

        job = DownloadJob(
            id=job_id,
            name=name,
            download_func=download_func,
            args=args,
            kwargs=kwargs or {},
            chat_id=chat_id,
            message_id=message_id
        )

        self.queue.append(job)
        logger.info(f"Added job '{name}' to queue (ID: {job_id})")

        return job_id

    def get_job(self, job_id: str) -> Optional[DownloadJob]:
        """Get job by ID."""
        # Check active
        if job_id in self.active:
            return self.active[job_id]

        # Check completed
        if job_id in self.completed:
            return self.completed[job_id]

        # Check queue
        for job in self.queue:
            if job.id == job_id:
                return job

        return None

    def get_queue_status(self) -> dict:
        """Get current queue status."""
        return {
            "pending": len(self.queue),
            "active": len(self.active),
            "completed": len(self.completed),
            "active_jobs": [
                {"id": j.id, "name": j.name, "progress": j.progress}
                for j in self.active.values()
            ]
        }

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending job."""
        for i, job in enumerate(self.queue):
            if job.id == job_id:
                job.status = DownloadStatus.CANCELLED
                del self.queue[i]
                self.completed[job_id] = job
                logger.info(f"Cancelled job '{job.name}'")
                return True
        return False

    async def _worker(self):
        """Background worker that processes the queue."""
        while self._running:
            try:
                # Check if we have jobs and capacity
                if self.queue and len(self.active) < self.max_parallel:
                    job = self.queue.popleft()
                    asyncio.create_task(self._execute_job(job))

                await asyncio.sleep(0.5)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker error: {e}")
                await asyncio.sleep(1)

    async def _execute_job(self, job: DownloadJob):
        """Execute a single download job."""
        async with self.semaphore:
            job.status = DownloadStatus.DOWNLOADING
            job.started_at = time.time()
            self.active[job.id] = job

            logger.info(f"Starting download: {job.name}")

            try:
                # Add progress callback to kwargs if we have chat/message IDs
                if job.chat_id and job.message_id:
                    # The download function should accept a progress_callback
                    job.kwargs['job'] = job

                # Execute the download function
                result = await job.download_func(*job.args, **job.kwargs)

                job.result = result
                job.status = DownloadStatus.COMPLETED
                job.progress = 1.0
                logger.info(f"Completed download: {job.name}")

            except Exception as e:
                job.status = DownloadStatus.FAILED
                job.error = str(e)
                logger.error(f"Failed download '{job.name}': {e}")

            finally:
                job.completed_at = time.time()
                del self.active[job.id]
                self.completed[job.id] = job

                # Clean old completed jobs (keep last 50)
                while len(self.completed) > 50:
                    oldest = min(self.completed.values(), key=lambda j: j.completed_at)
                    del self.completed[oldest.id]


# Global download manager instance
download_manager = DownloadManager(max_parallel=2)
