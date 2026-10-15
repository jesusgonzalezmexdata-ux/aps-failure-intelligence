"""SQL data contract executed with DuckDB (python -B -m aps_intel.contract).

The files are SHA256-verified first; DuckDB then reads them directly. The holdout is
exposed only as a view without the class column, so the contract cannot see its labels.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import duckdb

from aps_intel.data import HEADER_LINES, HOLDOUT_FILE, ROOT, TRAIN_FILE, _verified_bytes

SQL = Path("sql/contract.sql")
OUTPUT = Path("reports/contract/contract.json")


def checks(sql: str) -> list[tuple[str, str]]:
    parts = re.split(r"^-- name: (\w+)\s*$", sql, flags=re.M)[1:]
    return list(zip(parts[::2], (p.strip() for p in parts[1::2])))


def _reader(path: Path) -> str:
    return (f"read_csv('{path.as_posix()}', skip={HEADER_LINES}, header=true, nullstr='na', "
            "compression='gzip', sample_size=-1)")


def run(root: Path = ROOT) -> dict:
    root = Path(root)
    for name in (TRAIN_FILE, HOLDOUT_FILE):
        _verified_bytes(name, root)
    con = duckdb.connect()
    raw = root / "data" / "raw"
    con.execute(f"CREATE VIEW train AS SELECT * FROM {_reader(raw / TRAIN_FILE)}")
    con.execute(f"CREATE VIEW holdout_schema AS SELECT * EXCLUDE (class) FROM {_reader(raw / HOLDOUT_FILE)}")
    results = []
    for name, query in checks((root / SQL).read_text(encoding="utf-8")):
        ok, detail = con.execute(query).fetchone()
        results.append(dict(check=name, ok=bool(ok), detail=detail if isinstance(detail, (int, str)) else float(detail)))
    report = dict(engine=f"duckdb {duckdb.__version__}", passed=sum(r["ok"] for r in results),
                  total=len(results), checks=results)
    (root / OUTPUT).parent.mkdir(parents=True, exist_ok=True)
    (root / OUTPUT).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if report["passed"] != report["total"]:
        raise SystemExit(f"Data contract failed: {[r for r in results if not r['ok']]}")
    return report


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
