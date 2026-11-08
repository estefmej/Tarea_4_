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
| 2. Skills de ENAHO | Pobreza e indicadores de hogares | `skills/` | pendiente |
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

## Estructura

```
mcp/server.py         servidor MCP (herramientas, recurso y prompt)
mcp/test_server.py    8 pruebas originales (no se modifican)
mcp/test_propia.py    2 pruebas de la herramienta correlacion
salidas/              salida de las pruebas
skills/ integracion/ evaluacion/ evidencias_ia/   partes 2–4
```
