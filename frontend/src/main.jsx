import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { ProveedorEstado } from './estado.jsx';
import App from './App.jsx';
import './estilos.css';

createRoot(document.getElementById('raiz')).render(
  <StrictMode>
    <ProveedorEstado>
      <App />
    </ProveedorEstado>
  </StrictMode>,
);
