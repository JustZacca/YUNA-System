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
            self.anime = aw.Anime(anime_link)
            print(f"Anime loaded: {self.anime.getName()}")
            return self.anime
        except Exception as e:
            print(f"Error loading anime: {e}")
            self.anime = None
            return None
        
    def getEpisodes(self):
        """
        Get all episodes of the loaded anime.
        """
        if self.anime is None:
            print("No anime loaded.")
            return None
        try:
            episodes = self.anime.getEpisodes()
            return episodes
        except Exception as e:
            print(f"Error getting episodes: {e}")
            return None

    def downloadEpisode(self, episode_list):
        """
        Download a specific episode of the loaded anime and save it in a folder named after the anime.
        """
        if self.anime is None:
            print("No anime loaded.")
            return False
        
        anime_name = self.anime.getName()
        folder_path = f"./{anime_name}"
        
        # Create a folder for the anime if it doesn't exist
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"Created folder: {folder_path}")
        
        for ep in self.anime.getEpisodes(episode_list):
            try:
                print(f"Downloading episode {ep.number}.")

                # Save the episode {in the anime folder
                ep.download(title=f"{self.anime.getName()} - Episode {ep.number}", folder=folder_path)
                print(f"Download completed for episode {ep.number}.")
            except Exception as e:
                print(f"Error downloading episode {ep.number}: {e}")
                return False
        return True