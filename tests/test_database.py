"""
Tests for database.py - SQLite database operations for YUNA-System.

This module tests:
    - Database initialization and schema creation
    - CRUD operations for anime, TV shows, and movies
    - Migration from JSON configuration files
    - Duplicate handling and constraints
    - Concurrent database access
"""

import os
import sys
import sqlite3
import json
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Database, DEFAULT_DB_PATH


class TestDatabaseInitialization:
    """Tests for database initialization and schema creation."""

    def test_database_creates_file(self, temp_db):
        """Verify that Database.__init__ creates the database file."""
        db = Database(temp_db)
        assert os.path.exists(temp_db), "Database file should be created"

    def test_database_schema_tables_exist(self, temp_db):
        """Verify that all required tables are created during initialization."""
        db = Database(temp_db)

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # Check for required tables
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row[0] for row in cursor.fetchall()]

        assert "anime" in tables, "anime table should exist"
        assert "tv" in tables, "tv table should exist"
        assert "movies" in tables, "movies table should exist"

        conn.close()

    def test_database_schema_columns_anime(self, temp_db):
        """Verify that the anime table has correct columns."""
        db = Database(temp_db)

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(anime)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}

        expected_columns = {
            "id": "INTEGER",
            "name": "TEXT",
            "link": "TEXT",
            "last_update": "TIMESTAMP",
            "episodi_scaricati": "INTEGER",
            "numero_episodi": "INTEGER",
            "created_at": "TIMESTAMP",
        }

        for col_name, col_type in expected_columns.items():
            assert col_name in columns, f"Column {col_name} should exist"
            assert columns[col_name] == col_type, f"Column {col_name} should be {col_type}"

        conn.close()

    def test_database_schema_indexes_exist(self, temp_db):
        """Verify that performance indexes are created."""
        db = Database(temp_db)

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' ORDER BY name"
        )
        indexes = [row[0] for row in cursor.fetchall()]

        assert "idx_anime_name" in indexes, "Index on anime.name should exist"
        assert "idx_tv_name" in indexes, "Index on tv.name should exist"
        assert "idx_movies_name" in indexes, "Index on movies.name should exist"

        conn.close()

    def test_database_default_path(self):
        """Verify that the default database path constant is set correctly."""
        assert DEFAULT_DB_PATH == "yuna.db", "Default path should be yuna.db"


