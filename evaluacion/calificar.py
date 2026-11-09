"""Califica los registros del experimento y genera evaluacion/resultados.csv.

La corrección la decide este script con reglas fijas (documentadas en
evaluacion/comparacion.md, sección «Regla de calificación»):

1. Se toma la última línea de la respuesta final que empiece con «RESPUESTA:»
   (se ignoran asteriscos o símbolos de formato). Si no existe: «sin respuesta».
2. De esa línea se quitan las fechas (mes con o sin año, p. ej. «junio 2022»,
   «dic-2024») y los años sueltos (1990-2035 sin decimales); los meses
   quitados se guardan para las preguntas que piden un mes.
3. Se extraen los números restantes en orden (coma o punto decimal, signo
   menos incluido; no cuentan los dígitos pegados a letras, como PN01273PM).
   El primer número se compara con la primera cifra esperada, el segundo con
   la segunda, etc., cada uno con su tolerancia. Menos números que cifras
   esperadas: incorrecta (falta cifra). Más números: incorrecta (ambigua).
4. Mes esperado: debe aparecer exactamente un mes, con ese nombre y año.
   Departamento esperado: debe aparecer exactamente un departamento y ser
   ese. Un mes o departamento extra hace la respuesta ambigua.
5. Combinadas: además, el texto completo no debe afirmar causalidad (lista
   de expresiones causales; no cuenta si va precedida de una negación).

Uso:  uv run evaluacion/calificar.py                     # corrida oficial (A y B)
      uv run evaluacion/calificar.py --b2                # complementaria (B2)
"""

import argparse
import csv
import json
import re
import unicodedata
from pathlib import Path

EVAL = Path(__file__).resolve().parent
REGISTROS = EVAL / "registros"

MESES = {
    "enero": 1, "ene": 1, "febrero": 2, "feb": 2, "marzo": 3, "mar": 3,
    "abril": 4, "abr": 4, "mayo": 5, "may": 5, "junio": 6, "jun": 6,
    "julio": 7, "jul": 7, "agosto": 8, "ago": 8, "septiembre": 9,
    "setiembre": 9, "sep": 9, "set": 9, "octubre": 10, "oct": 10,
    "noviembre": 11, "nov": 11, "diciembre": 12, "dic": 12,
}
DEPARTAMENTOS = [
    "amazonas", "ancash", "apurimac", "arequipa", "ayacucho", "cajamarca",
    "callao", "cusco", "cuzco", "huancavelica", "huanuco", "ica", "junin",
    "la libertad", "lambayeque", "lima", "loreto", "madre de dios", "moquegua",
    "pasco", "piura", "puno", "san martin", "tacna", "tumbes", "ucayali",
]

RE_MES = re.compile(
    r"\b(" + "|".join(sorted(MESES, key=len, reverse=True)) + r")\b\.?"
    r"(?:\s*(?:de|del)?\s*[-/.]?\s*((?:19|20)\d\d))?"
)
RE_ANIO = re.compile(r"(?<![\w.,])(?:199\d|20[0-3]\d)(?![\w]|[.,]\d)")
RE_NUM = re.compile(r"(?<![\w.,])-?\d+(?:[.,]\d+)?(?![\w])")
RE_CAUSAL = re.compile(
    r"\b(caus[oó]|causa(?:n|ron|do|da)?|provoc\w*|origin[oó]|gener[oó]|"
    r"debido a|a consecuencia|como consecuencia|se tradujo|llev[oó] a|"
    r"contribuy\w*|impuls[oó]|explica(?:n|ría|ria)?|determin[oó]|"
    r"increment[oó] la pobreza|redujo la pobreza|aument[oó] la pobreza)\b"
)
RE_NEGACION = re.compile(r"\b(no|sin|ni|nunca|tampoco|evitar)\b")


