# Guía: cámara del celular + dataset con fotos reales (paso a paso)

> **Antes de empezar:** la cámara con la que capturen el dataset debe ser **la misma** de la demo, en la **misma posición**, con la **misma bandeja y la misma luz** (especificación §14.1). Si después la mueven o la cambian, hay que volver a capturar fotos.

Todos los comandos se escriben en PowerShell, desde la carpeta `backend`, con el entorno virtual activo:
```powershell
cd C:\Users\SrAno\Desktop\clasificador\backend; .\.venv\Scripts\Activate.ps1
```

---

## Parte A — Conectar la cámara del celular

### Paso A0. Elegir la app
Recomendamos **DroidCam** porque convierte el celular en una "webcam" de Windows y nuestro código la abre sin cambios.

| Qué | Dónde | Notas |
|---|---|---|
| App en el celular | **Android:** Play Store → "DroidCam" (Dev47Apps). **iPhone:** App Store → "DroidCam" | Gratis. La versión gratuita da 640×480, suficiente (la IA usa 224×224) |
| Programa en la laptop | **DroidCam Client** para Windows, del sitio oficial de Dev47Apps | Descárguenlo **ustedes** con buena red antes del evento y decláralo en `docs/recursos_externos.md` |

### Paso A1. Conectar por **USB** (recomendado: no depende del Wi-Fi del evento)

**Android:**
1. En el celular, ve a **Ajustes → Acerca del teléfono** y toca **7 veces** "Número de compilación". Así se activan las "Opciones de desarrollador".
2. Ve a **Ajustes → Sistema → Opciones de desarrollador** y activa **Depuración USB**.
3. Conecta el celular a la laptop con un cable USB **de datos**. Algunos cables solo cargan.
4. Cuando el celular pregunte **"¿Permitir depuración USB?"**, acepta y marca "Permitir siempre".
5. Abre la app DroidCam en el celular.
6. Abre **DroidCam Client** en la laptop, elige el ícono **USB** y presiona **Start**. Debe aparecer la imagen.

**iPhone:**
1. Instala **iTunes** o la app **Dispositivos Apple** en la laptop (los necesita el USB del iPhone).
2. Conecta el iPhone, acepta **"Confiar en esta computadora"** y abre la app DroidCam.
3. En DroidCam Client, elige **USB** (iOS) y presiona **Start**.

> **Deja DroidCam Client abierto** mientras uses la cámara: es lo que alimenta la "webcam virtual". Cierra Zoom, Teams y la app Cámara de Windows, porque la cámara solo la puede usar un programa a la vez.

### Paso A2. (Alternativa) Conectar por **Wi-Fi** con una URL
Úsenla solo si el USB no funciona. La laptop y el celular deben estar en la **misma red**.
1. Abre la app DroidCam en el celular. Muestra algo como **"WiFi IP: 192.168.1.50"** y **"Port: 4747"**.
2. **No abras** DroidCam Client: la app acepta una sola conexión a la vez.
3. La "cámara" para nuestros programas es la URL `http://192.168.1.50:4747/video` (con la IP de **tu** celular). Prueba que se ve:
   ```powershell
   python -m training.capturar_dataset --camara http://192.168.1.50:4747/video
   ```

**Plan B sin DroidCam (Android + Windows 11):** "Enlace Móvil" (Phone Link) → usar el celular como **cámara conectada**. Después corran el Paso A3 para ver si OpenCV la detecta.

### Paso A3. Averiguar qué número (índice) le tocó a la cámara
Con DroidCam funcionando:
```powershell
python tools\verificar_hardware.py
```
En la sección "Cámaras" debe aparecer una cámara más que antes, por ejemplo `índice 1: 640x480`. Si sale el aviso **"la imagen es de un solo color"**, la cámara existe pero DroidCam no está transmitiendo: dale **Start** en DroidCam Client. Abre las fotos `captures\prueba_camara_0.jpg`, `prueba_camara_1.jpg`… y fíjate cuál muestra la bandeja vista desde el celular.

### Paso A4. Guardar ese índice en la configuración
```powershell
python tools\configurar.py indice_camara 1
```
(o la URL: `python tools\configurar.py indice_camara http://192.168.1.50:4747/video`).
Para ver toda la configuración: `python tools\configurar.py --ver`.

> El índice **puede cambiar** si desconectan el celular o conectan otra cámara. Antes de cada sesión, repitan el Paso A3.

