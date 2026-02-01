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
  build: {
    target: 'es2020',
    minify: 'esbuild',
    cssMinify: true,
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor': ['svelte'],
          'ui': ['m3-svelte', '@iconify/svelte']
        }
      }
    }
  },
  optimizeDeps: {
    include: ['m3-svelte', '@iconify/svelte']
  },
  define: {
    'import.meta.env.VITE_API_URL': JSON.stringify(process.env.NODE_ENV === 'production' ? '/api' : 'http://localhost:8000/api')
  }
});
