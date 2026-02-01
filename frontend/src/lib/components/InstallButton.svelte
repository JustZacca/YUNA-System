<script lang="ts">
  import { onMount } from 'svelte';
  import { Button } from 'm3-svelte';
  import Icon from '@iconify/svelte';

  let deferredPrompt: any = null;
  let showInstallButton = $state(false);
  let isInstalled = $state(false);

  onMount(() => {
    // Check if already installed
    if (window.matchMedia('(display-mode: standalone)').matches) {
      isInstalled = true;
      return;
    }

    // Listen for beforeinstallprompt event
    window.addEventListener('beforeinstallprompt', (e) => {
      e.preventDefault();
      deferredPrompt = e;
      showInstallButton = true;
    });

    // Listen for app installed event
    window.addEventListener('appinstalled', () => {
      isInstalled = true;
      showInstallButton = false;
      deferredPrompt = null;
    });
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
</style>
