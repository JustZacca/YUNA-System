# -*- coding: utf-8 -*-
import animeworld as aw
import os
import logging
import asyncio
from colorama import Fore, Style, init
from airi import Airi
import re
from color_utils import ColoredFormatter  # Importa la classe ColoredFormatter dal file color_utils
from colorama import init
from datetime import datetime, timezone
import requests
import JellyfinClient
init(autoreset=True)


# Configura il logging con il custom formatter
class ColoredFormatterWithClass(ColoredFormatter):
    def format(self, record):
        # Coloriamo il nome della classe in base al livello di log
        classname_color = Fore.CYAN  # Puoi scegliere qualsiasi colore
        class_name = f"{classname_color}{record.classname}{Style.RESET_ALL}"
        log_message = super().format(record)
        return log_message.replace('%(classname)s', class_name)

formatter = ColoredFormatter(
    fmt="\033[34m%(asctime)s\033[0m - %(levelname)s - %(message)s",  # Make the time blue
    datefmt="%Y-%m-%d %H:%M:%S"  # Keep the date format
)
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(handler)

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

    async def _download_single_episode(self, ep, anime_name, folder):
        """
        Scarica un singolo episodio usando asyncio.to_thread per non bloccare.
        Il semaphore limita a 3 download simultanei.
        """
        async with self.download_semaphore:
            title = f"{anime_name} - Episode {ep.number}"
            logger.info(f"Inizio download: {title}", extra={"classname": self.__class__.__name__})

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
            else:
                logger.error(f"Fallito download Episode {ep_number}: {error_msg}", extra={"classname": self.__class__.__name__})

            return result

    async def downloadEpisodes(self, episode_list):
        """
        Scarica episodi in parallelo (max 3 alla volta) senza bloccare l'event loop.
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
            self._download_single_episode(ep, self.anime_name, self.anime_folder)
            for ep in episodes
        ]

        # Esegui tutti i task concorrentemente
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Conta successi e fallimenti
        successes = sum(1 for r in results if isinstance(r, tuple) and r[1])
        failures = len(results) - successes

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
