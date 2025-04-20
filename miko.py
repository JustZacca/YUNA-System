# -*- coding: utf-8 -*-
import animeworld as aw
import os

class Miko:
    def __init__(self):
        self.name = "Miko"
        self.description = "Media Indexing and Kapturing Operator (MIKO) is a tool for indexing and capturing media content."
        self.version = "1.0.0"
        self.author = "AnimeWorld"
        self.anime = None  # Variabile d’istanza per salvare l'anime
    
    def loadAnime(self, anime_link):
        """
        Load an anime by its link and save it to self.anime.
        """
        try:
            print(f"[INFO] Attempting to load anime from link: {anime_link}")
            self.anime = aw.Anime(anime_link)
            anime_name = self.anime.getName()
            print(f"[SUCCESS] Anime loaded successfully: {anime_name}")
            return self.anime
        except Exception as e:
            print(f"[ERROR] Failed to load anime from link '{anime_link}'. Error: {e}")
            self.anime = None
            return None
        
    def getEpisodes(self):
        """
        Get all episodes of the loaded anime.
        """
        if self.anime is None:
            print("[WARNING] No anime loaded. Please load an anime first.")
            return None
        try:
            print(f"[INFO] Fetching episodes for anime: {self.anime.getName()}")
            episodes = self.anime.getEpisodes()
            print(f"[SUCCESS] Retrieved {len(episodes)} episodes.")
            return episodes
        except Exception as e:
            print(f"[ERROR] Failed to fetch episodes for anime '{self.anime.getName()}'. Error: {e}")
            return None

    def downloadEpisode(self, episode_list):
        """
        Download specific episodes of the loaded anime and save them in a folder named after the anime.
        """
        if self.anime is None:
            print("[WARNING] No anime loaded. Please load an anime first.")
            return False
        
        anime_name = self.anime.getName()
        folder_path = f"./{anime_name}"
        
        # Create a folder for the anime if it doesn't exist
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"[INFO] Created folder for anime: {folder_path}")
        
        for ep in self.anime.getEpisodes(episode_list):
            try:
                print(f"[INFO] Starting download for episode {ep.number} of anime '{anime_name}'.")
                print(f"[DEBUG] Episode data: {ep.fileInfo}")  # Print episode data for debugging
                ep.download(title=f"{anime_name} - Episode {ep.number}", folder=folder_path)
                print(f"[SUCCESS] Download completed for episode {ep.number}. Saved to: {folder_path}")
            except Exception as e:
                print(f"[ERROR] Failed to download episode {ep.number} of anime '{anime_name}'. Error: {e}")
                print(f"[DEBUG] Episode data at failure: {ep}")  # Print episode data at failure
                return False
        print(f"[INFO] All requested episodes downloaded successfully for anime '{anime_name}'.")
        return True