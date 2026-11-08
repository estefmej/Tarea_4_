"""Limpia la ENAHO 2024 (módulos 34 y 02) y arma una base de personas con pobreza.

Uso (desde la raíz del proyecto):
    uv run python .claude/skills/limpiando-enaho/scripts/limpiar.py --anio 2024

Salidas:
    salidas/personas_2024.parquet  base de residentes habituales (NO se versiona)
    salidas/indicadores.csv        pobreza ponderada: nacional, área, sexo y departamentos
    salidas/validacion.txt         cada verificación marcada APROBADA / FALLIDA

Si una verificación esencial falla, el script termina con error. Nunca se ajustan
los resultados para que coincidan con las cifras de referencia.
"""

from __future__ import annotations

import argparse
import io
import re
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

# Código del portal de microdatos del INEI para cada año de la ENAHO anual.
CODIGOS_INEI = {2024: "966"}

LLAVES_HOGAR = ["conglome", "vivienda", "hogar"]
LLAVES_TEXTO = LLAVES_HOGAR + ["ubigeo", "codperso"]

# Cifras de referencia para validar (no son resultados: son los valores contra
# los que se compara lo calculado). Fuente: INEI y README de la Sesión 16.
REFERENCIA = {
    2024: {
        "pobreza_nacional": 27.6,
        "residentes": 108_664,
        "hogares_sumaria": 33_691,
        "urbano": 24.8,
        "rural": 39.3,
    }
}
TOLERANCIA_PP = 0.1

DEPARTAMENTOS = {
    "01": "Amazonas", "02": "Áncash", "03": "Apurímac", "04": "Arequipa",
    "05": "Ayacucho", "06": "Cajamarca", "07": "Callao", "08": "Cusco",
    "09": "Huancavelica", "10": "Huánuco", "11": "Ica", "12": "Junín",
    "13": "La Libertad", "14": "Lambayeque", "15": "Lima", "16": "Loreto",
    "17": "Madre de Dios", "18": "Moquegua", "19": "Pasco", "20": "Piura",
    "21": "Puno", "22": "San Martín", "23": "Tacna", "24": "Tumbes",
    "25": "Ucayali",
}


# ---------------------------------------------------------------- lectura
def buscar_dta(datos: Path, codigo: str, modulo: str, patron: str) -> tuple[Path, str | None]:
    """Devuelve (archivo, miembro_del_zip). Acepta el zip o la carpeta ya descomprimida."""
    carpeta = datos / f"{codigo}-Modulo{modulo}"
    if carpeta.is_dir():
        for f in carpeta.iterdir():
            if re.fullmatch(patron, f.name, flags=re.IGNORECASE):
                return f, None
    zp = datos / f"{codigo}-Modulo{modulo}.zip"
    if not zp.exists():
        sys.exit(
            f"ERROR: falta {zp}. Bájalo de "
            f"https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/{codigo}-Modulo{modulo}.zip"
        )
    with zipfile.ZipFile(zp) as zf:
        for nombre in zf.namelist():
            if re.fullmatch(patron, Path(nombre).name, flags=re.IGNORECASE):
                return zp, nombre
    sys.exit(f"ERROR: no encontré un archivo que cumpla {patron!r} dentro de {zp}")


def leer_stata(archivo: Path, miembro: str | None) -> pd.DataFrame:
    if miembro is None:
        df = pd.read_stata(archivo, convert_categoricals=False)
    else:
        with zipfile.ZipFile(archivo) as zf:
            df = pd.read_stata(io.BytesIO(zf.read(miembro)), convert_categoricals=False)
    return normalizar(df)


def normalizar(df: pd.DataFrame) -> pd.DataFrame:
    """Columnas en minúscula; la del año (aÑo, mal decodificada) pasa a 'año'.
    Las llaves se guardan como texto sin perder ceros a la izquierda."""
    df = df.rename(columns=lambda c: c.lower())
    df = df.rename(columns=lambda c: "año" if re.fullmatch(r"a.{1,2}o", c) else c)
    for c in LLAVES_TEXTO:
        if c in df.columns:
            if not pd.api.types.is_string_dtype(df[c]):
                raise TypeError(f"La llave {c} no llegó como texto ({df[c].dtype}); revisa el .dta")
            df[c] = df[c].astype("string").str.strip()
    return df


