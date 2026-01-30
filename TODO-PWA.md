# YUNA PWA - TODO

## Setup Iniziale
- [ ] Creare cartella `pwa/` nella root
- [ ] Setup React + Vite + TypeScript
- [ ] Configurare TailwindCSS
- [ ] Aggiungere manifest.json per PWA
- [ ] Service worker per offline support

## Autenticazione
- [ ] Pagina Login (`/login`)
- [ ] Salvare JWT in localStorage
- [ ] Redirect automatico se non autenticato
- [ ] Logout button

## Layout
- [ ] Navbar bottom (mobile-first)
  - Home / Anime / Serie / Film / Settings
- [ ] Header con logo e search
- [ ] Dark mode (default)

## Pagine

### Home (`/`)
- [ ] Stats cards (totale anime/serie/film)
- [ ] Ultimi aggiunti
- [ ] Download in corso (se presenti)

### Anime (`/anime`)
- [ ] Lista anime con cover
- [ ] Search/filter
- [ ] Card: nome, episodi scaricati/totali, ultimo update
- [ ] Click -> dettaglio

### Dettaglio Anime (`/anime/:id`)
- [ ] Cover grande
- [ ] Info (nome, episodi, folder)
- [ ] Lista episodi con stato
- [ ] Button: Scarica mancanti
- [ ] Button: Rimuovi (con conferma)

### Serie TV (`/series`)
- [ ] Lista serie StreamingCommunity
- [ ] Card: nome, stagioni, episodi

### Film (`/movies`)
- [ ] Lista film
- [ ] Stato download (pending/completed)

### Cerca (`/search`)
- [ ] Input search
- [ ] Toggle: AnimeWorld / StreamingCommunity
- [ ] Risultati con button "Aggiungi"

### Settings (`/settings`)
- [ ] Info versione
- [ ] Logout
- [ ] (futuro) Notifiche push

## API Endpoints da usare
```
GET  /api/health
GET  /api/stats
POST /api/login
GET  /api/me

GET  /api/anime
GET  /api/anime/{id}
GET  /api/anime/{id}/episodes
POST /api/anime (add)
DELETE /api/anime/{id}
POST /api/anime/{id}/download

GET  /api/series
GET  /api/movies
GET  /api/search?q=...&source=...
```

## Comandi utili
```bash
# Setup
cd pwa
npm create vite@latest . -- --template react-ts
npm install
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p

# Dev
npm run dev

# Build
npm run build
```

## Note
- API base: `http://localhost:8000/api`
- Auth header: `Authorization: Bearer <token>`
- Mobile-first design
- Colori: dark theme, accent blu/viola
