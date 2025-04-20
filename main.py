# -*- coding: utf-8 -*-
import miko
import sys

def main():
    # Initialize the Miko object
    miko_instance = miko.Miko()

    # Start the Miko instance
    miko_instance.loadAnime('https://www.animeworld.ac/play/from-old-country-bumpkin-to-master-swordsman.LiRJ9/q6w9vs')
    miko_instance.setupAnimeFolder()
    miko_instance.downloadEpisodes(miko_instance.setupAnimeFolder())

if __name__ == "__main__":
    main()