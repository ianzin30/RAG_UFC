"""Login gate — multi-mode auth page (email/password + Google OAuth) with Firebase.

Modes (stored in st.session_state._login_mode):
  "login"   — sign in with email/password (default)
  "signup"  — create a new account
  "forgot"  — send a password-reset email

Google sign-in uses Firebase JS SDK in a same-origin iframe component.
Email/password uses the Firebase REST Identity Toolkit API server-side.
All tokens are verified with firebase-admin before being trusted.
"""
from __future__ import annotations

import logging

import requests
import streamlit as st

from service.auth.FirebaseAuthService import is_firebase_enabled, verify_id_token
from service.auth.UserContext import UserContext
from .SessionUser import clear_current_user, get_current_user, set_current_user

logger = logging.getLogger("ragufc.auth")

# ─────────────────────────────────────────────────────────────────────────────
# Firebase REST helpers
# ─────────────────────────────────────────────────────────────────────────────

_REST_BASE = "https://identitytoolkit.googleapis.com/v1/accounts"

_ERROR_MAP = {
    "EMAIL_NOT_FOUND": "Nenhuma conta encontrada com este e-mail.",
    "INVALID_PASSWORD": "Senha incorreta. Verifique e tente novamente.",
    "INVALID_LOGIN_CREDENTIALS": "E-mail ou senha incorretos.",
    "EMAIL_EXISTS": "Já existe uma conta com este e-mail.",
    "WEAK_PASSWORD": "A senha deve ter pelo menos 6 caracteres.",
    "INVALID_EMAIL": "Por favor, insira um e-mail válido.",
    "TOO_MANY_ATTEMPTS_TRY_LATER": "Muitas tentativas seguidas. Tente novamente mais tarde.",
    "USER_DISABLED": "Esta conta foi desativada. Entre em contato com o suporte.",
    "OPERATION_NOT_ALLOWED": "Este método de login não está habilitado.",
    "MISSING_PASSWORD": "Por favor, insira a senha.",
    "MISSING_EMAIL": "Por favor, insira o e-mail.",
}


def _friendly(raw: str) -> str:
    for key, msg in _ERROR_MAP.items():
        if key in raw:
            return msg
    return "Erro de autenticação. Tente novamente."


def _rest(endpoint: str, api_key: str, body: dict) -> dict:
    try:
        resp = requests.post(
            f"{_REST_BASE}:{endpoint}?key={api_key}",
            json=body,
            timeout=10,
        )
        return resp.json()
    except requests.RequestException as exc:
        raise ValueError("Sem conexão com os servidores de autenticação.") from exc


def _email_signin(email: str, password: str, api_key: str) -> str:
    data = _rest("signInWithPassword", api_key, {
        "email": email, "password": password, "returnSecureToken": True,
    })
    if "idToken" not in data:
        raise ValueError(_friendly(data.get("error", {}).get("message", "")))
    return data["idToken"]


def _email_signup(email: str, password: str, api_key: str) -> str:
    data = _rest("signUp", api_key, {
        "email": email, "password": password, "returnSecureToken": True,
    })
    if "idToken" not in data:
        raise ValueError(_friendly(data.get("error", {}).get("message", "")))
    return data["idToken"]


def _send_reset_email(email: str, api_key: str) -> None:
    data = _rest("sendOobCode", api_key, {
        "requestType": "PASSWORD_RESET", "email": email,
    })
    if "error" in data:
        raise ValueError(_friendly(data["error"].get("message", "")))


# ─────────────────────────────────────────────────────────────────────────────
# Token handling (shared by email and Google flows)
# ─────────────────────────────────────────────────────────────────────────────

def _handle_token(id_token: str) -> None:
    """Verify *id_token* with firebase-admin, upsert profile, store in session, rerun."""
    user = verify_id_token(id_token)
    st.session_state["firebase_id_token"] = id_token
    set_current_user(user)
    try:
        from service.storage.MongoClientProvider import get_db, ensure_indexes
        from service.storage.UserProfileRepository import upsert_on_login
        db = get_db()
        ensure_indexes(db)
        upsert_on_login(db, user.user_id, user.email, user.display_name)
    except Exception as exc:
        logger.warning("MongoDB profile upsert failed (non-fatal): %s", exc)
    logger.info("Login successful — uid=%s email=%s", user.user_id, user.email)
    st.query_params.clear()
    st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Google sign-in HTML component
