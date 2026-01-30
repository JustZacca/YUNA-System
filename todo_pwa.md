# YUNA PWA - Piano di Sviluppo

## Obiettivo

Trasformare YUNA in un sistema ibrido:
- **PWA Svelte** per gestione completa con UI ricca
- **Telegram Bot** mantenuto per notifiche e comandi rapidi
- **FastAPI Backend** condiviso da entrambi
- **Single Docker** che espone tutto su una porta

---

## Decisioni Tecniche

| Aspetto | Decisione | Note |
|---------|-----------|------|
| **UI Style** | Neobrutalism | HyperUI components (Tailwind CSS) |
| **Database** | SQLite | File singolo, backup facile, niente migrazioni complesse |
| **Film/Serie metadata** | TMDB API | Richiede API key (gratuita) |
| **Anime metadata** | Jikan API | No API key, gratuita, dati MyAnimeList |
| **Frontend** | SvelteKit + Tailwind | PWA installabile |
| **Backend** | FastAPI | Async, veloce, OpenAPI automatico |

### Neobrutalism Components (HyperUI)

37 componenti disponibili:
- Accordions (3) - contenuti collassabili
- Alerts (3) - notifiche
- Badges (3) - etichette
- **Buttons (5)** - azioni
- **Cards (4)** - media items
- Checkboxes (3) - selezioni
- **Inputs (3)** - ricerca
- **Progress Bars (3)** - download
- Selects (3) - dropdown
- **Tabs (4)** - navigazione Anime/Serie/Film
- Textareas (3) - input testo

Link: https://www.hyperui.dev/components/neobrutalism

### API Metadata

| API | Uso | Auth | Rate Limit |
|-----|-----|------|------------|
| **TMDB** | Film, Serie TV | API Key (gratuita) | 50 req/sec |
| **Jikan** | Anime (dati MAL) | Nessuna | 3 req/sec |

```
Ricerca "Frieren" →
├── TMDB: poster HD, descrizione, cast, rating, anno
└── Jikan: episodi totali, status, studio, generi MAL
    └── AnimeWorld: link download
```

---

