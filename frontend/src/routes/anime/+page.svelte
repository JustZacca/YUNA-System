<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { user, isAuthenticated } from '$lib/stores';
  import { api } from '$lib/api';
  import { Button, Card, LinearProgressEstimate, snackbar } from 'm3-svelte';
  import Icon from '@iconify/svelte';

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

  async function loadData() {
    loading = true;
    error = null;

    try {
      animeList = await api.getAnimeList();
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
</script>

<svelte:head>
  <title>YUNA - Anime</title>
</svelte:head>

<div class="anime-page">
  <!-- Top Bar -->
  <header class="top-bar">
    <div class="top-bar-content">
      <button class="back-button" on:click={() => goto('/dashboard')}>
        <Icon icon="mdi:arrow-left" width="24" />
      </button>
      <h1 class="page-title">Anime</h1>
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
    {:else if animeList && animeList.items.length > 0}
      <section class="anime-section">
        <div class="section-header">
          <h2 class="section-title">I Miei Anime</h2>
          <span class="section-count">{animeList.total} titoli</span>
        </div>

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
      </section>
    {:else}
      <div class="empty-state">
        <Card variant="outlined">
          <div class="empty-content">
            <Icon icon="mdi:animation-play-outline" width="64" color="var(--m3c-outline)" />
            <h3>Nessun anime</h3>
            <p>Inizia ad aggiungere anime alla tua libreria</p>
            <Button variant="filled" onclick={goToSearch}>
              <Icon icon="mdi:magnify" width="20" />
              Cerca
            </Button>
          </div>
        </Card>
      </div>
    {/if}
  </main>
</div>

<style>
  .anime-page {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
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
    max-width: 1200px;
    margin: 0 auto;
    padding: 12px 16px;
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
    flex: 1;
    max-width: 1200px;
    margin: 0 auto;
    width: 100%;
    padding: 16px;
    padding-bottom: 80px;
  }

  /* Loading */
  .loading-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;
    padding: 48px 16px;
    text-align: center;
    color: var(--m3c-on-surface-variant);
  }

  /* Error */
  .error-container {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 48px 16px;
  }

  .error-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;
    text-align: center;
    padding: 24px;
  }

  /* Anime Section */
  .anime-section {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .section-title {
    font-size: 20px;
    font-weight: 500;
    color: var(--m3c-on-surface);
    margin: 0;
  }

  .section-count {
    font-size: 14px;
    color: var(--m3c-on-surface-variant);
  }

  .anime-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 16px;
  }

  .anime-card {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 12px;
    cursor: pointer;
    height: 100%;
  }

  .anime-poster {
    width: 100%;
    height: 220px;
    object-fit: cover;
    border-radius: var(--m3-shape-small);
  }

  .anime-poster-placeholder {
    width: 100%;
    height: 220px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--m3c-surface-container-high);
    border-radius: var(--m3-shape-small);
    color: var(--m3c-outline);
  }

  .anime-info {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .anime-title {
    font-size: 14px;
    font-weight: 500;
    color: var(--m3c-on-surface);
    margin: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
  }

  .anime-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    font-size: 11px;
    color: var(--m3c-on-surface-variant);
  }

  .anime-episodes,
  .anime-rating {
    display: flex;
    align-items: center;
    gap: 3px;
  }

  .anime-rating {
    color: var(--m3c-tertiary);
  }

  .anime-genres {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }

  .genre-chip {
    font-size: 10px;
    padding: 2px 6px;
    background: var(--m3c-surface-container-high);
    color: var(--m3c-on-surface-variant);
    border-radius: var(--m3-shape-extra-small);
  }

  /* Empty State */
  .empty-state {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 48px 16px;
  }

  .empty-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;
    text-align: center;
    padding: 32px;
  }

  .empty-content h3 {
    font-size: 20px;
    font-weight: 500;
    color: var(--m3c-on-surface);
    margin: 0;
  }

  .empty-content p {
    font-size: 14px;
    color: var(--m3c-on-surface-variant);
    margin: 0 0 12px 0;
  }

  /* Responsive */
  @media (max-width: 768px) {
    .main-content {
      padding-bottom: 80px;
    }

    .anime-grid {
      grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
    }
  }
</style>
