import { defineConfig } from 'vite';

export default defineConfig({
  base: '/',
  build: { outDir: '../static/app', emptyOutDir: true },
  server: { proxy: { '/api': 'http://127.0.0.1:8000', '/v1': 'http://127.0.0.1:8000', '/health': 'http://127.0.0.1:8000' } },
});
