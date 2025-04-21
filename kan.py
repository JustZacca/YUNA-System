from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes
import miko
from airi import Airi
import os
import logging
from color_utils import ColoredFormatter  # Importa la classe ColoredFormatter dal file color_utils
import signal
import asyncio
import datetime
from dateutil import parser

# Inizializza colorama
from colorama import init
init(autoreset=True)

# Configura il logging con il custom formatter
formatter = ColoredFormatter(
    fmt="\033[34m%(asctime)s\033[0m - %(levelname)s - %(message)s",  # Make the time blue
    datefmt="%Y-%m-%d %H:%M:%S"  # Keep the date format
)
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(handler)

# Inizializza Airi
airi = Airi()

# Il tuo chat ID
AUTHORIZED_USER_ID = airi.TELEGRAM_CHAT_ID  # Sostituisci con il tuo chat ID

# Stati della conversazione
LINK = 1

# Funzione per avviare la conversazione con /aggiungi_anime
async def aggiungi_anime(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    logger.info(f"/aggiungi_anime da {user_id}")

    if user_id != AUTHORIZED_USER_ID:
        logger.warning(f"Accesso negato: {user_id}")
        await update.message.reply_text("Non sei autorizzato a usare questo bot.")
        return ConversationHandler.END

    logger.info("Autorizzato. Attendo link.")
    await update.message.reply_text("Per favore, inviami un link di AnimeWorld.")
    return LINK

async def stop_bot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    logger.info(f"/stop_bot da {user_id}")

    if user_id != AUTHORIZED_USER_ID:
        logger.warning(f"Accesso negato: {user_id}")
        await update.message.reply_text("Non sei autorizzato a usare questo comando.")
        return

    logger.info("Autorizzato. Arresto bot.")
    await update.message.reply_text("Arresto del bot in corso...")
    os.kill(os.getpid(), signal.SIGINT)
    
# Funzione per ricevere il link di AnimeWorld
async def receive_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    link = update.message.text
    logger.info(f"Link: {link}")

    if 'animeworld' in link and link.startswith("https://"):
        try:
            miko_instance = miko.Miko()
            miko_instance.addAnime(link)
            logger.info(f"Anime aggiunto: {link}")
            await update.message.reply_text(f"Anime aggiunto con successo: {link}")
        except Exception as e:
            logger.error(f"Errore aggiunta anime: {e}")
            await update.message.reply_text("Si è verificato un errore nell'aggiunta dell'anime. Riprova più tardi.")
    else:
        logger.warning("Link non valido.")
        await update.message.reply_text("Il link non sembra provenire da AnimeWorld o non è formattato correttamente.")
    return ConversationHandler.END

# Funzione per gestire il comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    logger.info(f"/start da {user_id}")

    if user_id != AUTHORIZED_USER_ID:
        logger.warning(f"Accesso negato: {user_id}")
        await update.message.reply_text("Non sei autorizzato a usare questo bot.")
        return

    logger.info("Autorizzato. Inviando messaggio di benvenuto.")
    
    commands = [
        "/aggiungi_anime",
        "/lista_anime",
        "/trova_anime",
        "/download_episodi",
        "/stop_bot"
    ]
    command_list = "\n".join([f"• {command}" for command in commands])

    await update.message.reply_text(
        f"Benvenuto in KAN, spero tu sia Nicholas o non sei il benvenuto.\n\n"
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

# Funzione per annullare la conversazione
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info("Operazione annullata.")
    await update.message.reply_text("Operazione annullata.")
    return ConversationHandler.END

async def lista_anime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id != AUTHORIZED_USER_ID:
        logger.warning(f"Accesso negato: {user_id}")
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
        logger.warning(f"Accesso negato: {user_id}")
        await update.message.reply_text("Non sei autorizzato a usare questo bot.")
        return

    anime_name = update.message.text.replace("/trova_anime", "").strip()

    logger.info(f"Nome anime cercato: {anime_name}")
    link = airi.get_anime_link(anime_name)

    if link == "Anime non trovato.":
        await update.message.reply_text("Non sono riuscito a trovare l'anime. Assicurati che il nome sia corretto.")
    else:
        await update.message.reply_text(f"🎬 Ecco il link per l'anime: {link}")

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
        miko_instance.downloadEpisodes(anime_folder)
        logger.info("Download completato.")
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
        
        miko_instance.count_and_update_episodes(anime_name, episodi_scaricati)
        if anime_name and link and last_update:
            last_update_date = parser.parse(last_update)
            days_since_update = (datetime.datetime.now() - last_update_date).days
            
            if episodi_scaricati == 0 or (7 <= days_since_update < 28):
                miko_instance.loadAnime(link)
                
                missing_episodes = miko_instance.check_missing_episodes()

                if missing_episodes:
                    await context.bot.send_message(
                        chat_id=AUTHORIZED_USER_ID,
                        text=f"Episodi mancanti per {anime_name}. Inizio download..."
                    )
                    await download_new_episodes(anime_name)
                else:
                    logger.info(f"Tutti gli episodi di {anime_name} sono aggiornati.")
            else:
                logger.info(f"L'ultimo aggiornamento di {anime_name} è {days_since_update} giorni fa. Salto controllo.")
        else:
            logger.warning(f"Dati mancanti in {anime_data}")

async def download_new_episodes(anime_name: str):
    link = airi.get_anime_link(anime_name)

    if link == "Anime non trovato.":
        logger.error(f"Anime {anime_name} non trovato.")
        return

    miko_instance = miko.Miko()
    miko_instance.loadAnime(link)

    asyncio.create_task(download_task(miko_instance))  # Avvia il task in parallelo

    logger.info(f"Avviato download per {anime_name}.")

# Funzione principale per avviare il bot
def main():
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    if not TOKEN:
        logger.error("Token non trovato.")
        return

    logger.info("Avvio bot...")
    app = ApplicationBuilder().token(TOKEN).build()

    start_handler = CommandHandler("start", start)
    aggiungi_anime_handler = CommandHandler("aggiungi_anime", aggiungi_anime)

    conversation_handler = ConversationHandler(
        entry_points=[aggiungi_anime_handler],
        states={LINK: [MessageHandler(filters.TEXT, receive_link)]},
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(start_handler)
    app.add_handler(conversation_handler)
    app.add_handler(CommandHandler("lista_anime", lista_anime))
    app.add_handler(CommandHandler("trova_anime", trova_anime))
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("download_episodi", download_episodi)],
        states={
            LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_anime_name)],
        },
        fallbacks=[],
    ))
    app.add_handler(CommandHandler("stop_bot", stop_bot))

    app.job_queue.run_repeating(
        check_new_episodes,
        interval=airi.UPDATE_TIME,  
        first=datetime.time(0, 0),
    )

    def signal_handler(sig, frame):
        logger.info("Arresto bot... Interruzione manuale.")
        app.stop()

    signal.signal(signal.SIGINT, signal_handler)
    
    logger.info("Bot in esecuzione.")
    app.run_polling()

if __name__ == "__main__":
    main()
