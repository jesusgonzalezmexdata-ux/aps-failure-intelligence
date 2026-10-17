"""Entrada del calibrador de alertas: plantilla, lectura de Excel o CSV y validación con mensajes en español.

Una fila por alerta recibida de la telemática (o del tablero de códigos de falla), con lo que pasó después:
si se mandó a taller y si se confirmó la falla, en la revisión o como avería en ruta.
"""
from __future__ import annotations

import io
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

REQUIRED = ["unidad", "fecha", "tipo_alerta", "revisada", "falla"]
OPTIONAL = ["puntaje"]
ALIASES = {
    "camion": "unidad", "economico": "unidad", "eco": "unidad", "vehiculo": "unidad", "unit": "unidad", "tracto": "unidad",
    "date": "fecha", "fecha_alerta": "fecha",
    "tipo": "tipo_alerta", "alerta": "tipo_alerta", "codigo": "tipo_alerta", "dtc": "tipo_alerta", "codigo_falla": "tipo_alerta",
    "score": "puntaje", "riesgo": "puntaje", "probabilidad": "puntaje",
    "revisado": "revisada", "atendida": "revisada", "a_taller": "revisada", "taller": "revisada",
    "falla_confirmada": "falla", "averia": "falla", "resultado": "falla", "fallo": "falla",
}
YES = {"si", "s", "1", "true", "verdadero", "x", "yes", "y"}
NO = {"no", "n", "0", "false", "falso", ""}
MIN_ALERTS, MIN_FAILURES, MIN_WEEKS = 50, 5, 8

INSTRUCTIONS = [
    ("Columna", "Obligatoria", "Qué poner"),
    ("unidad", "Sí", "Número económico o placa de la unidad"),
    ("fecha", "Sí", "Día en que llegó la alerta (dd/mm/aaaa)"),
    ("tipo_alerta", "Sí", "Código o nombre de la alerta, siempre escrito igual (p. ej. «Presión de aire baja» o un código DTC)"),
    ("puntaje", "No", "Puntaje de riesgo que da la telemática; más alto = más riesgo. Si no hay, se prioriza por tipo de alerta"),
    ("revisada", "Sí", "sí / no: ¿se mandó la unidad a taller por esta alerta?"),
    ("falla", "Sí", "sí / no: ¿se confirmó la falla? Encontrada en la revisión, o avería en ruta del mismo sistema en los 30 días siguientes"),
    ("", "", "Mínimo 8 semanas de alertas y 5 fallas confirmadas; ideal 6 meses. El archivo se procesa en tu navegador y no se envía a ningún servidor."),
]


class DataError(ValueError):
    """El archivo no se puede analizar."""


@dataclass
class Issue:
    nivel: str        # "error" (fila excluida) o "aviso"
    fila: int | None  # fila del archivo (encabezado = 1)
    mensaje: str


def _key(text) -> str:
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode()
    key = "_".join(text.strip().lower().replace("-", " ").split())
    return ALIASES.get(key, key)


def read_table(source, name: str = "") -> pd.DataFrame:
    """Lee .xlsx (hoja «alertas» o la primera) o .csv (coma o punto y coma) desde ruta, bytes o archivo subido."""
    raw = source.getvalue() if hasattr(source, "getvalue") else source
    name = name or getattr(source, "name", "")
    try:
        if str(name).lower().endswith(".csv") or (isinstance(raw, (bytes, bytearray)) and raw[:2] != b"PK"):
            text = raw.decode("utf-8-sig") if isinstance(raw, (bytes, bytearray)) else Path(raw).read_text(encoding="utf-8-sig")
            sep = ";" if text.split("\n", 1)[0].count(";") > text.split("\n", 1)[0].count(",") else ","
            df = pd.read_csv(io.StringIO(text), sep=sep, dtype=str, keep_default_na=False)
        else:
            sheets = pd.read_excel(io.BytesIO(raw) if isinstance(raw, (bytes, bytearray)) else raw, sheet_name=None, dtype=str)
            df = next((d for n, d in sheets.items() if _key(n) == "alertas"), next(iter(sheets.values())))
    except Exception as exc:
        raise DataError(f"No se pudo leer el archivo como Excel (.xlsx) o CSV: {exc}") from exc
    return df.rename(columns=_key).dropna(how="all")


