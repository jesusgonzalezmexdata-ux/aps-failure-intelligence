# Security policy

## Supported versions

Only the latest release receives fixes. The frozen model artifact is not retrained or patched; a fix means new code or documentation around it.

## Model artifact risk

`artifacts/model/aps_lightgbm.joblib` is a joblib/pickle file. **Loading a pickle can execute arbitrary code.** The SHA256 in `reports/final/execution.json` detects modified bytes; it does not make an untrusted file safe.

- Load the model only from a trusted checkout of this repository.
- Never load a `.joblib` file received from a third party, an issue, or a pull request.
- For inference, run the provided Docker image, which loads only the artifact shipped in this repository.

## Reporting a vulnerability

Do not open a public issue. Use GitHub's **private vulnerability reporting** on this repository (Security tab → *Report a vulnerability*). You will get an acknowledgement within 7 days. Please include the affected file or workflow, steps to reproduce and the impact.

In scope: code in `src/`, `sql/`, `dashboard/`, the Docker image and the GitHub Actions workflows. Out of scope: the third-party dataset and vulnerabilities in pinned upstream packages already published by their maintainers.
