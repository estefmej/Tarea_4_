"""Servidor MCP del BCRP. Empiecen aquí: buscar_series ya funciona; completen los TODO hasta que pasen las pruebas.

    uv run pytest                                           # el contrato: las 8 pruebas deben pasar
    uv run server.py                                        # el servidor, por stdio
    claude mcp add --scope project bcrp -- uv run server.py # conectarlo a Claude Code

Las cuentas las hace Python, no el modelo: así cada cifra sale de una llamada que se puede repetir.
"""
import re
import time
import unicodedata
from functools import cache
from pathlib import Path

import httpx
import pandas as pd
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

AQUI = Path(__file__).parent
CATALOGO = AQUI / "datos" / "catalogo_bcrp.csv"
URL_CATALOGO = "https://estadisticas.bcrp.gob.pe/estadisticas/series/metadata"
API = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api"
SOLO_LECTURA = {"readOnlyHint": True, "openWorldHint": True}

mcp = FastMCP("bcrp", instructions=(
    "Series oficiales del Banco Central de Reserva del Perú (BCRP). Primero busca el código con buscar_series; "
    "luego usa resumen para variaciones, promedios y extremos, serie para los datos y correlacion para ver si "
    "dos series se movieron juntas (asociación, no causa). La ficha de cada serie está en bcrp://serie/{codigo}. "
    "No calcules a mano: cita siempre el código de la serie, el periodo y la fuente."))


def _sin_tildes(s):
    return unicodedata.normalize("NFD", str(s).lower()).encode("ascii", "ignore").decode()


@cache
def catalogo():
    """El catálogo oficial: 17 mil series en unos 7 MB. Se baja una vez y queda en datos/."""
    if not CATALOGO.exists():
        CATALOGO.parent.mkdir(exist_ok=True)
        r = httpx.get(URL_CATALOGO, timeout=120)
        r.raise_for_status()
        CATALOGO.write_text(r.content.decode("latin-1"), encoding="utf-8")
    df = pd.read_csv(CATALOGO, sep=";", dtype=str).fillna("")
    df = df.rename(columns={"Código de serie": "codigo", "Categoría de serie": "categoria", "Grupo de serie": "grupo",
                            "Nombre de serie": "nombre", "Frecuencia": "frecuencia",
                            "Fecha de actualización": "actualizada", "Fecha de inicio": "inicio"})
    df["texto"] = (df.categoria + " " + df.grupo + " " + df.nombre).map(_sin_tildes)
    return df


def _ficha(codigo):
    fila = catalogo().query("codigo == @codigo")
    if fila.empty:
        raise ToolError(f"No existe el código de serie {codigo!r}. Búsquenlo con buscar_series.")
    f = fila.iloc[0]
    return {"codigo": f.codigo, "nombre": f"{f.grupo} - {f.nombre}", "categoria": f.categoria,
            "frecuencia": f.frecuencia, "inicio": f.inicio, "actualizada": f.actualizada}


@mcp.tool(annotations=SOLO_LECTURA)
def buscar_series(texto: str, frecuencia: str | None = None, limite: int = 10) -> list[dict]:
    """Busca series del BCRP por palabras: todas deben aparecer en la categoría, el grupo o el nombre.

    Ejemplos: "ipc 12 meses", "tipo de cambio interbancario venta", "reservas internacionales netas",
    "tasa de referencia", "cobre precio". frecuencia: "Diaria", "Mensual", "Trimestral" o "Anual".
    Devuelve el código, el nombre completo, la frecuencia y desde cuándo hay datos. Si no hay resultados,
    prueben con menos palabras.
    """
    df = catalogo()
    m = pd.Series(True, index=df.index)
    for palabra in _sin_tildes(texto).split():
        m &= df.texto.str.contains(re.escape(palabra))
    if frecuencia:
        m &= df.frecuencia.str.lower() == frecuencia.lower()
    # primero las series vigentes y, entre ellas, las de nombre más corto (las más generales)
    sel = df[m]
    orden = sel.assign(vieja=sel.actualizada < "2025", largo=(sel.grupo + sel.nombre).str.len())
    return [_ficha(c) for c in orden.sort_values(["vieja", "largo"]).head(limite).codigo]


