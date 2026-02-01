# YUNA System - Guida Installazione PWA

## Funzionalità PWA Implementate

### ✅ Manifest PWA
- **Nome**: YUNA System
- **Nome Breve**: YUNA
- **Display**: Standalone (app a schermo intero)
- **Tema**: Material Design 3 con colori dark (#1e293b)
- **Icone**: 192x192 e 512x512 pixels
- **Scorciatoie**:
  - Cerca contenuti (`/search`)
  - Anime (`/anime`)

### ✅ Pulsante di Installazione
- Posizione: Sidebar desktop (sopra pulsante Esci)
- Rilevamento automatico: appare solo se il browser supporta l'installazione
- Stati:
  - Nascosto: se PWA già installata o browser non supporta
  - Visibile: "Installa App" con icona download
  - Installata: badge "App Installata" con icona check

### ✅ Meta Tags
- Viewport ottimizzato per mobile
- Theme color per barra di stato
- Apple Mobile Web App support
- Favicon e Apple Touch Icon

## Come Testare l'Installazione

### 1. Deploy in Locale (con HTTPS)

Le PWA richiedono HTTPS per funzionare. Opzioni:

**Opzione A: Nginx con Self-Signed Certificate**
```bash
# Nel server
cd /home/nzaccagnino/YUNA-System
docker compose up -d

# Configura nginx con SSL (vedi configurazione sotto)
```

**Opzione B: Tunneling con ngrok/cloudflared**
```bash
# Esponi il server locale con HTTPS
ngrok http 80
# o
cloudflared tunnel --url http://localhost:80
```

### 2. Testare su Desktop (Chrome/Edge)

1. Apri Chrome/Edge e vai su `https://your-domain.com`
2. Login nell'applicazione
3. Cerca il pulsante "Installa App" nella sidebar
4. Clicca sul pulsante
5. Conferma l'installazione nel popup del browser
6. L'app si aprirà come finestra standalone

**Verifica Manifest**:
- Apri DevTools (F12)
- Vai su Application > Manifest
- Verifica che tutte le proprietà siano caricate
- Application > Service Workers (se implementato in futuro)

### 3. Testare su Mobile (Android)

1. Apri Chrome su Android
2. Vai su `https://your-domain.com`
3. Login nell'applicazione
4. Clicca sul menu Chrome (⋮) > "Installa app" o "Aggiungi a Home"
5. L'icona YUNA apparirà nella home screen
6. Apri l'app dalla home: si aprirà in modalità fullscreen

**Nota iOS**: Safari su iOS ha supporto PWA limitato. Il pulsante "Condividi" > "Aggiungi a Home" funziona, ma alcune funzionalità potrebbero essere limitate.

### 4. Testare su Mobile (iOS Safari)

1. Apri Safari su iOS/iPadOS
2. Vai su `https://your-domain.com`
3. Login nell'applicazione
4. Clicca sul pulsante "Condividi" (icona quadrato con freccia)
5. Scorri e seleziona "Aggiungi a Home"
6. Conferma il nome e aggiungi
7. L'icona YUNA apparirà nella home screen

## Verifica Funzionalità PWA

### Checklist Desktop
- [ ] Pulsante "Installa App" visibile nella sidebar
- [ ] Click su "Installa App" mostra il prompt del browser
- [ ] L'app si installa e appare come app standalone
- [ ] Badge "App Installata" appare dopo l'installazione
- [ ] Icona YUNA corretta nell'app launcher
- [ ] Tema dark applicato alla barra del titolo
- [ ] Scorciatoie funzionanti (tasto destro sull'icona)

### Checklist Mobile
- [ ] "Aggiungi a Home" disponibile nel menu browser
- [ ] Icona YUNA appare nella home screen
- [ ] L'app si apre in modalità fullscreen (senza barra URL)
- [ ] Barra di stato colorata (#1e293b)
- [ ] Splash screen con icona YUNA (Android)
- [ ] Navigazione funzionante
- [ ] Bottom navigation visibile e funzionante

### Verifica Manifest (DevTools)

```javascript
// In DevTools Console
navigator.serviceWorker.ready.then(registration => {
  console.log('Service Worker ready');
});

// Verifica se installata
if (window.matchMedia('(display-mode: standalone)').matches) {
  console.log('Running as installed PWA');
}

// Verifica manifest
fetch('/manifest.json').then(r => r.json()).then(console.log);
```

## File Modificati

### Frontend
1. **src/app.html**: Meta tags PWA e manifest link
2. **src/routes/+layout.svelte**: Import e posizionamento InstallButton
3. **src/lib/components/InstallButton.svelte**: Nuovo componente (creato)
4. **static/manifest.json**: Configurazione PWA (creato)
5. **static/icon-192.png**: Icona 192x192 (generato)
6. **static/icon-512.png**: Icona 512x512 (generato)
7. **static/favicon.png**: Favicon 32x32 (generato)
8. **static/yuna-icon.svg**: Sorgente SVG icona (creato)

### Build
- Frontend rebuilded con nuove risorse PWA
- Docker image aggiornata: `ghcr.io/justzacca/yuna-system-frontend:latest`

## Prossimi Passi (Opzionali)

### Service Worker per Offline Support
```javascript
// Aggiungere in src/service-worker.ts
import { build, files, version } from '$service-worker';

const CACHE = `cache-${version}`;
const ASSETS = [...build, ...files];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(ASSETS))
  );
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;
  
  event.respondWith(
    caches.match(event.request).then((cached) => {
      return cached || fetch(event.request);
    })
  );
});
```

### Push Notifications
- Implementare notifiche per download completati
- Richiedere permessi utente
- Backend endpoint per invio notifiche

### Background Sync
- Sincronizzare dati quando l'app torna online
- Gestire download interrotti

## Troubleshooting

### Pulsante non appare
- Verifica HTTPS attivo
- Controlla che manifest.json sia accessibile
- Apri DevTools > Console per errori
- Su iOS usa "Aggiungi a Home" da Safari

### Icone non si caricano
- Verifica permessi file in Docker: `ls -la /usr/share/nginx/html/`
- Controlla nginx logs: `docker logs yuna-frontend`
- Testa URL diretto: `https://domain.com/icon-192.png`

### L'app non si apre in modalità standalone
- Verifica `"display": "standalone"` in manifest.json
- Controlla `start_url` sia raggiungibile
- Su iOS, chiudi e riapri l'app

### Tema/colori non applicati
- Verifica `theme-color` in HTML head
- Controlla CSS caricato correttamente
- Riavvia l'app installata

## Deploy su Produzione

```bash
# Sul server
cd /home/nzaccagnino/YUNA-System

# Pull nuova immagine (se pushata su registry)
docker compose pull yuna-frontend

# O rebuild locale
docker compose build yuna-frontend

# Restart con nuova immagine
docker compose up -d yuna-frontend

# Verifica
docker compose logs -f yuna-frontend
```

## Test Lighthouse PWA

Usa Chrome DevTools Lighthouse per verificare score PWA:

1. Apri DevTools > Lighthouse
2. Seleziona "Progressive Web App"
3. Genera report
4. Target: 90+ score

### Criteri Lighthouse
- [x] Fast load time
- [x] Works offline (se Service Worker implementato)
- [x] Can be installed
- [x] Is configured for a custom splash screen
- [x] Sets a theme color for the address bar
- [x] Has a `<meta name="viewport">` tag
- [x] Provides a valid manifest

## Risorse

- [Web.dev PWA Guide](https://web.dev/progressive-web-apps/)
- [MDN PWA Documentation](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps)
- [Material Design 3 Colors](https://m3.material.io/styles/color/overview)
