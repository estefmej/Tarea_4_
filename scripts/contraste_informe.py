"""Contraste de las cifras del informe final (Parte 3) con sus archivos de origen.

Lee los CSV que generaron graficar_serie (BCRP) y las Skills de ENAHO, calcula las pocas cifras
derivadas que usa el informe (valores de diciembre, meses con PBI negativo) y compara cada cifra
principal con su fuente. Escribe el resultado en salidas/contraste_informe.txt.

Uso: uv run python scripts/contraste_informe.py
"""
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
S = RAIZ / "salidas"


def serie(codigo):
    d = pd.read_csv(S / f"bcrp_{codigo}.csv", dtype={"periodo": str})
    return d.set_index("periodo")["valor"]


lineas = ["Contraste de cifras del informe final (Parte 3)", ""]

# BCRP
inf, tc, pbi = serie("PN01273PM"), serie("PN01206PM"), serie("PN01728AM")
lineas.append("[BCRP] salidas/bcrp_<codigo>.csv (descargados con graficar_serie, 2020-01 a 2024-12)")
lineas.append("PN01273PM inflación Lima 12 meses, diciembre de cada año: "
              + ", ".join(f"{a}: {inf[f'{a}-12']:.2f}" for a in range(2020, 2025)))
lineas.append(f"PN01273PM máximo: {inf.idxmax()} = {inf.max():.2f}; mínimo: {inf.idxmin()} = {inf.min():.2f}; "
              f"promedio = {inf.mean():.2f}; meses sobre 3 %: {(inf > 3).sum()} de {len(inf)}")
lineas.append(f"PN01206PM tipo de cambio: {tc.index[0]} = {tc.iloc[0]:.3f}; máximo {tc.idxmax()} = {tc.max():.3f}; "
              f"{tc.index[-1]} = {tc.iloc[-1]:.3f}; promedio = {tc.mean():.3f}")
p23 = pbi["2023-01":"2023-12"]
p24 = pbi["2024-01":"2024-12"]
lineas.append(f"PN01728AM PBI var. % interanual: mínimo {pbi.idxmin()} = {pbi.min():.2f}; máximo {pbi.idxmax()} = "
              f"{pbi.max():.2f}; 2023: {(p23 < 0).sum()} de 12 meses negativos, promedio {p23.mean():.2f}; "
              f"2024: promedio {p24.mean():.2f}, {pbi.index[-1]} = {pbi.iloc[-1]:.2f}")
lineas.append("")

# ENAHO
area = pd.read_csv(S / "grafico_por_area_2024.csv").set_index("codigo")
dep = pd.read_csv(S / "grafico_por_departamento_2024.csv", dtype={"codigo": str}).set_index("codigo")
comp = pd.read_csv(S / "comparacion_mapa.csv", dtype={"codigo": str}).set_index("codigo")
lineas.append("[ENAHO] salidas/grafico_por_area_2024.csv, grafico_por_departamento_2024.csv, comparacion_mapa.csv")
lineas.append(f"Nacional (sumaria): {area['promedio_peru'].iloc[0]:.2f} % "
              f"(IC {area['promedio_peru_ic_inf'].iloc[0]:.2f}-{area['promedio_peru_ic_sup'].iloc[0]:.2f})")
for c in ["urbano", "rural"]:
    r = area.loc[c]
    lineas.append(f"{r['categoria']}: {r['estimacion']:.2f} % (IC {r['ic_inf']:.2f}-{r['ic_sup']:.2f}, n = {r['n']} hogares)")
lineas.append(f"Brecha rural - urbano: {area.loc['rural', 'estimacion'] - area.loc['urbano', 'estimacion']:.2f} pp")
for c in ["06", "11", "15"]:
    r, k = dep.loc[c], comp.loc[c]
    lineas.append(f"{r['categoria']} ({c}): gráfico {r['estimacion']:.2f} %, mapa {k['pobreza_mapa_sumaria_pct']:.2f} %, "
                  f"referencia Sesión 16 {k['pobreza_referencia_pct']:.1f} %, diferencia {k['diferencia_pp']:+.2f} pp")
lineas.append(f"Departamentos a <= 0.1 pp de la referencia: {int(comp['dentro_tolerancia'].sum())} de {len(comp)}; "
              f"diferencia máxima {comp['diferencia_pp'].abs().max():.2f} pp")
coinciden = (dep["estimacion"].round(2) - comp["pobreza_mapa_sumaria_pct"].reindex(dep.index)).abs().max()
lineas.append(f"Gráfico vs mapa, diferencia máxima: {coinciden:.2f} pp")

texto = "\n".join(lineas) + "\n"
(S / "contraste_informe.txt").write_text(texto, encoding="utf-8")
print(texto)
