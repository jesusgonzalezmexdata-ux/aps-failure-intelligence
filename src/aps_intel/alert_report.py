"""Reporte de una página (HTML imprimible) del calibrador de alertas."""
from __future__ import annotations

import datetime as dt
import html

import pandas as pd

REFS = [
    ("NOM-068-SCT-2-2014", "Condiciones físico-mecánicas: la regla deja evidencia de qué alertas se atienden y por qué"),
    ("ISO 39001 · 8.1", "Seguridad vial: control operacional de fallas en ruta"),
    ("ISO 55001 · 6.2", "Gestión de activos: decisión por costo con criterios definidos antes de actuar"),
]


def mxn(v) -> str:
    if v is None or pd.isna(v):
        return "—"
    return f"${v / 1e6:,.2f} M" if abs(v) >= 1e6 else f"${v:,.0f}"


def _e(x) -> str:
    return html.escape(str(x))


def _table(df: pd.DataFrame) -> str:
    head = "".join(f"<th>{_e(c)}</th>" for c in df.columns)
    body = "".join("<tr>" + "".join(f"<td>{_e(v)}</td>" for v in row) + "</tr>" for row in df.itertuples(index=False))
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def rule_text(r) -> str:
    rule = r["rule"]
    if rule.modo == "puntaje":
        return f"Manda a taller toda alerta con puntaje ≥ {rule.corte:g}."
    attend = r["tabla"].loc[r["tabla"]["decision"] == "Atender siempre", "tipo_alerta"].tolist()
    skip = r["tabla"].loc[r["tabla"]["decision"] == "No mandar a taller", "tipo_alerta"].tolist()
    text = f"Manda a taller los tipos con probabilidad de falla ≥ {rule.corte:.1%} ({len(attend)} de {len(r['tabla'])} tipos)."
    if skip:
        text += " No vale la revisión: " + ", ".join(skip) + "."
    return text


def headline(r) -> str:
    c, retro = r["carga"], r["retro"]
    text = f"{rule_text(r)} Con ≈ {c['alertas_semana']} alertas por semana, espera entre {c['banda'][0]} y {c['banda'][1]} revisiones; una semana fuera de la banda que corresponde a sus alertas indica que algo cambió."
    if retro.get("ok"):
        if retro["veredicto"] == "gana":
            text += (f" En las últimas {retro['semanas']} semanas habría costado {mxn(retro['ahorro'])} menos que lo que se hizo "
                     f"(≈ {mxn(retro['ahorro_semana'])} por semana).")
        elif retro["veredicto"] == "pierde":
            text += " En la retrospectiva la regla costó más que la práctica actual: no conviene adoptarla."
        else:
            text += " En la retrospectiva la diferencia contra la práctica actual no es distinguible de cero."
    return text


