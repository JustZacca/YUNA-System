#!/usr/bin/env python3
"""
YUNA System - Entry point.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from yuna.bot import Kan


def main():
    bot = None
    try:
        bot = Kan()
        bot.launchBot()
    except KeyboardInterrupt:
        print("\nInterruzione rilevata. Arrivederci!")
        sys.exit(0)
    except Exception as e:
        print(f"Errore durante l'esecuzione del bot: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
