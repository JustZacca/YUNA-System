import asyncio
from gats import Gats

async def main():
    gats = Gats()
    query = input("Inserisci il nome della serie o film da cercare: ")
    
    results = gats.search_show(query)  # NOT await
    if not results:
        print("❌ Nessun risultato trovato.")
        return

    indexed = list(results.items())
    for i, (title, info) in enumerate(indexed):
        print(f"{i+1}. {title} (ID: {info['id']})")

    choice = input("Scegli un numero: ")
    try:
        index = int(choice) - 1
        selected = indexed[index][1]
        show_id = selected["id"]
    except Exception:
        print("❌ Scelta non valida.")
        return

    await gats.load_show(show_id)
    await gats.setup_show_folder()

    print(f"✅ Cartella creata per: {gats.show_name}")
    print(f"📂 Path: {gats.tv_folder}")

if __name__ == "__main__":
    asyncio.run(main())
