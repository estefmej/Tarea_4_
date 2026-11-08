"""Gráficos de la pobreza monetaria 2024 (ENAHO, INEI) por área, sexo, edad o departamento.

Uso (desde la raíz del proyecto):
    uv run python .claude/skills/graficando-enaho/scripts/graficar.py --por area
    uv run python .claude/skills/graficando-enaho/scripts/graficar.py --por todos --indicador extrema

Cada figura lleva intervalos de confianza al 95 % con el diseño muestral (linealización de
Taylor; UPM = conglome; estratos = departamento × estrato; ver diseno.py), el promedio
nacional y un título con el hallazgo calculado por el script. Los datos de cada figura se
guardan en salidas/grafico_por_<corte>_2024.csv.

Métodos:
    area, departamento -> sumaria de hogares, factor07 × mieperho (n en hogares)
    sexo, edad         -> personas, facpob07 (n en personas)
"""

from __future__ import annotations

import argparse
import sys
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from diseno import razon  # noqa: E402

AZUL = "#1F4E79"
ROJO = "#C0392B"
GRIS_IC = "#7f7f7f"
GRIS_TEXTO = "#595959"
GRIS_GRILLA = "#ebebeb"

DEPARTAMENTOS = {
    "01": "Amazonas", "02": "Áncash", "03": "Apurímac", "04": "Arequipa",
    "05": "Ayacucho", "06": "Cajamarca", "07": "Callao", "08": "Cusco",
    "09": "Huancavelica", "10": "Huánuco", "11": "Ica", "12": "Junín",
    "13": "La Libertad", "14": "Lambayeque", "15": "Lima", "16": "Loreto",
    "17": "Madre de Dios", "18": "Moquegua", "19": "Pasco", "20": "Piura",
    "21": "Puno", "22": "San Martín", "23": "Tacna", "24": "Tumbes",
    "25": "Ucayali",
}
EDADES = ["0-17", "18-29", "30-44", "45-64", "65+"]
EDAD_TEXTO = {"0-17": "0 a 17 años", "18-29": "18 a 29 años", "30-44": "30 a 44 años",
              "45-64": "45 a 64 años", "65+": "65 años a más"}

# Configuración de cada corte: base, columna, etiquetas, orden y frases para el título.
CORTES = {
    "area": {"base": "hogares", "col": "area", "orient": "v", "orden": "valor",
             "etiquetas": {"rural": "Rural", "urbano": "Urbana"},
             "frase": {"rural": "el área rural", "urbano": "el área urbana"},
             "grupo_txt": "área de residencia", "xlabel": None, "indicadores": "area_contraste"},
    "sexo": {"base": "personas", "col": "sexo", "orient": "v", "orden": "valor",
             "etiquetas": {"mujer": "Mujer", "hombre": "Hombre"},
             "frase": {"mujer": "mujeres", "hombre": "hombres"},
             "grupo_txt": "sexo", "xlabel": None, "indicadores": "sexo"},
    "edad": {"base": "personas", "col": "grupo_edad", "orient": "v", "orden": EDADES,
             "etiquetas": {e: e for e in EDADES}, "frase": EDAD_TEXTO,
             "grupo_txt": "grupo de edad", "xlabel": "Grupo de edad (n = personas en la muestra)",
             "indicadores": None},
    "departamento": {"base": "hogares", "col": "departamento", "orient": "h", "orden": "valor",
                     "etiquetas": DEPARTAMENTOS, "frase": DEPARTAMENTOS,
                     "grupo_txt": "departamento", "xlabel": None,
                     "indicadores": "departamento_contraste"},
}
METODO = {"hogares": "factor07 × mieperho (sumaria de hogares)", "personas": "facpob07 (personas)"}
NOTA_PERSONAS = "La pobreza monetaria se mide por hogar: todos sus miembros comparten la condición del hogar."


# ------------------------------------------------------------------ estimación
def cargar(salidas: Path, anio: int) -> dict[str, pd.DataFrame]:
    rutas = {"personas": salidas / f"personas_{anio}.parquet", "hogares": salidas / f"hogares_{anio}.parquet"}
    for r in rutas.values():
        if not r.exists():
            sys.exit(f"ERROR: no existe {r}. Usa primero la skill limpiando-enaho "
                     f"(uv run python .claude/skills/limpiando-enaho/scripts/limpiar.py --anio {anio}).")
    bases = {k: pd.read_parquet(v) for k, v in rutas.items()}
    for df in bases.values():
        df["estrato_diseno"] = df["departamento"].astype(str) + "-" + df["estrato"].astype(str)
        df["uno"] = 1.0
    p = bases["personas"]
    p["grupo_edad"] = pd.cut(p["p208a"], bins=[0, 18, 30, 45, 65, 200], right=False,
                             labels=EDADES).astype(str)
    return bases


