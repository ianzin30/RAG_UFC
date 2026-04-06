# Config Notes

This folder groups movable configuration and setup templates for readability.

## Files moved here

- `google-oauth-credentials.json`

## Files that must stay in the project root

- `.python-version`: `uv` and Python version managers expect it at the project root.
- `pyproject.toml`: `uv` resolves the project from the root `pyproject.toml`.
- `uv.lock`: `uv` expects the lockfile beside `pyproject.toml`.

## Git ignore rules

To keep the root minimal, the local ignore rules now live in `.git/info/exclude`.
That works on this machine, but it is not shared through GitHub the way a root `.gitignore` would be.
