import miko

def main():
    # Initialize the Miko object
    miko_instance = miko.Miko()

    # Start the Miko instance
    miko_instance.loadAnime('https://www.animeworld.ac/play/from-old-country-bumpkin-to-master-swordsman.LiRJ9/q6w9vs')
    miko_instance.downloadEpisode([1])

main()