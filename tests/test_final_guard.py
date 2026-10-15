import json

import numpy as np
import pytest

from aps_intel import final


def test_second_final_evaluation_is_refused(tmp_path):
    (tmp_path / final.OUT).mkdir(parents=True)
    (tmp_path / final.OUT / "execution.json").write_text("{}", encoding="utf-8")
    with pytest.raises(RuntimeError, match="already executed"):
        final.run(tmp_path)


def test_bootstrap_interval_contains_point_cost():
    rng = np.random.default_rng(0)
    y = rng.random(5000) < 0.02
    flag = y ^ (rng.random(5000) < 0.03)
    point = 10 * int((flag & ~y).sum()) + 500 * int((~flag & y).sum())
    ci = final.bootstrap_cost(y, flag, n=500)
    assert ci["low"] <= point <= ci["high"]


def test_recorded_final_evaluation_is_consistent():
    path = final.ROOT / final.OUT / "metrics.json"
    if not path.exists():
        pytest.skip("final evaluation not executed yet")
    m = json.loads(path.read_text(encoding="utf-8"))["holdout"]
    assert m["cost"] == 10 * m["fp"] + 500 * m["fn"]
    assert m["tp"] + m["fn"] == m["positives"]
    assert m["cost_bootstrap_95"]["low"] <= m["cost"] <= m["cost_bootstrap_95"]["high"]