# ---------------------------------------------------------------------------------------------------------------
# Fechas. La API del BCRP usa un formato para lo que se le PIDE y otro distinto para lo que DEVUELVE.
# Por eso hay dos funciones: _periodo_api traduce nuestro periodo al que pide la API y _normalizar_periodo
# traduce el que devuelve la API a uno estándar y ordenable. Los meses van en un diccionario propio, así
# el resultado no depende del idioma (locale) de la computadora.
# ---------------------------------------------------------------------------------------------------------------
MESES = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7, "ago": 8,
         "set": 9, "sep": 9,  # el BCRP usa ambas formas para setiembre
         "oct": 10, "nov": 11, "dic": 12}


def _anio_completo(aa):
    """Años de dos dígitos ("26" -> 2026, "97" -> 1997), con el mismo corte que Python usa en %y."""
    aa = int(aa)
    return 2000 + aa if aa < 69 else 1900 + aa


def _periodo_api(periodo, frecuencia, fin=False):
    """Lo que PIDE la API, según la frecuencia de la serie.

    Acepta "2025", "2025-03", "2025-03-15" o "2025-T1" y devuelve:
      Diaria -> "2025-03-15"   Mensual -> "2025-3"   Trimestral -> "2025-1"   Anual -> "2025"
    Si el periodo es menos preciso que la serie (p. ej. "2025" en una serie mensual), fin=False toma el
    inicio y fin=True el final ("2025" -> "2025-1" para desde y "2025-12" para hasta).
    """
    p = str(periodo).strip().upper()
    m = re.fullmatch(r"(\d{4})(?:-(T[1-4]|\d{1,2})(?:-(\d{1,2}))?)?", p)
    if not m:
        raise ToolError(f"Periodo {periodo!r} no válido. Usen 2025, 2025-03, 2025-03-15 o 2025-T1.")
    anio, medio, dia = int(m[1]), m[2], m[3]
    if medio and medio.startswith("T"):          # trimestre -> su primer o último mes
        mes = (int(medio[1]) - 1) * 3 + (3 if fin else 1)
    elif medio:
        mes = int(medio)
        if not 1 <= mes <= 12:
            raise ToolError(f"Mes fuera de rango en {periodo!r}.")
    else:
        mes = 12 if fin else 1
    f = frecuencia.lower()
    if f.startswith("diaria"):
        if dia is None:                          # sin día: primer o último día del mes
            dia = pd.Period(f"{anio}-{mes:02d}", "M").days_in_month if fin else 1
        return pd.Timestamp(anio, mes, int(dia)).strftime("%Y-%m-%d")
    if f.startswith("mensual"):
        return f"{anio}-{mes}"
    if f.startswith("trimestral"):
        return f"{anio}-{(mes - 1) // 3 + 1}"
    return str(anio)                             # anual


def _normalizar_periodo(nombre):
    """Lo que DEVUELVE la API, llevado a un formato estándar que se ordena bien como texto.

      "Ene.2025" -> "2025-01"    "Set.2025" -> "2025-09"    "01.Oct.26" -> "2026-10-01"
      "T1.25"    -> "2025-T1"    "2025"     -> "2025"
    """
    s = str(nombre).strip()
    if m := re.fullmatch(r"([A-Za-z]{3})\.(\d{4})", s):                 # mensual
        return f"{m[2]}-{MESES[m[1].lower()]:02d}"
    if m := re.fullmatch(r"(\d{1,2})\.([A-Za-z]{3})\.(\d{2,4})", s):    # diaria
        anio = int(m[3]) if len(m[3]) == 4 else _anio_completo(m[3])
        return f"{anio}-{MESES[m[2].lower()]:02d}-{int(m[1]):02d}"
    if m := re.fullmatch(r"T([1-4])\.(\d{2,4})", s, re.IGNORECASE):     # trimestral
        anio = int(m[2]) if len(m[2]) == 4 else _anio_completo(m[2])
        return f"{anio}-T{m[1]}"
    if re.fullmatch(r"\d{4}", s):                                       # anual
        return s
    raise ValueError(f"Formato de periodo del BCRP no reconocido: {nombre!r}")


