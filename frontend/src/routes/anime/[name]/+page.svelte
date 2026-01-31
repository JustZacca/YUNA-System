<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { user, isAuthenticated } from '$lib/stores';
  import { api } from '$lib/api';
  import { Button, Card, LinearProgressEstimate, snackbar } from 'm3-svelte';
  import Icon from '@iconify/svelte';
  import type { AnimeDetail } from '$lib/types';

  let anime: AnimeDetail | null = null;
  let loading = true;
  let error: string | null = null;

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
      anime = await api.getAnimeDetail(name);
    } catch (err: any) {
      error = err.message || 'Errore nel caricamento dei dettagli';
      snackbar(error ?? 'Errore sconosciuto', undefined, true);
    } finally {
      loading = false;
    }
  }

  function formatGenres(genres: string[]): string {
    return genres.join(', ');
  }

  function calculateDownloadPercentage(): number {
    if (!anime || anime.episodes_total === 0) return 0;
    return Math.round((anime.episodes_downloaded / anime.episodes_total) * 100);
  }
</script>

<svelte:head>
  <title>YUNA - {anime?.name || 'Anime'}</title>
</svelte:head>

<div class="anime-detail-page">
  <!-- Top Bar -->
  <header class="top-bar">
    <div class="top-bar-content">
      <button class="back-button" on:click={() => goto('/anime')}>
        <Icon icon="mdi:arrow-left" width="24" />
      </button>
      <h1 class="page-title">Dettagli Anime</h1>
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
    {:else if anime}
      <div class="anime-detail">
        <!-- Poster and Base Info -->
        <div class="detail-header">
          {#if anime.poster_url || anime.poster}
            <img
              src={anime.poster_url || anime.poster}
              alt={anime.name}
              class="poster-image"
            />
          {:else}
            <div class="poster-placeholder">
              <Icon icon="mdi:image-off" width="64" />
            </div>
          {/if}

          <div class="header-info">
            <h2 class="anime-title">{anime.name}</h2>

            <div class="basic-info">
              {#if anime.year}
                <div class="info-item">
                  <span class="label">Anno:</span>
                  <span class="value">{anime.year}</span>
                </div>
              {/if}

              {#if anime.rating}
                <div class="info-item">
                  <span class="label">Rating:</span>
                  <span class="value">⭐ {anime.rating.toFixed(1)}/10</span>
                </div>
              {/if}

              {#if anime.status}
                <div class="info-item">
                  <span class="label">Stato:</span>
                  <span class="value">{anime.status}</span>
                </div>
              {/if}

              {#if anime.genres && anime.genres.length > 0}
                <div class="info-item">
                  <span class="label">Generi:</span>
                  <span class="value">{formatGenres(anime.genres)}</span>
                </div>
              {/if}
            </div>
          </div>
        </div>

        <!-- Synopsis -->
        {#if anime.synopsis}
          <section class="section">
            <h3 class="section-title">Trama</h3>
            <Card variant="outlined">
              <p class="synopsis-text">{anime.synopsis}</p>
            </Card>
          </section>
        {/if}

        <!-- Episodes Statistics -->
        <section class="section">
          <h3 class="section-title">Episodi</h3>

          <div class="episodes-stats">
            <Card variant="filled">
              <div class="stat-card">
                <div class="stat-item">
                  <Icon icon="mdi:check-circle" width="32" color="var(--m3c-primary)" />
                  <div class="stat-content">
                    <p class="stat-label">Scaricati</p>
                    <p class="stat-value">{anime.episodes_downloaded}</p>
                  </div>
                </div>
              </div>
            </Card>

            <Card variant="filled">
              <div class="stat-card">
                <div class="stat-item">
                  <Icon icon="mdi:clock-outline" width="32" color="var(--m3c-tertiary)" />
                  <div class="stat-content">
                    <p class="stat-label">Non Scaricati</p>
                    <p class="stat-value">{anime.episodes_total - anime.episodes_downloaded}</p>
                  </div>
                </div>
              </div>
            </Card>

            <Card variant="filled">
              <div class="stat-card">
                <div class="stat-item">
                  <Icon icon="mdi:playlist-check" width="32" color="var(--m3c-secondary)" />
                  <div class="stat-content">
                    <p class="stat-label">Totali</p>
                    <p class="stat-value">{anime.episodes_total}</p>
                  </div>
                </div>
              </div>
            </Card>
          </div>

          <!-- Progress Bar -->
          <div class="progress-section">
            <div class="progress-info">
              <span class="progress-label">Completamento: {calculateDownloadPercentage()}%</span>
            </div>
            <div class="progress-bar">
              <div
                class="progress-fill"
                style="width: {calculateDownloadPercentage()}%"
              />
            </div>
          </div>

          <!-- Missing Episodes -->
          {#if anime.missing_episodes && anime.missing_episodes.length > 0}
            <div class="missing-episodes">
              <h4 class="missing-title">Episodi mancanti:</h4>
              <div class="episode-list">
                {#each anime.missing_episodes as ep}
                  <span class="episode-badge">{ep}</span>
                {/each}
              </div>
            </div>
          {/if}
        </section>
      </div>
    {:else}
      <div class="error-container">
        <Card variant="outlined">
          <div class="error-content">
            <Icon icon="mdi:alert-circle" width="48" color="var(--m3c-error)" />
            <p>Anime non trovato</p>
            <Button variant="filled" onclick={() => goto('/anime')}>Torna ai Miei Anime</Button>
          </div>
        </Card>
      </div>
    {/if}
  </main>

</div>

<style>
  .anime-detail-page {
    display: flex;
    flex-direction: column;
    min-height: 100vh;
  }

  .top-bar {
    background: var(--m3c-surface);
    border-bottom: 1px solid var(--m3c-outline-variant);
    padding: 16px;
    position: sticky;
    top: 0;
    z-index: 100;
  }

  .top-bar-content {
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .back-button {
    background: none;
    border: none;
    cursor: pointer;
    color: var(--m3c-on-surface);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 8px;
    border-radius: 50%;
    transition: background 0.2s;
  }

  .back-button:hover {
    background: var(--m3c-surface-container);
  }

  .page-title {
    font-size: 24px;
    font-weight: 600;
    color: var(--m3c-on-surface);
    margin: 0;
  }

  .main-content {
    flex: 1;
    overflow-y: auto;
    padding: 16px;
    padding-bottom: 96px;
  }

  .loading-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 16px;
    padding: 32px 16px;
  }

  .error-container {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 400px;
  }

  .error-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;
    padding: 32px;
    text-align: center;
  }

  .anime-detail {
    display: flex;
    flex-direction: column;
    gap: 24px;
  }

  .detail-header {
    display: grid;
    grid-template-columns: 160px 1fr;
    gap: 20px;
    align-items: start;
  }

  .poster-image {
    width: 160px;
    height: auto;
    border-radius: var(--m3-shape-medium);
    object-fit: cover;
  }

  .poster-placeholder {
    width: 160px;
    height: 240px;
    background: var(--m3c-surface-container);
    border-radius: var(--m3-shape-medium);
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--m3c-on-surface-variant);
  }

  .header-info {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .anime-title {
    font-size: 24px;
    font-weight: 600;
    color: var(--m3c-on-surface);
    margin: 0;
  }

  .basic-info {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .info-item {
    display: flex;
    flex-direction: column;
    gap: 4px;
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
  }

  .section {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .section-title {
    font-size: 18px;
    font-weight: 600;
    color: var(--m3c-on-surface);
    margin: 0;
  }

  .synopsis-text {
    font-size: 14px;
    color: var(--m3c-on-surface);
    line-height: 1.6;
    margin: 16px;
  }

  .episodes-stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 12px;
  }

  .stat-card {
    padding: 16px;
  }

  .stat-item {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .stat-content {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .stat-label {
    font-size: 12px;
    font-weight: 600;
    color: var(--m3c-on-surface-variant);
    text-transform: uppercase;
    margin: 0;
  }

  .stat-value {
    font-size: 24px;
    font-weight: 700;
    color: var(--m3c-on-surface);
    margin: 0;
  }

  .progress-section {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-top: 12px;
  }

  .progress-info {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .progress-label {
    font-size: 12px;
    font-weight: 600;
    color: var(--m3c-on-surface-variant);
  }

  .progress-bar {
    width: 100%;
    height: 8px;
    background: var(--m3c-surface-container);
    border-radius: 4px;
    overflow: hidden;
  }

  .progress-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--m3c-primary), var(--m3c-secondary));
    border-radius: 4px;
    transition: width 0.3s ease;
  }

  .missing-episodes {
    margin-top: 16px;
    padding: 12px;
    background: var(--m3c-surface-container-lowest);
    border-radius: var(--m3-shape-medium);
    border-left: 4px solid var(--m3c-warning);
  }

  .missing-title {
    font-size: 14px;
    font-weight: 600;
    color: var(--m3c-on-surface);
    margin: 0 0 8px 0;
  }

  .episode-list {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .episode-badge {
    background: var(--m3c-warning-container);
    color: var(--m3c-on-warning-container);
    padding: 4px 12px;
    border-radius: 16px;
    font-size: 12px;
    font-weight: 500;
  }

  .bottom-nav {
    display: none;
    position: fixed;
    bottom: 0;
    width: 100%;
    height: 80px;
    background: var(--m3c-surface-container-lowest);
    border-top: 1px solid var(--m3c-outline-variant);
    justify-content: space-around;
    align-items: center;
    z-index: 999;
  }

  .nav-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 4px;
    color: var(--m3c-on-surface-variant);
    text-decoration: none;
    font-size: 12px;
    font-weight: 500;
    background: none;
    border: none;
    cursor: pointer;
    padding: 8px;
    transition: color 0.2s;
    flex: 1;
    height: 100%;
  }

  .nav-item:hover {
    color: var(--m3c-on-surface);
  }

  .logout-btn-mobile {
    background: none;
    color: var(--m3c-error-container);
  }

  .logout-btn-mobile:hover {
    color: var(--m3c-error);
  }

  /* Responsive Design */
  @media (max-width: 768px) {
    .detail-header {
      grid-template-columns: 1fr;
    }

    .poster-image {
      width: 100%;
      max-width: 200px;
    }

    .anime-title {
      font-size: 20px;
    }

    .episodes-stats {
      grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    }

    .bottom-nav {
      display: flex !important;
    }

    .main-content {
      padding-bottom: 96px;
    }
  }

  @media (min-width: 769px) {
    .bottom-nav {
      display: none !important;
    }
  }
</style>
