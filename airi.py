from dotenv import load_dotenv
import os
import json
import logging
from colorama import Fore, Style, init
from color_utils import ColoredFormatter  # Importa la classe ColoredFormatter dal file color_utils
from colorama import init
import re
from urllib.parse import urlparse
import time

init(autoreset=True)

# Configura il logging con il custom formatter
formatter = ColoredFormatter(
    fmt="\033[34m%(asctime)s\033[0m - %(levelname)s - %(message)s",  # Make the time blue
    datefmt="%Y-%m-%d %H:%M:%S"  # Keep the date format
)
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(handler)
_config = None
_config_timestamp = 0
_config_ttl = 0.1  # 100 ms (puoi cambiare il valore)

class Airi:
    def __init__(self):
        load_dotenv()  # Carica il file .env nella environment

        self.destination_folder = os.getenv("DESTINATION_FOLDER")
        self.telegram_token = os.getenv("TELEGRAM_TOKEN")
        self.TELEGRAM_CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID"))
        self.UPDATE_TIME = int(os.getenv("UPDATE_TIME", 60))  # Default a 60 secondi se non impostato
        self.BASE_URL = os.getenv("BASE_URL", "https://www.animeworld.ac")        
        self.config_path = "config.json"
        self.config = self.load_or_create_config()
        
    def get_destination_folder(self):
        """
        Restituisce la cartella di destinazione per il download.
        """
        if not self.destination_folder:
            raise ValueError("La cartella di destinazione non è impostata nell'ambiente.")
        return self.destination_folder
    def load_or_create_config(self):
        """
        Carica il file config.json se esiste, altrimenti lo crea vuoto.
        In caso di errore, rinomina la vecchia configurazione e crea una nuova configurazione vuota.
        """
        global _config, _config_timestamp
        now = time.time()
        if _config is not None and (now - _config_timestamp) < _config_ttl:
            return _config

        if not os.path.exists(self.config_path):
            logger.info(f"{self.config_path} non trovato. Creazione di una configurazione vuota.")
            # Creazione di una configurazione vuota
            default_config = {
                "anime": []
            }
            with open(self.config_path, "w") as config_file:
                json.dump(default_config, config_file, indent=4)
            logger.info(f"{self.config_path} creato con lista anime vuota.")
            _config_timestamp = now
            return default_config

        # Se il file esiste, carica il contenuto
        try:
            with open(self.config_path, "r") as config_file:
                config = json.load(config_file)
                if not config:  # Controlla se il file è vuoto
                    raise ValueError("Il file config.json è vuoto.")
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Errore nella lettura di {self.config_path}: {e}. Rinominando il file e creando una nuova configurazione vuota.")
            # Rinomina il file corrotto
            corrupted_path = f"{self.config_path}.corrupted_{int(time.time())}"
            os.rename(self.config_path, corrupted_path)
            logger.info(f"File corrotto rinominato in {corrupted_path}. Backup creato con successo.")
            # Creazione di una configurazione vuota
            config = {
                "anime": []
            }
            with open(self.config_path, "w") as config_file:
                json.dump(config, config_file, indent=4)
            logger.info(f"{self.config_path} ripristinato con lista anime vuota.")
        else:
            logger.info(f"{self.config_path} caricato correttamente.")
        
        _config = config
        _config_timestamp = now
        return config
    
    def get_anime(self):
        """
        Ritorna la lista degli anime presenti nel config.
        """
        self.load_or_create_config()  # Assicurati che la configurazione sia caricata
        return self.config.get("anime", [])
    

    def add_anime(self, name, link, last_update, numero_episodi):
        """
        Aggiunge un nuovo anime al file config.json se non esiste già un anime con lo stesso link.
        """
        # Rimuove il base URL, mantiene solo il path (es: /play/nome-anime.xyz)
        parsed_link = urlparse(link).path

        # Controlla se esiste già un anime con lo stesso link
        for anime in self.config["anime"]:
            if anime.get("link") == parsed_link:
                logger.warning(f"L'anime con il link '{parsed_link}' esiste già. Aggiunta saltata.")
                return

        # Se non esiste, aggiungi il nuovo anime
        anime = {
            "name": name,
            "link": parsed_link,
            "last_update": last_update.strftime("%Y-%m-%d %H:%M:%S"),
            "episodi_scaricati": 0,
            "numero_episodi":numero_episodi
        }
        self.config["anime"].append(anime)

        # Scrittura nel file config.json
        with open(self.config_path, "w") as config_file:
            json.dump(self.config, config_file, indent=4)
        logger.info(f"Anime '{name}' aggiunto alla configurazione.")
        logger.debug(f"Configurazione aggiornata: {json.dumps(self.config, indent=4)}")
        self.invalidate_config()
        self.load_or_create_config()
        return
        
        
    def update_downloaded_episodes(self, name, episodi_scaricati):
        """
        Aggiorna la data di download dell'anime nel file config.json.
        """
        # Trova l'anime da aggiornare
        for anime in self.config["anime"]:
            if anime.get("name") == name:
                anime['episodi_scaricati'] = episodi_scaricati
                # Scrittura nel file config.json
                with open(self.config_path, "w") as config_file:
                    json.dump(self.config, config_file, indent=4)
                logger.info(f"Episodi scaricati aggiornati per l'anime '{name}'.")
                return
        logger.warning(f"L'anime '{name}' non trovato nella configurazione. Nessun aggiornamento effettuato.")
        self.invalidate_config()
        # Se non viene trovato alcun anime con quel nome, non fare nulla
    
    def update_last_update(self, name, last_update):
        """
        Aggiorna la data di last_update dell'anime nel file config.json.
        """
        # Trova l'anime da aggiornare
        for anime in self.config["anime"]:
            if anime.get("name") == name:
                anime['last_update'] = last_update.strftime("%Y-%m-%d %H:%M:%S")
                # Scrittura nel file config.json
                with open(self.config_path, "w") as config_file:
                    json.dump(self.config, config_file, indent=4)
                logger.info(f"Last update aggiornato per l'anime '{name}'.")
                return
        logger.warning(f"L'anime '{name}' non trovato nella configurazione. Nessun aggiornamento effettuato.")
        self.invalidate_config()
        # Se non viene trovato alcun anime con quel nome, non fare nulla
        
    def get_anime_link(self, anime_name):
        """
        Restituisce il link dell'anime in base al nome (anche parziale) usando una regex.
        La ricerca è insensibile al maiuscolo/minuscolo.
        """
        self.load_or_create_config()  # Assicurati che la configurazione sia caricata
        # Pulisci il nome dell'anime per evitare errori con spazi e caratteri speciali
        anime_name = anime_name.strip().lower()  # Normalizza il nome dell'anime in minuscolo
        logger.debug(f"Nome anime normalizzato per la ricerca: '{anime_name}'")

        # Carica la lista degli anime dal config
        anime_list = self.get_anime()
        logger.debug(f"Lista anime caricata: {anime_list}")

        # Itera sulla lista degli anime e cerca una corrispondenza parziale tramite regex
        for anime in anime_list:
            # Ottieni il nome dell'anime
            name = anime.get("name", "").lower()  # Converti il nome a minuscolo per una ricerca case-insensitive
            logger.debug(f"Controllando l'anime: '{name}' contro il termine di ricerca: '{anime_name}'")
            
            # Usa la regex per una ricerca parziale
            if re.search(anime_name, name, re.IGNORECASE):
                # Se viene trovato un match, restituisci il link
                link = anime.get("link", "Link non disponibile.")
                logger.debug(f"Match trovato. Anime: '{name}', Link: '{link}'")
                return link
        
        # Se non viene trovato alcun match, restituisci un messaggio di errore
        logger.debug(f"Nessun match trovato per anime_name: '{anime_name}'")
        return "Anime non trovato."

    def invalidate_config(self):
        global _config, _config_timestamp
        logger.info("Config invalidato")
        _config = None
        _config_timestamp = 0