<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { user, isAuthenticated } from '$lib/stores';
  import { api } from '$lib/api';
  import { Button, Card, LinearProgressEstimate, snackbar } from 'm3-svelte';
  import Icon from '@iconify/svelte';
  import type { FilmBase } from '$lib/types';

  let filmsList: FilmBase[] = [];
  let loading = true;
  let error: string | null = null;
  let gridSize: 'small' | 'medium' | 'large' = 'medium';

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
      const response = await api.getFilmsList();
      filmsList = response.items;
    } catch (err: any) {
      error = err.message || 'Errore nel caricamento';
      snackbar(error ?? 'Errore sconosciuto', undefined, true);
    } finally {
      loading = false;
    }
  }

  function goToSearch() {
    goto('/search');
  }

  function formatRuntime(minutes: number): string {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    if (hours > 0) {
      return `${hours}h ${mins}m`;
    }
    return `${mins}m`;
  }
</script>

<svelte:head>
  <title>YUNA - Film</title>
</svelte:head>

<div class="library-page">
  <!-- Top Bar -->
  <header class="top-bar">
    <div class="top-bar-content">
      <button class="back-button" on:click={() => goto('/dashboard')}>
        <Icon icon="mdi:arrow-left" width="24" />
      </button>
      <h1 class="page-title">Film</h1>
    </div>
  </header>

  <!-- Main Content -->
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
    {:else if filmsList.length > 0}
      <section class="library-section">
        <div class="section-header">
          <div class="section-header-left">
            <h2 class="section-title">La Mia Libreria</h2>
            <span class="section-count">{filmsList.length} {filmsList.length === 1 ? 'film' : 'film'}</span>
          </div>
          <div class="size-selector">
            <button
              class="size-btn"
              class:active={gridSize === 'small'}
              on:click={() => gridSize = 'small'}
              title="Compatto"
            >
              <Icon icon="mdi:view-grid" width="20" />
            </button>
            <button
              class="size-btn"
              class:active={gridSize === 'medium'}
              on:click={() => gridSize = 'medium'}
              title="Normale"
            >
              <Icon icon="mdi:view-grid-outline" width="20" />
            </button>
            <button
              class="size-btn"
              class:active={gridSize === 'large'}
              on:click={() => gridSize = 'large'}
              title="Grande"
            >
              <Icon icon="mdi:view-module" width="20" />
            </button>
          </div>
        </div>

        <div class="media-grid" class:grid-small={gridSize === 'small'} class:grid-medium={gridSize === 'medium'} class:grid-large={gridSize === 'large'}>
          {#each filmsList as film}
            <button class="media-card" on:click={() => goto(`/films/${encodeURIComponent(film.name)}`)}>
              <!-- Poster -->
              <div class="poster-container">
                {#if film.poster_url}
                  <img
                    src={film.poster_url}
                    alt={film.name}
                    class="poster"
                    loading="lazy"
                  />
                {:else}
                  <div class="poster-placeholder">
                    <Icon icon="mdi:movie" width="48" />
                  </div>
                {/if}

                <!-- Rating Badge -->
                {#if film.rating}
                  <div class="rating-badge">
                    <Icon icon="mdi:star" width="14" />
                    <span>{film.rating.toFixed(1)}</span>
                  </div>
                {/if}

                <!-- Downloaded Badge -->
                {#if film.downloaded}
                  <div class="download-badge">
                    <Icon icon="mdi:check-circle" width="16" />
                  </div>
                {/if}
              </div>

              <!-- Info Section -->
              <div class="media-info">
                <h3 class="media-title">{film.name}</h3>

                <!-- Year and Genres -->
                <div class="media-subtitle">
                  {#if film.year}
                    <span>{film.year}</span>
                  {/if}
                  {#if film.genres && film.genres.length > 0}
                    <span class="subtitle-separator">•</span>
                    <span>{film.genres.slice(0, 2).join(', ')}</span>
                  {:else if film.provider}
                    <span class="subtitle-separator">•</span>
                    <span>{film.provider}</span>
                  {/if}
                </div>

                <!-- Runtime & Status -->
                <div class="film-details">
                  {#if film.runtime}
                    <div class="detail-item">
                      <Icon icon="mdi:clock-outline" width="16" />
                      <span>{formatRuntime(film.runtime)}</span>
                    </div>
                  {/if}
                  <div class="detail-item status" class:downloaded={film.downloaded}>
                    <Icon icon={film.downloaded ? 'mdi:check-circle' : 'mdi:download-outline'} width="16" />
                    <span>{film.downloaded ? 'Scaricato' : 'Da scaricare'}</span>
                  </div>
                </div>
              </div>
            </button>
          {/each}
        </div>
      </section>
    {:else}
      <div class="state-container">
        <Card variant="outlined">
          <div class="state-content">
            <Icon icon="mdi:film" width="64" color="var(--m3c-outline)" />
            <h3>Nessun film</h3>
            <p>Inizia ad aggiungere film alla tua libreria</p>
            <Button variant="filled" onclick={goToSearch}>
              <Icon icon="mdi:magnify" width="20" />
              Cerca film
            </Button>
          </div>
        </Card>
      </div>
    {/if}
  </main>
</div>

<style>
  /* Page Layout */
  .library-page {
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
    max-width: 1400px;
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
    max-width: 1400px;
    margin: 0 auto;
    padding: 24px;
    padding-bottom: 120px;
    overflow-y: auto;
    max-height: calc(100vh - 64px);
  }

  /* Loading & States */
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
    align-items: center;
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
    max-width: 280px;
  }

  /* Section */
  .library-section {
    display: flex;
    flex-direction: column;
    gap: 24px;
  }

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 16px;
  }

  .section-header-left {
    display: flex;
    align-items: baseline;
    gap: 12px;
  }

  .section-title {
    font-size: 24px;
    font-weight: 500;
    color: var(--m3c-on-surface);
    margin: 0;
  }

  .section-count {
    font-size: 14px;
    color: var(--m3c-on-surface-variant);
  }

  /* Size Selector */
  .size-selector {
    display: none;
  }

  @media (min-width: 768px) {
    .size-selector {
      display: flex;
      gap: 4px;
      background: var(--m3c-surface-container);
      padding: 4px;
      border-radius: var(--m3-shape-medium);
    }
  }

  .size-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    border: none;
    background: transparent;
    color: var(--m3c-on-surface-variant);
    cursor: pointer;
    border-radius: var(--m3-shape-small);
    transition: all 0.2s;
  }

  .size-btn:hover {
    background: var(--m3c-surface-container-high);
    color: var(--m3c-on-surface);
  }

  .size-btn.active {
    background: var(--m3c-primary);
    color: var(--m3c-on-primary);
  }

  /* Media Grid */
  .media-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 20px;
  }

  @media (min-width: 768px) {
    .media-grid.grid-small {
      grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
      gap: 16px;
    }

    .media-grid.grid-medium {
      grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
      gap: 20px;
    }

    .media-grid.grid-large {
      grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
      gap: 24px;
    }
  }

  /* Media Card */
  .media-card {
    display: flex;
    flex-direction: column;
    background: var(--m3c-surface-container);
    border-radius: var(--m3-shape-large);
    overflow: hidden;
    cursor: pointer;
    border: 1px solid var(--m3c-outline-variant);
    padding: 0;
    text-align: left;
    transition: transform 0.2s, box-shadow 0.2s, border-color 0.2s;
  }

  .media-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
    border-color: var(--m3c-outline);
  }

  .media-card:active {
    transform: translateY(-2px);
  }

  /* Poster */
  .poster-container {
    position: relative;
    width: 100%;
    aspect-ratio: 2/3;
    overflow: hidden;
    background: var(--m3c-surface-container);
  }

  .poster {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .poster-placeholder {
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--m3c-surface-container-high);
    color: var(--m3c-outline);
  }

  /* Badges */
  .rating-badge {
    position: absolute;
    top: 10px;
    right: 10px;
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 6px 10px;
    background: rgba(0, 0, 0, 0.75);
    backdrop-filter: blur(8px);
    color: #fbbf24;
    border-radius: var(--m3-shape-medium);
    font-size: 13px;
    font-weight: 600;
  }

  .download-badge {
    position: absolute;
    bottom: 10px;
    right: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    background: var(--m3c-primary);
    color: var(--m3c-on-primary);
    border-radius: var(--m3-shape-full);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
  }

  /* Media Info */
  .media-info {
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .media-title {
    font-size: 15px;
    font-weight: 500;
    color: var(--m3c-on-surface);
    margin: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
    line-height: 1.4;
  }

  .media-subtitle {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 6px;
    font-size: 12px;
    color: var(--m3c-on-surface-variant);
  }

  .subtitle-separator {
    opacity: 0.5;
  }

  /* Film Details */
  .film-details {
    margin-top: 8px;
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
  }

  .detail-item {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 12px;
    color: var(--m3c-on-surface-variant);
  }

  .detail-item.status {
    color: var(--m3c-on-surface-variant);
  }

  .detail-item.status.downloaded {
    color: var(--m3c-primary);
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

    .media-grid {
      grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
      gap: 12px;
    }

    .media-info {
      padding: 12px;
    }

    .media-title {
      font-size: 14px;
    }
  }
</style>