class TestAnimeCRUD:
    """Tests for anime CRUD operations."""

    def test_add_anime_success(self, temp_db, sample_anime_data):
        """Verify that adding a new anime works correctly."""
        db = Database(temp_db)
        last_update = datetime.strptime(
            sample_anime_data["last_update"], "%Y-%m-%d %H:%M:%S"
        )

        result = db.add_anime(
            name=sample_anime_data["name"],
            link=sample_anime_data["link"],
            last_update=last_update,
            numero_episodi=sample_anime_data["numero_episodi"],
        )

        assert result is True, "add_anime should return True on success"

    def test_add_anime_duplicate_fails(self, temp_db, sample_anime_data):
        """Verify that adding a duplicate anime fails gracefully."""
        db = Database(temp_db)
        last_update = datetime.strptime(
            sample_anime_data["last_update"], "%Y-%m-%d %H:%M:%S"
        )

        # First add should succeed
        db.add_anime(
            name=sample_anime_data["name"],
            link=sample_anime_data["link"],
            last_update=last_update,
            numero_episodi=sample_anime_data["numero_episodi"],
        )

        # Second add should fail due to UNIQUE constraint
        result = db.add_anime(
            name=sample_anime_data["name"],
            link="/different/link",
            last_update=last_update,
            numero_episodi=sample_anime_data["numero_episodi"],
        )

        assert result is False, "Adding duplicate anime should return False"

    def test_get_all_anime_empty(self, temp_db):
        """Verify that get_all_anime returns empty list for new database."""
        db = Database(temp_db)
        anime_list = db.get_all_anime()

        assert anime_list == [], "Empty database should return empty list"

    def test_get_all_anime_with_data(self, temp_db, sample_anime_list):
        """Verify that get_all_anime returns all added anime."""
        db = Database(temp_db)

        for anime in sample_anime_list:
            last_update = datetime.strptime(
                anime["last_update"], "%Y-%m-%d %H:%M:%S"
            )
            db.add_anime(
                name=anime["name"],
                link=anime["link"],
                last_update=last_update,
                numero_episodi=anime["numero_episodi"],
            )

        anime_list = db.get_all_anime()
        assert len(anime_list) == 3, "Should return all 3 anime"

    def test_get_anime_by_name_found(self, temp_db, sample_anime_data):
        """Verify that get_anime_by_name returns correct anime."""
        db = Database(temp_db)
        last_update = datetime.strptime(
            sample_anime_data["last_update"], "%Y-%m-%d %H:%M:%S"
        )

        db.add_anime(
            name=sample_anime_data["name"],
            link=sample_anime_data["link"],
            last_update=last_update,
            numero_episodi=sample_anime_data["numero_episodi"],
        )

        anime = db.get_anime_by_name(sample_anime_data["name"])
        assert anime is not None, "Should find the anime"
        assert anime["name"] == sample_anime_data["name"]

    def test_get_anime_by_name_not_found(self, temp_db):
        """Verify that get_anime_by_name returns None for non-existent anime."""
        db = Database(temp_db)
        anime = db.get_anime_by_name("Non Existent Anime")

        assert anime is None, "Should return None for non-existent anime"

    def test_search_anime_by_name_partial_match(self, temp_db, sample_anime_data):
        """Verify that search_anime_by_name works with partial names."""
        db = Database(temp_db)
        last_update = datetime.strptime(
            sample_anime_data["last_update"], "%Y-%m-%d %H:%M:%S"
        )

        db.add_anime(
            name=sample_anime_data["name"],
            link=sample_anime_data["link"],
            last_update=last_update,
            numero_episodi=sample_anime_data["numero_episodi"],
        )

        # Search with partial name
        anime = db.search_anime_by_name("Test")
        assert anime is not None, "Should find anime with partial match"
        assert anime["name"] == sample_anime_data["name"]

    def test_search_anime_by_name_case_insensitive(self, temp_db, sample_anime_data):
        """Verify that search is case insensitive."""
        db = Database(temp_db)
        last_update = datetime.strptime(
            sample_anime_data["last_update"], "%Y-%m-%d %H:%M:%S"
        )

        db.add_anime(
            name=sample_anime_data["name"],
            link=sample_anime_data["link"],
            last_update=last_update,
            numero_episodi=sample_anime_data["numero_episodi"],
        )

        # Search with different case
        anime = db.search_anime_by_name("test anime")
        assert anime is not None, "Search should be case insensitive"

    def test_update_anime_episodes(self, temp_db, sample_anime_data):
        """Verify that updating downloaded episodes count works."""
        db = Database(temp_db)
        last_update = datetime.strptime(
            sample_anime_data["last_update"], "%Y-%m-%d %H:%M:%S"
        )

        db.add_anime(
            name=sample_anime_data["name"],
            link=sample_anime_data["link"],
            last_update=last_update,
            numero_episodi=sample_anime_data["numero_episodi"],
        )

        result = db.update_anime_episodes(sample_anime_data["name"], 10)
        assert result is True, "Update should succeed"

        anime = db.get_anime_by_name(sample_anime_data["name"])
        assert anime["episodi_scaricati"] == 10, "Episodes should be updated"

    def test_update_anime_episodes_not_found(self, temp_db):
        """Verify that updating non-existent anime returns False."""
        db = Database(temp_db)
        result = db.update_anime_episodes("Non Existent", 5)

        assert result is False, "Should return False for non-existent anime"

    def test_update_anime_total_episodes(self, temp_db, sample_anime_data):
        """Verify that updating total episodes count works."""
        db = Database(temp_db)
        last_update = datetime.strptime(
            sample_anime_data["last_update"], "%Y-%m-%d %H:%M:%S"
        )

        db.add_anime(
            name=sample_anime_data["name"],
            link=sample_anime_data["link"],
            last_update=last_update,
            numero_episodi=sample_anime_data["numero_episodi"],
        )

        result = db.update_anime_total_episodes(sample_anime_data["name"], 24)
        assert result is True, "Update should succeed"

        anime = db.get_anime_by_name(sample_anime_data["name"])
        assert anime["numero_episodi"] == 24, "Total episodes should be updated"

    def test_update_anime_last_update(self, temp_db, sample_anime_data):
        """Verify that updating last_update timestamp works."""
        db = Database(temp_db)
        last_update = datetime.strptime(
            sample_anime_data["last_update"], "%Y-%m-%d %H:%M:%S"
        )

        db.add_anime(
            name=sample_anime_data["name"],
            link=sample_anime_data["link"],
            last_update=last_update,
            numero_episodi=sample_anime_data["numero_episodi"],
        )

        new_update = datetime(2024, 6, 15, 10, 30, 0)
        result = db.update_anime_last_update(sample_anime_data["name"], new_update)
        assert result is True, "Update should succeed"

        anime = db.get_anime_by_name(sample_anime_data["name"])
        assert "2024-06-15" in anime["last_update"], "Last update should be updated"

    def test_remove_anime_success(self, temp_db, sample_anime_data):
        """Verify that removing anime works correctly."""
        db = Database(temp_db)
        last_update = datetime.strptime(
            sample_anime_data["last_update"], "%Y-%m-%d %H:%M:%S"
        )

        db.add_anime(
            name=sample_anime_data["name"],
            link=sample_anime_data["link"],
            last_update=last_update,
            numero_episodi=sample_anime_data["numero_episodi"],
        )

        result = db.remove_anime(sample_anime_data["name"])
        assert result is True, "Remove should succeed"

        anime = db.get_anime_by_name(sample_anime_data["name"])
        assert anime is None, "Anime should no longer exist"

    def test_remove_anime_not_found(self, temp_db):
        """Verify that removing non-existent anime returns False."""
        db = Database(temp_db)
        result = db.remove_anime("Non Existent Anime")

        assert result is False, "Should return False for non-existent anime"

    def test_get_anime_link(self, temp_db, sample_anime_data):
        """Verify that get_anime_link returns correct link."""
        db = Database(temp_db)
        last_update = datetime.strptime(
            sample_anime_data["last_update"], "%Y-%m-%d %H:%M:%S"
        )

        db.add_anime(
            name=sample_anime_data["name"],
            link=sample_anime_data["link"],
            last_update=last_update,
            numero_episodi=sample_anime_data["numero_episodi"],
        )

        link = db.get_anime_link("Test")  # Partial name search
        assert link == sample_anime_data["link"], "Should return correct link"

    def test_get_anime_link_not_found(self, temp_db):
        """Verify that get_anime_link returns None for non-existent anime."""
        db = Database(temp_db)
        link = db.get_anime_link("Non Existent")

        assert link is None, "Should return None for non-existent anime"


