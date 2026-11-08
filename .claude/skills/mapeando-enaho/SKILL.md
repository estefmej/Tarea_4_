---
name: mapeando-enaho
description: Hace un mapa coroplético de la pobreza monetaria por departamento del Perú con la ENAHO 2024 del INEI, uniendo por código de ubigeo (25 departamentos, Lima y Callao separados), y compara cada departamento con la referencia del curso. Úsala cuando pidan un mapa, mapear o ver geográficamente la pobreza por departamento o región con la ENAHO.
argument-hint: "[sin argumentos]"
---

# Mapear la pobreza por departamento con la ENAHO 2024

**Si no existe `salidas/personas_2024.parquet`, usa primero la skill `limpiando-enaho`.**
No calcules la pobreza por tu cuenta ni leas los `.dta` directamente.

## Pasos

1. Verifica que existan `salidas/personas_2024.parquet` y `salidas/hogares_2024.parquet`. Si
   falta alguno, usa la skill `limpiando-enaho` y continúa solo si su `salidas/validacion.txt`
   no tiene `FALLIDA`.
2. Verifica que existan en `datos/`:
   - `peru_departamental_simple.geojson` (límites; descarga:
     https://raw.githubusercontent.com/d2cml-ai/Data-Science-Python/main/sessions/06-geoespacial/lab/Data/peru_departamental_simple.geojson)
   - `pobreza_departamento_2024.csv` (referencia de la Sesión 16 del curso, calculada con
     ENAHO 2024 del INEI; descarga:
     https://raw.githubusercontent.com/d2cml-ai/Data-Science-Python/main/sessions/16-skills-enaho/referencias/pobreza_departamento_2024.csv)
3. Corre desde la raíz del proyecto:
   ```
   uv run python ${CLAUDE_SKILL_DIR}/scripts/mapear.py
   ```
4. Si el script termina con `ERROR`, detente y explica la causa. No cambies la unión ni
   las tolerancias para que pase.
5. Abre `mapas/pobreza_departamento_2024.png` y revisa que se lea bien. Responde con la
   ruta del mapa, el resumen de diferencias que imprimió el script y la ruta de
   `salidas/comparacion_mapa.csv`.

## Reglas del mapa (ya están en el script)

- Une `ubigeo[:2]` con `FIRST_IDDP`, ambos como texto. **Nunca por nombre**
  («APURIMAC» no es «Apurímac»).
- Exige 25 departamentos con dato; Lima (15) y Callao (07) van separados.
- Pondera con la sumaria de hogares, `factor07 × mieperho` (el mismo método del gráfico de
  departamentos de `graficando-enaho` y de la referencia del curso); nunca promedio simple.
- Escala secuencial `Blues`, de claro a oscuro, desde 0; nunca arcoíris.
- Leyenda con la unidad «% de personas» y nota «Fuente: INEI, ENAHO 2024 (módulos 34 y 02)…».

## Comparación con la referencia

`salidas/comparacion_mapa.csv` trae, por departamento, el valor del mapa (sumaria,
`factor07 × mieperho`), la referencia del curso, la diferencia (debe ser ≤0.1 pp) y, solo
como contraste, la cifra con personas y `facpob07`. El script además comprueba que el mapa
coincida con `salidas/indicadores.csv` y con `salidas/grafico_por_departamento_2024.csv`.
Cita las cifras desde ese CSV y no las presentes como causales.
