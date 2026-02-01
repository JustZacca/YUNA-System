<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { user, isAuthenticated } from '$lib/stores';
  import { api } from '$lib/api';
  import { Button, Card, LinearProgressEstimate, snackbar, CircularProgress } from 'm3-svelte';
  import Icon from '@iconify/svelte';
  import type { FilmDetail, ProviderSearchResult } from '$lib/types';

  let film: FilmDetail | null = null;
  let loading = true;
  let error: string | null = null;
  let associating = false;
  let showAssociateModal = false;
  let searchResults: any[] = [];
  let selectedResult: any = null;

  // Provider search state
  let showProviderSearchModal = false;
  let searchingProviders = false;
  let providerResults: ProviderSearchResult[] = [];
  let associatingProvider = false;

  const TMDB_IMAGE_BASE = 'https://image.tmdb.org/t/p/w500';

  onMount(async () => {
    await user.checkAuth();

    if (!$isAuthenticated) {
      goto('/');
      return;
    }

    await loadData();
  });

  async function loadData() {
    loading = true;
    error = null;

    try {
      const name = decodeURIComponent($page.params.name);
      film = await api.getFilmDetail(name);
    } catch (err: any) {
      error = err.message || 'Errore nel caricamento dei dettagli';
      snackbar(error ?? 'Errore sconosciuto', undefined, true);
    } finally {
      loading = false;
    }
  }

  function formatGenres(genreIds: number[]): string {
    const genreMap: Record<number, string> = {
      28: 'Azione', 12: 'Avventura', 16: 'Animazione', 35: 'Commedia', 80: 'Crimine',
      99: 'Documentario', 18: 'Dramma', 10751: 'Famiglia', 14: 'Fantasy', 36: 'Storia',
      27: 'Horror', 10402: 'Musica', 9648: 'Mistero', 10749: 'Romance', 878: 'Fantascienza',
      10770: 'Film TV', 53: 'Thriller', 10752: 'Guerra', 37: 'Western',
    };
    return genreIds.map(id => genreMap[id] || 'Altro').join(', ');
  }

  async function associateMetadata() {
    if (!film) return;
    associating = true;
    try {
      const cleanName = film.name.replace(/\s*\(\d{4}\)\s*/g, '').trim();
      const searchResponse = await api.search(cleanName, 'film');
      if (searchResponse.films && searchResponse.films.length > 0) {
        searchResults = searchResponse.films;
        showAssociateModal = true;
      } else {
        snackbar('Nessun risultato trovato su TMDB', undefined, true);
      }
    } catch (err: any) {
      snackbar(err.message || 'Errore nella ricerca dei metadati', undefined, true);
    } finally {
      associating = false;
    }
  }

  async function confirmAssociation() {
    if (!film || !selectedResult || !selectedResult.tmdb_id) return;
    try {
      film = await api.updateFilmMetadata(film.name, selectedResult.tmdb_id);
      snackbar('Metadati associati con successo!', undefined, false);
      showAssociateModal = false;
      searchResults = [];
      selectedResult = null;
    } catch (err: any) {
      snackbar(err.message || 'Errore nell\'associazione dei metadati', undefined, true);
    }
  }

  function closeModal() {
    showAssociateModal = false;
    searchResults = [];
    selectedResult = null;
  }

  async function searchProviders() {
    if (!film) return;
    
    showProviderSearchModal = true;
    searchingProviders = true;
    providerResults = [];
    
    try {
      const cleanName = film.name.replace(/\s*\(\d{4}\)\s*/g, '').trim();
      providerResults = await api.searchMediaProviders(cleanName, 'film');
      
      if (providerResults.length === 0) {
        snackbar('Nessun provider trovato', undefined, true);
      }
    } catch (err: any) {
      snackbar(err.message || 'Errore nella ricerca dei provider', undefined, true);
    } finally {
      searchingProviders = false;
    }
  }

  async function selectProvider(provider: ProviderSearchResult) {
    if (!film || !provider.media_id) return;
    
    associatingProvider = true;
    try {
      film = await api.associateFilmProvider(
        film.name,
        provider.provider,
        provider.media_id,
        provider.slug
      );
      snackbar('Provider associato con successo!', undefined, false);
      closeProviderModal();
      await loadData();
    } catch (err: any) {
      snackbar(err.message || 'Errore nell\'associazione del provider', undefined, true);
    } finally {
      associatingProvider = false;
    }
  }

  function closeProviderModal() {
    showProviderSearchModal = false;
    providerResults = [];
    searchingProviders = false;
    associatingProvider = false;
  }
