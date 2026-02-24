import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'

export default defineConfig({
  plugins: [svelte()],
  build: {
    // Avoid collision with game assets served at /assets
    assetsDir: '_app',
  },
})
