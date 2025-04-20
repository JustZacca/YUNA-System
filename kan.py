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

# Inizializza colorama
from colorama import init
init(autoreset=True)

# Configura il logging con il custom formatter
formatter = ColoredFormatter(
    fmt="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
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
    logger.info(f"Comando /aggiungi_anime ricevuto da user_id: {user_id}")

    if user_id != AUTHORIZED_USER_ID:
        logger.warning(f"Accesso negato per user_id: {user_id}")
        await update.message.reply_text("Non sei autorizzato a usare questo bot.")
        return ConversationHandler.END

    logger.info("Utente autorizzato. Avvio della conversazione per aggiungere anime.")
    await update.message.reply_text("Per favore, inviami un link di AnimeWorld.")
    return LINK

async def stop_bot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    logger.info(f"Comando /stop_bot ricevuto da user_id: {user_id}")

    if user_id != AUTHORIZED_USER_ID:
        logger.warning(f"Accesso negato per user_id: {user_id}")
        await update.message.reply_text("Non sei autorizzato a usare questo comando.")
        return

    logger.info("Utente autorizzato. Arresto del bot in corso...")
    await update.message.reply_text("Arresto del bot in corso...")
    os.kill(os.getpid(), signal.SIGINT)
    
# Funzione per ricevere il link di AnimeWorld
async def receive_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    link = update.message.text
    logger.info(f"Link ricevuto: {link}")

    if 'animeworld' in link and link.startswith("https://"):
        try:
            miko_instance = miko.Miko()
            miko_instance.addAnime(link)
            logger.info(f"Anime aggiunto: {link}")
            await update.message.reply_text(f"Anime aggiunto con successo: {link}")
        except Exception as e:
            logger.error(f"Errore durante l'aggiunta dell'anime: {e}")
            await update.message.reply_text("Si è verificato un errore nell'aggiunta dell'anime. Riprova più tardi.")
    else:
        logger.warning("Link non valido ricevuto.")
        await update.message.reply_text("Il link non sembra provenire da AnimeWorld o non è formattato correttamente.")
    return ConversationHandler.END

# Funzione per gestire il comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    logger.info(f"Comando /start ricevuto da user_id: {user_id}")

    if user_id != AUTHORIZED_USER_ID:
        logger.warning(f"Accesso negato per user_id: {user_id}")
        await update.message.reply_text("Non sei autorizzato a usare questo bot.")
        return

    logger.info("Utente autorizzato. Inviando il messaggio di benvenuto.")
    await update.message.reply_text("Benvenuto in KAN, spero tu sia Nicholas o non sei il benvenuto.\nPer favore, usa il comando /aggiungi_anime per aggiungere un anime. "+
                                    "\n Usa il comando /lista_anime per vedere gli anime già aggiunti.\n Usa il comando /download_episodi per scaricare gli episodi di un anime."+
                                    "\n Usa il comando /cancella_anime per cancellare un anime.\n Usa il comando /help per vedere i comandi disponibili.")

# Funzione per annullare la conversazione
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info("Operazione annullata dall'utente.")
    await update.message.reply_text("Operazione annullata.")
    return ConversationHandler.END



async def send_message_to_user(app, message: str):
    """Invia un messaggio all'utente autorizzato tramite il bot."""
    try:
        await app.bot.send_message(chat_id=AUTHORIZED_USER_ID, text=message)
        logger.info(f"Messaggio inviato a {AUTHORIZED_USER_ID}: {message}")
    except Exception as e:
        logger.error(f"Errore durante l'invio del messaggio: {e}")

async def lista_anime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id != AUTHORIZED_USER_ID:
        logger.warning(f"Accesso negato per user_id: {user_id}")
        await update.message.reply_text("Non sei autorizzato a usare questo bot.")
        return

    # Ottieni la lista degli anime
    anime_list = airi.get_anime()

    if not anime_list:
        await update.message.reply_text("📭 La lista degli anime è vuota.")
        return

    # Costruisci la lista dei nomi degli anime con link
    anime_text = ""
    for anime in anime_list:
        name = anime.get("name", "Sconosciuto")  # O cambia 'name' con 'nome' se è diverso nel JSON
        link = anime.get("link", "#")
        anime_text += f"• [{name}]({link})\n"

    await update.message.reply_text(f"📜 *Lista degli anime:*\n\n{anime_text}", parse_mode="Markdown")

async def trova_anime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id != AUTHORIZED_USER_ID:
        logger.warning(f"Accesso negato per user_id: {user_id}")
        await update.message.reply_text("Non sei autorizzato a usare questo bot.")
        return

    # Ottieni il nome dell'anime dal messaggio dell'utente, rimuovendo il comando /trova_anime
    anime_name = update.message.text.replace("/trova_anime", "").strip()

    # Cerca il link dell'anime usando la funzione get_anime_link
    logger.info(f"Nome anime cercato: {anime_name}")
    link = airi.get_anime_link(anime_name)

    if link == "Anime non trovato.":
        await update.message.reply_text("Non sono riuscito a trovare l'anime. Assicurati che il nome sia corretto.")
    else:
        await update.message.reply_text(f"🎬 Ecco il link per l'anime: {link}")


# Funzione per scaricare gli episodi di un anime
async def download_episodi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id != AUTHORIZED_USER_ID:
        logger.warning(f"Accesso negato per user_id: {user_id}")
        await update.message.reply_text("Non sei autorizzato a usare questo bot.")
        return

    # Ottieni il nome dell'anime dal messaggio dell'utente, rimuovendo il comando /download_episodi
    anime_name = update.message.text.replace("/download_episodi", "").strip()

    # Cerca il link dell'anime usando la funzione get_anime_link
    logger.info(f"Nome anime per download: {anime_name}")
    link = airi.get_anime_link(anime_name)

    if link == "Anime non trovato.":
        await update.message.reply_text("Non sono riuscito a trovare l'anime. Assicurati che il nome sia corretto.")
    else:
        # Inizializza Miko e scarica gli episodi
        miko_instance = miko.Miko()
        miko_instance.loadAnime(link)

        # Informa l'utente che il download è iniziato
        await update.message.reply_text("Scaricamento degli episodi in corso...")
        
        # Avvia il download in background senza bloccare il bot
        asyncio.create_task(download_task(miko_instance))  # Questo avvierà il task in parallelo

        await update.message.reply_text(f"🎬 Scaricamento degli episodi per l'anime: {link} è in corso."
                                        "\nControlla la cartella di destinazione per gli episodi scaricati.")

# Funzione per gestire il download in background
async def download_task(miko_instance: miko.Miko):
    try:
        miko_instance.downloadEpisodes(miko_instance.setupAnimeFolder())
        logger.info("Download completato.")
    except Exception as e:
        logger.error(f"Errore durante il download: {e}")

async def check_new_episodes(context: ContextTypes.DEFAULT_TYPE):
    anime_list = airi.get_anime()  # Ottieni la lista degli anime

    for anime in anime_list:
        anime_name = anime.get("name", "Sconosciuto")  # Ottieni il nome dell'anime

        # Verifica la presenza di nuovi episodi
        missing_episodes = anime.check_missing_episodes()
        if missing_episodes:
            # Invia un messaggio all'utente
            await context.bot.send_message(
                chat_id=AUTHORIZED_USER_ID,
                text=f"Nuovi episodi sono stati trovati per {anime_name}: {missing_episodes}. Avvio il download..."
            )
            # Avvia il download
            await download_new_episodes(anime_name)
        else:
            # Invia un messaggio all'utente se non ci sono nuovi episodi
            await context.bot.send_message(
                chat_id=AUTHORIZED_USER_ID,
                text=f"Non ci sono nuovi episodi per {anime_name} al momento."
            )

# Funzione per gestire il download in background
async def download_task(miko_instance: miko.Miko):
    try:
        miko_instance.downloadEpisodes(miko_instance.setupAnimeFolder())
        logger.info("Download completato.")
        
    except Exception as e:
        logger.error(f"Errore durante il download: {e}")

async def download_new_episodes(anime_name: str):
    link = airi.get_anime_link(anime_name)

    if link == "Anime non trovato.":
        logger.error(f"Anime {anime_name} non trovato.")
        return

    miko_instance = miko.Miko()
    miko_instance.addAnime(link)

    # Avvia il download in background
    asyncio.create_task(download_task(miko_instance))  # Avvia il task in parallelo

    logger.info(f"Avviato il download per {anime_name}.")

# Funzione principale per avviare il bot
def main():
    # Ottieni il token dal file .env
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    if not TOKEN:
        logger.error("Il token TELEGRAM_TOKEN non è stato trovato nell'ambiente.")
        return

    logger.info("Avvio del bot...")
    # Crea l'applicazione
    app = ApplicationBuilder().token(TOKEN).build()

    # Definisci i CommandHandler per /start e /aggiungi_anime
    start_handler = CommandHandler("start", start)
    aggiungi_anime_handler = CommandHandler("aggiungi_anime", aggiungi_anime)
    

    # Definisci il ConversationHandler per aggiungere anime
    conversation_handler = ConversationHandler(
        entry_points=[aggiungi_anime_handler],
        states={LINK: [MessageHandler(filters.TEXT, receive_link)]},
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Aggiungi gli handler all'applicazione
    app.add_handler(start_handler)
    app.add_handler(conversation_handler)
    app.add_handler(CommandHandler("lista_anime", lista_anime))
    app.add_handler(CommandHandler("trova_anime", trova_anime))
    app.add_handler(CommandHandler("download_episodi", download_episodi))
    app.add_handler(CommandHandler("stop_bot", stop_bot))

     # Pianifica il controllo ogni ora
    app.job_queue.run_repeating(
        check_new_episodes,
        interval=3600,  # 3600 secondi = 1 ora
        first=datetime.time(0, 0),  # Inizia a mezzanotte
    )


     # Funzione per gestire l'interruzione del server (Ctrl+C)
    def signal_handler(sig, frame):
        logger.info("Arresto del bot... Interruzione manuale ricevuta.")
        app.stop()

    # Aggiungi il gestore del segnale SIGINT (Ctrl+C)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Avvia il bot
    logger.info("Il bot è in esecuzione.")
    app.run_polling()
    


if __name__ == "__main__":
    main()
