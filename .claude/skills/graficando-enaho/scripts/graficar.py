"""Gráficos de barras de la pobreza monetaria 2024 (ENAHO, INEI) por área, sexo o departamento.

Uso (desde la raíz del proyecto):
    uv run python .claude/skills/graficando-enaho/scripts/graficar.py --por todos
    uv run python .claude/skills/graficando-enaho/scripts/graficar.py --por area

Reglas: pondera con facpob07; barras desde cero, ordenadas, un solo color y el valor
en cada barra; título analítico con el periodo; unidad (% de personas); fuente; PNG 200 dpi.
"""

from __future__ import annotations

import argparse
import sys
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

COLOR = "#2a78d6"        # un solo color para todas las barras
TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
FONDO = "#fcfcfb"
FUENTE = "Fuente: INEI, ENAHO 2024. Pobreza monetaria ponderada con facpob07 (residentes habituales)."
ETIQUETAS = {"urbano": "Urbano", "rural": "Rural", "hombre": "Hombres", "mujer": "Mujeres"}
AREA_FEM = {"Urbano": "urbana", "Rural": "rural"}  # «el área rural», «la urbana»
NOMBRE_POR = {"area": "área", "sexo": "sexo", "departamento": "departamento"}


def pobreza_por(base: pd.DataFrame, col: str) -> pd.Series:
    """% de personas pobres por grupo, ponderado con facpob07 (nunca promedio simple)."""
    return base.groupby(col).apply(
        lambda d: np.average(d["pobre"].astype(float), weights=d["facpob07"]) * 100,
        include_groups=False,
    )


def titulo(por: str, s: pd.Series, anio: int) -> str:
    """Título analítico construido con los datos (nada escrito a mano)."""
    s = s.sort_values(ascending=False)
    alto, bajo = s.index[0], s.index[-1]
    if por == "departamento":
        return (f"{alto} ({s.iloc[0]:.1f} %) tuvo la mayor pobreza monetaria en {anio}; "
                f"{bajo}, la menor ({s.iloc[-1]:.1f} %)")
    dif = s.iloc[0] - s.iloc[-1]
    if dif < 1:
        return (f"La pobreza monetaria fue similar entre {alto.lower()} ({s.iloc[0]:.1f} %) "
                f"y {bajo.lower()} ({s.iloc[-1]:.1f} %) en {anio}")
    return (f"En {anio}, la pobreza monetaria fue {dif:.1f} puntos mayor en el área "
            f"{AREA_FEM.get(alto, alto.lower())} ({s.iloc[0]:.1f} %) que en la "
            f"{AREA_FEM.get(bajo, bajo.lower())} ({s.iloc[-1]:.1f} %)")


def graficar(s: pd.Series, por: str, anio: int, salida: Path, nota_extra: str = "") -> Path:
    s = s.sort_values(ascending=True)  # en barras horizontales, la mayor queda arriba
    alto = 0.32 * len(s) + 2.2
    fig, ax = plt.subplots(figsize=(9, alto), facecolor=FONDO)
    ax.set_facecolor(FONDO)
    barras = ax.barh(s.index, s.values, color=COLOR, height=0.62)
    for b, v in zip(barras, s.values):
        ax.text(v + s.max() * 0.01, b.get_y() + b.get_height() / 2, f"{v:.1f}",
                va="center", ha="left", fontsize=9, color=TINTA)
    ax.set_xlim(0, s.max() * 1.12)  # el eje empieza en cero
    ax.set_xlabel("% de personas en situación de pobreza monetaria", color=TINTA_2, fontsize=9)
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color("#c8c7c2")
    ax.tick_params(axis="y", length=0, labelsize=10, colors=TINTA)
    ax.tick_params(axis="x", labelsize=8, colors=TINTA_2)
    ax.xaxis.grid(True, color="#e6e5e0", linewidth=0.8)
    ax.set_axisbelow(True)
    fig.suptitle(textwrap.fill(titulo(por, s, anio), 85), x=0.02, ha="left", fontsize=12,
                 fontweight="bold", color=TINTA)
    ax.set_title(f"Pobreza monetaria por {NOMBRE_POR[por]}, {anio} (% de personas)", loc="left",
                 fontsize=9.5, color=TINTA_2, pad=8)
    fig.text(0.02, 0.01, FUENTE + nota_extra, fontsize=7.5, color=TINTA_2, ha="left", va="bottom")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    salida.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(salida, dpi=200, facecolor=FONDO)
    plt.close(fig)
    return salida


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--por", choices=["area", "sexo", "departamento", "todos"], default="todos")
    ap.add_argument("--anio", type=int, default=2024)
    ap.add_argument("--salidas", type=Path, default=Path("salidas"))
    ap.add_argument("--figuras", type=Path, default=Path("figuras"))
    a = ap.parse_args()

    parquet = a.salidas / f"personas_{a.anio}.parquet"
    if not parquet.exists():
        sys.exit(f"ERROR: no existe {parquet}. Usa primero la skill limpiando-enaho "
                 f"(uv run python .claude/skills/limpiando-enaho/scripts/limpiar.py --anio {a.anio}).")
    base = pd.read_parquet(parquet)

    # Nombres de departamento desde indicadores.csv (los genera limpiando-enaho).
    ind = pd.read_csv(a.salidas / "indicadores.csv", dtype={"codigo": str})
    nombres = ind.loc[ind.grupo == "departamento"].set_index("codigo")["categoria"]

    pedidos = ["area", "sexo", "departamento"] if a.por == "todos" else [a.por]
    for por in pedidos:
        s = pobreza_por(base, por)
        # Control: lo graficado debe coincidir con indicadores.csv.
        ref = ind.loc[ind.grupo == por].set_index("codigo")["pobreza_pct"]
        dif = (s.round(2) - ref.reindex(s.index)).abs().max()
        if not dif <= 0.01:
            sys.exit(f"ERROR: la pobreza por {por} no coincide con indicadores.csv (dif. {dif}).")
        if por == "departamento":
            if len(s) != 25:
                sys.exit(f"ERROR: se esperaban 25 departamentos y hay {len(s)}.")
            s.index = s.index.map(nombres)
            nota = " Lima incluye Lima Metropolitana y Lima Provincias; Callao va aparte."
        else:
            s.index = s.index.map(ETIQUETAS)
            nota = " Urbano: estrato 1-5." if por == "area" else ""
        ruta = graficar(s, por, a.anio, a.figuras / f"pobreza_{por}_{a.anio}.png", nota)
        print(f"Guardado: {ruta}")
        print(s.sort_values(ascending=False).round(1).to_string())


if __name__ == "__main__":
    main()
