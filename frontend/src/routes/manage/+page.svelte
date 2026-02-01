<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { user, isAuthenticated } from '$lib/stores';
  import { api } from '$lib/api';
  import { Button, Card, TextFieldOutlined, LinearProgressEstimate, snackbar } from 'm3-svelte';
  import Icon from '@iconify/svelte';

  type MediaType = 'anime' | 'series' | 'films';
  
  let activeTab: MediaType = 'anime';
  let mediaList: any[] = [];
  let searchResults: any[] = [];
  let loading = false;
  let searching = false;
  let currentMedia: any = null;
  let searchQuery = '';
  let selectedResult: any = null;
  let showDeleteConfirm = false;
  let deleteTarget: any = null;
  let deleting = false;

  const TMDB_IMAGE_BASE = 'https://image.tmdb.org/t/p/w500';

  function cleanMediaName(name: string, type: MediaType): string {
    let cleaned = name;
    if (type === 'anime') {
      cleaned = cleaned
        .replace(/\s*\(ITA\)\s*/gi, '')
        .replace(/\s*\(SUB ITA\)\s*/gi, '')
        .replace(/\s*\(DUB ITA\)\s*/gi, '');
    } else {
      cleaned = cleaned.replace(/\s*\(\d{4}\)\s*/g, '');
    }
    return cleaned.trim();
  }

  onMount(async () => {
    await user.checkAuth();
    if (!$isAuthenticated) {
      goto('/');
      return;
    }
    await loadMedia();
  });

  async function loadMedia() {
    loading = true;
    try {
      let response;
      switch (activeTab) {
        case 'anime':
          response = await api.getAnimeList();
          break;
        case 'series':
          response = await api.getSeriesList();
          break;
        case 'films':
          response = await api.getFilmsList();
          break;
      }
      mediaList = response.items || [];
    } catch (err: any) {
      snackbar(`Errore nel caricamento dei ${getMediaLabel(activeTab)}`, undefined, true);
    } finally {
      loading = false;
    }
  }

  async function searchMedia() {
    if (!currentMedia || !searchQuery.trim()) {
      snackbar('Inserisci un nome da cercare', undefined, true);
      return;
    }

    searching = true;
    try {
      const response = await api.search(searchQuery, activeTab === 'films' ? 'film' : activeTab);
      searchResults = response[activeTab] || [];
      if (searchResults.length === 0) {
        snackbar('Nessun risultato trovato', undefined, true);
      }
    } catch (err: any) {
      snackbar('Errore nella ricerca', undefined, true);
    } finally {
      searching = false;
    }
  }

  async function associateMedia() {
    if (!currentMedia || !selectedResult) {
      snackbar('Seleziona un elemento da associare', undefined, true);
      return;
    }

    loading = true;
    try {
      let id;
      if (activeTab === 'anime') {
        id = selectedResult.mal_id || selectedResult.anilist_id;
        if (!id) {
          snackbar('Nessun ID AniList trovato', undefined, true);
          loading = false;
          return;
        }
        await api.updateAnimeMetadata(currentMedia.name, id);
      } else if (activeTab === 'series') {
        id = selectedResult.tmdb_id;
        if (!id) {
          snackbar('Nessun ID TMDB trovato', undefined, true);
          loading = false;
          return;
        }
        await api.updateSeriesMetadata(currentMedia.name, id);
      } else if (activeTab === 'films') {
        id = selectedResult.tmdb_id;
        if (!id) {
          snackbar('Nessun ID TMDB trovato', undefined, true);
          loading = false;
          return;
        }
        await api.updateFilmMetadata(currentMedia.name, id);
      }
      
      snackbar(`${cleanMediaName(currentMedia.name, activeTab)} associato con successo!`, undefined, false);
      currentMedia = null;
      searchQuery = '';
      searchResults = [];
      selectedResult = null;
      await loadMedia();
    } catch (err: any) {
      snackbar(err.message || 'Errore nell\'associazione', undefined, true);
    } finally {
      loading = false;
    }
  }

  function confirmDelete(media: any) {
    deleteTarget = media;
    showDeleteConfirm = true;
  }

  async function deleteMedia() {
    if (!deleteTarget) return;
    
    deleting = true;
    try {
      if (activeTab === 'anime') {
        await api.deleteAnime(deleteTarget.name);
      } else if (activeTab === 'series') {
        await api.deleteSeries(deleteTarget.name);
      } else if (activeTab === 'films') {
        await api.deleteFilm(deleteTarget.name);
      }
      
      snackbar(`${cleanMediaName(deleteTarget.name, activeTab)} eliminato con successo!`, undefined, false);
      showDeleteConfirm = false;
      deleteTarget = null;
      
      // Reset current media if it was the one deleted
      if (currentMedia?.name === deleteTarget?.name) {
        currentMedia = null;
        searchQuery = '';
        searchResults = [];
        selectedResult = null;
      }
      
      await loadMedia();
    } catch (err: any) {
      snackbar(err.message || 'Errore nella cancellazione', undefined, true);
    } finally {
      deleting = false;
    }
  }

  function cancelDelete() {
    showDeleteConfirm = false;
    deleteTarget = null;
  }

  function getMediaLabel(type: MediaType): string {
    switch (type) {
      case 'anime': return 'anime';
      case 'series': return 'serie TV';
      case 'films': return 'film';
    }
  }

  function getMediaIcon(type: MediaType): string {
    switch (type) {
      case 'anime': return 'mdi:animation-play';
      case 'series': return 'mdi:television';
      case 'films': return 'mdi:movie';
    }
  }

  function switchTab(tab: MediaType) {
    if (tab === activeTab) return;
    activeTab = tab;
    currentMedia = null;
    searchQuery = '';
    searchResults = [];
    selectedResult = null;
    loadMedia();
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Enter') {
      searchMedia();
    }
  }

  function hasMetadata(media: any): boolean {
    if (activeTab === 'anime') {
      return !!media.poster_url || !!media.poster;
    } else {
      return !!media.tmdb_id;
    }
  }
