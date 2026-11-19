# training

Fase 4: captura del dataset, entrenamiento y evaluación. Explicación técnica en [`docs/memoria_tecnica.md`](../../docs/memoria_tecnica.md), sección 3.

Todos los comandos se corren **desde `backend/`** con el entorno virtual activo:
```powershell
cd backend; .\.venv\Scripts\Activate.ps1
```

## 1. Capturar fotos (con la cámara, bandeja e iluminación de la demo)
```powershell
python -m training.capturar_dataset
```
- En la consola escribe el ID del objeto físico (por ejemplo `platano1`).
- En la ventana, presiona **1 / 2 / 3** para guardar una foto en Orgánica / Inorgánica / Peligroso. Cambia posición, orientación y lado entre fotos.
- Presiona **N** para pasar a otro objeto y **Q** para salir.
- Cámara distinta: `--camara 1`. Celular por Wi-Fi: `--camara http://IP:4747/video`.
- **Meta:** 40–60 fotos por clase, de **al menos 4–5 objetos distintos por clase** (mínimo 2 para poder separar entrenamiento y validación).

## 2. Entrenar
```powershell
python -m training.train
```
Opciones: `--cabeza densa` (Keras), `--aumentar` (aumento de datos), `--activar siempre`.
Si todo funciona, se ve la precisión de VALIDACIÓN, la matriz de confusión y si la versión quedó activada.

## 3. Evaluar
```powershell
python -m training.evaluate
```
Deja en `models/v<N>/evaluacion/` la imagen `matriz_confusion.png`, `resultados.md` y la carpeta `fallidos/` con las fotos que falló.
Con fotos propias: `--carpeta ruta\fotos`, que debe tener subcarpetas `organica/`, `inorganica/` y `peligroso/`.

## 4. Usarlo en el sistema
El backend en modo real (`SIMULACION=0`) carga solo la versión **activa**. Para reentrenar desde el panel: `POST /api/modelo/reentrenar`.