class TestTVCRUD:
    """Tests for TV show CRUD operations."""

    def test_add_tv_success(self, temp_db, sample_tv_data):
        """Verify that adding a new TV show works correctly."""
        db = Database(temp_db)
        last_update = datetime.strptime(
            sample_tv_data["last_update"], "%Y-%m-%d %H:%M:%S"
        )

        result = db.add_tv(
            name=sample_tv_data["name"],
            link=sample_tv_data["link"],
            last_update=last_update,
            numero_episodi=sample_tv_data["numero_episodi"],
        )

        assert result is True, "add_tv should return True on success"

    def test_add_tv_duplicate_fails(self, temp_db, sample_tv_data):
        """Verify that adding a duplicate TV show fails gracefully."""
        db = Database(temp_db)
        last_update = datetime.strptime(
            sample_tv_data["last_update"], "%Y-%m-%d %H:%M:%S"
        )

        db.add_tv(
            name=sample_tv_data["name"],
            link=sample_tv_data["link"],
            last_update=last_update,
            numero_episodi=sample_tv_data["numero_episodi"],
        )

        result = db.add_tv(
            name=sample_tv_data["name"],
            link="/different/link",
            last_update=last_update,
            numero_episodi=sample_tv_data["numero_episodi"],
        )

        assert result is False, "Adding duplicate TV show should return False"

    def test_get_all_tv_empty(self, temp_db):
        """Verify that get_all_tv returns empty list for new database."""
        db = Database(temp_db)
        tv_list = db.get_all_tv()

        assert tv_list == [], "Empty database should return empty list"

    def test_get_all_tv_with_data(self, temp_db, sample_tv_data):
        """Verify that get_all_tv returns all added TV shows."""
        db = Database(temp_db)
        last_update = datetime.strptime(
            sample_tv_data["last_update"], "%Y-%m-%d %H:%M:%S"
        )

        db.add_tv(
            name=sample_tv_data["name"],
            link=sample_tv_data["link"],
            last_update=last_update,
            numero_episodi=sample_tv_data["numero_episodi"],
        )

        tv_list = db.get_all_tv()
        assert len(tv_list) == 1, "Should return the added TV show"
        assert tv_list[0]["name"] == sample_tv_data["name"]


