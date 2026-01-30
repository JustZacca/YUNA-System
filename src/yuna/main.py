#!/usr/bin/env python3
"""
YUNA System - Media Management Bot
Entry point for the application.
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from yuna.bot.kan import Kan


def main():
    """Main entry point."""
    bot = Kan()
    bot.launchBot()


if __name__ == "__main__":
    main()
