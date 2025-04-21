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

# Initialize colorama
init(autoreset=True)

# Configure logging
formatter = ColoredFormatter(fmt="\033[34m%(asctime)s\033[0m - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(handler)

# Initialize Airi
airi = Airi()
AUTHORIZED_USER_ID = airi.TELEGRAM_CHAT_ID

# States of conversation
LINK = 1
SEARCH_NAME = range(1)

# Function to start conversation with /aggiungi_anime
async def aggiungi_anime(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    logger.info(f"/aggiungi_anime from {user_id}")

    if user_id != AUTHORIZED_USER_ID:
        logger.warning(f"Unauthorized access: {user_id}")
        await update.message.reply_text("Non sei autorizzato a usare questo bot.")
        return ConversationHandler.END

    logger.info("Authorized. Waiting for link.")
    await update.message.reply_text("Inviami un link di AnimeWorld.")
    return LINK

# Function to stop the bot
async def stop_bot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    logger.info(f"/stop_bot from {user_id}")

    if user_id != AUTHORIZED_USER_ID:
        logger.warning(f"Unauthorized access: {user_id}")
        await update.message.reply_text("Non sei autorizzato a usare questo comando.")
        return

    logger.info("Authorized. Stopping bot.")
    await update.message.reply_text("Arresto del bot in corso...")
    os.kill(os.getpid(), signal.SIGINT)

# Function to receive link from AnimeWorld
async def receive_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    link = update.message.text
    logger.info(f"Link received: {link}")

    if 'animeworld' in link and link.startswith("https://"):
        try:
            miko_instance = miko.Miko()
            miko_instance.addAnime(link)
            logger.info(f"Anime added: {link}")
            await update.message.reply_text(f"Anime aggiunto con successo: {link} 🎉")
        except Exception as e:
            logger.error(f"Error adding anime: {e}")
            await update.message.reply_text("Si è verificato un errore nell'aggiunta dell'anime. Riprova più tardi. ❌")
    else:
        logger.warning("Invalid link.")
        await update.message.reply_text("Il link non sembra provenire da AnimeWorld o non è formattato correttamente. ⚠️")
    return ConversationHandler.END

# Function to manage /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    logger.info(f"/start from {user_id}")

    if user_id != AUTHORIZED_USER_ID:
        logger.warning(f"Unauthorized access: {user_id}")
        await update.message.reply_text("Non sei autorizzato a usare questo bot.")
        return

    logger.info("Authorized. Sending welcome message.")
    
    commands = [
        "/aggiungi_anime",
        "/lista_anime",
        "/trova_anime",
        "/download_episodi",
        "/stop_bot"
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
        ('stop_bot', 'Arresta il bot')
    ]
    await context.bot.set_my_commands(commands)

# Function to cancel the conversation
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info("Operation cancelled.")
    await update.message.reply_text("Operazione annullata. 👋")
    return ConversationHandler.END

async def lista_anime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id != AUTHORIZED_USER_ID:
        logger.warning(f"Unauthorized access: {user_id}")
        await update.message.reply_text("Non sei autorizzato a usare questo bot.")
        return

    anime_list = airi.get_anime()

    if not anime_list:
        await update.message.reply_text("📭 La lista degli anime è vuota.")
        return

    anime_text = ""
    for anime in anime_list:
        name = anime.get("name", "Sconosciuto")
        link = anime.get("link", "#")
        anime_text += f"• [{name}]({link})\n"

    await update.message.reply_text(f"📜 *Lista degli anime:*\n\n{anime_text}", parse_mode="Markdown")

async def trova_anime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id != AUTHORIZED_USER_ID:
        logger.warning(f"Unauthorized access: {user_id}")
        await update.message.reply_text("Non sei autorizzato a usare questo bot.")
        return

    await update.message.reply_text("Scrivi il nome dell'anime che vuoi cercare 🧐:")
    return SEARCH_NAME

anime_id_map = {}

async def receive_anime_name_for_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    anime_name = update.message.text.strip()
    logger.info(f"Anime searched: {anime_name}")
    
    miko_instance = miko.Miko()
    results = miko_instance.findAnime(anime_name)
    
    if not results:
        await update.message.reply_text(
            f"😕 Nessun risultato trovato per '{anime_name}'."
            " Prova a cercare un altro anime! 💡"
        )
        return SEARCH_NAME

    results_unique = {}
    for anime in results:
        results_unique[anime['link']] = anime
    
    limited_results = list(results_unique.values())[:3]

    keyboard = []
    anime_id_map.clear()
    for idx, anime in enumerate(limited_results):
        anime_id = f"anime_{idx}"
        anime_id_map[anime_id] = anime['link']
        keyboard.append([InlineKeyboardButton(anime['name'], callback_data=anime_id)])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Ecco i risultati trovati. Seleziona un anime per aggiungerlo 📲:",
        reply_markup=reply_markup
    )
    return ConversationHandler.END

async def handle_inline_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    anime_id = query.data
    if anime_id in anime_id_map:
        anime_link = anime_id_map[anime_id]
        logger.info(f"Selected anime link: {anime_link}")

        miko_instance = miko.Miko()
        try:
            miko_instance.addAnime(anime_link)
            
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
            logger.error(f"Error adding anime: {e}")
            await query.edit_message_text("❌ Si è verificato un errore nell'aggiungere l'anime.")
            return ConversationHandler.END
    else:
        await query.edit_message_text("❌ Selezione non valida.")
        return ConversationHandler.END

async def handle_search_decision(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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
        return SEARCH_NAME
    elif query.data == "cancel_search":
        await query.edit_message_text("👋 Ricerca anime terminata. Alla prossima!")
        return ConversationHandler.END



# Function to check and download missing episodes
async def download_episodi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id != AUTHORIZED_USER_ID:
        logger.warning(f"Accesso negato: {user_id}")
        await update.message.reply_text("Non sei autorizzato a usare questo bot.")
        return

    logger.info("Attendo il nome dell'anime per il download.")
    await update.message.reply_text("Per favore, inviami il nome dell'anime di cui vuoi scaricare gli episodi.")
    return LINK


async def receive_anime_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    anime_name = update.message.text.strip()

    logger.info(f"Nome anime per download ricevuto: {anime_name}")
    link = airi.get_anime_link(anime_name)

    if link == "Anime non trovato.":
        await update.message.reply_text("Non sono riuscito a trovare l'anime. Assicurati che il nome sia corretto.")
        return LINK  # This will make the bot ask for the anime name again

    else:
        miko_instance = miko.Miko()
        miko_instance.loadAnime(link)

        await update.message.reply_text("Scaricamento in corso...")

        if not await download_task(miko_instance):  # Check if the download task returns False
            await update.message.reply_text(f"🎬 Tutti gli episodi di {anime_name} sono già scaricati.")
            return ConversationHandler.END  # End the conversation if no episodes need to be downloaded
        await update.message.reply_text(f"🎬 Tutti gli episodi di {anime_name} sono stati scaricati ")
        return ConversationHandler.END  # End the conversation when the download starts


async def download_task(miko_instance: miko.Miko):
    try:
        anime_folder = miko_instance.setupAnimeFolder()
        if not anime_folder:  # Check if the list is empty or zero
            logger.info("Nessun episodio da scaricare. Operazione annullata.")
            return False
        await miko_instance.downloadEpisodes(anime_folder)
        logger.info("Download completato.")
        return True

    except Exception as e:
        logger.error(f"Errore download: {e}")

async def check_new_episodes(context: ContextTypes.DEFAULT_TYPE):
    miko_instance = miko.Miko()
    anime_list = airi.get_anime()
    
    for anime_data in anime_list:
        anime_name = anime_data.get('name')
        link = anime_data.get('link')
        last_update = anime_data.get('last_update')
        episodi_scaricati = anime_data.get('episodi_scaricati', 0)

        if not (anime_name and link and last_update):
            logger.warning(f"Dati mancanti in {anime_data}")
            continue

        last_update_date = parser.parse(last_update)
        days_since_update = (datetime.datetime.now() - last_update_date).days

        # Salta se aggiornato di recente
        if episodi_scaricati > 0 and days_since_update < 7:
            logger.info(f"L'ultimo aggiornamento di {anime_name} è {days_since_update} giorni fa. Salto controllo.")
            continue

        miko_instance.count_and_update_episodes(anime_name, episodi_scaricati)
        miko_instance.loadAnime(link)

        missing_episodes = miko_instance.check_missing_episodes()

        if missing_episodes:
            logger.info(f"Episodi mancanti per {anime_name}: {missing_episodes}")
            await context.bot.send_message(
                chat_id=AUTHORIZED_USER_ID,
                text=f"Episodi mancanti per {anime_name}. Inizio download..."
            )
            await download_new_episodes(anime_name)
            await context.bot.send_message(
                chat_id=AUTHORIZED_USER_ID,
                text=f"🎬 Tutti gli episodi di {anime_name} sono stati scaricati."
            )
        else:
            logger.info(f"Tutti gli episodi di {anime_name} sono aggiornati.")


async def download_new_episodes(anime_name: str):
    link = airi.get_anime_link(anime_name)

    if link == "Anime non trovato.":
        logger.error(f"Anime {anime_name} non trovato.")
        return

    miko_instance = miko.Miko()
    miko_instance.loadAnime(link)

    await download_task(miko_instance)  # Avvia il task in parallelo

    logger.info(f"Avviato download per {anime_name}.")


# Main function to run the bot
def main():
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    if not TOKEN:
        logger.error("Token non trovato.")
        return

    logger.info("Starting bot...")
    app = ApplicationBuilder().token(TOKEN).build()

    start_handler = CommandHandler("start", start)
    aggiungi_anime_handler = CommandHandler("aggiungi_anime", aggiungi_anime)
    stop_bot_handler = CommandHandler("stop_bot", stop_bot)

    conversation_handler = ConversationHandler(
        entry_points=[aggiungi_anime_handler],
        states={LINK: [MessageHandler(filters.TEXT, receive_link)]},
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    trova_anime_handler = CommandHandler("trova_anime", trova_anime)
    trova_anime_conversation = ConversationHandler(
    entry_points=[trova_anime_handler],
        states={
            SEARCH_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_anime_name_for_search)]
        },
        fallbacks=[],
    )
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("download_episodi", download_episodi)],
        states={
            LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_anime_name)],
        },
        fallbacks=[],
    ))

    app.add_handler(CallbackQueryHandler(handle_inline_button, pattern="^anime_"))
    app.add_handler(CallbackQueryHandler(handle_search_decision, pattern="^(search_more|cancel_search)$"))
    app.add_handler(start_handler)
    app.add_handler(aggiungi_anime_handler)
    app.add_handler(stop_bot_handler)
    app.add_handler(conversation_handler)
    app.add_handler(trova_anime_conversation)
    app.add_handler(CallbackQueryHandler(handle_inline_button))
    app.add_handler(CallbackQueryHandler(handle_search_decision))
    app.job_queue.run_repeating(
        check_new_episodes,
        interval=airi.UPDATE_TIME,  
        first=datetime.time(0, 0),
        job_kwargs={'max_instances': 3}
    )

    def signal_handler(sig, frame):
        logger.info("Arresto bot... Interruzione manuale.")
        app.stop()

    signal.signal(signal.SIGINT, signal_handler)
    
    logger.info("Bot in esecuzione.")
    
    app.run_polling()

if __name__ == "__main__":
    main()
