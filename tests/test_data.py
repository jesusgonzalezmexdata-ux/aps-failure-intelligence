"""Data integrity and the sealed official test set."""
import gzip
import hashlib
import json
from pathlib import Path

import pytest

from aps_intel import data
from aps_intel.audit import audit

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("name", [data.TRAIN_FILE, data.HOLDOUT_FILE])
def test_compressed_files_reproduce_official_bytes(name):
    raw = gzip.decompress((ROOT / "data/raw" / name).read_bytes())
    official = dict(line.split()[::-1] for line in (ROOT / "data/raw/SHA256SUMS").read_text().splitlines())
    assert hashlib.sha256(raw).hexdigest() == official[name.removesuffix(".gz")] == data.EXPECTED[name]["sha256"]


def test_train_shape_labels_and_target():
    frame = data.load_train()
    X, y = data.split_xy(frame)
    assert X.shape == (60_000, 170) and int(y.sum()) == 1_000
    assert set(frame[data.TARGET]) == {"pos", "neg"}


def test_holdout_is_sealed():
    for purpose in (None, "tuning", "final_evaluation", "FINAL"):
        with pytest.raises(data.HoldoutSealed):
            data.load_holdout(purpose)


def test_holdout_integrity_exposes_no_labels():
    integrity = data.holdout_integrity()
    assert integrity == dict(sha256=data.EXPECTED[data.HOLDOUT_FILE]["sha256"], rows=16_000,
                             columns=171, same_schema_as_train=True)


def test_tampered_file_is_rejected(tmp_path):
    (tmp_path / "data/raw").mkdir(parents=True)
    raw = gzip.decompress((ROOT / "data/raw" / data.TRAIN_FILE).read_bytes())
    (tmp_path / "data/raw" / data.TRAIN_FILE).write_bytes(gzip.compress(raw.replace(b"\npos,", b"\nneg,", 1)))
    with pytest.raises(ValueError, match="SHA256"):
        data.load_train(tmp_path)


def test_committed_audit_is_reproducible():
    committed = json.loads((ROOT / "reports/audit/train_audit.json").read_text(encoding="utf-8"))
    assert committed == json.loads(json.dumps(audit()))
