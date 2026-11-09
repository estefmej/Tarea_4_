"""Genera ENTREGA.md: el comentario de entrega para el Issue 201, con el formato del enunciado.

Cada cifra se lee de su archivo (scripts/cifras.py); debajo del comentario va una tabla con el
archivo y la línea de donde salió cada valor. El nombre completo se deja para completarlo a mano.

Uso (desde la raíz del proyecto):
    uv run python scripts/generar_entrega.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cifras  # noqa: E402

REPO = "https://github.com/estefmej/Tarea_4_"
USUARIO = "estefmej"
RAMA = "main"


def enlace(ruta: str, carpeta: bool = False) -> str:
    return f"{REPO}/{'tree' if carpeta else 'blob'}/{RAMA}/{ruta}"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    p = cifras.pruebas_mcp()
    v = cifras.validacion_enaho()
    e = cifras.evaluacion()
    q = cifras.pregunta_investigacion()
    a, b = e["oficial"].loc["A"], e["oficial"].loc["B"]
    # Formato del enunciado: XX.X % y XX,XXX
    pobreza = f"{v['pobreza_nacional']:.1f}"
    residentes = f"{v['residentes']:,}"

    comentario = f"""### Tarea 4 – Individual

**Estudiante:** Nombre completo (@{USUARIO})

**Pregunta de investigación:** {q['pregunta']}

**Repositorio de GitHub:** {REPO}

**Informe final:** {enlace(cifras.INFORME)}

**Pruebas MCP:** {p['aprobadas']}/{p['total']} aprobadas

**Validación ENAHO:**
- Pobreza nacional 2024: {pobreza} %
- Residentes habituales: {residentes}
- Unidades territoriales procesadas: {v['departamentos']}/25

**Evaluación del agente:**
- Sin MCP/Skills: {a.correctas}/{a.preguntas} respuestas correctas
- Con MCP/Skills: {b.correctas}/{b.preguntas} respuestas correctas
- Resultados completos: {enlace(cifras.RESULTADOS)}

**Evidencia de integración MCP + Skills:** {enlace('evidencias_ia/integracion/02_ejecucion_agente.txt')}

**Evidencias de uso de IA:** {enlace('evidencias_ia', carpeta=True)}
"""

    origen = [
        ("Pregunta de investigación", "texto", q["origen"], "sección 1, línea «**Pregunta.**»"),
        ("Pruebas MCP", f"{p['aprobadas']}/{p['total']}", p["origen"], p["linea"]),
        ("Pobreza nacional 2024", f"{pobreza} % (de {v['pobreza_nacional']:.2f} %)", v["origen"],
         v["linea_pobreza"]),
        ("Residentes habituales", residentes, v["origen"], v["linea_residentes"]),
        ("Unidades territoriales", f"{v['departamentos']}/25", v["origen"],
         v["linea_departamentos"].split(":")[0]),
        ("Sin MCP/Skills (Modo A)", f"{a.correctas}/{a.preguntas}", e["origen"],
         "filas con modo = A y correcta = sí"),
        ("Con MCP/Skills (Modo B)", f"{b.correctas}/{b.preguntas}", e["origen"],
         "filas con modo = B y correcta = sí"),
    ]
    tabla = ["| Campo | Valor | Archivo | Línea o criterio |", "|---|---|---|---|"]
    tabla += [f"| {c} | {val} | `{arch}` | {det.replace('|', '/')} |" for c, val, arch, det in origen]

    texto = "\n".join([
        "# Entrega – Tarea 4",
        "",
        "<!-- Generado por scripts/generar_entrega.py; no editar las cifras a mano. -->",
        "",
        "Antes de publicar: reemplazar **Nombre completo**. Copiar en el Issue",
        "<https://github.com/d2cml-ai/Data-Science-Python/issues/201> el texto entre las dos líneas.",
        "",
        "---",
        "",
        comentario.rstrip(),
        "",
        "---",
        "",
        "## Origen de cada cifra (no copiar en el Issue)",
        "",
        *tabla,
        "",
        f"Pobreza nacional: se informa la cifra con la sumaria (`factor07 × mieperho`), el método del INEI "
        f"y del informe final. Con la base de personas (`facpob07`) es {v['pobreza_nacional_personas']:.2f} % "
        f"(misma fuente). La validación completa aprobó {v['aprobadas']} de {v['verificaciones']} "
        f"verificaciones.",
        "",
        f"Análisis complementario B2 (no se pide en el comentario): "
        f"{e['b2'].loc['B2'].correctas}/{e['b2'].loc['B2'].preguntas} en `{e['origen_b2']}`.",
        "",
    ])
    (cifras.RAIZ / "ENTREGA.md").write_text(texto, encoding="utf-8")
    print(texto)


if __name__ == "__main__":
    main()
