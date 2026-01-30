# -*- coding: utf-8 -*-
"""
Media service for YUNA System.
Contains Miko (anime) and MikoSC (streaming community) services.
"""

import animeworld as aw
import os
import re
import asyncio
import requests
from datetime import datetime, timezone
from colorama import Fore, Style, init

from yuna.utils.logging import get_logger
from yuna.providers.animeworld.client import Airi
from yuna.integrations.jellyfin import JellyfinClient

init(autoreset=True)

logger = get_logger(__name__)

class Miko:
    def __init__(self):
        self.name = "Miko"
        self.description = "Media Indexing and Kapturing Operator (MIKO) is a tool for indexing and capturing media content."
        self.version = "1.0.0"
        self.author = "AnimeWorld"
        self.anime = None  # Variabile d’istanza per salvare l'anime
        self.airi = Airi()  # Inizializza l'oggetto Airi
        self.anime_folder = None  # Variabile d’istanza per salvare la cartella dell'anime
        self.aw = aw
        self.aw.SES.base_url = self.airi.BASE_URL
        self.jellyfin = None  # JellyfinClient.JellyfinClient()  # Disabilitato temporaneamente
        self.anime_name = None  # Variabile d'istanza per salvare il nome dell'anime
        self.download_semaphore = asyncio.Semaphore(3)  # Max 3 download paralleli
    
    async def loadAnime(self, anime_link):
        """
        Carica un anime dal link e lo salva in self.anime.
        """
        try:
            self.anime = self.aw.Anime(anime_link)
            self.anime_name = self.anime.getName()
            logger.info(f"Anime caricato: {self.anime_name}", extra={"classname": self.__class__.__name__})
            await self.setupAnimeFolder()
            return self.anime
        except Exception as e:
            logger.error(f"Errore nel caricare l'anime dal link '{anime_link}': {e}", extra={"classname": self.__class__.__name__})
            self.anime = None
            return None
        
    async def getEpisodes(self):
        """
        Ottieni tutti gli episodi dell'anime caricato.
        """
        if self.anime is None:
            logger.warning("Nessun anime caricato. Carica un anime prima.", extra={"classname": self.__class__.__name__})
            return None
        try:
            logger.info(f"Recupero episodi per l'anime: {self.anime.getName()}", extra={"classname": self.__class__.__name__})
            episodes = self.anime.getEpisodes()
            logger.info(f"{len(episodes)} episodi recuperati.", extra={"classname": self.__class__.__name__})
            return episodes
        except Exception as e:
            logger.error(f"Errore nel recupero episodi per l'anime '{self.anime.getName()}': {e}", extra={"classname": self.__class__.__name__})
            return None

    async def setupAnimeFolder(self):
        if self.anime is None:
            logger.warning("Nessun anime caricato.", extra={"classname": self.__class__.__name__})
            return False

        self.anime_folder = os.path.join(self.airi.get_destination_folder(), self.anime_name)

        if not os.path.exists(self.anime_folder):
            try:
                os.makedirs(self.anime_folder)
                logger.info(f"Cartella creata: {self.anime_folder}", extra={"classname": self.__class__.__name__})
                await self.saveAnimeCover()
                if self.jellyfin:
                    self.jellyfin.trigger_scan()
                return True
            except Exception as e:
                logger.error(f"Errore nella creazione della cartella {self.anime_folder}: {e}", extra={"classname": self.__class__.__name__})
                return False
        return True

    async def saveAnimeCover(self):
        if self.anime is None:
            logger.warning("Nessun anime caricato.", extra={"classname": self.__class__.__name__})
            return False

        try:
            # Ottieni l'URL della copertina
            cover_url = self.anime.getCover()
            cover_path = os.path.join(self.anime_folder, "folder.jpg")

            # Scarica l'immagine
            response = requests.get(cover_url, stream=True)
            response.raise_for_status()  # solleva errore se c'è un problema con il download

            # Salva il file
            with open(cover_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.info(f"Copertina salvata in: {cover_path}", extra={"classname": self.__class__.__name__})
            return True

        except Exception as e:
            logger.error(f"Errore nel salvataggio della copertina per '{self.anime_name}': {e}", extra={"classname": self.__class__.__name__})
            return False
        

    async def getMissingEpisodes(self):
        if self.anime is None:
            logger.warning("Nessun anime caricato.", extra={"classname": self.__class__.__name__})
            return []

        episodes = self.anime.getEpisodes()
        if episodes is None:
            logger.warning(f"Errore nel recupero episodi per {self.anime_name}.", extra={"classname": self.__class__.__name__})
            return []

        existing_files = os.listdir(self.anime_folder)
        existing_numbers = set()

        for f in existing_files:
            match = re.match(rf".*Episode\s+(\d+)\.mp4", f, re.IGNORECASE)
            if match:
                existing_numbers.add(int(match.group(1)))

        # Supporta numeri interi e decimali (es: "9", "9.5")
        total_numbers = set()
        for ep in episodes:
            try:
                # Controlla se il numero e un intero o decimale valido
                if re.match(r'^\d+(\.\d+)?$', str(ep.number)):
                    total_numbers.add(int(float(ep.number)))
            except (ValueError, TypeError):
                logger.warning(f"Numero episodio non valido: {ep.number}", extra={"classname": self.__class__.__name__})

        missing = total_numbers - existing_numbers
        self.airi.update_downloaded_episodes(self.anime_name, len(existing_numbers))
        self.airi.update_episodes_number(self.anime_name, len(total_numbers))

        logger.info(f"Trovati {len(existing_numbers)} episodi già scaricati. Ne mancano {len(missing)}", extra={"classname": self.__class__.__name__})

        return missing
    
    def normalize_name(self,name):
        return re.sub(r'[^a-zA-Z0-9]', '', name).lower()

    async def check_missing_episodes(self):
        if self.anime is None:
            logger.warning("Nessun anime caricato.", extra={"classname": self.__class__.__name__})
            return []

        self.anime_folder = os.path.join(self.airi.get_destination_folder(), self.anime_name)

        if not os.path.exists(self.anime_folder):
            logger.warning(f"Cartella per {self.anime_name} non esiste. Creando la cartella...", extra={"classname": self.__class__.__name__})
            os.makedirs(self.anime_folder)
            logger.info(f"Cartella creata: {self.anime_folder}", extra={"classname": self.__class__.__name__})

        normalized_anime_name = self.normalize_name(self.anime_name)

        existing_files = os.listdir(self.anime_folder)
        existing_numbers = set()

        for f in existing_files:
            match = re.match(rf".*Episode\s+(\d+)\.mp4", f, re.IGNORECASE)
            if match:
                existing_numbers.add(int(match.group(1)))

        total_episodes = self.anime.getEpisodes()
        if total_episodes is None:
            logger.warning(f"Errore nel recupero episodi per {self.anime_name}.", extra={"classname": self.__class__.__name__})
            return []

        # Supporta numeri interi e decimali
        total_numbers = set()
        for ep in total_episodes:
            try:
                if re.match(r'^\d+(\.\d+)?$', str(ep.number)):
                    total_numbers.add(int(float(ep.number)))
            except (ValueError, TypeError):
                logger.warning(f"Numero episodio non valido: {ep.number}", extra={"classname": self.__class__.__name__})

        missing = total_numbers - existing_numbers
        extra = existing_numbers - total_numbers

        logger.info(f"Trovati {len(existing_numbers)} episodi già scaricati.", extra={"classname": self.__class__.__name__})
        if missing:
            logger.info(f"{len(missing)} episodi mancanti: {missing}", extra={"classname": self.__class__.__name__})
        if extra:
            logger.info(f"{len(extra)} episodi extra trovati: {extra}", extra={"classname": self.__class__.__name__})

        self.airi.update_downloaded_episodes(self.anime_name, len(existing_numbers))
        self.airi.update_episodes_number(self.anime_name, len(total_numbers))

        return bool(missing or extra)

    def count_and_update_episodes(self, anime_name, episodi_scaricati):
        """
        Conta gli episodi scaricati per un dato anime e aggiorna il conteggio in Airi.
        """
        self.anime_folder = os.path.join(self.airi.get_destination_folder(), anime_name)

        if not os.path.exists(self.anime_folder):
            logger.warning(f"Cartella per {anime_name} non esiste.", extra={"classname": self.__class__.__name__})
            return False

        existing_files = os.listdir(self.anime_folder)
        existing_numbers = set()

        for f in existing_files:
            match = re.match(rf".*Episode\s+(\d+)\.mp4", f, re.IGNORECASE)
            if match:
                existing_numbers.add(int(match.group(1)))

        logger.info(f"Trovati {len(existing_numbers)} episodi scaricati per '{anime_name}'.", extra={"classname": self.__class__.__name__})

        if len(existing_numbers) == episodi_scaricati:
            logger.info(f"Tutti gli episodi per '{anime_name}' sono già aggiornati. Nessun aggiornamento necessario.", extra={"classname": self.__class__.__name__})
            return True

        self.airi.update_downloaded_episodes(anime_name, len(existing_numbers))

        return True

    def my_hook(self, d, width=70):
        """
        Stampa una ProgressBar con tutte le informazioni di download.
        """
        if d['status'] == 'downloading':
            out = "{filename}:\n[{bar}][{percentage:^6.1%}]\n{downloaded_bytes}/{total_bytes} in {elapsed:%H:%M:%S} (ETA: {eta:%H:%M:%S})\x1B[3A"
            
            # Usa datetime.fromtimestamp con tz=timezone.utc per ottenere un datetime consapevole del fuso orario
            d['elapsed'] = datetime.fromtimestamp(d['elapsed'], tz=timezone.utc)
            d['eta'] = datetime.fromtimestamp(d['eta'], tz=timezone.utc)
            d['bar'] = '#'*int(width*d['percentage']) + ' '*(width-int(width*d['percentage']))

            print(out.format(**d))

        elif d['status'] == 'finished':
            print('\n\n\n')

    def _sync_download_episode(self, ep, title, folder):
        """
        Wrapper sincrono per ep.download() - viene eseguito in un thread separato.
        Restituisce (episode_number, success, error_msg, last_modified)
        """
        try:
            ep.download(title=title, folder=folder, hook=self.my_hook)
            last_modified = ep.fileInfo().get("last_modified", None)
            return (ep.number, True, None, last_modified)
        except Exception as e:
            return (ep.number, False, str(e), None)

    async def _download_single_episode(self, ep, anime_name, folder, progress_callback=None):
        """
        Scarica un singolo episodio usando asyncio.to_thread per non bloccare.
        Il semaphore limita a 3 download simultanei.
        """
        async with self.download_semaphore:
            title = f"{anime_name} - Episode {ep.number}"
            logger.info(f"Inizio download: {title}", extra={"classname": self.__class__.__name__})

            # Notify start
            if progress_callback:
                await progress_callback(ep.number, 0.1, done=False)

            # Esegui il download sincrono in un thread separato
            result = await asyncio.to_thread(
                self._sync_download_episode,
                ep, title, folder
            )

            ep_number, success, error_msg, last_modified = result

            if success:
                logger.info(f"Completato download: Episode {ep_number}", extra={"classname": self.__class__.__name__})
                if last_modified:
                    self.airi.update_last_update(anime_name, last_modified)
                # Notify complete
                if progress_callback:
                    await progress_callback(ep.number, 1.0, done=True)
            else:
                logger.error(f"Fallito download Episode {ep_number}: {error_msg}", extra={"classname": self.__class__.__name__})
                if progress_callback:
                    await progress_callback(ep.number, 0.0, done=True)

            return result

    async def downloadEpisodes(self, episode_list, progress_callback=None):
        """
        Scarica episodi in parallelo (max 3 alla volta) senza bloccare l'event loop.

        Args:
            episode_list: List of episode numbers to download
            progress_callback: Optional async callback(ep_num, progress, done)
        """
        if self.anime is None:
            logger.warning("Nessun anime caricato.", extra={"classname": self.__class__.__name__})
            return False

        try:
            episodes = self.anime.getEpisodes(episode_list)
        except Exception as e:
            logger.error(f"Impossibile recuperare gli episodi specificati. Errore: {e}", extra={"classname": self.__class__.__name__})
            return False

        logger.info(f"Inizio download PARALLELO di {len(episodes)} episodi (max 3 simultanei)...", extra={"classname": self.__class__.__name__})

        # Crea task per tutti gli episodi - il semaphore gestirà il limite
        tasks = [
            self._download_single_episode(ep, self.anime_name, self.anime_folder, progress_callback)
            for ep in episodes
        ]

        # Esegui tutti i task concorrentemente
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Conta successi e fallimenti
        successes = 0
        failures = 0
        for r in results:
            if isinstance(r, Exception):
                logger.error(f"Download exception: {type(r).__name__}: {r}", extra={"classname": self.__class__.__name__})
                failures += 1
            elif isinstance(r, tuple) and r[1]:
                successes += 1
            else:
                # Failed download with error message
                if isinstance(r, tuple) and len(r) >= 3:
                    logger.error(f"Download failed: Episode {r[0]} - {r[2]}", extra={"classname": self.__class__.__name__})
                failures += 1

        logger.info(f"Download completato. Successi: {successes}, Fallimenti: {failures}", extra={"classname": self.__class__.__name__})

        # Conta gli episodi effettivamente presenti nella cartella
        try:
            existing_files = os.listdir(self.anime_folder)
            downloaded_count = sum(
                1 for f in existing_files
                if re.match(rf".*Episode\s+(\d+)\.mp4", f, re.IGNORECASE)
            )
            self.airi.update_downloaded_episodes(self.anime_name, downloaded_count)
        except Exception as e:
            logger.error(f"Errore nel conteggio episodi scaricati: {e}", extra={"classname": self.__class__.__name__})

        # Trigger Jellyfin scan una sola volta alla fine
        if self.jellyfin and successes > 0:
            self.jellyfin.trigger_scan()

        return failures == 0
        
    async def addAnime(self, link):
        """
        Aggiunge un nuovo anime al file config.json.
        """
        anime = await self.loadAnime(link)
        if anime is None:
            logger.error(f"Impossibile caricare l'anime dal link: {link}", extra={"classname": self.__class__.__name__})
            return None

        episodes = self.anime.getEpisodes()
        if not episodes:
            logger.error(f"Nessun episodio trovato per l'anime: {self.anime_name}", extra={"classname": self.__class__.__name__})
            return None

        last_episode_info = episodes[-1].fileInfo()
        last_modified = last_episode_info.get("last_modified", "Sconosciuto")

        if not await self.setupAnimeFolder():
            logger.error("Impossibile configurare la cartella dell'anime. Operazione fallita.", extra={"classname": self.__class__.__name__})
            return None

        self.airi.add_anime(self.anime_name, link, last_modified, len(episodes))
        return self.anime_name
        
    def findAnime(self, anime_name):
        """
        Trova un anime su animeworld e ne restituisce nome e link
        """
        try:
            risultati = self.aw.find(anime_name)
            if risultati:
                anime_list = [{"name": anime["name"], "link": anime["link"]} for anime in risultati]
                logger.info(f"{len(anime_list)} risultati trovati per '{anime_name}'.", extra={"classname": self.__class__.__name__})
                return anime_list
            else:
                logger.warning(f"Nessun risultato trovato per '{anime_name}'.", extra={"classname": self.__class__.__name__})
                return []
        except Exception as e:
            logger.error(f"Errore durante la ricerca di '{anime_name}': {e}", extra={"classname": self.__class__.__name__})
            return []


# ==================== MIKO SC - StreamingCommunity Extension ====================

from yuna.providers.streamingcommunity.client import StreamingCommunity, MediaItem, SeriesInfo, Episode
from yuna.data.database import Database
import json


class MikoSC:
    """
    Media Indexing and Kapturing Operator for StreamingCommunity.
    Handles TV series and movies from StreamingCommunity.
    """

    def __init__(self, movies_folder: str = None, series_folder: str = None):
        self.name = "MikoSC"
        self.description = "StreamingCommunity extension for MIKO"
        self.version = "1.0.0"

        # Get folders from Airi config (uses env vars MOVIES_FOLDER, SERIES_FOLDER)
        self.airi = Airi()

        self.movies_folder = movies_folder or self.airi.get_movies_folder()
        self.series_folder = series_folder or self.airi.get_series_folder()

        # Initialize StreamingCommunity client
        self.sc = StreamingCommunity(
            movies_folder=self.movies_folder,
            series_folder=self.series_folder
        )

        # Database for persistence
        self.db = Database()

        # Current selection state
        self.current_series: SeriesInfo = None
        self.current_item: MediaItem = None
        self.search_results: list = []

        # Semaphore for parallel downloads
        self.download_semaphore = asyncio.Semaphore(2)

        logger.info(f"MikoSC initialized. Movies: {self.movies_folder}, Series: {self.series_folder}")

    def search(self, query: str, filter_type: str = None) -> list:
        """
        Search for content on StreamingCommunity.

        Args:
            query: Search query
            filter_type: 'movie', 'tv', or None for all

        Returns:
            List of MediaItem objects
        """
        logger.info(f"Searching StreamingCommunity for: {query}")
        results = self.sc.search(query)

        if filter_type == "movie":
            results = [r for r in results if r.type == "movie"]
        elif filter_type == "tv":
            results = [r for r in results if r.type == "tv"]

        self.search_results = results
        logger.info(f"Found {len(results)} results")
        return results

    def search_series(self, query: str) -> list:
        """Search for TV series only."""
        return self.search(query, filter_type="tv")

    def search_films(self, query: str) -> list:
        """Search for films only."""
        return self.search(query, filter_type="movie")

    def select_from_results(self, index: int) -> MediaItem:
        """Select an item from last search results by index."""
        if 0 <= index < len(self.search_results):
            self.current_item = self.search_results[index]
            logger.info(f"Selected: {self.current_item.name}")
            return self.current_item
        logger.warning(f"Invalid index: {index}")
        return None

    def get_series_info(self, item: MediaItem = None) -> SeriesInfo:
        """
        Get full series information.

        Args:
            item: MediaItem to get info for (uses current_item if None)

        Returns:
            SeriesInfo object
        """
        item = item or self.current_item
        if not item:
            logger.warning("No item selected")
            return None

        if item.type != "tv":
            logger.warning(f"{item.name} is not a TV series")
            return None

        info = self.sc.get_series_info(item)
        if info:
            self.current_series = info
            logger.info(f"Loaded series: {info.name} ({len(info.seasons)} seasons)")
        return info

    def get_season_episodes(self, season_number: int) -> list:
        """Get episodes for a specific season."""
        if not self.current_series:
            logger.warning("No series loaded")
            return []

        return self.sc.get_season_episodes(self.current_series, season_number)

    # ==================== DATABASE OPERATIONS ====================

    def add_series_to_library(self, item: MediaItem = None) -> bool:
        """
        Add a TV series to the library for tracking.

        Args:
            item: MediaItem to add (uses current_item if None)

        Returns:
            True if added successfully
        """
        item = item or self.current_item
        if not item or item.type != "tv":
            logger.warning("No TV series selected")
            return False

        # Get series info
        info = self.get_series_info(item)
        if not info:
            return False

        # Calculate total episodes across all seasons
        total_episodes = 0
        for season in info.seasons:
            if not season.episodes:
                self.get_season_episodes(season.number)
            total_episodes += len(season.episodes)

        # Build link for database
        link = f"{self.sc.base_url}/{item.provider_language}/titles/{item.id}-{item.slug}"

        success = self.db.add_tv(
            name=item.name,
            link=link,
            last_update=datetime.now(),
            numero_episodi=total_episodes,
            slug=item.slug,
            media_id=item.id,
            provider_language=item.provider_language,
            year=item.year,
            provider="streamingcommunity"
        )

        if success:
            logger.info(f"Added series '{item.name}' to library")
            # Create series folder
            series_folder = os.path.join(self.series_folder, item.name)
            os.makedirs(series_folder, exist_ok=True)

        return success

    def add_film_to_library(self, item: MediaItem = None) -> bool:
        """
        Add a film to the library.

        Args:
            item: MediaItem to add (uses current_item if None)

        Returns:
            True if added successfully
        """
        item = item or self.current_item
        if not item or item.type != "movie":
            logger.warning("No movie selected")
            return False

        link = f"{self.sc.base_url}/{item.provider_language}/titles/{item.id}-{item.slug}"

        success = self.db.add_movie(
            name=item.name,
            link=link,
            last_update=datetime.now(),
            slug=item.slug,
            media_id=item.id,
            provider_language=item.provider_language,
            year=item.year,
            provider="streamingcommunity"
        )

        if success:
            logger.info(f"Added movie '{item.name}' to library")

        return success

    def get_library_series(self) -> list:
        """Get all TV series from library."""
        return self.db.get_all_tv()

    def get_library_films(self) -> list:
        """Get all films from library."""
        return self.db.get_all_movies()

    def get_pending_films(self) -> list:
        """Get films that haven't been downloaded yet."""
        return self.db.get_pending_movies()

    def remove_series(self, name: str) -> bool:
        """Remove a series from the library."""
        return self.db.remove_tv(name)

    def remove_film(self, name: str) -> bool:
        """Remove a film from the library."""
        return self.db.remove_movie(name)

    # ==================== DOWNLOAD OPERATIONS ====================

    async def download_film(self, item: MediaItem = None,
                            progress_callback=None) -> tuple:
        """
        Download a film.

        Args:
            item: MediaItem to download (uses current_item if None)
            progress_callback: Optional callback for progress updates

        Returns:
            Tuple of (success, path or error)
        """
        item = item or self.current_item
        if not item or item.type != "movie":
            return (False, "No movie selected")

        logger.info(f"Downloading film: {item.name}")

        async with self.download_semaphore:
            success, result = await self.sc.download_film(item, progress_callback)

        if success:
            # Mark as downloaded in database
            self.db.update_movie_downloaded(item.name, 1)
            logger.info(f"Film downloaded: {result}")
        else:
            logger.error(f"Download failed: {result}")

        return (success, result)

    async def download_episode(self, series_name: str, season_number: int,
                               episode_number: int, progress_callback=None) -> tuple:
        """
        Download a single episode.

        Args:
            series_name: Name of the series
            season_number: Season number
            episode_number: Episode number
            progress_callback: Optional callback

        Returns:
            Tuple of (success, path or error)
        """
        # Get series from database
        series_data = self.db.get_tv_by_name(series_name)
        if not series_data:
            return (False, f"Series '{series_name}' not found in library")

        # Load series info
        item = MediaItem(
            id=series_data["media_id"],
            name=series_data["name"],
            slug=series_data["slug"],
            type="tv",
            year=series_data.get("year", ""),
            provider_language=series_data.get("provider_language", "it")
        )

        info = self.sc.get_series_info(item)
        if not info:
            return (False, "Could not load series info")

        # Get episodes for season
        episodes = self.sc.get_season_episodes(info, season_number)
        if not episodes:
            return (False, f"Season {season_number} not found")

        # Find episode
        episode = next((e for e in episodes if e.number == episode_number), None)
        if not episode:
            return (False, f"Episode {episode_number} not found")

        logger.info(f"Downloading: {series_name} S{season_number:02d}E{episode_number:02d}")

        async with self.download_semaphore:
            success, result = await self.sc.download_episode(
                info, season_number, episode,
                lang=series_data.get("provider_language", "it"),
                progress_callback=progress_callback
            )

        if success:
            # Update seasons data in database
            self._update_downloaded_episode(series_name, season_number, episode_number)
            logger.info(f"Episode downloaded: {result}")
        else:
            logger.error(f"Download failed: {result}")

        return (success, result)

    async def download_season(self, series_name: str, season_number: int,
                              progress_callback=None) -> dict:
        """
        Download all episodes of a season.

        Args:
            series_name: Name of the series
            season_number: Season number
            progress_callback: Optional callback

        Returns:
            Dict mapping episode numbers to (success, path or error)
        """
        series_data = self.db.get_tv_by_name(series_name)
        if not series_data:
            return {}

        item = MediaItem(
            id=series_data["media_id"],
            name=series_data["name"],
            slug=series_data["slug"],
            type="tv",
            year=series_data.get("year", ""),
            provider_language=series_data.get("provider_language", "it")
        )

        info = self.sc.get_series_info(item)
        if not info:
            return {}

        logger.info(f"Downloading season {season_number} of {series_name}")

        results = await self.sc.download_season(
            info, season_number,
            lang=series_data.get("provider_language", "it"),
            progress_callback=progress_callback
        )

        # Update database
        for ep_num, (success, _) in results.items():
            if success:
                self._update_downloaded_episode(series_name, season_number, ep_num)

        return results

    def _update_downloaded_episode(self, series_name: str, season: int, episode: int):
        """Update the seasons_data JSON in database."""
        series_data = self.db.get_tv_by_name(series_name)
        if not series_data:
            return

        # Parse existing seasons_data or create new
        seasons_data = {}
        if series_data.get("seasons_data"):
            try:
                seasons_data = json.loads(series_data["seasons_data"])
            except json.JSONDecodeError:
                pass

        # Initialize season if needed
        season_key = str(season)
        if season_key not in seasons_data:
            seasons_data[season_key] = {"total": 0, "downloaded": []}

        # Add episode to downloaded list
        if episode not in seasons_data[season_key]["downloaded"]:
            seasons_data[season_key]["downloaded"].append(episode)
            seasons_data[season_key]["downloaded"].sort()

        # Update database
        self.db.update_tv_seasons_data(series_name, json.dumps(seasons_data))

        # Update total downloaded count
        total_downloaded = sum(
            len(s.get("downloaded", [])) for s in seasons_data.values()
        )
        self.db.update_tv_episodes(series_name, total_downloaded)

    def get_missing_episodes(self, series_name: str) -> dict:
        """
        Get missing episodes for a series.

        Returns:
            Dict mapping season numbers to lists of missing episode numbers
        """
        series_data = self.db.get_tv_by_name(series_name)
        if not series_data:
            return {}

        # Load series info
        item = MediaItem(
            id=series_data["media_id"],
            name=series_data["name"],
            slug=series_data["slug"],
            type="tv",
            provider_language=series_data.get("provider_language", "it")
        )

        info = self.sc.get_series_info(item)
        if not info:
            return {}

        # Parse downloaded episodes
        downloaded = {}
        if series_data.get("seasons_data"):
            try:
                seasons_json = json.loads(series_data["seasons_data"])
                for s_key, s_data in seasons_json.items():
                    downloaded[int(s_key)] = set(s_data.get("downloaded", []))
            except json.JSONDecodeError:
                pass

        # Find missing episodes per season
        missing = {}
        for season in info.seasons:
            if not season.episodes:
                self.sc.get_season_episodes(info, season.number)

            all_eps = {ep.number for ep in season.episodes}
            downloaded_eps = downloaded.get(season.number, set())
            missing_eps = all_eps - downloaded_eps

            if missing_eps:
                missing[season.number] = sorted(missing_eps)

        return missing

    async def download_missing_episodes(self, series_name: str,
                                        progress_callback=None) -> dict:
        """
        Download all missing episodes for a series.

        Returns:
            Dict with results per season
        """
        missing = self.get_missing_episodes(series_name)
        if not missing:
            logger.info(f"No missing episodes for {series_name}")
            return {}

        results = {}
        for season, episodes in missing.items():
            logger.info(f"Downloading {len(episodes)} missing episodes from S{season:02d}")
            season_results = {}

            for ep_num in episodes:
                success, result = await self.download_episode(
                    series_name, season, ep_num, progress_callback
                )
                season_results[ep_num] = (success, result)

            results[season] = season_results

        return results

    async def check_and_download_new_episodes(self, progress_callback=None) -> dict:
        """
        Check all series for new episodes and download them.

        Returns:
            Dict with download results per series
        """
        all_results = {}
        series_list = self.get_library_series()

        for series in series_list:
            name = series.get("name")
            if not name:
                continue

            logger.info(f"Checking for new episodes: {name}")
            missing = self.get_missing_episodes(name)

            if missing:
                total_missing = sum(len(eps) for eps in missing.values())
                logger.info(f"Found {total_missing} missing episodes for {name}")

                results = await self.download_missing_episodes(name, progress_callback)
                all_results[name] = results
            else:
                logger.info(f"No new episodes for {name}")

        return all_results