</script>

<svelte:head>
  <title>YUNA - Gestisci Media</title>
</svelte:head>

<div class="manage-page">
  <!-- Top Bar -->
  <header class="top-bar">
    <div class="top-bar-content">
      <button class="back-button" on:click={() => goto('/dashboard')}>
        <Icon icon="mdi:arrow-left" width="24" />
      </button>
      <h1 class="page-title">Gestisci Media</h1>
    </div>
  </header>

  <!-- Tabs -->
  <div class="tabs-container">
    <div class="tabs">
      <button
        class="tab"
        class:active={activeTab === 'anime'}
        on:click={() => switchTab('anime')}
      >
        <Icon icon="mdi:animation-play" width="20" />
        <span>Anime</span>
      </button>
      <button
        class="tab"
        class:active={activeTab === 'series'}
        on:click={() => switchTab('series')}
      >
        <Icon icon="mdi:television" width="20" />
        <span>Serie TV</span>
      </button>
      <button
        class="tab"
        class:active={activeTab === 'films'}
        on:click={() => switchTab('films')}
      >
        <Icon icon="mdi:movie" width="20" />
        <span>Film</span>
      </button>
    </div>
  </div>

  <!-- Main Content -->
  <main class="main-content">
    <div class="container">
      <!-- Left Panel: Media List -->
      <div class="media-list-panel">
        <div class="panel-header">
          <h2>I Miei {getMediaLabel(activeTab)}</h2>
          <span class="count">{mediaList.length}</span>
        </div>
        
        {#if loading && mediaList.length === 0}
          <div class="loading">
            <LinearProgressEstimate sToHalfway={2} />
          </div>
        {:else if mediaList.length === 0}
          <div class="empty-state">
            <Icon icon={getMediaIcon(activeTab)} width="48" color="var(--m3c-outline)" />
            <p>Nessun {getMediaLabel(activeTab)} trovato</p>
          </div>
        {:else}
          <div class="media-items">
            {#each mediaList as media}
              <div
                class="media-item"
                class:active={currentMedia?.name === media.name}
              >
                <button
                  class="media-item-button"
                  on:click={() => {
                    currentMedia = media;
                    searchQuery = cleanMediaName(media.name, activeTab);
                    searchResults = [];
                    selectedResult = null;
                  }}
                >
                  <div class="media-item-content">
                    <h3>{cleanMediaName(media.name, activeTab)}</h3>
                    <div class="media-badges">
                      {#if hasMetadata(media)}
                        <span class="badge success">
                          <Icon icon="mdi:check-circle" width="14" />
                          Metadati
                        </span>
                      {:else}
                        <span class="badge pending">
                          <Icon icon="mdi:alert-circle-outline" width="14" />
                          No metadati
                        </span>
                      {/if}
                      {#if activeTab === 'anime'}
                        <span class="badge-info">{media.episodes_downloaded}/{media.episodes_total} ep</span>
                      {:else if activeTab === 'series'}
                        <span class="badge-info">{media.episodes_downloaded}/{media.episodes_total || '?'} ep</span>
                      {/if}
                    </div>
                  </div>
                </button>
                <button
                  class="delete-button"
                  on:click={() => confirmDelete(media)}
                  title="Elimina"
                >
                  <Icon icon="mdi:delete-outline" width="20" />
                </button>
              </div>
            {/each}
          </div>
        {/if}
      </div>

      <!-- Right Panel: Search & Results -->
      <div class="search-panel">
        {#if currentMedia}
          <div class="selected-media">
            <div class="selected-header">
              <Icon icon={getMediaIcon(activeTab)} width="24" />
              <h3>{cleanMediaName(currentMedia.name, activeTab)}</h3>
            </div>
            <div class="selected-info">
              {#if activeTab === 'anime'}
                <span>Episodi: {currentMedia.episodes_downloaded}/{currentMedia.episodes_total}</span>
              {:else if activeTab === 'series'}
                <span>Episodi: {currentMedia.episodes_downloaded}/{currentMedia.episodes_total || '?'}</span>
              {:else}
                <span>Anno: {currentMedia.year || 'N/D'}</span>
              {/if}
            </div>
          </div>

          <!-- Search -->
          <div class="search-section">
            <div class="search-input">
              <TextFieldOutlined
                label="Cerca {activeTab === 'anime' ? 'su AniList' : 'su TMDB'}..."
                bind:value={searchQuery}
                onkeydown={handleKeydown}
                disabled={searching}
              />
              <Button
                variant="filled"
                onclick={searchMedia}
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
          {:else if searchResults.length > 0}
            <div class="results-section">
              <h4>Risultati ({searchResults.length})</h4>
              <div class="results-list">
                {#each searchResults as result}
                  <button
                    class="result-item"
                    class:selected={selectedResult === result}
                    on:click={() => { selectedResult = result; }}
                  >
                    {#if result.poster}
                      <img src={result.poster} alt={result.name} class="result-poster" />
                    {:else}
                      <div class="result-poster-placeholder">
                        <Icon icon={getMediaIcon(activeTab)} width="20" />
                      </div>
                    {/if}
                    <div class="result-info">
                      <h5>{result.name}</h5>
                      <div class="result-meta">
                        {#if result.year}
                          <span><Icon icon="mdi:calendar" width="12" /> {result.year}</span>
                        {/if}
                        {#if result.rating || result.vote_average}
                          <span class="rating">
                            <Icon icon="mdi:star" width="12" />
                            {(result.rating || result.vote_average).toFixed(1)}
                          </span>
                        {/if}
                      </div>
                      {#if result.genres && result.genres.length > 0}
                        <div class="genres">
                          {#each result.genres.slice(0, 2) as genre}
                            <span class="genre-tag">{genre}</span>
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

              {#if selectedResult}
                <Button variant="filled" onclick={associateMedia} disabled={loading}>
                  <Icon icon="mdi:link-variant" width="20" />
                  Associa Metadati
                </Button>
              {/if}
            </div>
          {:else if searchResults.length === 0 && searchQuery}
            <div class="empty-state">
              <Icon icon="mdi:magnify-close" width="48" color="var(--m3c-outline)" />
              <p>Nessun risultato trovato per "{searchQuery}"</p>
            </div>
          {/if}
        {:else}
          <div class="empty-state">
            <Icon icon="mdi:arrow-left" width="48" color="var(--m3c-outline)" />
            <p>Seleziona un {getMediaLabel(activeTab)} dalla lista</p>
          </div>
        {/if}
      </div>
    </div>
  </main>

  <!-- Delete Confirmation Modal -->
  {#if showDeleteConfirm && deleteTarget}
    <div 
      class="modal-overlay"
      on:click={cancelDelete}
      on:keydown={(e) => e.key === 'Escape' && cancelDelete()}
      role="button"
      tabindex="0"
    >
      <div
        class="modal-content delete-modal"
        on:click={(e) => e.stopPropagation()}
        on:keydown={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        tabindex="-1"
      >
        <div class="modal-header">
          <Icon icon="mdi:alert-circle" width="48" color="var(--m3c-error)" />
          <h2>Conferma Eliminazione</h2>
        </div>
        <div class="modal-body">
          <p>Sei sicuro di voler eliminare <strong>{cleanMediaName(deleteTarget.name, activeTab)}</strong>?</p>
          <p class="warning-text">Questa azione eliminerà tutti i file e i metadati associati. L'operazione è irreversibile.</p>
        </div>
        <div class="modal-footer">
          <Button variant="text" onclick={cancelDelete} disabled={deleting}>
            Annulla
          </Button>
          <Button variant="filled" onclick={deleteMedia} disabled={deleting}>
            {#if deleting}
              <Icon icon="mdi:loading" width="18" class="spinning" />
              Eliminazione...
            {:else}
              <Icon icon="mdi:delete" width="18" />
              Elimina
            {/if}
          </Button>
        </div>
      </div>
    </div>
  {/if}
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
    z-index: 101;
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

  /* Tabs */
  .tabs-container {
    position: sticky;
    top: 64px;
    z-index: 100;
    background: var(--m3c-surface);
    border-bottom: 1px solid var(--m3c-outline-variant);
  }

  .tabs {
    max-width: 1400px;
    margin: 0 auto;
    display: flex;
    gap: 4px;
    padding: 0 16px;
  }

  .tab {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px 24px;
    border: none;
    background: none;
    color: var(--m3c-on-surface-variant);
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    border-bottom: 2px solid transparent;
    transition: all 0.2s;
  }

  .tab:hover {
    background: var(--m3c-surface-container);
  }

  .tab.active {
    color: var(--m3c-primary);
    border-bottom-color: var(--m3c-primary);
  }

  /* Main Content */
  .main-content {
    flex: 1;
    max-width: 1400px;
    margin: 0 auto;
    padding: 24px 16px;
    padding-bottom: 120px;
    width: 100%;
    box-sizing: border-box;
  }

  .container {
    display: grid;
    grid-template-columns: 400px 1fr;
    gap: 24px;
    height: 100%;
  }

  /* Media List Panel */
  .media-list-panel {
    display: flex;
    flex-direction: column;
    gap: 16px;
    background: var(--m3c-surface-container);
    border: 1px solid var(--m3c-outline-variant);
    border-radius: var(--m3-shape-large);
    padding: 20px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  }

  .panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--m3c-outline-variant);
  }

  .panel-header h2 {
    font-size: 20px;
    font-weight: 600;
    color: var(--m3c-on-surface);
    margin: 0;
    text-transform: capitalize;
  }

  .count {
    display: flex;
    align-items: center;
    justify-content: center;
    min-width: 32px;
    height: 32px;
    padding: 0 12px;
    background: var(--m3c-primary-container);
    color: var(--m3c-on-primary-container);
    border-radius: var(--m3-shape-full);
    font-size: 14px;
    font-weight: 600;
  }

  .media-items {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .media-item {
    display: flex;
    align-items: stretch;
    gap: 4px;
    background: var(--m3c-surface);
    border: 1px solid var(--m3c-outline-variant);
    border-radius: var(--m3-shape-medium);
    overflow: hidden;
    transition: all 0.2s;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
  }

  .media-item:hover {
    border-color: var(--m3c-primary);
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    transform: translateY(-1px);
  }

  .media-item.active {
    background: var(--m3c-primary-container);
    border-color: var(--m3c-primary);
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.12);
  }

  .media-item-button {
    flex: 1;
    display: block;
    text-align: left;
    border: none;
    background: none;
    padding: 14px 16px;
    cursor: pointer;
    transition: background 0.2s;
  }

  .media-item-button:hover {
    background: rgba(0, 0, 0, 0.03);
  }

  .media-item-content h3 {
    font-size: 14px;
    font-weight: 500;
    color: var(--m3c-on-surface);
    margin: 0 0 8px 0;
    line-height: 1.3;
  }

  .media-badges {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }

  .badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 4px 8px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 500;
  }

  .badge.success {
    background: var(--m3c-tertiary-container);
    color: var(--m3c-on-tertiary-container);
  }

  .badge.pending {
    background: var(--m3c-error-container);
    color: var(--m3c-on-error-container);
  }

  .badge-info {
    padding: 4px 8px;
    background: var(--m3c-surface-container-highest);
    color: var(--m3c-on-surface-variant);
    border-radius: 12px;
    font-size: 11px;
    font-weight: 500;
  }

  .delete-button {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 44px;
    border: none;
    background: none;
    color: var(--m3c-error);
    cursor: pointer;
    transition: background 0.2s;
  }

  .delete-button:hover {
    background: var(--m3c-error-container);
  }

  /* Search Panel */
  .search-panel {
    display: flex;
    flex-direction: column;
    gap: 20px;
    background: var(--m3c-surface-container);
    border: 1px solid var(--m3c-outline-variant);
    border-radius: var(--m3-shape-large);
    padding: 24px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  }

  .selected-media {
    padding: 16px;
    background: var(--m3c-primary-container);
    border-radius: var(--m3-shape-medium);
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
  }

  .selected-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 8px;
  }

  .selected-header h3 {
    font-size: 18px;
    font-weight: 600;
    color: var(--m3c-on-primary-container);
    margin: 0;
  }

  .selected-info {
    font-size: 14px;
    color: var(--m3c-on-primary-container);
    opacity: 0.8;
  }

  .search-section {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .search-input {
    display: flex;
    gap: 12px;
  }

  .search-input :global(.m3-container) {
    flex: 1;
  }

  .results-section {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .results-section h4 {
    font-size: 16px;
    font-weight: 600;
    color: var(--m3c-on-surface);
    margin: 0;
  }

  .results-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
    max-height: 200px;
    overflow-y: auto;
    padding: 2px;
  }

  .result-item {
    position: relative;
    display: flex;
    gap: 8px;
    padding: 6px;
    background: var(--m3c-surface);
    border: 2px solid var(--m3c-outline-variant);
    border-radius: var(--m3-shape-small);
    cursor: pointer;
    transition: all 0.2s;
    text-align: left;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
  }

  .result-item:hover {
    border-color: var(--m3c-primary);
    background: var(--m3c-surface-container-high);
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    transform: translateY(-1px);
  }

  .result-item.selected {
    border-color: var(--m3c-primary);
    background: var(--m3c-primary-container);
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.12);
  }

  .result-poster {
    width: 35px;
    height: 52px;
    object-fit: cover;
    border-radius: 4px;
    flex-shrink: 0;
  }

  .result-poster-placeholder {
    width: 35px;
    height: 52px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--m3c-surface-container-highest);
    border-radius: 4px;
    color: var(--m3c-outline);
    flex-shrink: 0;
  }

  .result-poster-placeholder :global(svg) {
    width: 20px;
    height: 20px;
  }

  .result-info {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 4px;
    min-width: 0;
  }

  .result-info h5 {
    font-size: 12px;
    font-weight: 600;
    color: var(--m3c-on-surface);
    margin: 0;
    line-height: 1.2;
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 1;
    -webkit-box-orient: vertical;
  }

  .result-meta {
    display: flex;
    gap: 6px;
    font-size: 10px;
    color: var(--m3c-on-surface-variant);
  }

  .result-meta span {
    display: flex;
    align-items: center;
    gap: 3px;
  }

  .result-meta .rating {
    color: #f59e0b;
  }

  .genres {
    display: flex;
    gap: 3px;
    flex-wrap: wrap;
  }

  .genre-tag {
    padding: 2px 5px;
    background: var(--m3c-secondary-container);
    color: var(--m3c-on-secondary-container);
    border-radius: 8px;
    font-size: 9px;
    font-weight: 500;
  }

  .selected-check {
    position: absolute;
    top: 6px;
    right: 6px;
    color: var(--m3c-primary);
  }

  .selected-check :global(svg) {
    width: 18px;
    height: 18px;
  }

  /* Empty State */
  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 16px;
    padding: 48px 24px;
    text-align: center;
    color: var(--m3c-on-surface-variant);
  }

  .empty-state p {
    margin: 0;
    font-size: 14px;
  }

  /* Loading */
  .loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;
    padding: 32px;
    text-align: center;
    color: var(--m3c-on-surface-variant);
  }

  .loading p {
    margin: 0;
    font-size: 14px;
  }

  /* Delete Modal */
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
    max-width: 500px;
    width: 100%;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  }

  .delete-modal .modal-header {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;
    padding: 32px 24px 16px;
  }

  .delete-modal .modal-header h2 {
    font-size: 22px;
    font-weight: 600;
    color: var(--m3c-on-surface);
    margin: 0;
  }

  .modal-body {
    padding: 16px 24px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .modal-body p {
    margin: 0;
    font-size: 14px;
    color: var(--m3c-on-surface);
    line-height: 1.5;
  }

  .warning-text {
    color: var(--m3c-error) !important;
    font-weight: 500;
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
  @media (max-width: 968px) {
    .main-content {
      padding: 16px 12px;
      padding-bottom: 120px;
    }

    .container {
      grid-template-columns: 1fr;
      gap: 16px;
    }

    .media-list-panel {
      padding: 16px;
    }

    .search-panel {
      padding: 16px;
      min-height: auto;
    }

    .tabs {
      justify-content: space-around;
      padding: 0 8px;
    }

    .tab {
      padding: 12px 16px;
      font-size: 13px;
    }

    /* Mantieni le stesse dimensioni compatte */
    .results-list {
      max-height: 200px;
    }

    .result-item {
      padding: 6px;
      gap: 8px;
    }

    .result-poster,
    .result-poster-placeholder {
      width: 35px;
      height: 52px;
    }

    .result-info h5 {
      font-size: 12px;
    }

    .result-meta {
      font-size: 10px;
    }

    .genre-tag {
      font-size: 9px;
      padding: 2px 5px;
    }

    .modal-content {
      max-width: calc(100vw - 32px);
      margin: 16px;
    }
  }

  @media (max-width: 640px) {
    .main-content {
      padding: 12px 8px;
      padding-bottom: 100px;
    }

    .top-bar-content {
      padding: 12px 12px;
    }

    .page-title {
      font-size: 18px;
    }

    .tab {
      padding: 10px 12px;
      font-size: 12px;
    }

    .tab span {
      display: none;
    }

    .panel-header h2 {
      font-size: 18px;
    }

    .media-list-panel {
      padding: 12px;
    }

    .search-panel {
      padding: 12px;
    }

    .media-item-content h3 {
      font-size: 13px;
    }

    .media-item-button {
      padding: 10px 12px;
    }

    .delete-button {
      width: 40px;
    }

    .selected-media {
      padding: 12px;
    }

    .selected-header h3 {
      font-size: 16px;
    }

    .search-input {
      flex-direction: column;
      gap: 8px;
    }

    .results-section h4 {
      font-size: 14px;
    }

    /* Mantieni le stesse dimensioni compatte */
    .results-list {
      max-height: 200px;
    }

    .result-item {
      padding: 6px;
      gap: 8px;
    }

    .result-poster,
    .result-poster-placeholder {
      width: 35px;
      height: 52px;
    }

    .result-info h5 {
      font-size: 12px;
      -webkit-line-clamp: 1;
    }

    .result-meta {
      font-size: 10px;
      gap: 6px;
    }

    .genre-tag {
      font-size: 9px;
      padding: 2px 5px;
    }
  }
</style>
