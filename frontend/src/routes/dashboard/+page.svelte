<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { user, isAuthenticated } from '$lib/stores';
  import { api } from '$lib/api';
  import { Button, Card, LinearProgressEstimate, snackbar } from 'm3-svelte';
  import Icon from '@iconify/svelte';

  let health: any = null;
  let stats: any = null;
  let animeList: any = null;
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

  $: if (!$isAuthenticated && typeof window !== 'undefined') {
    goto('/');
  }

  async function loadData() {
    loading = true;
    error = null;

    try {
      [health, stats, animeList] = await Promise.all([
        api.getHealth(),
        api.getStats(),
        api.getAnimeList()
      ]);
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

  function handleLogout() {
    user.logout();
    snackbar('Logout effettuato', undefined, true);
    window.location.href = '/';
  }

  function formatDate(dateStr: string | null): string {
    if (!dateStr) return 'Mai';
    const date = new Date(dateStr);
    return date.toLocaleDateString('it-IT', { day: '2-digit', month: 'short' });
  }
</script>

<svelte:head>
  <title>YUNA - Dashboard</title>
</svelte:head>

<div class="dashboard">
  <!-- Top App Bar -->
  <header class="top-bar">
    <div class="top-bar-content">
      <div class="brand">
        <Icon icon="mdi:play-circle" width="28" />
        <span class="brand-text">YUNA</span>
      </div>
      <button class="logout-mobile" on:click={handleLogout}>
        <Icon icon="mdi:logout" width="20" />
        <span class="logout-label">Esci</span>
      </button>
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
      <div class="error-container">
        <Card variant="outlined">
          <div class="error-content">
            <Icon icon="mdi:alert-circle" width="48" color="var(--m3c-error)" />
            <p>{error}</p>
            <Button variant="filled" onclick={loadData}>Riprova</Button>
          </div>
        </Card>
      </div>
    {:else}
      <!-- Stats Section -->
      <section class="section">
        <h2 class="section-title">Panoramica</h2>

        {#if health}
          <Card variant="filled">
            <div class="system-status">
              <div class="status-indicator">
                <Icon icon="mdi:check-circle" width="24" color="var(--m3c-primary)" />
                <div class="status-info">
                  <span class="status-label">Sistema Online</span>
                  <span class="status-detail">v{health.api_version} • Uptime: {Math.floor(health.uptime / 3600)}h</span>
                </div>
              </div>
            </div>
          </Card>
        {/if}

        {#if stats}
          <div class="stats-grid">
            <Card variant="elevated" onclick={() => goto('/anime')}>
              <div class="stat-card">
                <Icon icon="mdi:animation-play" width="32" color="var(--m3c-primary)" />
                <span class="stat-number">{stats.anime_count}</span>
                <span class="stat-name">Anime</span>
              </div>
            </Card>
            <Card variant="elevated" onclick={() => goto('/series')}>
              <div class="stat-card">
                <Icon icon="mdi:television-classic" width="32" color="var(--m3c-secondary)" />
                <span class="stat-number">{stats.series_count}</span>
                <span class="stat-name">Serie TV</span>
              </div>
            </Card>
            <Card variant="elevated" onclick={() => goto('/movies')}>
              <div class="stat-card">
                <Icon icon="mdi:movie-open" width="32" color="var(--m3c-tertiary)" />
                <span class="stat-number">{stats.films_count}</span>
                <span class="stat-name">Film</span>
              </div>
            </Card>
          </div>
        {/if}
      </section>

      <!-- Anime Library -->
      <section class="section">
        <div class="section-header">
          <h2 class="section-title">Libreria Anime</h2>
          {#if animeList && animeList.total > 0}
            <span class="section-count">{animeList.total} titoli</span>
          {/if}
        </div>

        {#if animeList && animeList.items.length > 0}
          <div class="anime-grid">
            {#each animeList.items as anime}
              <Card variant="filled" onclick={() => goto(`/anime/${encodeURIComponent(anime.name)}`)}>
                <div class="anime-card">
                  {#if anime.poster_url || anime.poster}
                    <img
                      src={anime.poster_url || anime.poster}
                      alt={anime.name}
                      class="anime-poster"
                      loading="lazy"
                    />
                  {:else}
                    <div class="anime-poster-placeholder">
                      <Icon icon="mdi:image-off" width="48" />
                    </div>
                  {/if}
                  <div class="anime-info">
                    <h3 class="anime-title">{anime.name}</h3>
                    <div class="anime-meta">
                      <span class="anime-episodes">
                        <Icon icon="mdi:play-box-multiple" width="16" />
                        {anime.episodes_downloaded}/{anime.episodes_total}
                      </span>
                      {#if anime.rating}
                        <span class="anime-rating">
                          <Icon icon="mdi:star" width="16" />
                          {anime.rating.toFixed(1)}
                        </span>
                      {/if}
                    </div>
                    {#if anime.genres && anime.genres.length > 0}
                      <div class="anime-genres">
                        {#each anime.genres.slice(0, 2) as genre}
                          <span class="genre-chip">{genre}</span>
                        {/each}
                      </div>
                    {/if}
                  </div>
                </div>
              </Card>
            {/each}
          </div>
        {:else}
          <Card variant="outlined">
            <div class="empty-state">
              <Icon icon="mdi:folder-open" width="64" color="var(--m3c-outline)" />
              <h3>Nessun anime</h3>
              <p>La tua libreria è vuota. Cerca e aggiungi degli anime!</p>
              <Button variant="filled" onclick={goToSearch}>
                <Icon icon="mdi:magnify" width="20" />
                Cerca Anime
              </Button>
            </div>
          </Card>
        {/if}
      </section>
    {/if}
  </main>

  <!-- FAB -->
  <div class="fab-container">
    <button class="fab" on:click={goToSearch}>
      <Icon icon="mdi:magnify" width="24" />
    </button>
  </div>
</div>

<style>
  .dashboard {
    min-height: 100vh;
    background: var(--m3c-surface);
  }

  /* Top App Bar */
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
    justify-content: space-between;
  }

  .brand {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--m3c-primary);
  }

  .brand-text {
    font-size: 20px;
    font-weight: 700;
    letter-spacing: -0.5px;
  }

  /* Main Content */
  .main-content {
    max-width: 1200px;
    margin: 0 auto;
    padding: 24px 20px;
    padding-bottom: 140px;
    width: 100%;
    box-sizing: border-box;
    overflow-y: auto;
    max-height: calc(100vh - 64px);
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

  /* Sections */
  .section {
    margin-bottom: 32px;
  }

  .section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
  }

  .section-title {
    font-size: 22px;
    font-weight: 500;
    color: var(--m3c-on-surface);
    margin: 0 0 16px 0;
  }

  .section-count {
    font-size: 14px;
    color: var(--m3c-on-surface-variant);
  }

  /* System Status */
  .system-status {
    padding: 16px;
  }

  .status-indicator {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .status-info {
    display: flex;
    flex-direction: column;
  }

  .status-label {
    font-size: 16px;
    font-weight: 500;
    color: var(--m3c-on-surface);
  }

  .status-detail {
    font-size: 12px;
    color: var(--m3c-on-surface-variant);
  }

  /* Stats Grid */
  .stats-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
    margin-top: 16px;
  }

  .stat-card {
    padding: 20px 16px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    cursor: pointer;
  }

  .stat-number {
    font-size: 32px;
    font-weight: 700;
    color: var(--m3c-on-surface);
  }

  .stat-name {
    font-size: 12px;
    color: var(--m3c-on-surface-variant);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  /* Anime Grid */
  .anime-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 16px;
  }

  .anime-card {
    display: flex;
    gap: 12px;
    padding: 12px;
    cursor: pointer;
  }

  .anime-poster {
    width: 80px;
    height: 120px;
    object-fit: cover;
    border-radius: var(--m3-shape-small);
    flex-shrink: 0;
  }

  .anime-poster-placeholder {
    width: 80px;
    height: 120px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--m3c-surface-container-high);
    border-radius: var(--m3-shape-small);
    color: var(--m3c-outline);
    flex-shrink: 0;
  }

  .anime-info {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 6px;
    min-width: 0;
  }

  .anime-title {
    font-size: 16px;
    font-weight: 500;
    color: var(--m3c-on-surface);
    margin: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .anime-meta {
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 12px;
    color: var(--m3c-on-surface-variant);
  }

  .anime-episodes,
  .anime-rating {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .anime-genres {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 4px;
  }

  .genre-chip {
    font-size: 11px;
    padding: 4px 8px;
    background: var(--m3c-surface-container-high);
    color: var(--m3c-on-surface-variant);
    border-radius: var(--m3-shape-small);
  }

  /* Empty State */
  .empty-state {
    padding: 48px 24px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    text-align: center;
  }

  .empty-state h3 {
    font-size: 20px;
    font-weight: 500;
    color: var(--m3c-on-surface);
    margin: 0;
  }

  .empty-state p {
    font-size: 14px;
    color: var(--m3c-on-surface-variant);
    margin: 0 0 8px 0;
  }

  /* FAB */
  .fab-container {
    position: fixed;
    bottom: 96px;
    right: 16px;
    z-index: 50;
  }

  .fab {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 56px;
    height: 56px;
    border: none;
    border-radius: var(--m3-shape-large);
    background: var(--m3c-primary-container);
    color: var(--m3c-on-primary-container);
    cursor: pointer;
    box-shadow: var(--m3-elevation-3);
    transition: all 0.2s ease;
  }

  .fab:hover {
    box-shadow: var(--m3-elevation-4);
  }

  .fab:active {
    box-shadow: var(--m3-elevation-2);
  }

  @media (min-width: 840px) {
    .fab-container {
      bottom: 24px;
    }
  }

  /* Mobile Logout Button */
  @media (max-width: 768px) {
    .logout-mobile {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      color: var(--m3c-on-error-container);
      background: var(--m3c-error-container);
      border: none;
      border-radius: var(--m3-shape-medium);
      cursor: pointer;
      font-size: 14px;
      font-weight: 500;
      transition: background 0.2s;
    }

    .logout-mobile:hover {
      background: var(--m3c-error);
    }

    .logout-label {
      display: inline;
    }
  }

  @media (min-width: 769px) {
    .logout-mobile {
      display: none !important;
    }

    .logout-label {
      display: none;
    }
  }
</style>
