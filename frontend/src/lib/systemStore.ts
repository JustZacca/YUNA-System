import { writable } from 'svelte/store';
import { api } from '$lib/api';
import type { SystemHealth, SystemStats } from '$lib/types';

export const health = writable<SystemHealth | null>(null);
export const stats = writable<SystemStats | null>(null);
export const loading = writable(false);
export const error = writable<string | null>(null);

export async function loadSystemData() {
  loading.set(true);
  error.set(null);
  try {
    const [h, s] = await Promise.all([
      api.getHealth(),
      api.getStats()
    ]);
    health.set(h);
    stats.set(s);
  } catch (err: any) {
    error.set(err.message || 'Failed to load system data');
  } finally {
    loading.set(false);
  }
}