## Architettura

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Container                      │
│                        :8000                             │
│  ┌───────────────────────────────────────────────────┐  │
│  │                    FastAPI                         │  │
│  │  /        → Svelte PWA (static)                   │  │
│  │  /api/*   → REST API                              │  │
│  │  /ws      → WebSocket (progress)                  │  │
│  └───────────────────────────────────────────────────┘  │
│                          │                               │
│  ┌───────────────────────┴───────────────────────────┐  │
│  │              Shared Services Layer                 │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ │  │
│  │  │  Miko   │ │ MikoSC  │ │Providers│ │Database │ │  │
│  │  │ (Anime) │ │(Serie/  │ │AW,SC,   │ │ SQLite  │ │  │
│  │  │         │ │ Film)   │ │TMDB,    │ │         │ │  │
│  │  │         │ │         │ │Jikan    │ │         │ │  │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘ │  │
│  └───────────────────────────────────────────────────┘  │
│                          │                               │
│  ┌───────────────────────┴───────────────────────────┐  │
│  │              Telegram Bot (background)             │  │
│  │              - Notifiche nuovi episodi            │  │
│  │              - Alert download completati          │  │
│  │              - Comandi quick                      │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## Divisione Responsabilità

### Telegram Bot (mantenuto)
- [x] Notifiche push nuovi episodi disponibili
- [x] Alert download completati
- [x] Comandi rapidi (/lista, /cerca)
- [x] Status veloce

### PWA Svelte (nuovo)
- [ ] Ricerca titoli con UI ricca (TMDB + Jikan + AW + SC)
- [ ] Gestione libreria completa (add/remove/edit)
- [ ] Navigazione stagioni/episodi con cover art
- [ ] Progress download real-time (WebSocket)
- [ ] Configurazione sistema
- [ ] Statistiche e grafici
- [ ] Filtri e ordinamento avanzati

---

## Struttura Progetto Finale

```
YUNA-System/
├── src/
│   └── yuna/
│       ├── __init__.py
│       ├── __main__.py              # Entry point (FastAPI + Bot)
│       │
│       ├── api/                     # [NEW] FastAPI Backend
│       │   ├── __init__.py
│       │   ├── main.py              # FastAPI app, serve static
│       │   ├── auth.py              # JWT authentication
│       │   ├── deps.py              # Dependencies (get_db, get_current_user)
│       │   ├── websocket.py         # WebSocket per progress
│       │   └── routes/
│       │       ├── __init__.py
│       │       ├── auth.py          # POST /api/login
│       │       ├── anime.py         # /api/anime/*
│       │       ├── series.py        # /api/series/*
│       │       ├── films.py         # /api/films/*
│       │       ├── search.py        # /api/search/*
│       │       ├── downloads.py     # /api/downloads/*
│       │       └── system.py        # /api/system/* (config, stats)
│       │
│       ├── bot/                     # [KEEP] Telegram Bot
│       │   ├── kan.py
│       │   └── ui/
│       │
│       ├── services/                # [KEEP] Business Logic
│       │   ├── media_service.py     # Miko
│       │   └── ...
│       │
│       ├── providers/               # [KEEP + NEW] External APIs
│       │   ├── animeworld/
│       │   ├── streamingcommunity/
│       │   ├── tmdb/                # [NEW] TMDB integration
│       │   │   ├── __init__.py
│       │   │   └── client.py
│       │   └── jikan/               # [NEW] Jikan/MAL integration
│       │       ├── __init__.py
│       │       └── client.py
│       │
│       ├── data/                    # [KEEP] Database
│       │   └── database.py
│       │
│       └── utils/                   # [KEEP] Utilities
│
├── frontend/                        # [NEW] Svelte PWA
│   ├── src/
│   │   ├── lib/
│   │   │   ├── api.ts               # API client
│   │   │   ├── stores.ts            # Svelte stores
│   │   │   └── components/
│   │   │       ├── ui/              # Neobrutalism components
│   │   │       │   ├── Button.svelte
│   │   │       │   ├── Card.svelte
│   │   │       │   ├── Input.svelte
│   │   │       │   ├── Badge.svelte
│   │   │       │   ├── Progress.svelte
│   │   │       │   ├── Tabs.svelte
│   │   │       │   └── Alert.svelte
│   │   │       ├── MediaCard.svelte
│   │   │       ├── SearchBar.svelte
│   │   │       ├── DownloadProgress.svelte
│   │   │       ├── SeasonSelector.svelte
│   │   │       └── ...
│   │   ├── routes/
│   │   │   ├── +layout.svelte
│   │   │   ├── +page.svelte         # Dashboard
│   │   │   ├── login/
│   │   │   ├── anime/
│   │   │   ├── series/
│   │   │   ├── films/
│   │   │   ├── search/
│   │   │   └── settings/
│   │   ├── app.html
│   │   └── app.css                  # Tailwind + Neobrutalism base
│   ├── static/
│   │   ├── manifest.json            # PWA manifest
│   │   └── icons/
│   ├── package.json
│   ├── svelte.config.js
│   ├── vite.config.js
│   └── tailwind.config.js           # Neobrutalism theme
│
├── docker/
│   └── Dockerfile                   # Single container
│
├── docker-compose.yml
├── .env.example
├── pyproject.toml
└── README.md
```

---

## Fasi di Implementazione

### Fase 1: FastAPI Backend Foundation
- [ ] Creare `src/yuna/api/main.py` con FastAPI app
- [ ] Implementare `src/yuna/api/auth.py` (JWT, login)
- [ ] Creare `src/yuna/api/deps.py` (dependencies)
- [ ] Route base: health check, versione

### Fase 2: API Routes
- [ ] `routes/auth.py` - POST /api/login, GET /api/me
- [ ] `routes/anime.py` - CRUD anime library
- [ ] `routes/series.py` - CRUD serie TV
- [ ] `routes/films.py` - CRUD film
- [ ] `routes/search.py` - Ricerca su AW, SC, TMDB, Jikan
- [ ] `routes/downloads.py` - Avvia/ferma download, lista attivi
- [ ] `routes/system.py` - Config, stats, Jellyfin refresh

### Fase 3: Metadata Providers
- [ ] `providers/tmdb/client.py` - TMDB API client (film/serie)
- [ ] `providers/jikan/client.py` - Jikan API client (anime)
- [ ] Ricerca unificata con metadata enrichment
- [ ] Cache poster e metadata (SQLite o file)

### Fase 4: WebSocket Progress
- [ ] `websocket.py` - WebSocket endpoint /ws
- [ ] Modificare download per emettere eventi progress
- [ ] Client-side reconnection handling

### Fase 5: Svelte PWA Base
- [ ] Setup progetto SvelteKit
- [ ] Configurare Tailwind con tema Neobrutalism
- [ ] Creare componenti UI base (Button, Card, Input, etc.)
- [ ] PWA manifest + service worker
- [ ] Layout base con navigation (tabs)
- [ ] Login page
- [ ] API client TypeScript

### Fase 6: PWA Features
- [ ] Dashboard (overview libreria, download attivi)
- [ ] Pagina ricerca con risultati rich (poster, rating, anno)
- [ ] Lista anime con cover art e status
- [ ] Lista serie TV con stagioni/episodi
- [ ] Lista film con stato download
- [ ] Dettaglio media con azioni (download, rimuovi)
- [ ] Download progress real-time
- [ ] Settings page

### Fase 7: Docker Integration
- [ ] Dockerfile multi-stage (build frontend + Python)
- [ ] `__main__.py` che avvia FastAPI + Bot insieme
- [ ] docker-compose.yml
- [ ] Volume mounts per data e media

### Fase 8: Polish
- [ ] Error handling consistente (toast notifications)
- [ ] Loading states (skeleton)
- [ ] Mobile responsive
- [ ] Animazioni subtle
- [ ] Documentazione API (OpenAPI/Swagger)

---

## API Endpoints

### Auth
```
POST /api/login          # Login, ritorna JWT
GET  /api/me             # User info corrente
```

### Anime
```
GET    /api/anime                    # Lista tutti
GET    /api/anime/{name}             # Dettaglio + metadata Jikan
POST   /api/anime                    # Aggiungi (body: {url})
DELETE /api/anime/{name}             # Rimuovi
POST   /api/anime/{name}/download    # Scarica episodi mancanti
GET    /api/anime/{name}/episodes    # Lista episodi
```

### Serie TV
```
GET    /api/series                       # Lista tutte
GET    /api/series/{name}                # Dettaglio + metadata TMDB
POST   /api/series                       # Aggiungi
DELETE /api/series/{name}                # Rimuovi
GET    /api/series/{name}/seasons        # Lista stagioni
POST   /api/series/{name}/download       # Scarica episodi mancanti
```

### Film
```
GET    /api/films                    # Lista tutti
GET    /api/films/{name}             # Dettaglio + metadata TMDB
POST   /api/films                    # Aggiungi
DELETE /api/films/{name}             # Rimuovi
POST   /api/films/{name}/download    # Scarica film
```

### Search
```
GET /api/search?q={query}&type={anime|series|film|all}
    # Ricerca unificata:
    # - anime: Jikan metadata + AnimeWorld link
    # - series/film: TMDB metadata + StreamingCommunity link
```

### Downloads
```
GET    /api/downloads                # Lista download attivi
POST   /api/downloads/all            # Scarica tutti i mancanti
DELETE /api/downloads/{id}           # Cancella download
```

### System
```
GET  /api/system/stats               # Statistiche libreria
POST /api/system/jellyfin/refresh    # Refresh Jellyfin library
GET  /api/system/config              # Configurazione attuale
```

### WebSocket
```
WS /ws                               # Progress updates real-time
   # Eventi: download_start, download_progress, download_complete, download_error
```

---

## Configurazione (.env)

```env
# === Telegram Bot ===
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# === PWA Auth ===
YUNA_USERNAME=admin
YUNA_PASSWORD=your_secure_password
JWT_SECRET=random_secret_key_here
JWT_EXPIRE_HOURS=24

# === Paths ===
ANIME_FOLDER=/media/anime
SERIES_FOLDER=/media/series
FILMS_FOLDER=/media/films
DATABASE_PATH=/app/data/yuna.db

# === External APIs ===
TMDB_API_KEY=your_tmdb_api_key
# Jikan non richiede API key

# === Jellyfin (optional) ===
JELLYFIN_URL=http://jellyfin:8096
JELLYFIN_API_KEY=your_jellyfin_key

# === Server ===
HOST=0.0.0.0
PORT=8000
```

---

## Docker

### Dockerfile
```dockerfile
# Stage 1: Build frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python app
FROM python:3.12-slim
WORKDIR /app

# Install ffmpeg for video processing
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir .

# Copy backend
COPY src/ ./src/

# Copy built frontend
COPY --from=frontend-builder /app/frontend/build ./static

# Create data directory
RUN mkdir -p /app/data

EXPOSE 8000

CMD ["python", "-m", "yuna"]
```

### docker-compose.yml
```yaml
version: "3.8"

services:
  yuna:
    build: .
    container_name: yuna
    restart: unless-stopped
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./data:/app/data
      - /path/to/media/anime:/media/anime
      - /path/to/media/series:/media/series
      - /path/to/media/films:/media/films
    networks:
      - media

networks:
  media:
    external: true
```

---

## Note Tecniche

### Concorrenza Bot + API
```python
# src/yuna/__main__.py
import asyncio
from contextlib import asynccontextmanager
from yuna.api.main import create_app
from yuna.bot.kan import Kan

bot = Kan()

@asynccontextmanager
async def lifespan(app):
    # Startup: avvia bot
    bot_task = asyncio.create_task(bot.start_polling())
    yield
    # Shutdown: ferma bot
    await bot.stop()
    bot_task.cancel()

app = create_app(lifespan=lifespan)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### WebSocket Progress Pattern
```python
# Manager per broadcast a tutti i client connessi
class ProgressManager:
    def __init__(self):
        self.connections: list[WebSocket] = []

    async def broadcast(self, event: dict):
        for ws in self.connections:
            await ws.send_json(event)

progress_manager = ProgressManager()

# Nel download:
await progress_manager.broadcast({
    "type": "download_progress",
    "name": "Frieren",
    "episode": 5,
    "progress": 45.2
})
```

### Neobrutalism Tailwind Config
```javascript
// tailwind.config.js
module.exports = {
  content: ['./src/**/*.{html,js,svelte,ts}'],
  theme: {
    extend: {
      boxShadow: {
        'brutal': '4px 4px 0px 0px rgba(0,0,0,1)',
        'brutal-lg': '6px 6px 0px 0px rgba(0,0,0,1)',
      },
      borderWidth: {
        '3': '3px',
      },
      colors: {
        'brutal-yellow': '#FFE500',
        'brutal-pink': '#FF6B9D',
        'brutal-blue': '#00D4FF',
        'brutal-green': '#00FF85',
        'brutal-purple': '#9B5DE5',
      }
    },
  },
  plugins: [],
}
```

### Jikan API Usage
```python
# providers/jikan/client.py
import httpx

