# YUNA-System

**Your Underground Networked Animebot** - Sistema automatizzato per il download e la gestione di anime, serie TV e film con integrazione Telegram.

---

## Significato dei Nomi

| Classe | Acronimo | Descrizione |
|--------|----------|-------------|
| **YUNA** | *Your Underground Networked Animebot* | Sistema centrale che coordina tutte le operazioni |
| **MIKO** | *Media Indexing and Kapturing Operator* | Responsabile del download e dell'indicizzazione dei contenuti |
| **AIRI** | *Anime Intelligent Retrieval Interface* | Gestisce la memorizzazione dei dati e le variabili d'ambiente |
| **KAN** | *Kommunicative Anime Notification Assistant* | Bot Telegram per la gestione e le notifiche |

---

## Funzionalità Principali

### Anime (AnimeWorld)
- Ricerca e download automatico da AnimeWorld
- Monitoraggio nuovi episodi con aggiornamento automatico
- Gestione libreria anime via Telegram

### Serie TV e Film (StreamingCommunity)
- Ricerca film e serie TV su StreamingCommunity
- Download in qualità HD/FHD via HLS
- Tracciamento serie con notifica nuovi episodi
- Organizzazione automatica in cartelle (Serie/Stagione/Episodio)

### Generale
- Aggiornamento automatico periodico della libreria
- Notifiche Telegram in tempo reale
- Refresh automatico libreria Jellyfin
- Database SQLite per persistenza dati

---

## Requisiti

- Docker e Docker Compose
- Token Bot Telegram
- Chat ID Telegram autorizzato
- (Opzionale) Jellyfin per la gestione della libreria media

---

## Installazione

1. **Clona il repository**
   ```bash
   git clone https://github.com/justzacca/yuna-system.git
   cd yuna-system
   ```

2. **Configura Docker Compose**
   ```bash
   cp docker-compose.example.yml docker-compose.yml
   ```

3. **Modifica `docker-compose.yml`**
   - Inserisci il tuo `TELEGRAM_TOKEN` e `CHAT_ID`
   - Modifica i path dei volumi con le tue cartelle

4. **Avvia il container**
   ```bash
   docker compose up -d
   ```

---

## Configurazione

### Variabili d'ambiente

In `docker-compose.yml`, sezione `environment`:

| Variabile | Obbligatorio | Descrizione |
|-----------|--------------|-------------|
| `TELEGRAM_TOKEN` | Si | Token del bot Telegram |
| `CHAT_ID` | Si | Il tuo Chat ID Telegram |
| `JELLYFIN_URL` | No | URL del server Jellyfin |
| `JELLYFIN_API_KEY` | No | API Key di Jellyfin |
| `UPDATE_TIME` | No | Intervallo aggiornamento in minuti (default: 60) |

### Volumi

I volumi mappano le cartelle del tuo sistema alle cartelle interne del container:

```yaml
volumes:
  - /tuo/path/locale:/path/interno/container
```

| Volume | Descrizione |
|--------|-------------|
| `./data:/data` | Database (non modificare) |
| `/path/to/anime:/downloads/anime` | Cartella anime |
| `/path/to/series:/downloads/series` | Cartella serie TV |
| `/path/to/movies:/downloads/movies` | Cartella film |

**Modifica solo la parte sinistra** (prima dei `:`) con i tuoi path locali.

Per uso locale senza Docker, vedi `.env.example`.

---

## Comandi Telegram

### Anime
| Comando | Descrizione |
|---------|-------------|
| `/start` | Avvia il bot e mostra il menu |
| `/aggiungi_anime` | Aggiungi un anime dalla URL di AnimeWorld |
| `/cerca_anime` | Cerca un anime per nome |
| `/lista_anime` | Mostra gli anime in libreria |
| `/rimuovi_anime` | Rimuovi anime dalla libreria |
| `/aggiorna_libreria` | Forza aggiornamento libreria |

### Serie TV e Film
| Comando | Descrizione |
|---------|-------------|
| `/cerca_sc` | Cerca su StreamingCommunity |
| `/lista_serie` | Mostra le serie TV in libreria |
| `/lista_film` | Mostra i film in libreria |
| `/rimuovi_serie` | Rimuovi una serie dalla libreria |
| `/aggiorna_serie` | Controlla nuovi episodi delle serie |

### Sistema
| Comando | Descrizione |
|---------|-------------|
| `/stop_bot` | Arresta il bot |

---

## Struttura Cartelle Download

```
downloads/
├── anime/
│   └── NomeAnime/
│       ├── NomeAnime_Ep_01.mp4
│       └── ...
├── series/
│   └── NomeSerie/
│       ├── S01/
│       │   ├── NomeSerie - S01E01 - Titolo.mp4
│       │   └── ...
│       └── S02/
│           └── ...
└── movies/
    └── NomeFilm/
        └── NomeFilm.mp4
```

---

## Sviluppo

### Eseguire i test
```bash
pytest tests/ -v
```

### Build locale Docker
```bash
docker build -t yuna-system:local .
```

---

## Ringraziamenti

Questo progetto utilizza risorse di terze parti:

- **[MainKronos](https://github.com/MainKronos)** - Per [AnimeWorld-API](https://github.com/MainKronos/AnimeWorld-API), la libreria Python non ufficiale per AnimeWorld
- **[Arrowar](https://github.com/Arrowar)** - Per [SC_Domains](https://github.com/Arrowar/SC_Domains), che fornisce gli URL aggiornati automaticamente per StreamingCommunity e altri siti di streaming
- **[AnimeWorld](https://www.animeworld.ac)** - Fonte per il download degli anime
- **[StreamingCommunity](https://streamingcommunity.computer)** - Fonte per serie TV e film

---

## Licenza

Questo progetto è solo per uso personale e educativo.
