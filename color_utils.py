# color_utils.py
from colorama import Fore, Style
import logging

# Custom log formatter with colors
class ColoredFormatter(logging.Formatter):
    def format(self, record):
        # Define color for the log level
        level_color = {
            "DEBUG": Fore.BLUE,
            "INFO": Fore.GREEN,
            "WARNING": Fore.YELLOW,
            "ERROR": Fore.RED,
            "CRITICAL": Fore.MAGENTA,
        }.get(record.levelname, Fore.WHITE)

        # Define color for the timestamp (time)
        time_color = Fore.BLUE  # Timestamp in blue
        reset = Style.RESET_ALL

        # Apply color to log level
        record.levelname = f"{level_color}{record.levelname}{reset}"
        
        # Apply color to timestamp (asctime) using fmt
        record.asctime = f"{time_color}{self.formatTime(record)}{reset}"

        return super().format(record)
