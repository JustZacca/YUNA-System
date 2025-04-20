import animeworld as aw
import concurrent.futures

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
        Download specific episodes of the loaded anime in parallel using multithreading.
        """
        if self.anime is None:
            print("No anime loaded.")
            return False
        
        def download_single_episode(episode_number):
            try:
                # Recupera l'episodio tramite il numero
                episode = self.anime.getEpisode(episode_number)
                print(f"Downloading episode {episode.number}.")
                episode.download()
                print(f"Download completed for episode {episode.number}.")
            except Exception as e:
                print(f"Error downloading episode {episode_number}: {e}")
                return False
            return True

        # Use ThreadPoolExecutor to download episodes concurrently
        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = list(executor.map(download_single_episode, episode_list))

        # Check if all downloads were successful
        if all(results):
            return True
        else:
            print("Some episodes failed to download.")
            return False
