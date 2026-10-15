# Contributing

This repository is a reproducible decision-science case on public Scania data. Contributions follow the same discipline as the original work: **evidence first, frozen results protected**.

## What is welcome

- Bug reports and fixes in code, tests, CI, SQL contract, service, dashboard or Docker.
- Documentation improvements and translations.
- Reproducibility reports on other platforms.
- New analyses that **do not** change the frozen model or use the official test set for decisions.

## What is out of scope

The selected LightGBM configuration, its threshold and the official test set (16,000 trucks) are frozen once the single final evaluation runs (`reports/final/execution.json`). Pull requests that retune, change the threshold or features using test-set results, or report new test-set scores as if they were independent, will be declined. A new model needs new, independent data; propose it first as an *Experiment proposal* issue.

## Workflow

1. **Open an issue** with the matching template and wait for agreement before large changes.
2. **Branch** from `main`: `fix/...`, `feat/...`, `docs/...`, `chore/...`.
3. **Set up** Python 3.13 and run from the repository root:
   ```bash
   pip install -r requirements-dev.txt
   PYTHONPATH=src python -B -m aps_intel.contract
   python -B -m pytest -q
   ```
4. **Commit** with [Conventional Commits](https://www.conventionalcommits.org/), one logical change per commit.
5. **Open a pull request** and complete its checklist. All CI jobs must pass.

## Scientific integrity rules

- Never relax a test or a tolerance to make CI pass; explain and fix the cause.
- Any new number in documentation must be reproducible by a command in the repository.
- Keep claims within scope: classification of current readings under the official cost matrix; no time-to-failure, causal or real-money claims.

By contributing you agree that your contribution is licensed under the Apache License 2.0 and that you follow the [Code of Conduct](CODE_OF_CONDUCT.md).
