# Evaluación del modelo v1

- Fotos evaluadas: **300**
- Precisión total: **98.0%** (294/300)

| Clase | Aciertos | Total | Acierto |
|---|---|---|---|
| organica | 100 | 100 | 100% |
| inorganica | 96 | 100 | 96% |
| peligroso | 98 | 100 | 98% |

## Matriz de confusión (filas = real, columnas = predicción)

```
real \ pred    Org  Inorg    Pel
        Org    100      0      0
      Inorg      2     96      2
        Pel      0      2     98
```

## Con los umbrales actuales (0.60 / 0.35)

- Irían a REVISIÓN: 4 (1%)
- Precisión de las aceptadas: 98.7%
- Peligrosos aceptados en un bote equivocado: 0

Casos fallidos copiados en `C:\Users\alan6\clasificador\backend\models\v1\evaluacion\fallidos`.