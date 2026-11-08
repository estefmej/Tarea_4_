# Referencia: variables y reglas de la ENAHO 2024

## Archivos

| Módulo | Archivo | Una fila por | Filas | Llaves | Factor |
|---|---|---|---|---|---|
| 34 Sumaria | `966-Modulo34/sumaria-2024.dta` | hogar | 33,691 | `conglome`, `vivienda`, `hogar` | `factor07` |
| 02 Miembros | `966-Modulo02/enaho01-2024-200.dta` | persona | 117,721 | las tres + `codperso` | `facpob07` |

El zip del módulo 34 también trae `sumaria-2024-12g.dta` (gasto en 12 grupos); no se usa.

## Diccionario de variables usadas

| Variable | Módulo | Descripción | Valores / tipo |
|---|---|---|---|
| `año` | ambos | Año de la encuesta (llega como `aÑo`; se normaliza) | texto |
| `mes` | ambos | Mes de la entrevista | texto |
| `conglome` | ambos | Conglomerado | texto, 6 dígitos con ceros |
| `vivienda` | ambos | Vivienda dentro del conglomerado | texto, 3 dígitos |
| `hogar` | ambos | Hogar dentro de la vivienda | texto, 2 dígitos |
| `codperso` | 02 | Número de orden de la persona | texto, 2 dígitos |
| `ubigeo` | ambos | Ubicación geográfica (departamento-provincia-distrito) | texto, 6 dígitos con ceros |
| `dominio` | ambos | Dominio geográfico (8 = Lima Metropolitana) | 1-8 |
| `estrato` | ambos | Estrato geográfico por tamaño de centro poblado | 1-5 urbano, 6-8 rural |
| `p204` | 02 | ¿Es miembro del hogar? | 1 sí, 2 no |
| `p205` | 02 | ¿Se encuentra ausente del hogar 30 días o más? | 1 sí, 2 no |
| `p206` | 02 | ¿Está presente en el hogar 30 días o más? (no miembros) | 1 sí, 2 no |
| `p207` | 02 | Sexo | 1 hombre, 2 mujer |
| `p208a` | 02 | Edad en años cumplidos | número |
| `facpob07` | 02 | Factor de expansión poblacional (proyecciones del Censo 2007) | número |
| `pobreza` | 34 | Pobreza monetaria del hogar | 1 pobre extremo, 2 pobre no extremo, 3 no pobre |
| `factor07` | 34 | Factor de expansión del hogar | número |
| `mieperho` | 34 | Miembros del hogar (sin trabajadores del hogar ni pensionistas) | número |
| `linea`, `linpe` | 34 | Línea de pobreza total y extrema (S/ por persona al mes) | número |

## Variables construidas

| Variable | Regla |
|---|---|
| `departamento` | `ubigeo[:2]` como texto ("01"…"25"); Lima = "15", Callao = "07" |
| `area` | `"urbano"` si `estrato <= 5`, si no `"rural"` |
| `pobre` | `pobreza <= 2` (incluye pobres extremos) |
| `pobre_extremo` | `pobreza == 1` |
| `sexo` | `p207`: 1 → `"hombre"`, 2 → `"mujer"` |

## Reglas metodológicas

1. **Leer** con `pd.read_stata(..., convert_categoricals=False)`. Las llaves (`conglome`,
   `vivienda`, `hogar`, `codperso`, `ubigeo`) siempre como texto: si se vuelven número
   se pierden los ceros y `ubigeo[:2]` deja de ser el departamento.
2. **Columnas en minúscula**; la del año pasa a `año`.
3. **Residentes habituales:** `((p204 == 1) & (p205 == 2)) | ((p204 == 2) & (p206 == 1))`.
   Miembros que no están ausentes 30 días o más, más no miembros presentes 30 días o más.
   Deja 108,664 de 117,721 filas.
4. **Unir** personas con la sumaria por `conglome`, `vivienda`, `hogar` con
   `merge(..., how="left", validate="m:1")`; verificar que ninguna persona quede sin
   hogar y que no se dupliquen filas.
5. **Ponderar siempre.** Nunca promedio simple:
   - Personas: `np.average(pobre, weights=facpob07)`.
   - Hogares de la sumaria, en términos de personas: peso `factor07 × mieperho`.
6. **Dos ponderaciones, dos cifras.** Con personas/`facpob07` la pobreza 2024 es 27.53 %;
   con sumaria/`factor07 × mieperho`, 27.58 % (la oficial redondeada es 27.6 %). La
   diferencia existe porque en ~5.5 % de los hogares los residentes habituales no
   coinciden con `mieperho`. Las cifras oficiales por área (24.8 % / 39.3 %) usan la
   sumaria; por eso la validación de área compara con ese método.
7. **Validar sin ajustar.** Tolerancia 0.1 pp. Si falla una validación esencial, el script
   termina con error y no guarda la base.
8. **No causalidad.** Diferencias entre áreas, sexos o departamentos son asociaciones
   descriptivas.

## Cifras de referencia (ENAHO 2024)

| Cifra | Valor | Método |
|---|---|---|
| Pobreza monetaria nacional | 27.6 % | oficial INEI |
| Residentes habituales | 108,664 | filtro de la regla 3 |
| Urbano / rural | 24.8 % / 39.3 % | sumaria, `factor07 × mieperho` |
| Por departamento | `datos/pobreza_departamento_2024.csv` | referencia de la Sesión 16 del curso, calculada con ENAHO 2024 del INEI |
