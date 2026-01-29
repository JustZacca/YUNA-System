# YUNA-System - Idee Future

## Architettura Provider Unificati

Creare un sistema a provider multipli con fallback automatico:

```
MediaSearch (API unificata)
    ├── StreamingCommunityProvider
    ├── AltadefinizioneProvider
    └── AnimeWorldProvider (già esistente)
```

- Interfaccia comune `MediaProvider`
- Ricerca su tutti i provider
- Deduplicazione risultati per titolo/anno
- Fallback automatico se un provider non ha il contenuto

## Metadati Esterni

Integrare API esterne per metadati di qualità:

### Film/Serie TV
- **TMDB** (The Movie Database) - Poster HD, plot, cast, rating, trailer
- **OMDb** - IMDB rating, info base
- **Fanart.tv** - Logo, banner, clearart HD

### Anime
- **AniList** - GraphQL API gratuita, cover, episodi, rating
- **Jikan** - API non ufficiale MyAnimeList

### Dati da recuperare
- Identificatori cross-platform (tmdb_id, imdb_id, anilist_id)
- Titolo originale + localizzato
- Anno, durata, generi, trama multi-lingua
- Rating da più fonti
- Artwork HD (poster, backdrop, logo, banner)
- Cast & crew con foto
- Trailer YouTube
- Info episodi (titoli, trame, air date)

### Vantaggi
- Matching preciso via ID invece che titolo
- Generazione NFO per Jellyfin/Plex
- UI Telegram migliorata con poster
- Deduplicazione affidabile

## Cache

Cache in-memory con TTL (no Redis, overkill per uso personale):

| Dato | TTL |
|------|-----|
| Domain SC (da Arrowar) | 1-6 ore |
| Risultati ricerca | 30-60 min |
| Info serie/stagioni | 1-24 ore |
| Metadati TMDB/AniList | 24-48 ore |
| URL video | 5-10 min |

## Provider Altadefinizione

Da implementare come fallback per StreamingCommunity:
- Stesso pattern di SC (Inertia.js?)
- Usare Arrowar API per domain aggiornato
- Implementare interfaccia `MediaProvider`
