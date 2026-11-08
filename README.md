# Tarea 4 – Agente de investigación socioeconómica del Perú

Referencia oficial: <https://github.com/d2cml-ai/Data-Science-Python/issues/201>

## Pregunta de investigación

> ¿Cómo fue la pobreza monetaria en el Perú en 2024 por área y departamento, y en qué contexto
> macroeconómico (inflación, tipo de cambio, actividad económica) ocurrió?

El agente responde con datos oficiales y verificables, la **ENAHO 2024** del INEI y las **series del BCRP**,
usando herramientas que procesan los datos en Python y citan su fuente. No responde de memoria.

## Las 4 partes

| Parte | Qué hace | Carpeta | Estado |
|---|---|---|---|
| 1. Servidor MCP del BCRP | Datos macroeconómicos: inflación, tipo de cambio, PBI… | `mcp/` | ✅ |
| 2. Skills de ENAHO | Pobreza por área, sexo y departamento: limpieza, gráficos y mapa | `.claude/skills/` | ✅ |
| 3. Integración | El agente combina ambas fuentes para responder | `integracion/` | pendiente |
| 4. Evaluación y reproducibilidad | Evaluación, documentación y evidencias | `evaluacion/`, `evidencias_ia/` | pendiente |

## Parte 1 · Servidor MCP del BCRP (`mcp/server.py`)

