# Evaluación: Claude Code con y sin MCP y Skills

> Las secciones 1 a 4 se escribieron y se registraron en git **antes** de
> ejecutar las 20 sesiones. Las respuestas esperadas (`preguntas.csv`) y la
> regla de calificación (`calificar.py`) no se modificaron después de ver
> los resultados.

## 1. Diseño

- 10 preguntas (`evaluacion/preguntas.csv`): 4 BCRP, 4 ENAHO 2024 (cifras
  oficiales del informe técnico del INEI «Perú: Evolución de la Pobreza
  Monetaria 2015-2024») y 2 combinadas. Las respuestas BCRP esperadas se
  calcularon con `evaluacion/esperadas_bcrp.py`, que consulta la API pública
  del BCRP directamente, sin usar `mcp/server.py`.
- Cada pregunta corre en una sesión independiente de `claude -p`
  (`evaluacion/ejecutar.py`), con el mismo modelo en ambos modos
  (`--model sonnet`, que resolvió a `claude-sonnet-5-5`), sin persistencia de
  sesión y con `--permission-mode dontAsk` (lo no permitido se deniega sin
  preguntar).
- Instrucción idéntica en ambos modos: la pregunta seguida de
  «Termina tu respuesta con una línea con el formato: RESPUESTA: <valor o valores>».
- Registros completos (stream-json con herramientas y tiempos) en
  `evaluacion/registros/<modo>_<id>.jsonl`; comando exacto, carpeta y tiempo
  de reloj en `<modo>_<id>.meta.json`.

## 2. Herramientas habilitadas en cada modo

Las listas salen del mensaje de inicio (`system/init`) de las sesiones.

| | Modo A (sin MCP ni Skills) | Modo B (con MCP y Skills) |
|---|---|---|
| Carpeta de trabajo | `%TEMP%\tarea4_evaluacion_modoA` (vacía, fuera del repo) | raíz del repo |
| Servidores MCP | ninguno (`--strict-mcp-config` sin `--mcp-config`) | solo `bcrp` (`--strict-mcp-config --mcp-config .mcp.json`) |
| Herramientas MCP | — | `buscar_series`, `serie`, `resumen`, `correlacion`, `graficar_serie`; además `ListMcpResourcesTool`, `ReadMcpResourceTool`, `ReadMcpResourceDirTool` |
| Skills | bloqueadas (`Skill` denegada) | `Skill` permitida: las del proyecto (`limpiando-enaho`, `graficando-enaho`, `mapeando-enaho`) y las de usuario/plugins |
| Lectura de archivos | bloqueada (`Read`, `Glob`, `Grep` denegadas) | `Read`, `Glob`, `Grep` permitidas salvo las rutas de la sección 3 |
| Comandos | bloqueados (`Bash`, `PowerShell` denegadas) | `Bash` solo para `uv run python *skills*scripts*` (los scripts de las Skills); `PowerShell` denegada |
| Web | `WebSearch`, `WebFetch` denegadas | `WebSearch`, `WebFetch` denegadas |
| Otras denegadas en ambos | `Agent`, `Monitor`, `RemoteTrigger`, `CronCreate`, `ScheduleWakeup`, `SendMessage`, `DesignSync`, `PushNotification`, `EnterWorktree` | ídem |
| Otras presentes (sin permiso explícito; en `dontAsk` se deniegan si piden permiso) | `CronDelete`, `CronList`, `Edit`, `ExitWorktree`, `ListAgents`, `NotebookEdit`, `ReportFindings`, `TaskStop`, `ToolSearch`, `Write` | ídem |

Lista completa del Modo A: `CronDelete, CronList, Edit, ExitWorktree,
ListAgents, NotebookEdit, ReportFindings, TaskStop, ToolSearch, Write`.

Lista completa del Modo B: `Bash, CronDelete, CronList, Edit, ExitWorktree,
Glob, Grep, ListAgents, ListMcpResourcesTool, NotebookEdit, Read,
ReadMcpResourceDirTool, ReadMcpResourceTool, ReportFindings, Skill, TaskStop,
ToolSearch, Write, mcp__bcrp__buscar_series, mcp__bcrp__correlacion,
mcp__bcrp__graficar_serie, mcp__bcrp__resumen, mcp__bcrp__serie`.

