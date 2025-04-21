import os
import requests

class JellyfinClient:
    def __init__(self):
        # Ottieni l'URL di Jellyfin e il token dall'ambiente
        self.jellyfin_url = os.getenv("JELLYFIN_URL")
        self.api_key = os.getenv("JELLYFIN_API_KEY")
        
        if not self.jellyfin_url or not self.api_key:
            raise ValueError("L'URL di Jellyfin o il token non sono configurati correttamente nelle variabili d'ambiente.")

        # Impostiamo l'header per l'autenticazione
        self.headers = {
            "X-Emby-Token": self.api_key
        }

    def trigger_scan(self):
        """Triggera la scansione di tutte le librerie di Jellyfin."""
        url = f"{self.jellyfin_url}/Library/Scan"
        try:
            # Fai la richiesta POST per avviare la scansione delle librerie
            response = requests.post(url, headers=self.headers)

            if response.status_code == 200:
                print("Scansione delle librerie avviata con successo.")
                self.refresh_library()
            else:
                print(f"Errore durante la scansione: {response.status_code}, {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Errore nella connessione a Jellyfin: {e}")
            
    def refresh_library(self, library_id):
        url = f"{self.jellyfin_url}/Library/Refresh?Ids={library_id}"
        try:
            response = requests.post(url, headers=self.headers)
            if response.status_code == 200:
                print(f"Libreria {library_id} aggiornata con successo.")
            else:
                print(f"Errore durante l'aggiornamento della libreria: {response.status_code}, {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Errore nella connessione a Jellyfin: {e}")
