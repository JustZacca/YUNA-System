<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { user, isAuthenticated } from '$lib/stores';
  import { api } from '$lib/api';
  import { Button, Card, LinearProgressEstimate, snackbar } from 'm3-svelte';
  import Icon from '@iconify/svelte';
  import type { SeriesDetail } from '$lib/types';

  let series: SeriesDetail | null = null;
  let loading = true;
  let error: string | null = null;
  let associating = false;
  let showAssociateModal = false;
  let searchResults: any[] = [];
  let selectedResult: any = null;

  const TMDB_IMAGE_BASE = 'https://image.tmdb.org/t/p/w500';

  const GENRE_MAP: Record<number, string> = {
    10759: 'Azione e Avventura', 16: 'Animazione', 35: 'Commedia', 80: 'Crimine',
    99: 'Documentario', 18: 'Dramma', 10751: 'Famiglia', 10762: 'Ragazzi',
    9648: 'Mistero', 10763: 'News', 10764: 'Reality', 10765: 'Sci-Fi e Fantasy',
    10766: 'Soap', 10767: 'Talk Show', 10768: 'Guerra e Politica', 37: 'Western',
  };

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
      series = await api.getSeriesDetail(name);
    } catch (err: any) {
      error = err.message || 'Errore nel caricamento dei dettagli';
      snackbar(error ?? 'Errore sconosciuto', undefined, true);
    } finally {
      loading = false;
    }
  }

  function getProgressPercent(): number {
    if (!series || !series.episodes_total || series.episodes_total === 0) return 0;
    return Math.min(100, Math.round((series.episodes_downloaded / series.episodes_total) * 100));
  }

  function getProgressColor(): string {
    const percent = getProgressPercent();
    if (percent >= 100) return 'var(--m3c-primary)';
    if (percent >= 50) return 'var(--m3c-tertiary)';
    return 'var(--m3c-secondary)';
  }

  async function associateMetadata() {
    if (!series) return;
    associating = true;
    try {
      const cleanName = series.name.replace(/\s*\(\d{4}\)\s*/g, '').trim();
      const searchResponse = await api.search(cleanName, 'series');
      if (searchResponse.series && searchResponse.series.length > 0) {
        searchResults = searchResponse.series;
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
    if (!series || !selectedResult || !selectedResult.tmdb_id) return;
    try {
      series = await api.updateSeriesMetadata(series.name, selectedResult.tmdb_id);
      snackbar('Metadati associati con successo!', undefined, false);
      closeModal();
    } catch (err: any) {
      snackbar(err.message || 'Errore nell\'associazione dei metadati', undefined, true);
    }
  }

  function closeModal() {
    showAssociateModal = false;
    searchResults = [];
    selectedResult = null;
  }
</script>

<svelte:head>
  <title>YUNA - {series?.name || 'Serie TV'}</title>
</svelte:head>

<div class="detail-page">
  <!-- Top Bar -->
  <header class="top-bar">
    <div class="top-bar-content">
      <button class="back-button" on:click={() => goto('/series')}>
        <Icon icon="mdi:arrow-left" width="24" />
      </button>
      <h1 class="page-title">Dettagli Serie TV</h1>
    </div>
  </header>

  <main class="main-content">
    {#if loading}
      <div class="loading-container">
        <LinearProgressEstimate sToHalfway={2} />
        <p>Caricamento...</p>
      </div>
    {:else if error}
      <div class="state-container">
        <Card variant="outlined">
          <div class="state-content">
            <Icon icon="mdi:alert-circle" width="48" color="var(--m3c-error)" />
            <h3>Errore</h3>
            <p>{error}</p>
            <Button variant="filled" onclick={loadData}>Riprova</Button>
          </div>
        </Card>
      </div>
    {:else if series}
      <div class="detail-layout">
        <!-- Hero Section -->
        <section class="hero-section">
          <div class="poster-wrapper">
            {#if series.poster_path}
              <img
                src="{TMDB_IMAGE_BASE}{series.poster_path}"
                alt={series.name}
                class="poster"
              />
            {:else}
              <div class="poster-placeholder">
                <Icon icon="mdi:television" width="64" />
              </div>
            {/if}
          </div>

          <div class="hero-info">
            <h1 class="title">{series.name}</h1>

            <!-- Metadata Row -->
            <div class="meta-row">
              {#if series.year}
                <span class="meta-chip">
                  <Icon icon="mdi:calendar" width="16" />
                  {series.year}
                </span>
              {/if}
              {#if series.vote_average}
                <span class="meta-chip rating">
                  <Icon icon="mdi:star" width="16" />
                  {series.vote_average.toFixed(1)}
                </span>
              {/if}
              {#if series.provider}
                <span class="meta-chip">
                  <Icon icon="mdi:web" width="16" />
                  {series.provider}
                </span>
              {/if}
            </div>

            <!-- Genres -->
            {#if series.genre_ids && series.genre_ids.length > 0}
              <div class="genres-row">
                {#each series.genre_ids as genreId}
                  <span class="genre-chip">{GENRE_MAP[genreId] || 'Altro'}</span>
                {/each}
              </div>
            {/if}

            <!-- No Metadata Warning -->
            {#if !series.tmdb_id}
              <div class="warning-banner">
                <Icon icon="mdi:alert-circle-outline" width="20" />
                <span>Metadati non associati</span>
                <Button variant="tonal" onclick={associateMetadata} disabled={associating}>
                  {#if associating}
                    <Icon icon="mdi:loading" width="18" class="spinning" />
                  {:else}
                    <Icon icon="mdi:link" width="18" />
                  {/if}
                  Associa
                </Button>
              </div>
            {/if}
          </div>
        </section>

        <!-- Synopsis -->
        {#if series.overview}
          <section class="content-section">
            <h2 class="section-title">Trama</h2>
            <div class="synopsis-card">
              <p>{series.overview}</p>
            </div>
          </section>
        {/if}

        <!-- Episodes Section -->
        {#if series.episodes_downloaded > 0 || series.episodes_total > 0}
          <section class="content-section">
            <h2 class="section-title">Episodi</h2>

            <!-- Stats Grid -->
            <div class="stats-grid stats-2col">
              <div class="stat-card">
                <div class="stat-icon" style="background: var(--m3c-primary-container); color: var(--m3c-on-primary-container);">
                  <Icon icon="mdi:check-circle" width="24" />
                </div>
                <div class="stat-info">
                  <span class="stat-value">{series.episodes_downloaded}</span>
                  <span class="stat-label">Scaricati</span>
                </div>
              </div>

              <div class="stat-card">
                <div class="stat-icon" style="background: var(--m3c-secondary-container); color: var(--m3c-on-secondary-container);">
                  <Icon icon="mdi:playlist-check" width="24" />
                </div>
                <div class="stat-info">
                  <span class="stat-value">{series.episodes_total || '?'}</span>
                  <span class="stat-label">Totali</span>
                </div>
              </div>
            </div>

            <!-- Progress -->
            <div class="progress-card">
              <div class="progress-header">
                <span class="progress-title">Progresso download</span>
                <span class="progress-percent">{getProgressPercent()}%</span>
              </div>
              <div class="progress-bar">
                <div class="progress-fill" style="width: {getProgressPercent()}%; background: {getProgressColor()}"></div>
              </div>
              <span class="progress-detail">
                {series.episodes_downloaded} di {series.episodes_total || '?'} episodi
              </span>
            </div>
          </section>
        {/if}
      </div>
    {:else}
      <div class="state-container">
        <Card variant="outlined">
          <div class="state-content">
            <Icon icon="mdi:alert-circle" width="48" color="var(--m3c-error)" />
            <h3>Serie non trovata</h3>
            <Button variant="filled" onclick={() => goto('/series')}>Torna alla lista</Button>
          </div>
        </Card>
      </div>
    {/if}
  </main>

  <!-- Association Modal -->
  {#if showAssociateModal}
    <div class="modal-overlay" on:click={closeModal} on:keydown={(e) => e.key === 'Escape' && closeModal()} role="button" tabindex="0">
      <div class="modal-content" on:click|stopPropagation on:keydown|stopPropagation role="dialog" aria-modal="true">
        <div class="modal-header">
          <h2>Seleziona Serie TV</h2>
          <button class="icon-button" on:click={closeModal}>
            <Icon icon="mdi:close" width="24" />
          </button>
        </div>

        <div class="modal-body">
          <p class="modal-subtitle">Trovati {searchResults.length} risultati per "{series?.name}"</p>

          <div class="results-list">
            {#each searchResults as result}
              <button
                class="result-item"
                class:selected={selectedResult === result}
                on:click={() => selectedResult = result}
              >
                {#if result.poster}
                  <img src={result.poster} alt={result.name} class="result-poster" />
                {:else}
                  <div class="result-poster-placeholder">
                    <Icon icon="mdi:image-off" width="24" />
                  </div>
                {/if}

                <div class="result-info">
                  <h3>{result.name}</h3>
                  <div class="result-meta">
                    {#if result.year}<span><Icon icon="mdi:calendar" width="14" /> {result.year}</span>{/if}
                    {#if result.rating}<span class="rating"><Icon icon="mdi:star" width="14" /> {result.rating.toFixed(1)}</span>{/if}
                    {#if result.seasons}<span><Icon icon="mdi:television" width="14" /> {result.seasons} stagioni</span>{/if}
                  </div>
                  {#if result.genres?.length > 0}
                    <div class="result-genres">
                      {#each result.genres.slice(0, 3) as genre}
                        <span>{genre}</span>
                      {/each}
                    </div>
                  {/if}
                </div>

                {#if selectedResult === result}
                  <div class="selected-check">
                    <Icon icon="mdi:check-circle" width="24" />
                  </div>
                {/if}
              </button>
            {/each}
          </div>
        </div>

        <div class="modal-footer">
          <Button variant="text" onclick={closeModal}>Annulla</Button>
          <Button variant="filled" onclick={confirmAssociation} disabled={!selectedResult}>
            Conferma
          </Button>
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  .detail-page {
    min-height: 100vh;
    background: var(--m3c-surface);
  }

  /* Top Bar */
  .top-bar {
    position: sticky;
    top: 0;
    z-index: 100;
    background: var(--m3c-surface);
    border-bottom: 1px solid var(--m3c-outline-variant);
  }

  .top-bar-content {
    max-width: 1000px;
    margin: 0 auto;
    padding: 12px 24px;
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .back-button {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 40px;
    height: 40px;
    border: none;
    background: none;
    color: var(--m3c-on-surface);
    cursor: pointer;
    border-radius: var(--m3-shape-full);
    transition: background 0.2s;
  }

  .back-button:hover {
    background: var(--m3c-surface-container-high);
  }

  .page-title {
    font-size: 22px;
    font-weight: 500;
    color: var(--m3c-on-surface);
    margin: 0;
  }

  /* Main Content */
  .main-content {
    max-width: 1000px;
    margin: 0 auto;
    padding: 24px;
    padding-bottom: 120px;
    overflow-y: auto;
    max-height: calc(100vh - 64px);
  }

  .loading-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;
    padding: 64px 24px;
    text-align: center;
    color: var(--m3c-on-surface-variant);
  }

  .state-container {
    display: flex;
    justify-content: center;
    padding: 64px 24px;
  }

  .state-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;
    text-align: center;
    padding: 48px 32px;
  }

  .state-content h3 {
    font-size: 20px;
    font-weight: 500;
    color: var(--m3c-on-surface);
    margin: 0;
  }

  .state-content p {
    font-size: 14px;
    color: var(--m3c-on-surface-variant);
    margin: 0;
  }

  /* Detail Layout */
  .detail-layout {
    display: flex;
    flex-direction: column;
    gap: 32px;
  }

  /* Hero Section */
  .hero-section {
    display: flex;
    gap: 24px;
    align-items: flex-start;
  }

  .poster-wrapper {
    flex-shrink: 0;
  }

  .poster {
    width: 180px;
    height: 270px;
    object-fit: cover;
    border-radius: var(--m3-shape-large);
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
  }

  .poster-placeholder {
    width: 180px;
    height: 270px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--m3c-surface-container-high);
    border-radius: var(--m3-shape-large);
    color: var(--m3c-outline);
  }

  .hero-info {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .title {
    font-size: 28px;
    font-weight: 600;
    color: var(--m3c-on-surface);
    margin: 0;
    line-height: 1.3;
  }

  .meta-row {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .meta-chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    background: var(--m3c-surface-container);
    border: 1px solid var(--m3c-outline-variant);
    border-radius: var(--m3-shape-full);
    font-size: 13px;
    font-weight: 500;
    color: var(--m3c-on-surface-variant);
  }

  .meta-chip.rating {
    color: #f59e0b;
    border-color: #f59e0b;
  }

  .genres-row {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .genre-chip {
    padding: 6px 14px;
    background: var(--m3c-secondary-container);
    color: var(--m3c-on-secondary-container);
    border-radius: var(--m3-shape-full);
    font-size: 13px;
    font-weight: 500;
  }

  .warning-banner {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 16px;
    background: var(--m3c-error-container);
    color: var(--m3c-on-error-container);
    border-radius: var(--m3-shape-medium);
    font-size: 14px;
  }

  /* Content Sections */
  .content-section {
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

  .synopsis-card {
    padding: 20px;
    background: var(--m3c-surface-container);
    border: 1px solid var(--m3c-outline-variant);
    border-radius: var(--m3-shape-large);
  }

  .synopsis-card p {
    font-size: 14px;
    line-height: 1.7;
    color: var(--m3c-on-surface);
    margin: 0;
  }

  /* Stats Grid */
  .stats-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
  }

  .stats-grid.stats-2col {
    grid-template-columns: repeat(2, 1fr);
  }

  .stat-card {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 16px;
    background: var(--m3c-surface-container);
    border: 1px solid var(--m3c-outline-variant);
    border-radius: var(--m3-shape-large);
  }

  .stat-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 48px;
    height: 48px;
    border-radius: var(--m3-shape-medium);
  }

  .stat-info {
    display: flex;
    flex-direction: column;
  }

  .stat-value {
    font-size: 24px;
    font-weight: 700;
    color: var(--m3c-on-surface);
  }

  .stat-label {
    font-size: 12px;
    font-weight: 500;
    color: var(--m3c-on-surface-variant);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  /* Progress Card */
  .progress-card {
    padding: 20px;
    background: var(--m3c-surface-container);
    border: 1px solid var(--m3c-outline-variant);
    border-radius: var(--m3-shape-large);
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .progress-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .progress-title {
    font-size: 14px;
    font-weight: 500;
    color: var(--m3c-on-surface);
  }

  .progress-percent {
    font-size: 16px;
    font-weight: 700;
    color: var(--m3c-primary);
  }

  .progress-bar {
    height: 8px;
    background: var(--m3c-surface-container-highest);
    border-radius: 4px;
    overflow: hidden;
  }

  .progress-fill {
    height: 100%;
    border-radius: 4px;
    transition: width 0.3s ease;
  }

  .progress-detail {
    font-size: 12px;
    color: var(--m3c-on-surface-variant);
  }

  /* Modal */
  .modal-overlay {
    position: fixed;
    inset: 0;
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
    max-width: 600px;
    width: 100%;
    max-height: 85vh;
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

  .modal-header h2 {
    font-size: 22px;
    font-weight: 600;
    color: var(--m3c-on-surface);
    margin: 0;
  }

  .icon-button {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 40px;
    height: 40px;
    border: none;
    background: none;
    color: var(--m3c-on-surface-variant);
    cursor: pointer;
    border-radius: var(--m3-shape-full);
    transition: background 0.2s;
  }

  .icon-button:hover {
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
    display: flex;
    gap: 16px;
    padding: 16px;
    background: var(--m3c-surface-container);
    border: 2px solid var(--m3c-outline-variant);
    border-radius: var(--m3-shape-large);
    cursor: pointer;
    transition: all 0.2s;
    text-align: left;
  }

  .result-item:hover {
    border-color: var(--m3c-primary);
  }

  .result-item.selected {
    border-color: var(--m3c-primary);
    background: var(--m3c-primary-container);
  }

  .result-poster {
    width: 70px;
    height: 100px;
    object-fit: cover;
    border-radius: var(--m3-shape-medium);
    flex-shrink: 0;
  }

  .result-poster-placeholder {
    width: 70px;
    height: 100px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--m3c-surface-container-high);
    border-radius: var(--m3-shape-medium);
    color: var(--m3c-outline);
    flex-shrink: 0;
  }

  .result-info {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .result-info h3 {
    font-size: 15px;
    font-weight: 600;
    color: var(--m3c-on-surface);
    margin: 0;
    line-height: 1.3;
  }

  .result-item.selected .result-info h3 {
    color: var(--m3c-on-primary-container);
  }

  .result-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    font-size: 12px;
    color: var(--m3c-on-surface-variant);
  }

  .result-meta span {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .result-meta .rating {
    color: #f59e0b;
  }

  .result-genres {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .result-genres span {
    padding: 3px 8px;
    background: var(--m3c-surface-container-high);
    color: var(--m3c-on-surface-variant);
    border-radius: var(--m3-shape-full);
    font-size: 11px;
  }

  .result-item.selected .result-genres span {
    background: var(--m3c-primary);
    color: var(--m3c-on-primary);
  }

  .selected-check {
    position: absolute;
    top: 12px;
    right: 12px;
    color: var(--m3c-on-primary-container);
  }

  .modal-footer {
    display: flex;
    justify-content: flex-end;
    gap: 12px;
    padding: 16px 24px;
    border-top: 1px solid var(--m3c-outline-variant);
  }

  :global(.spinning) {
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }

  /* Responsive */
  @media (max-width: 768px) {
    .top-bar-content {
      padding: 12px 16px;
    }

    .main-content {
      padding: 16px;
      padding-bottom: 100px;
    }

    .hero-section {
      flex-direction: column;
      align-items: center;
      text-align: center;
    }

    .poster {
      width: 160px;
      height: 240px;
    }

    .poster-placeholder {
      width: 160px;
      height: 240px;
    }

    .title {
      font-size: 24px;
    }

    .meta-row, .genres-row {
      justify-content: center;
    }

    .warning-banner {
      flex-direction: column;
      text-align: center;
    }

    .stats-grid, .stats-grid.stats-2col {
      grid-template-columns: 1fr;
    }

    .stat-card {
      justify-content: center;
    }

    .modal-content {
      max-height: 100vh;
      border-radius: 0;
    }
  }
</style>
