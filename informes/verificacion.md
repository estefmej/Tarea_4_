# Verificación de afirmaciones del informe final

Hay cuatro afirmaciones de `informes/informe_final.md`: dos del BCRP y dos de la ENAHO. Para cada una, la
columna «Cómo verificarlo» indica una fuente **independiente** de nuestro procesamiento (no el servidor MCP
ni nuestros scripts). Las tres últimas columnas quedan vacías para completarlas a mano.

| # | Afirmación | Valor calculado | Archivo o serie de origen | Cómo verificarlo | Valor en la fuente oficial | ¿Coincide? | Diferencia |
|---|---|---|---|---|---|---|---|
| 1 | La inflación de Lima a 12 meses llegó a su máximo del periodo 2020-2024 en junio de 2022 (H1). | 8,81 % (8,8126) | Serie BCRP `PN01273PM`; `salidas/bcrp_PN01273PM.csv`, fila `2022-06` | Abrir la tabla oficial del BCRP https://estadisticas.bcrp.gob.pe/estadisticas/series/api/PN01273PM/html/2022-6/2022-6 y leer el valor de **Jun.2022**. | 8,81 % en la tabla web del BCRP; 8,812633 en la descarga XLSX oficial (enero-diciembre 2022), donde además junio es el valor más alto del año | Sí | 0,00 pp (solo redondeo de decimales) |
| 2 | El PBI cayó 39,28 % interanual en abril de 2020 (H3). | −39,28 % (−39,2770) | Serie BCRP `PN01728AM`; `salidas/bcrp_PN01728AM.csv`, fila `2020-04` | Abrir la tabla oficial del BCRP https://estadisticas.bcrp.gob.pe/estadisticas/series/api/PN01728AM/html/2020-4/2020-4 y leer el valor de **Abr.2020**. | −39,3 % en la tabla web del BCRP; −39,277 en la descarga XLSX oficial. Serie: «Producto bruto interno y demanda interna (variación porcentual interanual) - PBI» | Sí | 0,00 pp (la web muestra un decimal) |
| 3 | La pobreza monetaria nacional en 2024 fue 27,58 % (H4). | 27,58 % (IC 95 %: 26,59-28,57) | `salidas/grafico_por_area_2024.csv`, columna `promedio_peru` (sumaria, `factor07 × mieperho`) | Informe técnico del INEI «Perú: Evolución de la Pobreza Monetaria 2015-2024», cuadro de incidencia de la pobreza monetaria total, **Total nacional, año 2024**. | 27,6 % (INEI, sección 4.2, p. 63). Intervalo de confianza oficial 2024: 26,6 a 28,6 (p. 64) | Sí | 0,02 pp por redondeo; el intervalo calculado (26,59-28,57) también coincide con el oficial al redondear |
| 4 | La pobreza monetaria rural en 2024 fue 39,30 % (H4). | 39,30 % (IC 95 %: 37,80-40,81) | `salidas/grafico_por_area_2024.csv`, fila `rural` (sumaria, `factor07 × mieperho`) | Informe técnico del INEI «Perú: Evolución de la Pobreza Monetaria 2015-2024», cuadro de incidencia de la pobreza monetaria por área de residencia, **Rural, año 2024**. | 39,3 % (INEI, sección 4.2.1, p. 64) | Sí | 0,00 pp |

**Verificación manual realizada el 8 de noviembre de 2026** consultando directamente el portal BCRPData (tabla web y descarga XLSX) y el informe técnico del INEI en PDF. Las 4 afirmaciones coinciden con las fuentes oficiales; las únicas diferencias son de redondeo. Un hallazgo adicional: el intervalo de confianza calculado por el proyecto para la pobreza nacional (26,59-28,57) coincide con el que publica el INEI (26,6-28,6), lo que respalda que el diseño muestral se aplicó correctamente.

Notas:
- Las cifras del INEI vienen con un decimal. Al comparar, conviene redondear el valor calculado a un decimal
  antes de anotar la diferencia.
- No se eligió Lima como afirmación porque el departamento 15 de la ENAHO no corresponde a las categorías
  que publica el INEI («Lima Metropolitana», que incluye Callao, y «Lima región»). Ver Limitaciones del
  informe.
