import asyncio
from gats import Gats  # Assicurati che la classe sia salvata in gats.py

async def main():
    gats = Gats()
    
    query = input("Inserisci il nome della serie o film da cercare: ")
    results = await gats.search_show(query)

    if not results:
        print("❌ Nessun risultato trovato.")
        return

    print("\n📺 Risultati trovati:")
    indexed = list(results.items())
    for i, (title, info) in enumerate(indexed):
        print(f"{i + 1}. {title} (ID: {info['id']}, Tipo: {info.get('type')})")

    choice = input("\nScegli un numero dalla lista: ")
    try:
        index = int(choice) - 1
        selected = indexed[index][1]
        show_id = selected["id"]
    except (ValueError, IndexError):
        print("❌ Scelta non valida.")
        return

    # Carica e crea cartella
    await gats.load_show(show_id)
    await gats.setup_show_folder()

    print(f"✅ Cartella creata per: {gats.show_name}")
    print(f"📂 Path: {gats.tv_folder}")

if __name__ == "__main__":
    asyncio.run(main())
