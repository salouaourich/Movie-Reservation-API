import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Use 127.0.0.1 (IPv4) explicitly. Docker Desktop on Windows binds
      // its port relay on both ::1 and 0.0.0.0; when the IPv6 relay
      // (wslrelay.exe) stalls, requests to "localhost" resolve to ::1
      // first and hang. 127.0.0.1 forces IPv4 and bypasses the bug.
      '/api': 'http://127.0.0.1:8000',
    },
  },
});
