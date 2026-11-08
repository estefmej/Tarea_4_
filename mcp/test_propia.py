"""Pruebas de la herramienta propia `correlacion`, con el mismo cliente en memoria que test_server.py.

    uv run pytest -v mcp/test_propia.py
"""
import asyncio

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from server import mcp


def llamar(herramienta, **args):
    async def f():
        async with Client(mcp) as c:
            return (await c.call_tool(herramienta, args)).data
    return asyncio.run(f())


def test_correlacion_de_una_serie_consigo_misma_es_uno():
    r = llamar("correlacion", codigo_a="PN01273PM", codigo_b="PN01273PM", desde="2024-01", hasta="2024-12")
    assert r["coeficiente"] == pytest.approx(1.0, abs=1e-9)
    assert r["n"] == 12 and len(r["periodos"]) == 12
    assert r["periodos"][0] == "2024-01" and r["periodos"][-1] == "2024-12"
    assert "causal" in r["nota"].lower() and r["fuentes"][0].startswith("https://estadisticas.bcrp.gob.pe")


def test_correlacion_rechaza_frecuencias_distintas():
    with pytest.raises(ToolError, match="Frecuencias distintas"):
        llamar("correlacion", codigo_a="PN01273PM", codigo_b="PD04638PD", desde="2024-01", hasta="2024-12")
