# color_utils.py
from colorama import Fore, Style
import logging

# Custom log formatter with colors
class ColoredFormatter(logging.Formatter):
    def format(self, record):
        level_color = {
            "DEBUG": Fore.BLUE,
            "INFO": Fore.GREEN,
            "WARNING": Fore.YELLOW,
            "ERROR": Fore.RED,
            "CRITICAL": Fore.MAGENTA,
        }.get(record.levelname, Fore.WHITE)

        time_color = Fore.CYAN
        reset = Style.RESET_ALL

        record.levelname = f"{level_color}{record.levelname}{reset}"
        record.asctime = f"{time_color}{self.formatTime(record)}{reset}"
        return super().format(record)