# ---------------------------------------------------------------- cálculo
def pct_ponderado(indicador: pd.Series, peso: pd.Series) -> float:
    """Porcentaje ponderado. Nunca promedio simple."""
    return float(np.average(indicador.astype(float), weights=peso.astype(float)) * 100)


def tabla_indicadores(p: pd.DataFrame) -> pd.DataFrame:
    filas = []

    def agregar(grupo, codigo, categoria, d):
        filas.append({
            "grupo": grupo,
            "codigo": codigo,
            "categoria": categoria,
            "pobreza_pct": round(pct_ponderado(d["pobre"], d["facpob07"]), 2),
            "pobreza_extrema_pct": round(pct_ponderado(d["pobre_extremo"], d["facpob07"]), 2),
            "poblacion_expandida": round(float(d["facpob07"].sum())),
            "n_muestra": len(d),
            "ponderador": "facpob07",
        })

    agregar("nacional", "PE", "Perú", p)
    for area, d in p.groupby("area", sort=True):
        agregar("area", area, area.capitalize(), d)
    for sexo, d in p.groupby("sexo", sort=True):
        agregar("sexo", sexo, sexo.capitalize(), d)
    for dep, d in p.groupby("departamento", sort=True):
        agregar("departamento", dep, DEPARTAMENTOS.get(dep, dep), d)
    return pd.DataFrame(filas)


