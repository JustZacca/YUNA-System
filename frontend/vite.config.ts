import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
import { functionsMixins } from 'vite-plugin-functions-mixins';

export default defineConfig({
  plugins: [
    functionsMixins({ deps: ['m3-svelte'] }),
    sveltekit()
  ],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false
      }
    }
  },
  define: {
    'import.meta.env.VITE_API_URL': JSON.stringify(process.env.NODE_ENV === 'production' ? '/api' : 'http://localhost:8000/api')
  }
});
