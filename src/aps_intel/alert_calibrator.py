"""Calibrador de alertas por costo: qué alertas mandar a taller, cuánta carga esperar y cuándo sospechar un cambio.

Generaliza el método del caso Scania a las alertas que una flota ya recibe:

* Prioridad: el puntaje de la telemática si existe; si no, la tasa de falla del tipo de alerta con
  contracción bayesiana empírica (un tipo con 3 alertas no decide solo).
* Regla: el corte que minimiza costo de revisión × revisiones + costo de falla en ruta × fallas no atendidas
  (búsqueda exacta de ``cost.cost_optimal_threshold``); con puntaje se elige sobre los datos, con tipo se
  atiende todo tipo cuya probabilidad supere costo_revisión / (costo_revisión + costo_falla).
* Capacidad: si el taller no alcanza, se sube el corte hasta caber y se reporta lo que cuesta.
* Retrospectiva temporal: la regla se elige con las primeras semanas y se mide en las últimas contra la
  práctica actual, con intervalo bootstrap por semanas.
* Monitor semanal: carga de taller contra la banda binomial 99 % y cambio en la mezcla de alertas y del
  puntaje (ji cuadrada para decidir, PSI para el tamaño), reutilizando ``monitor.workshop_band`` y ``monitor.psi``.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.stats import chisquare

from aps_intel.cost import cost_optimal_threshold
from aps_intel.monitor import PSI_MODERATE, psi, workshop_band

P_ALERTA, P_AVISO = 0.001, 0.01  # el cambio se juzga con una prueba de bondad de ajuste; el PSI solo dice su tamaño


def _gof(expected: list[float], actual: list[float], n: int) -> float:
    """Valor p de ji cuadrada de la mezcla observada contra la de referencia; junta las celdas con menos de 5 esperadas."""
    e, a = np.asarray(expected, float) * n, np.asarray(actual, float) * n
    small = e < 5
    if small.any():
        e, a = np.append(e[~small], e[small].sum()), np.append(a[~small], a[small].sum())
    keep = e > 0
    if (a[~keep] > 0).any():  # aparece algo que la referencia nunca tuvo
        return 0.0
    e, a = e[keep], a[keep]
    if len(e) < 2:
        return 1.0
    return float(chisquare(a, e * a.sum() / e.sum()).pvalue)


@dataclass(frozen=True)
class Settings:
    costo_revision: float = 1_800.0   # horas de técnico + medio día de unidad detenida (MXN)
    costo_falla: float = 38_000.0     # extra de una falla en ruta frente a repararla en taller: grúa, carga, días parada
    capacidad_semana: int = 0         # revisiones por semana que admite el taller; 0 = sin límite
    fraccion_prueba: float = 1 / 3    # últimas semanas reservadas para la retrospectiva
    nivel: float = 0.90
    remuestreos: int = 2000
    semilla: int = 7


def _week(fecha: pd.Series) -> pd.Series:
    return fecha.dt.to_period("W-SUN").dt.start_time


# ---------------------------------------------------------------- prioridad
def type_rates(df: pd.DataFrame) -> pd.DataFrame:
    """Probabilidad de falla por tipo con previa beta ajustada por momentos (contracción hacia la tasa global)."""
    g = df.groupby("tipo_alerta")["falla"].agg(alertas="size", fallas="sum").reset_index()
    p0 = max(df["falla"].mean(), 1e-4)
    raw = g["fallas"] / g["alertas"]
    w = g["alertas"] / g["alertas"].sum()
    var = float((w * (raw - p0) ** 2).sum() - (w * raw * (1 - raw) / g["alertas"]).sum())  # varianza entre tipos
    strength = float(np.clip(p0 * (1 - p0) / var - 1, 2, 500)) if var > 0 else 500.0
    g["prob"] = (p0 * strength + g["fallas"]) / (strength + g["alertas"])
    g["previa_alertas"] = strength
    return g.sort_values("prob", ascending=False).reset_index(drop=True)


@dataclass
class Rule:
    modo: str                 # "puntaje" o "tipo"
    corte: float              # se atiende prioridad >= corte
    corte_sin_capacidad: float
    tasas: pd.DataFrame       # por tipo (siempre, para explicar)
    ref_tipos: dict           # proporción de cada tipo en el periodo de referencia
    ref_puntaje: dict | None  # cortes y proporciones del puntaje
    tasa_atencion: float      # fracción de alertas atendidas en la referencia

    def priority(self, df: pd.DataFrame) -> np.ndarray:
        if self.modo == "puntaje":
            return df["puntaje"].to_numpy(float)
        prob = dict(zip(self.tasas["tipo_alerta"], self.tasas["prob"], strict=True))
        p0 = float((self.tasas["fallas"].sum()) / self.tasas["alertas"].sum())
        return df["tipo_alerta"].map(prob).fillna(p0).to_numpy(float)

    def attend(self, df: pd.DataFrame) -> np.ndarray:
        return self.priority(df) >= self.corte


def _cap_threshold(priority: np.ndarray, weeks: pd.Series, cap: int) -> float:
    """El corte más bajo con el que la semana promedio no rebasa la capacidad."""
    n_weeks = max(1, weeks.nunique())
    budget = int(cap * n_weeks)
    if budget >= len(priority):
        return -np.inf
    s = np.sort(priority)[::-1]
    return float(np.nextafter(s[budget], np.inf)) if budget > 0 else float(np.nextafter(s[0], np.inf))


def fit_rule(df: pd.DataFrame, st: Settings) -> Rule:
    modo = "puntaje" if "puntaje" in df.columns else "tipo"
    tasas = type_rates(df)
    if modo == "puntaje":
        corte = cost_optimal_threshold(df["falla"].to_numpy(), df["puntaje"].to_numpy(float), st.costo_revision, st.costo_falla)
    else:
        corte = st.costo_revision / (st.costo_revision + st.costo_falla)
    base = Rule(modo, corte, corte, tasas, {}, None, 0.0)
    pr = base.priority(df)
    if st.capacidad_semana > 0:
        base.corte = max(corte, _cap_threshold(pr, _week(df["fecha"]), st.capacidad_semana))
    mix = df["tipo_alerta"].value_counts(normalize=True)
    base.ref_tipos = {str(k): float(v) for k, v in mix.items()}
    if modo == "puntaje":
        edges = [float(e) for e in np.unique(np.quantile(df["puntaje"], np.linspace(0, 1, 11)[1:-1]))]
        base.ref_puntaje = dict(edges=edges, proportions=_hist(df["puntaje"], edges))
    base.tasa_atencion = float((pr >= base.corte).mean())
    return base


def _hist(values: pd.Series, edges: list[float]) -> list[float]:
    idx = np.searchsorted(np.asarray(edges), values.to_numpy(float), side="right")
    counts = np.bincount(idx, minlength=len(edges) + 1).astype(float)
    return list(counts / max(1, len(values)))


# ---------------------------------------------------------------- costos y retrospectiva
def outcome(df: pd.DataFrame, flag: np.ndarray, st: Settings) -> dict:
    y = df["falla"].to_numpy(bool)
    flag = np.asarray(flag, bool)
    rev, en_ruta = int(flag.sum()), int((y & ~flag).sum())
    return dict(revisiones=rev, fallas_atendidas=int((y & flag).sum()), revisiones_sin_falla=int((flag & ~y).sum()),
                fallas_en_ruta=en_ruta, costo=float(st.costo_revision * rev + st.costo_falla * en_ruta))


def retrospective(df: pd.DataFrame, st: Settings) -> dict:
    """Regla elegida con las primeras semanas, medida en las últimas contra lo que se hizo."""
    week = _week(df["fecha"])
    weeks = np.sort(week.unique())
    n_test = max(2, int(round(len(weeks) * st.fraccion_prueba)))
    if len(weeks) - n_test < 4:
        return dict(ok=False, motivo="Se necesitan al menos 6 semanas para separar entrenamiento y prueba.")
    cut = weeks[-n_test]
    train, test = df[week < cut], df[week >= cut].reset_index(drop=True)
    if train["falla"].sum() < 3:
        return dict(ok=False, motivo="Hay muy pocas fallas en las primeras semanas para elegir la regla.")
    rule = fit_rule(train, st)
    flag = rule.attend(test)
    current = test["revisada"].to_numpy(bool)
    res = dict(ok=True, desde=test["fecha"].min(), hasta=test["fecha"].max(), semanas=n_test, alertas=len(test),
               regla=outcome(test, flag, st), actual=outcome(test, current, st),
               todo=outcome(test, np.ones(len(test), bool), st), nada=outcome(test, np.zeros(len(test), bool), st))

    # Bootstrap por semanas: ahorro = costo actual − costo de la regla.
    y = test["falla"].to_numpy(bool)
    per_alert = (st.costo_revision * current + st.costo_falla * (y & ~current)) - (st.costo_revision * flag + st.costo_falla * (y & ~flag))
    tw = _week(test["fecha"]).to_numpy()
    sums = pd.Series(per_alert).groupby(tw).sum().to_numpy()
    rng = np.random.default_rng(st.semilla)
    boot = sums[rng.integers(0, len(sums), size=(st.remuestreos, len(sums)))].sum(axis=1)
    a = (1 - st.nivel) / 2
    lo, hi = np.quantile(boot, [a, 1 - a])
    res.update(ahorro=float(sums.sum()), ahorro_lo=float(lo), ahorro_hi=float(hi),
               ahorro_semana=float(sums.sum() / n_test),
               veredicto="gana" if lo > 0 else ("pierde" if hi < 0 else "no se distingue"))
    return res


# ---------------------------------------------------------------- carga y monitor
def workload(df: pd.DataFrame, rule: Rule, level: float = 0.99) -> dict:
    weekly = df.groupby(_week(df["fecha"])).size()
    n = int(round(weekly.median()))
    lo, hi = workshop_band(rule.tasa_atencion, n, level)
    flagged = pd.Series(rule.attend(df)).groupby(_week(df["fecha"]).to_numpy()).sum()
    return dict(alertas_semana=n, banda=(lo, hi), esperado=rule.tasa_atencion * n,
                semana_max=int(flagged.max()), semana_min=int(flagged.min()))


def monitor_week(week_df: pd.DataFrame, rule: Rule) -> dict:
    n = len(week_df)
    flag = rule.attend(week_df)
    lo, hi = workshop_band(rule.tasa_atencion, n)
    mix = week_df["tipo_alerta"].value_counts(normalize=True)
    ref = rule.ref_tipos
    known = [t for t in ref]
    expected = [ref[t] for t in known] + [0.0]
    actual = [float(mix.get(t, 0.0)) for t in known] + [float(mix[~mix.index.isin(known)].sum())]
    psi_tipos = psi(expected, actual)
    nuevos = sorted(set(mix.index) - set(known))
    p_tipos = _gof(expected, actual, n)
    psi_punt, p_punt = None, 1.0
    if rule.modo == "puntaje" and "puntaje" in week_df:
        hist_now = _hist(week_df["puntaje"], rule.ref_puntaje["edges"])
        psi_punt = psi(rule.ref_puntaje["proportions"], hist_now)
        p_punt = _gof(rule.ref_puntaje["proportions"], hist_now, n)
    change = (mix.reindex(known + nuevos, fill_value=0) - pd.Series(ref).reindex(known + nuevos, fill_value=0)).sort_values()
    señales = dict(carga=not (lo <= int(flag.sum()) <= hi), mezcla=p_tipos < P_ALERTA and psi_tipos >= PSI_MODERATE,
                   puntaje=p_punt < P_ALERTA and (psi_punt or 0) >= PSI_MODERATE, nuevos=bool(nuevos))
    moderate = min(p_tipos, p_punt) < P_AVISO
    estado = "ALERTA" if any(señales.values()) else ("AVISO" if moderate else "OK")
    lista = week_df.assign(prioridad=rule.priority(week_df), atender=flag).sort_values("prioridad", ascending=False)
    return dict(estado=estado, alertas=n, atender=int(flag.sum()), banda=(lo, hi), psi_tipos=round(psi_tipos, 3),
                psi_puntaje=None if psi_punt is None else round(psi_punt, 3), nuevos=nuevos, señales=señales,
                mayor_alza=change.index[-1] if len(change) and change.iloc[-1] > 0.05 else None,
                lista=lista[lista["atender"]].drop(columns="atender"))


def decision_table(rule: Rule, df: pd.DataFrame, st: Settings) -> pd.DataFrame:
    t = rule.tasas.copy()
    flag = pd.Series(rule.attend(df), index=df.index)
    t["se_atiende"] = t["tipo_alerta"].map(flag.groupby(df["tipo_alerta"]).mean())
    t["costo_esperado_ignorar"] = t["prob"] * st.costo_falla
    t["decision"] = np.where(t["se_atiende"] >= 0.999, "Atender siempre",
                             np.where(t["se_atiende"] <= 0.001, "No mandar a taller",
                                      [f"Según puntaje: se atiende el {v:.0%}" for v in t["se_atiende"]]))
    return t


def analyse(df: pd.DataFrame, st: Settings) -> dict:
    rule = fit_rule(df, st)
    flag = rule.attend(df)
    out = dict(rule=rule, settings=st, tabla=decision_table(rule, df, st), carga=workload(df, rule),
               retro=retrospective(df, st), alertas=len(df), fallas=int(df["falla"].sum()),
               desde=df["fecha"].min(), hasta=df["fecha"].max(), en_historial=outcome(df, flag, st),
               actual_historial=outcome(df, df["revisada"].to_numpy(bool), st))
    if st.capacidad_semana > 0 and rule.corte > rule.corte_sin_capacidad:
        free = rule.priority(df) >= rule.corte_sin_capacidad
        weeks = max(1, _week(df["fecha"]).nunique())
        out["costo_capacidad_semana"] = (outcome(df, flag, st)["costo"] - outcome(df, free, st)["costo"]) / weeks
    return out
