import adapter from '@sveltejs/adapter-auto';

/** @type {import('@sveltejs/kit').Config} */
const config = {
  kit: {
    adapter: adapter(),
    appDir: 'src',
    prerender: {
      handleHttpError: 'warn'
    }
  }
};

export default config;