### Paso A5. Dejar el celular fijo y estable
- Montado en el **soporte cenital**, siempre a la misma altura, mirando hacia abajo y sin rotación.
- **Cargando** (el mismo USB carga), con la **pantalla siempre encendida** y en modo **No molestar**, para que ninguna notificación tape la imagen.
- Si la app lo permite, **fija el enfoque y la exposición** tocando la pantalla sobre la bandeja. Los cambios automáticos de brillo confunden a la IA.
- Desactiva la rotación automática de pantalla.

---

## Parte B — Dataset con fotos reales (paso a paso)

### Paso B0. Revisar lo físico
- [ ] Torre armada, con la bandeja y su **fondo liso** de un solo color.
- [ ] **Iluminación blanca** encendida y paredes que tapan la luz ambiente.
- [ ] Celular en su posición **definitiva** (Parte A).
- [ ] Objetos reunidos y **limpios**. Los "peligrosos" son **simulados**: pila descargada, envase vacío de medicamento, blíster vacío.

### Paso B1. Ajustar la zona de interés (ROI)
La IA solo mira lo que está dentro del **rectángulo verde**, que debe cubrir el **interior de la bandeja** con un poco de margen.
1. Abre la vista de captura y observa el rectángulo:
   ```powershell
   python -m training.capturar_dataset
   ```
   Escribe cualquier ID (por ejemplo `prueba`), mira la ventana y presiona **Q** para salir sin guardar.
2. Si el rectángulo no coincide con la bandeja, ajústalo. Son 4 números **[x, y, ancho, alto]** en fracciones de la imagen (0 = borde izquierdo o superior, 1 = borde derecho o inferior). Por ejemplo, para quitar un 20 % a la izquierda y un 10 % arriba, con 60 % de ancho y 80 % de alto:
   ```powershell
   python tools\configurar.py roi "[0.2, 0.1, 0.6, 0.8]"
   ```
3. Repite hasta que coincida. **Fíjenlo antes de tomar las fotos del dataset.** Cada modelo guarda la ROI con la que se entrenó; si la cambian después, hay que reentrenar.

### Paso B2. Planear qué fotografiar
La meta es **40–60 fotos por clase**, tomadas de **varios objetos distintos**. Vale más tener muchos objetos distintos que muchas fotos del mismo.

| Clase | Objetos sugeridos (5–6 por clase) | Fotos por objeto |
|---|---|---|
| Orgánica (tecla 1) | cáscara de plátano, restos de manzana, cáscara de naranja, cáscara de huevo, servilleta con comida | 8–10 |
| Inorgánica (tecla 2) | botella PET, lata, cartón, papel, envoltura, unicel | 8–10 |
| Peligroso (tecla 3) | pila descargada (2 tamaños), envase vacío de medicamento, blíster vacío, cubrebocas | 8–10 |

- Den a cada objeto un **ID único** y anótenlo: `platano1`, `platano2`, `lata1`, `pila_aa1`…
- **Mínimo absoluto: 2 objetos distintos por clase.** Sin eso, el entrenamiento no arranca, porque no puede separar entrenamiento y validación.
- **Los 20 residuos de la prueba oficial**, de preferencia, **no** se fotografían para el dataset. Si alguno se usa, anótenlo con `usado_en_entrenamiento` al registrarlo en el panel (Pruebas).
- **No fotografíen el objeto "dudoso"** de la demo (momento 3). Debe ser algo que la IA nunca haya visto.

### Paso B3. Tomar las fotos
```powershell
python -m training.capturar_dataset
```
1. En la **consola**, escribe el ID del primer objeto (por ejemplo `platano1`) y presiona Enter.
2. Pon el objeto en la bandeja y, **con la ventana de video seleccionada**, presiona la tecla de su clase: **1** Orgánica, **2** Inorgánica o **3** Peligroso. Cada vez que presionas, se guarda **una foto**.
3. Entre foto y foto, **mueve el objeto**: otra posición dentro de la bandeja, otra orientación y el otro lado, y si se puede, arrugado o doblado. Toma de 8 a 10 fotos así.
4. Presiona **N**, escribe el ID del siguiente objeto en la consola y repite.
5. Al terminar, presiona **Q**. La consola muestra el resumen: cuántas fotos y cuántos objetos hay por clase.

**Para que las fotos sirvan:**
- No dejes la **mano** en la foto: suelta el objeto y aléjate antes de presionar la tecla.
- Una foto movida o borrosa es mejor no tomarla.
- No cambies la luz ni muevas el celular a mitad de la sesión.
- Fotografía **un objeto a la vez**.

