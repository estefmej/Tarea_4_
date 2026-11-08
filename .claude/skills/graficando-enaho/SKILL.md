---
name: graficando-enaho
description: Hace gráficos de barras de la pobreza monetaria o extrema en el Perú con la ENAHO 2024 del INEI, por área (urbano/rural), sexo, grupo de edad o departamento, con intervalos de confianza al 95 % del diseño muestral, el promedio nacional y un título con el hallazgo; guarda PNG en figuras/ y los datos en salidas/. Úsala cuando pidan graficar, visualizar o comparar en un gráfico la pobreza de la ENAHO por área, sexo, edad, niños, adultos mayores, región o departamento.
argument-hint: "[area | sexo | edad | departamento | todos] [pobreza | extrema]"
---

# Graficar la pobreza con la ENAHO 2024

**Si no existe `salidas/personas_2024.parquet`, usa primero la skill `limpiando-enaho`.**
Este script también necesita `salidas/hogares_2024.parquet`, que genera la misma skill.
No calcules la pobreza por tu cuenta ni leas los `.dta` directamente.

## Pasos

1. Verifica que existan `salidas/personas_2024.parquet` y `salidas/hogares_2024.parquet`. Si
   falta alguno, usa la skill `limpiando-enaho` y continúa solo si su `salidas/validacion.txt`
   no tiene `FALLIDA`.
2. Traduce el pedido al argumento `--por` con la tabla de abajo (si el usuario pasó
   argumentos, usa `$ARGUMENTS`). Corre desde la raíz del proyecto:
   ```
   uv run python ${CLAUDE_SKILL_DIR}/scripts/graficar.py --por <corte> --indicador <pobreza|extrema>
   ```
3. El script imprime la estimación, el IC 95 % y la muestra de cada categoría, y guarda:
   - `figuras/pobreza_<corte>_2024.png` (`pobreza_extrema_<corte>_2024.png` si es extrema)
   - `salidas/grafico_por_<corte>_2024.csv` (`grafico_por_<corte>_extrema_2024.csv`)
4. Abre el PNG y revisa que nada se encime. Responde con la ruta del PNG y las cifras que
   imprimió el script o que están en el CSV; no inventes ni redondees otras.

## Qué dice el usuario → `--por`

| El usuario dice… | `--por` | Método |
|---|---|---|
| área, urbano, rural, campo, ciudad | `area` | sumaria, `factor07 × mieperho` (n en hogares) |
| sexo, mujeres, hombres, género | `sexo` | personas, `facpob07` (n en personas) |
| edad, niños, niñas, menores, jóvenes, adultos, adultos mayores, tercera edad | `edad` | personas, `facpob07` (n en personas) |
| departamento, regiones, región, mapa en barras, Cusco, Lima… | `departamento` | sumaria, `factor07 × mieperho` (n en hogares) |
| todo, todos los gráficos | `todos` | — |
| pobreza extrema, indigencia | `--indicador extrema` | igual que arriba |

Grupos de edad: 0-17, 18-29, 30-44, 45-64 y 65+ (en ese orden, no por valor).

## Reglas de estilo (ya están en `scripts/graficar.py`; no las rompas si lo modificas)

- Fondo blanco, sin bordes superior ni derecho, grilla gris muy clara en el eje de valores,
  eje desde 0 con margen arriba. Eje de valores: «% de personas», sin cortes.
- Barras anchas de un solo color azul oscuro `#1F4E79`.
- Valor de cada barra en blanco y negrita dentro de la barra (cerca de la base en verticales,
  al final en horizontales); si la barra es muy corta, afuera en negro.
- IC 95 % como líneas grises con tope, por linealización de Taylor (UPM = `conglome`;
  estratos = departamento × estrato; ver `scripts/diseno.py`). Se dibujan recortados en 0.
- Línea discontinua roja `#C0392B` con el promedio nacional (mismo método que el gráfico) y
  leyenda «Promedio Perú: X %» arriba a la derecha (abajo a la derecha en departamentos).
- Título en negrita, a la izquierda, con el hallazgo y cifras calculadas por el script. Si los
  IC se superponen, el título dice que no hay diferencia estadísticamente clara.
- Subtítulo gris en dos líneas: grupo, periodo y unidad, y una «Lectura: …» generada según si
  los intervalos se superponen (o cuántos quedan sobre/bajo el promedio).
- Bajo cada categoría, su nombre y «(n = X hogares)» o «(n = X personas)».
- Departamentos: barras horizontales de mayor (arriba) a menor, nombres con tildes.
- Nota al pie gris con fuente, método e IC; en gráficos con personas agrega que la pobreza se
  mide por hogar.
- PNG a 200 dpi con `bbox_inches="tight"`.

## Al interpretar

- Superposición de IC es un criterio conservador; las diferencias son descriptivas, no causales.
- Área y departamento usan la sumaria (coinciden con las cifras oficiales); sexo y edad usan
  personas. Por eso el «Promedio Perú» difiere en décimas entre gráficos. Ambas cifras
  nacionales están en `salidas/validacion.txt`.
