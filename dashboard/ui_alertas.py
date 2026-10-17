"""Modo «Tus alertas»: el método del caso Scania aplicado al historial de alertas de una flota, en el navegador."""
import altair as alt
import pandas as pd
import streamlit as st

from aps_intel import alert_calibrator as ac
from aps_intel import alert_intake as ai
from aps_intel import alert_report as rp

NEGRO, GRIS, AMARILLO, LINEA = "#0E0F11", "#4A4E54", "#FFD21F", "#C9CDD1"


def _md(text: str) -> str:
    return text.replace("$", "\\$")


@st.cache_data(show_spinner=False)
def _template():
    return ai.template_bytes()


@st.cache_data(show_spinner=False)
def _examples():
    return ai.to_csv_bytes(ai.example_with_errors()), ai.to_csv_bytes(ai.example_week())


@st.cache_data(show_spinner="Validando y calibrando…")
def _run(content: bytes, name: str, settings: ac.Settings):
    raw = ai.read_table(content, name)
    df, issues = ai.validate(raw)
    return len(raw), df, issues, ac.analyse(df, settings)


def _rango(lo: float, hi: float) -> str:
    if max(abs(lo), abs(hi)) >= 1e6:
        return f"${lo / 1e6:,.2f}–{hi / 1e6:,.2f} M"
    return f"${lo / 1e3:,.0f}–{hi / 1e3:,.0f} k"


def _issues(issues):
    return pd.DataFrame([dict(Nivel=i.nivel, Fila=str(i.fila) if i.fila else "—", Detalle=i.mensaje) for i in issues])


def _load_chart(df, r):
    week = df["fecha"].dt.to_period("W-SUN").dt.start_time
    rule = r["rule"]
    t = pd.DataFrame({"semana": week, "Regla calibrada": rule.attend(df), "Lo que se hizo": df["revisada"], "alertas": 1})
    t = t.groupby("semana").sum().reset_index()
    t[["lo", "hi"]] = [ac.workshop_band(rule.tasa_atencion, int(n)) for n in t["alertas"]]
    band = alt.Chart(t).mark_area(color=AMARILLO, opacity=0.45, interpolate="step-after").encode(
        x="semana:T", y="lo:Q", y2="hi:Q", tooltip=[alt.Tooltip("semana:T"), "alertas:Q", "lo:Q", "hi:Q"])
    long = t.melt("semana", ["Regla calibrada", "Lo que se hizo"], var_name="serie", value_name="revisiones")
    lines = alt.Chart(long).mark_line(point=True, strokeWidth=2).encode(
        x=alt.X("semana:T", title=None), y=alt.Y("revisiones:Q", title="Unidades a taller por semana"),
        color=alt.Color("serie:N", scale=alt.Scale(domain=["Regla calibrada", "Lo que se hizo"], range=[NEGRO, GRIS]),
                        legend=alt.Legend(orient="top", title=None)),
        tooltip=["semana:T", "serie:N", "revisiones:Q"])
    return (band + lines).properties(height=280, title="Carga de taller por semana (en amarillo, la banda esperada según las alertas de esa semana)")


