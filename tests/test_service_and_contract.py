import json

import joblib
import pytest
from fastapi.testclient import TestClient

from aps_intel import contract, service
from aps_intel.data import load_train, split_xy
from aps_intel.tuning import pipeline


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    X, y = split_xy(load_train())
    sample = X.index[(y == 1) | (X.index % 15 == 0)]
    model = pipeline(dict(n_estimators=30, num_leaves=15)).fit(X.loc[sample], y.loc[sample])
    tmp = tmp_path_factory.mktemp("svc")
    joblib.dump(model, tmp / "m.joblib")
    (tmp / "d.json").write_text(json.dumps(dict(threshold=0.5)), encoding="utf-8")
    service.MODEL_PATH, service.DECISION_PATH = tmp / "m.joblib", tmp / "d.json"
    service.bundle.cache_clear()
    yield TestClient(service.app), X, y
    service.bundle.cache_clear()


def test_health_reports_cost_matrix(client):
    body = client[0].get("/health").json()
    assert body["status"] == "ok" and body["cost_missed_failure"] == 500 and body["n_features"] == 170


def test_score_matches_model_and_accepts_missing(client):
    c, X, y = client
    rows = X[y == 1].head(3)
    trucks = [dict(readings={k: (None if v != v else v) for k, v in r.items()}) for r in rows.to_dict("records")]
    trucks.append(dict(readings={"aa_000": 100.0}))  # mostly missing truck still scores
    body = c.post("/score?explain=3", json=dict(trucks=trucks)).json()
    expected = service.bundle()["model"].predict_proba(rows)[:, 1]
    assert [r["score"] for r in body["results"][:3]] == pytest.approx(expected, abs=1e-6)
    assert body["results"][3]["missing_readings"] == 169
    assert len(body["results"][0]["drivers"]) == 3


def test_unknown_reading_is_rejected(client):
    r = client[0].post("/score", json=dict(trucks=[dict(readings={"zz_999": 1.0})]))
    assert r.status_code == 422


def test_sql_data_contract_passes(tmp_path):
    report = contract.run()
    assert report["passed"] == report["total"] == 11
