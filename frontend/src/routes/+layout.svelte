<script lang="ts">
  import { goto } from '$app/navigation';
  import { preloadData } from '$app/navigation';
  import '../app.css';
  import { Snackbar } from 'm3-svelte';
  import Icon from '@iconify/svelte';

  function handleLogout() {
    localStorage.removeItem('access_token');
    goto('/');
  }

  // Preload common routes on hover
  function handleMouseEnter(route: string) {
    preloadData(route);
  }
</script>

<div class="app-layout">
  <!-- Sidebar (Desktop only) -->
  <nav class="sidebar">
    <div class="logo">
      <Icon icon="mdi:play-circle" width="32" />
      <span>YUNA</span>
    </div>

    <ul class="nav-menu">
      <li>
        <a href="/dashboard" on:mouseenter={() => handleMouseEnter('/dashboard')} data-sveltekit-preload-data>
          <Icon icon="mdi:home" width="24" />
          <span>Home</span>
        </a>
      </li>
      <li>
        <a href="/search" on:mouseenter={() => handleMouseEnter('/search')} data-sveltekit-preload-data>
          <Icon icon="mdi:magnify" width="24" />
          <span>Cerca</span>
        </a>
      </li>
      <li>
        <a href="/anime" on:mouseenter={() => handleMouseEnter('/anime')} data-sveltekit-preload-data>
          <Icon icon="mdi:animation-play" width="24" />
          <span>Anime</span>
        </a>
      </li>
      <li>
        <a href="/series" on:mouseenter={() => handleMouseEnter('/series')} data-sveltekit-preload-data>
          <Icon icon="mdi:television-classic" width="24" />
          <span>Serie</span>
        </a>
      </li>
      <li>
        <a href="/films" on:mouseenter={() => handleMouseEnter('/films')} data-sveltekit-preload-data>
          <Icon icon="mdi:film" width="24" />
          <span>Film</span>
        </a>
      </li>
      <li>
        <a href="/manage" on:mouseenter={() => handleMouseEnter('/manage')} data-sveltekit-preload-data>
          <Icon icon="mdi:cog" width="24" />
          <span>Gestisci</span>
        </a>
      </li>
    </ul>

    <button class="logout-btn" on:click={handleLogout}>
      <Icon icon="mdi:logout" width="20" />
      <span>Esci</span>
    </button>
  </nav>

  <!-- Main Content -->
  <div class="main-wrapper">
    <slot />
    <Snackbar />
  </div>

  <!-- Bottom Navigation (Mobile) -->
  <nav class="bottom-nav">
    <a href="/dashboard" class="nav-item" data-sveltekit-preload-data>
      <Icon icon="mdi:home" width="24" />
      <span>Home</span>
    </a>
    <a href="/anime" class="nav-item" data-sveltekit-preload-data>
      <Icon icon="mdi:animation-play" width="24" />
      <span>Anime</span>
    </a>
    <a href="/series" class="nav-item" data-sveltekit-preload-data>
      <Icon icon="mdi:television-classic" width="24" />
      <span>Serie</span>
    </a>
    <a href="/films" class="nav-item" data-sveltekit-preload-data>
      <Icon icon="mdi:film" width="24" />
      <span>Film</span>
    </a>
    <a href="/manage" class="nav-item" data-sveltekit-preload-data>
      <Icon icon="mdi:cog" width="24" />
      <span>Gestisci</span>
    </a>
  </nav>
</div>

<style>
  .app-layout {
    display: flex;
    min-height: 100vh;
  }

  /* Sidebar */
  .sidebar {
    display: none;
    flex-direction: column;
    width: 250px;
    background: var(--m3c-surface-container-lowest);
    border-right: 1px solid var(--m3c-outline-variant);
    padding: 20px 12px;
    gap: 24px;
    position: fixed;
    height: 100vh;
    overflow-y: auto;
    z-index: 1000;
  }

  .logo {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 8px;
    font-size: 24px;
    font-weight: 700;
    color: var(--m3c-primary);
    margin-bottom: 12px;
  }

  .nav-menu {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 8px;
    flex: 1;
  }

  .nav-menu li {
    margin: 0;
  }

  .nav-menu a {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 12px 16px;
    border-radius: var(--m3-shape-medium);
    color: var(--m3c-on-surface-variant);
    text-decoration: none;
    font-size: 14px;
    font-weight: 500;
    transition: all 0.2s;
    border: none;
    background: none;
    cursor: pointer;
    width: 100%;
    text-align: left;
  }

  .nav-menu a:hover {
    background: var(--m3c-surface-container);
    color: var(--m3c-on-surface);
  }

  .logout-btn {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 12px 16px;
    border-radius: var(--m3-shape-medium);
    border: none;
    background: var(--m3c-error-container);
    color: var(--m3c-on-error-container);
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: background 0.2s;
    width: 100%;
    text-align: left;
  }

  .logout-btn:hover {
    background: var(--m3c-error);
    color: var(--m3c-on-error);
  }

  /* Bottom Navigation (Mobile) */
  .bottom-nav {
    display: flex;
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

  .main-wrapper {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  /* Desktop Layout */
  @media (min-width: 769px) {
    .sidebar {
      display: flex;
    }

    .main-wrapper {
      margin-left: 250px;
    }

    .bottom-nav {
      display: none;
    }
  }

  /* Mobile Layout */
  @media (max-width: 768px) {
    .main-wrapper {
      padding-bottom: 80px;
    }
  }
</style>

