# -*- coding: utf-8 -*-
import animeworld as aw
import os
import logging
from colorama import Fore, Style, init
from airi import Airi
import re
from color_utils import ColoredFormatter  # Importa la classe ColoredFormatter dal file color_utils
from colorama import init
from datetime import datetime, timezone
import asyncio
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
    
    def loadAnime(self, anime_link):
        """
        Carica un anime dal link e lo salva in self.anime.
        """
        try:
            logger.info(f"Caricamento anime da link: {anime_link}", extra={"classname": self.__class__.__name__})
            self.anime = self.aw.Anime(anime_link)
            anime_name = self.anime.getName()
            logger.info(f"Anime caricato: {anime_name}", extra={"classname": self.__class__.__name__})
            return self.anime
        except Exception as e:
            logger.error(f"Errore nel caricare l'anime dal link '{anime_link}': {e}", extra={"classname": self.__class__.__name__})
            self.anime = None
            return None
        
    def getEpisodes(self):
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

    def setupAnimeFolder(self):
        if self.anime is None:
            logger.warning("Nessun anime caricato.", extra={"classname": self.__class__.__name__})
            return []

        anime_name = self.anime.getName()
        self.anime_folder = os.path.join(self.airi.get_destination_folder(), anime_name)

        if not os.path.exists(self.anime_folder):
            os.makedirs(self.anime_folder)
            logger.info(f"Cartella creata: {self.anime_folder}", extra={"classname": self.__class__.__name__})
            episodes = self.anime.getEpisodes()
            logger.info(f"Totale episodi da scaricare: {len(episodes)}", extra={"classname": self.__class__.__name__})
            return [ep.number for ep in episodes]

        normalized_anime_name = self.normalize_name(anime_name)

        existing_files = os.listdir(self.anime_folder)
        existing_numbers = set()

        for f in existing_files:
            match = re.match(rf".*Episode\s+(\d+)\.mp4", f, re.IGNORECASE)
            if match:
                existing_numbers.add(int(match.group(1)))

        total_episodes = self.anime.getEpisodes()
        if total_episodes is None:
            logger.warning(f"Errore nel recupero episodi per {anime_name}.", extra={"classname": self.__class__.__name__})
            return []

        total_numbers = {int(ep.number) for ep in total_episodes}

        missing = total_numbers - existing_numbers

        logger.info(f"Trovati {len(existing_numbers)} episodi già scaricati.", extra={"classname": self.__class__.__name__})
        logger.info(f"{len(missing)} episodi mancanti: {missing}", extra={"classname": self.__class__.__name__})

        return missing
    
    def normalize_name(self,name):
        return re.sub(r'[^a-zA-Z0-9]', '', name).lower()

    def check_missing_episodes(self):
        if self.anime is None:
            logger.warning("Nessun anime caricato.", extra={"classname": self.__class__.__name__})
            return []

        anime_name = self.anime.getName()
        self.anime_folder = os.path.join(self.airi.get_destination_folder(), anime_name)

        if not os.path.exists(self.anime_folder):
            logger.warning(f"Cartella per {anime_name} non esiste. Creando la cartella...", extra={"classname": self.__class__.__name__})
            os.makedirs(self.anime_folder)
            logger.info(f"Cartella creata: {self.anime_folder}", extra={"classname": self.__class__.__name__})

        normalized_anime_name = self.normalize_name(anime_name)

        existing_files = os.listdir(self.anime_folder)
        existing_numbers = set()

        for f in existing_files:
            match = re.match(rf".*Episode\s+(\d+)\.mp4", f, re.IGNORECASE)
            if match:
                existing_numbers.add(int(match.group(1)))

        total_episodes = self.anime.getEpisodes()
        if total_episodes is None:
            logger.warning(f"Errore nel recupero episodi per {anime_name}.", extra={"classname": self.__class__.__name__})
            return []

        total_numbers = {int(ep.number) for ep in total_episodes}

        missing = total_numbers - existing_numbers
        extra = existing_numbers - total_numbers

        logger.info(f"Trovati {len(existing_numbers)} episodi già scaricati.", extra={"classname": self.__class__.__name__})
        logger.info(f"{len(missing)} episodi mancanti: {missing}", extra={"classname": self.__class__.__name__})
        logger.info(f"{len(extra)} episodi extra trovati: {extra}", extra={"classname": self.__class__.__name__})

        self.airi.update_downloaded_episodes(anime_name, len(existing_numbers))

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

    async def downloadEpisodes(self, episode_list):
        if self.anime is None:
            logger.warning("Nessun anime caricato.", extra={"classname": self.__class__.__name__})
            return False

        anime_name = self.anime.getName()

        try:
            episodes = self.anime.getEpisodes(episode_list)
        except Exception as e:
            logger.error(f"Impossibile recuperare gli episodi specificati. Errore: {e}", extra={"classname": self.__class__.__name__})
            return False

        logger.info(f"Inizio download di {len(episodes)} episodi...", extra={"classname": self.__class__.__name__})

        for ep in episodes:
            try:
                # Aggiungi l'hook per visualizzare il progresso del download
                ep.download(title=f"{anime_name} - Episode {ep.number}", folder=self.anime_folder, hook=self.my_hook)
            except Exception as e:
                logger.error(f"[ERRORE] Episodio {ep.number} fallito. Errore: {e}", extra={"classname": self.__class__.__name__})
                continue

        logger.info("Download degli episodi completato.", extra={"classname": self.__class__.__name__})
        return True
        
    def addAnime(self, link):
        """
        Aggiunge un nuovo anime al file config.json.
        """
        self.loadAnime(link)
        anime_name = self.anime.getName()
        episodes = self.anime.getEpisodes()
        last_episode_info = episodes[-1].fileInfo()
        last_modified = last_episode_info.get("last_modified", "Sconosciuto")
        self.airi.add_anime(anime_name, link, last_modified)
