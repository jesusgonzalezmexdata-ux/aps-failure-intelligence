# Changelog

All notable changes follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and [Semantic Versioning](https://semver.org/).

## [1.0.0] — 2026-10-15

### Added
- Byte-verified Scania APS data with the official test set sealed in code.
- Training audit, problem contract and the official cost (10 per check, 500 per missed failure).
- Nested cost cross-validation, logistic baseline, pre-registered candidates and 12-configuration tuning.
- Single final evaluation: official cost 11,540 (95 % interval 7,940–15,661), recall 95.7 %, 44.6 checks per 1,000 trucks.
- Phase-7 analysis: bootstrap uncertainty, cost-ratio sensitivity, calibration, error groups, LightGBM drivers.
- DuckDB SQL data contract, FastAPI triage service, Docker image, Streamlit decision dashboard.
- Model Card, governance files and CI (tests, dashboard, image smoke test).