class JikanClient:
    BASE_URL = "https://api.jikan.moe/v4"

    async def search_anime(self, query: str) -> list[dict]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/anime",
                params={"q": query, "limit": 10}
            )
            data = response.json()
            return data.get("data", [])

    async def get_anime(self, mal_id: int) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.BASE_URL}/anime/{mal_id}")
            return response.json().get("data", {})
```

---

## Priorità

1. **Alta**: Fase 1-2 (Backend API funzionante)
2. **Alta**: Fase 5 (PWA base con login e componenti Neobrutalism)
3. **Alta**: Fase 3 (TMDB + Jikan per metadata rich)
4. **Media**: Fase 4 (WebSocket progress)
5. **Media**: Fase 6 (Features complete)
6. **Media**: Fase 7 (Docker)
7. **Bassa**: Fase 8 (Polish)

---

## Timeline Stimata

| Fase | Descrizione | Effort |
|------|-------------|--------|
| 1 | FastAPI foundation | 1-2 giorni |
| 2 | API routes complete | 2-3 giorni |
| 3 | TMDB + Jikan providers | 1-2 giorni |
| 4 | WebSocket | 1 giorno |
| 5 | Svelte PWA base + Neobrutalism | 2-3 giorni |
| 6 | PWA features | 3-5 giorni |
| 7 | Docker | 1 giorno |
| 8 | Polish | 2-3 giorni |

**Totale stimato**: 2-3 settimane

---

## Checklist Pre-Sviluppo

- [x] Framework CSS: Tailwind + HyperUI Neobrutalism
- [x] Database: SQLite (mantenuto)
- [x] API Film/Serie: TMDB (richiede registrazione gratuita)
- [x] API Anime: Jikan (no registrazione)
- [ ] Registrare API key TMDB: https://www.themoviedb.org/settings/api
- [ ] Definire palette colori Neobrutalism finale

---

## Links Utili

- HyperUI Neobrutalism: https://www.hyperui.dev/components/neobrutalism
- TMDB API Docs: https://developer.themoviedb.org/docs
- Jikan API Docs: https://docs.api.jikan.moe/
- SvelteKit: https://kit.svelte.dev/
- FastAPI: https://fastapi.tiangolo.com/