def render():
    st.subheader("Calibrador de alertas con tu historial")
    st.markdown("Sube las alertas de tu telemática con lo que pasó después y obtén **qué alertas mandar a taller, cuántas "
                "revisiones esperar por semana y cuándo sospechar que algo cambió**. **El archivo se procesa en tu navegador: "
                "no se envía a ningún servidor.**")
    a, b = st.columns(2)
    a.download_button("Descargar plantilla de Excel (con datos de ejemplo)", _template(), "plantilla_alertas.xlsx",
                      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    if b.button("O prueba con un historial de ejemplo que trae errores de captura"):
        st.session_state["alertas_ejemplo"] = True
    st.caption("Columnas: *unidad, fecha, tipo_alerta, revisada (sí/no), falla (sí/no)* y, si la telemática lo da, *puntaje*. "
               "Acepta .xlsx o .csv. Mínimo 8 semanas; ideal 6 meses.")
    up = st.file_uploader("Historial de alertas (.xlsx o .csv)", type=["xlsx", "csv"])
    flota = st.text_input("Nombre de la flota (aparece en el reporte)", "Mi flota")
    c1, c2, c3 = st.columns(3)
    c_rev = c1.number_input("Costo de una revisión (MXN)", 0, 1_000_000, 1_800, 100,
                            help="Horas de técnico y tiempo de la unidad detenida, aunque no se encuentre nada.")
    c_fal = c2.number_input("Costo extra de una falla en ruta (MXN)", 1, 10_000_000, 38_000, 1_000,
                            help="Grúa, carga retrasada o perdida y días de unidad parada, frente a repararla en taller.")
    cap = c3.number_input("Revisiones por semana que admite el taller (0 = sin límite)", 0, 10_000, 0, 1)

    if up is not None:
        content, name = up.getvalue(), up.name
    elif st.session_state.get("alertas_ejemplo"):
        content, name = _examples()[0], "ejemplo.csv"
        st.caption("Analizando el ejemplo: 140 tractocamiones, 26 semanas, 8 tipos de alerta; 4 filas con error y 1 repetida. "
                   "Práctica actual: siempre aceite, balatas y aire; 3 de cada 10 de lo demás.")
    else:
        st.info("Para probar, descarga la plantilla y súbela tal cual, o usa el historial de ejemplo con errores.")
        return

    settings = ac.Settings(costo_revision=float(c_rev), costo_falla=float(c_fal), capacidad_semana=int(cap))
    try:
        n_raw, df, issues, r = _run(content, name, settings)
    except ai.DataError as exc:
        st.error(str(exc))
        return
    errors = [i for i in issues if i.nivel == "error"]
    st.markdown(f"**{len(df):,} de {n_raw:,} alertas válidas** · {len(errors)} filas excluidas · {len(issues) - len(errors)} avisos · "
                f"prioridad por **{'puntaje' if r['rule'].modo == 'puntaje' else 'tipo de alerta'}**")
    if issues:
        with st.expander("Ver errores y avisos de los datos", expanded=bool(errors)):
            st.dataframe(_issues(issues), hide_index=True)

    retro, carga = r["retro"], r["carga"]
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Regla", f"puntaje ≥ {r['rule'].corte:g}" if r["rule"].modo == "puntaje" else f"P(falla) ≥ {r['rule'].corte:.1%}", border=True)
    k2.metric("Revisiones por semana", f"{carga['banda'][0]}–{carga['banda'][1]}", border=True,
              help=f"Banda del 99 % para una semana típica de ≈ {carga['alertas_semana']} alertas.")
    if retro.get("ok"):
        k3.metric(f"Ahorro en {retro['semanas']} semanas de prueba", _md(rp.mxn(retro["ahorro"])), border=True,
                  help="Contra lo que se hizo en esas semanas, con la regla elegida solo con las semanas anteriores.")
        k4.metric(f"Intervalo {settings.nivel:.0%} del ahorro", _md(_rango(retro["ahorro_lo"], retro["ahorro_hi"])),
                  retro["veredicto"], delta_color="normal" if retro["veredicto"] == "gana" else "inverse", border=True)
    (st.success if retro.get("veredicto", "gana") == "gana" else st.warning)(_md(rp.headline(r)))
    if r.get("costo_capacidad_semana"):
        st.caption(_md(f"Respetar la capacidad del taller cuesta ≈ {rp.mxn(r['costo_capacidad_semana'])} por semana en fallas en ruta."))

    st.markdown("**Decisión por tipo de alerta**")
    t = r["tabla"]
    st.dataframe(pd.DataFrame({"Tipo de alerta": t["tipo_alerta"], "Alertas": t["alertas"], "Fallas": t["fallas"],
                               "P(falla)": t["prob"], "Costo esperado de ignorarla": t["costo_esperado_ignorar"], "Decisión": t["decision"]})
                 .style.format({"P(falla)": "{:.1%}", "Costo esperado de ignorarla": "${:,.0f}"}), hide_index=True)
    if retro.get("ok"):
        rows = [("Regla calibrada", retro["regla"]), ("Lo que se hizo", retro["actual"]), ("Revisar todo", retro["todo"]),
                ("No revisar nada", retro["nada"])]
        st.markdown(f"**Retrospectiva:** regla elegida con las semanas previas al {retro['desde']:%d/%m/%Y}, medida en las {retro['semanas']} siguientes")
        st.dataframe(pd.DataFrame({"Estrategia": [n for n, _ in rows], "Revisiones": [o["revisiones"] for _, o in rows],
                                   "Sin falla": [o["revisiones_sin_falla"] for _, o in rows],
                                   "Fallas en ruta": [o["fallas_en_ruta"] for _, o in rows], "Costo": [o["costo"] for _, o in rows]})
                     .style.format({"Costo": "${:,.0f}"}), hide_index=True)
    else:
        st.caption(retro.get("motivo", ""))
    st.altair_chart(_load_chart(df, r), use_container_width=True)

    st.markdown("#### Semana nueva: lista de esta semana y monitor")
    st.caption("Sube las alertas de la semana (sin resultados todavía). Sale la lista de unidades a mandar a taller y una señal si la "
               "carga o la mezcla de alertas se salen de lo esperado.")
    wk_up = st.file_uploader("Alertas de la semana (.xlsx o .csv)", type=["xlsx", "csv"], key="semana")
    if st.button("Usar una semana de ejemplo (con una actualización de firmware que dispara alertas ABS)"):
        st.session_state["semana_ejemplo"] = True
    semana = None
    week_bytes = (wk_up.getvalue(), wk_up.name) if wk_up is not None else (
        (_examples()[1], "semana.csv") if st.session_state.get("semana_ejemplo") else None)
    if week_bytes:
        try:
            wdf, _ = ai.validate(ai.read_table(*week_bytes), need_outcome=False)
            if r["rule"].modo == "puntaje" and "puntaje" not in wdf:
                raise ai.DataError("La regla usa el puntaje, pero la semana nueva no lo trae.")
            semana = ac.monitor_week(wdf, r["rule"])
        except ai.DataError as exc:
            st.error(str(exc))
    if semana:
        msg = (f"Estado **{semana['estado']}** · {semana['alertas']} alertas · atender **{semana['atender']}** "
               f"(banda {semana['banda'][0]}–{semana['banda'][1]}) · cambio en la mezcla PSI {semana['psi_tipos']}")
        if semana["mayor_alza"]:
            msg += f"; subió sobre todo «{semana['mayor_alza']}»"
        if semana["nuevos"]:
            msg += f"; tipos nuevos: {', '.join(semana['nuevos'])}"
        {"OK": st.success, "AVISO": st.warning, "ALERTA": st.error}[semana["estado"]](msg + ".")
        if semana["estado"] != "OK":
            st.caption("La regla no cambia sola: revisa si hubo actualización de la telemática, unidades nuevas o una ruta distinta "
                       "antes de recalibrar con más historial.")
        lst = semana["lista"]
        lst = pd.DataFrame({"Unidad": lst["unidad"], "Fecha": lst["fecha"].dt.strftime("%d/%m/%Y"), "Alerta": lst["tipo_alerta"],
                            ("Puntaje" if r["rule"].modo == "puntaje" else "P(falla) del tipo"): lst["prioridad"].round(3)})
        st.dataframe(lst, hide_index=True)
        st.download_button("Descargar la lista de esta semana (CSV)", ai.to_csv_bytes(lst), "lista_taller_semana.csv", "text/csv")
    html_report = rp.report_html(r, issues, flota, (n_raw, len(df)), semana)
    st.download_button("Descargar reporte de una página (HTML, imprimible a PDF)", html_report.encode("utf-8"),
                       "calibrador_alertas.html", "text/html", type="primary")
