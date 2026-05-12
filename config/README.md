# Config Notes

This folder groups runtime configuration and setup templates.

## Primary runtime config

- `config.toml`
  - non-secret runtime tuning lives here
  - this is the file to edit for model defaults, embedding device, quantization, batch size, and max length
  - retrieval tuning includes the dense/lexical candidate pool size and LLM evidence selector limits
  - the checked-in defaults are CPU-safe and use a local CPU `int8` embedding export on first run
  - Streamlit benchmark mode opens without Firebase/Mongo app login and uses shared local state under `data/`

## Secret template / credentials

- `.env.example`
  - template for secrets and machine-specific values
- `google-oauth-credentials.json`
  - Google OAuth client credentials.
  - For the Streamlit UI, use an OAuth **Web application** client (key `web` in the JSON) and add the Streamlit origin (default `http://localhost:8501/`) as an authorized redirect URI in Google Cloud Console.
  - The Telegram bot still uses the legacy desktop flow, so a `installed` block is accepted as a fallback but logs a warning.
- `google-drive-token.json` (generated at runtime, gitignored)
  - Persistent shared VM-level cache of the Drive OAuth token. Override the location with `GOOGLE_OAUTH_TOKEN_FILE`. Delete it (or click **Desconectar** in the sidebar) to force re-authentication.
- `GOOGLE_OAUTH_REDIRECT_URI` (env var, optional)
  - Overrides the redirect URI used in the OAuth flow. Defaults to the first `redirect_uris` entry in the credentials JSON, falling back to `http://localhost:8501/`. Must exactly match a redirect URI registered for the OAuth web client.

## Files that must stay in the project root

- `.python-version`: `uv` and Python version managers expect it at the project root.
- `pyproject.toml`: `uv` resolves the project from the root `pyproject.toml`.
- `uv.lock`: `uv` expects the lockfile beside `pyproject.toml`.
- `.env`: runtime secrets stay at the root, but non-secret tuning now belongs in `config/config.toml`.

## Git ignore rules

To keep the root minimal, the local ignore rules now live in `.git/info/exclude`.
That works on this machine, but it is not shared through GitHub the way a root `.gitignore` would be.