Usa la API pública del BCRP (<https://estadisticas.bcrp.gob.pe/estadisticas/series/api>), que no pide clave.
El catálogo de series (~17 mil) se descarga la primera vez a `mcp/datos/`, que no se sube al repositorio.

### Herramientas

| Herramienta | Qué hace |
|---|---|
| `buscar_series(texto, frecuencia, limite)` | Busca códigos de serie por palabras (p. ej. "ipc 12 meses"). |
| `serie(codigo, desde, hasta)` | Datos de la serie con periodos normalizados, valores `n.d.` omitidos y `fuente` = URL consultada. |
| `resumen(codigo, desde, hasta)` | Primero, último, cambio, variación %, promedio, máximo y mínimo con su periodo (pandas). |
| `correlacion(codigo_a, codigo_b, desde, hasta)` | **Herramienta propia.** Correlación de Pearson entre dos series de la misma frecuencia: alinea periodos, descarta faltantes, exige ≥ 3 periodos y devuelve coeficiente, n, periodos, descartados, fuentes y una nota de que es una asociación descriptiva, no causal. |

### Recurso y prompt

- **Recurso** `bcrp://serie/{codigo}`: ficha descriptiva de la serie (nombre, categoría, frecuencia, inicio,
  última actualización y enlace de la API).
- **Prompt** `informe(tema)`: pide un informe en el que cada cifra cite **código, periodo y fuente**, use solo
  las herramientas y no presente asociaciones como causales.

### Parseo de fechas

La API usa un formato para lo que se le **pide** y otro para lo que **devuelve**, así que hay dos funciones:

- `_periodo_api(periodo, frecuencia, fin)` traduce lo que escribe el usuario (`2025`, `2025-03`,
  `2025-03-15`, `2025-T1`) al formato que pide la API según la frecuencia de la serie: diaria `2025-03-15`,
  mensual `2025-3`, trimestral `2025-1`, anual `2025`.
- `_normalizar_periodo(nombre)` traduce lo que devuelve la API a un formato estándar y ordenable:

| La API devuelve | Normalizado |
|---|---|
| `Ene.2025` | `2025-01` |
| `Set.2025` / `Sep.2025` | `2025-09` |
| `01.Oct.26` | `2026-10-01` |
| `T1.25` | `2025-T1` |
| `2025` | `2025` |

Los meses se leen de un diccionario propio en español (incluye `Set` y `Sep`), así el resultado no depende
del idioma (locale) de la computadora. Los años de dos dígitos siguen el corte de Python: `00–68` → 20xx y
`69–99` → 19xx.

## Instalación

Requiere [uv](https://docs.astral.sh/uv/).

```powershell
uv sync
```

## Pruebas

```powershell
uv run pytest -v
```

Son 10 pruebas: las 8 originales de la Sesión 04 (`mcp/test_server.py`, sin modificar) y 2 propias
(`mcp/test_propia.py`). Consultan la API real del BCRP, así que necesitan internet. La última salida está en
`salidas/pruebas_mcp.txt`.

## Conectar el servidor a Claude Code

El repositorio ya incluye `.mcp.json`. Si hiciera falta registrarlo de nuevo:

```powershell
claude mcp add --scope project bcrp -- uv run mcp/server.py
```

Al abrir `claude` en esta carpeta, apruebe el servidor `bcrp`. Luego:

- `/mcp` → `bcrp` debe aparecer conectado con 4 herramientas.
- `@bcrp:bcrp://serie/PN01273PM` → adjunta la ficha de la serie.
- `/bcrp:informe` (o `/mcp__bcrp__informe`) → prompt de informe con citas.

## Parte 2 · Skills para procesar y analizar la ENAHO (`.claude/skills/`)

Metodología: [Sesión 16 del curso](https://github.com/d2cml-ai/Data-Science-Python/tree/main/sessions/16-skills-enaho).
Tres skills de Claude Code que se versionan con el repositorio. Cada una corre un script fijo, así el
resultado es el mismo cada vez.

| Skill | Qué hace | Entra | Sale |
|---|---|---|---|
| `limpiando-enaho` | Lee los módulos 34 y 02, filtra residentes habituales, une con `validate="m:1"`, construye departamento, área, sexo y pobreza; pondera y valida | `datos/966-Modulo34.zip`, `datos/966-Modulo02.zip` | `salidas/personas_2024.parquet` y `salidas/hogares_2024.parquet` (no se suben), `salidas/indicadores.csv`, `salidas/validacion.txt` |
| `graficando-enaho` | Barras de pobreza (o pobreza extrema) por área, sexo, edad y departamento, con IC 95 % del diseño muestral y el promedio nacional | los dos parquet | `figuras/pobreza_{area,sexo,edad,departamento}_2024.png`, `salidas/grafico_por_<corte>_2024.csv` |
| `mapeando-enaho` | Mapa coroplético por departamento unido por código (`ubigeo[:2]` = `FIRST_IDDP`) y comparación con la referencia | el parquet, el GeoJSON y el CSV de referencia | `mapas/pobreza_departamento_2024.png`, `salidas/comparacion_mapa.csv` |

`graficando-enaho` y `mapeando-enaho` dicen: «Si no existe `salidas/personas_2024.parquet`, usa primero
la skill `limpiando-enaho`». Así un solo pedido (por ejemplo, «Haz un mapa de la pobreza monetaria por
departamento con ENAHO 2024») activa dos skills seguidas.

### Ponderación

Toda cifra está ponderada; nunca se usan promedios simples. La base de personas usa `facpob07`, el factor
de expansión de cada persona. Como contraste, la sumaria usa `factor07 × mieperho`, porque cada hogar
representa a tantas personas como su factor por el número de miembros. Las cifras oficiales por área y la
referencia por departamento usan la sumaria, así que cada cifra se valida contra la referencia calculada
con el mismo método. Las dos ponderaciones difieren en décimas porque en algunos hogares los residentes
habituales no coinciden con `mieperho`; el detalle está en `salidas/validacion.txt`.

### Descargar los datos

Los datos van en `datos/`, que no se sube al repositorio (tampoco los `.zip`, los `.dta` ni el parquet).

```powershell
New-Item -ItemType Directory -Force datos, figuras, mapas | Out-Null
$base = "https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA"
Invoke-WebRequest "$base/966-Modulo34.zip" -OutFile datos/966-Modulo34.zip
Invoke-WebRequest "$base/966-Modulo02.zip" -OutFile datos/966-Modulo02.zip
$curso = "https://raw.githubusercontent.com/d2cml-ai/Data-Science-Python/main/sessions"
Invoke-WebRequest "$curso/06-geoespacial/lab/Data/peru_departamental_simple.geojson" -OutFile datos/peru_departamental_simple.geojson
Invoke-WebRequest "$curso/16-skills-enaho/referencias/pobreza_departamento_2024.csv" -OutFile datos/pobreza_departamento_2024.csv
```

`966` es el código de la ENAHO 2024 en el portal del INEI. Si el servidor del INEI no responde, baje los
dos zip con el navegador. `pobreza_departamento_2024.csv` es la referencia de la Sesión 16 del curso,
calculada con ENAHO 2024 del INEI; no es un archivo publicado por el INEI.

### Ejecutar

Dentro de Claude Code: `/limpiando-enaho`, `/graficando-enaho todos` y `/mapeando-enaho`, o un pedido en
lenguaje natural. Sin Claude Code, desde la raíz del proyecto:

```powershell
uv run python .claude/skills/limpiando-enaho/scripts/limpiar.py --anio 2024
uv run python .claude/skills/graficando-enaho/scripts/graficar.py --por todos   # --indicador extrema: pobreza extrema
uv run python .claude/skills/mapeando-enaho/scripts/mapear.py
uv run python scripts/actualizar_readme.py   # actualiza las cifras de abajo
```

Si una validación esencial falla, `limpiar.py` termina con error y no guarda la base. Nunca se ajustan
resultados para que coincidan.

### Cifras de validación

<!-- validacion:inicio -->
<!-- Generado por scripts/actualizar_readme.py; no editar a mano. -->

Contenido de `salidas/validacion.txt`:

```text
Validación ENAHO 2024 (INEI, código 966) — skill limpiando-enaho
Tolerancia para porcentajes: 0.1 puntos porcentuales. Todas las cifras de pobreza están ponderadas.
Cada cifra se compara con la referencia calculada con el mismo método.

[APROBADA] Llaves únicas en la sumaria (conglome, vivienda, hogar): 33,691 hogares; referencia 33,691
[APROBADA] Hogares en la sumaria: 33,691 (referencia 33,691)
[APROBADA] Llaves únicas en personas (conglome, vivienda, hogar, codperso): 108,664 filas
[APROBADA] Residentes habituales: 108,664 de 117,721 filas del módulo 02 (referencia 108,664)
[APROBADA] Unión m:1 sin perder filas: 108,664 filas tras unir; 0 personas sin hogar en la sumaria
[APROBADA] Unión sin duplicar personas: cada persona aparece una vez
[APROBADA] Sin vacíos en pobreza, facpob07, ubigeo, estrato y sexo: {'pobreza': 0, 'facpob07': 0, 'ubigeo': 0, 'estrato': 0, 'sexo': 0}
[APROBADA] 25 códigos de departamento (01-25): 25 códigos: 01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25
[APROBADA] Pobreza nacional (personas, facpob07) a ≤0.1 pp de 27.6 %: 27.53 % (diferencia -0.07 pp)
[APROBADA] Pobreza nacional (sumaria, factor07 × mieperho) a ≤0.1 pp de 27.6 %: 27.58 % (diferencia -0.02 pp)
[APROBADA] Pobreza urbana (sumaria, factor07 × mieperho) ≈ 24.8 % (≤0.1 pp): 24.81 % (diferencia +0.01 pp)
[APROBADA] Pobreza rural (sumaria, factor07 × mieperho) ≈ 39.3 % (≤0.1 pp): 39.30 % (diferencia +0.00 pp)

[INFORMATIVA] Pobreza por área con personas y facpob07 (la que usan los gráficos y el mapa): urbano 24.74 %, rural 39.44 %.
[INFORMATIVA] Difiere de la sumaria porque en 1,846 de 33,691 hogares (5.5%) los residentes habituales del módulo 02 no coinciden con mieperho (el INEI excluye de mieperho a trabajadores del hogar y pensionistas). Son dos ponderaciones válidas; ninguna cifra se ajustó.

Resultado: 12 de 12 verificaciones aprobadas.
```

Indicadores principales (`salidas/indicadores.csv`; los 25 departamentos están en ese archivo):

| Grupo | Categoría | Pobreza (%) | Pobreza extrema (%) | Ponderador | n muestra |
|---|---|---|---|---|---|
| nacional | Perú | 27.53 | 5.50 | `facpob07` | 108,664 |
| area | Rural | 39.44 | 15.60 | `facpob07` | 36,071 |
| area | Urbano | 24.74 | 3.13 | `facpob07` | 72,593 |
| sexo | Hombre | 27.37 | 5.37 | `facpob07` | 52,587 |
| sexo | Mujer | 27.68 | 5.62 | `facpob07` | 56,077 |
| nacional_contraste | Perú (sumaria, factor07 × mieperho) | 27.58 | 5.50 | `factor07*mieperho` | 33,691 |
| area_contraste | Rural (sumaria, factor07 × mieperho) | 39.30 | 15.52 | `factor07*mieperho` | 11,660 |
| area_contraste | Urbano (sumaria, factor07 × mieperho) | 24.81 | 3.14 | `factor07*mieperho` | 22,031 |
<!-- validacion:fin -->

## Estructura

```
mcp/server.py         servidor MCP (herramientas, recurso y prompt)
mcp/test_server.py    8 pruebas originales (no se modifican)
mcp/test_propia.py    2 pruebas de la herramienta correlacion
.claude/skills/       limpiando-enaho, graficando-enaho y mapeando-enaho (Parte 2)
scripts/              actualizar_readme.py (cifras de la Parte 2 en el README)
salidas/              pruebas del MCP, validación, indicadores y comparación del mapa
figuras/ mapas/       gráficos y mapa de la ENAHO 2024
integracion/ evaluacion/ evidencias_ia/   partes 3–4 y evidencias
```
