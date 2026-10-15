## Summary

<!-- What changes and why. Link the issue: Closes #... -->

## Type

- [ ] Bug fix
- [ ] Feature / tooling
- [ ] Documentation
- [ ] Dependencies / CI

## Scientific integrity

- [ ] The frozen model, its parameters and features are unchanged.
- [ ] The consumed holdout is not used for any new decision, metric or tuning.
- [ ] No test or tolerance was relaxed to make CI pass.
- [ ] Every new number in the docs is reproducible by a command in the repository.
- [ ] Claims stay in scope (classification of current readings under the official cost; no time-to-failure, causal or real-money claims).

## Verification

<!-- Commands you ran and their result, e.g. pytest, python -B -m aps_intel.contract. -->

- [ ] All CI jobs pass.
- [ ] CHANGELOG.md updated when the change is user-visible.
