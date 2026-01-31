<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { user, isAuthenticated } from '$lib/stores';
  import { Button, TextFieldOutlined, Card, LinearProgressEstimate, snackbar } from 'm3-svelte';
  import Icon from '@iconify/svelte';

  let username = '';
  let password = '';
  let loading = false;

  onMount(async () => {
    await user.checkAuth();
    if ($isAuthenticated) {
      goto('/dashboard');
    }
  });

  async function handleLogin() {
    if (!username || !password) {
      snackbar('Inserisci username e password', undefined, true);
      return;
    }

    loading = true;

    try {
      const result = await user.login(username, password);
      if (result.success) {
        snackbar('Login effettuato!', undefined, true);
        goto('/dashboard');
      } else {
        snackbar(result.message || 'Login fallito', undefined, true);
      }
    } catch (e: any) {
      snackbar(e.message || 'Errore di connessione', undefined, true);
    } finally {
      loading = false;
    }
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Enter') {
      handleLogin();
    }
  }
</script>

<svelte:head>
  <title>YUNA - Login</title>
</svelte:head>

<div class="login-container">
  <div class="login-card">
    <!-- Logo -->
    <div class="logo-section">
      <div class="logo">
        <Icon icon="mdi:play-circle" width="48" />
      </div>
      <h1 class="title">YUNA</h1>
      <p class="subtitle">Your Underground Networked Animebot</p>
    </div>

    <!-- Login Form -->
    <Card variant="filled">
      <div class="form-content">
        <h2 class="form-title">Accedi</h2>

        <div class="field">
          <TextFieldOutlined
            label="Username"
            bind:value={username}
            disabled={loading}
          />
        </div>

        <div class="field">
          <TextFieldOutlined
            label="Password"
            bind:value={password}
            type="password"
            disabled={loading}
            onkeydown={handleKeydown}
          />
        </div>

        {#if loading}
          <LinearProgressEstimate sToHalfway={2} />
        {/if}

        <Button
          variant="filled"
          onclick={handleLogin}
          disabled={loading}
        >
          {loading ? 'Accesso in corso...' : 'Accedi'}
        </Button>
      </div>
    </Card>
  </div>
</div>

<style>
  .login-container {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 24px;
    background: linear-gradient(135deg, var(--m3c-surface-dim) 0%, var(--m3c-surface) 100%);
  }

  .login-card {
    width: 100%;
    max-width: 420px;
    display: flex;
    flex-direction: column;
    gap: 0;
  }

  .logo-section {
    text-align: center;
    padding: 32px 24px 24px;
  }

  .logo {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 80px;
    height: 80px;
    background: var(--m3c-primary-container);
    border-radius: var(--m3-shape-extra-large);
    color: var(--m3c-on-primary-container);
    margin: 0 auto 20px;
  }

  .title {
    font-size: 36px;
    font-weight: 700;
    color: var(--m3c-primary);
    margin: 0 0 12px 0;
    letter-spacing: -0.5px;
  }

  .subtitle {
    font-size: 14px;
    color: var(--m3c-on-surface-variant);
    margin: 0;
    line-height: 1.4;
  }

  .form-content {
    padding: 28px 24px;
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .form-title {
    font-size: 24px;
    font-weight: 500;
    color: var(--m3c-on-surface);
    margin: 0 0 8px 0;
    text-align: center;
  }

  .field {
    width: 100%;
  }

  :global(.field .m3-container) {
    width: 100%;
  }
</style>
