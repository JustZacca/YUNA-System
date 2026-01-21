import kan
import sys

def main():
    bot = None
    try:
        bot = kan.Kan()
        bot.launchBot()
    except KeyboardInterrupt:
        print("\nInterruzione rilevata. Arrivederci!")
        # keyboard_stop_bot non e necessario qui perche il signal handler in launchBot
        # gestisce gia SIGINT. Inoltre keyboard_stop_bot e async ma qui siamo in sync.
        sys.exit(0)
    except Exception as e:
        print(f"Errore durante l'esecuzione del bot: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()