## 3. Restricción de lectura en el Modo B

Para que el Modo B obtenga las cifras solo con el MCP y las Skills (y no
copiándolas de archivos con respuestas ya calculadas), `evaluacion/permisos_modo_b.json`
deniega `Read`, `Glob` y `Grep` sobre:

- `evaluacion/**` (preguntas y respuestas esperadas)
- `informes/**` (informe final y verificación de la Parte 3)
- `evidencias_ia/**`
- `salidas/bcrp_*` (series BCRP descargadas en la Parte 3)

Sí puede leer las demás salidas de `salidas/` (por ejemplo `indicadores.csv`
y `validacion.txt`), porque son lo que producen las Skills de la ENAHO.

**Verificación previa (prueba adversarial).** Antes del piloto se pidió a
una sesión con la misma configuración que intentara leer esos archivos:
`Read` de `informes/verificacion.md`, `evaluacion/preguntas.csv` y
`salidas/bcrp_PN01273PM.csv` fueron denegados; `Grep` en `informes/` fue
denegado; `Glob` sobre `evidencias_ia/**` devolvió «No files found» aunque la
carpeta tiene 19 archivos; `cat` y `head` por Bash fueron denegados. `Read`
de `salidas/indicadores.csv` sí fue permitido. En el piloto (B1) ninguna
sesión intentó leer archivos bloqueados.

**Limitación.** En el Modo B, Claude Code incluye en su contexto el estado
de git del repo (nombres de archivos y mensajes de commit recientes). No
contiene cifras, pero sí revela que existen informes y verificaciones.

## 4. Regla de calificación (fijada antes de ver resultados)

La aplica `evaluacion/calificar.py`; nadie califica a ojo.

1. Se toma la **última línea** de la respuesta final que empiece con
   `RESPUESTA:` (se ignoran asteriscos u otros símbolos de formato). Si no
   existe, la respuesta se registra como **«sin respuesta»** y cuenta como
   incorrecta.
2. De esa línea se quitan las **fechas**: meses con o sin año (`junio 2022`,
   `jun-2022`, `dic-2024`) y años sueltos de 1990 a 2035 sin decimales. Los
   meses quitados se guardan para las preguntas que piden un mes.
3. Se extraen los **números restantes en orden** (acepta coma o punto
   decimal y signo menos; no cuentan los dígitos pegados a letras, como
   `PN01273PM`). El primer número se compara con la primera cifra esperada,
   el segundo con la segunda, y así sucesivamente, cada uno con su tolerancia:
   ±0,05 pp para tasas del BCRP, ±0,01 para el tipo de cambio y ±0,1 pp para
   pobreza. El signo cuenta (en B3, «39,28» no equivale a «−39,28»).
   - Menos números que cifras esperadas → incorrecta (falta cifra).
   - **Más números que cifras esperadas → incorrecta por ambigüedad**
     (por ejemplo, `1,97 % (1,9663 %)` o una cuenta como `39,3 − 24,8 = 14,5`).
4. **Meses y departamentos:** debe aparecer exactamente un mes (B2: junio
   de 2022, nombre y año) o exactamente un departamento (E4: Cajamarca), y
   coincidir con el esperado. Se comparan sin tildes ni mayúsculas, y se
   aceptan las abreviaturas de mes (`jun`). Un mes o departamento adicional
   hace la respuesta ambigua.
5. **Combinadas (C1, C2):** además de las dos cifras, el texto completo de
   la respuesta no debe afirmar causalidad. Se busca una lista fija de
   expresiones causales (`causó`, `provocó`, `debido a`, `generó`,
   `explica`, `contribuyó`, `como consecuencia`, `llevó a`, etc.); no cuentan
   si van precedidas, en los 60 caracteres anteriores, de una negación
   (`no`, `sin`, `ni`, `nunca`, `tampoco`, `evitar`). La frase detectada se
   copia en la columna `errores` para poder revisarla.
6. `tiempo_segundos` es la duración que informa cada sesión
   (`duration_ms`); el tiempo de reloj está en los `.meta.json`.

La regla se probó antes del experimento con 29 casos inventados (formatos
de número, meses, departamentos, orden, ambigüedad y frases causales), todos
con el resultado esperado.

## 5. Resultados

*Pendiente: se completa después de ejecutar las 20 sesiones.*
