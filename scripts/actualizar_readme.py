"""Inserta en README.md las cifras leídas de los archivos, para que ninguna se escriba a mano.

Reemplaza el texto entre cada par de marcadores <!-- <bloque>:inicio --> y <!-- <bloque>:fin -->:
  - pruebas:    resultado de salidas/pruebas_mcp.txt;
  - validacion: salidas/validacion.txt copiado tal cual y las filas nacional, área y sexo de
                salidas/indicadores.csv;
  - evaluacion: correctas y tiempos por modo de evaluacion/resultados.csv (A y B) y
                evaluacion/resultados_b2.csv (análisis complementario B2).

Uso (desde la raíz del proyecto):
    uv run python scripts/actualizar_readme.py
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cifras  # noqa: E402

AVISO = "<!-- Generado por scripts/actualizar_readme.py; no editar a mano. -->"
NOMBRE_MODO = {"A": "A · sin MCP ni Skills", "B": "B · con MCP y Skills (oficial)",
               "B2": "B2 · con MCP y Skills, sin cifras precalculadas de la ENAHO"}


def bloque_pruebas() -> list[str]:
    p = cifras.pruebas_mcp()
    return [f"Última corrida (`{p['origen']}`): **{p['aprobadas']} de {p['total']} pruebas aprobadas**.",
            "", "```text", p["linea"], "```"]


def bloque_validacion() -> list[str]:
    ind_path = cifras.RAIZ / "salidas/indicadores.csv"
    if not ind_path.exists():
        sys.exit("ERROR: falta salidas/indicadores.csv. Corre primero la skill limpiando-enaho.")
    ind = pd.read_csv(ind_path, dtype={"codigo": str})
    filas = ind[ind["grupo"].isin(["nacional", "area", "sexo", "nacional_contraste", "area_contraste"])]
    tabla = ["| Grupo | Categoría | Pobreza (%) | Pobreza extrema (%) | Ponderador | n muestra |",
             "|---|---|---|---|---|---|"]
    for _, f in filas.iterrows():
        tabla.append(f"| {f.grupo} | {f.categoria} | {f.pobreza_pct:.2f} | {f.pobreza_extrema_pct:.2f} "
                     f"| `{f.ponderador}` | {f.n_muestra:,} |")
    return ["Contenido de `salidas/validacion.txt`:", "", "```text",
            (cifras.RAIZ / cifras.VALIDACION).read_text(encoding="utf-8").rstrip(), "```", "",
            "Indicadores principales (`salidas/indicadores.csv`; los 25 departamentos están en ese archivo):",
            "", *tabla]


def bloque_evaluacion() -> list[str]:
    e = cifras.evaluacion()
    tabla = ["| Modo | Correctas | Incorrectas | Tiempo promedio (s) | Mediana (s) | Archivo |",
             "|---|---|---|---|---|---|"]
    for df, origen in ((e["oficial"], e["origen"]), (e["b2"], e["origen_b2"])):
        for modo, f in df.iterrows():
            tabla.append(f"| {NOMBRE_MODO.get(modo, modo)} | **{f.correctas} / {f.preguntas}** | "
                         f"{f.incorrectas} | {f.tiempo_promedio:.1f} | {f.tiempo_mediana:.1f} | `{origen}` |")
    return [*tabla, "",
            f"En las mismas {e['n_b2']} preguntas que B2 (ENAHO y combinadas), el Modo B oficial tuvo "
            f"{e['b_en_preguntas_b2']} / {e['n_b2']} correctas (`{e['origen']}`)."]


BLOQUES = {"pruebas": bloque_pruebas, "validacion": bloque_validacion, "evaluacion": bloque_evaluacion}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    readme = cifras.RAIZ / "README.md"
    texto = readme.read_text(encoding="utf-8")
    for nombre, generar in BLOQUES.items():
        inicio, fin = f"<!-- {nombre}:inicio -->", f"<!-- {nombre}:fin -->"
        if texto.count(inicio) != 1 or texto.count(fin) != 1:
            sys.exit(f"ERROR: README.md debe tener una vez cada marcador del bloque '{nombre}'.")
        antes, resto = texto.split(inicio)
        _, despues = resto.split(fin)
        texto = antes + "\n".join([inicio, AVISO, "", *generar(), fin]) + despues
    readme.write_text(texto, encoding="utf-8")
    print("README.md actualizado: bloques " + ", ".join(BLOQUES))


if __name__ == "__main__":
    main()
