# Entrega – Tarea 4

<!-- Generado por scripts/generar_entrega.py; no editar las cifras a mano. -->

Antes de publicar: reemplazar **Nombre completo**. Copiar en el Issue
<https://github.com/d2cml-ai/Data-Science-Python/issues/201> el texto entre las dos líneas.

---

### Tarea 4 – Individual

**Estudiante:** Nombre completo (@estefmej)

**Pregunta de investigación:** ¿Cómo evolucionaron la inflación, el tipo de cambio y la actividad económica del Perú entre 2020 y 2024, y qué diferencias por área y departamento presentaba la pobreza monetaria en 2024?

**Repositorio de GitHub:** https://github.com/estefmej/Tarea_4_

**Informe final:** https://github.com/estefmej/Tarea_4_/blob/main/informes/informe_final.md

**Pruebas MCP:** 10/10 aprobadas

**Validación ENAHO:**
- Pobreza nacional 2024: 27.6 %
- Residentes habituales: 108,664
- Unidades territoriales procesadas: 25/25

**Evaluación del agente:**
- Sin MCP/Skills: 3/10 respuestas correctas
- Con MCP/Skills: 8/10 respuestas correctas
- Resultados completos: https://github.com/estefmej/Tarea_4_/blob/main/evaluacion/resultados.csv

**Evidencia de integración MCP + Skills:** https://github.com/estefmej/Tarea_4_/blob/main/evidencias_ia/integracion/02_ejecucion_agente.txt

**Evidencias de uso de IA:** https://github.com/estefmej/Tarea_4_/tree/main/evidencias_ia

---

## Origen de cada cifra (no copiar en el Issue)

| Campo | Valor | Archivo | Línea o criterio |
|---|---|---|---|
| Pregunta de investigación | texto | `informes/informe_final.md` | sección 1, línea «**Pregunta.**» |
| Pruebas MCP | 10/10 | `salidas/pruebas_mcp.txt` | ============================= 10 passed in 4.21s ============================== |
| Pobreza nacional 2024 | 27.6 % (de 27.58 %) | `salidas/validacion.txt` | [APROBADA] Pobreza nacional (sumaria, factor07 × mieperho) a ≤0.1 pp de 27.6 %: 27.58 % (diferencia -0.02 pp) |
| Residentes habituales | 108,664 | `salidas/validacion.txt` | [APROBADA] Residentes habituales: 108,664 de 117,721 filas del módulo 02 (referencia 108,664) |
| Unidades territoriales | 25/25 | `salidas/validacion.txt` | [APROBADA] 25 códigos de departamento (01-25) |
| Sin MCP/Skills (Modo A) | 3/10 | `evaluacion/resultados.csv` | filas con modo = A y correcta = sí |
| Con MCP/Skills (Modo B) | 8/10 | `evaluacion/resultados.csv` | filas con modo = B y correcta = sí |

Pobreza nacional: se informa la cifra con la sumaria (`factor07 × mieperho`), el método del INEI y del informe final. Con la base de personas (`facpob07`) es 27.53 % (misma fuente). La validación completa aprobó 12 de 12 verificaciones.

Análisis complementario B2 (no se pide en el comentario): 1/6 en `evaluacion/resultados_b2.csv`.
