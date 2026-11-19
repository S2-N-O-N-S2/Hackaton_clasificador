# sim_images

Imágenes para el **modo simulación** (`SIMULACION=1`), cuando no hay cámara. Todo lo generado con ellas se marca como **SIMULADO**.

Opcional: pongan fotos en subcarpetas `organica/`, `inorganica/`, `peligroso/` y `dudoso/`. `POST /api/sim/objeto {"categoria_real": 1}` elige una foto de `inorganica/`. Si una carpeta está vacía, el backend dibuja una imagen sintética rotulada "SIMULADO #n".