def estimar(df: pd.DataFrame, base: str, ind: str, dominio=None) -> dict:
    if base == "personas":
        return razon(df, ind, "uno", "facpob07", dominio)
    df = df.assign(_y=df[ind].astype(float) * df["mieperho"])
    return razon(df, "_y", "mieperho", "factor07", dominio)


def tabla(bases, por: str, ind: str) -> tuple[pd.DataFrame, dict]:
    c = CORTES[por]
    df = bases[c["base"]]
    filas = []
    for cod in sorted(df[c["col"]].astype(str).unique()):
        r = estimar(df, c["base"], ind, df[c["col"]].astype(str) == cod)
        filas.append({"codigo": cod, "categoria": c["etiquetas"].get(cod, cod), **r})
    t = pd.DataFrame(filas)
    if c["orden"] == "valor":
        t = t.sort_values("estimacion", ascending=False)
    else:
        t = t.set_index("codigo").loc[c["orden"]].reset_index()
    nac = estimar(df, c["base"], ind)
    return t.reset_index(drop=True), nac


# ------------------------------------------------------------------ textos
def se_superponen(a, b) -> bool:
    return not (a["ic_inf"] > b["ic_sup"] or b["ic_inf"] > a["ic_sup"])


def textos(t: pd.DataFrame, nac: dict, por: str, nombre_ind: str) -> tuple[str, str]:
    c = CORTES[por]
    fr = c["frase"]
    hi = t.loc[t["estimacion"].idxmax()]
    lo = t.loc[t["estimacion"].idxmin()]
    solapan = se_superponen(hi, lo)
    if len(t) == 2:
        if solapan:
            titulo = (f"{nombre_ind}: sin diferencia estadísticamente clara entre {fr[hi.codigo]} "
                      f"({hi.estimacion:.1f} %) y {fr[lo.codigo]} ({lo.estimacion:.1f} %)")
            lectura = "Lectura: los IC 95 % se superponen; la diferencia no es estadísticamente clara."
        else:
            dif = hi.estimacion - lo.estimacion
            titulo = (f"{nombre_ind}: {dif:.1f} puntos porcentuales más alta en {fr[hi.codigo]} "
                      f"({hi.estimacion:.1f} %) que en {fr[lo.codigo]} ({lo.estimacion:.1f} %)")
            lectura = "Lectura: los IC 95 % no se superponen; la diferencia es estadísticamente clara."
        return titulo, lectura

    if por == "departamento":
        # Un cociente con base casi nula (o cuyo IC toca 0) exagera: ahí se informa el rango.
        if lo.ic_inf > 0.5 and hi.estimacion / lo.estimacion <= 20:
            titulo = (f"{nombre_ind}: {fr[hi.codigo]} ({hi.estimacion:.1f} %) multiplica por "
                      f"{hi.estimacion / lo.estimacion:.1f} a {fr[lo.codigo]} ({lo.estimacion:.1f} %)")
        else:
            titulo = (f"{nombre_ind}: va de {lo.estimacion:.1f} % en {fr[lo.codigo]} "
                      f"a {hi.estimacion:.1f} % en {fr[hi.codigo]}")
        unidad = "departamentos"
    else:
        if solapan:
            titulo = (f"{nombre_ind}: sin diferencias estadísticamente claras entre grupos de edad "
                      f"({lo.estimacion:.1f} % a {hi.estimacion:.1f} %)")
        else:
            titulo = (f"{nombre_ind}: más alta entre las personas de {fr[hi.codigo]} "
                      f"({hi.estimacion:.1f} %) y más baja entre las de {fr[lo.codigo]} ({lo.estimacion:.1f} %)")
        unidad = "grupos de edad"
    arriba = int((t["ic_inf"] > nac["estimacion"]).sum())
    abajo = int((t["ic_sup"] < nac["estimacion"]).sum())
    incluyen = len(t) - arriba - abajo
    def num(k, sing, plur):
        return f"{k} {sing if k == 1 else plur}"

    lectura = (f"Lectura: de {len(t)} {unidad}, {num(arriba, 'tiene', 'tienen')} el IC 95 % por encima "
               f"del promedio Perú, {abajo} por debajo y {num(incluyen, 'lo incluye', 'lo incluyen')}.")
    return titulo, lectura


