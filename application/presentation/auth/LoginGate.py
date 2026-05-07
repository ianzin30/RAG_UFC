"""Login gate — renders Google sign-in and verifies Firebase ID tokens.

Flow:
1. If st.session_state["user"] is set → already authenticated, return immediately.
2. If ?firebase_token=<jwt> is in the URL → verify server-side, store, redirect clean.
3. Otherwise → render the sign-in page (Firebase JS SDK + Google OAuth popup) and st.stop().

The Firebase JS SDK runs in a st.components.v1.html iframe (same-origin with the
Streamlit server). After a successful sign-in popup, JS navigates window.parent to
append ?firebase_token=<id_token>, triggering a Streamlit rerun.
"""
from __future__ import annotations

import logging

import streamlit as st

from service.auth.FirebaseAuthService import is_firebase_enabled, verify_id_token
from service.auth.UserContext import UserContext
from .SessionUser import clear_current_user, get_current_user, set_current_user

logger = logging.getLogger("ragufc.auth")

_SIGN_IN_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<style>
  body {{
    margin: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100px;
    background: transparent;
    font-family: sans-serif;
  }}
  #sign-in-btn {{
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 20px;
    background: #4285F4;
    color: white;
    border: none;
    border-radius: 6px;
    font-size: 15px;
    cursor: pointer;
    font-weight: 500;
  }}
  #sign-in-btn:hover {{ background: #3367d6; }}
  #sign-in-btn:disabled {{ background: #999; cursor: not-allowed; }}
  #status {{ font-size: 13px; color: #555; margin-top: 8px; }}
  .wrap {{ display: flex; flex-direction: column; align-items: center; }}
</style>
</head>
<body>
<div class="wrap">
  <button id="sign-in-btn">
    <svg width="18" height="18" viewBox="0 0 48 48">
      <path fill="#FFC107" d="M43.6 20.1H42V20H24v8h11.3C33.7 32.6 29.2 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.1 8 2.9l5.7-5.7C34.5 6.5 29.5 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.6-.4-3.9z"/>
      <path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.7 16 19 12 24 12c3.1 0 5.8 1.1 8 2.9l5.7-5.7C34.5 6.5 29.5 4 24 4 16.3 4 9.7 8.3 6.3 14.7z"/>
      <path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.3 26.7 36 24 36c-5.2 0-9.6-3.3-11.3-8H6.3C9.7 35.7 16.4 44 24 44z"/>
      <path fill="#1976D2" d="M43.6 20.1H42V20H24v8h11.3c-.8 2.3-2.3 4.2-4.2 5.6l6.2 5.2C41.8 35.1 44 29.9 44 24c0-1.3-.1-2.6-.4-3.9z"/>
    </svg>
    Entrar com Google
  </button>
  <div id="status"></div>
</div>

<script type="module">
  import {{ initializeApp }} from "https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js";
  import {{ getAuth, signInWithPopup, GoogleAuthProvider }} from "https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";

  const firebaseConfig = {{
    apiKey: "{api_key}",
    authDomain: "{auth_domain}",
    projectId: "{project_id}",
  }};

  let app;
  try {{
    app = initializeApp(firebaseConfig);
  }} catch (e) {{
    // Already initialized (hot-reload)
    const {{ getApp }} = await import("https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js");
    app = getApp();
  }}

  const auth = getAuth(app);
  const provider = new GoogleAuthProvider();

  document.getElementById("sign-in-btn").addEventListener("click", async () => {{
    const btn = document.getElementById("sign-in-btn");
    const status = document.getElementById("status");
    btn.disabled = true;
    status.textContent = "Abrindo janela de login...";
    try {{
      const result = await signInWithPopup(auth, provider);
      const token = await result.user.getIdToken();
      status.textContent = "Autenticado! Redirecionando...";
      const url = new URL(window.parent.location.href);
      url.searchParams.set("firebase_token", token);
      window.parent.location.href = url.toString();
    }} catch (err) {{
      status.textContent = "Erro: " + err.message;
      btn.disabled = false;
    }}
  }});
</script>
</body>
</html>
"""


def _render_login_page(error: str | None = None) -> None:
    from service.RuntimeConfig import get_runtime_config

    st.markdown(
        """
        <div style="display:flex;flex-direction:column;align-items:center;
                    justify-content:center;min-height:60vh;gap:24px;">
        """,
        unsafe_allow_html=True,
    )
    st.title("RAG Treino")
    st.caption("Faça login para acessar seus documentos e conversas.")

    if error:
        st.error(f"Falha na autenticação: {error}")

    cfg = get_runtime_config().firebase
    if not cfg.web_api_key or not cfg.auth_domain or not cfg.project_id:
        st.warning(
            "Firebase web config incompleto. Preencha `web_api_key`, `auth_domain` e `project_id` "
            "em `config/config.toml` → `[firebase]`."
        )
        st.stop()
        return

    html = _SIGN_IN_HTML_TEMPLATE.format(
        api_key=cfg.web_api_key,
        auth_domain=cfg.auth_domain,
        project_id=cfg.project_id,
    )
    st.components.v1.html(html, height=130)
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()


def require_authenticated_user() -> UserContext | None:
    """Ensure a user is authenticated; render login gate and st.stop() otherwise.

    Returns the active UserContext when already authenticated so callers can
    short-circuit before rendering the main app.
    """
    if not is_firebase_enabled():
        # Firebase disabled (e.g. local dev without credentials). Return a stub so
        # the rest of the app still works when auth is not configured.
        return None

    # Already authenticated in this browser session
    existing = get_current_user()
    if existing is not None:
        logger.debug("Active user: uid=%s", existing.user_id)
        return existing

    # Token delivered via query param after Google sign-in
    firebase_token = st.query_params.get("firebase_token", "")
    if firebase_token:
        try:
            user = verify_id_token(firebase_token)
        except Exception as exc:
            logger.warning("Token verification failed: %s", exc)
            # Clear the bad token from the URL and show login with error
            st.query_params.clear()
            _render_login_page(error=str(exc))
            return None

        st.session_state["firebase_id_token"] = firebase_token
        set_current_user(user)

        # Upsert profile in MongoDB
        try:
            from service.storage.MongoClientProvider import get_db, ensure_indexes
            from service.storage.UserProfileRepository import upsert_on_login
            db = get_db()
            ensure_indexes(db)
            upsert_on_login(db, user.user_id, user.email, user.display_name)
        except Exception as exc:
            logger.warning("MongoDB profile upsert failed (non-fatal): %s", exc)

        logger.info("Login successful — uid=%s email=%s", user.user_id, user.email)
        # Clear token from URL then rerun
        st.query_params.clear()
        st.rerun()

    _render_login_page()
    return None


def logout() -> None:
    """Clear session and rerun, returning user to the login page."""
    logger.info("Logout — uid=%s", getattr(get_current_user(), "user_id", "?"))
    clear_current_user()
    st.rerun()