def report_html(r, issues=None, flota: str = "Flota", data_rows=None, semana=None) -> str:
    st, rule, retro, c = r["settings"], r["rule"], r["retro"], r["carga"]
    issues = issues or []
    parts = [f"<h1>Calibrador de alertas · {_e(flota)}</h1>",
             f"<p class='meta'>Historial del {r['desde']:%d/%m/%Y} al {r['hasta']:%d/%m/%Y} · generado el {dt.date.today():%d/%m/%Y} · "
             "Jesús R. L. González</p>", f"<p class='lead'>{_e(headline(r))}</p>"]
    if data_rows:
        err = sum(i.nivel == "error" for i in issues)
        parts.append(f"<h2>1 · Datos</h2><p>{data_rows[1]:,} de {data_rows[0]:,} alertas válidas · {err} excluidas por error · "
                     f"{r['fallas']} fallas confirmadas. Prioridad por {'puntaje de la telemática' if rule.modo == 'puntaje' else 'tipo de alerta'}. "
                     "Los datos se procesaron en el equipo del usuario.</p>")
    t = r["tabla"]
    parts.append("<h2>2 · Regla por tipo de alerta</h2>" + _table(pd.DataFrame({
        "Tipo de alerta": t["tipo_alerta"], "Alertas": t["alertas"], "Fallas": t["fallas"],
        "P(falla)": t["prob"].map("{:.1%}".format), "Costo esperado de ignorarla": t["costo_esperado_ignorar"].map(mxn),
        "Decisión": t["decision"]}))
        + f"<p class='note'>Costo de una revisión {mxn(st.costo_revision)}; costo extra de una falla en ruta {mxn(st.costo_falla)}. "
          f"Una alerta vale la revisión si P(falla) × {mxn(st.costo_falla)} supera {mxn(st.costo_revision)}, es decir P(falla) ≥ "
          f"{st.costo_revision / (st.costo_revision + st.costo_falla):.1%}. P(falla) se contrae hacia la tasa global en tipos con pocas alertas.</p>")
    cap = f" Capacidad del taller: {st.capacidad_semana} revisiones por semana." if st.capacidad_semana else ""
    if r.get("costo_capacidad_semana"):
        cap += f" Respetarla cuesta ≈ {mxn(r['costo_capacidad_semana'])} por semana en fallas en ruta."
    parts.append(f"<h2>3 · Carga de taller esperada</h2><p>Con {c['alertas_semana']} alertas en una semana típica, la regla manda "
                 f"≈ {c['esperado']:.0f} unidades a taller; la banda del 99 % es {c['banda'][0]}–{c['banda'][1]}. Fuera de la banda: revisar "
                 f"si cambió la telemática, la ruta o la flota antes de culpar a la regla.{_e(cap)}</p>")
    parts.append("<h2>4 · ¿Qué tan confiable es?</h2>")
    if retro.get("ok"):
        rows = [("Regla calibrada", retro["regla"]), ("Lo que se hizo", retro["actual"]),
                ("Revisar todo", retro["todo"]), ("No revisar nada", retro["nada"])]
        parts.append(f"<p>Regla elegida con las semanas previas al {retro['desde']:%d/%m/%Y} y medida en las {retro['semanas']} siguientes "
                     f"({retro['alertas']} alertas):</p>" + _table(pd.DataFrame({
                         "Estrategia": [n for n, _ in rows], "Revisiones": [o["revisiones"] for _, o in rows],
                         "Sin falla": [o["revisiones_sin_falla"] for _, o in rows], "Fallas en ruta": [o["fallas_en_ruta"] for _, o in rows],
                         "Costo": [mxn(o["costo"]) for _, o in rows]}))
                     + f"<p>Ahorro contra lo que se hizo: <b>{mxn(retro['ahorro'])}</b> (intervalo {st.nivel:.0%}: {mxn(retro['ahorro_lo'])} a "
                       f"{mxn(retro['ahorro_hi'])}, bootstrap por semanas). Veredicto: <b>{_e(retro['veredicto'])}</b>.</p>")
        if retro["veredicto"] != "gana":
            parts.append("<p class='warn'>Criterio de abandono: el intervalo del ahorro incluye cero o es negativo. No pasar a modo sombra.</p>")
    else:
        parts.append(f"<p>{_e(retro.get('motivo', 'Sin retrospectiva.'))}</p>")
    parts.append("<ul><li>Supuesto: una falla encontrada en la revisión habría terminado en avería en ruta. Si muchas se habrían "
                 "resuelto solas, el beneficio real es menor.</li><li>Una alerta no revisada sin avería en 30 días cuenta como «sin falla»; "
                 "una falla lenta que aparece después queda fuera.</li><li>Solo decide entre alertas: las averías sin alerta previa no "
                 "cambian con esta regla.</li></ul>")
    if semana is not None:
        lst = semana["lista"].head(25)
        parts.append(f"<h2>5 · Semana nueva: estado {semana['estado']}</h2><p>{semana['alertas']} alertas; atender {semana['atender']} "
                     f"(banda {semana['banda'][0]}–{semana['banda'][1]}). Cambio en la mezcla de alertas: PSI {semana['psi_tipos']}"
                     + (f"; subió sobre todo «{_e(semana['mayor_alza'])}»" if semana["mayor_alza"] else "") + ".</p>"
                     + _table(pd.DataFrame({"Unidad": lst["unidad"], "Fecha": lst["fecha"].dt.strftime("%d/%m/%Y"),
                                            "Alerta": lst["tipo_alerta"], "Prioridad": lst["prioridad"].map("{:.3g}".format)})))
    parts.append("<h2>Referencias</h2>" + _table(pd.DataFrame(REFS, columns=["Requisito", "Cómo se atiende"])))
    css = """body{font-family:Barlow,system-ui,-apple-system,'Segoe UI',sans-serif;color:#0E0F11;max-width:900px;margin:24px auto;
padding:0 16px;font-size:14px;line-height:1.5}h1{font:700 26px/1.1 'Barlow Condensed','Arial Narrow',sans-serif;margin-bottom:4px}
h2{font:700 18px/1.2 'Barlow Condensed','Arial Narrow',sans-serif;margin:22px 0 6px;border-bottom:3px solid #0E0F11;padding-bottom:2px}
.meta{color:#4A4E54;margin-top:0}.lead{font-size:15px;background:#FFD21F;padding:10px 12px;border-top:4px solid #0E0F11}
table{border-collapse:collapse;margin:6px 0;font-size:13px}th,td{border:1px solid #C9CDD1;padding:4px 8px;text-align:left}
th{background:#F6F7F5}.note{color:#4A4E54;font-size:12.5px}.warn{background:#FDECEA;padding:8px 10px;border-left:4px solid #D7261E}
@media print{body{margin:0}h2{break-after:avoid}}"""
    return ("<!doctype html><html lang='es'><head><meta charset='utf-8'><title>Calibrador de alertas · "
            f"{_e(flota)}</title><style>{css}</style></head><body>" + "".join(parts)
            + "<p class='note'>© 2026 Jesús R. L. González · Código bajo licencia Apache 2.0</p></body></html>")
