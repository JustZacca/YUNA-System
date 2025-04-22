from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes, CallbackQueryHandler
import miko
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
        self.SEARCH_NAME = range(1)

        # Anime ID map for inline buttons
        self.anime_id_map = {}
        self.anime_link = None
        self.miko_instance = miko.Miko()
        self.missing_episodes_list = []

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
        
    async def keyboard_stop_bot(self) -> None:
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
                self.miko_instance.setupAnimeFolder()
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
        
        commands = [
            "/aggiungi_anime",
            "/lista_anime",
            "/trova_anime",
            "/download_episodi",
            "/stop_bot",
            "/aggiorna_libreria"
        
        ]
        command_list = "\n".join([f"• {command}" for command in commands])

        await update.message.reply_text(
            f"Benvenuto in KAN, spero tu sia Nicholas o non sei il benvenuto. ⚡\n\n"
            f"Ecco cosa puoi fare:\n{command_list}"
        )

        commands = [
            ('start', 'Avvia il bot'),
            ('aggiungi_anime', 'Aggiungi un anime'),
            ('lista_anime', 'Visualizza la lista degli anime'),
            ('trova_anime', 'Trova un anime'),
            ('download_episodi', 'Scarica gli episodi'),
            ('stop_bot', 'Arresta il bot'),
            ('aggiorna_libreria', 'Aggiorna la libreria lanciando manualmente il job'),
        ]
        await context.bot.set_my_commands(commands)

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

    anime_id_map = {}

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

            if not len(self.missing_episodes_list) > 0:  # Check if the list is empty or zero
                self.logger.info("Nessun episodio da scaricare. Operazione annullata.")
                return False
            await self.miko_instance.downloadEpisodes(self.missing_episodes_list)
            self.logger.info("Download completato.")
            return True

        except Exception as e:
            self.logger.error(f"Errore download: {e}")

    async def check_new_episodes(self, context: ContextTypes.DEFAULT_TYPE):
        anime_list = self.airi.get_anime()
        
        for anime_data in anime_list:
            anime_name = anime_data.get('name')
            self.anime_link = anime_data.get('link')
            last_update = anime_data.get('last_update')
            episodi_scaricati = anime_data.get('episodi_scaricati', 0)
            numero_episodi = anime_data.get('numero_episodi', 0)

            if not (anime_name and self.anime_link and last_update):
                self.logger.warning(f"Dati mancanti in {anime_data}")
                continue

            last_update_date = parser.parse(last_update)
            days_since_update = (datetime.datetime.now() - last_update_date).days


            # Salta se aggiornato di recente
            isNuovoEpisodio = False
            if episodi_scaricati != numero_episodi:
                self.logger.info(f"{anime_name} non ha tutti gli episodi. Procedo con il controllo.")
                await context.bot.send_message(
                    chat_id=self.AUTHORIZED_USER_ID,
                    text=f"{anime_name} Non ha tutti gli episodi. 😅",
                    parse_mode="Markdown"
                )
            elif 7 <= days_since_update < 21:
                self.logger.info(f"Potrebbero esserci nuovi episodi per {anime_name}. Procedo con il controllo. 🤩")
                isNuovoEpisodio = True
            elif episodi_scaricati == numero_episodi:
                self.logger.info(f"{anime_name} è aggiornato. Salto controllo.")
                continue
            
            await self.miko_instance.loadAnime(self.anime_link)

            self.missing_episodes_list = await self.miko_instance.getMissingEpisodes()
            missing_episodes = len(self.missing_episodes_list) > 0

            if missing_episodes:
                if isNuovoEpisodio:
                    self.logger.info(f"Nuovi episodi trovati per {anime_name}. Inizio download...")
                    await context.bot.send_message(
                        chat_id=self.AUTHORIZED_USER_ID,
                        text=f"Nuovi episodi trovati per [{anime_name}]({self.airi.BASE_URL+self.anime_link}). Inizio download...",
                        parse_mode="Markdown"
                    )
                else:
                    self.logger.info(f"Mancano {len(self.missing_episodes_list)} episodi di {anime_name}. Inizio download...")
                    await context.bot.send_message(
                        chat_id=self.AUTHORIZED_USER_ID,
                        text=f"Mancano {len(self.missing_episodes_list)} episodi per {anime_name}. Inizio download...",
                        parse_mode="Markdown"
                    )
                await self.download_new_episodes(anime_name)
                await context.bot.send_message(
                    chat_id=self.AUTHORIZED_USER_ID,
                    text=f"🎬 Tutti gli episodi di {anime_name} sono stati scaricati.",
                    parse_mode="Markdown"
                )
            else:
                isNuovoEpisodio = False
                self.logger.info(f"Tutti gli episodi di {anime_name} sono aggiornati.")
        self.logger.info("Controllo episodi completato.")
        await context.bot.send_message(
            chat_id=self.AUTHORIZED_USER_ID,
            text="Controllo episodi completato. Tutti gli anime sono aggiornati. ✅"
        )


    async def download_new_episodes(self, anime_name: str):

        if self.anime_link == "Anime non trovato.":
            self.logger.error(f"Anime {anime_name} non trovato.")
            return
        self.logger.info(f"Scaricamento episodi per {anime_name}...")
        await self.download_task()  # Avvia il task in parallelo

        

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
        app = ApplicationBuilder().token(self.TOKEN).build()

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
       
        app.add_handler(CommandHandler("download_episodi", self.download_episodi))
        app.add_handler(CallbackQueryHandler(self.handle_anime_selection, pattern=r"^download_anime\|"))
        app.add_handler(CallbackQueryHandler(self.handle_inline_button, pattern="^anime_"))
        app.add_handler(CallbackQueryHandler(self.handle_search_decision, pattern="^(search_more|cancel_search)$"))
        app.add_handler(start_handler)
        app.add_handler(aggiungi_anime_handler)
        app.add_handler(stop_bot_handler)
        app.add_handler(conversation_handler)
        app.add_handler(trova_anime_conversation)
        app.add_handler(CallbackQueryHandler(self.handle_inline_button))
        app.add_handler(CallbackQueryHandler(self.handle_search_decision))
        app.add_handler(CommandHandler("lista_anime", self.lista_anime))
        aggiorna_libreria_handler = CommandHandler("aggiorna_libreria", self.aggiorna_libreria)
        app.add_handler(aggiorna_libreria_handler)
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

