from dotenv import load_dotenv
import os
import logging
import shutil
from colorama import Fore, Style, init
# Importa la classe ColoredFormatter dal file color_utils
from color_utils import ColoredFormatter
from colorama import init
import re
from urllib.parse import urlparse
from datetime import datetime
import httpx

from database import Database

init(autoreset=True)

# Configura il logging con il custom formatter
formatter = ColoredFormatter(
    # Make the time blue
    fmt="\033[34m%(asctime)s\033[0m - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"  # Keep the date format
)
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(handler)

# Cache per l'URL di AnimeWorld
_animeworld_url_cache = None


def get_animeworld_url():
    """
    Recupera automaticamente l'URL corrente di AnimeWorld seguendo i redirect.
    Usa una cache per evitare richieste multiple.
    """
    global _animeworld_url_cache

    if _animeworld_url_cache is not None:
        return _animeworld_url_cache

    # Domini noti che reindirizzano all'URL corrente
    fallback_domains = [
        'https://www.animeworld.tv/',
        'https://animeworld.tv/',
        'https://www.animeworld.so/',
    ]

    for domain in fallback_domains:
        try:
            response = httpx.get(domain, follow_redirects=True, timeout=10)
            # Estrae il base URL (schema + host)
            final_url = str(response.url)
            parsed = urlparse(final_url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            _animeworld_url_cache = base_url
            logger.info(f"URL AnimeWorld recuperato automaticamente: {base_url}")
            return base_url
        except Exception as e:
            logger.warning(f"Impossibile raggiungere {domain}: {e}")
            continue

    # Fallback al default se tutti i tentativi falliscono
    default_url = "https://www.animeworld.ac"
    logger.warning(f"Impossibile recuperare URL AnimeWorld, uso default: {default_url}")
    _animeworld_url_cache = default_url
    return default_url


class Airi:
    def __init__(self, db_path: str = None):
        load_dotenv()  # Carica il file .env nella environment

        # Download folders - supporta cartelle separate per tipo di media
        self.anime_folder = os.getenv("ANIME_FOLDER", "/downloads/anime")
        self.series_folder = os.getenv("SERIES_FOLDER", "/downloads/series")
        self.movies_folder = os.getenv("MOVIES_FOLDER", "/downloads/movies")

        # Legacy: DESTINATION_FOLDER per retrocompatibilità (usa anime_folder come default)
        self.destination_folder = os.getenv("DESTINATION_FOLDER", self.anime_folder)
        self.telegram_token = os.getenv("TELEGRAM_TOKEN")
        # Gestione errore per TELEGRAM_CHAT_ID non valido
        telegram_chat_id_str = os.getenv("TELEGRAM_CHAT_ID")
        if not telegram_chat_id_str:
            raise ValueError("TELEGRAM_CHAT_ID non configurato nelle variabili d'ambiente.")
        try:
            self.TELEGRAM_CHAT_ID = int(telegram_chat_id_str)
        except ValueError:
            raise ValueError(f"TELEGRAM_CHAT_ID deve essere un numero intero, ricevuto: {telegram_chat_id_str}")
        # Default a 60 secondi se non impostato
        self.UPDATE_TIME = int(os.getenv("UPDATE_TIME", 60))
        # Recupera automaticamente l'URL di AnimeWorld
        self.BASE_URL = get_animeworld_url()
        self.BASE_URL_SC = os.getenv(
            "BASE_URL_SC", "https://streamingunity.shop")
        self.config_path = "config.json"
        self.tv_config_path = "tv_config.json"

        # Initialize database and auto-migrate from JSON if exists
        # db_path=None means use DATABASE_PATH env var or default /data/yuna.db
        self.db = Database(db_path)
        self._auto_migrate_from_json()

        # Log database location for debugging
        logger.info(f"Database path: {self.db.db_path}")

    def _auto_migrate_from_json(self):
        """
        Automatically migrate from config.json to SQLite if the JSON file exists.
        """
        if os.path.exists(self.config_path):
            logger.info(f"Found {self.config_path}, migrating to SQLite database...")
            success, message = self.db.migrate_from_json(self.config_path)
            if success:
                logger.info(f"Migration completed: {message}")
            else:
                logger.warning(f"Migration failed: {message}")

    def _format_last_update(self, last_update) -> str:
        """
        Convert last_update to string format.
        Handles both datetime objects and strings.
        """
        if isinstance(last_update, datetime):
            return last_update.strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(last_update, str):
            return last_update
        else:
            return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _parse_last_update(self, last_update) -> datetime:
        """
        Convert last_update to datetime object.
        Handles both datetime objects and strings.
        """
        if isinstance(last_update, datetime):
            return last_update
        elif isinstance(last_update, str):
            try:
                return datetime.strptime(last_update, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return datetime.now()
        else:
            return datetime.now()

    def get_destination_folder(self):
        """
        Restituisce la cartella di destinazione per il download (legacy/anime).
        """
        if not self.destination_folder:
            raise ValueError(
                "La cartella di destinazione non è impostata nell'ambiente.")
        return self.destination_folder

    def get_anime_folder(self):
        """
        Restituisce la cartella di destinazione per gli anime.
        """
        return self.anime_folder

    def get_series_folder(self):
        """
        Restituisce la cartella di destinazione per le serie TV.
        """
        return self.series_folder

    def get_movies_folder(self):
        """
        Restituisce la cartella di destinazione per i film.
        """
        return self.movies_folder

    def load_or_create_config(self):
        """
        Legacy method for backward compatibility.
        Returns a dict-like structure from the database.
        """
        return {
            "anime": self.db.get_all_anime(),
            "tv": self.db.get_all_tv(),
            "movies": self.db.get_all_movies()
        }

    def get_anime(self):
        """
        Ritorna la lista degli anime presenti nel database.
        """
        return self.db.get_all_anime()

    def add_anime(self, name, link, last_update, numero_episodi):
        """
        Aggiunge un nuovo anime al database se non esiste già un anime con lo stesso link.
        """
        # Rimuove il base URL, mantiene solo il path (es: /play/nome-anime.xyz)
        parsed_link = urlparse(link).path

        # Convert last_update to datetime if it's a string
        last_update_dt = self._parse_last_update(last_update)

        # Check if anime with same link already exists
        existing_anime = self.db.get_all_anime()
        for anime in existing_anime:
            if anime.get("link") == parsed_link:
                logger.warning(
                    f"L'anime con il link '{parsed_link}' esiste già. Aggiunta saltata.")
                return

        # Add to database
        success = self.db.add_anime(name, parsed_link, last_update_dt, numero_episodi)
        if success:
            logger.info(f"Anime '{name}' aggiunto alla configurazione.")
        return

    def update_downloaded_episodes(self, name, episodi_scaricati: int):
        """
        Aggiorna il numero di episodi scaricati dell'anime nel database.
        """
        success = self.db.update_anime_episodes(name, episodi_scaricati)
        if success:
            logger.info(
                f"Numero di episodi scaricati aggiornato per l'anime '{name}'.")
        else:
            logger.warning(
                f"L'anime '{name}' non trovato nella configurazione. Nessun aggiornamento effettuato.")

    def update_episodes_number(self, name, numero_episodi):
        """
        Aggiorna il numero totale di episodi dell'anime nel database.
        """
        success = self.db.update_anime_total_episodes(name, numero_episodi)
        if success:
            logger.info(
                f"Numero episodi totale aggiornato per l'anime '{name}'.")
        else:
            logger.warning(
                f"L'anime '{name}' non trovato nella configurazione. Nessun aggiornamento effettuato.")

    def update_last_update(self, name, last_update):
        """
        Aggiorna la data di last_update dell'anime nel database.
        """
        # Convert last_update to datetime if it's a string
        last_update_dt = self._parse_last_update(last_update)

        success = self.db.update_anime_last_update(name, last_update_dt)
        if success:
            logger.info(f"Last update aggiornato per l'anime '{name}'.")
        else:
            logger.warning(
                f"L'anime '{name}' non trovato nella configurazione. Nessun aggiornamento effettuato.")

    def get_anime_link(self, anime_name):
        """
        Restituisce il link dell'anime in base al nome (anche parziale) usando una regex.
        La ricerca è insensibile al maiuscolo/minuscolo.
        """
        # Pulisci il nome dell'anime per evitare errori con spazi e caratteri speciali
        # Normalizza il nome dell'anime in minuscolo
        anime_name = anime_name.strip().lower()
        logger.debug(f"Nome anime normalizzato per la ricerca: '{anime_name}'")

        # Use database search
        anime = self.db.search_anime_by_name(anime_name)
        if anime:
            link = anime.get("link", "Link non disponibile.")
            logger.debug(f"Match trovato. Anime: '{anime.get('name')}', Link: '{link}'")
            return link

        # Se non viene trovato alcun match, restituisci un messaggio di errore
        logger.debug(f"Nessun match trovato per anime_name: '{anime_name}'")
        return "Anime non trovato."

    def invalidate_config(self):
        """
        Legacy method for backward compatibility.
        No longer needed since SQLite handles data persistence.
        """
        logger.debug("Config invalidation not needed with SQLite database")

    def get_tv(self):
        """
        Ritorna la lista delle serie TV presenti nel database.
        """
        return self.db.get_all_tv()

    def add_tv(self, name, link, last_update, numero_episodi,
               slug=None, media_id=None, provider_language="it",
               year=None, provider="streamingcommunity"):
        """
        Aggiunge una nuova serie TV al database.
        Supporta sia link completi che path relativi.
        """
        # Se il link è un URL completo, estrai solo il path
        if link.startswith("http"):
            parsed_link = urlparse(link).path
        else:
            parsed_link = link

        # Convert last_update to datetime if it's a string
        last_update_dt = self._parse_last_update(last_update)

        # Check if TV show with same name already exists
        existing_tv = self.db.get_tv_by_name(name)
        if existing_tv:
            logger.warning(f"La serie TV '{name}' esiste già. Aggiunta saltata.")
            return False

        success = self.db.add_tv(
            name, parsed_link, last_update_dt, numero_episodi,
            slug=slug, media_id=media_id, provider_language=provider_language,
            year=year, provider=provider
        )
        if success:
            logger.info(f"Serie TV '{name}' aggiunta alla configurazione.")
        return success

    def update_tv_episodes(self, name, episodi_scaricati: int):
        """
        Aggiorna il numero di episodi scaricati della serie TV nel database.
        """
        success = self.db.update_tv_episodes(name, episodi_scaricati)
        if success:
            logger.info(f"Episodi scaricati aggiornati per la serie TV '{name}'.")
        return success

    def update_tv_total_episodes(self, name, numero_episodi: int):
        """
        Aggiorna il numero totale di episodi della serie TV nel database.
        """
        return self.db.update_tv_total_episodes(name, numero_episodi)

    def update_tv_last_update(self, name, last_update):
        """
        Aggiorna la data di last_update della serie TV nel database.
        """
        last_update_dt = self._parse_last_update(last_update)
        return self.db.update_tv_last_update(name, last_update_dt)

    def update_tv_seasons_data(self, name, seasons_data: dict):
        """
        Aggiorna i dati delle stagioni della serie TV (JSON).
        """
        import json
        return self.db.update_tv_seasons_data(name, json.dumps(seasons_data))

    def get_tv_link(self, tv_name):
        """
        Restituisce il link della serie TV in base al nome.
        """
        tv_name = tv_name.strip().lower()
        tv = self.db.search_tv_by_name(tv_name)
        if tv:
            return tv.get("link", "Link non disponibile.")
        return "Serie TV non trovata."

    def remove_tv(self, tv_name: str) -> tuple:
        """
        Rimuove una serie TV dal database e cancella la sua cartella dal disco.
        """
        tv = self.db.get_tv_by_name(tv_name)
        if tv is None:
            logger.warning(f"Serie TV '{tv_name}' non trovata nella configurazione.")
            return (False, f"Serie TV '{tv_name}' non trovata.")

        success = self.db.remove_tv(tv_name)
        if not success:
            logger.error(f"Errore nella rimozione della serie TV '{tv_name}' dal database.")
            return (False, "Errore nella rimozione dal database.")

        logger.info(f"Serie TV '{tv_name}' rimossa dalla configurazione.")

        # Cancella la cartella dal disco
        tv_folder = os.path.join(self.series_folder, tv_name)
        folder_deleted = False

        if os.path.exists(tv_folder):
            try:
                shutil.rmtree(tv_folder)
                logger.info(f"Cartella '{tv_folder}' eliminata con successo.")
                folder_deleted = True
            except Exception as e:
                logger.error(f"Errore nell'eliminazione della cartella '{tv_folder}': {e}")
                return (True, f"Serie TV rimossa dal config, ma errore nell'eliminazione cartella: {e}")
        else:
            logger.warning(f"Cartella '{tv_folder}' non esistente.")

        if folder_deleted:
            return (True, f"Serie TV '{tv_name}' rimossa completamente (config + cartella).")
        else:
            return (True, f"Serie TV '{tv_name}' rimossa dal config. Cartella non esisteva.")

    def get_movies(self):
        """
        Ritorna la lista dei film presenti nel database.
        """
        return self.db.get_all_movies()

    def get_pending_movies(self):
        """
        Ritorna la lista dei film non ancora scaricati.
        """
        return self.db.get_pending_movies()

    def add_movie(self, name, link, last_update, slug=None, media_id=None,
                  provider_language="it", year=None, provider="streamingcommunity"):
        """
        Aggiunge un nuovo film al database.
        """
        # Se il link è un URL completo, estrai solo il path
        if link.startswith("http"):
            parsed_link = urlparse(link).path
        else:
            parsed_link = link

        # Convert last_update to datetime if it's a string
        last_update_dt = self._parse_last_update(last_update)

        # Check if movie with same name already exists
        existing_movie = self.db.get_movie_by_name(name)
        if existing_movie:
            logger.warning(f"Il film '{name}' esiste già. Aggiunta saltata.")
            return False

        success = self.db.add_movie(
            name, parsed_link, last_update_dt,
            slug=slug, media_id=media_id, provider_language=provider_language,
            year=year, provider=provider
        )
        if success:
            logger.info(f"Film '{name}' aggiunto alla configurazione.")
        return success

    def update_movie_downloaded(self, name, scaricato: int = 1):
        """
        Segna un film come scaricato.
        """
        return self.db.update_movie_downloaded(name, scaricato)

    def update_movie_last_update(self, name, last_update):
        """
        Aggiorna la data di last_update del film nel database.
        """
        last_update_dt = self._parse_last_update(last_update)
        return self.db.update_movie_last_update(name, last_update_dt)

    def get_movie_link(self, movie_name):
        """
        Restituisce il link del film in base al nome.
        """
        movie_name = movie_name.strip().lower()
        movie = self.db.search_movie_by_name(movie_name)
        if movie:
            return movie.get("link", "Link non disponibile.")
        return "Film non trovato."

    def remove_movie(self, movie_name: str) -> tuple:
        """
        Rimuove un film dal database e cancella la sua cartella dal disco.
        """
        movie = self.db.get_movie_by_name(movie_name)
        if movie is None:
            logger.warning(f"Film '{movie_name}' non trovato nella configurazione.")
            return (False, f"Film '{movie_name}' non trovato.")

        success = self.db.remove_movie(movie_name)
        if not success:
            logger.error(f"Errore nella rimozione del film '{movie_name}' dal database.")
            return (False, "Errore nella rimozione dal database.")

        logger.info(f"Film '{movie_name}' rimosso dalla configurazione.")

        # Cancella la cartella dal disco
        movie_folder = os.path.join(self.movies_folder, movie_name)
        folder_deleted = False

        if os.path.exists(movie_folder):
            try:
                shutil.rmtree(movie_folder)
                logger.info(f"Cartella '{movie_folder}' eliminata con successo.")
                folder_deleted = True
            except Exception as e:
                logger.error(f"Errore nell'eliminazione della cartella '{movie_folder}': {e}")
                return (True, f"Film rimosso dal config, ma errore nell'eliminazione cartella: {e}")
        else:
            logger.warning(f"Cartella '{movie_folder}' non esistente.")

        if folder_deleted:
            return (True, f"Film '{movie_name}' rimosso completamente (config + cartella).")
        else:
            return (True, f"Film '{movie_name}' rimosso dal config. Cartella non esisteva.")

    def remove_anime(self, anime_name: str) -> tuple:
        """
        Rimuove un anime dal database e cancella la sua cartella dal disco.

        Args:
            anime_name: Nome dell'anime da rimuovere

        Returns:
            tuple: (success: bool, message: str)
        """
        # Check if anime exists
        anime = self.db.get_anime_by_name(anime_name)
        if anime is None:
            logger.warning(f"Anime '{anime_name}' non trovato nella configurazione.")
            return (False, f"Anime '{anime_name}' non trovato.")

        # Remove from database
        success = self.db.remove_anime(anime_name)
        if not success:
            logger.error(f"Errore nella rimozione dell'anime '{anime_name}' dal database.")
            return (False, f"Errore nella rimozione dal database.")

        logger.info(f"Anime '{anime_name}' rimosso dalla configurazione.")

        # Cancella la cartella dal disco
        anime_folder = os.path.join(self.destination_folder, anime_name)
        folder_deleted = False

        if os.path.exists(anime_folder):
            try:
                shutil.rmtree(anime_folder)
                logger.info(f"Cartella '{anime_folder}' eliminata con successo.")
                folder_deleted = True
            except Exception as e:
                logger.error(f"Errore nell'eliminazione della cartella '{anime_folder}': {e}")
                return (True, f"Anime rimosso dal config, ma errore nell'eliminazione cartella: {e}")
        else:
            logger.warning(f"Cartella '{anime_folder}' non esistente.")

        if folder_deleted:
            return (True, f"Anime '{anime_name}' rimosso completamente (config + cartella).")
        else:
            return (True, f"Anime '{anime_name}' rimosso dal config. Cartella non esisteva.")
