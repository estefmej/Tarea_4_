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

> **Nota añadida después de la corrida.** La fila «Comandos» del Modo B no
> se cumplió tal como se describió: en `dontAsk`, Claude Code aprobó solo
> los comandos Bash de **solo lectura** (`ls`, `cat`, `head`, `grep`) aunque
> no estuvieran en la lista permitida. Las reglas de la sección 3 sí se
> aplicaron también a Bash (`ls evaluacion` fue denegado en C2). Ver 5.5.

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

Corrida del 2026-11-08, 20 sesiones (10 por modo), todas terminaron con
código 0. Detalle por pregunta en `evaluacion/resultados.csv`.

### 5.1 Resumen

| | Modo A (sin MCP ni Skills) | Modo B (con MCP y Skills) |
|---|---|---|
| Correctas | **3 / 10** | **8 / 10** |
| Incorrectas (cifra fuera de tolerancia) | 4 (B3, B4, E2, C2) | 0 |
| Incorrectas por ambigüedad (regla 3) | 2 (E3, C1) | 2 (C1, C2) |
| Sin cifra (no respondió) | 1 (E4) | 0 |
| Sin línea `RESPUESTA` | 0 | 0 |
| Afirmaciones causales en combinadas | 0 | 0 |
| Tiempo promedio (`duration_ms`) | 4,5 s (mediana 4,0) | 10,7 s (mediana 9,1) |
| Tiempo de reloj promedio | 6,1 s | 16,2 s |

### 5.2 Por pregunta

| id | Esperada | Modo A | Modo B | Cambio |
|---|---|---|---|---|
| B1 | 1,97 | 1,97 ✔ | 1,97 ✔ (MCP `serie`) | igual |
| B2 | 8,81; junio 2022 | 8,81, junio 2022 ✔ | 8,81, junio 2022 ✔ (MCP `resumen`) | igual |
| B3 | −39,28 | −40,5 ✘ | −39,28 ✔ (MCP `serie`) | **mejora** |
| B4 | 3,737 | ≈3,75 ✘ | 3,737 ✔ (MCP `serie`) | **mejora** |
| E1 | 27,6 | 27,6 ✔ | 27,6 ✔ (memoria, sin herramientas) | igual |
| E2 | 39,3 | 39,8 ✘ | 39,3 ✔ (`Grep` + salidas previas) | **mejora** |
| E3 | 24,8 | «≈26,1 % (aprox. 26 %)» ✘ ambigua | 24,8 ✔ (`Grep` en README) | **mejora** |
| E4 | Cajamarca; 45,0 | no responde ✘ | Cajamarca, 45,0 ✔ (`Bash cat` de salidas previas) | **mejora** |
| C1 | 1,97; 27,6 | 1,97 y 27,6 ✘ ambigua | 1,97 y 27,6 ✘ ambigua | igual |
| C2 | 8,81; 14,5 | 8,81 y ≈14,7 ✘ | 8,81 y 14,5 ✘ ambigua | igual (A erró la cifra; B, por formato) |

Mejoraron 5 preguntas (B3, B4, E2, E3, E4); ninguna empeoró.

### 5.3 Principales errores

- **Modo A, cifras de memoria desactualizadas o de otra fuente.** En B3
  respondió −40,5 %, cifra cercana a la que difundió el INEI para abril de
  2020; la serie PN01728AM del BCRP marca −39,28 %. En B4 redondeó el tipo
  de cambio a 3,75. En E2 dio 39,8 % (cerca de la pobreza rural de 2023, no
  la de 2024) y en C2 estimó la brecha en 14,7 pp.
- **Modo A, respuestas con dudas.** En E3 dio dos cifras («≈26,1 %
  (aprox. 26 %, por confirmar)») y en E4 declaró que no podía confirmar el
  dato sin consultar al INEI. Es una conducta prudente, pero no responde.
- **Ambigüedad por el formato (ambos modos).** C1 falló en los dos modos
  porque la línea decía «Inflación Lima Metropolitana dic-2024 **(12
  meses)** = 1,97 %…»: el «12» de la etiqueta cuenta como número según la
  regla 3. En el Modo B, C2 falló porque la línea incluyó la cuenta
  «(39,3 % − 24,8 %)». En los tres casos las cifras eran correctas.
  La regla no se cambió después de ver los resultados.
  **Solo como sensibilidad** (no es la calificación oficial): sin esas
  etiquetas y cuentas, el Modo A tendría 4/10 y el Modo B 10/10.
