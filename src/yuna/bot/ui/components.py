"""
Telegram UI Helper Module for YUNA-System.
Provides consistent message formatting, keyboard builders, and UI utilities.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List, Optional, Tuple, Callable
from dataclasses import dataclass


# ==================== EMOJI CONSTANTS ====================

class Emoji:
    """Consistent emoji usage across the bot."""
    # Status
    SUCCESS = "✅"
    ERROR = "❌"
    WARNING = "⚠️"
    LOADING = "⏳"
    DONE = "🎉"

    # Content types
    ANIME = "🎌"
    SERIES = "📺"
    FILM = "🎬"
    DOWNLOAD = "📥"
    SEARCH = "🔍"

    # Actions
    ADD = "➕"
    REMOVE = "🗑️"
    REFRESH = "🔄"
    SETTINGS = "⚙️"
    INFO = "ℹ️"
    BACK = "◀️"
    NEXT = "▶️"
    CANCEL = "❌"

    # UI Elements
    CHECKBOX_ON = "✅"
    CHECKBOX_OFF = "⬜"
    BULLET = "•"
    ARROW = "→"
    EMPTY = "📭"
    LIST = "📋"
    CALENDAR = "📅"

    # Numbers for selection
    NUMBERS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]


# ==================== MESSAGE TEMPLATES ====================

class Messages:
    """Reusable message templates."""

    # Authorization
    UNAUTHORIZED = "Non sei autorizzato a usare questo bot."

    # Empty states
    NO_ANIME = f"{Emoji.EMPTY} Nessun anime nella libreria."
    NO_SERIES = f"{Emoji.EMPTY} Nessuna serie TV nella libreria."
    NO_FILMS = f"{Emoji.EMPTY} Nessun film nella libreria."
    NO_RESULTS = f"{Emoji.EMPTY} Nessun risultato trovato."

    # Success
    DOWNLOAD_STARTED = f"{Emoji.DOWNLOAD} Download avviato in background.\nControlla il messaggio di progresso."
    DOWNLOAD_COMPLETE = f"{Emoji.SUCCESS} Download completato!"
    OPERATION_SUCCESS = f"{Emoji.SUCCESS} Operazione completata."

    # Errors
    GENERIC_ERROR = f"{Emoji.ERROR} Si è verificato un errore."
    TIMEOUT_ERROR = f"{Emoji.ERROR} Operazione scaduta."

    # Instructions
    SEND_LINK = f"{Emoji.ANIME} Inviami il link di AnimeWorld per aggiungere l'anime."
    SEARCH_ANIME = f"{Emoji.SEARCH} Scrivi il nome dell'anime da cercare:"
    SEARCH_SC = f"{Emoji.SEARCH} Scrivi il nome del film o serie da cercare:"

    @staticmethod
    def list_header(title: str, emoji: str = "") -> str:
        """Create a formatted list header."""
        return f"{emoji} *{title}*\n" if emoji else f"*{title}*\n"

    @staticmethod
    def item_with_details(name: str, details: str = "", bullet: str = Emoji.BULLET) -> str:
        """Format a list item with optional details."""
        if details:
            return f"{bullet} *{name}* — {details}"
        return f"{bullet} *{name}*"


# ==================== KEYBOARD BUILDERS ====================

class KeyboardBuilder:
    """Fluent builder for inline keyboards."""

    def __init__(self):
        self.rows: List[List[InlineKeyboardButton]] = []
        self._current_row: List[InlineKeyboardButton] = []

    def button(self, text: str, callback_data: str) -> 'KeyboardBuilder':
        """Add a button to the current row."""
        self._current_row.append(InlineKeyboardButton(text, callback_data=callback_data))
        return self

    def url_button(self, text: str, url: str) -> 'KeyboardBuilder':
        """Add a URL button to the current row."""
        self._current_row.append(InlineKeyboardButton(text, url=url))
        return self

    def row(self) -> 'KeyboardBuilder':
        """End current row and start a new one."""
        if self._current_row:
            self.rows.append(self._current_row)
            self._current_row = []
        return self

    def buttons_per_row(self, items: List[Tuple[str, str]], per_row: int = 2) -> 'KeyboardBuilder':
        """Add multiple buttons with specified buttons per row."""
        for i, (text, callback_data) in enumerate(items):
            self.button(text, callback_data)
            if (i + 1) % per_row == 0:
                self.row()
        if self._current_row:
            self.row()
        return self

    def selection_list(self, items: List[Tuple[str, str, bool]],
                       prefix: str = "", use_numbers: bool = False) -> 'KeyboardBuilder':
        """
        Create a selection list with optional checkboxes.

        Args:
            items: List of (display_text, callback_data, is_selected)
            prefix: Optional prefix for callback_data
            use_numbers: Use number emoji instead of checkboxes
        """
        for i, (text, callback, selected) in enumerate(items):
            if use_numbers and i < len(Emoji.NUMBERS):
                icon = Emoji.NUMBERS[i]
            else:
                icon = Emoji.CHECKBOX_ON if selected else Emoji.CHECKBOX_OFF

            cb_data = f"{prefix}|{callback}" if prefix else callback
            self.button(f"{icon} {text}", cb_data).row()
        return self

    def action_row(self, actions: List[Tuple[str, str]]) -> 'KeyboardBuilder':
        """Add a row of action buttons."""
        for text, callback in actions:
            self.button(text, callback)
        return self.row()

    def confirm_cancel(self, confirm_text: str = "Conferma", cancel_text: str = "Annulla",
                       confirm_data: str = "confirm", cancel_data: str = "cancel") -> 'KeyboardBuilder':
        """Add confirm/cancel buttons."""
        return self.button(f"{Emoji.SUCCESS} {confirm_text}", confirm_data)\
                   .button(f"{Emoji.CANCEL} {cancel_text}", cancel_data)\
                   .row()

    def back_button(self, text: str = "Indietro", callback_data: str = "back") -> 'KeyboardBuilder':
        """Add a back button."""
        return self.button(f"{Emoji.BACK} {text}", callback_data).row()

    def navigation(self, current_page: int, total_pages: int,
                   prev_data: str = "prev", next_data: str = "next") -> 'KeyboardBuilder':
        """Add pagination buttons."""
        if current_page > 1:
            self.button(f"{Emoji.BACK} Precedente", prev_data)
        self.button(f"{current_page}/{total_pages}", "noop")
        if current_page < total_pages:
            self.button(f"Successivo {Emoji.NEXT}", next_data)
        return self.row()

    def build(self) -> InlineKeyboardMarkup:
        """Build and return the InlineKeyboardMarkup."""
        if self._current_row:
            self.rows.append(self._current_row)
        return InlineKeyboardMarkup(self.rows)


# ==================== MENU TEMPLATES ====================

class MenuTemplates:
    """Pre-built menu templates for common use cases."""

    @staticmethod
    def main_menu() -> InlineKeyboardMarkup:
        """Create the main menu keyboard with categories."""
        builder = KeyboardBuilder()

        # Category buttons
        builder.button(f"{Emoji.ANIME} Anime", "submenu_anime")
        builder.button(f"{Emoji.SERIES} Serie TV", "submenu_series")
        builder.button(f"{Emoji.FILM} Film", "submenu_film").row()

        # Quick actions
        builder.button(f"{Emoji.DOWNLOAD} Scarica Mancanti", "action_download_all")
        builder.button(f"{Emoji.REFRESH} Mostra Progresso", "action_show_progress").row()

        # Utility
        builder.button(f"{Emoji.REFRESH} Aggiorna Libreria", "action_refresh_library").row()

        return builder.build()

    @staticmethod
    def anime_submenu() -> InlineKeyboardMarkup:
        """Create anime submenu."""
        builder = KeyboardBuilder()

        builder.button(f"{Emoji.SEARCH} Cerca Anime", "anime_search")
        builder.button(f"{Emoji.LIST} Lista Anime", "anime_list").row()
        builder.button(f"{Emoji.DOWNLOAD} Scarica Episodi", "anime_download")
        builder.button(f"{Emoji.REMOVE} Rimuovi Anime", "anime_remove").row()
        builder.button(f"{Emoji.BACK} Menu Principale", "menu_main")

        return builder.build()

    @staticmethod
    def series_submenu() -> InlineKeyboardMarkup:
        """Create series submenu."""
        builder = KeyboardBuilder()

        builder.button(f"{Emoji.SEARCH} Cerca Serie", "series_search")
        builder.button(f"{Emoji.LIST} Lista Serie", "series_list").row()
        builder.button(f"{Emoji.DOWNLOAD} Aggiorna Serie", "series_update")
        builder.button(f"{Emoji.REMOVE} Rimuovi Serie", "series_remove").row()
        builder.button(f"{Emoji.BACK} Menu Principale", "menu_main")

        return builder.build()

    @staticmethod
    def film_submenu() -> InlineKeyboardMarkup:
        """Create film submenu."""
        builder = KeyboardBuilder()

        builder.button(f"{Emoji.SEARCH} Cerca Film", "film_search")
        builder.button(f"{Emoji.LIST} Lista Film", "film_list").row()
        builder.button(f"{Emoji.REMOVE} Rimuovi Film", "film_remove").row()
        builder.button(f"{Emoji.BACK} Menu Principale", "menu_main")

        return builder.build()

    @staticmethod
    def back_to_submenu(submenu_type: str) -> InlineKeyboardMarkup:
        """Create back button to a specific submenu."""
        builder = KeyboardBuilder()
        builder.button(f"{Emoji.BACK} Indietro", f"submenu_{submenu_type}")
        return builder.build()

    @staticmethod
    def back_to_main() -> InlineKeyboardMarkup:
        """Create back button to main menu."""
        builder = KeyboardBuilder()
        builder.button(f"{Emoji.BACK} Menu Principale", "menu_main")
        return builder.build()

    @staticmethod
    def selection_menu(items: List[Tuple[str, str]], selected: set = None,
                       select_all: bool = True, confirm: bool = True,
                       prefix: str = "select") -> InlineKeyboardMarkup:
        """
        Create a multi-select menu.

        Args:
            items: List of (display_text, item_id)
            selected: Set of selected item IDs
            select_all: Include select/deselect all buttons
            confirm: Include confirm/cancel buttons
            prefix: Callback data prefix
        """
        selected = selected or set()
        builder = KeyboardBuilder()

        # Selection items
        for text, item_id in items:
            is_selected = item_id in selected
            icon = Emoji.CHECKBOX_ON if is_selected else Emoji.CHECKBOX_OFF
            builder.button(f"{icon} {text}", f"{prefix}_toggle|{item_id}").row()

        # Select all / Deselect all
        if select_all:
            builder.button(f"{Emoji.CHECKBOX_ON} Seleziona Tutti", f"{prefix}_all")
            builder.button(f"{Emoji.CHECKBOX_OFF} Deseleziona", f"{prefix}_none").row()

        # Confirm / Cancel
        if confirm:
            builder.confirm_cancel(
                confirm_data=f"{prefix}_confirm",
                cancel_data=f"{prefix}_cancel"
            )

        return builder.build()

    @staticmethod
    def search_results(results: List[Tuple[str, str, str]],
                       prefix: str = "result",
                       show_type: bool = True) -> InlineKeyboardMarkup:
        """
        Create search results keyboard.

        Args:
            results: List of (name, item_id, type) where type is "anime", "series", or "film"
            prefix: Callback data prefix
            show_type: Show type emoji prefix
        """
        type_emoji = {
            "anime": Emoji.ANIME,
            "series": Emoji.SERIES,
            "film": Emoji.FILM,
            "tv": Emoji.SERIES
        }

        builder = KeyboardBuilder()
        for i, (name, item_id, item_type) in enumerate(results):
            emoji = type_emoji.get(item_type, "") if show_type else ""
            # Truncate long names
            display_name = name[:30] + "..." if len(name) > 30 else name
            text = f"{emoji} {display_name}" if emoji else display_name
            builder.button(text, f"{prefix}|{item_id}").row()

        builder.back_button(callback_data=f"{prefix}_cancel")
        return builder.build()

    @staticmethod
    def confirmation_dialog(message: str, confirm_text: str = "Conferma",
                            confirm_data: str = "confirm",
                            cancel_data: str = "cancel",
                            dangerous: bool = False) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Create a confirmation dialog.

        Returns:
            Tuple of (formatted_message, keyboard)
        """
        emoji = Emoji.WARNING if dangerous else Emoji.INFO
        formatted_msg = f"{emoji} {message}"

        builder = KeyboardBuilder()
        if dangerous:
            builder.button(f"{Emoji.REMOVE} {confirm_text}", confirm_data)
        else:
            builder.button(f"{Emoji.SUCCESS} {confirm_text}", confirm_data)
        builder.button(f"{Emoji.CANCEL} Annulla", cancel_data)

        return formatted_msg, builder.row().build()

    @staticmethod
    def season_selection(seasons: List[int], series_name: str,
                         prefix: str = "sc_season") -> InlineKeyboardMarkup:
        """Create season selection keyboard."""
        builder = KeyboardBuilder()

        # Season buttons (2 per row)
        season_items = [
            (f"Stagione {s}", f"{prefix}|{s}")
            for s in seasons
        ]
        builder.buttons_per_row(season_items, per_row=2)

        # Download all option
        builder.button(f"{Emoji.DOWNLOAD} Scarica Tutte", f"{prefix}|all").row()
        builder.back_button(callback_data=f"{prefix}|cancel")

        return builder.build()