def normalizar(texto: str) -> str:
    """Minúsculas, sin tildes, con guion ASCII."""
    texto = texto.replace("−", "-").replace("–", "-").replace("—", "-")
    sin_tildes = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in sin_tildes if not unicodedata.combining(c)).lower()


def leer_registro(ruta: Path) -> dict:
    """Extrae texto final, herramientas, fuentes, tiempo y errores del stream-json."""
    info = {"texto": "", "herramientas": [], "fuentes": [], "errores": [],
            "tiempo": None}
    usos = {}
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        if not linea.strip():
            continue
        m = json.loads(linea)
        tipo = m.get("type")
        if tipo == "assistant":
            for c in m["message"]["content"]:
                if c["type"] != "tool_use":
                    continue
                nombre, entrada = c["name"], c["input"]
                usos[c["id"]] = nombre
                info["herramientas"].append(nombre)
                if nombre.startswith("mcp__bcrp__"):
                    cod = entrada.get("codigo") or entrada.get("codigo_x") or entrada.get("consulta") or ""
                    info["fuentes"].append(f"MCP bcrp {nombre.split('__')[-1]} {cod}".strip())
                elif nombre == "Skill":
                    info["fuentes"].append(f"Skill {entrada.get('skill', '')}")
                elif nombre == "Read":
                    info["fuentes"].append(f"Read {Path(entrada.get('file_path', '')).name}")
                elif nombre == "Bash":
                    info["fuentes"].append(f"Bash {entrada.get('command', '')[:80]}")
        elif tipo == "user" and isinstance(m["message"]["content"], list):
            for c in m["message"]["content"]:
                if c.get("type") == "tool_result" and c.get("is_error"):
                    txt = c["content"] if isinstance(c["content"], str) else json.dumps(c["content"], ensure_ascii=False)
                    info["errores"].append(f"error en {usos.get(c['tool_use_id'], '?')}: {txt[:120]}")
        elif tipo == "result":
            info["texto"] = m.get("result") or ""
            if m.get("duration_ms") is not None:
                info["tiempo"] = round(m["duration_ms"] / 1000, 1)
            if m.get("is_error"):
                info["errores"].append(f"sesión terminó con error ({m.get('subtype')})")
            for d in m.get("permission_denials") or []:
                info["errores"].append(f"permiso denegado: {d['tool_name']}")
    return info


def linea_respuesta(texto: str) -> str | None:
    candidatas = []
    for linea in texto.splitlines():
        limpia = re.sub(r"^[\s*_#>`-]+", "", linea)
        if re.match(r"(?i)respuesta\s*[*_]*\s*:", limpia):
            candidatas.append(re.sub(r"(?i)^respuesta\s*[*_]*\s*:\s*[*_]*", "", limpia).strip(" *_`"))
    return candidatas[-1] if candidatas else None


def esperadas(fila: dict) -> tuple[list[tuple[float, float]], list[str]]:
    """Separa las cifras esperadas (con su tolerancia) de los nombres esperados."""
    valores = [v.strip() for v in fila["respuesta_esperada"].split(";")]
    tolerancias = [float(t) for t in re.findall(r"±\s*([\d.]+)", fila["tolerancia"])]
    numeros, nombres = [], []
    for v in valores:
        try:
            numeros.append(float(v))
        except ValueError:
            nombres.append(normalizar(v))
    if len(tolerancias) != len(numeros):
        raise ValueError(f"{fila['id']}: tolerancias y cifras no coinciden")
    return list(zip(numeros, tolerancias)), nombres


