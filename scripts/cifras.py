"""Lee las cifras del README desde los archivos del repositorio.

Lo usa scripts/actualizar_readme.py, para que ninguna cifra del
README se escriba a mano. Cada función devuelve el valor y el archivo y la línea
de donde salió, para poder mostrar el origen.

Si un archivo no tiene el formato esperado, se detiene con un error en vez de inventar un valor.
"""
import re
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
PRUEBAS = "salidas/pruebas_mcp.txt"
VALIDACION = "salidas/validacion.txt"
RESULTADOS = "evaluacion/resultados.csv"
RESULTADOS_B2 = "evaluacion/resultados_b2.csv"
INFORME = "informes/informe_final.md"


def _leer(ruta: str) -> str:
    p = RAIZ / ruta
    if not p.exists():
        sys.exit(f"ERROR: falta {ruta}.")
    return p.read_text(encoding="utf-8")


def _buscar(ruta: str, patron: str) -> tuple[re.Match, str]:
    """Primera línea de `ruta` que cumple `patron`; devuelve el match y la línea."""
    for linea in _leer(ruta).splitlines():
        m = re.search(patron, linea)
        if m:
            return m, linea.strip()
    sys.exit(f"ERROR: no se encontró /{patron}/ en {ruta}.")


def pruebas_mcp() -> dict:
    """Pruebas aprobadas y totales según la línea final de pytest."""
    m, linea = _buscar(PRUEBAS, r"=+ (.*) in [\d.]+s =+")
    conteo = dict((k, int(v)) for v, k in re.findall(r"(\d+) (\w+)", m.group(1)))
    total = sum(conteo.values())
    return {"aprobadas": conteo.get("passed", 0), "total": total, "origen": PRUEBAS, "linea": linea}


def validacion_enaho() -> dict:
    """Pobreza nacional, residentes habituales, departamentos y resultado global de la validación."""
    pob, l_pob = _buscar(VALIDACION, r"Pobreza nacional \(sumaria.*?: ([\d.]+) %")
    pob_p, l_pob_p = _buscar(VALIDACION, r"Pobreza nacional \(personas.*?: ([\d.]+) %")
    res, l_res = _buscar(VALIDACION, r"Residentes habituales: ([\d,]+) de")
    dep, l_dep = _buscar(VALIDACION, r"\[APROBADA\] (\d+) códigos de departamento")
    tot, l_tot = _buscar(VALIDACION, r"Resultado: (\d+) de (\d+) verificaciones aprobadas")
    return {
        "pobreza_nacional": float(pob.group(1)), "linea_pobreza": l_pob,
        "pobreza_nacional_personas": float(pob_p.group(1)), "linea_pobreza_personas": l_pob_p,
        "residentes": int(res.group(1).replace(",", "")), "linea_residentes": l_res,
        "departamentos": int(dep.group(1)), "linea_departamentos": l_dep,
        "aprobadas": int(tot.group(1)), "verificaciones": int(tot.group(2)), "linea_total": l_tot,
        "origen": VALIDACION,
    }


def _resumen_modos(ruta: str) -> pd.DataFrame:
    d = pd.read_csv(RAIZ / ruta, encoding="utf-8")
    d["ok"] = d["correcta"].eq("sí")
    return d.groupby("modo", sort=False).agg(
        correctas=("ok", "sum"), preguntas=("ok", "size"),
        tiempo_promedio=("tiempo_segundos", "mean"), tiempo_mediana=("tiempo_segundos", "median"),
        incorrectas=("id", lambda s: ", ".join(s[~d.loc[s.index, "ok"]]) or "—"),
    )


def evaluacion() -> dict:
    """Correctas por modo en la corrida oficial (A y B) y en el análisis complementario B2."""
    oficial = _resumen_modos(RESULTADOS)
    b2 = _resumen_modos(RESULTADOS_B2)
    d = pd.read_csv(RAIZ / RESULTADOS, encoding="utf-8")
    ids_b2 = pd.read_csv(RAIZ / RESULTADOS_B2, encoding="utf-8")["id"]
    b_mismas = d[(d["modo"] == "B") & d["id"].isin(ids_b2)]
    return {
        "oficial": oficial, "b2": b2,
        "b_en_preguntas_b2": int(b_mismas["correcta"].eq("sí").sum()), "n_b2": len(ids_b2),
        "origen": RESULTADOS, "origen_b2": RESULTADOS_B2,
    }


def pregunta_investigacion() -> dict:
    _buscar(INFORME, r"^\*\*Pregunta\.\*\* ")  # falla con un mensaje claro si no está
    texto = _leer(INFORME)
    # La pregunta puede seguir en la línea siguiente: se toma hasta el signo de cierre.
    inicio = texto.index("**Pregunta.**") + len("**Pregunta.**")
    pregunta = " ".join(texto[inicio:texto.index("?", inicio) + 1].split())
    return {"pregunta": pregunta, "origen": INFORME}
