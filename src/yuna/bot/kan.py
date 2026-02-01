"""
KAN - Telegram Bot for YUNA System.
Handles user interactions for anime and media management.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ConversationHandler, ContextTypes, CallbackQueryHandler
)
import os
import signal
import asyncio
import datetime
from dateutil import parser
from colorama import init

from yuna.utils.logging import get_logger
from yuna.services.media_service import Miko, MikoSC
from yuna.providers.animeworld.client import Airi
from yuna.providers.anilist import AniListClient
from yuna.services.download_service import (
    download_manager, TelegramProgress, get_unified_tracker, UnifiedProgressTracker
)
from yuna.bot.ui.components import (
    Emoji, Messages, KeyboardBuilder, MenuTemplates, MessageFormatter
)

class Kan:
    def __init__(self):
        # Configure logging
        self.logger = get_logger(__name__)

        # Initialize colorama
        init(autoreset=True)

        # Initialize Airi
        self.airi = Airi()
        self.AUTHORIZED_USER_ID = self.airi.TELEGRAM_CHAT_ID

        # States of conversation
        self.LINK = 1
        self.SEARCH_NAME = 0  # Deve essere un intero, non range(1)

        # Anime ID map for inline buttons
        self.anime_id_map = {}
        self.anime_link = None
        self.miko_instance = Miko()
        self.missing_episodes_list = []

        # Stato per menu rimozione anime
        
        # AniList client
        self.anilist_client = AniListClient()
        self.selected_anime_for_removal = {}  # user_id -> set(anime_names)

        # StreamingCommunity extension
        self.miko_sc = MikoSC()
        self.sc_search_results = {}  # user_id -> list of MediaItem
        self.sc_current_series = {}  # user_id -> SeriesInfo
        self.selected_series_for_removal = {}  # user_id -> set(series_names)
        self.selected_films_for_removal = {}  # user_id -> set(film_names)

        # Conversation states for SC
        self.SC_SEARCH = 10
        self.SC_SELECT_SEASON = 11

        # Unified download tracker (single progress message for all downloads)
        self.unified_tracker: UnifiedProgressTracker = None
        self._download_counter = 0

    # Function to start conversation with /aggiungi_anime
    async def aggiungi_anime(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = update.message.from_user.id
        self.logger.info(f"/aggiungi_anime from {user_id}")

        if user_id != self.AUTHORIZED_USER_ID:
            self.logger.warning(f"Unauthorized access: {user_id}")
            await update.message.reply_text("Non sei autorizzato a usare questo bot.")
            return ConversationHandler.END

        self.logger.info("Authorized. Waiting for link.")
        await update.message.reply_text("Inviami un link di AnimeWorld.")
        return self.LINK

    # Function to stop the bot
    async def stop_bot(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = update.message.from_user.id
        self.logger.info(f"/stop_bot from {user_id}")

        if user_id != self.AUTHORIZED_USER_ID:
            self.logger.warning(f"Unauthorized access: {user_id}")
            await update.message.reply_text("Non sei autorizzato a usare questo comando.")
            return

        self.logger.info("Authorized. Stopping bot.")
        await update.message.reply_text("Arresto del bot in corso...")
        os.kill(os.getpid(), signal.SIGINT)
        
    def keyboard_stop_bot(self) -> None:
        """Metodo sincrono per fermare il bot da keyboard interrupt."""
        self.logger.info("Keyboard stop bot triggered.")
        os.kill(os.getpid(), signal.SIGINT)

    # Function to receive link from AnimeWorld
    async def receive_link(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        link = update.message.text
        self.logger.info(f"Link received: {link}")

        if 'animeworld' in link and link.startswith("https://"):
            try:
                name = await self.miko_instance.addAnime(link)
                self.logger.info(f"Anime added: {name}")
                await self.miko_instance.setupAnimeFolder()
                self.logger.info(f"Anime folder set up for: {name}")
                await update.message.reply_text(f"Anime aggiunto con successo: {name} 🎉")
            except Exception as e:
                self.logger.error(f"Error adding anime: {e}")
                await update.message.reply_text("Si è verificato un errore nell'aggiunta dell'anime. Riprova più tardi. ❌")
        else:
            self.logger.warning("Invalid link.")
            await update.message.reply_text("Il link non sembra provenire da AnimeWorld o non è formattato correttamente. ⚠️")
        return ConversationHandler.END

    # ==================== MENU SYSTEM ====================

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command - show main menu."""
        user_id = update.message.from_user.id
        self.logger.info(f"/start from {user_id}")

        if user_id != self.AUTHORIZED_USER_ID:
            self.logger.warning(f"Unauthorized access: {user_id}")
            await update.message.reply_text(Messages.UNAUTHORIZED)
            return

        # Clear any pending search state
        context.user_data["awaiting_search"] = None
        context.user_data["search_context"] = None

        await update.message.reply_text(
            self._main_menu_text(),
            parse_mode="Markdown",
            reply_markup=MenuTemplates.main_menu()
        )

    def _main_menu_text(self) -> str:
        """Get main menu text."""
        return f"""
{Emoji.ANIME} *YUNA System — Media Manager*

Seleziona una categoria:

{Emoji.ANIME} *Anime* — AnimeWorld
{Emoji.SERIES} *Serie TV* — StreamingCommunity
{Emoji.FILM} *Film* — StreamingCommunity
""".strip()

    def _back_to_menu_keyboard(self, submenu: str = None) -> InlineKeyboardMarkup:
        """Create a back button keyboard."""
        if submenu:
            return MenuTemplates.back_to_submenu(submenu)
        return MenuTemplates.back_to_main()

    async def _send_main_menu(self, target, edit: bool = False):
        """Send or edit the main menu message."""
        text = self._main_menu_text()
        keyboard = MenuTemplates.main_menu()

        if edit and hasattr(target, 'edit_message_text'):
            await target.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)
        else:
            await target.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)

    # ==================== MAIN MENU HANDLER ====================

    async def handle_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle main menu and submenu navigation."""
        query = update.callback_query
        await query.answer()

        user_id = query.from_user.id
        if user_id != self.AUTHORIZED_USER_ID:
            return

        action = query.data

        # Clear search state when navigating menus
        context.user_data["awaiting_search"] = None

        # Main menu
        if action == "menu_main":
            await query.edit_message_text(
                self._main_menu_text(),
                parse_mode="Markdown",
                reply_markup=MenuTemplates.main_menu()
            )
            return

        # ===== SUBMENUS =====
        if action == "submenu_anime":
            await query.edit_message_text(
                f"{Emoji.ANIME} *Menu Anime*\n\nGestione anime da AnimeWorld:",
                parse_mode="Markdown",
                reply_markup=MenuTemplates.anime_submenu()
            )
        elif action == "submenu_series":
            await query.edit_message_text(
                f"{Emoji.SERIES} *Menu Serie TV*\n\nGestione serie da StreamingCommunity:",
                parse_mode="Markdown",
                reply_markup=MenuTemplates.series_submenu()
            )
        elif action == "submenu_film":
            await query.edit_message_text(
                f"{Emoji.FILM} *Menu Film*\n\nGestione film da StreamingCommunity:",
                parse_mode="Markdown",
                reply_markup=MenuTemplates.film_submenu()
            )

        # ===== QUICK ACTIONS =====
        elif action == "action_download_all":
            await self._handle_download_all_missing(query, context)
        elif action == "action_show_progress":
            await self._handle_show_progress(query, context)
        elif action == "action_refresh_library":
            await query.edit_message_text(
                f"{Emoji.REFRESH} Aggiornamento libreria in corso...",
                parse_mode="Markdown",
                reply_markup=MenuTemplates.back_to_main()
            )
            asyncio.create_task(self._update_library_background(context.bot))

    # ==================== ANIME SUBMENU HANDLERS ====================

    async def handle_anime_submenu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle anime submenu actions."""
        query = update.callback_query
        await query.answer()

        user_id = query.from_user.id
        if user_id != self.AUTHORIZED_USER_ID:
            return

        action = query.data

        if action == "anime_search":
            context.user_data["awaiting_search"] = "anime"
            context.user_data["search_context"] = "anime"
            await query.edit_message_text(
                f"{Emoji.SEARCH} *Cerca Anime*\n\n"
                f"Scrivi il nome dell'anime da cercare:",
                parse_mode="Markdown",
                reply_markup=MenuTemplates.back_to_submenu("anime")
            )
        elif action == "anime_list":
            await self._show_anime_list(query)
        elif action == "anime_download":
            await self._show_download_menu(query)
        elif action == "anime_remove":
            await self._show_removal_menu(query, user_id)

    # ==================== SERIES SUBMENU HANDLERS ====================

    async def handle_series_submenu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle series submenu actions."""
        query = update.callback_query
        await query.answer()

        user_id = query.from_user.id
        if user_id != self.AUTHORIZED_USER_ID:
            return

        action = query.data

        if action == "series_search":
            context.user_data["awaiting_search"] = "series"
            context.user_data["search_context"] = "series"
            await query.edit_message_text(
                f"{Emoji.SEARCH} *Cerca Serie TV*\n\n"
                f"Scrivi il nome della serie da cercare:",
                parse_mode="Markdown",
                reply_markup=MenuTemplates.back_to_submenu("series")
            )
        elif action == "series_list":
            await self._show_series_list(query)
        elif action == "series_update":
            await query.edit_message_text(
                f"{Emoji.REFRESH} Controllo nuovi episodi...",
                parse_mode="Markdown",
                reply_markup=MenuTemplates.back_to_submenu("series")
            )
            asyncio.create_task(self._check_series_updates(query, context))
        elif action == "series_remove":
            await self._show_series_removal_menu(query, user_id)

    # ==================== FILM SUBMENU HANDLERS ====================

    async def handle_film_submenu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle film submenu actions."""
        query = update.callback_query
        await query.answer()

        user_id = query.from_user.id
        if user_id != self.AUTHORIZED_USER_ID:
            return

        action = query.data

        if action == "film_search":
            context.user_data["awaiting_search"] = "film"
            context.user_data["search_context"] = "film"
            await query.edit_message_text(
                f"{Emoji.SEARCH} *Cerca Film*\n\n"
                f"Scrivi il nome del film da cercare:",
                parse_mode="Markdown",
                reply_markup=MenuTemplates.back_to_submenu("film")
            )
        elif action == "film_list":
            await self._show_film_list(query)
        elif action == "film_remove":
            await self._show_film_removal_menu(query, user_id)

    # ==================== QUICK ACTIONS ====================

    async def _handle_download_all_missing(self, query, context):
        """Download all missing media."""
        await query.edit_message_text(
            f"{Emoji.DOWNLOAD} *Scarica Media Mancanti*\n\n"
            f"Avvio download di tutti i media mancanti...",
            parse_mode="Markdown",
            reply_markup=MenuTemplates.back_to_main()
        )
        asyncio.create_task(self._download_all_missing_background(query, context))

    async def _download_all_missing_background(self, query, context):
        """Background task to download all missing media."""
        try:
            bot = context.bot
            chat_id = query.message.chat_id

            # Initialize unified tracker if needed
            if not self.unified_tracker:
                msg = await bot.send_message(
                    chat_id=chat_id,
                    text=f"{Emoji.DOWNLOAD} *Download Manager*\n\nInizializzazione...",
                    parse_mode="Markdown"
                )
                self.unified_tracker = get_unified_tracker(bot, chat_id, msg.message_id)

            tracker = self.unified_tracker

            # Download missing anime episodes
            anime_list = self.airi.get_anime()
            for anime in anime_list:
                link = anime.get("link")
                name = anime.get("name")
                if link:
                    asyncio.create_task(self._download_anime_episodes_for_name(name, link, bot, tracker))

            # Download pending films
            pending_films = self.miko_sc.get_pending_films()
            for film in pending_films:
                # Create MediaItem-like object for pending films
                from yuna.providers.streamingcommunity.client import MediaItem
                item = MediaItem(
                    id=film.get("media_id", 0),
                    name=film.get("name"),
                    slug=film.get("slug", ""),
                    type="movie"
                )
                asyncio.create_task(self._download_film_background(bot, item, tracker))

            # Check series for new episodes (run as task like anime/films)
            asyncio.create_task(self._download_series_background(bot, chat_id, tracker))

            await bot.send_message(
                chat_id=chat_id,
                text=f"{Emoji.SUCCESS} Avvio download completato.\nControlla il progresso sopra.",
                reply_markup=MenuTemplates.back_to_main()
            )

        except Exception as e:
            self.logger.error(f"Error downloading all missing: {e}")

    async def _download_series_background(self, bot, chat_id, tracker):
        """Background task to download missing series episodes."""
        try:
            series_list = self.miko_sc.get_library_series()
            for series in series_list:
                name = series.get("name")
                if not name:
                    continue

                missing = self.miko_sc.get_missing_episodes(name)
                if missing:
                    total_missing = sum(len(eps) for eps in missing.values())
                    dl_id = f"series_{name}"

                    # Add to tracker
                    if tracker:
                        tracker.add_download(dl_id, f"{name} ({total_missing} ep)", "series")

                    # Create progress callback for tracker
                    async def series_progress(current, total, ep_name=""):
                        if tracker and total > 0:
                            progress = (current / total) * 100
                            tracker.update_progress(dl_id, progress)

                    await self.miko_sc.download_missing_episodes(name, series_progress)

                    if tracker:
                        tracker.complete_download(dl_id)

        except Exception as e:
            self.logger.error(f"Error downloading series: {e}")

    async def _download_anime_episodes_for_name(self, name: str, link: str, bot, tracker):
        """Download missing episodes for a single anime."""
        try:
            # Create a NEW Miko instance to avoid race conditions with parallel downloads
            from yuna.services.media_service import Miko
            miko = Miko()

            # Load the anime
            await miko.loadAnime(link)

            # Get missing episodes
            missing = await miko.getMissingEpisodes()
            if not missing:
                self.logger.info(f"No missing episodes for {name}")
                return

            dl_id = self._next_download_id("anime")
            tracker.add_download(dl_id, f"{name} ({len(missing)} ep)", "anime")

            async def anime_progress(ep_num, progress, done=False):
                # progress is 0.0-1.0, convert to percentage
                tracker.update_progress(dl_id, progress * 100)

            # Download
            await miko.downloadEpisodes(missing, progress_callback=anime_progress)

            tracker.complete_download(dl_id, success=True)
            self.logger.info(f"Anime download completed: {name}")

        except Exception as e:
            self.logger.error(f"Error downloading anime {name}: {e}")

    async def _handle_show_progress(self, query, context):
        """Show or resend the progress tracker message."""
        chat_id = query.message.chat_id
        bot = context.bot

        # Create new progress message
        msg = await bot.send_message(
            chat_id=chat_id,
            text=f"{Emoji.DOWNLOAD} *Download Manager*\n\n"
                 f"Nessun download attivo.\n\n"
                 f"Usa 'Scarica Mancanti' per avviare i download.",
            parse_mode="Markdown"
        )

        # Update unified tracker
        self.unified_tracker = get_unified_tracker(bot, chat_id, msg.message_id)

        await query.edit_message_text(
            f"{Emoji.SUCCESS} Messaggio progresso creato!",
            parse_mode="Markdown",
            reply_markup=MenuTemplates.back_to_main()
        )

    async def _check_series_updates(self, query, context):
        """Check for series updates in background."""
        try:
            updates = await self.miko_sc.check_and_download_new_episodes()
            if updates:
                msg = f"{Emoji.SUCCESS} Trovati nuovi episodi per:\n"
                for series_name, eps in updates.items():
                    msg += f"\n{Emoji.BULLET} {series_name}: {len(eps)} nuovi"
            else:
                msg = f"{Emoji.SUCCESS} Tutte le serie sono aggiornate!"

            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=msg,
                parse_mode="Markdown",
                reply_markup=MenuTemplates.back_to_submenu("series")
            )
        except Exception as e:
            self.logger.error(f"Error checking series: {e}")

    # ==================== SEARCH INPUT HANDLER ====================

    async def handle_menu_search_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle search input from menu (not conversation)."""
        user_id = update.effective_user.id
        if user_id != self.AUTHORIZED_USER_ID:
            return

        awaiting = context.user_data.get("awaiting_search")
        if not awaiting:
            return  # Not waiting for search input

        search_term = update.message.text.strip()
        context.user_data["awaiting_search"] = None  # Clear state
        search_context = context.user_data.get("search_context", awaiting)

        if awaiting == "anime":
            await self._do_anime_search(update, context, search_term)
        elif awaiting in ("sc", "series"):
            await self._do_sc_search(update, context, search_term, filter_type="tv")
        elif awaiting == "film":
            await self._do_sc_search(update, context, search_term, filter_type="movie")

    async def _do_anime_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE, search_term: str):
        """Perform anime search."""
        await update.message.reply_text(f"{Emoji.SEARCH} Cerco *{search_term}*...", parse_mode="Markdown")

        try:
            results = self.miko_instance.searchAnime(search_term)
            if not results:
                await update.message.reply_text(
                    f"{Emoji.EMPTY} Nessun risultato per '{search_term}'",
                    reply_markup=self._back_to_menu_keyboard()
                )
                return

            # Store results and show keyboard
            self.anime_id_map[update.effective_user.id] = {f"anime_{i}": anime for i, anime in enumerate(results[:5])}

            builder = KeyboardBuilder()
            for i, anime in enumerate(results[:5]):
                name = anime.get("name", "?")[:35]
                builder.button(f"{Emoji.ANIME} {name}", f"anime_{i}").row()
            builder.button(f"{Emoji.BACK} Menu Anime", "submenu_anime")

            await update.message.reply_text(
                f"{Emoji.SUCCESS} *Risultati per '{search_term}':*",
                parse_mode="Markdown",
                reply_markup=builder.build()
            )
        except Exception as e:
            self.logger.error(f"Anime search error: {e}")
            await update.message.reply_text(
                f"{Emoji.ERROR} Errore nella ricerca: {e}",
                reply_markup=self._back_to_menu_keyboard()
            )

    async def _do_sc_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                            search_term: str, filter_type: str = None):
        """Perform StreamingCommunity search.

        Args:
            filter_type: "tv" for series only, "movie" for films only, None for all
        """
        await update.message.reply_text(f"{Emoji.SEARCH} Cerco *{search_term}*...", parse_mode="Markdown")

        try:
            results = self.miko_sc.search(search_term)

            # Filter by type if specified
            if filter_type:
                results = [r for r in results if r.type == filter_type]

            if not results:
                await update.message.reply_text(
                    f"{Emoji.EMPTY} Nessun risultato per '{search_term}'",
                    reply_markup=self._back_to_menu_keyboard()
                )
                return

            # Store results
            user_id = update.effective_user.id
            self.sc_search_results[user_id] = results[:6]

            # Build keyboard
            builder = KeyboardBuilder()
            type_emoji = {"tv": Emoji.SERIES, "movie": Emoji.FILM}

            for i, item in enumerate(results[:6]):
                emoji = type_emoji.get(item.type, Emoji.FILM)
                name = item.name[:30] + "..." if len(item.name) > 30 else item.name
                year = f" ({item.year})" if item.year else ""
                builder.button(f"{emoji} {name}{year}", f"sc_select|{i}").row()

            # Back button based on context
            search_context = context.user_data.get("search_context", "")
            if search_context == "series":
                builder.button(f"{Emoji.BACK} Menu Serie", "submenu_series")
            elif search_context == "film":
                builder.button(f"{Emoji.BACK} Menu Film", "submenu_film")
            else:
                builder.button(f"{Emoji.BACK} Menu", "menu_main")

            await update.message.reply_text(
                f"{Emoji.SUCCESS} *Risultati per '{search_term}':*",
                parse_mode="Markdown",
                reply_markup=builder.build()
            )
        except Exception as e:
            self.logger.error(f"SC search error: {e}")
            await update.message.reply_text(
                f"{Emoji.ERROR} Errore nella ricerca: {e}",
                reply_markup=self._back_to_menu_keyboard()
            )

    async def _show_anime_list(self, query):
        """Show anime list from menu."""
        anime_list = self.airi.get_anime()
        text = MessageFormatter.format_anime_list(anime_list, self.airi.BASE_URL)
        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            disable_web_page_preview=True,
            reply_markup=MenuTemplates.back_to_submenu("anime")
        )

    async def _show_download_menu(self, query):
        """Show download selection menu."""
        anime_list = self.airi.get_anime()
        if not anime_list:
            await query.edit_message_text(
                Messages.NO_ANIME,
                reply_markup=MenuTemplates.back_to_submenu("anime")
            )
            return

        builder = KeyboardBuilder()
        for anime in anime_list:
            name = anime.get("name", "?")
            builder.button(f"{Emoji.ANIME} {name}", f"download_anime|{name}").row()
        builder.button(f"{Emoji.BACK} Menu Anime", "submenu_anime")

        await query.edit_message_text(
            f"{Emoji.DOWNLOAD} *Seleziona anime da scaricare:*",
            parse_mode="Markdown",
            reply_markup=builder.build()
        )

    async def _show_removal_menu(self, query, user_id):
        """Show removal selection menu."""
        self.selected_anime_for_removal[user_id] = set()
        keyboard = self._build_removal_keyboard(user_id)
        await query.edit_message_text(
            f"{Emoji.REMOVE} *Seleziona gli anime da rimuovere:*\n\n"
            f"_Clicca per selezionare/deselezionare_",
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    async def _show_series_list(self, query):
        """Show series list from menu."""
        series_list = self.miko_sc.get_library_series()
        text = MessageFormatter.format_series_list(series_list)
        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=MenuTemplates.back_to_submenu("series")
        )

    async def _show_film_list(self, query):
        """Show film list from menu."""
        film_list = self.miko_sc.get_library_films()
        text = MessageFormatter.format_film_list(film_list)
        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=MenuTemplates.back_to_submenu("film")
        )

    async def _show_series_removal_menu(self, query, user_id):
        """Show series removal menu (from submenu)."""
        series_list = self.miko_sc.get_library_series()
        if not series_list:
            await query.edit_message_text(
                Messages.NO_SERIES,
                reply_markup=MenuTemplates.back_to_submenu("series")
            )
            return

        self.selected_series_for_removal[user_id] = set()
        reply_markup = self._build_series_removal_keyboard(user_id)
        await query.edit_message_text(
            f"{Emoji.REMOVE} *Seleziona le serie da rimuovere:*\n\n"
            f"_Clicca per selezionare/deselezionare_",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

    async def _show_film_removal_menu(self, query, user_id):
        """Show film removal menu (from submenu)."""
        films_list = self.miko_sc.get_library_films()
        if not films_list:
            await query.edit_message_text(
                Messages.NO_FILMS,
                reply_markup=MenuTemplates.back_to_submenu("film")
            )
            return

        self.selected_films_for_removal[user_id] = set()
        reply_markup = self._build_film_removal_keyboard(user_id)
        await query.edit_message_text(
            f"{Emoji.REMOVE} *Seleziona i film da rimuovere:*\n\n"
            f"_Clicca per selezionare/deselezionare_",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

    async def _update_library_background(self, bot):
        """Background task to update library - checks episode counts for all anime."""
        try:
            anime_list = self.airi.get_anime()
            updated = 0
            for anime in anime_list:
                name = anime.get("name")
                link = anime.get("link")
                anilist_id = anime.get("anilist_id")
                if name and link:
                    try:
                        # Get available episodes from AnimeWorld
                        await self.miko_instance.loadAnime(link)
                        episodes = await self.miko_instance.getEpisodes()
                        if episodes:
                            self.airi.update_available_episodes(name, len(episodes))
                        
                        # Get total episodes from AniList if we have the ID
                        if anilist_id:
                            try:
                                anilist_data = self.anilist_client.get_anime(anilist_id)
                                if anilist_data and anilist_data.get("episodes"):
                                    self.airi.update_episodes_number(name, anilist_data["episodes"])
                            except Exception as e:
                                self.logger.warning(f"Could not fetch AniList data for {name}: {e}")
                        
                        updated += 1
                    except Exception as e:
                        self.logger.warning(f"Error updating {name}: {e}")
            await bot.send_message(
                self.AUTHORIZED_USER_ID,
                f"{Emoji.SUCCESS} Aggiornamento libreria completato.\n"
                f"Aggiornati {updated}/{len(anime_list)} anime.",
                reply_markup=self._back_to_menu_keyboard()
            )
        except Exception as e:
            self.logger.error(f"Library update error: {e}")
            await bot.send_message(
                self.AUTHORIZED_USER_ID,
                f"{Emoji.ERROR} Errore aggiornamento: {e}",
                reply_markup=self._back_to_menu_keyboard()
            )

    # Function to cancel the conversation
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        self.logger.info("Operation cancelled.")
        await update.message.reply_text("Operazione annullata. 👋")
        return ConversationHandler.END

    async def lista_anime(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id

        if user_id != self.AUTHORIZED_USER_ID:
            self.logger.warning(f"Unauthorized access: {user_id}")
            await update.message.reply_text(Messages.UNAUTHORIZED)
            return

        anime_list = self.airi.get_anime()
        text = MessageFormatter.format_anime_list(anime_list, self.airi.BASE_URL)
        await update.message.reply_text(text, parse_mode="Markdown", disable_web_page_preview=True)

    async def trova_anime(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id

        if user_id != self.AUTHORIZED_USER_ID:
            self.logger.warning(f"Unauthorized access: {user_id}")
            await update.message.reply_text(Messages.UNAUTHORIZED)
            return

        await update.message.reply_text("Scrivi il nome dell'anime che vuoi cercare 🧐:")
        return self.SEARCH_NAME

    # RIMOSSO: anime_id_map duplicato (gia definito in __init__)

    async def receive_anime_name_for_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        anime_name = update.message.text.strip()
        self.logger.info(f"Anime searched: {anime_name}")
        
        results = self.miko_instance.findAnime(anime_name)
        
        if not results:
            await update.message.reply_text(
                f"😕 Nessun risultato trovato per '{anime_name}'."
                " Prova a cercare un altro anime! 💡"
            )
            return self.SEARCH_NAME

        results_unique = {}
        for anime in results:
            results_unique[anime['link']] = anime
        
        limited_results = list(results_unique.values())[:3]

        keyboard = []
        self.anime_id_map.clear()
        for idx, anime in enumerate(limited_results):
            anime_id = f"anime_{idx}"
            self.anime_id_map[anime_id] = anime['link']
            keyboard.append([InlineKeyboardButton(anime['name'], callback_data=anime_id)])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "Ecco i risultati trovati. Seleziona un anime per aggiungerlo 📲:",
            reply_markup=reply_markup
        )
        return ConversationHandler.END

    async def handle_inline_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        await query.answer()

        anime_id = query.data
        if anime_id in self.anime_id_map:
            anime_link = self.anime_id_map[anime_id]
            self.logger.info(f"Selected anime link: {anime_link}")

            try:
                await self.miko_instance.addAnime(anime_link)
                
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Cerca un altro anime", callback_data="search_more")],
                    [InlineKeyboardButton("❌ Termina", callback_data="cancel_search")]
                ])

                await query.edit_message_text(
                    text="✅ Anime aggiunto con successo! 🎉\n\nVuoi cercare un altro anime?",
                    reply_markup=keyboard
                )
                return ConversationHandler.END

            except Exception as e:
                self.logger.error(f"Error adding anime: {e}")
                await query.edit_message_text("❌ Si è verificato un errore nell'aggiungere l'anime.")
                return ConversationHandler.END
        else:
            await query.edit_message_text("❌ Selezione non valida.")
            return ConversationHandler.END

    async def handle_search_decision(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        await query.answer()

        if query.data == "search_more":
            # Invia un messaggio per chiedere il nome del prossimo anime da cercare
            await context.bot.send_message(query.from_user.id, "✍️ Rilancia la ricerca /trova_anime")
            await context.bot.send_message(
                    chat_id=query.from_user.id,
                    text="/trova_anime"
                )
            # Ritorna allo stato SEARCH_NAME per fare la ricerca
            return self.SEARCH_NAME
        elif query.data == "cancel_search":
            await query.edit_message_text("👋 Ricerca anime terminata. Alla prossima!")
            return ConversationHandler.END



        # Function to check and download missing episodes
    async def download_episodi(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id

        if user_id != self.AUTHORIZED_USER_ID:
            await update.message.reply_text(Messages.UNAUTHORIZED)
            return

        anime_list = self.airi.get_anime()
        if not anime_list:
            await update.message.reply_text(Messages.NO_ANIME)
            return

        # Build keyboard with anime emoji
        builder = KeyboardBuilder()
        for anime in anime_list:
            name = anime.get("name", "Sconosciuto")
            builder.button(f"{Emoji.ANIME} {name}", f"download_anime|{name}").row()
        builder.back_button("Annulla", "download_cancel")

        await update.message.reply_text(
            f"{Emoji.DOWNLOAD} *Seleziona anime da scaricare:*",
            parse_mode="Markdown",
            reply_markup=builder.build()
        )



    async def handle_anime_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        user_id = query.from_user.id
        if user_id != self.AUTHORIZED_USER_ID:
            self.logger.warning(f"Accesso negato: {user_id}")
            await query.edit_message_text("Non sei autorizzato a usare questo bot.")
            return

        data = query.data
        if not data.startswith("download_anime|"):
            return

        anime_name = data.split("|", 1)[1]
        self.logger.info(f"Nome anime selezionato: {anime_name}")

        link = self.airi.get_anime_link(anime_name)
        if link == "Anime non trovato.":
            await query.edit_message_text("❌ Non sono riuscito a trovare l'anime.")
            logging.error(f"Anime '{anime_name}' non trovato.")
            return

        self.logger.info(f"Anime selezionato per il download: {link}")

        await self.miko_instance.loadAnime(link)
        self.missing_episodes_list = await self.miko_instance.getMissingEpisodes()

        if len(self.missing_episodes_list) == 0:
            await query.edit_message_text(f"✅ Tutti gli episodi di {self.miko_instance.anime_name} sono già scaricati. La serie è completa!")
            return

        if len(self.missing_episodes_list) == 1:
            await query.edit_message_text(f"🎬 Manca 1 episodio di {self.miko_instance.anime_name}. Inizio download...")
        else:
            await query.edit_message_text(f"🎬 Mancano {len(self.missing_episodes_list)} episodi di {self.miko_instance.anime_name}. Inizio download...")

        if not await self.download_task():
            await context.bot.send_message(chat_id=query.message.chat_id, text="❌ Si è verificato un errore durante il download degli episodi.")
            return

        await context.bot.send_message(chat_id=query.message.chat_id, text=f"✅ Tutti gli episodi di {self.miko_instance.anime_name} sono stati scaricati con successo!")




    async def download_task(self):
        try:
            if not self.missing_episodes_list:  # Check if the list is empty
                self.logger.info("Nessun episodio da scaricare. Operazione annullata.")
                return False
            await self.miko_instance.downloadEpisodes(self.missing_episodes_list)
            self.logger.info("Download completato.")
            return True

        except Exception as e:
            self.logger.error(f"Errore download: {e}")
            return False  # Bug fix: mancava il return in caso di eccezione

    async def check_new_episodes(self, context: ContextTypes.DEFAULT_TYPE):
        anime_list = self.airi.get_anime()

        for anime_data in anime_list:
            anime_name = anime_data.get('name')
            anime_link = anime_data.get('link')  # Variabile locale invece di self.anime_link
            last_update = anime_data.get('last_update')
            episodi_scaricati = anime_data.get('episodi_scaricati', 0)
            numero_episodi = anime_data.get('numero_episodi', 0)

            if not (anime_name and anime_link and last_update):
                self.logger.warning(f"Dati mancanti in {anime_data}")
                continue

            try:
                last_update_date = parser.parse(last_update)
                days_since_update = (datetime.datetime.now() - last_update_date).days
            except Exception as e:
                self.logger.error(f"Errore nel parsing della data per {anime_name}: {e}")
                continue

            # Salta se aggiornato di recente
            isNuovoEpisodio = False
            if episodi_scaricati != numero_episodi:
                self.logger.info(f"{anime_name} non ha tutti gli episodi. Procedo con il controllo.")
                await context.bot.send_message(
                    chat_id=self.AUTHORIZED_USER_ID,
                    text=f"{anime_name} Non ha tutti gli episodi.",
                    parse_mode="Markdown"
                )
            elif 7 <= days_since_update < 21:
                self.logger.info(f"Potrebbero esserci nuovi episodi per {anime_name}. Procedo con il controllo.")
                isNuovoEpisodio = True
            elif episodi_scaricati == numero_episodi:
                self.logger.info(f"{anime_name} è aggiornato. Salto controllo.")
                continue

            await self.miko_instance.loadAnime(anime_link)

            missing_episodes_list = await self.miko_instance.getMissingEpisodes()
            missing_episodes = len(missing_episodes_list) > 0

            if missing_episodes:
                if isNuovoEpisodio:
                    self.logger.info(f"Nuovi episodi trovati per {anime_name}. Inizio download...")
                    await context.bot.send_message(
                        chat_id=self.AUTHORIZED_USER_ID,
                        text=f"Nuovi episodi trovati per [{anime_name}]({self.airi.BASE_URL + anime_link}). Inizio download...",
                        parse_mode="Markdown"
                    )
                else:
                    self.logger.info(f"Mancano {len(missing_episodes_list)} episodi di {anime_name}. Inizio download...")
                    await context.bot.send_message(
                        chat_id=self.AUTHORIZED_USER_ID,
                        text=f"Mancano {len(missing_episodes_list)} episodi per {anime_name}. Inizio download...",
                        parse_mode="Markdown"
                    )
                # Passa direttamente la lista invece di usare variabile di istanza
                await self._download_episodes_for_anime(missing_episodes_list, anime_name, bot=context.bot)
                await context.bot.send_message(
                    chat_id=self.AUTHORIZED_USER_ID,
                    text=f"✅ Tutti gli episodi di {anime_name} sono stati scaricati.",
                    parse_mode="Markdown"
                )
            else:
                self.logger.info(f"Tutti gli episodi di {anime_name} sono aggiornati.")

        self.logger.info("Controllo episodi completato.")
        await context.bot.send_message(
            chat_id=self.AUTHORIZED_USER_ID,
            text="Controllo episodi completato. Tutti gli anime sono aggiornati."
        )

    async def _ensure_tracker(self, bot):
        """Ensure unified tracker is running."""
        if self.unified_tracker is None:
            self.unified_tracker = get_unified_tracker(bot, self.AUTHORIZED_USER_ID)
            await self.unified_tracker.start()
        return self.unified_tracker

    def _next_download_id(self, prefix: str = "dl") -> str:
        """Generate unique download ID."""
        self._download_counter += 1
        return f"{prefix}_{self._download_counter}"

    async def _download_episodes_for_anime(self, episodes_list: list, anime_name: str, bot=None) -> bool:
        """Helper method per scaricare episodi con tracking unificato."""
        try:
            if not episodes_list:
                self.logger.info(f"Nessun episodio da scaricare per {anime_name}.")
                return False

            # Setup unified tracker if bot available
            tracker = None
            download_ids = []
            if bot:
                tracker = await self._ensure_tracker(bot)
                for ep_num in episodes_list:
                    dl_id = self._next_download_id("anime")
                    tracker.add_download(dl_id, anime_name, "anime", f"Ep {ep_num}")
                    download_ids.append((dl_id, ep_num))

            # Start download with progress callback
            async def update_episode_progress(ep_num, progress, done=False):
                if tracker:
                    for dl_id, ep in download_ids:
                        if ep == ep_num:
                            if done:
                                tracker.complete_download(dl_id, success=True)
                            else:
                                tracker.update_progress(dl_id, progress)
                            break

            await self.miko_instance.downloadEpisodes(episodes_list, progress_callback=update_episode_progress)
            self.logger.info(f"Download completato per {anime_name}.")

            # Mark all as complete
            if tracker:
                for dl_id, _ in download_ids:
                    tracker.complete_download(dl_id, success=True)

            return True
        except Exception as e:
            self.logger.error(f"Errore download per {anime_name}: {e}")
            return False

    async def download_new_episodes(self, anime_name: str):
        """Metodo legacy - usa self.missing_episodes_list (deprecato per race conditions)."""
        if not self.missing_episodes_list:
            self.logger.error(f"Nessun episodio mancante per {anime_name}.")
            return
        self.logger.info(f"Scaricamento episodi per {anime_name}...")
        await self.download_task()

    # ==================== MENU RIMOZIONE ANIME ====================

    def _build_removal_keyboard(self, user_id: int) -> InlineKeyboardMarkup:
        """Costruisce la tastiera per il menu rimozione anime."""
        anime_list = self.airi.get_anime()
        selected = self.selected_anime_for_removal.get(user_id, set())

        builder = KeyboardBuilder()
        for anime in anime_list:
            name = anime.get("name", "Sconosciuto")
            is_selected = name in selected
            checkbox = Emoji.CHECKBOX_ON if is_selected else Emoji.CHECKBOX_OFF
            builder.button(f"{checkbox} {name}", f"removal_toggle|{name}").row()

        # Action buttons
        builder.button(f"{Emoji.CHECKBOX_ON} Seleziona Tutti", "removal_select_all")
        builder.button(f"{Emoji.CHECKBOX_OFF} Deseleziona", "removal_deselect_all").row()
        builder.button(f"{Emoji.REMOVE} Conferma", "removal_confirm")
        builder.button(f"{Emoji.CANCEL} Annulla", "removal_cancel").row()
        builder.button(f"{Emoji.BACK} Menu Anime", "submenu_anime")

        return builder.build()

    async def rimuovi_anime(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostra il menu per rimuovere anime dalla libreria."""
        user_id = update.effective_user.id

        if user_id != self.AUTHORIZED_USER_ID:
            self.logger.warning(f"Unauthorized access: {user_id}")
            await update.message.reply_text("Non sei autorizzato a usare questo bot.")
            return

        anime_list = self.airi.get_anime()
        if not anime_list:
            await update.message.reply_text("📭 La lista degli anime è vuota.")
            return

        # Inizializza selezione vuota per l'utente
        self.selected_anime_for_removal[user_id] = set()

        reply_markup = self._build_removal_keyboard(user_id)
        await update.message.reply_text(
            "🗑️ *Seleziona gli anime da rimuovere:*\n\n"
            "_Clicca su un anime per selezionarlo/deselezionarlo_",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

    async def handle_removal_toggle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gestisce il toggle di selezione di un singolo anime."""
        query = update.callback_query
        await query.answer()

        user_id = query.from_user.id
        if user_id != self.AUTHORIZED_USER_ID:
            return

        data = query.data

        if data.startswith("removal_toggle|"):
            anime_name = data.split("|", 1)[1]
            selected = self.selected_anime_for_removal.get(user_id, set())

            if anime_name in selected:
                selected.discard(anime_name)
            else:
                selected.add(anime_name)

            self.selected_anime_for_removal[user_id] = selected

        elif data == "removal_select_all":
            anime_list = self.airi.get_anime()
            self.selected_anime_for_removal[user_id] = {
                anime.get("name") for anime in anime_list
            }

        elif data == "removal_deselect_all":
            self.selected_anime_for_removal[user_id] = set()

        elif data == "removal_cancel":
            self.selected_anime_for_removal.pop(user_id, None)
            await query.edit_message_text("👋 Operazione annullata.")
            return

        elif data == "removal_confirm":
            await self._show_removal_confirmation(query, user_id)
            return

        # Aggiorna la tastiera
        reply_markup = self._build_removal_keyboard(user_id)
        await query.edit_message_reply_markup(reply_markup=reply_markup)

    async def _show_removal_confirmation(self, query, user_id: int):
        """Mostra la finestra di conferma finale."""
        selected = self.selected_anime_for_removal.get(user_id, set())

        if not selected:
            await query.answer("Nessun anime selezionato!", show_alert=True)
            return

        anime_list_text = "\n".join([f"  • {name}" for name in sorted(selected)])

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🗑️ SÌ, ELIMINA", callback_data="removal_execute"),
                InlineKeyboardButton("❌ Annulla", callback_data="removal_back")
            ]
        ])

        await query.edit_message_text(
            f"⚠️ *ATTENZIONE!*\n\n"
            f"Stai per eliminare definitivamente:\n{anime_list_text}\n\n"
            f"_Questa azione rimuoverà sia la configurazione che le cartelle dal disco._",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )

    async def handle_removal_execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Esegue la rimozione dopo la conferma."""
        query = update.callback_query
        await query.answer()

        user_id = query.from_user.id
        if user_id != self.AUTHORIZED_USER_ID:
            return

        data = query.data

        if data == "removal_back":
            # Torna al menu di selezione
            reply_markup = self._build_removal_keyboard(user_id)
            await query.edit_message_text(
                "🗑️ *Seleziona gli anime da rimuovere:*\n\n"
                "_Clicca su un anime per selezionarlo/deselezionarlo_",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            return

        if data == "removal_execute":
            selected = self.selected_anime_for_removal.get(user_id, set())

            if not selected:
                await query.edit_message_text("❌ Nessun anime selezionato.")
                return

            results = []
            for anime_name in selected:
                success, message = self.airi.remove_anime(anime_name)
                results.append(f"{'✅' if success else '❌'} {message}")

            # Pulisci la selezione
            self.selected_anime_for_removal.pop(user_id, None)

            result_text = "\n".join(results)
            await query.edit_message_text(
                f"🗑️ *Rimozione completata:*\n\n{result_text}",
                parse_mode="Markdown"
            )

    # ==================== ERROR HANDLER ====================

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gestisce tutti gli errori non catturati senza far crashare il bot."""
        self.logger.error(f"Errore nel bot: {context.error}", exc_info=context.error)

        # Notifica l'utente autorizzato
        try:
            error_message = f"⚠️ Errore nel bot:\n`{type(context.error).__name__}: {context.error}`"
            await context.bot.send_message(
                chat_id=self.AUTHORIZED_USER_ID,
                text=error_message,
                parse_mode="Markdown"
            )
        except Exception:
            pass  # Se anche la notifica fallisce, non crashare

    # ==================== STREAMINGCOMMUNITY COMMANDS ====================

    async def cerca_sc(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Command /cerca_sc - Search on StreamingCommunity."""
        user_id = update.effective_user.id

        if user_id != self.AUTHORIZED_USER_ID:
            await update.message.reply_text("Non sei autorizzato a usare questo bot.")
            return

        await update.message.reply_text(
            "Scrivi il nome del film o serie TV da cercare su StreamingCommunity:"
        )
        return self.SC_SEARCH

    async def receive_sc_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle search query for StreamingCommunity."""
        query = update.message.text.strip()
        user_id = update.effective_user.id

        self.logger.info(f"SC search: {query}")

        # Perform search
        results = self.miko_sc.search(query)

        if not results:
            await update.message.reply_text(
                f"Nessun risultato trovato per '{query}'."
            )
            return self.SC_SEARCH

        # Store results for user
        self.sc_search_results[user_id] = results[:6]  # Max 6 results

        # Build keyboard
        keyboard = []
        for idx, item in enumerate(self.sc_search_results[user_id]):
            type_emoji = "📺" if item.type == "tv" else "🎬"
            label = f"{type_emoji} {item.name}"
            if item.year:
                label += f" ({item.year})"
            keyboard.append([InlineKeyboardButton(
                label, callback_data=f"sc_select|{idx}"
            )])

        keyboard.append([InlineKeyboardButton("❌ Annulla", callback_data="sc_cancel")])

        await update.message.reply_text(
            f"Trovati {len(results)} risultati. Seleziona:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ConversationHandler.END

    async def handle_sc_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle selection from SC search results."""
        query = update.callback_query
        await query.answer()

        user_id = query.from_user.id
        if user_id != self.AUTHORIZED_USER_ID:
            return

        data = query.data

        if data == "sc_cancel":
            await query.edit_message_text("Ricerca annullata.")
            return

        if data.startswith("sc_select|"):
            idx = int(data.split("|")[1])
            results = self.sc_search_results.get(user_id, [])

            if 0 <= idx < len(results):
                item = results[idx]
                self.miko_sc.current_item = item

                if item.type == "tv":
                    # Show series options
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton("➕ Aggiungi alla libreria", callback_data=f"sc_add_series|{idx}")],
                        [InlineKeyboardButton("📥 Scarica episodi", callback_data=f"sc_download_series|{idx}")],
                        [InlineKeyboardButton("❌ Annulla", callback_data="sc_cancel")]
                    ])
                    await query.edit_message_text(
                        f"📺 *{item.name}* ({item.year})\n\nCosa vuoi fare?",
                        reply_markup=keyboard,
                        parse_mode="Markdown"
                    )
                else:
                    # Show movie options
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton("➕ Aggiungi e Scarica", callback_data=f"sc_download_film|{idx}")],
                        [InlineKeyboardButton("❌ Annulla", callback_data="sc_cancel")]
                    ])
                    await query.edit_message_text(
                        f"🎬 *{item.name}* ({item.year})\n\nCosa vuoi fare?",
                        reply_markup=keyboard,
                        parse_mode="Markdown"
                    )

    async def handle_sc_add_series(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle adding a series to library."""
        query = update.callback_query
        await query.answer()

        user_id = query.from_user.id
        if user_id != self.AUTHORIZED_USER_ID:
            return

        data = query.data

        if data.startswith("sc_add_series|"):
            idx = int(data.split("|")[1])
            results = self.sc_search_results.get(user_id, [])

            if 0 <= idx < len(results):
                item = results[idx]
                self.miko_sc.current_item = item

                await query.edit_message_text(f"Aggiungo '{item.name}' alla libreria...")

                success = self.miko_sc.add_series_to_library(item)

                if success:
                    await context.bot.send_message(
                        chat_id=query.message.chat_id,
                        text=f"✅ Serie '{item.name}' aggiunta alla libreria!"
                    )
                else:
                    await context.bot.send_message(
                        chat_id=query.message.chat_id,
                        text=f"❌ Errore nell'aggiunta di '{item.name}'. Potrebbe essere già presente."
                    )

    async def handle_sc_download_series(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle downloading series episodes."""
        query = update.callback_query
        await query.answer()

        user_id = query.from_user.id
        if user_id != self.AUTHORIZED_USER_ID:
            return

        data = query.data

        if data.startswith("sc_download_series|"):
            idx = int(data.split("|")[1])
            results = self.sc_search_results.get(user_id, [])

            if 0 <= idx < len(results):
                item = results[idx]
                self.miko_sc.current_item = item

                # Get series info
                info = self.miko_sc.get_series_info(item)
                if not info:
                    await query.edit_message_text("Errore nel recupero delle informazioni della serie.")
                    return

                self.sc_current_series[user_id] = info

                # Build season selection keyboard
                keyboard = []
                for season in info.seasons:
                    keyboard.append([InlineKeyboardButton(
                        f"Stagione {season.number}",
                        callback_data=f"sc_season|{season.number}"
                    )])

                keyboard.append([InlineKeyboardButton(
                    "📥 Scarica TUTTE le stagioni",
                    callback_data="sc_season|all"
                )])
                keyboard.append([InlineKeyboardButton("❌ Annulla", callback_data="sc_cancel")])

                await query.edit_message_text(
                    f"📺 *{info.name}*\n\n"
                    f"Seleziona la stagione da scaricare:",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="Markdown"
                )

    async def handle_sc_season_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle season selection for download."""
        query = update.callback_query
        await query.answer()

        user_id = query.from_user.id
        if user_id != self.AUTHORIZED_USER_ID:
            return

        data = query.data

        if data.startswith("sc_season|"):
            season_str = data.split("|")[1]
            series_info = self.sc_current_series.get(user_id)

            if not series_info:
                await query.edit_message_text("Errore: nessuna serie selezionata.")
                return

            # Add to library first if not present
            if not self.miko_sc.db.get_tv_by_name(series_info.name):
                self.miko_sc.add_series_to_library()

            chat_id = query.message.chat_id
            bot = context.bot

            if season_str == "all":
                # Download all seasons in background
                await query.edit_message_text(
                    f"📥 *{series_info.name}*\n"
                    f"Download di tutte le stagioni avviato in background.\n"
                    f"Il bot rimane disponibile per altri comandi.",
                    parse_mode="Markdown"
                )

                # Start background download task
                asyncio.create_task(
                    self._download_all_seasons_background(
                        bot, chat_id, series_info
                    )
                )
            else:
                # Download single season in background
                season_num = int(season_str)

                # Ensure tracker is running
                tracker = await self._ensure_tracker(bot)

                await query.edit_message_text(
                    f"✅ Download avviato in background.\n"
                    f"Controlla il messaggio di progresso.",
                    parse_mode="Markdown"
                )

                # Start background download task
                asyncio.create_task(
                    self._download_season_background(
                        bot, chat_id, series_info, season_num, tracker
                    )
                )

    async def _download_season_background(self, bot, chat_id, series_info, season_num, tracker):
        """Background task to download a season with unified tracker."""
        download_ids = {}
        results = {"success": 0, "failed": 0, "total": 0}

        async def episode_progress(completed, total, ep_num, success):
            results["total"] = total

            # Add download to tracker on first callback for this episode
            if ep_num not in download_ids:
                dl_id = self._next_download_id("series")
                download_ids[ep_num] = dl_id
                tracker.add_download(dl_id, series_info.name, "series", f"S{season_num:02d}E{ep_num:02d}")

            dl_id = download_ids[ep_num]

            if success:
                results["success"] += 1
                tracker.complete_download(dl_id, success=True)
            else:
                results["failed"] += 1
                tracker.complete_download(dl_id, success=False)

        try:
            download_results = await self.miko_sc.download_season(
                series_info.name, season_num,
                progress_callback=episode_progress
            )

            self.logger.info(f"Season download completed: {series_info.name} S{season_num} - {results['success']}/{results['total']}")

        except Exception as e:
            self.logger.error(f"Background download error: {e}")
            # Mark any active downloads as failed
            for dl_id in download_ids.values():
                tracker.complete_download(dl_id, success=False)

    async def _download_all_seasons_background(self, bot, chat_id, series_info):
        """Background task to download all seasons."""
        tracker = await self._ensure_tracker(bot)

        for season in series_info.seasons:
            await self._download_season_background(
                bot, chat_id, series_info, season.number, tracker
            )

        self.logger.info(f"All seasons completed: {series_info.name}")

    async def handle_sc_download_film(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle film download."""
        query = update.callback_query
        await query.answer()

        user_id = query.from_user.id
        if user_id != self.AUTHORIZED_USER_ID:
            return

        data = query.data

        if data.startswith("sc_download_film|"):
            idx = int(data.split("|")[1])
            results = self.sc_search_results.get(user_id, [])

            if 0 <= idx < len(results):
                item = results[idx]
                self.miko_sc.current_item = item

                bot = context.bot

                # Add to library
                self.miko_sc.add_film_to_library(item)

                # Ensure tracker is running
                tracker = await self._ensure_tracker(bot)

                await query.edit_message_text(
                    f"✅ Download avviato in background.\n"
                    f"Controlla il messaggio di progresso.",
                    parse_mode="Markdown"
                )

                # Start background download task
                asyncio.create_task(
                    self._download_film_background(bot, item, tracker)
                )

    async def _download_film_background(self, bot, item, tracker):
        """Background task to download a film with unified tracker."""
        dl_id = self._next_download_id("film")
        tracker.add_download(dl_id, item.name, "film")

        async def film_progress(prog, elapsed, size):
            tracker.update_progress(dl_id, prog)

        try:
            success, result = await self.miko_sc.download_film(
                item, progress_callback=film_progress
            )

            tracker.complete_download(dl_id, success=success)

            if success:
                self.logger.info(f"Film download completed: {item.name}")
            else:
                self.logger.error(f"Film download failed: {item.name} - {result}")

        except Exception as e:
            self.logger.error(f"Background film download error: {e}")
            tracker.complete_download(dl_id, success=False)
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=f"❌ Errore download: {e}",
                parse_mode="Markdown"
            )

    async def lista_serie(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Command /lista_serie - List all tracked TV series."""
        user_id = update.effective_user.id

        if user_id != self.AUTHORIZED_USER_ID:
            await update.message.reply_text(Messages.UNAUTHORIZED)
            return

        series_list = self.miko_sc.get_library_series()
        text = MessageFormatter.format_series_list(series_list)
        await update.message.reply_text(text, parse_mode="Markdown")

    async def lista_film(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Command /lista_film - List all films."""
        user_id = update.effective_user.id

        if user_id != self.AUTHORIZED_USER_ID:
            await update.message.reply_text(Messages.UNAUTHORIZED)
            return

        films_list = self.miko_sc.get_library_films()
        text = MessageFormatter.format_film_list(films_list)
        await update.message.reply_text(text, parse_mode="Markdown")

    async def aggiorna_serie(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Command /aggiorna_serie - Check and download new episodes for all series."""
        user_id = update.effective_user.id

        if user_id != self.AUTHORIZED_USER_ID:
            await update.message.reply_text("Non sei autorizzato a usare questo bot.")
            return

        await update.message.reply_text("🔍 Controllo nuovi episodi per tutte le serie...")

        results = await self.miko_sc.check_and_download_new_episodes()

        if not results:
            await update.message.reply_text("✅ Tutte le serie sono aggiornate!")
            return

        # Build report
        text = "📥 *Download completato:*\n\n"
        for series_name, seasons in results.items():
            total = sum(len(eps) for eps in seasons.values())
            text += f"• *{series_name}*: {total} episodi scaricati\n"

        await update.message.reply_text(text, parse_mode="Markdown")

    # ==================== REMOVAL MENU FOR SERIES ====================

    def _build_series_removal_keyboard(self, user_id: int) -> InlineKeyboardMarkup:
        """Build keyboard for series removal menu."""
        series_list = self.miko_sc.get_library_series()
        selected = self.selected_series_for_removal.get(user_id, set())

        builder = KeyboardBuilder()
        for series in series_list:
            name = series.get("name", "Sconosciuto")
            is_selected = name in selected
            checkbox = Emoji.CHECKBOX_ON if is_selected else Emoji.CHECKBOX_OFF
            builder.button(f"{checkbox} {name}", f"sc_removal_toggle|{name}").row()

        builder.button(f"{Emoji.CHECKBOX_ON} Seleziona Tutti", "sc_removal_select_all")
        builder.button(f"{Emoji.CHECKBOX_OFF} Deseleziona", "sc_removal_deselect_all").row()
        builder.button(f"{Emoji.REMOVE} Conferma", "sc_removal_confirm")
        builder.button(f"{Emoji.CANCEL} Annulla", "sc_removal_cancel").row()
        builder.button(f"{Emoji.BACK} Menu Serie", "submenu_series")

        return builder.build()

    async def rimuovi_serie(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Command /rimuovi_serie - Remove series from library."""
        user_id = update.effective_user.id

        if user_id != self.AUTHORIZED_USER_ID:
            await update.message.reply_text("Non sei autorizzato a usare questo bot.")
            return

        series_list = self.miko_sc.get_library_series()
        if not series_list:
            await update.message.reply_text("📭 Nessuna serie nella libreria.")
            return

        self.selected_series_for_removal[user_id] = set()

        reply_markup = self._build_series_removal_keyboard(user_id)
        await update.message.reply_text(
            "🗑️ *Seleziona le serie da rimuovere:*",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

    async def handle_sc_removal_toggle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle series removal toggle."""
        query = update.callback_query
        await query.answer()

        user_id = query.from_user.id
        if user_id != self.AUTHORIZED_USER_ID:
            return

        data = query.data

        if data.startswith("sc_removal_toggle|"):
            name = data.split("|", 1)[1]
            selected = self.selected_series_for_removal.get(user_id, set())

            if name in selected:
                selected.discard(name)
            else:
                selected.add(name)

            self.selected_series_for_removal[user_id] = selected

        elif data == "sc_removal_select_all":
            series_list = self.miko_sc.get_library_series()
            self.selected_series_for_removal[user_id] = {
                s.get("name") for s in series_list
            }

        elif data == "sc_removal_deselect_all":
            self.selected_series_for_removal[user_id] = set()

        elif data == "sc_removal_cancel":
            self.selected_series_for_removal.pop(user_id, None)
            await query.edit_message_text("👋 Operazione annullata.")
            return

        elif data == "sc_removal_confirm":
            selected = self.selected_series_for_removal.get(user_id, set())
            if not selected:
                await query.answer("Nessuna serie selezionata!", show_alert=True)
                return

            # Execute removal
            results = []
            for name in selected:
                success = self.miko_sc.remove_series(name)
                results.append(f"{'✅' if success else '❌'} {name}")

            self.selected_series_for_removal.pop(user_id, None)

            await query.edit_message_text(
                f"🗑️ *Rimozione completata:*\n\n" + "\n".join(results),
                parse_mode="Markdown"
            )
            return

        # Update keyboard
        reply_markup = self._build_series_removal_keyboard(user_id)
        await query.edit_message_reply_markup(reply_markup=reply_markup)

    # ==================== FILM REMOVAL ====================

    async def rimuovi_film(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Command /rimuovi_film - Remove films from library."""
        user_id = update.effective_user.id

        if user_id != self.AUTHORIZED_USER_ID:
            await update.message.reply_text(Messages.UNAUTHORIZED)
            return

        films_list = self.miko_sc.get_library_films()

        if not films_list:
            await update.message.reply_text(Messages.NO_FILMS)
            return

        # Initialize selection
        if user_id not in self.selected_films_for_removal:
            self.selected_films_for_removal[user_id] = set()

        reply_markup = self._build_film_removal_keyboard(user_id)
        await update.message.reply_text(
            f"{Emoji.REMOVE} *Seleziona i film da rimuovere:*\n\n"
            f"_Clicca per selezionare/deselezionare_",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

    def _build_film_removal_keyboard(self, user_id: int) -> InlineKeyboardMarkup:
        """Build keyboard for film removal selection."""
        films_list = self.miko_sc.get_library_films()
        selected = self.selected_films_for_removal.get(user_id, set())

        builder = KeyboardBuilder()
        for film in films_list:
            name = film.get("name", "?")
            is_selected = name in selected
            icon = Emoji.CHECKBOX_ON if is_selected else Emoji.CHECKBOX_OFF
            builder.button(f"{icon} {name}", f"film_removal_toggle|{name}").row()

        # Action buttons
        builder.button(f"{Emoji.CHECKBOX_ON} Seleziona Tutti", "film_removal_select_all")
        builder.button(f"{Emoji.CHECKBOX_OFF} Deseleziona", "film_removal_deselect_all").row()
        builder.button(f"{Emoji.REMOVE} Conferma", "film_removal_confirm")
        builder.button(f"{Emoji.CANCEL} Annulla", "film_removal_cancel").row()
        builder.button(f"{Emoji.BACK} Menu Film", "submenu_film")

        return builder.build()

    async def handle_film_removal_toggle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle film removal toggle."""
        query = update.callback_query
        await query.answer()

        user_id = query.from_user.id
        if user_id != self.AUTHORIZED_USER_ID:
            return

        data = query.data

        if data.startswith("film_removal_toggle|"):
            name = data.split("|", 1)[1]
            selected = self.selected_films_for_removal.get(user_id, set())

            if name in selected:
                selected.discard(name)
            else:
                selected.add(name)

            self.selected_films_for_removal[user_id] = selected

        elif data == "film_removal_select_all":
            films_list = self.miko_sc.get_library_films()
            self.selected_films_for_removal[user_id] = {
                f.get("name") for f in films_list
            }

        elif data == "film_removal_deselect_all":
            self.selected_films_for_removal[user_id] = set()

        elif data == "film_removal_cancel":
            self.selected_films_for_removal.pop(user_id, None)
            await query.edit_message_text(f"{Emoji.BACK} Operazione annullata.")
            return

        elif data == "film_removal_confirm":
            selected = self.selected_films_for_removal.get(user_id, set())
            if not selected:
                await query.answer("Nessun film selezionato!", show_alert=True)
                return

            # Execute removal
            results = []
            for name in selected:
                success = self.miko_sc.remove_film(name)
                results.append(f"{Emoji.SUCCESS if success else Emoji.ERROR} {name}")

            self.selected_films_for_removal.pop(user_id, None)

            await query.edit_message_text(
                f"{Emoji.REMOVE} *Rimozione completata:*\n\n" + "\n".join(results),
                parse_mode="Markdown"
            )
            return

        # Update keyboard
        reply_markup = self._build_film_removal_keyboard(user_id)
        await query.edit_message_reply_markup(reply_markup=reply_markup)

    async def aggiorna_libreria(self,update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = update.message.from_user.id
        self.logger.info(f"/aggiorna_libreria from {user_id}")

        if user_id != self.AUTHORIZED_USER_ID:
            self.logger.warning(f"Unauthorized access: {user_id}")
            await update.message.reply_text("Non sei autorizzato a usare questo comando.")
            return

        self.logger.info("Authorized. Triggering job for updating library...")
        
        # Triggera manualmente il job check_new_episodes
        context.application.job_queue.run_once(self.check_new_episodes, 0, job_kwargs={'max_instances': 3})

        await update.message.reply_text("Aggiornamento della libreria avviato! 🚀")


    # Main function to run the bot
    def launchBot(self):
        self.TOKEN = os.getenv("TELEGRAM_TOKEN")
        if not self.TOKEN:
            self.logger.error("Token non trovato.")
            return

        self.logger.info("Starting bot...")

        # Callback per registrare i comandi all'avvio
        async def post_init(application):
            commands = [
                ('start', 'Avvia il bot'),
                # Anime commands
                ('aggiungi_anime', 'Aggiungi un anime'),
                ('lista_anime', 'Visualizza la lista degli anime'),
                ('trova_anime', 'Trova un anime'),
                ('download_episodi', 'Scarica gli episodi anime'),
                ('rimuovi_anime', 'Rimuovi anime dalla libreria'),
                ('aggiorna_libreria', 'Aggiorna la libreria anime'),
                # StreamingCommunity commands
                ('cerca_sc', 'Cerca film/serie su SC'),
                ('lista_serie', 'Lista serie TV'),
                ('lista_film', 'Lista film'),
                ('aggiorna_serie', 'Scarica nuovi episodi serie'),
                ('rimuovi_serie', 'Rimuovi serie dalla libreria'),
                ('rimuovi_film', 'Rimuovi film dalla libreria'),
                # System
                ('stop_bot', 'Arresta il bot'),
            ]
            await application.bot.set_my_commands(commands)
            self.logger.info("Comandi del bot registrati.")

        app = ApplicationBuilder().token(self.TOKEN).post_init(post_init).build()

        start_handler = CommandHandler("start", self.start)
        aggiungi_anime_handler = CommandHandler("aggiungi_anime", self.aggiungi_anime)
        stop_bot_handler = CommandHandler("stop_bot", self.stop_bot)

        conversation_handler = ConversationHandler(
            entry_points=[aggiungi_anime_handler],
            states={self.LINK: [MessageHandler(filters.TEXT, self.receive_link)]},
            fallbacks=[CommandHandler("cancel", self.cancel)],
        )

        trova_anime_handler = CommandHandler("trova_anime", self.trova_anime)
        trova_anime_conversation = ConversationHandler(
        entry_points=[trova_anime_handler],
            states={
                self.SEARCH_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.receive_anime_name_for_search)]
            },
            fallbacks=[],
        )
       
        # Command handlers (evita duplicati)
        app.add_handler(start_handler)
        app.add_handler(stop_bot_handler)
        app.add_handler(CommandHandler("lista_anime", self.lista_anime))
        app.add_handler(CommandHandler("download_episodi", self.download_episodi))
        app.add_handler(CommandHandler("rimuovi_anime", self.rimuovi_anime))

        # StreamingCommunity command handlers
        app.add_handler(CommandHandler("lista_serie", self.lista_serie))
        app.add_handler(CommandHandler("lista_film", self.lista_film))
        app.add_handler(CommandHandler("aggiorna_serie", self.aggiorna_serie))
        app.add_handler(CommandHandler("rimuovi_serie", self.rimuovi_serie))

        # Conversation handlers
        app.add_handler(conversation_handler)
        app.add_handler(trova_anime_conversation)

        # StreamingCommunity search conversation
        cerca_sc_conversation = ConversationHandler(
            entry_points=[CommandHandler("cerca_sc", self.cerca_sc)],
            states={
                self.SC_SEARCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.receive_sc_search)]
            },
            fallbacks=[CommandHandler("cancel", self.cancel)],
        )
        app.add_handler(cerca_sc_conversation)

        # Main menu and submenu handlers
        app.add_handler(CallbackQueryHandler(self.handle_main_menu, pattern=r"^(menu_|submenu_|action_)"))

        # Anime submenu handlers
        app.add_handler(CallbackQueryHandler(self.handle_anime_submenu, pattern=r"^anime_(search|list|download|remove)$"))

        # Series submenu handlers
        app.add_handler(CallbackQueryHandler(self.handle_series_submenu, pattern=r"^series_(search|list|update|remove)$"))

        # Film submenu handlers
        app.add_handler(CallbackQueryHandler(self.handle_film_submenu, pattern=r"^film_(search|list|remove)$"))

        # Callback query handlers con pattern specifici (ordine importante: pattern specifici prima)
        app.add_handler(CallbackQueryHandler(self.handle_anime_selection, pattern=r"^download_anime\|"))
        app.add_handler(CallbackQueryHandler(self.handle_inline_button, pattern=r"^anime_\d+$"))
        app.add_handler(CallbackQueryHandler(self.handle_search_decision, pattern=r"^(search_more|cancel_search)$"))
        # Handler per menu rimozione anime
        app.add_handler(CallbackQueryHandler(self.handle_removal_toggle, pattern=r"^removal_(toggle\||select_all|deselect_all|cancel|confirm)"))
        app.add_handler(CallbackQueryHandler(self.handle_removal_execute, pattern=r"^removal_(execute|back)$"))

        # StreamingCommunity callback handlers
        app.add_handler(CallbackQueryHandler(self.handle_sc_selection, pattern=r"^sc_select\|"))
        app.add_handler(CallbackQueryHandler(self.handle_sc_selection, pattern=r"^sc_cancel$"))
        app.add_handler(CallbackQueryHandler(self.handle_sc_add_series, pattern=r"^sc_add_series\|"))
        app.add_handler(CallbackQueryHandler(self.handle_sc_download_series, pattern=r"^sc_download_series\|"))
        app.add_handler(CallbackQueryHandler(self.handle_sc_season_selection, pattern=r"^sc_season\|"))
        app.add_handler(CallbackQueryHandler(self.handle_sc_download_film, pattern=r"^sc_download_film\|"))
        app.add_handler(CallbackQueryHandler(self.handle_sc_removal_toggle, pattern=r"^sc_removal_"))
        app.add_handler(CallbackQueryHandler(self.handle_film_removal_toggle, pattern=r"^film_removal_"))

        # Film removal command
        app.add_handler(CommandHandler("rimuovi_film", self.rimuovi_film))

        # Menu search input handler (lower priority, group 1)
        app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            self.handle_menu_search_input
        ), group=1)

        aggiorna_libreria_handler = CommandHandler("aggiorna_libreria", self.aggiorna_libreria)
        app.add_handler(aggiorna_libreria_handler)

        # Global error handler
        app.add_error_handler(self.error_handler)
        app.job_queue.run_repeating(
            self.check_new_episodes,
            interval=self.airi.UPDATE_TIME,  
            first=datetime.time(0, 0),
            job_kwargs={'max_instances': 3}
        )

        def signal_handler(sig, frame):
            self.logger.info("Arresto bot... Interruzione manuale.")
            app.stop()

        signal.signal(signal.SIGINT, signal_handler)
        
        self.logger.info("Bot in esecuzione.")
        
        app.run_polling()