# ==================== MESSAGE FORMATTERS ====================

class MessageFormatter:
    """Utilities for formatting messages."""

    @staticmethod
    def format_list(items: List[str], header: str = "", empty_message: str = None,
                    numbered: bool = False, emoji: str = Emoji.BULLET) -> str:
        """
        Format a list of items.

        Args:
            items: List of strings to display
            header: Optional header text
            empty_message: Message to show if list is empty
            numbered: Use numbered list instead of bullets
            emoji: Custom bullet emoji
        """
        if not items:
            return empty_message or f"{Emoji.EMPTY} Lista vuota."

        lines = []
        if header:
            lines.append(f"*{header}*\n")

        for i, item in enumerate(items):
            if numbered:
                prefix = Emoji.NUMBERS[i] if i < len(Emoji.NUMBERS) else f"{i+1}."
            else:
                prefix = emoji
            lines.append(f"{prefix} {item}")

        return "\n".join(lines)

    @staticmethod
    def format_anime_list(anime_list: List[dict], base_url: str = "") -> str:
        """Format anime list with links and episode counts."""
        if not anime_list:
            return Messages.NO_ANIME

        lines = [f"{Emoji.ANIME} *Anime nella libreria:*\n"]

        for anime in anime_list:
            name = anime.get("name", "Sconosciuto")
            downloaded = anime.get("episodi_scaricati", 0)
            total = anime.get("numero_episodi", "?")
            link = anime.get("link", "")

            if base_url and link:
                lines.append(f"{Emoji.BULLET} [{name}]({base_url}{link}) — {downloaded}/{total} ep")
            else:
                lines.append(f"{Emoji.BULLET} *{name}* — {downloaded}/{total} ep")

        return "\n".join(lines)

    @staticmethod
    def format_series_list(series_list: List[dict]) -> str:
        """Format series list with episode counts."""
        if not series_list:
            return Messages.NO_SERIES

        lines = [f"{Emoji.SERIES} *Serie TV nella libreria:*\n"]

        for series in series_list:
            name = series.get("name", "Sconosciuto")
            year = series.get("year", "")
            downloaded = series.get("episodi_scaricati", 0)
            total = series.get("numero_episodi", 0)

            year_str = f" ({year})" if year else ""
            lines.append(f"{Emoji.BULLET} *{name}*{year_str} — {downloaded}/{total} ep")

        return "\n".join(lines)

    @staticmethod
    def format_film_list(film_list: List[dict]) -> str:
        """Format film list with download status."""
        if not film_list:
            return Messages.NO_FILMS

        lines = [f"{Emoji.FILM} *Film nella libreria:*\n"]

        for film in film_list:
            name = film.get("name", "Sconosciuto")
            year = film.get("year", "")
            downloaded = film.get("scaricato", 0)

            year_str = f" ({year})" if year else ""
            status = Emoji.SUCCESS if downloaded else Emoji.LOADING
            lines.append(f"{status} *{name}*{year_str}")

        return "\n".join(lines)

    @staticmethod
    def welcome_message() -> Tuple[str, InlineKeyboardMarkup]:
        """Create welcome message with interactive menu."""
        msg = f"""
{Emoji.ANIME} *YUNA System - Media Manager*

Benvenuto! Seleziona una categoria:

{Emoji.ANIME} *Anime* — Gestisci anime da AnimeWorld
{Emoji.SERIES} *Serie TV* — Gestisci serie da StreamingCommunity
{Emoji.FILM} *Film* — Gestisci film da StreamingCommunity

{Emoji.DOWNLOAD} *Scarica Mancanti* — Scarica tutti i media mancanti
{Emoji.REFRESH} *Mostra Progresso* — Mostra la barra di progresso
"""
        keyboard = MenuTemplates.main_menu()
        return msg.strip(), keyboard

    @staticmethod
    def format_download_progress(downloads: List[dict]) -> str:
        """Format multiple download progress entries."""
        if not downloads:
            return f"{Emoji.DOWNLOAD} *Download Manager*\n\nNessun download attivo."

        lines = [f"{Emoji.DOWNLOAD} *Download in corso:*\n"]

        type_emoji = {"anime": Emoji.ANIME, "series": Emoji.SERIES, "film": Emoji.FILM}

        for dl in downloads:
            emoji = type_emoji.get(dl.get("type"), Emoji.DOWNLOAD)
            name = dl.get("name", "")
            progress = dl.get("progress", 0)
            details = dl.get("details", "")

            bar = MessageFormatter._progress_bar(progress)
            detail_str = f" ({details})" if details else ""

            lines.append(f"{emoji} {name}{detail_str}")
            lines.append(f"   `{bar}` {progress:.0%}")

        return "\n".join(lines)

    @staticmethod
    def _progress_bar(progress: float, width: int = 10) -> str:
        """Create ASCII progress bar."""
        filled = int(width * progress)
        return "█" * filled + "░" * (width - filled)
