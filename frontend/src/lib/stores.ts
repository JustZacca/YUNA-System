import { writable, derived } from 'svelte/store';
import { api } from './api';
import type { User } from './types';

function createUserStore() {
  const { subscribe, set, update } = writable<User | null>(null);

  return {
    subscribe,
    login: async (username: string, password: string) => {
      try {
        const response = await api.login({ username, password });
        const user = await api.getCurrentUser();
        set(user);
        return { success: true, message: 'Login successful' };
      } catch (error: any) {
        return { success: false, message: error.message || 'Login failed' };
      }
    },
    logout: () => {
      console.log('Logging out...');
      api.logout();
      set(null);
      console.log('User store cleared');
    },
    checkAuth: async () => {
      if (api.isAuthenticated) {
        try {
          const user = await api.getCurrentUser();
          set(user);
        } catch {
          api.logout();
          set(null);
        }
      }
    }
  };
}

export const user = createUserStore();

export const isAuthenticated = derived(user, $user => !!$user);