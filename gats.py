from scuapi import API
import os
import logging
from colorama import Fore, Style, init
from airi import Airi
import re
# Importa la classe ColoredFormatter dal file color_utils
from color_utils import ColoredFormatter
from colorama import init
from datetime import datetime, timezone
import requests
import JellyfinClient

# Configura il logging con il custom formatter


class ColoredFormatterWithClass(ColoredFormatter):
    def format(self, record):
        # Coloriamo il nome della classe in base al livello di log
        classname_color = Fore.CYAN  # Puoi scegliere qualsiasi colore
        class_name = f"{classname_color}{record.classname}{Style.RESET_ALL}"
        log_message = super().format(record)
        return log_message.replace('%(classname)s', class_name)


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


class Gats:
    def __init__(self):
        self.name = "Gats"
        self.description = "General Advances Tv Scraper"
        self.version = "1.0.0"
        self.author = "Lord"
        self.anime = None  # Variabile d’istanza per salvare l'anime
        self.airi = Airi()  # Inizializza l'oggetto Airi
        self.tv_folder = None  # Variabile d’istanza per salvare la cartella dell'anime
        self.sc = API('https://172.67.161.253')
        self.jellyfin = JellyfinClient.JellyfinClient()  # Initialize the client correctly
        self.show_name = None  # Variabile d’istanza per salvare il nome dell'anime
        self.show_id = None

    async def search_show(self, query: str):
        logger.info(f"[SEARCH] Cerco: {query}", extra={"classname": self.__class__.__name__})
        try:
            results = await self.sc.search(query)
            if not results:
                logger.warning("[SEARCH] Nessun risultato trovato", extra={"classname": self.__class__.__name__})
            return results
        except Exception as e:
            logger.error(f"[SEARCH ERROR] {e}", extra={"classname": self.__class__.__name__})
            return {}


        async def load_show(self, show_id: str):
            try:
                logger.info(f"[LOAD] Carico show ID: {show_id}", extra={
                            "classname": self.__class__.__name__})
                data = await self.sc.load(show_id)
                self.show = data
                self.show_id = data.get("id")
                self.show_name = data.get("name")
                logger.info(f"[SUCCESS] Caricato: {self.show_name}", extra={
                            "classname": self.__class__.__name__})
                return data
            except Exception as e:
                logger.error(f"[ERROR] Caricamento fallito: {e}", extra={
                             "classname": self.__class__.__name__})
                return None

        async def setup_show_folder(self):
            safe_name = re.sub(
                r'[^\w\s-]', '', self.show_name).strip().replace(" ", "_")
            folder = os.path.join(os.getcwd(), "downloads", safe_name)
            os.makedirs(folder, exist_ok=True)
            self.tv_folder = folder
            logger.info(f"[FOLDER] Cartella creata: {folder}", extra={
                        "classname": self.__class__.__name__})
            return folder

        def list_episodes(self):
            if not self.show or self.show.get("type", "").lower() != "tv":
                logger.warning("[SKIP] Non è una serie TV", extra={
                               "classname": self.__class__.__name__})
                return {}
            seasons = {}
            for s in self.show.get("seasons", []):
                season_num = s.get("season_number")
                episodes = s.get("episodes", [])
                seasons[season_num] = episodes
            logger.info(f"[EPISODES] Trovate {len(seasons)} stagioni", extra={
                        "classname": self.__class__.__name__})
            return seasons
