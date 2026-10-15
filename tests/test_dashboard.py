from pathlib import Path

import pytest

AppTest = pytest.importorskip("streamlit.testing.v1").AppTest
APP = Path(__file__).resolve().parents[1] / "dashboard" / "app.py"
READY = (APP.parents[1] / "reports" / "analysis" / "oof_scores.csv").exists()


def test_dashboard_renders():
    at = AppTest.from_file(str(APP), default_timeout=120).run()
    assert not at.exception
    if not READY:
        assert at.error
        return
    labels = [m.label for m in at.metric]
    assert "Threshold (from training)" in labels and "Failures caught" in labels


@pytest.mark.skipif(not READY, reason="analysis outputs not generated yet")
def test_higher_miss_cost_never_lowers_recall():
    at = AppTest.from_file(str(APP), default_timeout=120).run()
    recall = lambda: float(next(m for m in at.metric if m.label == "Failures caught").delta.split("%")[0])  # noqa: E731
    base = recall()
    at.number_input[1].set_value(5000).run()
    assert recall() >= base
