"""Inserta en README.md las cifras de validación de la Parte 2, leídas de los archivos.

Reemplaza el texto entre <!-- validacion:inicio --> y <!-- validacion:fin --> con:
  - salidas/validacion.txt copiado tal cual;
  - las filas nacional, área y sexo de salidas/indicadores.csv.
Así ninguna cifra del README se escribe a mano.

Uso (desde la raíz del proyecto):
    uv run python scripts/actualizar_readme.py
"""

import sys
from pathlib import Path

import pandas as pd

INICIO, FIN = "<!-- validacion:inicio -->", "<!-- validacion:fin -->"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    readme = Path("README.md")
    validacion = Path("salidas/validacion.txt")
    ind_path = Path("salidas/indicadores.csv")
    for p in (validacion, ind_path):
        if not p.exists():
            sys.exit(f"ERROR: falta {p}. Corre primero la skill limpiando-enaho.")

    ind = pd.read_csv(ind_path, dtype={"codigo": str})
    filas = ind[ind["grupo"].isin(["nacional", "area", "sexo", "nacional_contraste", "area_contraste"])]
    tabla = ["| Grupo | Categoría | Pobreza (%) | Pobreza extrema (%) | Ponderador | n muestra |",
             "|---|---|---|---|---|---|"]
    for _, f in filas.iterrows():
        tabla.append(f"| {f.grupo} | {f.categoria} | {f.pobreza_pct:.2f} | {f.pobreza_extrema_pct:.2f} "
                     f"| `{f.ponderador}` | {f.n_muestra:,} |")

    bloque = "\n".join([
        INICIO,
        "<!-- Generado por scripts/actualizar_readme.py; no editar a mano. -->",
        "",
        "Contenido de `salidas/validacion.txt`:",
        "",
        "```text",
        validacion.read_text(encoding="utf-8").rstrip(),
        "```",
        "",
        "Indicadores principales (`salidas/indicadores.csv`; los 25 departamentos están en ese archivo):",
        "",
        *tabla,
        FIN,
    ])
    texto = readme.read_text(encoding="utf-8")
    if texto.count(INICIO) != 1 or texto.count(FIN) != 1:
        sys.exit("ERROR: README.md debe tener una vez cada marcador de validación.")
    antes, resto = texto.split(INICIO)
    _, despues = resto.split(FIN)
    readme.write_text(antes + bloque + despues, encoding="utf-8")
    print("README.md actualizado con salidas/validacion.txt y salidas/indicadores.csv")


if __name__ == "__main__":
    main()
