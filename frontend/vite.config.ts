import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import tailwindcss from '@tailwindcss/vite';
import path from 'path';

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    tailwindcss(),
    svelte(), // <-- Must come after Tailwind
  ],
  server: {
    port: 3000,
  },
  resolve: {
    alias: {
      $lib: path.resolve('./src/lib'),
    },
  },
  define: {
    'process.env': process.env,
  },
});
