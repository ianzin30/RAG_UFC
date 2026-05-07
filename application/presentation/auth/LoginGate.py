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
# Google sign-in — temporarily disabled, shows a "coming soon" popup
# ─────────────────────────────────────────────────────────────────────────────

@st.dialog("Login com Google")
def _render_google_unavailable_dialog() -> None:
    st.write("O login com Google estará disponível em breve.")
    st.caption("Esta opção de login ainda está em desenvolvimento.")
    if st.button("OK", key="google_dialog_ok", use_container_width=True, type="primary"):
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Page CSS
# ─────────────────────────────────────────────────────────────────────────────

_CSS = """
<style>
/* Hide Streamlit's "Press Enter to submit form" overlay only — narrow
   selector so we don't accidentally strip pointer-events from the input
   wrapper (which would make the field unclickable). */
[data-testid="InputInstructions"] {
    display: none !important;
}

/* True full-viewport centering — make every Streamlit layer a flex column
   so the block-container stretches to fill remaining height, then center
   the auth card within it. Works on any screen size with no magic numbers. */
.stApp, [data-testid="stApp"] {
    min-height: 100vh !important;
}

[data-testid="stMain"] {
    min-height: 100vh !important;
}

[data-testid="stMainBlockContainer"] {
    padding-top: 0 !important;
    padding-bottom: 0 !important;
    min-height: 100vh !important;
}

[data-testid="stMainBlockContainer"] > .block-container {
    padding: 2rem 1rem !important;
    min-height: 100vh !important;
}

/* Auth card wrapper — constrain width, let parent flex do the centering */
.st-key-auth_card {
    position: fixed !important;
    top: 50% !important;
    left: 50% !important;
    right: auto !important;
    bottom: auto !important;
    transform: translate(-50%, -50%) !important;
    width: 100% !important;
    max-width: min(440px, calc(100vw - 2rem)) !important;
    max-height: calc(100vh - 2rem) !important;
    overflow-y: auto !important;
    z-index: 10 !important;
}

/* Card — visual styles only; width/centering handled by .st-key-auth_card above */
.st-key-auth_card div[data-testid="stVerticalBlock"]:has(> div > [data-testid="stForm"]) {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 14px;
    padding: 2.4rem 2.4rem 2rem;
    box-shadow: 0 4px 32px rgba(0,0,0,0.35);
}

/* Standardize all text inputs in the auth card so email / password /
   confirm-password are visually identical regardless of mode. */
.st-key-auth_card [data-testid="stTextInput"] {
    margin-bottom: 0.85rem !important;
}

.st-key-auth_card [data-testid="stTextInput"] [data-baseweb="input"] {
    width: 100% !important;
    height: 44px !important;
    min-height: 44px !important;
    background: var(--app-input-bg) !important;
    border: 1px solid var(--app-input-border) !important;
    border-radius: 10px !important;
    box-shadow: none !important;
    overflow: hidden !important;
}
.st-key-auth_card [data-testid="stTextInput"] [data-baseweb="input"] > div {
    width: 100% !important;
    height: 100% !important;
    min-height: 100% !important;
    background: transparent !important;
    border: 0 !important;
    border-radius: 0 !important;
    box-shadow: none !important;
}
.st-key-auth_card [data-testid="stTextInput"] [data-baseweb="input"]:focus-within {
    border-color: var(--app-input-border-focus) !important;
    box-shadow: var(--app-input-shadow) !important;
}
.st-key-auth_card [data-testid="stTextInput"] [data-baseweb="input"] > div:focus-within {
    border-color: transparent !important;
    box-shadow: none !important;
}
.st-key-auth_card [data-testid="stTextInput"] input {
    height: 44px !important;
    padding: 0 14px !important;
    font-size: 14px !important;
    line-height: 1.4 !important;
}
.st-key-auth_card [data-testid="stTextInput"] label {
    font-size: 13px !important;
    margin-bottom: 0.3rem !important;
}

/* Greyed-out look for the "Continuar com Google" button (clickable but
   visually inactive — opens a "coming soon" dialog instead of signing in).
   Selectors include the baseweb attribute to win specificity vs. the
   generic secondary-button rules below. */
.st-key-google_login_disabled button[data-testid="baseButton-secondary"],
.st-key-google_login_disabled button {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.10) !important;
    color: rgba(255,255,255,0.55) !important;
    box-shadow: none !important;
    cursor: pointer !important;
    height: 44px !important;
    min-height: 44px !important;
    max-height: 44px !important;
    font-size: 14px !important;
    font-weight: 500 !important;
    padding: 0 14px !important;
}
.st-key-google_login_disabled button[data-testid="baseButton-secondary"]:hover,
.st-key-google_login_disabled button:hover {
    background: rgba(255,255,255,0.07) !important;
    border-color: rgba(255,255,255,0.18) !important;
    color: rgba(255,255,255,0.75) !important;
}
.st-key-google_login_disabled button p,
.st-key-google_login_disabled button span,
.st-key-google_login_disabled button svg {
    color: inherit !important;
    fill: currentColor !important;
    line-height: 44px !important;
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

/* Link-style secondary buttons — fixed size, no text wrap */
button[data-testid="baseButton-secondary"] {
    background: transparent !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    border-radius: 8px !important;
    color: #60a5fa !important;
    font-size: 13px !important;
    font-weight: 400 !important;
    cursor: pointer !important;
    box-shadow: none !important;
    overflow: hidden !important;
    width: 100% !important;
    height: 38px !important;
    min-height: 38px !important;
    max-height: 38px !important;
    padding: 0 12px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}
/* Target the <p> Streamlit renders inside the button — this is where wrapping happens */
button[data-testid="baseButton-secondary"] p,
button[data-testid="baseButton-secondary"] span,
button[data-testid="baseButton-secondary"] div {
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    margin: 0 !important;
    line-height: 38px !important;
}
button[data-testid="baseButton-secondary"]:hover {
    color: #93c5fd !important;
    background: rgba(255,255,255,0.05) !important;
    border-color: rgba(255,255,255,0.25) !important;
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

    with st.container(key="auth_card"):
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

            # Google divider + temporarily-disabled button (opens "coming soon" dialog)
            st.markdown(
                '<div class="auth-divider">ou continue com</div>',
                unsafe_allow_html=True,
            )
            if st.button(
                "Continuar com Google",
                key="google_login_disabled",
                use_container_width=True,
                icon=":material/account_circle:",
            ):
                _render_google_unavailable_dialog()

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

    # Token delivered via query param after Google sign-in popup.
    # Currently unreachable (Google login UI is parked behind a "coming soon"
    # dialog); kept wired so re-enabling Google login is a UI-only change.
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