# ─────────────────────────────────────────────────────────────────────────────

_GOOGLE_HTML = """\
<!DOCTYPE html><html><head><meta charset="UTF-8"/>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:transparent;display:flex;align-items:center;
        justify-content:center;height:60px;padding:6px 0;
        font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}}
  button{{width:100%;max-width:340px;display:flex;align-items:center;
          justify-content:center;gap:10px;padding:10px 16px;
          background:#fff;color:#3c4043;border:1px solid #dadce0;
          border-radius:8px;font-size:14px;font-weight:500;cursor:pointer;
          transition:background .15s,box-shadow .15s;letter-spacing:.01em}}
  button:hover{{background:#f8f9fa;box-shadow:0 1px 3px rgba(0,0,0,.2)}}
  button:disabled{{opacity:.55;cursor:not-allowed}}
  #err{{font-size:12px;color:#f87171;margin-top:6px;text-align:center;min-height:18px}}
</style></head><body>
<div style="display:flex;flex-direction:column;align-items:center;width:100%">
  <button id="btn">
    <svg width="18" height="18" viewBox="0 0 48 48">
      <path fill="#FFC107" d="M43.6 20.1H42V20H24v8h11.3C33.7 32.6 29.2 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.1 8 2.9l5.7-5.7C34.5 6.5 29.5 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.6-.4-3.9z"/>
      <path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.7 16 19 12 24 12c3.1 0 5.8 1.1 8 2.9l5.7-5.7C34.5 6.5 29.5 4 24 4 16.3 4 9.7 8.3 6.3 14.7z"/>
      <path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.3 26.7 36 24 36c-5.2 0-9.6-3.3-11.3-8H6.3C9.7 35.7 16.4 44 24 44z"/>
      <path fill="#1976D2" d="M43.6 20.1H42V20H24v8h11.3c-.8 2.3-2.3 4.2-4.2 5.6l6.2 5.2C41.8 35.1 44 29.9 44 24c0-1.3-.1-2.6-.4-3.9z"/>
    </svg>
    Continuar com Google
  </button>
  <div id="err"></div>
</div>
<script type="module">
  import {{initializeApp}} from "https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js";
  import {{getAuth,signInWithPopup,GoogleAuthProvider}}
    from "https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";
  const cfg={{apiKey:"{api_key}",authDomain:"{auth_domain}",projectId:"{project_id}"}};
  let app;
  try{{app=initializeApp(cfg)}}
  catch{{const {{getApp}}=await import("https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js");app=getApp()}}
  const auth=getAuth(app);
  const prov=new GoogleAuthProvider();
  document.getElementById("btn").addEventListener("click",async()=>{{
    const btn=document.getElementById("btn");
    const err=document.getElementById("err");
    btn.disabled=true; btn.lastChild.textContent=" Abrindo..."; err.textContent="";
    try{{
      const r=await signInWithPopup(auth,prov);
      const tok=await r.user.getIdToken();
      const url=new URL(window.parent.location.href);
      url.searchParams.set("firebase_token",tok);
      window.parent.location.href=url.toString();
    }}catch(e){{
      btn.disabled=false; btn.lastChild.textContent=" Continuar com Google";
      if(e.code!=="auth/popup-closed-by-user") err.textContent=e.message||"Erro ao entrar com Google.";
    }}
  }});
</script>
</body></html>
"""


# ─────────────────────────────────────────────────────────────────────────────
# Page CSS
# ─────────────────────────────────────────────────────────────────────────────

