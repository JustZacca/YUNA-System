# -*- coding: utf-8 -*-
import animeworld as aw
import os
import logging
from colorama import Fore, Style, init
from airi import Airi
import re
from tqdm import tqdm
from color_utils import ColoredFormatter  # Importa la classe ColoredFormatter dal file color_utils
from colorama import init
init(autoreset=True)

# Configura il logging con il custom formatter
formatter = ColoredFormatter(
    fmt="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
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
    
    def loadAnime(self, anime_link):
        """
        Load an anime by its link and save it to self.anime.
        """
        try:
            logger.info(f"Attempting to load anime from link: {anime_link}")
            self.anime = aw.Anime(anime_link)
            anime_name = self.anime.getName()
            logger.info(f"Anime loaded successfully: {anime_name}")
            return self.anime
        except Exception as e:
            logger.error(f"Failed to load anime from link '{anime_link}'. Error: {e}")
            self.anime = None
            return None
        
    def getEpisodes(self):
        """
        Get all episodes of the loaded anime.
        """
        if self.anime is None:
            logger.warning("No anime loaded. Please load an anime first.")
            return None
        try:
            logger.info(f"Fetching episodes for anime: {self.anime.getName()}")
            episodes = self.anime.getEpisodes()
            logger.info(f"Retrieved {len(episodes)} episodes.")
            return episodes
        except Exception as e:
            logger.error(f"Failed to fetch episodes for anime '{self.anime.getName()}'. Error: {e}")
            return None

    def setupAnimeFolder(self):
        if self.anime is None:
            logger.warning("No anime loaded.")
            return []

        anime_name = self.anime.getName()
        self.anime_folder = os.path.join(self.airi.get_destination_folder(), anime_name)

        if not os.path.exists(self.anime_folder):
            os.makedirs(self.anime_folder)
            logger.info(f"Created folder: {self.anime_folder}")
            episodes = self.anime.getEpisodes()
            logger.info(f"Total episodes to download: {len(episodes)}")
            return [ep.number for ep in episodes]

        # Trova gli episodi già presenti
        existing_files = os.listdir(self.anime_folder)
        episode_pattern = re.compile(rf"{re.escape(anime_name)} - Episode (\d+)\.mp4")

        existing_numbers = {
            int(match.group(1))
            for f in existing_files
            for match in [episode_pattern.match(f)]
            if match
        }

        total_episodes = self.anime.getEpisodes()
        missing = [int(ep.number) for ep in total_episodes if int(ep.number) not in existing_numbers]

        logger.info(f"Found {len(existing_numbers)} episode(s) already downloaded.")
        logger.info(f"{len(missing)} episode(s) still missing: {missing}")
        
        return missing

    def downloadEpisodes(self, episode_list):
        if self.anime is None:
            logger.warning("No anime loaded.")
            return False

        anime_name = self.anime.getName()

        try:
            episodes = self.anime.getEpisodes(episode_list) 
        except Exception as e:
            logger.error(f"Could not retrieve specified episodes. Error: {e}")
            return False

        logger.info(f"Starting download of {len(episodes)} episodes...\n")

        for ep in tqdm(episodes, desc="Downloading episodes", unit="ep", colour="cyan"):
            try:
                ep.download(title=f"{anime_name} - Episode {ep.number}", folder=self.anime_folder)
            except Exception as e:
                tqdm.write(f"[ERROR] Episode {ep.number} failed. Error: {e}")
                continue

        logger.info("Finished downloading requested episodes.")
        return True
    
    def addAnime(self, link):
        """
        Aggiunge un nuovo anime al file config.json.
        """
        self.loadAnime(link)
        anime_name = self.anime.getName()
        self.airi.add_anime(anime_name, link)