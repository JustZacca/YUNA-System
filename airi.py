import json
from typing import List, Dict, Any

class AnimeLibrary:
    def __init__(self, file_path: str):
        """
        Inizializza la classe con il percorso del file JSON.
        :param file_path: Il percorso del file JSON.
        """
        self.file_path = file_path

    def carica(self) -> List[Dict[str, Any]]:
        """
        Carica il contenuto del file JSON in una lista di dizionari.
        :return: La lista di anime caricati.
        """
        try:
            with open(self.file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
            return data
        except FileNotFoundError:
            print(f"File non trovato: {self.file_path}")
            return []
        except json.JSONDecodeError:
            print("Errore nel decodificare il JSON.")
            return []

    def scrivi(self, data: List[Dict[str, Any]]) -> bool:
        """
        Scrive i dati nel file JSON.
        :param data: La lista di anime da scrivere nel file.
        :return: True se l'operazione è andata a buon fine, False altrimenti.
        """
        try:
            with open(self.file_path, 'w', encoding='utf-8') as file:
                json.dump(data, file, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"Errore nella scrittura del file JSON: {e}")
            return False

    def aggiungi_anime(self, anime: Dict[str, Any]) -> bool:
        """
        Aggiunge un nuovo anime al file JSON.
        :param anime: Il dizionario che rappresenta l'anime da aggiungere.
        :return: True se l'operazione è andata a buon fine, False altrimenti.
        """
        data = self.carica()  # Carica i dati esistenti
        if data is not None:
            data.append(anime)  # Aggiungi il nuovo anime
            return self.scrivi(data)
        return False

    def aggiorna_anime(self, link: str, updated_anime: Dict[str, Any]) -> bool:
        """
        Aggiorna un anime esistente nel file JSON in base al suo link.
        :param link: Il link dell'anime da aggiornare.
        :param updated_anime: I nuovi dati dell'anime.
        :return: True se l'operazione è andata a buon fine, False altrimenti.
        """
        data = self.carica()  # Carica i dati esistenti
        for i, anime in enumerate(data):
            if anime.get("link") == link:
                data[i] = updated_anime  # Aggiorna l'anime
                return self.scrivi(data)
        print(f"Anime con link {link} non trovato.")
        return False

    def leggi_anime(self) -> None:
        """
        Legge e stampa i dati di tutti gli anime nel file JSON.
        """
        data = self.carica()
        if data:
            for anime in data:
                print(f"Anime: {anime['anime']}, Link: {anime['link']}, Stato: {anime['stato']}")
        else:
            print("Nessun anime trovato.")
            
    def trova_link_per_nome(self, nome: str):
        """
        Restituisce il link dell'anime dato il suo nome.
        :param nome: Il nome dell'anime da cercare.
        :return: Il link dell'anime, o None se non trovato.
        """
        data = self.carica()  # Carica i dati esistenti
        for anime in data:
            if anime.get("anime").lower() == nome.lower():  # Confronta ignorando maiuscole/minuscole
                return anime.get("link")
        print(f"Anime con nome '{nome}' non trovato.")
        return None