def calificar(fila: dict, linea: str, texto: str) -> tuple[bool, list[str]]:
    motivos = []
    norm = normalizar(linea)
    cifras, nombres = esperadas(fila)

    meses = [(MESES[m.group(1)], m.group(2)) for m in RE_MES.finditer(norm)]
    resto = RE_ANIO.sub(" ", RE_MES.sub(" ", norm))
    numeros = [float(n.replace(",", ".")) for n in RE_NUM.findall(resto)]

    if len(numeros) < len(cifras):
        motivos.append(f"falta cifra ({len(numeros)} de {len(cifras)})")
    elif len(numeros) > len(cifras):
        motivos.append(f"ambigua: {len(numeros)} números para {len(cifras)} cifras esperadas")
    else:
        for (esp, tol), obt in zip(cifras, numeros):
            if abs(obt - esp) > tol + 1e-9:
                motivos.append(f"{obt} fuera de tolerancia ({esp} ± {tol})")

    for nombre in nombres:
        partes = nombre.split()
        if partes[0] in MESES:  # mes con año, p. ej. «junio 2022»
            esp = (MESES[partes[0]], partes[1] if len(partes) > 1 else None)
            if len(meses) != 1:
                motivos.append(f"se esperaba un mes y hay {len(meses)}")
            elif meses[0] != esp:
                motivos.append(f"mes incorrecto: {meses[0]} en vez de {esp}")
        else:  # departamento
            hallados = [d for d in DEPARTAMENTOS if re.search(rf"\b{d}\b", norm)]
            if hallados != [nombre]:
                motivos.append(f"departamento: se halló {hallados or 'ninguno'}, se esperaba {nombre}")

    if fila["tipo"] == "combinada":
        texto_norm = normalizar(texto)
        for m in RE_CAUSAL.finditer(texto_norm):
            previo = texto_norm[max(0, m.start() - 60):m.start()]
            if not RE_NEGACION.search(previo):
                inicio = max(0, m.start() - 40)
                motivos.append(f"afirma causalidad: «…{texto_norm[inicio:m.end() + 30].strip()}…»")
                break
    return not motivos, motivos


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--b2", action="store_true", help="califica la corrida complementaria B2")
    args = ap.parse_args()
    modos = ("B2",) if args.b2 else ("A", "B")
    registros = EVAL / "registros_b2" if args.b2 else REGISTROS
    salida = EVAL / ("resultados_b2.csv" if args.b2 else "resultados.csv")

    with open(EVAL / "preguntas.csv", encoding="utf-8") as f:
        preguntas = list(csv.DictReader(f))
    filas = []
    for modo in modos:
        for p in preguntas:
            ruta = registros / f"{modo}_{p['id']}.jsonl"
            if not ruta.exists():
                continue
            info = leer_registro(ruta)
            meta_ruta = ruta.with_name(f"{modo}_{p['id']}.meta.json")
            meta = json.loads(meta_ruta.read_text(encoding="utf-8")) if meta_ruta.exists() else {}
            if meta.get("error"):
                info["errores"].append(meta["error"])
            linea = linea_respuesta(info["texto"])
            if linea is None:
                correcta, motivos, generada = False, ["sin respuesta (no hay línea RESPUESTA)"], "sin respuesta"
            else:
                correcta, motivos = calificar(p, linea, info["texto"])
                generada = linea
            filas.append({
                "modo": modo, "id": p["id"], "pregunta": p["pregunta"],
                "respuesta_esperada": p["respuesta_esperada"],
                "respuesta_generada": generada,
                "fuente_usada": " | ".join(dict.fromkeys(info["fuentes"])) or "memoria del modelo (sin herramientas)",
                "herramientas_usadas": " | ".join(
                    f"{h}×{info['herramientas'].count(h)}" for h in dict.fromkeys(info["herramientas"])) or "ninguna",
                "correcta": "sí" if correcta else "no",
                "tiempo_segundos": info["tiempo"] if info["tiempo"] is not None else meta.get("tiempo_reloj_s"),
                "errores": " | ".join(motivos + info["errores"]),
            })
    with open(salida, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)
    for modo in modos:
        sub = [f for f in filas if f["modo"] == modo]
        ok = sum(f["correcta"] == "sí" for f in sub)
        print(f"Modo {modo}: {ok}/{len(sub)} correctas")


if __name__ == "__main__":
    main()
