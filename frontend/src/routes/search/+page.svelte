<script lang="ts">
  import { goto } from '$app/navigation';
  import { api } from '$lib/api';
  import { Button, Card, TextFieldOutlined, LinearProgressEstimate, snackbar } from 'm3-svelte';
  import Icon from '@iconify/svelte';
  import type { SearchResult, SearchResponse } from '$lib/types';

  let searchQuery = '';
  let searchType: 'anime' | 'series' | 'film' = 'anime';
  let results: SearchResponse | null = null;
  let loading = false;
  let hasSearched = false;

  async function handleSearch() {
    if (!searchQuery.trim()) {
      snackbar('Inserisci un termine di ricerca', undefined, true);
      return;
    }

    loading = true;
    hasSearched = true;

    try {
      results = await api.search(searchQuery, searchType);
    } catch (err: any) {
      snackbar(err.message || 'Errore nella ricerca', undefined, true);
      results = null;
    } finally {
      loading = false;
    }
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Enter') {
      handleSearch();
    }
  }

  function selectResult(result: SearchResult) {
    if (result.type === 'anime' && result.provider_url) {
      // For anime, we could add to library
      goto(`/anime/add?url=${encodeURIComponent(result.provider_url)}`);
    } else if (result.mal_id) {
      goto(`/anime/jikan/${result.mal_id}`);
    } else if (result.tmdb_id) {
      goto(`/${result.type === 'film' ? 'movies' : 'series'}/tmdb/${result.tmdb_id}`);
    }
  }

  function setType(type: 'anime' | 'series' | 'film') {
    searchType = type;
    if (searchQuery.trim()) {
      handleSearch();
    }
  }

  $: allResults = results ? [...(results.anime || []), ...(results.series || []), ...(results.films || [])] : [];
</script>

<svelte:head>
  <title>YUNA - Cerca</title>
</svelte:head>