_CSS = """
<style>
/* Full-viewport centering wrapper */
[data-testid="stMain"] > div:first-child {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 92vh;
}

/* Card */
div[data-testid="stVerticalBlock"]:has(> div > [data-testid="stForm"]) {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 14px;
    padding: 2.4rem 2.4rem 2rem;
    width: 100%;
    max-width: 420px;
    box-shadow: 0 4px 32px rgba(0,0,0,0.35);
}

/* Divider text */
.auth-divider {
    display: flex; align-items: center; gap: 12px;
    color: rgba(255,255,255,0.35); font-size: 13px;
    margin: 12px 0 8px;
}
.auth-divider::before,.auth-divider::after {
    content:""; flex:1; height:1px;
    background: rgba(255,255,255,0.12);
}

/* Link-style secondary buttons */
button[data-testid="baseButton-secondary"] {
    background: transparent !important;
    border: none !important;
    color: #60a5fa !important;
    font-size: 13px !important;
    font-weight: 400 !important;
    text-decoration: underline !important;
    cursor: pointer !important;
    box-shadow: none !important;
    /* Fixed size so both buttons are identical regardless of text length */
    width: 152px !important;
    min-width: 152px !important;
    max-width: 152px !important;
    height: 32px !important;
    min-height: 32px !important;
    padding: 0 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}
button[data-testid="baseButton-secondary"]:hover {
    color: #93c5fd !important;
    background: transparent !important;
}

/* Center the two-button row and remove column stretch */
div[data-testid="stVerticalBlock"]:has(> div > [data-testid="stForm"])
  div[data-testid="stHorizontalBlock"] {
    display: flex !important;
    justify-content: center !important;
    gap: 12px !important;
}
div[data-testid="stVerticalBlock"]:has(> div > [data-testid="stForm"])
  div[data-testid="stHorizontalBlock"] div[data-testid="column"] {
    flex: 0 0 auto !important;
    width: auto !important;
    min-width: 0 !important;
}
</style>
"""


# ─────────────────────────────────────────────────────────────────────────────
# Mode helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_mode() -> str:
    return st.session_state.get("_login_mode", "login")


def _set_mode(mode: str) -> None:
    st.session_state["_login_mode"] = mode
    st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Login page renderer
# ─────────────────────────────────────────────────────────────────────────────

