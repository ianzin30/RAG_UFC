"""Regression tests that the Streamlit app no longer uses app auth."""

from pathlib import Path


APPLICATION_DIR = Path(__file__).resolve().parents[1] / "application"


def test_streamlit_entrypoint_has_no_login_gate_or_firebase_session_restore():
    source = (APPLICATION_DIR / "app.py").read_text(encoding="utf-8")

    assert "LoginGate" not in source
    assert "require_authenticated_user" not in source
    assert "Firebase" not in source
    assert "firebase" not in source


def test_navigation_rail_has_no_logout_or_account_action():
    source = (APPLICATION_DIR / "presentation" / "nav_rail" / "Navigation.py").read_text(encoding="utf-8")

    assert "logout" not in source.lower()
    assert "clear_current_user" not in source
    assert "get_current_user" not in source


def test_session_defaults_do_not_create_auth_state():
    source = (APPLICATION_DIR / "presentation" / "shared" / "SessionState.py").read_text(encoding="utf-8")

    assert '"user"' not in source
    assert "firebase_id_token" not in source