def _flag(series: pd.Series) -> pd.Series:
    key = series.fillna("").map(lambda v: _key(v).replace("_", ""))
    return pd.Series(np.where(key.isin(YES), True, np.where(key.isin(NO), False, None)), index=series.index, dtype=object)


def _dates(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip().str.slice(0, 10)
    iso = pd.to_datetime(s, format="%Y-%m-%d", errors="coerce")
    dmy = pd.to_datetime(s, format="%d/%m/%Y", errors="coerce")
    serial = pd.to_numeric(s, errors="coerce")
    ok = serial.between(20000, 80000)
    excel = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")
    if ok.any():  # número de serie de Excel (fecha guardada como número)
        excel[ok] = pd.Timestamp("1899-12-30") + pd.to_timedelta(serial[ok].round(), unit="D")
    return iso.fillna(dmy).fillna(excel)


def validate(df: pd.DataFrame, need_outcome: bool = True):
    """Devuelve (alertas, avisos). Excluye filas con error y las reporta; lanza DataError si no hay qué analizar.

    need_outcome=False valida una semana nueva, que todavía no tiene «revisada» ni «falla»."""
    required = REQUIRED if need_outcome else ["unidad", "fecha", "tipo_alerta"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise DataError("Faltan columnas obligatorias: " + ", ".join(missing) + ". Usa la plantilla descargable.")
    issues: list[Issue] = []
    out = pd.DataFrame(index=df.index)
    rows = pd.Series(np.arange(len(df)) + 2, index=df.index)
    bad = pd.Series(False, index=df.index)

    for col in ("unidad", "tipo_alerta"):
        out[col] = df[col].astype(str).str.strip().str.replace(r"\s+", " ", regex=True)
        empty = out[col].isin(["", "nan", "None"])
        for r in df.index[empty & ~bad]:
            issues.append(Issue("error", int(rows[r]), f"«{col}» vacío"))
        bad |= empty
    out["fecha"] = _dates(df["fecha"])
    for r in df.index[out["fecha"].isna() & ~bad]:
        issues.append(Issue("error", int(rows[r]), f"«fecha» no reconocida (valor: {df.at[r, 'fecha']!r}); usa dd/mm/aaaa"))
    bad |= out["fecha"].isna()

    for col in ("revisada", "falla"):
        if col not in df.columns:
            continue
        out[col] = _flag(df[col])
        for r in df.index[out[col].isna() & ~bad]:
            issues.append(Issue("error", int(rows[r]), f"«{col}» debe ser sí o no (valor: {df.at[r, col]!r})"))
        bad |= out[col].isna()

    if "puntaje" in df.columns:
        given = ~df["puntaje"].astype(str).str.strip().isin(["", "nan", "None"])
        out["puntaje"] = pd.to_numeric(df["puntaje"].astype(str).str.replace(",", ".", regex=False), errors="coerce")
        wrong = given & out["puntaje"].isna()
        for r in df.index[wrong & ~bad][:20]:
            issues.append(Issue("aviso", int(rows[r]), f"«puntaje» no es un número (valor: {df.at[r, 'puntaje']!r}); se deja vacío"))

    out = out[~bad].copy()
    for col in ("revisada", "falla"):
        if col in out:
            out[col] = out[col].astype(bool)
    dup = out.duplicated(["unidad", "fecha", "tipo_alerta"], keep="first")
    if dup.any():
        issues.append(Issue("aviso", None, f"{int(dup.sum())} alertas repetidas (misma unidad, día y tipo) se cuentan una vez."))
        out = out[~dup]
    if "puntaje" in out:
        share = out["puntaje"].isna().mean()
        if share > 0.2:
            issues.append(Issue("aviso", None, f"El {share:.0%} de las alertas no tiene puntaje: se prioriza por tipo de alerta."))
            out = out.drop(columns="puntaje")
        elif share > 0:
            issues.append(Issue("aviso", None, f"{int(out['puntaje'].isna().sum())} alertas sin puntaje reciben el puntaje mediano de su tipo."))
            out["puntaje"] = out["puntaje"].fillna(out.groupby("tipo_alerta")["puntaje"].transform("median")).fillna(out["puntaje"].median())

    if out.empty:
        raise DataError("Ninguna fila es válida. Revisa los errores por fila.")
    if need_outcome:
        weeks = (out["fecha"].max() - out["fecha"].min()).days / 7
        if len(out) < MIN_ALERTS or out["falla"].sum() < MIN_FAILURES:
            raise DataError(f"Se necesitan al menos {MIN_ALERTS} alertas y {MIN_FAILURES} fallas confirmadas; "
                            f"hay {len(out)} alertas y {int(out['falla'].sum())} fallas.")
        if weeks < MIN_WEEKS:
            issues.append(Issue("aviso", None, f"El historial cubre {weeks:.0f} semanas; con menos de {MIN_WEEKS} la validación es débil."))
        if out["revisada"].all():
            issues.append(Issue("aviso", None, "Todas las alertas se revisaron: la regla actual es «revisar todo»."))
    return out.sort_values("fecha").reset_index(drop=True), issues


# ---------------------------------------------------------------- datos de ejemplo
TYPES = [  # tipo, probabilidad de falla real, alertas por semana en la flota
    ("Presión de aire baja", 0.12, 9), ("Temperatura de refrigerante alta", 0.10, 6),
    ("Presión de aceite baja", 0.20, 3), ("Voltaje de batería bajo", 0.03, 12),
    ("Filtro de partículas saturado", 0.06, 8), ("Sensor ABS intermitente", 0.02, 14),
    ("Desgaste de balatas", 0.25, 4), ("Falla de comunicación CAN", 0.01, 10),
]
ALWAYS_CHECKED = {"Presión de aceite baja", "Desgaste de balatas", "Presión de aire baja"}


def example_data(weeks: int = 26, seed: int = 11, start: str = "2026-04-06", drift: bool = False, outcome: bool = True) -> pd.DataFrame:
    """Flota simulada de 140 tractocamiones. Regla actual: revisar siempre aceite, balatas y aire, y 3 de cada 10 de lo demás.

    drift=True agrega una actualización de firmware que dispara las alertas de ABS (para el monitor semanal)."""
    rng = np.random.default_rng(seed)
    rows = []
    for w in range(weeks):
        monday = pd.Timestamp(start) + pd.Timedelta(weeks=int(w))
        for tipo, p, rate in TYPES:
            n = rng.poisson(rate * (3 if drift and tipo == "Sensor ABS intermitente" else 1))
            for _ in range(n):
                z = rng.normal()
                logit = np.log(p / (1 - p)) + 1.4 * z
                falla = rng.random() < 1 / (1 + np.exp(-logit))
                puntaje = float(np.clip(round(100 / (1 + np.exp(-(logit + rng.normal(0, 0.9) + 1.5) / 1.6))), 1, 99))
                row = dict(unidad=f"T-{rng.integers(101, 241)}", fecha=(monday + pd.Timedelta(days=int(rng.integers(0, 7)))).strftime("%d/%m/%Y"),
                           tipo_alerta=tipo, puntaje=puntaje)
                if outcome:
                    row.update(revisada="sí" if tipo in ALWAYS_CHECKED or rng.random() < 0.3 else "no", falla="sí" if falla else "no")
                rows.append(row)
    return pd.DataFrame(rows).drop_duplicates(["unidad", "fecha", "tipo_alerta"]).reset_index(drop=True)


def example_week() -> pd.DataFrame:
    """La semana siguiente al historial de ejemplo, sin resultados todavía y con el disparo de alertas ABS."""
    return example_data(weeks=1, seed=99, start="2026-10-05", drift=True, outcome=False)


def example_with_errors() -> pd.DataFrame:
    df = example_data().astype(str)
    df.loc[3, "fecha"] = "31/02/2026"
    df.loc[10, "falla"] = "tal vez"
    df.loc[25, "unidad"] = ""
    df.loc[40, "puntaje"] = "alto"
    return pd.concat([df, df.iloc[[5]]], ignore_index=True)


def template_bytes() -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xl:
        example_data().to_excel(xl, sheet_name="alertas", index=False)
        pd.DataFrame(INSTRUCTIONS[1:], columns=INSTRUCTIONS[0]).to_excel(xl, sheet_name="instrucciones", index=False)
    return buf.getvalue()


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")