# ------------------------------------------------------------------ figura
def graficar(t: pd.DataFrame, nac: dict, por: str, ind_txt: str, anio: int, salida: Path) -> Path:
    c = CORTES[por]
    base = c["base"]
    unidad_n = "hogares" if base == "hogares" else "personas"
    titulo, lectura = textos(t, nac, por, ind_txt)
    subtitulo = (f"{ind_txt} según {c['grupo_txt']}, Perú {anio}, % de personas. "
                 f"Líneas grises: IC 95 %.\n{lectura}")
    nota = (f"Fuente: INEI, ENAHO {anio} (módulos 34 y 02). Estimación ponderada con {METODO[base]}. "
            "IC 95 % por linealización (UPM = conglome; estratos = departamento × estrato). Elaboración propia.")
    if base == "personas":
        nota += " " + NOTA_PERSONAS
    vertical = c["orient"] == "v"
    tope = max(t["ic_sup"].max(), nac["estimacion"]) * 1.15  # margen para que nada quede pegado

    if vertical:
        fig, ax = plt.subplots(figsize=(8.5, 6.2), facecolor="white")
        x = range(len(t))
        # Si el eje X ya dice la unidad de n (edad), la etiqueta solo lleva el número.
        sufijo_n = "" if c["xlabel"] else f" {unidad_n}"
        etiquetas = [f"{r.categoria}\n(n = {r.n:,}{sufijo_n})" for r in t.itertuples()]
        ax.bar(x, t["estimacion"], width=0.68, color=AZUL, zorder=2)
        ax.errorbar(x, t["estimacion"], yerr=[t["estimacion"] - t["ic_inf"].clip(lower=0),
                                              t["ic_sup"] - t["estimacion"]],
                    fmt="none", ecolor=GRIS_IC, elinewidth=1.6, capsize=8, capthick=1.6, zorder=3)
        for i, r in enumerate(t.itertuples()):
            if r.estimacion >= tope * 0.12:
                ax.text(i, tope * 0.025, f"{r.estimacion:.1f} %", ha="center", va="bottom",
                        color="white", fontweight="bold", fontsize=11, zorder=4,
                        bbox={"facecolor": AZUL, "edgecolor": "none", "pad": 1.5})
            else:
                ax.text(i, r.ic_sup + tope * 0.02, f"{r.estimacion:.1f} %", ha="center", va="bottom",
                        color="black", fontweight="bold", fontsize=11, zorder=4,
                        bbox={"facecolor": "white", "edgecolor": "none", "pad": 1.5})
        ax.axhline(nac["estimacion"], ls="--", color=ROJO, lw=1.6, zorder=3,
                   label=f"Promedio Perú: {nac['estimacion']:.1f} %")
        ax.set_xticks(list(x), etiquetas, fontsize=10)
        ax.set_ylim(0, tope)
        ax.set_ylabel("% de personas", fontsize=10, color=GRIS_TEXTO)
        if c["xlabel"]:
            ax.set_xlabel(c["xlabel"], fontsize=10, color=GRIS_TEXTO, labelpad=8)
        ax.yaxis.grid(True, color=GRIS_GRILLA, linewidth=0.9, zorder=0)
        ax.legend(loc="upper right", frameon=False, fontsize=10)
        ancho_texto = 80
    else:
        fig, ax = plt.subplots(figsize=(10, 11.5), facecolor="white")
        t = t.iloc[::-1].reset_index(drop=True)  # la mayor queda arriba
        y = range(len(t))
        etiquetas = [f"{r.categoria} (n = {r.n:,} {unidad_n})" for r in t.itertuples()]
        ax.barh(y, t["estimacion"], height=0.74, color=AZUL, zorder=2)
        ax.errorbar(t["estimacion"], y, xerr=[t["estimacion"] - t["ic_inf"].clip(lower=0),
                                              t["ic_sup"] - t["estimacion"]],
                    fmt="none", ecolor=GRIS_IC, elinewidth=1.4, capsize=4, capthick=1.4, zorder=3)
        for i, r in enumerate(t.itertuples()):
            if r.estimacion >= tope * 0.14:
                ax.text(min(r.estimacion, r.ic_inf) - tope * 0.012, i, f"{r.estimacion:.1f} %", ha="right",
                        va="center", color="white", fontweight="bold", fontsize=9.5, zorder=4,
                        bbox={"facecolor": AZUL, "edgecolor": "none", "pad": 1.5})  # tapa la línea roja
            else:
                ax.text(r.ic_sup + tope * 0.012, i, f"{r.estimacion:.1f} %", ha="left", va="center",
                        color="black", fontweight="bold", fontsize=9.5, zorder=4,
                        bbox={"facecolor": "white", "edgecolor": "none", "pad": 1.5})
        ax.axvline(nac["estimacion"], ls="--", color=ROJO, lw=1.6, zorder=3,
                   label=f"Promedio Perú: {nac['estimacion']:.1f} %")
        ax.set_yticks(list(y), etiquetas, fontsize=9.5)
        ax.set_ylim(-0.6, len(t) - 0.4)
        ax.set_xlim(0, tope)
        ax.set_xlabel("% de personas", fontsize=10, color=GRIS_TEXTO)
        ax.xaxis.grid(True, color=GRIS_GRILLA, linewidth=0.9, zorder=0)
        ax.legend(loc="lower right", frameon=False, fontsize=10)
        ancho_texto = 95

    ax.set_facecolor("white")
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color("#bfbfbf")
    ax.tick_params(colors="#333333", length=0)
    ax.set_axisbelow(True)

    fig.tight_layout(rect=(0, 0.07 if vertical else 0.045, 1, 0.80 if vertical else 0.915))
    izq = 0.01
    fig.text(izq, 0.995, textwrap.fill(titulo, ancho_texto - 18), ha="left", va="top",
             fontsize=14, fontweight="bold", color="black")
    alto_titulo = 0.055 * (titulo.count(" ") > 0) * len(textwrap.wrap(titulo, ancho_texto - 18))
    fig.text(izq, 0.995 - (alto_titulo if vertical else alto_titulo * 0.55) - 0.005, subtitulo,
             ha="left", va="top", fontsize=10, color=GRIS_TEXTO, linespacing=1.4)
    fig.text(izq, 0.005, textwrap.fill(nota, ancho_texto + 30), ha="left", va="bottom",
             fontsize=7.5, color=GRIS_TEXTO)
    salida.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(salida, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return salida


# ------------------------------------------------------------------ control
def controlar(t: pd.DataFrame, nac: dict, por: str, ind: str, salidas: Path) -> None:
    """Lo graficado debe coincidir con salidas/indicadores.csv (mismo método)."""
    if ind != "pobre":
        return
    ref = pd.read_csv(salidas / "indicadores.csv", dtype={"codigo": str})
    grupo = CORTES[por]["indicadores"]
    if grupo:
        r = ref.loc[ref.grupo == grupo].set_index("codigo")["pobreza_pct"]
        dif = (t.set_index("codigo")["estimacion"].round(2) - r.reindex(t["codigo"])).abs().max()
        if not dif <= 0.01:
            sys.exit(f"ERROR: la pobreza por {por} no coincide con indicadores.csv (dif. {dif}).")
    nac_grupo = "nacional_contraste" if CORTES[por]["base"] == "hogares" else "nacional"
    r_nac = float(ref.loc[ref.grupo == nac_grupo, "pobreza_pct"].iloc[0])
    if abs(round(nac["estimacion"], 2) - r_nac) > 0.01:
        sys.exit(f"ERROR: el promedio Perú ({nac['estimacion']:.2f}) no coincide con indicadores.csv ({r_nac}).")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--por", choices=[*CORTES, "todos"], default="todos")
    ap.add_argument("--indicador", choices=["pobreza", "extrema"], default="pobreza")
    ap.add_argument("--anio", type=int, default=2024)
    ap.add_argument("--salidas", type=Path, default=Path("salidas"))
    ap.add_argument("--figuras", type=Path, default=Path("figuras"))
    a = ap.parse_args()

    bases = cargar(a.salidas, a.anio)
    ind = "pobre" if a.indicador == "pobreza" else "pobre_extremo"
    ind_txt = "Pobreza monetaria" if a.indicador == "pobreza" else "Pobreza extrema"
    sufijo = "" if a.indicador == "pobreza" else "_extrema"

    for por in (CORTES if a.por == "todos" else [a.por]):
        t, nac = tabla(bases, por, ind)
        if por == "departamento" and len(t) != 25:
            sys.exit(f"ERROR: se esperaban 25 departamentos y hay {len(t)}.")
        controlar(t, nac, por, ind, a.salidas)
        base = CORTES[por]["base"]
        datos = t.assign(
            indicador=a.indicador, metodo=METODO[base],
            unidad_n="hogares" if base == "hogares" else "personas",
            promedio_peru=nac["estimacion"], promedio_peru_ic_inf=nac["ic_inf"],
            promedio_peru_ic_sup=nac["ic_sup"],
        ).round(3)
        csv = a.salidas / f"grafico_por_{por}{sufijo}_{a.anio}.csv"
        datos.to_csv(csv, index=False, encoding="utf-8")
        png = a.figuras / f"pobreza{sufijo}_{por}_{a.anio}.png"
        graficar(t, nac, por, ind_txt, a.anio, png)
        print(f"Guardado: {png} y {csv}")
        print(datos[["categoria", "estimacion", "ic_inf", "ic_sup", "n"]].round(2).to_string(index=False))
        if t["upm_unica"].max():
            print(f"  Nota: {int(t['upm_unica'].max())} estrato con una sola UPM, centrado en la media general.")


if __name__ == "__main__":
    main()