class TestMoviesCRUD:
    """Tests for movies CRUD operations."""

    def test_add_movie_success(self, temp_db, sample_movie_data):
        """Verify that adding a new movie works correctly."""
        db = Database(temp_db)
        last_update = datetime.strptime(
            sample_movie_data["last_update"], "%Y-%m-%d %H:%M:%S"
        )

        result = db.add_movie(
            name=sample_movie_data["name"],
            link=sample_movie_data["link"],
            last_update=last_update,
        )

        assert result is True, "add_movie should return True on success"

    def test_add_movie_duplicate_fails(self, temp_db, sample_movie_data):
        """Verify that adding a duplicate movie fails gracefully."""
        db = Database(temp_db)
        last_update = datetime.strptime(
            sample_movie_data["last_update"], "%Y-%m-%d %H:%M:%S"
        )

        db.add_movie(
            name=sample_movie_data["name"],
            link=sample_movie_data["link"],
            last_update=last_update,
        )

        result = db.add_movie(
            name=sample_movie_data["name"],
            link="/different/link",
            last_update=last_update,
        )

        assert result is False, "Adding duplicate movie should return False"

    def test_get_all_movies_empty(self, temp_db):
        """Verify that get_all_movies returns empty list for new database."""
        db = Database(temp_db)
        movies_list = db.get_all_movies()

        assert movies_list == [], "Empty database should return empty list"

    def test_get_all_movies_with_data(self, temp_db, sample_movie_data):
        """Verify that get_all_movies returns all added movies."""
        db = Database(temp_db)
        last_update = datetime.strptime(
            sample_movie_data["last_update"], "%Y-%m-%d %H:%M:%S"
        )

        db.add_movie(
            name=sample_movie_data["name"],
            link=sample_movie_data["link"],
            last_update=last_update,
        )

        movies_list = db.get_all_movies()
        assert len(movies_list) == 1, "Should return the added movie"
        assert movies_list[0]["name"] == sample_movie_data["name"]


class TestMigrationFromJSON:
    """Tests for migrating data from config.json to SQLite."""

    def test_migrate_from_json_success(self, temp_db, sample_config_json):
        """Verify that migration from JSON works correctly."""
        db = Database(temp_db)
        success, message = db.migrate_from_json(sample_config_json)

        assert success is True, "Migration should succeed"
        assert "2 anime" in message, "Should report migrated anime count"
        assert "1 TV" in message, "Should report migrated TV count"
        assert "1 movies" in message, "Should report migrated movies count"

    def test_migrate_from_json_creates_backup(self, temp_db, sample_config_json):
        """Verify that migration creates a backup of the original JSON."""
        db = Database(temp_db)
        db.migrate_from_json(sample_config_json)

        # Check that original file is renamed
        assert not os.path.exists(sample_config_json), "Original file should be renamed"

        # Check that backup exists
        backup_files = [
            f for f in os.listdir(os.path.dirname(sample_config_json))
            if "migrated" in f
        ]
        assert len(backup_files) > 0, "Backup file should exist"

    def test_migrate_from_json_file_not_found(self, temp_db):
        """Verify that migration handles missing JSON file."""
        db = Database(temp_db)
        success, message = db.migrate_from_json("/nonexistent/path/config.json")

        assert success is False, "Migration should fail for missing file"
        assert "not found" in message, "Message should indicate file not found"

    def test_migrate_from_json_invalid_json(self, temp_db, tmp_path):
        """Verify that migration handles invalid JSON gracefully."""
        # Create invalid JSON file
        invalid_json_path = tmp_path / "invalid.json"
        with open(invalid_json_path, "w") as f:
            f.write("not valid json {{{")

        db = Database(temp_db)
        success, message = db.migrate_from_json(str(invalid_json_path))

        assert success is False, "Migration should fail for invalid JSON"
        assert "Error reading" in message, "Message should indicate read error"

    def test_migrate_anime_data_correctness(self, temp_db, sample_config_json):
        """Verify that migrated anime data is correct."""
        db = Database(temp_db)
        db.migrate_from_json(sample_config_json)

        anime_list = db.get_all_anime()
        assert len(anime_list) == 2, "Should migrate 2 anime"

        anime_names = [a["name"] for a in anime_list]
        assert "Migration Anime 1" in anime_names
        assert "Migration Anime 2" in anime_names

    def test_migrate_handles_missing_fields(self, temp_db, tmp_path):
        """Verify that migration handles JSON with missing optional fields."""
        config_data = {
            "anime": [
                {
                    "name": "Minimal Anime",
                    "link": "/play/minimal.12345",
                    # Missing last_update, episodi_scaricati, numero_episodi
                }
            ],
            "tv": [],
            "movies": [],
        }

        config_path = tmp_path / "minimal_config.json"
        with open(config_path, "w") as f:
            json.dump(config_data, f)

        db = Database(temp_db)
        success, message = db.migrate_from_json(str(config_path))

        # Should succeed even with missing fields
        assert success is True, "Migration should succeed with minimal data"


