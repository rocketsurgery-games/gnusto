import { defineConfig } from 'vite'

export default defineConfig({
  build: {
    // Avoid collision with game assets served at /assets
    assetsDir: '_app',
  },
})
