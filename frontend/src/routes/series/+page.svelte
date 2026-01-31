<script lang="ts">
  import { goto } from '$app/navigation';
  import { Button, Card } from 'm3-svelte';
  import Icon from '@iconify/svelte';

  function goToSearch() {
    goto('/search');
  }
</script>

<svelte:head>
  <title>YUNA - Serie TV</title>
</svelte:head>

<div class="content-page">
  <!-- Top Bar -->
  <header class="top-bar">
    <div class="top-bar-content">
      <button class="back-button" on:click={() => goto('/dashboard')}>
        <Icon icon="mdi:arrow-left" width="24" />
      </button>
      <h1 class="page-title">Serie TV</h1>
    </div>
  </header>

  <!-- Main Content -->
  <main class="main-content">
    <div class="empty-state">
      <Card variant="outlined">
        <div class="empty-content">
          <Icon icon="mdi:television-classic" width="64" color="var(--m3c-outline)" />
          <h3>Nessuna serie</h3>
          <p>Inizia ad aggiungere serie TV alla tua libreria</p>
          <Button variant="filled" onclick={goToSearch}>
            <Icon icon="mdi:magnify" width="20" />
            Cerca
          </Button>
        </div>
      </Card>
    </div>
  </main>
</div>

<style>
  .content-page {
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
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 16px;
    padding-bottom: 80px;
  }

  /* Empty State */
  .empty-state {
    width: 100%;
    max-width: 400px;
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
  }
</style>
