"""MVP «Calibrador de alertas por costo»: entrada, regla, retrospectiva, monitor y reporte."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from aps_intel import alert_calibrator as ac
from aps_intel import alert_intake as ai
from aps_intel import alert_report as rp


@pytest.fixture(scope="module")
def hist():
    df, issues = ai.validate(ai.example_data())
    return df, issues


def test_template_round_trip(hist):
    pytest.importorskip("openpyxl")
    df, _ = ai.validate(ai.read_table(ai.template_bytes(), "plantilla.xlsx"))
    assert len(df) == len(hist[0]) and {"puntaje", "revisada", "falla"} <= set(df.columns)


def test_errors_are_reported_by_row_and_excluded():
    raw = ai.read_table(ai.to_csv_bytes(ai.example_with_errors()), "x.csv")
    df, issues = ai.validate(raw)
    errors = [i for i in issues if i.nivel == "error"]
    assert len(errors) == 3 and all(i.fila for i in errors)
    assert any("repetidas" in i.mensaje for i in issues)
    assert len(df) == len(raw) - 3 - 1


def test_semicolon_csv_aliases_and_spanish_flags():
    text = "Económico;Fecha;Código;Revisado;Avería\n" + "\n".join(
        f"T-{i % 9};{1 + i % 28:02d}/0{1 + i // 28}/2026;A{i % 3};{'Sí' if i % 2 else 'no'};{'SI' if i % 7 == 0 else 'No'}" for i in range(120))
    df, _ = ai.validate(ai.read_table(text.encode(), "export.csv"))
    assert {"unidad", "tipo_alerta", "fecha"} <= set(df.columns)
    assert df["revisada"].dtype == bool and df["falla"].sum() > 0


def test_missing_column_and_too_few_failures_raise():
    with pytest.raises(ai.DataError, match="Faltan columnas"):
        ai.validate(pd.DataFrame({"unidad": ["a"], "fecha": ["01/01/2026"]}))
    df = ai.example_data()
    df["falla"] = "no"
    with pytest.raises(ai.DataError, match="fallas"):
        ai.validate(df)


def test_type_rates_shrink_small_types(hist):
    df = hist[0].copy()
    extra = pd.DataFrame(dict(unidad="T-1", fecha=df["fecha"].iloc[:2], tipo_alerta="Rara", revisada=True, falla=True, puntaje=50.0))
    t = ac.type_rates(pd.concat([df, extra], ignore_index=True)).set_index("tipo_alerta")
    assert t.loc["Rara", "prob"] < 0.6  # 2 de 2 no basta para decir 100 %


def test_type_mode_follows_bayes_rule(hist):
    df = hist[0].drop(columns="puntaje")
    st = ac.Settings()
    r = ac.analyse(df, st)
    p = st.costo_revision / (st.costo_revision + st.costo_falla)
    t = r["tabla"]
    assert (t.loc[t["prob"] >= p, "decision"] == "Atender siempre").all()
    assert (t.loc[t["prob"] < p, "decision"] == "No mandar a taller").all()


def test_more_expensive_failures_never_reduce_checks(hist):
    df = hist[0]
    a = ac.fit_rule(df, ac.Settings(costo_falla=10_000)).attend(df).sum()
    b = ac.fit_rule(df, ac.Settings(costo_falla=200_000)).attend(df).sum()
    assert b >= a


def test_capacity_is_respected_on_average(hist):
    df = hist[0]
    r = ac.analyse(df, ac.Settings(capacidad_semana=12))
    weeks = df["fecha"].dt.to_period("W-SUN").nunique()
    assert r["rule"].attend(df).sum() <= 12 * weeks
    assert r["costo_capacidad_semana"] > 0


def test_retrospective_beats_current_practice_on_example(hist):
    retro = ac.analyse(hist[0], ac.Settings())["retro"]
    assert retro["ok"] and retro["veredicto"] == "gana"
    assert retro["ahorro_lo"] > 0 and retro["regla"]["fallas_en_ruta"] < retro["actual"]["fallas_en_ruta"]
    assert retro["ahorro"] == pytest.approx(retro["actual"]["costo"] - retro["regla"]["costo"])


def test_retrospective_uses_only_earlier_weeks(hist):
    df = hist[0]
    st = ac.Settings()
    retro = ac.retrospective(df, st)
    week = df["fecha"].dt.to_period("W-SUN").dt.start_time
    train = df[week < week[df["fecha"] >= retro["desde"]].min()]
    rule = ac.fit_rule(train, st)
    test = df[df["fecha"] >= retro["desde"]]
    assert ac.outcome(test, rule.attend(test), st) == retro["regla"]


def test_monitor_flags_firmware_burst_and_lists_checks(hist):
    rule = ac.fit_rule(hist[0], ac.Settings())
    week, _ = ai.validate(ai.example_week(), need_outcome=False)
    m = ac.monitor_week(week, rule)
    assert m["estado"] == "ALERTA" and m["señales"]["mezcla"] and m["mayor_alza"] == "Sensor ABS intermitente"
    assert len(m["lista"]) == m["atender"] and m["lista"]["prioridad"].is_monotonic_decreasing


def test_monitor_false_alarms_stay_rare(hist):
    rule = ac.fit_rule(hist[0], ac.Settings())
    alarms = sum(ac.monitor_week(ai.validate(ai.example_data(weeks=1, seed=100 + s, start="2026-10-05", outcome=False),
                                             need_outcome=False)[0], rule)["estado"] == "ALERTA" for s in range(60))
    assert alarms <= 4  # semanas tranquilas: ≤ 7 % de falsas alarmas


def test_report_is_self_contained(hist):
    df, issues = hist
    r = ac.analyse(df, ac.Settings())
    week, _ = ai.validate(ai.example_week(), need_outcome=False)
    html = rp.report_html(r, issues, "Flota prueba", (len(df), len(df)), ac.monitor_week(week, r["rule"]))
    assert "Calibrador de alertas · Flota prueba" in html and "Semana nueva" in html and "Apache 2.0" in html
    assert "<script" not in html


def test_ui_mode_renders_example():
    AppTest = pytest.importorskip("streamlit.testing.v1").AppTest
    app = Path(__file__).resolve().parents[1] / "dashboard" / "app.py"
    at = AppTest.from_file(str(app), default_timeout=180).run()
    at.button_group[0].set_value("Tus alertas").run()
    at.button[0].click().run()
    assert not at.exception
    assert any(m.label.startswith("Ahorro en") and "476" in m.value for m in at.metric)
    np.testing.assert_equal(any("gana" in str(m.delta) for m in at.metric), True)