def _render_login_page() -> None:
    from service.RuntimeConfig import get_runtime_config

    cfg = get_runtime_config().firebase
    api_key = cfg.web_api_key

    st.markdown(_CSS, unsafe_allow_html=True)

    # Strip the browser "Press Enter to submit form" tooltip Streamlit adds to form inputs
    st.components.v1.html("""<script>
(function () {
  function strip() {
    window.parent.document.querySelectorAll('input[title]')
      .forEach(function (el) { el.removeAttribute('title'); });
  }
  strip();
  new MutationObserver(strip).observe(window.parent.document.body,
    {subtree: true, childList: true, attributes: true, attributeFilter: ['title']});
})();
</script>""", height=0)

    # Use columns to horizontally center the card
    _, col, _ = st.columns([1, 2, 1])

    with col:
        mode = _get_mode()

        # ── Title ──────────────────────────────────────────────────────────
        st.markdown(
            "<h2 style='text-align:center;margin-bottom:4px;font-weight:700;"
            "letter-spacing:-0.5px'>RAG UFC</h2>",
            unsafe_allow_html=True,
        )

        subtitles = {
            "login": "Faça login para testar o protótipo inicial da ferramenta",
            "signup": "Crie sua conta para começar.",
            "forgot": "Informe seu e-mail para receber o link de redefinição.",
        }
        st.markdown(
            f"<p style='text-align:center;color:rgba(255,255,255,.55);"
            f"font-size:14px;margin-bottom:1.4rem'>{subtitles[mode]}</p>",
            unsafe_allow_html=True,
        )

        # ── Firebase config warning ─────────────────────────────────────────
        if not api_key or not cfg.auth_domain or not cfg.project_id:
            st.warning(
                "Firebase não configurado. Preencha `FIREBASE_WEB_API_KEY`, "
                "`FIREBASE_AUTH_DOMAIN` e `FIREBASE_PROJECT_ID` no `.env`."
            )
            st.stop()
            return

        # ── Error / success placeholder ─────────────────────────────────────
        feedback = st.empty()

        # ══════════════════════════════════════════════════════════════════
        # LOGIN mode
        # ══════════════════════════════════════════════════════════════════
        if mode == "login":
            with st.form("login_form", clear_on_submit=False):
                email = st.text_input("E-mail", placeholder="seu@email.com")
                password = st.text_input("Senha", type="password", placeholder="••••••••")
                submitted = st.form_submit_button("Entrar", use_container_width=True, type="primary")

            if submitted:
                if not email.strip() or not password:
                    feedback.error("Preencha o e-mail e a senha.")
                else:
                    try:
                        token = _email_signin(email.strip(), password, api_key)
                        _handle_token(token)
                    except Exception as exc:
                        feedback.error(str(exc))

            # Forgot password + sign-up links — equal-width, centered columns
            fc, sc = st.columns([1, 1])
            with fc:
                if st.button("Esqueceu a senha?", key="to_forgot", use_container_width=True):
                    _set_mode("forgot")
            with sc:
                if st.button("Criar conta", key="to_signup", use_container_width=True):
                    _set_mode("signup")

            # Google divider + button with enough breathing room
            st.markdown(
                '<div class="auth-divider">ou continue com</div>',
                unsafe_allow_html=True,
            )
            google_html = _GOOGLE_HTML.format(
                api_key=api_key,
                auth_domain=cfg.auth_domain,
                project_id=cfg.project_id,
            )
            st.components.v1.html(google_html, height=96)

        # ══════════════════════════════════════════════════════════════════
        # SIGNUP mode
        # ══════════════════════════════════════════════════════════════════
        elif mode == "signup":
            with st.form("signup_form", clear_on_submit=False):
                email = st.text_input("E-mail", placeholder="seu@email.com")
                password = st.text_input(
                    "Senha", type="password", placeholder="mínimo 6 caracteres"
                )
                password2 = st.text_input(
                    "Confirmar senha", type="password", placeholder="repita a senha"
                )
                submitted = st.form_submit_button(
                    "Criar conta", use_container_width=True, type="primary"
                )

            if submitted:
                if not email.strip() or not password:
                    feedback.error("Preencha todos os campos.")
                elif password != password2:
                    feedback.error("As senhas não coincidem.")
                elif len(password) < 6:
                    feedback.error("A senha deve ter pelo menos 6 caracteres.")
                else:
                    try:
                        token = _email_signup(email.strip(), password, api_key)
                        _handle_token(token)
                    except Exception as exc:
                        feedback.error(str(exc))

            st.markdown("<div style='height:8px'/>", unsafe_allow_html=True)
            if st.button("Já tem uma conta? Entrar", key="to_login"):
                _set_mode("login")

        # ══════════════════════════════════════════════════════════════════
        # FORGOT PASSWORD mode
        # ══════════════════════════════════════════════════════════════════
        elif mode == "forgot":
            with st.form("forgot_form", clear_on_submit=True):
                email = st.text_input("E-mail da conta", placeholder="seu@email.com")
                submitted = st.form_submit_button(
                    "Enviar link de redefinição", use_container_width=True, type="primary"
                )

            if submitted:
                if not email.strip():
                    feedback.error("Insira o e-mail da sua conta.")
                else:
                    try:
                        _send_reset_email(email.strip(), api_key)
                        feedback.success(
                            f"Link de redefinição enviado para **{email.strip()}**. "
                            "Verifique sua caixa de entrada."
                        )
                    except Exception as exc:
                        feedback.error(str(exc))

            st.markdown("<div style='height:8px'/>", unsafe_allow_html=True)
            if st.button("← Voltar para o login", key="back_to_login"):
                _set_mode("login")

    st.stop()


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def require_authenticated_user() -> UserContext | None:
    """Ensure a user is authenticated; render login gate and st.stop() otherwise."""
    if not is_firebase_enabled():
        return None

    existing = get_current_user()
    if existing is not None:
        logger.debug("Active user: uid=%s", existing.user_id)
        return existing

    # Token delivered via query param after Google sign-in popup
    firebase_token = st.query_params.get("firebase_token", "")
    if firebase_token:
        try:
            _handle_token(firebase_token)
        except Exception as exc:
            logger.warning("Token verification failed: %s", exc)
            st.query_params.clear()
            # Fall through to render login page with error surfaced via st.error

    _render_login_page()
    return None


def logout() -> None:
    """Clear session and rerun, returning user to the login page."""
    logger.info("Logout — uid=%s", getattr(get_current_user(), "user_id", "?"))
    clear_current_user()
    st.rerun()
