from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes, CallbackQueryHandler
import miko
from miko import MikoSC
from airi import Airi
import os
import logging
from color_utils import ColoredFormatter
import signal
import asyncio
import datetime
from dateutil import parser
from colorama import init

class Kan:
    def __init__(self):
        # Configure logging
        formatter = ColoredFormatter(
            fmt="\033[34m%(asctime)s\033[0m - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(handler)

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
        self.miko_instance = miko.Miko()
        self.missing_episodes_list = []

        # Stato per menu rimozione anime
        self.selected_anime_for_removal = {}  # user_id -> set(anime_names)

        # StreamingCommunity extension
        self.miko_sc = MikoSC()
        self.sc_search_results = {}  # user_id -> list of MediaItem
        self.sc_current_series = {}  # user_id -> SeriesInfo
        self.selected_series_for_removal = {}  # user_id -> set(series_names)

        # Conversation states for SC
        self.SC_SEARCH = 10
        self.SC_SELECT_SEASON = 11

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

    # Function to manage /start command
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = update.message.from_user.id
        self.logger.info(f"/start from {user_id}")

        if user_id != self.AUTHORIZED_USER_ID:
            self.logger.warning(f"Unauthorized access: {user_id}")
            await update.message.reply_text("Non sei autorizzato a usare questo bot.")
            return

        self.logger.info("Authorized. Sending welcome message.")
        
        anime_commands = [
            "/aggiungi_anime - Aggiungi anime",
            "/lista_anime - Lista anime",
            "/trova_anime - Cerca anime",
            "/download_episodi - Scarica episodi",
            "/rimuovi_anime - Rimuovi anime",
            "/aggiorna_libreria - Aggiorna anime",
        ]
        sc_commands = [
            "/cerca_sc - Cerca film/serie TV",
            "/lista_serie - Lista serie TV",
            "/lista_film - Lista film",
            "/aggiorna_serie - Scarica nuovi episodi",
            "/rimuovi_serie - Rimuovi serie",
        ]
        system_commands = [
            "/stop_bot - Arresta il bot",
        ]

        await update.message.reply_text(
            f"Benvenuto in KAN, spero tu sia Nicholas o non sei il benvenuto.\n\n"
            f"*Anime (AnimeWorld):*\n" + "\n".join([f"  {c}" for c in anime_commands]) + "\n\n"
            f"*Film/Serie (StreamingCommunity):*\n" + "\n".join([f"  {c}" for c in sc_commands]) + "\n\n"
            f"*Sistema:*\n" + "\n".join([f"  {c}" for c in system_commands]),
            parse_mode="Markdown"
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
            await update.message.reply_text("Non sei autorizzato a usare questo bot.")
            return

        anime_list = self.airi.get_anime()

        if not anime_list:
            await update.message.reply_text("📭 La lista degli anime è vuota.")
            return

        anime_text = ""
        for anime in anime_list:
            name = anime.get("name", "Sconosciuto")
            link = anime.get("link", "#")
            anime_text += f"• [{name}]({link})\n"

        await update.message.reply_text(f"📜 *Lista degli anime:*\n\n{anime_text}", parse_mode="Markdown")

    async def trova_anime(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id

        if user_id != self.AUTHORIZED_USER_ID:
            self.logger.warning(f"Unauthorized access: {user_id}")
            await update.message.reply_text("Non sei autorizzato a usare questo bot.")
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
            await update.message.reply_text("Non sei autorizzato a usare questo bot.")
            return

        anime_list = self.airi.get_anime()
        if not anime_list:
            await update.message.reply_text("📭 La lista degli anime è vuota.")
            return

        keyboard = []

        for anime in anime_list:
            name = anime.get("name", "Sconosciuto")
            keyboard.append([InlineKeyboardButton(name, callback_data=f"download_anime|{name}")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Seleziona l'anime da scaricare:", reply_markup=reply_markup)



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
                await self._download_episodes_for_anime(missing_episodes_list, anime_name)
                await context.bot.send_message(
                    chat_id=self.AUTHORIZED_USER_ID,
                    text=f"Tutti gli episodi di {anime_name} sono stati scaricati.",
                    parse_mode="Markdown"
                )
            else:
                self.logger.info(f"Tutti gli episodi di {anime_name} sono aggiornati.")

        self.logger.info("Controllo episodi completato.")
        await context.bot.send_message(
            chat_id=self.AUTHORIZED_USER_ID,
            text="Controllo episodi completato. Tutti gli anime sono aggiornati."
        )

    async def _download_episodes_for_anime(self, episodes_list: list, anime_name: str) -> bool:
        """Helper method per scaricare episodi senza usare variabili di istanza condivise."""
        try:
            if not episodes_list:
                self.logger.info(f"Nessun episodio da scaricare per {anime_name}.")
                return False
            await self.miko_instance.downloadEpisodes(episodes_list)
            self.logger.info(f"Download completato per {anime_name}.")
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

        keyboard = []
        for anime in anime_list:
            name = anime.get("name", "Sconosciuto")
            is_selected = name in selected
            checkbox = "✅" if is_selected else "⬜"
            keyboard.append([InlineKeyboardButton(
                f"{checkbox} {name}",
                callback_data=f"removal_toggle|{name}"
            )])

        # Bottoni azione
        keyboard.append([
            InlineKeyboardButton("✅ Seleziona Tutti", callback_data="removal_select_all"),
            InlineKeyboardButton("⬜ Deseleziona", callback_data="removal_deselect_all")
        ])
        keyboard.append([
            InlineKeyboardButton("🗑️ Conferma Rimozione", callback_data="removal_confirm"),
            InlineKeyboardButton("❌ Annulla", callback_data="removal_cancel")
        ])

        return InlineKeyboardMarkup(keyboard)

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

            if season_str == "all":
                # Download all seasons
                await query.edit_message_text(
                    f"📥 Inizio download di tutte le stagioni di *{series_info.name}*...\n"
                    f"Questo potrebbe richiedere tempo.",
                    parse_mode="Markdown"
                )

                for season in series_info.seasons:
                    await context.bot.send_message(
                        chat_id=query.message.chat_id,
                        text=f"⏳ Scaricando Stagione {season.number}..."
                    )
                    results = await self.miko_sc.download_season(series_info.name, season.number)
                    successes = sum(1 for s, _ in results.values() if s)
                    await context.bot.send_message(
                        chat_id=query.message.chat_id,
                        text=f"✅ Stagione {season.number}: {successes}/{len(results)} episodi scaricati"
                    )

                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=f"🎉 Download di *{series_info.name}* completato!",
                    parse_mode="Markdown"
                )
            else:
                # Download single season
                season_num = int(season_str)
                await query.edit_message_text(
                    f"📥 Scaricando Stagione {season_num} di *{series_info.name}*...",
                    parse_mode="Markdown"
                )

                results = await self.miko_sc.download_season(series_info.name, season_num)
                successes = sum(1 for s, _ in results.values() if s)

                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=f"✅ Stagione {season_num}: {successes}/{len(results)} episodi scaricati"
                )

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

                await query.edit_message_text(
                    f"📥 Scaricando *{item.name}*...\n"
                    f"Questo potrebbe richiedere tempo.",
                    parse_mode="Markdown"
                )

                # Add to library
                self.miko_sc.add_film_to_library(item)

                # Download
                success, result = await self.miko_sc.download_film(item)

                if success:
                    await context.bot.send_message(
                        chat_id=query.message.chat_id,
                        text=f"✅ Film *{item.name}* scaricato con successo!",
                        parse_mode="Markdown"
                    )
                else:
                    await context.bot.send_message(
                        chat_id=query.message.chat_id,
                        text=f"❌ Errore nel download: {result}"
                    )

    async def lista_serie(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Command /lista_serie - List all tracked TV series."""
        user_id = update.effective_user.id

        if user_id != self.AUTHORIZED_USER_ID:
            await update.message.reply_text("Non sei autorizzato a usare questo bot.")
            return

        series_list = self.miko_sc.get_library_series()

        if not series_list:
            await update.message.reply_text("📭 Nessuna serie TV nella libreria.")
            return

        text = "📺 *Serie TV nella libreria:*\n\n"
        for series in series_list:
            name = series.get("name", "Sconosciuto")
            year = series.get("year", "")
            downloaded = series.get("episodi_scaricati", 0)
            total = series.get("numero_episodi", 0)
            text += f"• *{name}* ({year}) - {downloaded}/{total} episodi\n"

        await update.message.reply_text(text, parse_mode="Markdown")

    async def lista_film(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Command /lista_film - List all films."""
        user_id = update.effective_user.id

        if user_id != self.AUTHORIZED_USER_ID:
            await update.message.reply_text("Non sei autorizzato a usare questo bot.")
            return

        films_list = self.miko_sc.get_library_films()

        if not films_list:
            await update.message.reply_text("📭 Nessun film nella libreria.")
            return

        text = "🎬 *Film nella libreria:*\n\n"
        for film in films_list:
            name = film.get("name", "Sconosciuto")
            year = film.get("year", "")
            downloaded = "✅" if film.get("scaricato") else "⏳"
            text += f"• {downloaded} *{name}* ({year})\n"

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

        keyboard = []
        for series in series_list:
            name = series.get("name", "Sconosciuto")
            is_selected = name in selected
            checkbox = "✅" if is_selected else "⬜"
            keyboard.append([InlineKeyboardButton(
                f"{checkbox} {name}",
                callback_data=f"sc_removal_toggle|{name}"
            )])

        keyboard.append([
            InlineKeyboardButton("✅ Seleziona Tutti", callback_data="sc_removal_select_all"),
            InlineKeyboardButton("⬜ Deseleziona", callback_data="sc_removal_deselect_all")
        ])
        keyboard.append([
            InlineKeyboardButton("🗑️ Conferma Rimozione", callback_data="sc_removal_confirm"),
            InlineKeyboardButton("❌ Annulla", callback_data="sc_removal_cancel")
        ])

        return InlineKeyboardMarkup(keyboard)

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

        # Callback query handlers con pattern specifici (ordine importante: pattern specifici prima)
        app.add_handler(CallbackQueryHandler(self.handle_anime_selection, pattern=r"^download_anime\|"))
        app.add_handler(CallbackQueryHandler(self.handle_inline_button, pattern=r"^anime_"))
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
        # RIMOSSO: handler duplicati senza pattern che catturavano tutto
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