@cache
def _descargar(url, intentos=4):
    """Pide JSON a la API. Si responde HTML (límite de pedidos), espera y reintenta. Guarda en caché."""
    for i in range(intentos):
        try:
            r = httpx.get(url, timeout=60, follow_redirects=True)
            if r.status_code == 200 and r.text.lstrip().startswith("{"):
                return r.json()
        except (httpx.HTTPError, ValueError):
            pass
        time.sleep(2 * (i + 1))
    raise ToolError(f"La API del BCRP no devolvió datos tras {intentos} intentos: {url}")


def _obtener(codigo, desde, hasta):
    """Ficha + datos de una serie, sin pasar por MCP (lo reutilizan serie, resumen y correlacion)."""
    ficha = _ficha(codigo.strip().upper())       # ToolError claro si el código no existe
    d, h = _periodo_api(desde, ficha["frecuencia"]), _periodo_api(hasta, ficha["frecuencia"], fin=True)
    url = f"{API}/{ficha['codigo']}/json/{d}/{h}"
    datos, omitidos = [], 0
    for p in _descargar(url).get("periods", []):
        valor = (p.get("values") or ["n.d."])[0]
        try:
            datos.append({"periodo": _normalizar_periodo(p["name"]), "valor": float(valor)})
        except (TypeError, ValueError):          # "n.d." y similares: no hay dato ese periodo
            omitidos += 1
    return {**ficha, "datos": datos, "omitidos": omitidos, "fuente": url}


@mcp.tool(annotations=SOLO_LECTURA)
def serie(codigo: str, desde: str, hasta: str) -> dict:
    """Datos de una serie del BCRP entre dos periodos (inclusive).

    codigo: el código de buscar_series, p. ej. "PN01273PM" (IPC, var. % 12 meses).
    desde / hasta: "2025", "2025-03", "2025-03-15" o "2025-T1"; se adaptan a la frecuencia de la serie.
    Devuelve el periodo normalizado ("2025-01", "2026-10-01", "2025-T1" o "2025") y el valor de cada dato,
    cuántos periodos sin dato ("n.d.") se omitieron y en "fuente" la URL exacta consultada: cítenla.
    """
    r = _obtener(codigo, desde, hasta)
    return {k: r[k] for k in ("codigo", "nombre", "frecuencia", "datos", "omitidos", "fuente")}


def _punto(df, i):
    return {"periodo": df.periodo.loc[i], "valor": float(df.valor.loc[i])}


@mcp.tool(annotations=SOLO_LECTURA)
def resumen(codigo: str, desde: str, hasta: str) -> dict:
    """Estadísticas de una serie del BCRP entre dos periodos, calculadas con pandas: úsenla en vez de hacer
    cuentas a mano.

    Devuelve primero y ultimo (periodo y valor), cambio (ultimo - primero), variacion_pct (cambio relativo
    al primero, en %; None si el primero es 0), promedio, maximo y minimo (con su periodo), n, la fuente
    y los periodos omitidos por no tener dato. Ojo: si la serie ya es una variación % (p. ej. el IPC a 12
    meses), "cambio" está en puntos porcentuales.
    Ejemplo: resumen("PN01273PM", "2024-01", "2024-12") -> inflación a 12 meses durante 2024.
    """
    r = _obtener(codigo, desde, hasta)
    df = pd.DataFrame(r["datos"])
    if df.empty:
        raise ToolError(f"La serie {r['codigo']} no tiene datos entre {desde} y {hasta}. Fuente: {r['fuente']}")
    df = df.sort_values("periodo", ignore_index=True)
    primero, ultimo = df.valor.iloc[0], df.valor.iloc[-1]
    cambio = ultimo - primero
    return {"codigo": r["codigo"], "nombre": r["nombre"], "frecuencia": r["frecuencia"],
            "primero": _punto(df, 0), "ultimo": _punto(df, len(df) - 1),
            "cambio": float(cambio),
            "variacion_pct": None if primero == 0 else float(cambio / abs(primero) * 100),
            "promedio": float(df.valor.mean()),
            "maximo": _punto(df, df.valor.idxmax()), "minimo": _punto(df, df.valor.idxmin()),
            "n": int(len(df)), "omitidos": r["omitidos"], "fuente": r["fuente"]}


