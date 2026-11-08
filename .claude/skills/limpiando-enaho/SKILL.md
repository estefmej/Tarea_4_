---
name: limpiando-enaho
description: Limpia y une los módulos 34 (sumaria) y 02 (miembros del hogar) de la ENAHO 2024 del INEI, filtra residentes habituales, calcula la pobreza monetaria ponderada (nacional, urbano/rural, sexo y departamento) y la valida contra las cifras oficiales. Úsala cuando pidan limpiar, unir, preparar o analizar la ENAHO, calcular la pobreza en el Perú por área, sexo, región o departamento, o cuando otra skill (gráfico o mapa de la ENAHO) necesite salidas/personas_2024.parquet.
argument-hint: "[año, por ahora solo 2024]"
---

# Limpiar la ENAHO 2024

Lo que no se discute (llaves, filtro, unión, ponderación y validación) está en
`scripts/limpiar.py`. Córrelo tal cual: no reescribas el pipeline en el chat.

## Pasos

1. Verifica que existan en `datos/` los zip `966-Modulo34.zip` y `966-Modulo02.zip`
   (966 = ENAHO 2024 en el portal del INEI). Si faltan, pide al usuario que los baje de:
   - https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/966-Modulo34.zip
   - https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/966-Modulo02.zip
2. Desde la raíz del proyecto corre exactamente:
   ```
   uv run python ${CLAUDE_SKILL_DIR}/scripts/limpiar.py --anio 2024
   ```
3. Lee `salidas/validacion.txt`. Si alguna línea dice `FALLIDA` o el script terminó con
   error, **detente**, muestra la línea y explica la causa. Nunca cambies filtros,
   factores ni tolerancias para que la cifra coincida.
4. Responde con los archivos generados:
   - `salidas/personas_2024.parquet`: una fila por residente habitual (no se sube a git).
   - `salidas/indicadores.csv`: pobreza y pobreza extrema ponderadas por grupo.
   - `salidas/validacion.txt`: verificaciones APROBADA/FALLIDA.
5. Para preguntas puntuales (p. ej. «¿pobreza en Cusco?») lee `salidas/indicadores.csv`
   o calcula desde el parquet **siempre ponderando con `facpob07`**
   (`numpy.average(pobre, weights=facpob07)`). Nunca promedios simples.
6. Antes de usar una variable que no esté en la base, o si dudas de una regla, lee
   [reference.md](reference.md).

## Reglas al responder

- Cita la fuente: «INEI, ENAHO 2024», e indica que es % de personas.
- Diferencia entre las dos ponderaciones: personas con `facpob07` (base de gráficos y
  mapas) y sumaria con `factor07 × mieperho` (método de las cifras oficiales por área).
- Las comparaciones entre grupos son descriptivas: no las presentes como causales.