<div class="search-page">
  <!-- Top Bar -->
  <header class="top-bar">
    <div class="top-bar-content">
      <button class="back-button" on:click={() => goto('/dashboard')}>
        <Icon icon="mdi:arrow-left" width="24" />
      </button>
      <h1 class="page-title">Cerca</h1>
    </div>
  </header>

  <main class="main-content">
    <!-- Search Section -->
    <section class="search-section">
      <Card variant="filled">
        <div class="search-form">
          <!-- Filter Chips -->
          <div class="filter-chips">
            <button
              class="chip"
              class:selected={searchType === 'anime'}
              on:click={() => setType('anime')}
            >
              Anime
            </button>
            <button
              class="chip"
              class:selected={searchType === 'series'}
              on:click={() => setType('series')}
            >
              Serie TV
            </button>
            <button
              class="chip"
              class:selected={searchType === 'film'}
              on:click={() => setType('film')}
            >
              Film
            </button>
          </div>

          <div class="search-input-wrapper">
            <div class="field">
              <TextFieldOutlined
                label="Cerca anime, serie, film..."
                bind:value={searchQuery}
                onkeydown={handleKeydown}
                disabled={loading}
              />
            </div>
            <Button variant="filled" onclick={handleSearch} disabled={loading}>
              <Icon icon="mdi:magnify" width="20" />
            </Button>
          </div>
        </div>
      </Card>
    </section>

    <!-- Results Section -->
    {#if loading}
      <div class="loading-section">
        <LinearProgressEstimate sToHalfway={2} />
        <p>Ricerca in corso...</p>
      </div>
    {:else if hasSearched && results}
      <section class="results-section">
        <div class="results-header">
          <span class="results-count">{results.total} risultati per "{searchQuery}"</span>
        </div>

        {#if allResults.length > 0}
          <div class="results-grid">
            {#each allResults as result}
              <Card variant="outlined" onclick={() => selectResult(result)}>
                <div class="result-card">
                  <div class="result-poster-container">
                    {#if result.poster}
                      <img
                        src={result.poster}
                        alt={result.name}
                        class="result-poster"
                        loading="lazy"
                      />
                    {:else}
                      <div class="result-poster-placeholder">
                        <Icon icon="mdi:image-off" width="48" />
                      </div>
                    {/if}
                    <div class="result-type-badge" class:anime={result.type === 'anime'} class:series={result.type === 'series'} class:film={result.type === 'film'}>
                      {result.type === 'anime' ? 'ANIME' : result.type === 'series' ? 'SERIE' : 'FILM'}
                    </div>
                  </div>
                  
                  <div class="result-info">
                    <h3 class="result-title" title={result.name}>{result.name}</h3>
                    
                    <div class="result-meta">
                      {#if result.year}
                        <span class="meta-item">
                          <Icon icon="mdi:calendar" width="16" />
                          {result.year}
                        </span>
                      {/if}
                      {#if result.rating}
                        <span class="meta-item rating">
                          <Icon icon="mdi:star" width="16" />
                          {result.rating.toFixed(1)}
                        </span>
                      {/if}
                      {#if result.episodes}
                        <span class="meta-item">
                          <Icon icon="mdi:play-box-multiple" width="16" />
                          {result.episodes} ep
                        </span>
                      {/if}
                    </div>
                    
                    {#if result.genres && result.genres.length > 0}
                      <div class="result-genres">
                        {#each result.genres.slice(0, 3) as genre}
                          <span class="genre-tag">{genre}</span>
                        {/each}
                      </div>
                    {/if}
                    
                    {#if result.overview}
                      <p class="result-overview">{result.overview}</p>
                    {/if}
                  </div>
                </div>
              </Card>
            {/each}
          </div>
        {:else}
          <Card variant="outlined">
            <div class="empty-state">
              <Icon icon="mdi:magnify-close" width="64" color="var(--m3c-outline)" />
              <h3>Nessun risultato</h3>
              <p>Prova con termini di ricerca diversi</p>
            </div>
          </Card>
        {/if}
      </section>
    {:else if !hasSearched}
      <section class="hint-section">
        <Card variant="outlined">
          <div class="hint-content">
            <Icon icon="mdi:magnify" width="64" color="var(--m3c-outline)" />
            <h3>Cerca contenuti</h3>
            <p>Cerca anime, serie TV o film da aggiungere alla tua libreria</p>
          </div>
        </Card>
      </section>
    {/if}
  </main>
</div>

<style>
  .search-page {
    display: flex;
    flex-direction: column;
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
    padding: 16px;
    overflow-y: auto;
    width: 100%;
    box-sizing: border-box;
  }

  /* Search Section */
  .search-section {
    margin-bottom: 24px;
  }

  .search-form {
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 20px;
    box-sizing: border-box;
  }

  .search-input-wrapper {
    display: flex;
    gap: 12px;
    align-items: flex-end;
    width: 100%;
  }

  .field {
    flex: 1;
    min-width: 200px;
  }

  .field :global(.m3-container) {
    width: 100%;
  }

  /* Filter Chips */
  .filter-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 8px;
  }

  .chip {
    padding: 8px 16px;
    border-radius: var(--m3-shape-small);
    border: 1px solid var(--m3c-outline);
    background: transparent;
    color: var(--m3c-on-surface);
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
  }

  .chip:hover {
    background: var(--m3c-surface-container-high);
  }

  .chip.selected {
    background: var(--m3c-primary-container);
    color: var(--m3c-on-primary-container);
    border-color: var(--m3c-primary-container);
  }

  /* Loading */
  .loading-section {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;
    padding: 48px 16px;
    text-align: center;
    color: var(--m3c-on-surface-variant);
  }

  /* Results */
  .results-section {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .results-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .results-count {
    font-size: 14px;
    color: var(--m3c-on-surface-variant);
  }

  .results-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 20px;
  }

  .results-grid :global(.m3-card) {
    width: 100%;
    transition: transform 0.2s, box-shadow 0.2s;
    cursor: pointer;
  }

  .results-grid :global(.m3-card:hover) {
    transform: translateY(-4px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  }

  .result-card {
    display: flex;
    flex-direction: column;
    padding: 0;
    width: 100%;
    box-sizing: border-box;
  }

  .result-poster-container {
    position: relative;
    width: 100%;
    aspect-ratio: 2/3;
    overflow: hidden;
  }

  .result-poster {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }

  .result-poster-placeholder {
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--m3c-surface-container-high);
    color: var(--m3c-outline);
  }

  .result-info {
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    flex: 1;
  }

  .result-type-badge {
    position: absolute;
    top: 8px;
    left: 8px;
    padding: 6px 12px;
    border-radius: var(--m3-shape-small);
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    backdrop-filter: blur(8px);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
  }

  .result-type-badge.anime {
    background: rgba(103, 80, 164, 0.9);
    color: #ffffff;
  }

  .result-type-badge.series {
    background: rgba(3, 218, 198, 0.9);
    color: #000000;
  }

  .result-type-badge.film {
    background: rgba(251, 140, 0, 0.9);
    color: #000000;
  }

  .result-title {
    font-size: 16px;
    font-weight: 600;
    color: var(--m3c-on-surface);
    margin: 0;
    line-height: 1.4;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    word-wrap: break-word;
  }

  .result-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    font-size: 13px;
    color: var(--m3c-on-surface-variant);
  }

  .meta-item {
    display: flex;
    align-items: center;
    gap: 4px;
    font-weight: 500;
  }

  .meta-item.rating {
    color: #f59e0b;
    font-weight: 600;
  }

  .result-genres {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .genre-tag {
    font-size: 11px;
    padding: 4px 10px;
    background: var(--m3c-surface-container-highest);
    color: var(--m3c-on-surface-variant);
    border-radius: var(--m3-shape-full);
    font-weight: 500;
  }

  .result-overview {
    font-size: 13px;
    line-height: 1.5;
    color: var(--m3c-on-surface-variant);
    margin: 0;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  /* Empty State & Hints */
  .empty-state,
  .hint-content {
    padding: 48px 24px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    text-align: center;
  }

  .empty-state h3,
  .hint-content h3 {
    font-size: 20px;
    font-weight: 500;
    color: var(--m3c-on-surface);
    margin: 0;
  }

  .empty-state p,
  .hint-content p {
    font-size: 14px;
    color: var(--m3c-on-surface-variant);
    margin: 0;
  }

  /* Responsive */
  @media (max-width: 768px) {
    .main-content {
      padding: 10px;
      padding-bottom: 100px;
    }

    .search-form {
      padding: 12px;
    }

    .results-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }

    .results-grid :global(.m3-card) {
      overflow: hidden;
    }

    .result-poster-container {
      aspect-ratio: 2/3;
    }

    .result-info {
      padding: 10px;
      gap: 6px;
    }

    .result-title {
      font-size: 13px;
      line-height: 1.3;
      -webkit-line-clamp: 2;
      line-clamp: 2;
    }

    .result-meta {
      font-size: 11px;
      gap: 6px;
      flex-wrap: wrap;
    }

    .meta-item :global(svg) {
      width: 13px;
      height: 13px;
    }

    .result-genres {
      gap: 4px;
    }

    .genre-tag {
      font-size: 9px;
      padding: 3px 6px;
    }

    .result-overview {
      font-size: 11px;
      line-height: 1.4;
      -webkit-line-clamp: 2;
      line-clamp: 2;
    }

    .result-type-badge {
      padding: 4px 8px;
      font-size: 9px;
      letter-spacing: 0.4px;
      top: 6px;
      left: 6px;
    }
  }

  @media (max-width: 480px) {
    .main-content {
      padding: 8px;
      padding-bottom: 100px;
    }

    .results-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
    }

    .result-info {
      padding: 8px;
    }

    .result-title {
      font-size: 12px;
    }
  }

</style>
