<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { user, isAuthenticated } from '$lib/stores';
  import { api } from '$lib/api';
  import { Button, Card, TextFieldOutlined, LinearProgressEstimate, snackbar } from 'm3-svelte';
  import Icon from '@iconify/svelte';

  let animeList: any[] = [];
  let jikanResults: any[] = [];
  let loading = false;
  let searching = false;
  let currentAnime: any = null;
  let searchQuery = '';
  let selectedResult: any = null;

  onMount(async () => {
    await user.checkAuth();

    if (!$isAuthenticated) {
      goto('/');
      return;
    }

    await loadAnime();
  });

  async function loadAnime() {
    loading = true;
    try {
      const response = await api.getAnimeList();
      animeList = response.items || [];
    } catch (err: any) {
      snackbar('Errore nel caricamento degli anime', undefined, true);
    } finally {
      loading = false;
    }
  }

  async function searchJikan() {
    if (!currentAnime || !searchQuery.trim()) {
      snackbar('Inserisci un nome da cercare', undefined, true);
      return;
    }

    searching = true;
    try {
      const response = await fetch(`/api/search?q=${encodeURIComponent(searchQuery)}&type=anime`);
      const data = await response.json();
      jikanResults = data.anime || [];
      if (jikanResults.length === 0) {
        snackbar('Nessun risultato trovato', undefined, true);
      }
    } catch (err: any) {
      snackbar('Errore nella ricerca', undefined, true);
    } finally {
      searching = false;
    }
  }

  async function associateAnime() {
    if (!currentAnime || !selectedResult) {
      snackbar('Seleziona un anime da associare', undefined, true);
      return;
    }

    loading = true;
    try {
      const response = await fetch(`/api/anime/${encodeURIComponent(currentAnime.name)}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          mal_id: selectedResult.mal_id,
          synopsis: selectedResult.overview,
          rating: selectedResult.rating,
          year: selectedResult.year,
          genres: selectedResult.genres?.join(','),
          status: selectedResult.status,
          poster_url: selectedResult.poster,
        }),
      });

      if (response.ok) {
        snackbar(`${currentAnime.name} associato con successo!`, undefined, true);
        currentAnime = null;
        searchQuery = '';
        jikanResults = [];
        selectedResult = null;
        await loadAnime();
      } else {
        snackbar('Errore nell\'associazione', undefined, true);
      }
    } catch (err: any) {
      snackbar(err.message || 'Errore', undefined, true);
    } finally {
      loading = false;
    }
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Enter') {
      searchJikan();
    }
  }
</script>

<svelte:head>
  <title>YUNA - Gestisci Anime</title>
</svelte:head>

<div class="manage-page">
  <!-- Top Bar -->
  <header class="top-bar">
    <div class="top-bar-content">
      <button class="back-button" on:click={() => goto('/dashboard')}>
        <Icon icon="mdi:arrow-left" width="24" />
      </button>
      <h1 class="page-title">Associa Metadati</h1>
    </div>
  </header>

  <!-- Main Content -->
  <main class="main-content">
    <div class="container">
      <!-- Left Panel: Anime List -->
      <div class="anime-list-panel">
        <h2>I Miei Anime</h2>
        {#if loading && animeList.length === 0}
          <div class="loading">
            <LinearProgressEstimate sToHalfway={2} />
          </div>
        {:else}
          <div class="anime-items">
            {#each animeList as anime}
              <button
                class="anime-item"
                class:active={currentAnime?.name === anime.name}
                on:click={() => {
                  currentAnime = anime;
                  searchQuery = anime.name;
                  jikanResults = [];
                  selectedResult = null;
                }}
              >
                <div class="anime-item-content">
                  <h3>{anime.name}</h3>
                  {#if anime.poster_url}
                    <span class="badge success">✓ Ha poster</span>
                  {:else}
                    <span class="badge pending">⊘ No poster</span>
                  {/if}
                </div>
              </button>
            {/each}
          </div>
        {/if}
      </div>

      <!-- Right Panel: Search & Results -->
      <div class="search-panel">
        {#if currentAnime}
          <div class="selected-anime">
            <h3>{currentAnime.name}</h3>
            <p class="subtitle">Episodi: {currentAnime.episodes_downloaded}/{currentAnime.episodes_total}</p>
          </div>

          <!-- Search -->
          <div class="search-section">
            <div class="search-input">
              <TextFieldOutlined
                label="Cerca su Jikan..."
                bind:value={searchQuery}
                onkeydown={handleKeydown}
                disabled={searching}
              />
              <Button
                variant="filled"
                onclick={searchJikan}
                disabled={searching || !searchQuery.trim()}
              >
                <Icon icon="mdi:magnify" width="20" />
              </Button>
            </div>
          </div>

          <!-- Results -->
          {#if searching}
            <div class="loading">
              <LinearProgressEstimate sToHalfway={2} />
              <p>Ricerca in corso...</p>
            </div>
          {:else if jikanResults.length > 0}
            <div class="results-section">
              <h4>Risultati ({jikanResults.length})</h4>
              <div class="results-list">
                {#each jikanResults as result}
                  <Card
                    variant={selectedResult?.mal_id === result.mal_id ? 'filled' : 'outlined'}
                    onclick={() => {
                      selectedResult = result;
                    }}
                  >
                    <div class="result-item">
                      {#if result.poster}
                        <img src={result.poster} alt={result.name} class="result-poster" />
                      {/if}
                      <div class="result-info">
                        <h5>{result.name}</h5>
                        {#if result.year}
                          <p class="year">Anno: {result.year}</p>
                        {/if}
                        {#if result.rating}
                          <p class="rating">⭐ {result.rating.toFixed(1)}</p>
                        {/if}
                        {#if result.genres}
                          <div class="genres">
                            {#each result.genres.slice(0, 3) as genre}
                              <span class="genre-tag">{genre}</span>
                            {/each}
                          </div>
                        {/if}
                      </div>
                    </div>
                  </Card>
                {/each}
              </div>

              {#if selectedResult}
                <Button variant="filled" onclick={associateAnime} disabled={loading}>
                  <Icon icon="mdi:check" width="20" />
                  Associa
                </Button>
              {/if}
            </div>
          {:else if jikanResults.length === 0 && searchQuery}
            <div class="empty-state">
              <Icon icon="mdi:magnify-close" width="48" color="var(--m3c-outline)" />
              <p>Nessun risultato trovato per "{searchQuery}"</p>
            </div>
          {/if}
        {:else}
          <div class="empty-state">
            <Icon icon="mdi:arrow-left" width="48" color="var(--m3c-outline)" />
            <p>Seleziona un anime dalla lista</p>
          </div>
        {/if}
      </div>
    </div>
  </main>
</div>

<style>
  .manage-page {
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
    max-width: 1400px;
    margin: 0 auto;
    padding: 12px 16px;
    display: flex;
    align-items: center;
    gap: 16px;
    width: 100%;
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
    max-width: 1400px;
    margin: 0 auto;
    width: 100%;
    padding: 16px;
  }

  .container {
    display: grid;
    grid-template-columns: 300px 1fr;
    gap: 20px;
    height: 600px;
  }

  /* Anime List Panel */
  .anime-list-panel {
    display: flex;
    flex-direction: column;
    gap: 12px;
    border-radius: var(--m3-shape-medium);
    background: var(--m3c-surface-container);
    padding: 16px;
    overflow: hidden;
  }

  .anime-list-panel h2 {
    margin: 0;
    font-size: 16px;
    font-weight: 600;
    color: var(--m3c-on-surface);
  }

  .anime-items {
    display: flex;
    flex-direction: column;
    gap: 8px;
    overflow-y: auto;
    flex: 1;
  }

  .anime-item {
    padding: 12px;
    border: 1px solid var(--m3c-outline-variant);
    border-radius: var(--m3-shape-small);
    background: var(--m3c-surface);
    color: var(--m3c-on-surface);
    cursor: pointer;
    text-align: left;
    transition: all 0.2s;
    border: none;
  }

  .anime-item:hover {
    background: var(--m3c-surface-container-high);
  }

  .anime-item.active {
    background: var(--m3c-primary-container);
    color: var(--m3c-on-primary-container);
  }

  .anime-item-content {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .anime-item-content h3 {
    margin: 0;
    font-size: 13px;
    font-weight: 500;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .badge {
    font-size: 11px;
    padding: 2px 8px;
    border-radius: var(--m3-shape-extra-small);
    width: fit-content;
  }

  .badge.success {
    background: var(--m3c-primary-container);
    color: var(--m3c-on-primary-container);
  }

  .badge.pending {
    background: var(--m3c-secondary-container);
    color: var(--m3c-on-secondary-container);
  }

  /* Search Panel */
  .search-panel {
    display: flex;
    flex-direction: column;
    gap: 16px;
    border-radius: var(--m3-shape-medium);
    background: var(--m3c-surface-container);
    padding: 16px;
    overflow: hidden;
  }

  .selected-anime {
    padding: 12px;
    background: var(--m3c-primary-container);
    border-radius: var(--m3-shape-small);
    color: var(--m3c-on-primary-container);
  }

  .selected-anime h3 {
    margin: 0 0 6px 0;
    font-size: 16px;
    font-weight: 500;
  }

  .subtitle {
    margin: 0;
    font-size: 12px;
    opacity: 0.9;
  }

  .search-section {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .search-input {
    display: flex;
    gap: 12px;
    align-items: flex-end;
  }

  .search-input :global(.m3-container) {
    flex: 1;
  }

  .loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 12px;
    padding: 24px;
    color: var(--m3c-on-surface-variant);
    text-align: center;
  }

  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 12px;
    flex: 1;
    color: var(--m3c-on-surface-variant);
    text-align: center;
  }

  .empty-state p {
    margin: 0;
  }

  .results-section {
    display: flex;
    flex-direction: column;
    gap: 12px;
    flex: 1;
    overflow-y: auto;
  }

  .results-section h4 {
    margin: 0;
    font-size: 14px;
    font-weight: 500;
    color: var(--m3c-on-surface);
  }

  .results-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
    overflow-y: auto;
    flex: 1;
  }

  .result-item {
    display: flex;
    gap: 12px;
    padding: 12px;
    cursor: pointer;
  }

  .result-poster {
    width: 60px;
    height: 90px;
    object-fit: cover;
    border-radius: var(--m3-shape-small);
    flex-shrink: 0;
  }

  .result-info {
    display: flex;
    flex-direction: column;
    gap: 6px;
    flex: 1;
    min-width: 0;
  }

  .result-info h5 {
    margin: 0;
    font-size: 13px;
    font-weight: 500;
    color: var(--m3c-on-surface);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .year {
    margin: 0;
    font-size: 11px;
    color: var(--m3c-on-surface-variant);
  }

  .rating {
    margin: 0;
    font-size: 11px;
    color: var(--m3c-tertiary);
    font-weight: 500;
  }

  .genres {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }

  .genre-tag {
    font-size: 9px;
    padding: 2px 6px;
    background: var(--m3c-surface-container-high);
    color: var(--m3c-on-surface-variant);
    border-radius: var(--m3-shape-extra-small);
  }

  /* Responsive */
  @media (max-width: 1024px) {
    .container {
      grid-template-columns: 1fr;
      height: auto;
    }

    .anime-list-panel {
      max-height: 300px;
    }
  }

  @media (max-width: 600px) {
    .main-content {
      padding: 12px;
    }
  }
</style>
