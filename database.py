"""
Database module for YUNA-System.
Handles SQLite database operations for anime, TV shows, and movies.
"""

import sqlite3
import logging
import os
import json
from datetime import datetime
from contextlib import contextmanager
from typing import Optional, List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# Default database path
DEFAULT_DB_PATH = "yuna.db"


class Database:
    """SQLite database handler with CRUD operations."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize database with schema."""
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS anime (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    link TEXT NOT NULL,
                    last_update TIMESTAMP,
                    episodi_scaricati INTEGER DEFAULT 0,
                    numero_episodi INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS tv (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    link TEXT NOT NULL,
                    last_update TIMESTAMP,
                    episodi_scaricati INTEGER DEFAULT 0,
                    numero_episodi INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS movies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    link TEXT NOT NULL,
                    last_update TIMESTAMP,
                    scaricato INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_anime_name ON anime(name);
                CREATE INDEX IF NOT EXISTS idx_tv_name ON tv(name);
                CREATE INDEX IF NOT EXISTS idx_movies_name ON movies(name);
            """)
            logger.info(f"Database initialized: {self.db_path}")

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()

    # ==================== ANIME OPERATIONS ====================

    def get_all_anime(self) -> List[Dict[str, Any]]:
        """Get all anime from database."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT name, link, last_update, episodi_scaricati, numero_episodi
                FROM anime ORDER BY name
            """)
            return [dict(row) for row in cursor.fetchall()]

    def get_anime_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get anime by exact name."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM anime WHERE name = ?", (name,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def search_anime_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Search anime by partial name (case insensitive)."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM anime WHERE LOWER(name) LIKE LOWER(?)",
                (f"%{name}%",)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def add_anime(self, name: str, link: str, last_update: datetime,
                  numero_episodi: int) -> bool:
        """Add new anime to database."""
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO anime (name, link, last_update, numero_episodi)
                    VALUES (?, ?, ?, ?)
                """, (name, link, last_update.strftime("%Y-%m-%d %H:%M:%S"),
                      numero_episodi))
                logger.info(f"Anime '{name}' added to database.")
                return True
        except sqlite3.IntegrityError:
            logger.warning(f"Anime '{name}' already exists.")
            return False

    def update_anime_episodes(self, name: str, episodi_scaricati: int) -> bool:
        """Update downloaded episodes count."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                UPDATE anime SET episodi_scaricati = ?
                WHERE name = ?
            """, (episodi_scaricati, name))
            if cursor.rowcount > 0:
                logger.info(f"Updated episodes for '{name}': {episodi_scaricati}")
                return True
            logger.warning(f"Anime '{name}' not found.")
            return False

    def update_anime_total_episodes(self, name: str, numero_episodi: int) -> bool:
        """Update total episodes count."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                UPDATE anime SET numero_episodi = ?
                WHERE name = ?
            """, (numero_episodi, name))
            return cursor.rowcount > 0

    def update_anime_last_update(self, name: str, last_update: datetime) -> bool:
        """Update last update timestamp."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                UPDATE anime SET last_update = ?
                WHERE name = ?
            """, (last_update.strftime("%Y-%m-%d %H:%M:%S"), name))
            return cursor.rowcount > 0

    def remove_anime(self, name: str) -> bool:
        """Remove anime from database."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM anime WHERE name = ?", (name,)
            )
            if cursor.rowcount > 0:
                logger.info(f"Anime '{name}' removed from database.")
                return True
            logger.warning(f"Anime '{name}' not found.")
            return False

    def get_anime_link(self, name: str) -> Optional[str]:
        """Get anime link by name (partial match)."""
        anime = self.search_anime_by_name(name)
        return anime["link"] if anime else None

    # ==================== TV OPERATIONS ====================

    def get_all_tv(self) -> List[Dict[str, Any]]:
        """Get all TV shows from database."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT name, link, last_update, episodi_scaricati, numero_episodi
                FROM tv ORDER BY name
            """)
            return [dict(row) for row in cursor.fetchall()]

    def add_tv(self, name: str, link: str, last_update: datetime,
               numero_episodi: int) -> bool:
        """Add new TV show to database."""
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO tv (name, link, last_update, numero_episodi)
                    VALUES (?, ?, ?, ?)
                """, (name, link, last_update.strftime("%Y-%m-%d %H:%M:%S"),
                      numero_episodi))
                logger.info(f"TV show '{name}' added to database.")
                return True
        except sqlite3.IntegrityError:
            logger.warning(f"TV show '{name}' already exists.")
            return False

    # ==================== MOVIES OPERATIONS ====================

    def get_all_movies(self) -> List[Dict[str, Any]]:
        """Get all movies from database."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT name, link, last_update, scaricato
                FROM movies ORDER BY name
            """)
            return [dict(row) for row in cursor.fetchall()]

    def add_movie(self, name: str, link: str, last_update: datetime) -> bool:
        """Add new movie to database."""
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO movies (name, link, last_update)
                    VALUES (?, ?, ?)
                """, (name, link, last_update.strftime("%Y-%m-%d %H:%M:%S")))
                logger.info(f"Movie '{name}' added to database.")
                return True
        except sqlite3.IntegrityError:
            logger.warning(f"Movie '{name}' already exists.")
            return False

    # ==================== MIGRATION ====================

    def migrate_from_json(self, json_path: str = "config.json") -> Tuple[bool, str]:
        """
        Migrate data from config.json to SQLite database.

        Returns:
            Tuple of (success, message)
        """
        if not os.path.exists(json_path):
            return (False, f"File {json_path} not found.")

        try:
            with open(json_path, "r") as f:
                config = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            return (False, f"Error reading {json_path}: {e}")

        migrated = {"anime": 0, "tv": 0, "movies": 0}

        # Migrate anime
        for anime in config.get("anime", []):
            try:
                last_update = datetime.strptime(
                    anime.get("last_update", "2000-01-01 00:00:00"),
                    "%Y-%m-%d %H:%M:%S"
                )
            except ValueError:
                last_update = datetime.now()

            with self._get_connection() as conn:
                try:
                    conn.execute("""
                        INSERT OR IGNORE INTO anime
                        (name, link, last_update, episodi_scaricati, numero_episodi)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        anime.get("name"),
                        anime.get("link"),
                        last_update.strftime("%Y-%m-%d %H:%M:%S"),
                        anime.get("episodi_scaricati", 0),
                        anime.get("numero_episodi", 0)
                    ))
                    if conn.total_changes:
                        migrated["anime"] += 1
                except Exception as e:
                    logger.warning(f"Failed to migrate anime {anime.get('name')}: {e}")

        # Migrate TV shows
        for tv in config.get("tv", []):
            try:
                last_update = datetime.strptime(
                    tv.get("last_update", "2000-01-01 00:00:00"),
                    "%Y-%m-%d %H:%M:%S"
                )
            except ValueError:
                last_update = datetime.now()

            with self._get_connection() as conn:
                try:
                    conn.execute("""
                        INSERT OR IGNORE INTO tv
                        (name, link, last_update, episodi_scaricati, numero_episodi)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        tv.get("name"),
                        tv.get("link"),
                        last_update.strftime("%Y-%m-%d %H:%M:%S"),
                        tv.get("episodi_scaricati", 0),
                        tv.get("numero_episodi", 0)
                    ))
                    if conn.total_changes:
                        migrated["tv"] += 1
                except Exception as e:
                    logger.warning(f"Failed to migrate TV {tv.get('name')}: {e}")

        # Migrate movies
        for movie in config.get("movies", []):
            try:
                last_update = datetime.strptime(
                    movie.get("last_update", "2000-01-01 00:00:00"),
                    "%Y-%m-%d %H:%M:%S"
                )
            except ValueError:
                last_update = datetime.now()

            with self._get_connection() as conn:
                try:
                    conn.execute("""
                        INSERT OR IGNORE INTO movies
                        (name, link, last_update, scaricato)
                        VALUES (?, ?, ?, ?)
                    """, (
                        movie.get("name"),
                        movie.get("link"),
                        last_update.strftime("%Y-%m-%d %H:%M:%S"),
                        1 if movie.get("scaricato") else 0
                    ))
                    if conn.total_changes:
                        migrated["movies"] += 1
                except Exception as e:
                    logger.warning(f"Failed to migrate movie {movie.get('name')}: {e}")

        # Rename old config.json
        if any(migrated.values()):
            backup_path = f"{json_path}.migrated_{int(datetime.now().timestamp())}"
            os.rename(json_path, backup_path)
            logger.info(f"Old config backed up to {backup_path}")

        msg = f"Migration complete: {migrated['anime']} anime, {migrated['tv']} TV, {migrated['movies']} movies"
        logger.info(msg)
        return (True, msg)
