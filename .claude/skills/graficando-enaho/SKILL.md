---
name: graficando-enaho
description: Hace gráficos de barras de la pobreza monetaria en el Perú con la ENAHO 2024 del INEI, por área (urbano/rural), sexo o departamento, ponderados con facpob07 y guardados como PNG en figuras/. Úsala cuando pidan graficar, visualizar o comparar en un gráfico la pobreza de la ENAHO por área, sexo, región o departamento.
argument-hint: "[area | sexo | departamento | todos]"
---

# Graficar la pobreza con la ENAHO 2024

**Si no existe `salidas/personas_2024.parquet`, usa primero la skill `limpiando-enaho`.**
No calcules la pobreza por tu cuenta ni leas los `.dta` directamente.

## Pasos

1. Verifica que exista `salidas/personas_2024.parquet`. Si no existe, usa la skill
   `limpiando-enaho` y continúa solo si su `salidas/validacion.txt` no tiene `FALLIDA`.
2. Elige el grupo según el pedido: `area`, `sexo`, `departamento` o `todos`
   (si el usuario pasó un argumento, usa `$ARGUMENTS`). Corre desde la raíz del proyecto:
   ```
   uv run python ${CLAUDE_SKILL_DIR}/scripts/graficar.py --por <grupo>
   ```
3. El script imprime los valores graficados y guarda `figuras/pobreza_<grupo>_2024.png`.
   Abre el PNG y revisa que el título, los valores y la fuente se lean bien.
4. Responde con la ruta del PNG y las cifras que imprimió el script (no las redondees
   a mano ni inventes otras).

## Reglas del gráfico (ya están en el script; no las rompas si lo modificas)

- Pondera siempre con `facpob07`; nunca promedios simples.
- Barras horizontales que empiezan en cero, ordenadas de mayor a menor.
- Un solo color (`#2a78d6`) y el valor escrito en cada barra.
- Título analítico construido con los datos y con el periodo (2024).
- Unidad en el eje: «% de personas».
- Nota al pie: «Fuente: INEI, ENAHO 2024».
- PNG a 200 dpi en `figuras/`.

## Al interpretar

- Las diferencias son descriptivas: no digas que el área o el sexo *causan* la pobreza.
- La pobreza por área con personas y `facpob07` difiere en décimas de la cifra oficial,
  que usa la sumaria con `factor07 × mieperho`. Ambas cifras y la causa están en las
  líneas `[INFORMATIVA]` de `salidas/validacion.txt`; cítalas de ahí.