- **Ninguna combinada afirmó causalidad** en ninguno de los dos modos.

### 5.4 Qué herramientas usó realmente el Modo B

- **MCP `bcrp`: se usó en las 6 preguntas con datos del BCRP** (B1-B4,
  C1, C2), con los códigos correctos (PN01273PM, PN01728AM, PN01206PM). En
  B4 también consultó una serie diaria (PD04638PD) para contrastar.
- **Skills: ninguna sesión invocó una Skill.** Las cifras de la ENAHO no se
  recalcularon con los microdatos. Salieron de:
  - memoria del modelo (E1);
  - resultados que las Skills ya habían generado en la Parte 2, guardados en
    `salidas/` (`grafico_por_area_2024.csv`, `grafico_por_departamento_2024.csv`,
    `validacion.txt`) (E2, E4, C2);
  - el `README.md`, que copia la salida de validación con las cifras de
    referencia (E3), y `.claude/skills/limpiando-enaho/reference.md`, que trae
    las cifras oficiales del INEI (C1);
  - en E4, además, `datos/pobreza_departamento_2024.csv` (tabla de referencia
    del curso que descarga la Skill del mapa).

### 5.5 Desviaciones respecto del diseño

1. **Bash de solo lectura permitido en el Modo B.** Ver la nota de la
   sección 2. Así se leyeron `salidas/grafico_por_departamento_2024.csv` y
   `datos/pobreza_departamento_2024.csv` en E4. Ninguno estaba en la lista
   bloqueada.
2. **Fuentes con respuestas no bloqueadas.** La restricción de la sección 3
   cubría `evaluacion/`, `informes/`, `evidencias_ia/` y `salidas/bcrp_*`,
   pero `README.md`, `reference.md`, `datos/pobreza_departamento_2024.csv` y
   las demás salidas de las Skills también contienen las cifras de la ENAHO.
   Por eso el acierto del Modo B en E2-E4 refleja **el trabajo previo del
   repositorio** (Skills ya ejecutadas y documentadas), no la ejecución de
   una Skill durante la evaluación.
3. **Accesos bloqueados.** El único intento de entrar a una ruta bloqueada
   (`ls evaluacion` en C2) fue denegado. Ninguna sesión leyó contenido de
   `evaluacion/`, `informes/`, `evidencias_ia/` ni `salidas/bcrp_*`. En E4,
   `ls salidas` mostró los **nombres** de los archivos `bcrp_*.csv`, no su
   contenido.

## 6. Conclusión

- **El MCP del BCRP es claramente útil.** Con él, el Modo B acertó las 4
  preguntas del BCRP y la parte BCRP de las combinadas, con el código de la
  serie y la fuente citados. Sin él, el Modo A acertó solo los dos datos más
  conocidos (inflación de diciembre 2024 y su máximo) y falló los que exigen
  precisión (PBI de abril 2020, tipo de cambio). El costo es tiempo: unas
  2,4 veces más por pregunta (10,7 s frente a 4,5 s), que sigue siendo poco.
- **Las Skills no se pusieron a prueba en esta evaluación.** El Modo B
  acertó las 4 preguntas de la ENAHO, pero ninguna sesión ejecutó una Skill:
  el modelo prefirió leer las salidas y la documentación que las Skills ya
  habían dejado en el repositorio, o responder de memoria. Esto muestra el
  valor de un repositorio bien documentado y reproducible, pero **no permite
  atribuir la mejora a las Skills en sí**. Para medirlas habría que bloquear
  también `salidas/`, `datos/pobreza_departamento_2024.csv`, `README.md` y
  `reference.md`, o formular preguntas que solo se respondan recalculando
  con los microdatos (por ejemplo, un corte que no esté en `salidas/`).
- **El formato de la respuesta pesa.** Tres de las nueve respuestas
  incorrectas (C1 en ambos modos y C2 en el Modo B) tenían cifras correctas,
  pero agregaron etiquetas o cuentas con números. Una instrucción más estricta («solo los valores, separados
  por punto y coma») reduciría ese ruido en futuras corridas.
- **Ningún modo afirmó causalidad** entre inflación y pobreza.
