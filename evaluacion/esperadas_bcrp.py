"""Respuestas esperadas de las preguntas BCRP de la evaluación (Parte 4).

Script independiente: consulta directamente la API pública del BCRP con la
biblioteca estándar. No importa ni usa mcp/server.py, para que la referencia
no dependa del sistema que se está evaluando.

Uso:  uv run evaluacion/esperadas_bcrp.py
"""

import json
import urllib.request

API = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api/{codigo}/json/{ini}/{fin}/esp"

MESES = {
    "Ene": "enero", "Feb": "febrero", "Mar": "marzo", "Abr": "abril",
    "May": "mayo", "Jun": "junio", "Jul": "julio", "Ago": "agosto",
    "Sep": "septiembre", "Set": "septiembre", "Oct": "octubre",
    "Nov": "noviembre", "Dic": "diciembre",
}


def descargar(codigo: str, ini: str, fin: str) -> dict[str, float]:
    """Devuelve {'Dic.2024': valor, ...} de una serie mensual del BCRP."""
    url = API.format(codigo=codigo, ini=ini, fin=fin)
    req = urllib.request.Request(url, headers={"User-Agent": "tarea4-evaluacion"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        texto = resp.read().decode("utf-8").lstrip()
    # A veces la API agrega un aviso HTML tras el JSON: se lee solo el objeto.
    datos, _ = json.JSONDecoder().raw_decode(texto)
    serie = {}
    for p in datos["periods"]:
        valor = p["values"][0]
        if valor not in ("n.d.", ""):
            serie[p["name"]] = float(valor)
    return serie


def mes_legible(periodo: str) -> str:
    """'Abr.2020' -> 'abril 2020'."""
    abrev, anio = periodo.split(".")
    return f"{MESES[abrev]} {anio}"


def main() -> None:
    inflacion = descargar("PN01273PM", "2020-1", "2024-12")
    pbi = descargar("PN01728AM", "2020-4", "2020-4")
    tc = descargar("PN01206PM", "2024-12", "2024-12")

    infl_dic24 = inflacion["Dic.2024"]
    mes_max, infl_max = max(inflacion.items(), key=lambda kv: kv[1])

    print("BCRP01 inflación Lima 12 meses dic-2024 (PN01273PM):", round(infl_dic24, 2), "%")
    print("BCRP02 máximo 2020-2024 (PN01273PM):", round(infl_max, 2), "% en", mes_legible(mes_max))
    print("BCRP03 PBI var. interanual abr-2020 (PN01728AM):", round(pbi["Abr.2020"], 2), "%")
    print("BCRP04 tipo de cambio venta promedio dic-2024 (PN01206PM):", round(tc["Dic.2024"], 3), "S/ por US$")


if __name__ == "__main__":
    main()
