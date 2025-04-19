import animeworld as aw

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
        Download a specific episode of the loaded anime.
        """
        if self.anime is None:
            print("No anime loaded.")
            return False
        for ep in self.anime.getEpisodes(episode_list):
            try:
                print(f"Downloading episode {ep.number}.")

                # One at a time...
                ep.download() 
                print(f"Download completed.")
            except Exception as e:
                print(f"Error downloading episode {ep.number}: {e}")
                return False
        return True