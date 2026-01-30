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

# Default database path - uses environment variable or fallback
DEFAULT_DB_PATH = os.getenv("DATABASE_PATH", "/data/yuna.db")


class Database:
    """SQLite database handler with CRUD operations."""

    def __init__(self, db_path: str = None):
        # Use provided path, or environment variable, or default
        if db_path is None:
            db_path = DEFAULT_DB_PATH
        self.db_path = db_path
        self._init_database()

    # Migration definitions - add new migrations at the end with incremental IDs
    MIGRATIONS = [
        {
            "id": 1,
            "description": "Initial schema with anime, tv, movies tables",
            "sql": """
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
            """
        },
        {
            "id": 2,
            "description": "Add StreamingCommunity fields to tv and movies tables",
            "sql": """
                -- Add provider field to distinguish between sources (animeworld, streamingcommunity)
                ALTER TABLE tv ADD COLUMN provider TEXT DEFAULT 'streamingcommunity';
                ALTER TABLE movies ADD COLUMN provider TEXT DEFAULT 'streamingcommunity';
                ALTER TABLE anime ADD COLUMN provider TEXT DEFAULT 'animeworld';

                -- Add StreamingCommunity specific fields
                ALTER TABLE tv ADD COLUMN slug TEXT;
                ALTER TABLE tv ADD COLUMN media_id INTEGER;
                ALTER TABLE tv ADD COLUMN provider_language TEXT DEFAULT 'it';
                ALTER TABLE tv ADD COLUMN year TEXT;

                ALTER TABLE movies ADD COLUMN slug TEXT;
                ALTER TABLE movies ADD COLUMN media_id INTEGER;
                ALTER TABLE movies ADD COLUMN provider_language TEXT DEFAULT 'it';
                ALTER TABLE movies ADD COLUMN year TEXT;
            """
        },
        {
            "id": 3,
            "description": "Add season tracking for TV series",
            "sql": """
                -- Track which seasons/episodes have been downloaded for series
                ALTER TABLE tv ADD COLUMN seasons_data TEXT;
                -- JSON format: {"1": {"total": 10, "downloaded": [1,2,3]}, "2": {...}}
            """
        },
    ]

    def _init_database(self):
        """Initialize database with schema using migrations."""
        # Ensure the directory exists
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            logger.info(f"Created database directory: {db_dir}")

        # Create migrations table if not exists
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS migrations (
                    id INTEGER PRIMARY KEY,
                    description TEXT,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

        # Run pending migrations
        self._run_migrations()
        logger.info(f"Database initialized: {self.db_path}")

    def _get_applied_migrations(self) -> set:
        """Get set of already applied migration IDs."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT id FROM migrations")
            return {row[0] for row in cursor.fetchall()}

    def _run_migrations(self):
        """Run all pending migrations."""
        applied = self._get_applied_migrations()

        for migration in self.MIGRATIONS:
            if migration["id"] in applied:
                continue

            logger.info(f"Running migration {migration['id']}: {migration['description']}")

            try:
                with self._get_connection() as conn:
                    # Remove SQL comments and split by statements
                    sql_lines = []
                    for line in migration["sql"].split("\n"):
                        line = line.strip()
                        # Skip empty lines and comment-only lines
                        if line and not line.startswith("--"):
                            sql_lines.append(line)

                    # Join and split by semicolon
                    full_sql = " ".join(sql_lines)
                    for statement in full_sql.split(";"):
                        statement = statement.strip()
                        if statement:
                            try:
                                conn.execute(statement)
                            except sqlite3.OperationalError as e:
                                # Ignore "duplicate column" errors for idempotency
                                if "duplicate column name" in str(e).lower():
                                    logger.debug(f"Column already exists, skipping: {e}")
                                else:
                                    raise

                    # Mark migration as applied
                    conn.execute(
                        "INSERT INTO migrations (id, description) VALUES (?, ?)",
                        (migration["id"], migration["description"])
                    )
                    logger.info(f"Migration {migration['id']} completed successfully")

            except Exception as e:
                logger.error(f"Migration {migration['id']} failed: {e}")
                raise

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
                SELECT name, link, last_update, episodi_scaricati, numero_episodi,
                       provider, slug, media_id, provider_language, year, seasons_data
                FROM tv ORDER BY name
            """)
            return [dict(row) for row in cursor.fetchall()]

    def get_tv_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get TV show by exact name."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM tv WHERE name = ?", (name,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def search_tv_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Search TV show by partial name (case insensitive)."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM tv WHERE LOWER(name) LIKE LOWER(?)",
                (f"%{name}%",)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def add_tv(self, name: str, link: str, last_update: datetime,
               numero_episodi: int, slug: str = None, media_id: int = None,
               provider_language: str = "it", year: str = None,
               provider: str = "streamingcommunity") -> bool:
        """Add new TV show to database."""
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO tv (name, link, last_update, numero_episodi,
                                   provider, slug, media_id, provider_language, year)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (name, link, last_update.strftime("%Y-%m-%d %H:%M:%S"),
                      numero_episodi, provider, slug, media_id, provider_language, year))
                logger.info(f"TV show '{name}' added to database.")
                return True
        except sqlite3.IntegrityError:
            logger.warning(f"TV show '{name}' already exists.")
            return False

    def update_tv_episodes(self, name: str, episodi_scaricati: int) -> bool:
        """Update downloaded episodes count for TV show."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                UPDATE tv SET episodi_scaricati = ?
                WHERE name = ?
            """, (episodi_scaricati, name))
            if cursor.rowcount > 0:
                logger.info(f"Updated episodes for TV '{name}': {episodi_scaricati}")
                return True
            logger.warning(f"TV show '{name}' not found.")
            return False

    def update_tv_total_episodes(self, name: str, numero_episodi: int) -> bool:
        """Update total episodes count for TV show."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                UPDATE tv SET numero_episodi = ?
                WHERE name = ?
            """, (numero_episodi, name))
            return cursor.rowcount > 0

    def update_tv_last_update(self, name: str, last_update: datetime) -> bool:
        """Update last update timestamp for TV show."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                UPDATE tv SET last_update = ?
                WHERE name = ?
            """, (last_update.strftime("%Y-%m-%d %H:%M:%S"), name))
            return cursor.rowcount > 0

    def update_tv_seasons_data(self, name: str, seasons_data: str) -> bool:
        """Update seasons data JSON for TV show."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                UPDATE tv SET seasons_data = ?
                WHERE name = ?
            """, (seasons_data, name))
            return cursor.rowcount > 0

    def remove_tv(self, name: str) -> bool:
        """Remove TV show from database."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM tv WHERE name = ?", (name,)
            )
            if cursor.rowcount > 0:
                logger.info(f"TV show '{name}' removed from database.")
                return True
            logger.warning(f"TV show '{name}' not found.")
            return False

    def get_tv_link(self, name: str) -> Optional[str]:
        """Get TV show link by name (partial match)."""
        tv = self.search_tv_by_name(name)
        return tv["link"] if tv else None

    # ==================== MOVIES OPERATIONS ====================

    def get_all_movies(self) -> List[Dict[str, Any]]:
        """Get all movies from database."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT name, link, last_update, scaricato,
                       provider, slug, media_id, provider_language, year
                FROM movies ORDER BY name
            """)
            return [dict(row) for row in cursor.fetchall()]

    def get_movie_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get movie by exact name."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM movies WHERE name = ?", (name,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def search_movie_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Search movie by partial name (case insensitive)."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM movies WHERE LOWER(name) LIKE LOWER(?)",
                (f"%{name}%",)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def add_movie(self, name: str, link: str, last_update: datetime,
                  slug: str = None, media_id: int = None,
                  provider_language: str = "it", year: str = None,
                  provider: str = "streamingcommunity") -> bool:
        """Add new movie to database."""
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO movies (name, link, last_update, provider,
                                       slug, media_id, provider_language, year)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (name, link, last_update.strftime("%Y-%m-%d %H:%M:%S"),
                      provider, slug, media_id, provider_language, year))
                logger.info(f"Movie '{name}' added to database.")
                return True
        except sqlite3.IntegrityError:
            logger.warning(f"Movie '{name}' already exists.")
            return False

    def update_movie_downloaded(self, name: str, scaricato: int = 1) -> bool:
        """Mark movie as downloaded."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                UPDATE movies SET scaricato = ?
                WHERE name = ?
            """, (scaricato, name))
            if cursor.rowcount > 0:
                logger.info(f"Movie '{name}' marked as downloaded.")
                return True
            logger.warning(f"Movie '{name}' not found.")
            return False

    def update_movie_last_update(self, name: str, last_update: datetime) -> bool:
        """Update last update timestamp for movie."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                UPDATE movies SET last_update = ?
                WHERE name = ?
            """, (last_update.strftime("%Y-%m-%d %H:%M:%S"), name))
            return cursor.rowcount > 0

    def remove_movie(self, name: str) -> bool:
        """Remove movie from database."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM movies WHERE name = ?", (name,)
            )
            if cursor.rowcount > 0:
                logger.info(f"Movie '{name}' removed from database.")
                return True
            logger.warning(f"Movie '{name}' not found.")
            return False

    def get_movie_link(self, name: str) -> Optional[str]:
        """Get movie link by name (partial match)."""
        movie = self.search_movie_by_name(name)
        return movie["link"] if movie else None

    def get_pending_movies(self) -> List[Dict[str, Any]]:
        """Get all movies not yet downloaded."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT name, link, last_update, scaricato,
                       provider, slug, media_id, provider_language, year
                FROM movies WHERE scaricato = 0 ORDER BY name
            """)
            return [dict(row) for row in cursor.fetchall()]

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
