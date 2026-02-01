<script lang="ts">
  import { onMount } from 'svelte';
  import { Button } from 'm3-svelte';
  import Icon from '@iconify/svelte';

  let deferredPrompt: any = null;
  let showInstallButton = $state(false);
  let isInstalled = $state(false);
  let debugInfo = $state('');

  onMount(() => {
    console.log('[PWA] InstallButton mounted');
    
    // Check if already installed
    if (window.matchMedia('(display-mode: standalone)').matches) {
      isInstalled = true;
      debugInfo = 'Already installed';
      console.log('[PWA] App already installed');
      return;
    }

    // Check browser support
    if (!('BeforeInstallPromptEvent' in window)) {
      debugInfo = 'Browser does not support PWA install';
      console.warn('[PWA] beforeinstallprompt not supported');
    }

    // Listen for beforeinstallprompt event
    window.addEventListener('beforeinstallprompt', (e) => {
      console.log('[PWA] beforeinstallprompt event received!');
      e.preventDefault();
      deferredPrompt = e;
      showInstallButton = true;
      debugInfo = 'Ready to install';
    });

    // Listen for app installed event
    window.addEventListener('appinstalled', () => {
      console.log('[PWA] App installed!');
      isInstalled = true;
      showInstallButton = false;
      deferredPrompt = null;
      debugInfo = 'Installed!';
    });

    // Debug: check after 2 seconds
    setTimeout(() => {
      if (!showInstallButton && !isInstalled) {
        console.warn('[PWA] No install prompt after 2s. Possible reasons:');
        console.warn('- Not HTTPS (except localhost)');
        console.warn('- App already installed');
        console.warn('- Browser does not support (Firefox, Safari)');
        console.warn('- Missing manifest or service worker criteria');
        debugInfo = 'Install not available (check console)';
      }
    }, 2000);
  });

  async function installApp() {
    if (!deferredPrompt) return;

    // Show install prompt
    deferredPrompt.prompt();

    // Wait for user response
    const { outcome } = await deferredPrompt.userChoice;
    
    if (outcome === 'accepted') {
      console.log('User accepted the install prompt');
    }

    deferredPrompt = null;
    showInstallButton = false;
  }
</script>

{#if showInstallButton && !isInstalled}
  <Button variant="tonal" onclick={installApp}>
    <Icon icon="mdi:download" width="20" />
    Installa App
  </Button>
{/if}

{#if isInstalled}
  <div class="installed-badge">
    <Icon icon="mdi:check-circle" width="16" />
    <span>App Installata</span>
  </div>
{/if}

<!-- Debug info (dev mode only) -->
{#if import.meta.env.DEV && debugInfo}
  <div class="debug-info">
    <Icon icon="mdi:information-outline" width="14" />
    <span>{debugInfo}</span>
  </div>
{/if}

<style>
  .installed-badge {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 12px;
    background: var(--m3c-primary-container);
    color: var(--m3c-on-primary-container);
    border-radius: var(--m3-shape-full);
    font-size: 13px;
    font-weight: 500;
  }

  .debug-info {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 10px;
    background: var(--m3c-secondary-container);
    color: var(--m3c-on-secondary-container);
    border-radius: var(--m3-shape-small);
    font-size: 11px;
    font-family: monospace;
    opacity: 0.8;
  }
</style>
