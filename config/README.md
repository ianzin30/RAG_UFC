# Config Notes

This folder groups runtime configuration and setup templates.

## Primary runtime config

- `config.toml`
  - non-secret runtime tuning lives here
  - this is the file to edit for model defaults, embedding device, quantization, batch size, and max length

## Secret template / credentials

- `.env.example`
  - template for secrets and machine-specific values
- `google-oauth-credentials.json`
  - Google OAuth desktop client credentials

## Files that must stay in the project root

- `.python-version`: `uv` and Python version managers expect it at the project root.
- `pyproject.toml`: `uv` resolves the project from the root `pyproject.toml`.
- `uv.lock`: `uv` expects the lockfile beside `pyproject.toml`.
- `.env`: runtime secrets stay at the root, but non-secret tuning now belongs in `config/config.toml`.

## Git ignore rules

To keep the root minimal, the local ignore rules now live in `.git/info/exclude`.
That works on this machine, but it is not shared through GitHub the way a root `.gitignore` would be.
