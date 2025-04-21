import os
import requests
import logging
from dotenv import load_dotenv
from colorama import Fore, Style, init
from color_utils import ColoredFormatter  # Importa la classe ColoredFormatter dal file color_utils

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

class JellyfinClient:
    def __init__(self):
        # Ottieni l'URL di Jellyfin e il token dall'ambiente
        load_dotenv()  # Carica il file .env nella environment
        self.jellyfin_url = os.getenv("JELLYFIN_URL")
        self.api_key = os.getenv("JELLYFIN_API_KEY")
        
        if not self.jellyfin_url or not self.api_key:
            logger.error("L'URL di Jellyfin o il token non sono configurati correttamente nelle variabili d'ambiente.")
            raise ValueError("L'URL di Jellyfin o il token non sono configurati correttamente nelle variabili d'ambiente.")

        # Impostiamo l'header per l'autenticazione
        self.headers = {
            "X-Emby-Token": self.api_key
        }

    def trigger_scan(self):
        """Triggera la scansione di tutte le librerie di Jellyfin."""
        url = f"{self.jellyfin_url}/Library/Refresh" 
        try:
            # Fai la richiesta POST per avviare la scansione delle librerie
            response = requests.post(url, headers=self.headers)

            # Log del corpo della risposta per il debug
            logger.debug(f"Status Code: {response.status_code}")
            logger.debug(f"Response Text: {response.text}")

            if response.status_code == 200 or response.status_code == 204:
                logger.info("Scansione delle librerie avviata con successo.")
            else:
                logger.error(f"Errore durante la scansione: {response.status_code}, {response.text}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Errore nella connessione a Jellyfin: {e}")

# Esegui il trigger della scansione
if __name__ == "__main__":
    jellyfin_client = JellyfinClient()
    jellyfin_client.trigger_scan()