@mcp.tool(annotations=SOLO_LECTURA)
def correlacion(codigo_a: str, codigo_b: str, desde: str, hasta: str) -> dict:
    """Correlación de Pearson entre dos series del BCRP de la misma frecuencia, en los periodos que ambas tienen.

    Qué hace: baja las dos series, las alinea por periodo, descarta los periodos donde falta alguna y calcula
    el coeficiente (de -1 a 1) con pandas.
    Cuándo usarla: para describir si dos indicadores se movieron juntos en un periodo, p. ej. inflación y
    tipo de cambio, o tasa de referencia e inflación. Exige la misma frecuencia (Mensual con Mensual, etc.)
    y al menos 3 periodos comunes; si no, da un ToolError.
    Ojo: es una asociación descriptiva, NO prueba causalidad. No la presenten como causa y efecto.
    Ejemplo: correlacion("PN01273PM", "PN01207PM", "2024-01", "2024-12") -> inflación a 12 meses frente
    al tipo de cambio mensual durante 2024.
    Devuelve coeficiente, n, periodos usados, periodos descartados, las fuentes y una nota.
    """
    fa, fb = _ficha(codigo_a.strip().upper()), _ficha(codigo_b.strip().upper())
    if fa["frecuencia"] != fb["frecuencia"]:
        raise ToolError(f"Frecuencias distintas: {fa['codigo']} es {fa['frecuencia']} y {fb['codigo']} es "
                        f"{fb['frecuencia']}. Elijan dos series con la misma frecuencia.")
    a, b = _obtener(fa["codigo"], desde, hasta), _obtener(fb["codigo"], desde, hasta)
    sa = pd.DataFrame(a["datos"], columns=["periodo", "valor"]).set_index("periodo").valor.rename("a")
    sb = pd.DataFrame(b["datos"], columns=["periodo", "valor"]).set_index("periodo").valor.rename("b")
    junto = pd.concat([sa, sb], axis=1).sort_index()           # unión de periodos: los faltantes quedan NaN
    completos = junto.dropna()
    descartados = sorted(set(junto.index) - set(completos.index))
    if len(completos) < 3:
        raise ToolError(f"Solo hay {len(completos)} periodos con dato en ambas series entre {desde} y {hasta}; "
                        "se necesitan al menos 3.")
    coef = completos.a.corr(completos.b)
    return {"codigo_a": fa["codigo"], "nombre_a": fa["nombre"], "codigo_b": fb["codigo"], "nombre_b": fb["nombre"],
            "frecuencia": fa["frecuencia"],
            "coeficiente": None if pd.isna(coef) else float(coef),  # NaN si una serie es constante
            "n": int(len(completos)), "periodos": list(completos.index), "descartados": descartados,
            "fuentes": [a["fuente"], b["fuente"]],
            "nota": "Correlación de Pearson: asociación descriptiva entre las dos series en estos periodos. "
                    "No implica causalidad."}

@mcp.resource("bcrp://serie/{codigo}", mime_type="application/json")
def ficha_serie(codigo: str) -> dict:
    """Ficha descriptiva de una serie del BCRP: nombre, categoría, frecuencia, inicio, última actualización
    y el enlace para pedir sus datos. No trae valores: para eso están serie y resumen."""
    f = _ficha(codigo.strip().upper())
    return {**f, "api": f"{API}/{f['codigo']}/json/{{desde}}/{{hasta}}", "catalogo": URL_CATALOGO,
            "institucion": "Banco Central de Reserva del Perú (BCRP)"}


@mcp.prompt
def informe(tema: str) -> str:
    """Informe breve con datos del BCRP sobre un tema, citando código, periodo y fuente de cada cifra."""
    return f"""Escribe un informe breve sobre: {tema}

Reglas obligatorias:
1. Usa solo datos obtenidos con las herramientas del servidor bcrp: busca los códigos con buscar_series y
   obtén las cifras con serie, resumen o correlacion. No uses cifras de memoria ni hagas cuentas a mano.
2. Cada cifra debe citar el código de la serie, el periodo exacto y la fuente (la URL que devolvió la
   herramienta). Formato sugerido: "1.97 % (PN01273PM, 2024-12, fuente: <url>)".
3. Las correlaciones y coincidencias en el tiempo son asociaciones descriptivas: no las presentes como
   causas ("X provocó Y"). Usa expresiones como "se movieron en la misma dirección".
4. Si un dato no existe o la herramienta da error, dilo; no lo inventes.
5. Termina con una lista de las series usadas: código, nombre, frecuencia y periodo consultado."""


if __name__ == "__main__":
    mcp.run()