class TestDuplicateHandling:
    """Tests for handling duplicate entries."""

    def test_unique_constraint_on_anime_name(self, temp_db):
        """Verify that anime name UNIQUE constraint is enforced."""
        db = Database(temp_db)
        now = datetime.now()

        db.add_anime("Unique Anime", "/link1", now, 12)
        result = db.add_anime("Unique Anime", "/link2", now, 24)

        assert result is False, "Duplicate name should be rejected"

        # Verify only one entry exists
        anime_list = db.get_all_anime()
        assert len(anime_list) == 1

    def test_unique_constraint_on_tv_name(self, temp_db):
        """Verify that TV show name UNIQUE constraint is enforced."""
        db = Database(temp_db)
        now = datetime.now()

        db.add_tv("Unique TV", "/link1", now, 10)
        result = db.add_tv("Unique TV", "/link2", now, 20)

        assert result is False, "Duplicate TV name should be rejected"

    def test_unique_constraint_on_movie_name(self, temp_db):
        """Verify that movie name UNIQUE constraint is enforced."""
        db = Database(temp_db)
        now = datetime.now()

        db.add_movie("Unique Movie", "/link1", now)
        result = db.add_movie("Unique Movie", "/link2", now)

        assert result is False, "Duplicate movie name should be rejected"


class TestConcurrentAccess:
    """Tests for concurrent database access."""

    def test_concurrent_reads(self, temp_db, sample_anime_list):
        """Verify that concurrent read operations work correctly."""
        db = Database(temp_db)

        # Add sample data
        for anime in sample_anime_list:
            last_update = datetime.strptime(
                anime["last_update"], "%Y-%m-%d %H:%M:%S"
            )
            db.add_anime(
                name=anime["name"],
                link=anime["link"],
                last_update=last_update,
                numero_episodi=anime["numero_episodi"],
            )

        results = []

        def read_anime():
            local_db = Database(temp_db)
            anime_list = local_db.get_all_anime()
            results.append(len(anime_list))

        # Run concurrent reads
        threads = [threading.Thread(target=read_anime) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All reads should return the same result
        assert all(r == 3 for r in results), "All concurrent reads should succeed"

    def test_concurrent_writes(self, temp_db):
        """Verify that concurrent write operations are handled safely."""
        db = Database(temp_db)
        results = []

        def add_anime(name):
            try:
                local_db = Database(temp_db)
                result = local_db.add_anime(
                    name=name,
                    link=f"/play/{name.replace(' ', '-').lower()}",
                    last_update=datetime.now(),
                    numero_episodi=12,
                )
                results.append((name, result))
            except Exception as e:
                results.append((name, f"Error: {e}"))

        # Run concurrent writes with unique names
        with ThreadPoolExecutor(max_workers=5) as executor:
            for i in range(10):
                executor.submit(add_anime, f"Concurrent Anime {i}")

        # All writes should succeed
        successful = [r for r in results if r[1] is True]
        assert len(successful) == 10, "All concurrent writes with unique names should succeed"

    def test_transaction_rollback_on_error(self, temp_db):
        """Verify that transactions are rolled back on error."""
        db = Database(temp_db)

        # Add initial data
        db.add_anime("Initial Anime", "/link", datetime.now(), 12)

        # Try to add duplicate (should fail but not corrupt database)
        db.add_anime("Initial Anime", "/different-link", datetime.now(), 24)

        # Database should still be usable
        anime_list = db.get_all_anime()
        assert len(anime_list) == 1, "Database should remain consistent after error"
        assert anime_list[0]["name"] == "Initial Anime"


class TestConnectionManagement:
    """Tests for database connection management."""

    def test_connection_context_manager(self, temp_db):
        """Verify that the connection context manager works correctly."""
        db = Database(temp_db)

        # The context manager should handle opening/closing connections
        db.add_anime("Test", "/link", datetime.now(), 12)
        anime = db.get_anime_by_name("Test")

        assert anime is not None, "Connection should work through context manager"

    def test_connection_auto_commit(self, temp_db):
        """Verify that changes are committed automatically."""
        db = Database(temp_db)
        db.add_anime("AutoCommit Test", "/link", datetime.now(), 12)

        # Create new database instance to verify persistence
        db2 = Database(temp_db)
        anime = db2.get_anime_by_name("AutoCommit Test")

        assert anime is not None, "Changes should be persisted automatically"

    def test_connection_rollback_on_exception(self, temp_db):
        """Verify that exceptions trigger rollback."""
        db = Database(temp_db)

        # Add initial anime
        db.add_anime("Rollback Test", "/link", datetime.now(), 12)

        # The UNIQUE constraint violation should be handled gracefully
        result = db.add_anime("Rollback Test", "/link2", datetime.now(), 24)
        assert result is False

        # Database should still be functional
        anime_list = db.get_all_anime()
        assert len(anime_list) == 1
