# -*- coding: utf-8 -*-
import miko
import sys

def main():
    # Controlla se è stato passato un argomento
    if len(sys.argv) < 2:
        print("Usage: python main.py <episode_number>")
        return

    try:
        # Leggi il numero dell'episodio dalla linea di comando
        episode_number = int(sys.argv[1])
    except ValueError:
        print("Please provide a valid episode number.")
        return

    # Initialize the Miko object
    miko_instance = miko.Miko()

    # Start the Miko instance
    miko_instance.loadAnime('https://www.animeworld.ac/play/from-old-country-bumpkin-to-master-swordsman.LiRJ9/q6w9vs')
    miko_instance.downloadEpisode([episode_number])

if __name__ == "__main__":
    main()