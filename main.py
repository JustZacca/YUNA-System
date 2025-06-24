import kan
import sys

def main():
    try:
        bot = kan.Kan()
        bot.launchBot()
    except KeyboardInterrupt:
        print("\nInterruzione rilevata. Arrivederci!")
        bot.keyboard_stop_bot()
        sys.exit(0)

if __name__ == "__main__":
    main()