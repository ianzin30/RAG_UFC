"""Theme state and palette helpers for the app shell."""

import streamlit as st


DEFAULT_APP_THEME = "dark"

APP_THEMES = {
    "dark": {
        "--app-bg": "#07101d",
        "--app-elevated-bg": "#101a2c",
        "--app-sidebar-bg": "linear-gradient(180deg, #0a1220 0%, #08101d 100%)",
        "--app-panel-bg": "transparent",
        "--app-panel-border": "transparent",
        "--app-panel-shadow": "none",
        "--app-rail-bg": "rgba(226, 232, 240, 0.05)",
        "--app-rail-border": "rgba(148, 163, 184, 0.16)",
        "--app-rail-hover-bg": "rgba(148, 163, 184, 0.1)",
        "--app-rail-icon-bg": "#0f172a",
        "--app-rail-icon": "#b8c4d9",
        "--app-rail-active-bg": "#edf3ff",
        "--app-rail-active-border": "#edf3ff",
        "--app-rail-active-text": "#0f172a",
        "--app-surface": "#101827",
        "--app-surface-soft": "#1d2940",
        "--app-surface-strong": "#0f172a",
        "--app-text": "#e5edf8",
        "--app-muted": "#93a4bc",
        "--app-border": "#334155",
        "--app-border-soft": "#253244",
        "--app-chat-row-hover-bg": "rgba(148, 163, 184, 0.08)",
        "--app-chat-row-active-bg": "rgba(148, 163, 184, 0.09)",
        "--app-chat-row-active-border": "#334155",
        "--app-button-bg": "#1e293b",
        "--app-button-bg-hover": "#28364d",
        "--app-button-border": "#334155",
        "--app-button-active-bg": "#31425c",
        "--app-card-bg": "rgba(16, 24, 39, 0.82)",
        "--app-card-bg-hover": "#1f2b41",
        "--app-input-bg": "#0f172a",
        "--app-input-border": "#334155",
        "--app-input-placeholder": "#8093ae",
        "--app-uploader-bg": "linear-gradient(180deg, rgba(15, 23, 42, 0.92), rgba(10, 17, 31, 0.98))",
        "--app-uploader-border": "#314156",
        "--app-divider": "rgba(148, 163, 184, 0.16)",
        "--app-note-bg": "rgba(15, 23, 42, 0.72)",
        "--app-note-border": "#314156",
        "--app-note-text": "#e5edf8",
        "--app-chat-user-bg": "#1f2d44",
        "--app-chat-assistant-bg": "#0f172a",
        "--app-logo-filter": "brightness(0) invert(1)",
    },
    "light": {
        "--app-bg": "#f6f7fb",
        "--app-elevated-bg": "#ffffff",
        "--app-sidebar-bg": "linear-gradient(180deg, #fbfcfe 0%, #f5f7fb 100%)",
        "--app-panel-bg": "transparent",
        "--app-panel-border": "transparent",
        "--app-panel-shadow": "none",
        "--app-rail-bg": "#f1f4f8",
        "--app-rail-border": "#e5eaf2",
        "--app-rail-hover-bg": "#e8eef6",
        "--app-rail-icon-bg": "#ffffff",
        "--app-rail-icon": "#64748b",
        "--app-rail-active-bg": "#0f172a",
        "--app-rail-active-border": "#0f172a",
        "--app-rail-active-text": "#ffffff",
        "--app-surface": "#ffffff",
        "--app-surface-soft": "#f3f6fb",
        "--app-surface-strong": "#e8eef6",
        "--app-text": "#111827",
        "--app-muted": "#64748b",
        "--app-border": "#dbe4ef",
        "--app-border-soft": "#e5ebf3",
        "--app-chat-row-hover-bg": "#f4f7fb",
        "--app-chat-row-active-bg": "#ffffff",
        "--app-chat-row-active-border": "#dbe4ef",
        "--app-button-bg": "#ffffff",
        "--app-button-bg-hover": "#eef3fb",
        "--app-button-border": "#dbe4ef",
        "--app-button-active-bg": "#e6edf7",
        "--app-card-bg": "rgba(255, 255, 255, 0.94)",
        "--app-card-bg-hover": "#f2f6fc",
        "--app-input-bg": "#ffffff",
        "--app-input-border": "#dbe4ef",
        "--app-input-placeholder": "#7b8798",
        "--app-uploader-bg": "linear-gradient(180deg, rgba(248, 250, 252, 0.96), rgba(255, 255, 255, 1))",
        "--app-uploader-border": "#cbd5e1",
        "--app-divider": "#e5eaf2",
        "--app-note-bg": "rgba(255, 255, 255, 0.92)",
        "--app-note-border": "#dbe4ef",
        "--app-note-text": "#111827",
        "--app-chat-user-bg": "#eaf1fb",
        "--app-chat-assistant-bg": "#ffffff",
        "--app-logo-filter": "none",
    },
}


# Este helper devolve o tema ativo ja validado contra a paleta conhecida.
def get_active_theme_name() -> str:
    theme_name = str(st.session_state.get("app_theme") or DEFAULT_APP_THEME).strip().lower()
    if theme_name not in APP_THEMES:
        theme_name = DEFAULT_APP_THEME
        st.session_state.app_theme = theme_name
    return theme_name


# Este toggle alterna entre dark e light mantendo a escolha na sessao atual.
def toggle_app_theme() -> None:
    current_theme = get_active_theme_name()
    st.session_state.app_theme = "light" if current_theme == "dark" else "dark"


# Este bloco injeta as variaveis CSS que o stylesheet principal reutiliza.
def build_theme_variables_css(theme_name: str) -> str:
    palette = APP_THEMES.get(theme_name, APP_THEMES[DEFAULT_APP_THEME])
    variable_lines = [f"    {name}: {value};" for name, value in palette.items()]
    return ":root {\n" + "\n".join(variable_lines) + "\n}"
