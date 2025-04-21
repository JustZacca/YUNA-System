from dotenv import load_dotenv
import os
import json
import logging
from colorama import Fore, Style, init
from color_utils import ColoredFormatter  # Importa la classe ColoredFormatter dal file color_utils
from colorama import init
import re
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

class Airi:
    def __init__(self):
        load_dotenv()  # Carica il file .env nella environment

        self.destination_folder = os.getenv("DESTINATION_FOLDER")
        self.telegram_token = os.getenv("TELEGRAM_TOKEN")
        self.TELEGRAM_CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID"))
        self.UPDATE_TIME = int(os.getenv("UPDATE_TIME", 60))  # Default to 60 seconds if not set
        logger.info(f"Config loaded: destination_folder={self.destination_folder}")
        
        self.config_path = "config.json"
        self.config = self.load_or_create_config()
        
    def get_destination_folder(self):
        """
        Restituisce la cartella di destinazione per il download.
        """
        if not self.destination_folder:
            raise ValueError("Destination folder not set in the environment.")
        return self.destination_folder
    
    def load_or_create_config(self):
        """
        Carica il file config.json se esiste, altrimenti lo crea vuoto.
        """
        if not os.path.exists(self.config_path):
            logger.info(f"{self.config_path} not found. Creating empty config.")
            # Creazione di un config vuoto
            default_config = {
                "anime": []
            }
            with open(self.config_path, "w") as config_file:
                json.dump(default_config, config_file, indent=4)
            logger.info(f"{self.config_path} created with empty anime list.")
            return default_config

        # Se il file esiste, carica il contenuto
        with open(self.config_path, "r") as config_file:
            config = json.load(config_file)
        logger.info(f"{self.config_path} loaded.")
        return config
    
    def get_anime(self):
        """
        Ritorna la lista degli anime presenti nel config.
        """
        self.reload_config()
        return self.config.get("anime", [])
    
    def add_anime(self, name, link, last_update):
        """
        Aggiunge un nuovo anime al file config.json.
        """
        anime = {
            "name": name,
            "link": link,
            "last_update" : last_update.strftime("%Y-%m-%d %H:%M:%S")  # Formatta la data in stringa
        }
        self.config["anime"].append(anime)

        # Scrittura nel file config.json
        with open(self.config_path, "w") as config_file:
            json.dump(self.config, config_file, indent=4)
        logger.info(f"Anime '{name}' added to config.")
        logger.debug(f"Updated config: {json.dumps(self.config, indent=4)}")
        self.reload_config()
        
    def reload_config(self):
        """
        Ricarica il file di configurazione.
        """
        self.config = self.load_or_create_config()
        logger.info(f"Config ricaricato.")
        
    def get_anime_link(self, anime_name):
        """
        Restituisce il link dell'anime in base al nome (anche parziale) usando una regex.
        La ricerca è insensibile al maiuscolo/minuscolo.
        """
        # Pulisci il nome dell'anime per evitare errori con spazi e caratteri speciali
        anime_name = anime_name.strip().lower()  # Normalizza il nome dell'anime in minuscolo
        logger.debug(f"Normalized anime_name for search: '{anime_name}'")

        # Carica la lista degli anime dal config
        anime_list = self.get_anime()
        logger.debug(f"Loaded anime list: {anime_list}")

        # Itera sulla lista degli anime e cerca una corrispondenza parziale tramite regex
        for anime in anime_list:
            # Ottieni il nome dell'anime
            name = anime.get("name", "").lower()  # Converti il nome a minuscolo per una ricerca case-insensitive
            logger.debug(f"Checking anime: '{name}' against search term: '{anime_name}'")
            
            # Usa la regex per una ricerca parziale
            if re.search(anime_name, name, re.IGNORECASE):
                # Se viene trovato un match, restituisci il link
                link = anime.get("link", "Link non disponibile.")
                logger.debug(f"Match found. Anime: '{name}', Link: '{link}'")
                return link
        
        # Se non viene trovato alcun match, restituisci un messaggio di errore
        logger.debug(f"No match found for anime_name: '{anime_name}'")
        return "Anime non trovato."