Las fotos quedan en `backend\dataset\organica\`, `inorganica\` y `peligroso\`, con nombres como `platano1__20261119_141500_3.jpg`. Cada una se anota en `dataset\metadatos.csv`.

### Paso B4. Revisar las fotos
Abre las carpetas de `backend\dataset\` en el Explorador de Windows y **borra** las fotos malas: borrosas, con la mano, con el objeto fuera de la bandeja o en la clase equivocada. No hace falta editar el CSV.

### Paso B5. Entrenar
```powershell
python -m training.train
```
Qué debe verse:
- Cuántas **fotos y objetos** hay por clase.
- **"Precisión VALIDACIÓN"**: se mide con objetos que el modelo **no vio**. Es el número honesto.
- La **matriz de confusión**: la diagonal son los aciertos; lo que está fuera de la diagonal son las confusiones (fila = real, columna = lo que dijo la IA).
- **"Activado: …"**: el backend usará esta versión.

Si dice *"NO SE PUDO ENTRENAR: Cada clase necesita fotos de al menos 2 objetos distintos…"*, falta fotografiar más objetos de la clase que indica.

### Paso B6. Evaluar
```powershell
python -m training.evaluate
```
Abre:
- `backend\models\v1\evaluacion\matriz_confusion.png`: la imagen de la matriz, para la memoria técnica y la defensa.
- `backend\models\v1\evaluacion\fallidos\`: las fotos que falló, con su clase real y lo que dijo la IA en el nombre.
- La sección **"Con los umbrales actuales"**: cuántas fotos irían a REVISIÓN y la precisión de las que el sistema sí acepta.

### Paso B7. Probar en vivo con la cámara (todavía sin Arduino)
```powershell
python tools\probar_modelo_vivo.py
```
- Pon un objeto y presiona **ESPACIO**: se ve la categoría, la confianza y las 3 probabilidades, igual que las calculará el sistema real. **C** activa la clasificación continua.
- Pruébalo con objetos que **no** usaste para entrenar. Con el objeto "dudoso" debería salir **REVISION**.

### Paso B8. Mejorar si se equivoca
1. Mira qué confunde en la matriz o en `fallidos\`.
2. Toma fotos de **más objetos** de esas clases (Paso B3) y borra las fotos malas.
3. Entrena otra vez (Paso B5). Solo se procesan las fotos nuevas, así que tarda segundos. La versión nueva (`v2`, `v3`…) **solo se activa si no empeora**.
   - Si el dataset cambió mucho, las precisiones no son del todo comparables, porque se validó con objetos distintos. En ese caso pueden forzar la nueva con `python -m training.train --activar siempre`, después de revisarla con `evaluate`.
4. Si casi todo va a REVISIÓN aunque acierte, el umbral puede estar alto. Se ajusta con `python tools\configurar.py umbral_general 0.55`, pero decídanlo con los datos de `evaluate` y anoten el motivo.

### Paso B9. Registrar los resultados reales
- Copia la precisión de validación, el número de fotos y objetos y la matriz a `docs/memoria_tecnica.md`, sección 3.5.
- Agrega una fila a `docs/bitacora.md` con la hora, la versión y el resultado.
- **Nunca** reporten la prueba con imágenes sintéticas ni números que no salieron de `train` o `evaluate`.

---

## Problemas comunes

| Problema | Causa probable | Solución |
|---|---|---|
| `verificar_hardware.py` no muestra la cámara nueva | DroidCam Client cerrado, o la versión de código anterior (solo buscaba con DirectShow; DroidCam 7 solo se ve con Media Foundation) | Actualicen el código (ya usa MSMF), abran DroidCam Client y repitan |
| La cámara de DroidCam aparece pero la foto es **verde lisa** (aviso "imagen de un solo color") | DroidCam no está transmitiendo: es su pantalla de espera | Abre la app en el celular (pantalla principal), en DroidCam Client elige **USB** y presiona **Start**; repite `verificar_hardware.py` |
| DroidCam Client dice que no encuentra el dispositivo o da error de ADB | Choque entre el `adb` de Android Studio y el que trae DroidCam | Cierra Android Studio, corre `adb kill-server` (o reinicia la laptop) y presiona Start otra vez |
| La cámara se abre pero la imagen sale negra | Otro programa la está usando | Cierra Zoom, Teams y la app Cámara |
| "No se pudo abrir la cámara 1" | El índice cambió | Repite los pasos A3 y A4 |
| La imagen se congela por Wi-Fi | La red del evento es lenta | Usa USB (Paso A1) |
| El celular no pide "Permitir depuración USB" | El cable solo carga | Cambia de cable o de puerto USB |
| Precisión de validación baja | Pocos objetos, luz cambiante o ROI mal puesta | Más objetos por clase; revisa la luz y el Paso B1 |
| Entrena bien pero en vivo falla | Movieron la cámara o cambió la luz | Vuelvan a la posición original o recapturen |
