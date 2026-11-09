"""Experimento de la Parte 4: cada pregunta en una sesión independiente de `claude -p`.

Modo A (sin MCP ni Skills): desde una carpeta vacía en %TEMP%, sin servidores MCP,
    sin Skills, sin web y sin herramientas para leer archivos o ejecutar comandos.
Modo B (con MCP y Skills): desde la raíz del repo, solo con el MCP `bcrp` de
    .mcp.json y las Skills; sin web; permisos en evaluacion/permisos_modo_b.json
    (bloquea leer evaluacion/, informes/, evidencias_ia/ y salidas/bcrp_*).

Ambos modos usan el mismo modelo (sonnet) y la misma instrucción. La salida
completa (stream-json) se guarda en evaluacion/registros/<modo>_<id>.jsonl y los
metadatos de la corrida (comando, carpeta, tiempo) en <modo>_<id>.meta.json.

Uso:
    uv run evaluacion/ejecutar.py --modos A B --ids B1      # piloto
    uv run evaluacion/ejecutar.py --modos A B               # las 20 corridas
"""

import argparse
import csv
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
EVAL = RAIZ / "evaluacion"
REGISTROS = EVAL / "registros"
CARPETA_A = Path(os.environ["TEMP"]) / "tarea4_evaluacion_modoA"

MODELO = "sonnet"
INSTRUCCION = "Termina tu respuesta con una línea con el formato: RESPUESTA: <valor o valores>"
TIEMPO_MAX = 900  # segundos por pregunta

COMUNES = [
    "-p",
    "--model", MODELO,
    "--output-format", "stream-json",
    "--verbose",
    "--no-session-persistence",
    "--permission-mode", "dontAsk",  # lo que no esté permitido se deniega sin preguntar
    "--strict-mcp-config",           # ignora toda config MCP salvo --mcp-config
]

# Herramientas bloqueadas en ambos modos: las que lanzan otros agentes, tareas
# programadas o sesiones remotas, que podrían saltarse las restricciones.
BLOQUEO_COMUN = ["WebSearch", "WebFetch", "PowerShell", "Agent", "Monitor",
                 "RemoteTrigger", "CronCreate", "ScheduleWakeup", "SendMessage",
                 "DesignSync", "PushNotification", "EnterWorktree"]
BLOQUEO_A = [*BLOQUEO_COMUN, "Skill", "Bash", "Read", "Glob", "Grep"]
BLOQUEO_B = BLOQUEO_COMUN


def comando(modo: str) -> tuple[list[str], Path]:
    claude = shutil.which("claude")
    if modo == "A":
        CARPETA_A.mkdir(exist_ok=True)
        if any(CARPETA_A.iterdir()):
            raise SystemExit(f"La carpeta del Modo A no está vacía: {CARPETA_A}")
        # Sin --mcp-config: con --strict-mcp-config no se carga ningún servidor MCP.
        return [claude, *COMUNES, "--disallowedTools", *BLOQUEO_A], CARPETA_A
    return [claude, *COMUNES,
            "--mcp-config", ".mcp.json",
            "--settings", "evaluacion/permisos_modo_b.json",
            "--disallowedTools", *BLOQUEO_B], RAIZ


def correr(modo: str, fila: dict) -> None:
    cmd, cwd = comando(modo)
    prompt = f"{fila['pregunta']}\n\n{INSTRUCCION}"
    base = REGISTROS / f"{modo}_{fila['id']}"
    inicio = time.time()
    error = ""
    try:
        res = subprocess.run(cmd, cwd=cwd, input=prompt.encode("utf-8"),
                             capture_output=True, timeout=TIEMPO_MAX)
        salida, err, codigo = res.stdout, res.stderr, res.returncode
    except subprocess.TimeoutExpired as e:
        salida, err, codigo = e.stdout or b"", e.stderr or b"", None
        error = f"timeout tras {TIEMPO_MAX} s"
    fin = time.time()

    base.with_suffix(".jsonl").write_bytes(salida)
    meta = {
        "modo": modo, "id": fila["id"], "modelo": MODELO, "prompt": prompt,
        "comando": [Path(cmd[0]).name, *cmd[1:]], "carpeta": str(cwd),
        "inicio": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(inicio)),
        "tiempo_reloj_s": round(fin - inicio, 1), "codigo_salida": codigo,
        "error": error, "stderr": err.decode("utf-8", "replace")[-4000:],
    }
    base.with_suffix(".meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{modo} {fila['id']}: {meta['tiempo_reloj_s']} s, código {codigo} {error}", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modos", nargs="+", default=["A", "B"], choices=["A", "B"])
    ap.add_argument("--ids", nargs="*", help="ids de preguntas (por defecto todas)")
    args = ap.parse_args()

    with open(EVAL / "preguntas.csv", encoding="utf-8") as f:
        preguntas = list(csv.DictReader(f))
    if args.ids:
        preguntas = [p for p in preguntas if p["id"] in args.ids]
    REGISTROS.mkdir(exist_ok=True)
    for fila in preguntas:
        for modo in args.modos:
            correr(modo, fila)


if __name__ == "__main__":
    main()