# ---------------------------------------------------------------- principal
def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--anio", type=int, default=2024)
    ap.add_argument("--datos", type=Path, default=Path("datos"))
    ap.add_argument("--salidas", type=Path, default=Path("salidas"))
    a = ap.parse_args()

    if a.anio not in CODIGOS_INEI or a.anio not in REFERENCIA:
        sys.exit(f"ERROR: el año {a.anio} no está configurado (código INEI y cifras de validación). Solo: {sorted(CODIGOS_INEI)}")
    codigo, ref = CODIGOS_INEI[a.anio], REFERENCIA[a.anio]
    a.salidas.mkdir(parents=True, exist_ok=True)

    # 1. Leer
    sumaria = leer_stata(*buscar_dta(a.datos, codigo, "34", rf"sumaria-{a.anio}\.dta"))
    miembros = leer_stata(*buscar_dta(a.datos, codigo, "02", rf"enaho01-{a.anio}-200\.dta"))
    n_miembros = len(miembros)

    # 2. Residentes habituales
    residente = ((miembros["p204"] == 1) & (miembros["p205"] == 2)) | (
        (miembros["p204"] == 2) & (miembros["p206"] == 1)
    )
    personas = miembros.loc[residente].copy()
    n_residentes = len(personas)

    # 3. Unir personas (m) con sumaria (1)
    cols_sumaria = LLAVES_HOGAR + ["pobreza", "factor07", "mieperho", "linea", "linpe"]
    cols_sumaria = [c for c in cols_sumaria if c in sumaria.columns]
    base = personas.merge(
        sumaria[cols_sumaria], on=LLAVES_HOGAR, how="left", validate="m:1", indicator=True
    )
    sin_hogar = int((base["_merge"] != "both").sum())
    base = base.drop(columns="_merge")

    # 4. Construir variables
    base["departamento"] = base["ubigeo"].str[:2]
    base["area"] = np.where(base["estrato"] <= 5, "urbano", "rural")
    base["pobre"] = base["pobreza"] <= 2
    base["pobre_extremo"] = base["pobreza"] == 1
    base["sexo"] = base["p207"].map({1: "hombre", 2: "mujer"})
    base["anio"] = a.anio

    # 5. Indicadores ponderados
    ind = tabla_indicadores(base)
    pob_personas = pct_ponderado(base["pobre"], base["facpob07"])
    # Contraste con la sumaria: cada hogar pesa factor07 × mieperho (personas que
    # representa). Es el método de las cifras de referencia del INEI por área.
    hog = sumaria.copy()
    hog["peso"] = hog["factor07"] * hog["mieperho"]
    hog["area"] = np.where(hog["estrato"] <= 5, "urbano", "rural")
    hog["departamento"] = hog["ubigeo"].str[:2]
    pob_sumaria = pct_ponderado(hog["pobreza"] <= 2, hog["peso"])
    contraste = []
    for grupo, codigo_g, cat, d in [("nacional_contraste", "PE", "Perú", hog),
                                    *[("area_contraste", ar, ar.capitalize(), dd)
                                      for ar, dd in hog.groupby("area", sort=True)],
                                    *[("departamento_contraste", dep, DEPARTAMENTOS.get(dep, dep), dd)
                                      for dep, dd in hog.groupby("departamento", sort=True)]]:
        contraste.append({
            "grupo": grupo, "codigo": codigo_g, "categoria": f"{cat} (sumaria, factor07 × mieperho)",
            "pobreza_pct": round(pct_ponderado(d["pobreza"] <= 2, d["peso"]), 2),
            "pobreza_extrema_pct": round(pct_ponderado(d["pobreza"] == 1, d["peso"]), 2),
            "poblacion_expandida": round(float(d["peso"].sum())),
            "n_muestra": len(d), "ponderador": "factor07*mieperho",
        })
    ind = pd.concat([ind, pd.DataFrame(contraste)], ignore_index=True)

    def valor(grupo, codigo_g):
        return float(ind.loc[(ind.grupo == grupo) & (ind.codigo == codigo_g), "pobreza_pct"].iloc[0])

    urb_s, rur_s = valor("area_contraste", "urbano"), valor("area_contraste", "rural")
    urb_p, rur_p = valor("area", "urbano"), valor("area", "rural")
    n_hog_distinto = int((
        personas.groupby(LLAVES_HOGAR).size()
        .reindex(pd.MultiIndex.from_frame(sumaria[LLAVES_HOGAR])).fillna(0).to_numpy()
        != sumaria["mieperho"].to_numpy()
    ).sum())

    # 6. Validar
    chequeos: list[tuple[str, bool, bool, str]] = []  # (nombre, ok, esencial, detalle)

    def chequear(nombre, ok, detalle, esencial=True):
        chequeos.append((nombre, bool(ok), esencial, detalle))

    chequear("Llaves únicas en la sumaria (conglome, vivienda, hogar)",
             not sumaria.duplicated(LLAVES_HOGAR).any(),
             f"{len(sumaria):,} hogares; referencia {ref['hogares_sumaria']:,}")
    chequear("Hogares en la sumaria", len(sumaria) == ref["hogares_sumaria"],
             f"{len(sumaria):,} (referencia {ref['hogares_sumaria']:,})")
    chequear("Llaves únicas en personas (conglome, vivienda, hogar, codperso)",
             not personas.duplicated(LLAVES_HOGAR + ["codperso"]).any(), f"{n_residentes:,} filas")
    chequear("Residentes habituales", n_residentes == ref["residentes"],
             f"{n_residentes:,} de {n_miembros:,} filas del módulo 02 (referencia {ref['residentes']:,})")
    chequear("Unión m:1 sin perder filas", len(base) == n_residentes and sin_hogar == 0,
             f"{len(base):,} filas tras unir; {sin_hogar} personas sin hogar en la sumaria")
    chequear("Unión sin duplicar personas", not base.duplicated(LLAVES_HOGAR + ["codperso"]).any(),
             "cada persona aparece una vez")
    chequear("Sin vacíos en pobreza, facpob07, ubigeo, estrato y sexo",
             not base[["pobreza", "facpob07", "ubigeo", "estrato", "sexo"]].isna().any().any(),
             str(base[["pobreza", "facpob07", "ubigeo", "estrato", "sexo"]].isna().sum().to_dict()))
    codigos = sorted(base["departamento"].unique())
    chequear("25 códigos de departamento (01-25)", codigos == sorted(DEPARTAMENTOS),
             f"{len(codigos)} códigos: {', '.join(codigos)}")
    chequear(f"Pobreza nacional (personas, facpob07) a ≤{TOLERANCIA_PP} pp de {ref['pobreza_nacional']} %",
             abs(pob_personas - ref["pobreza_nacional"]) <= TOLERANCIA_PP,
             f"{pob_personas:.2f} % (diferencia {pob_personas - ref['pobreza_nacional']:+.2f} pp)")
    chequear(f"Pobreza nacional (sumaria, factor07 × mieperho) a ≤{TOLERANCIA_PP} pp de {ref['pobreza_nacional']} %",
             abs(pob_sumaria - ref["pobreza_nacional"]) <= TOLERANCIA_PP,
             f"{pob_sumaria:.2f} % (diferencia {pob_sumaria - ref['pobreza_nacional']:+.2f} pp)")
    chequear(f"Pobreza urbana (sumaria, factor07 × mieperho) ≈ {ref['urbano']} % (≤{TOLERANCIA_PP} pp)",
             abs(urb_s - ref["urbano"]) <= TOLERANCIA_PP,
             f"{urb_s:.2f} % (diferencia {urb_s - ref['urbano']:+.2f} pp)")
    chequear(f"Pobreza rural (sumaria, factor07 × mieperho) ≈ {ref['rural']} % (≤{TOLERANCIA_PP} pp)",
             abs(rur_s - ref["rural"]) <= TOLERANCIA_PP,
             f"{rur_s:.2f} % (diferencia {rur_s - ref['rural']:+.2f} pp)")

    lineas = [
        f"Validación ENAHO {a.anio} (INEI, código {codigo}) — skill limpiando-enaho",
        f"Tolerancia para porcentajes: {TOLERANCIA_PP} puntos porcentuales. Todas las cifras de pobreza están ponderadas.",
        "Cada cifra se compara con la referencia calculada con el mismo método.",
        "",
    ]
    for nombre, ok, esencial, detalle in chequeos:
        marca = "APROBADA" if ok else "FALLIDA"
        lineas.append(f"[{marca}] {nombre}{'' if esencial else ' (no esencial)'}: {detalle}")
    fallidas = [c for c in chequeos if not c[1] and c[2]]
    lineas += [
        "",
        "[INFORMATIVA] Pobreza por área con personas y facpob07 (la que usan los gráficos y el mapa): "
        f"urbano {urb_p:.2f} %, rural {rur_p:.2f} %.",
        f"[INFORMATIVA] Difiere de la sumaria porque en {n_hog_distinto:,} de {len(sumaria):,} hogares "
        f"({n_hog_distinto / len(sumaria):.1%}) los residentes habituales del módulo 02 no coinciden con "
        "mieperho (el INEI excluye de mieperho a trabajadores del hogar y pensionistas). "
        "Son dos ponderaciones válidas; ninguna cifra se ajustó.",
        "",
        f"Resultado: {len(chequeos) - len(fallidas)} de {len(chequeos)} verificaciones aprobadas.",
    ]
    texto = "\n".join(lineas) + "\n"
    (a.salidas / "validacion.txt").write_text(texto, encoding="utf-8")
    print(texto)

    if fallidas:
        sys.exit("ERROR: falló una validación esencial; no se guardan la base ni los indicadores. "
                 "Revisa el filtro, la unión y la ponderación (no ajustes resultados).")

    # 7. Guardar
    columnas = ["anio", "mes", *LLAVES_HOGAR, "codperso", "ubigeo", "departamento", "dominio",
                "estrato", "area", "p207", "sexo", "p208a", "facpob07", "pobreza", "pobre",
                "pobre_extremo", "factor07", "mieperho", "linea", "linpe"]
    columnas = [c for c in columnas if c in base.columns]
    base[columnas].to_parquet(a.salidas / f"personas_{a.anio}.parquet", index=False)
    ind.to_csv(a.salidas / "indicadores.csv", index=False, encoding="utf-8")
    print(f"Guardado: {a.salidas / f'personas_{a.anio}.parquet'} ({len(base):,} personas)")
    print(f"Guardado: {a.salidas / 'indicadores.csv'} ({len(ind)} filas)")


if __name__ == "__main__":
    main()
