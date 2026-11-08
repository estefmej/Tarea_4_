"""Estimación de proporciones con el diseño muestral de la ENAHO.

Error estándar por linealización de Taylor de un estimador de razón:
    R = Σ w·y / Σ w·x
- Personas:  y = pobre,            x = 1,         w = facpob07
- Hogares:   y = pobre × mieperho, x = mieperho,  w = factor07
UPM = conglome; estratos = departamento × estrato. Muestreo de UPM con reemplazo
dentro de cada estrato (aproximación estándar, como svy en Stata o survey en R).
Los dominios (área, sexo, edad, departamento) se estiman como subpoblaciones: se
conservan todas las UPM y la variable de dominio pone en 0 a quien no pertenece.
Un estrato con una sola UPM se centra en la media general de las UPM
(equivalente a survey.lonely.psu = "adjust" en R).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

Z_95 = 1.959964


def razon(df: pd.DataFrame, y: str, x: str, w: str, dominio: pd.Series | None = None,
          upm: str = "conglome", estrato: str = "estrato_diseno") -> dict:
    """Devuelve estimación, error estándar e IC 95 % de R = Σw·y / Σw·x en el dominio."""
    d = np.ones(len(df)) if dominio is None else dominio.to_numpy(dtype=float)
    wy = df[w].to_numpy(float) * df[y].to_numpy(float) * d
    wx = df[w].to_numpy(float) * df[x].to_numpy(float) * d
    X = wx.sum()
    R = wy.sum() / X
    z = (wy - R * wx) / X  # variable linealizada (ya ponderada)

    t = (pd.DataFrame({"h": df[estrato].to_numpy(), "u": df[upm].to_numpy(), "z": z})
         .groupby(["h", "u"], sort=False)["z"].sum().reset_index())
    n_h = t.groupby("h")["u"].transform("size").to_numpy()
    media_h = t.groupby("h")["z"].transform("mean").to_numpy()
    zt = t["z"].to_numpy()
    multi = n_h > 1
    var = float(((n_h[multi] / (n_h[multi] - 1)) * (zt[multi] - media_h[multi]) ** 2).sum())
    var += float(((zt[~multi] - zt.mean()) ** 2).sum())  # estratos con una sola UPM
    ee = var ** 0.5
    return {"estimacion": R * 100, "ee": ee * 100,
            "ic_inf": (R - Z_95 * ee) * 100, "ic_sup": (R + Z_95 * ee) * 100,
            "n": int((d > 0).sum()), "upm_unica": int((~multi).sum())}
