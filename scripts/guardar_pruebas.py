"""Corre las pruebas del MCP y guarda la salida en salidas/pruebas_mcp.txt.

Reemplaza la ruta local del proyecto por <proyecto> para no publicar el nombre de usuario de la
computadora. Termina con el mismo código de salida que pytest.

Uso (desde la raíz del proyecto):
    uv run python scripts/guardar_pruebas.py
"""
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

r = subprocess.run([sys.executable, "-m", "pytest", "-v"], cwd=RAIZ, capture_output=True,
                   text=True, encoding="utf-8", errors="replace")
texto = (r.stdout + r.stderr).replace(str(RAIZ), "<proyecto>")
(RAIZ / "salidas" / "pruebas_mcp.txt").write_text(texto, encoding="utf-8")
print(texto.strip().splitlines()[-1])
sys.exit(r.returncode)