</script>

<svelte:head>
  <title>YUNA - {film?.name || 'Film'}</title>
</svelte:head>

<div class="film-detail-page">
  <!-- Top Bar -->
  <header class="top-bar">
    <div class="top-bar-content">
      <button class="back-button" on:click={() => goto('/films')}>
        <Icon icon="mdi:arrow-left" width="24" />
      </button>
      <h1 class="page-title">Dettagli Film</h1>
    </div>
  </header>

  <!-- Main Content -->
  <main class="main-content">
    {#if loading}
      <div class="loading-container">
        <LinearProgressEstimate sToHalfway={2} />
        <p>Caricamento dettagli...</p>
      </div>
    {:else if error}
      <div class="error-container">
        <Card variant="outlined">
          <div class="error-content">
            <Icon icon="mdi:alert-circle" width="48" color="var(--m3c-error)" />
            <p>{error}</p>
            <Button variant="filled" onclick={loadData}>Riprova</Button>
          </div>
        </Card>
      </div>
    {:else if film}
      <div class="film-detail">
        <!-- Poster and Base Info -->
        <div class="detail-header">
          {#if film.poster_path}
            <img
              src="{TMDB_IMAGE_BASE}{film.poster_path}"
              alt={film.name}
              class="poster-image"
            />
          {:else}
            <div class="poster-placeholder">
              <Icon icon="mdi:movie" width="64" />
            </div>
          {/if}

          <div class="header-info">
            <h2 class="film-title">{film.name}</h2>

            {#if !film.provider}
              <div class="associate-banner provider-warning">
                <Icon icon="mdi:link-variant-off" width="20" />
                <span>Nessun provider associato</span>
                <Button 
                  variant="filled" 
                  onclick={searchProviders} 
                  disabled={searchingProviders}
                >
                  {#if searchingProviders}
                    <Icon icon="mdi:loading" width="16" class="spinning" />
                    Ricerca in corso...
                  {:else}
                    <Icon icon="mdi:magnify" width="16" />
                    Cerca provider
                  {/if}
                </Button>
              </div>
            {/if}

            {#if !film.tmdb_id}
              <div class="associate-banner">
                <Icon icon="mdi:alert-circle-outline" width="20" />
                <span>Questo film non ha metadati associati</span>
                <Button 
                  variant="filled" 
                  onclick={associateMetadata} 
                  disabled={associating}
                >
                  {#if associating}
                    <Icon icon="mdi:loading" width="16" class="spinning" />
                    Ricerca in corso...
                  {:else}
                    <Icon icon="mdi:link" width="16" />
                    Associa Metadati
                  {/if}
                </Button>
              </div>
            {/if}

            <div class="basic-info">
              <div class="info-grid">
                {#if film.year}
                  <div class="info-item">
                    <span class="label">Anno:</span>
                    <span class="value">{film.year}</span>
                  </div>
                {/if}

                {#if film.vote_average}
                  <div class="info-item">
                    <span class="label">Voto:</span>
                    <span class="value">⭐ {film.vote_average.toFixed(1)}/10</span>
                  </div>
                {/if}

                {#if film.provider}
                  <div class="info-item">
                    <span class="label">Provider:</span>
                    <span class="value">{film.provider}</span>
                  </div>
                {/if}

                <div class="info-item">
                  <span class="label">Stato:</span>
                  <span class="value">
                    {#if film.downloaded}
                      <Icon icon="mdi:check-circle" width="16" color="var(--m3c-primary)" /> Scaricato
                    {:else}
                      <Icon icon="mdi:download-outline" width="16" /> Non scaricato
                    {/if}
                  </span>
                </div>
              </div>

              {#if film.genre_ids && film.genre_ids.length > 0}
                <div class="info-item full-width">
                  <span class="label">Generi:</span>
                  <div class="genre-chips">
                    {#each film.genre_ids as genreId}
                      <span class="genre-chip">{formatGenres([genreId])}</span>
                    {/each}
                  </div>
                </div>
              {/if}
            </div>
          </div>
        </div>

        <!-- Overview -->
        {#if film.overview}
          <section class="section">
            <h3 class="section-title">Trama</h3>
            <Card variant="outlined">
              <p class="overview-text">{film.overview}</p>
            </Card>
          </section>
        {/if}
      </div>
    {/if}
  </main>

  <!-- Association Modal -->
  {#if showAssociateModal}
    <div 
      class="modal-overlay" 
      on:click={closeModal}
      on:keydown={(e) => e.key === 'Escape' && closeModal()}
      role="button"
      tabindex="0"
    >
      <div
        class="modal-content"
        on:click={(e) => e.stopPropagation()}
        on:keydown={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        tabindex="-1"
      >
        <div class="modal-header">
          <h2 class="modal-title">Seleziona Film da Associare</h2>
          <button class="close-button" on:click={closeModal}>
            <Icon icon="mdi:close" width="24" />
          </button>
        </div>

        <div class="modal-body">
          <p class="modal-subtitle">Trovati {searchResults.length} risultati per "{film?.name}"</p>
          
          <div class="results-list">
            {#each searchResults as result}
              <div 
                class="result-item" 
                class:selected={selectedResult === result}
                on:click={() => selectedResult = result}
                on:keydown={(e) => (e.key === 'Enter' || e.key === ' ') && (selectedResult = result)}
                role="button"
                tabindex="0"
              >
                <div class="result-item-content">
                  {#if result.poster}
                    <img src={result.poster} alt={result.name} class="result-item-poster" />
                  {:else}
                    <div class="result-item-poster-placeholder">
                      <Icon icon="mdi:image-off" width="24" />
                    </div>
                  {/if}
                  
                  <div class="result-item-info">
                    <h3 class="result-item-title">{result.name}</h3>
                    <div class="result-item-meta">
                      {#if result.year}
                        <span class="meta-badge">
                          <Icon icon="mdi:calendar" width="14" />
                          {result.year}
                        </span>
                      {/if}
                      {#if result.rating}
                        <span class="meta-badge rating">
                          <Icon icon="mdi:star" width="14" />
                          {result.rating.toFixed(1)}
                        </span>
                      {/if}
                      {#if result.runtime}
                        <span class="meta-badge">
                          <Icon icon="mdi:clock-outline" width="14" />
                          {result.runtime} min
                        </span>
                      {/if}
                    </div>
                    {#if result.genres && result.genres.length > 0}
                      <div class="result-item-genres">
                        {#each result.genres.slice(0, 3) as genre}
                          <span class="genre-pill">{genre}</span>
                        {/each}
                      </div>
                    {/if}
                    {#if result.overview}
                      <p class="result-item-overview">{result.overview}</p>
                    {/if}
                  </div>
                </div>
                
                {#if selectedResult === result}
                  <div class="selected-badge">
                    <Icon icon="mdi:check-circle" width="24" />
                  </div>
                {/if}
              </div>
            {/each}
          </div>
        </div>

        <div class="modal-footer">
          <Button variant="text" onclick={closeModal}>Annulla</Button>
          <Button 
            variant="filled" 
            onclick={confirmAssociation}
            disabled={!selectedResult}
          >
            Conferma Associazione
          </Button>
        </div>
      </div>
    </div>
  {/if}

  <!-- Provider Search Modal -->
  {#if showProviderSearchModal}
    <div class="modal-overlay" on:click={closeProviderModal} on:keydown={(e) => e.key === 'Escape' && closeProviderModal()} role="presentation">
      <div class="modal-content" on:click|stopPropagation on:keydown|stopPropagation role="dialog" aria-modal="true" tabindex="-1">
        <div class="modal-header">
          <h2>Cerca provider per "{film?.name}"</h2>
          <button class="icon-button" on:click={closeProviderModal}>
            <Icon icon="mdi:close" width="24" />
          </button>
        </div>

        <div class="modal-body">
          {#if searchingProviders}
            <div class="modal-loading">
              <CircularProgress />
              <p>Ricerca in corso sui provider disponibili...</p>
            </div>
          {:else if providerResults.length > 0}
            <p class="modal-subtitle">Trovati {providerResults.length} risultati</p>
            <div class="results-list">
              {#each providerResults as result}
                <button
                  class="result-item provider-result"
                  on:click={() => selectProvider(result)}
                  disabled={associatingProvider}
                >
                  {#if result.poster}
                    <img src={result.poster} alt={result.title} class="result-poster" />
                  {:else}
                    <div class="result-poster-placeholder">
                      <Icon icon="mdi:image-off" width="24" />
                    </div>
                  {/if}

                  <div class="result-info">
                    <h3>{result.title}</h3>
                    <div class="result-meta">
                      <span class="provider-badge">{result.provider}</span>
                      {#if result.year}<span><Icon icon="mdi:calendar" width="14" /> {result.year}</span>{/if}
                    </div>
                  </div>

                  <div class="action-arrow">
                    <Icon icon="mdi:chevron-right" width="24" />
                  </div>
                </button>
              {/each}
            </div>
          {:else}
            <div class="modal-empty">
              <Icon icon="mdi:magnify-close" width="48" color="var(--m3c-outline)" />
              <p>Nessun provider trovato</p>
            </div>
          {/if}
        </div>

        <div class="modal-footer">
          <Button variant="text" onclick={closeProviderModal} disabled={associatingProvider}>
            {associatingProvider ? 'Associazione in corso...' : 'Chiudi'}
          </Button>
        </div>
      </div>
    </div>
  {/if}

</div>

<style>
  .film-detail-page {
    min-height: 100vh;
    background: var(--m3c-surface);
  }

  .top-bar {
    position: sticky;
    top: 0;
    z-index: 100;
    background: var(--m3c-surface);
    border-bottom: 1px solid var(--m3c-outline-variant);
  }

  .top-bar-content {
    max-width: 1200px;
    margin: 0 auto;
    padding: 12px 16px;
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .back-button {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 40px;
    height: 40px;
    border: none;
    background: transparent;
    color: var(--m3c-on-surface);
    border-radius: var(--m3-shape-full);
    cursor: pointer;
    transition: background 0.2s;
  }

  .back-button:hover {
    background: var(--m3c-surface-container-highest);
  }

  .page-title {
    font-size: 22px;
    font-weight: 500;
    color: var(--m3c-on-surface);
    margin: 0;
  }

  .main-content {
    max-width: 1200px;
    margin: 0 auto;
    padding: 24px 20px;
    padding-bottom: 140px;
    box-sizing: border-box;
  }

  .loading-container,
  .error-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 16px;
    padding: 48px 16px;
    text-align: center;
  }

  .error-content {
    padding: 32px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;
  }

  .film-detail {
    display: flex;
    flex-direction: column;
    gap: 24px;
  }

  .detail-header {
    display: flex;
    gap: 24px;
    align-items: flex-start;
  }

  .poster-placeholder {
    width: 200px;
    height: 300px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--m3c-surface-container-high);
    border-radius: var(--m3-shape-medium);
    color: var(--m3c-outline);
  }

  .header-info {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .film-title {
    font-size: 28px;
    font-weight: 600;
    color: var(--m3c-on-surface);
    margin: 0;
  }

  .basic-info {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .info-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 12px;
  }

  .info-item {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .info-item.full-width {
    grid-column: 1 / -1;
  }

  .genre-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .genre-chip {
    display: inline-block;
    padding: 6px 12px;
    background: var(--m3c-secondary-container);
    color: var(--m3c-on-secondary-container);
    border-radius: 16px;
    font-size: 13px;
    font-weight: 500;
  }

  .associate-banner {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 16px;
    background: var(--m3c-warning-container);
    color: var(--m3c-on-warning-container);
    border-radius: var(--m3-shape-medium);
    font-size: 14px;
  }

  .associate-banner.provider-warning {
    background: var(--m3c-tertiary-container);
    color: var(--m3c-on-tertiary-container);
  }

  .section {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .section-title {
    font-size: 20px;
    font-weight: 600;
    color: var(--m3c-on-surface);
    margin: 0;
  }

  .overview-text {
    font-size: 14px;
    line-height: 1.6;
    color: var(--m3c-on-surface-variant);
    margin: 16px;
  }

  .poster-image {
    width: 200px;
    height: 300px;
    border-radius: var(--m3-shape-medium);
    object-fit: cover;
    flex-shrink: 0;
  }

  :global(.spinning) {
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }

  .label {
    font-size: 12px;
    font-weight: 600;
    color: var(--m3c-on-surface-variant);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .value {
    font-size: 14px;
    color: var(--m3c-on-surface);
    display: flex;
    align-items: center;
    gap: 4px;
  }

  @media (max-width: 768px) {
    .detail-header {
      flex-direction: column;
      align-items: center;
    }

    .poster-image,
    .poster-placeholder {
      width: 160px;
      height: 240px;
    }

    .modal-content {
      max-width: 100%;
      max-height: 100vh;
      border-radius: 0;
    }

    .result-item-content {
      flex-direction: column;
    }

    .result-item-poster,
    .result-item-poster-placeholder {
      width: 100%;
      height: 180px;
    }
  }

  /* Modal Styles */
  .modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.6);
    backdrop-filter: blur(4px);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    padding: 16px;
  }

  .modal-content {
    background: var(--m3c-surface);
    border-radius: var(--m3-shape-extra-large);
    max-width: 700px;
    width: 100%;
    max-height: 90vh;
    display: flex;
    flex-direction: column;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  }

  .modal-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 20px 24px;
    border-bottom: 1px solid var(--m3c-outline-variant);
  }

  .modal-title {
    font-size: 22px;
    font-weight: 600;
    color: var(--m3c-on-surface);
    margin: 0;
  }

  .close-button {
    background: none;
    border: none;
    cursor: pointer;
    color: var(--m3c-on-surface-variant);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 8px;
    border-radius: 50%;
    transition: background 0.2s;
  }

  .close-button:hover {
    background: var(--m3c-surface-container-high);
  }

  .modal-body {
    flex: 1;
    overflow-y: auto;
    padding: 24px;
  }

  .modal-subtitle {
    font-size: 14px;
    color: var(--m3c-on-surface-variant);
    margin: 0 0 16px 0;
  }

  .results-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .result-item {
    position: relative;
    border: 2px solid var(--m3c-outline-variant);
    border-radius: var(--m3-shape-medium);
    padding: 16px;
    cursor: pointer;
    transition: all 0.2s;
  }

  .result-item:hover {
    border-color: var(--m3c-primary);
    background: var(--m3c-surface-container-lowest);
  }

  .result-item.selected {
    border-color: var(--m3c-primary);
    background: var(--m3c-primary-container);
  }

  .result-item-content {
    display: flex;
    gap: 16px;
  }

  .result-item-poster {
    width: 80px;
    height: 120px;
    object-fit: cover;
    border-radius: var(--m3-shape-small);
    flex-shrink: 0;
  }

  .result-item-poster-placeholder {
    width: 80px;
    height: 120px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--m3c-surface-container);
    border-radius: var(--m3-shape-small);
    color: var(--m3c-outline);
    flex-shrink: 0;
  }

  .result-item-info {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .result-item-title {
    font-size: 16px;
    font-weight: 600;
    color: var(--m3c-on-surface);
    margin: 0;
  }

  .result-item-meta {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }

  .meta-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 4px 8px;
    background: var(--m3c-surface-container);
    border-radius: 12px;
    font-size: 12px;
    color: var(--m3c-on-surface-variant);
  }

  .meta-badge.rating {
    color: var(--m3c-primary);
  }

  .result-item-genres {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
  }

  .genre-pill {
    padding: 4px 10px;
    background: var(--m3c-secondary-container);
    color: var(--m3c-on-secondary-container);
    border-radius: 16px;
    font-size: 11px;
    font-weight: 500;
  }

  .result-item-overview {
    font-size: 13px;
    line-height: 1.4;
    color: var(--m3c-on-surface-variant);
    margin: 4px 0 0 0;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .selected-badge {
    position: absolute;
    top: 16px;
    right: 16px;
    color: var(--m3c-primary);
  }

  .modal-footer {
    display: flex;
    justify-content: flex-end;
    gap: 12px;
    padding: 16px 24px;
    border-top: 1px solid var(--m3c-outline-variant);
  }

  /* Provider search modal specific styles */
  .modal-loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;
    padding: 48px 24px;
    text-align: center;
  }

  .modal-loading p {
    font-size: 14px;
    color: var(--m3c-on-surface-variant);
    margin: 0;
  }

  .modal-empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;
    padding: 48px 24px;
    text-align: center;
  }

  .modal-empty p {
    font-size: 14px;
    color: var(--m3c-on-surface-variant);
    margin: 0;
  }

  .result-item.provider-result {
    border: 1px solid var(--m3c-outline-variant);
  }

  .result-item.provider-result:hover {
    background: var(--m3c-surface-container-high);
    border-color: var(--m3c-primary);
  }

  .result-item.provider-result:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .provider-badge {
    display: inline-flex;
    align-items: center;
    padding: 4px 10px;
    background: var(--m3c-primary-container);
    color: var(--m3c-on-primary-container);
    border-radius: var(--m3-shape-small);
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .action-arrow {
    display: flex;
    align-items: center;
    color: var(--m3c-on-surface-variant);
  }

  :global(.spinning) {
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
</style>
