"""Mapa coroplético de la pobreza monetaria 2024 por departamento (ENAHO, INEI).

Uso (desde la raíz del proyecto):
    uv run python .claude/skills/mapeando-enaho/scripts/mapear.py

Entradas:
    salidas/personas_2024.parquet          (lo genera la skill limpiando-enaho)
    datos/peru_departamental_simple.geojson (límites; código FIRST_IDDP)
    datos/pobreza_departamento_2024.csv     (referencia de la Sesión 16 del curso,
                                             calculada con ENAHO 2024 del INEI)
Salidas:
    mapas/pobreza_departamento_2024.png
    salidas/comparacion_mapa.csv

Reglas: une ubigeo[:2] con FIRST_IDDP como texto (nunca por nombre); exige 25
departamentos con dato, con Lima (15) y Callao (07) separados; escala secuencial
de claro a oscuro desde 0; leyenda «% de personas»; fuente.
"""

from __future__ import annotations

import argparse
import sys
import textwrap
from pathlib import Path

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
FONDO = "#fcfcfb"
CODIGOS = [f"{i:02d}" for i in range(1, 26)]
# La referencia usa la sumaria (factor07 × mieperho) y viene redondeada a un decimal.
# Con el mismo método se exige ≤0.1 pp. El mapa usa personas y facpob07; ahí se acepta
# hasta 1 pp (la diferencia de método); una brecha mayor indica un error de unión.
TOLERANCIA_MISMO_METODO_PP = 0.1
TOLERANCIA_REF_PP = 1.0
URL_GEOJSON = ("https://raw.githubusercontent.com/d2cml-ai/Data-Science-Python/main/"
               "sessions/06-geoespacial/lab/Data/peru_departamental_simple.geojson")
URL_REF = ("https://raw.githubusercontent.com/d2cml-ai/Data-Science-Python/main/"
           "sessions/16-skills-enaho/referencias/pobreza_departamento_2024.csv")


