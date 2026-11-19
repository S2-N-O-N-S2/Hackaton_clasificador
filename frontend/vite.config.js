import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Configuración de Vite. El puerto del panel es 5173; el del backend se define en src/config.js.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true, // permite abrir el panel desde un celular en la misma red
  },
});
