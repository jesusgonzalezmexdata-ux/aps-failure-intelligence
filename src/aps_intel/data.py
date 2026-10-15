"""Verified loading of the Scania APS data with a sealed official test set.

The official test set is the final, independent holdout. It can only be read
through ``load_holdout(purpose=FINAL_EVALUATION)``; every other attempt raises.
All development decisions use the training set only.
"""
from __future__ import annotations

import gzip
import hashlib
import io
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
TRAIN_FILE = "aps_failure_training_set.csv.gz"
HOLDOUT_FILE = "aps_failure_test_set.csv.gz"
HEADER_LINES = 20  # Scania license header preceding the CSV header row
TARGET = "class"
POSITIVE = "pos"
EXPECTED = {
    TRAIN_FILE: dict(sha256="bb484302e3a3a1c8ef5e1f0129c4dc7cbd58f350867f95b575461ca21ab6b9da",
                     rows=60_000),
    HOLDOUT_FILE: dict(sha256="2cdf6f7661c7b4c63333c93cdec36a3a82350176b604a2312cf82799fb2712f3",
                       rows=16_000),
}
N_COLUMNS = 171
FINAL_EVALUATION = "FINAL_EVALUATION"


class HoldoutSealed(PermissionError):
    """Raised when the official test set is requested outside the final evaluation."""


def _verified_bytes(name: str, root: Path = ROOT) -> bytes:
    raw = gzip.decompress((Path(root) / "data" / "raw" / name).read_bytes())
    digest = hashlib.sha256(raw).hexdigest()
    if digest != EXPECTED[name]["sha256"]:
        raise ValueError(f"{name}: SHA256 {digest} does not match the official file")
    return raw


def _parse(raw: bytes, name: str) -> pd.DataFrame:
    frame = pd.read_csv(io.BytesIO(raw), skiprows=HEADER_LINES, na_values="na")
    if frame.shape != (EXPECTED[name]["rows"], N_COLUMNS) or frame.columns[0] != TARGET:
        raise ValueError(f"{name}: unexpected shape {frame.shape} or first column {frame.columns[0]}")
    if not frame[TARGET].isin(["pos", "neg"]).all():
        raise ValueError(f"{name}: unexpected class labels")
    return frame


def split_xy(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Features (float) and binary target (1 = APS component failure)."""
    return frame.drop(columns=TARGET).astype(float), frame[TARGET].eq(POSITIVE).astype(int)


def load_train(root: Path = ROOT) -> pd.DataFrame:
    return _parse(_verified_bytes(TRAIN_FILE, root), TRAIN_FILE)


def holdout_integrity(root: Path = ROOT) -> dict:
    """Hash, row count and schema of the sealed holdout, without exposing labels."""
    raw = _verified_bytes(HOLDOUT_FILE, root)
    header = io.BytesIO(raw).read().decode("ascii").splitlines()[HEADER_LINES].split(",")
    train_header = load_train(root).columns.tolist()
    return dict(sha256=EXPECTED[HOLDOUT_FILE]["sha256"], rows=EXPECTED[HOLDOUT_FILE]["rows"],
                columns=len(header), same_schema_as_train=header == train_header)


def load_holdout(purpose: str | None = None, root: Path = ROOT) -> pd.DataFrame:
    if purpose != FINAL_EVALUATION:
        raise HoldoutSealed("The official test set is sealed until the single final evaluation.")
    return _parse(_verified_bytes(HOLDOUT_FILE, root), HOLDOUT_FILE)