def fallar(msj: str) -> None:
    sys.exit(f"ERROR: {msj}")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--anio", type=int, default=2024)
    ap.add_argument("--datos", type=Path, default=Path("datos"))
    ap.add_argument("--salidas", type=Path, default=Path("salidas"))
    ap.add_argument("--mapas", type=Path, default=Path("mapas"))
    a = ap.parse_args()

    parquet = a.salidas / f"personas_{a.anio}.parquet"
    if not parquet.exists():
        fallar(f"no existe {parquet}. Usa primero la skill limpiando-enaho "
               f"(uv run python .claude/skills/limpiando-enaho/scripts/limpiar.py --anio {a.anio}).")
    geo_path = a.datos / "peru_departamental_simple.geojson"
    ref_path = a.datos / f"pobreza_departamento_{a.anio}.csv"
    for ruta, url in [(geo_path, URL_GEOJSON), (ref_path, URL_REF)]:
        if not ruta.exists():
            fallar(f"falta {ruta}. Descárgalo de {url}")

    # 1. Pobreza por departamento, ponderada con facpob07 (nunca promedio simple).
    base = pd.read_parquet(parquet, columns=["departamento", "pobre", "facpob07"])
    base["departamento"] = base["departamento"].astype(str)
    pob = (
        base.groupby("departamento")
        .apply(lambda d: np.average(d["pobre"].astype(float), weights=d["facpob07"]) * 100,
               include_groups=False)
        .rename("pobreza_pct")
        .reset_index()
    )

    # 2. Unir por código como texto (FIRST_IDDP), nunca por nombre.
    geo = gpd.read_file(geo_path)
    geo["FIRST_IDDP"] = geo["FIRST_IDDP"].astype(str).str.zfill(2)
    if geo["FIRST_IDDP"].duplicated().any():
        fallar("el GeoJSON tiene códigos FIRST_IDDP repetidos.")
    mapa = geo.merge(pob, left_on="FIRST_IDDP", right_on="departamento", how="left", validate="1:1")

    con_dato = mapa.loc[mapa["pobreza_pct"].notna(), "FIRST_IDDP"]
    if sorted(con_dato) != CODIGOS or len(mapa) != 25:
        faltan = sorted(set(CODIGOS) - set(con_dato))
        fallar(f"el mapa debe tener 25 departamentos con dato; tiene {len(con_dato)}. Sin dato: {faltan}")
    for cod, nombre in [("15", "Lima"), ("07", "Callao")]:
        if (mapa["FIRST_IDDP"] == cod).sum() != 1:
            fallar(f"{nombre} ({cod}) debe ser una unidad propia en el mapa.")
    print(f"Unión por código: {len(con_dato)} de 25 departamentos con dato; Lima (15) y Callao (07) separados.")

    # 3. Comparar con la referencia de la Sesión 16.
    ref = pd.read_csv(ref_path, dtype={"ccdd": str})
    ref["ccdd"] = ref["ccdd"].str.zfill(2)
    comp = (
        mapa[["FIRST_IDDP", "NOMBDEP", "pobreza_pct"]]
        .rename(columns={"FIRST_IDDP": "codigo", "NOMBDEP": "departamento",
                         "pobreza_pct": "pobreza_calculada_pct"})
        .merge(ref.rename(columns={"ccdd": "codigo", "pobreza_pct": "pobreza_referencia_pct"})
               [["codigo", "pobreza_referencia_pct"]], on="codigo", how="left", validate="1:1")
        .sort_values("codigo")
    )
    # Contraste con el mismo método de la referencia (sumaria, factor07 × mieperho),
    # que calcula limpiando-enaho en salidas/indicadores.csv.
    ind = pd.read_csv(a.salidas / "indicadores.csv", dtype={"codigo": str})
    sumaria = (ind.loc[ind.grupo == "departamento_contraste", ["codigo", "pobreza_pct"]]
               .rename(columns={"pobreza_pct": "pobreza_sumaria_pct"}))
    if len(sumaria) != 25:
        fallar("indicadores.csv no tiene los 25 departamentos de contraste; vuelve a correr limpiando-enaho.")
    comp = comp.merge(sumaria, on="codigo", how="left", validate="1:1")
    comp["pobreza_calculada_pct"] = comp["pobreza_calculada_pct"].round(2)
    comp["dif_facpob07_pp"] = (comp["pobreza_calculada_pct"] - comp["pobreza_referencia_pct"]).round(2)
    comp["dif_sumaria_pp"] = (comp["pobreza_sumaria_pct"] - comp["pobreza_referencia_pct"]).round(2)
    comp["valida_mismo_metodo"] = comp["dif_sumaria_pp"].abs() <= TOLERANCIA_MISMO_METODO_PP
    comp["valida_facpob07"] = comp["dif_facpob07_pp"].abs() <= TOLERANCIA_REF_PP
    comp = comp.rename(columns={"pobreza_calculada_pct": "pobreza_mapa_facpob07_pct"})
    comp["referencia"] = "Sesión 16 del curso, calculada con ENAHO 2024 del INEI"
    a.salidas.mkdir(parents=True, exist_ok=True)
    comp.drop(columns="geometry", errors="ignore").to_csv(
        a.salidas / "comparacion_mapa.csv", index=False, encoding="utf-8")
    print(f"Guardado: {a.salidas / 'comparacion_mapa.csv'}")
    for col, met in [("dif_sumaria_pp", "sumaria, factor07 × mieperho (mismo método)"),
                     ("dif_facpob07_pp", "personas, facpob07 (valor del mapa)")]:
        print(f"Diferencia con la referencia [{met}]: media {comp[col].abs().mean():.2f} pp, "
              f"máxima {comp[col].abs().max():.2f} pp ({comp.loc[comp[col].abs().idxmax(), 'departamento']}).")
    malos = comp.loc[~(comp["valida_mismo_metodo"] & comp["valida_facpob07"])]
    if comp["pobreza_referencia_pct"].isna().any() or len(malos):
        print(malos.to_string(index=False))
        fallar(f"algún departamento difiere de la referencia (>{TOLERANCIA_MISMO_METODO_PP} pp con el mismo "
               f"método o >{TOLERANCIA_REF_PP} pp con facpob07); revisa la unión (no ajustes resultados).")
    print(f"Validación: 25 de 25 departamentos a ≤{TOLERANCIA_MISMO_METODO_PP} pp de la referencia con el mismo método.")

    # 4. Mapa: una sola escala secuencial (claro→oscuro) desde 0.
    vmax = float(np.ceil(mapa["pobreza_pct"].max() / 10) * 10)
    fig, ax = plt.subplots(figsize=(9, 9), facecolor=FONDO)
    ax.set_facecolor(FONDO)
    mapa.plot(column="pobreza_pct", cmap="Blues", vmin=0, vmax=vmax, ax=ax,
              edgecolor="white", linewidth=0.6, legend=True,
              legend_kwds={"label": "% de personas", "shrink": 0.55,
                           "orientation": "vertical", "pad": 0.01})
    ax.set_axis_off()
    # Rótulos en el océano con línea guía: los dos extremos, Lima y Callao (valores calculados).
    orden = mapa.sort_values("pobreza_pct")
    minx, _, maxx, _ = mapa.total_bounds
    x_texto = minx - 0.6
    desplazar = {"15": +0.7, "07": -0.7}  # separa Lima y Callao, que están pegados
    rotular = [orden.iloc[-1]["FIRST_IDDP"], "15", "07", orden.iloc[0]["FIRST_IDDP"]]
    for cod in dict.fromkeys(rotular):
        f = mapa[mapa["FIRST_IDDP"] == cod].iloc[0]
        x, y = f.geometry.representative_point().coords[0]
        ax.annotate(f"{f['NOMBDEP'].title()} {f['pobreza_pct']:.1f} %", (x, y),
                    xytext=(x_texto, y + desplazar.get(cod, 0)), ha="right", va="center",
                    fontsize=8.5, color=TINTA,
                    arrowprops={"arrowstyle": "-", "color": TINTA_2, "linewidth": 0.7,
                                "shrinkA": 2, "shrinkB": 0})
    ax.set_xlim(minx - 4.5, maxx + 0.3)
    alto, bajo = orden.iloc[-1], orden.iloc[0]
    fig.suptitle(f"La pobreza monetaria en {a.anio} fue mayor en {alto['NOMBDEP'].title()} "
                 f"({alto['pobreza_pct']:.1f} %)\ny menor en {bajo['NOMBDEP'].title()} "
                 f"({bajo['pobreza_pct']:.1f} %)",
                 x=0.04, y=0.97, ha="left", fontsize=13, fontweight="bold", color=TINTA)
    ax.set_title(f"Pobreza monetaria por departamento, {a.anio} (% de personas). "
                 "Lima y Callao por separado.", loc="left", fontsize=9, color=TINTA_2)
    # Misma nota que graficando-enaho (sin la frase de IC: el mapa no muestra intervalos).
    nota = (f"Fuente: INEI, ENAHO {a.anio} (módulos 34 y 02). Estimación ponderada con facpob07 (personas). "
            "Elaboración propia. La pobreza monetaria se mide por hogar: todos sus miembros comparten la "
            "condición del hogar. Límites: GeoJSON departamental del curso.")
    fig.text(0.04, 0.02, textwrap.fill(nota, 125), fontsize=7.5, color=TINTA_2, ha="left", va="bottom")
    a.mapas.mkdir(parents=True, exist_ok=True)
    salida = a.mapas / f"pobreza_departamento_{a.anio}.png"
    fig.savefig(salida, dpi=200, facecolor=FONDO, bbox_inches="tight")
    plt.close(fig)
    print(f"Guardado: {salida}")


if __name__ == "__main__":
    main()
