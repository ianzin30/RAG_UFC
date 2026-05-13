"""
Navigation rail for the sidebar.

Provides vertical navigation to switch between Chat and Files panels.
"""

import streamlit as st

from presentation.shared.Config import LOGO_DATA_URI

# Sidebar panel constants
SIDEBAR_CHAT_PANEL = "chat"
SIDEBAR_FILES_PANEL = "files"
ICON_ONLY_BUTTON_LABEL = "\u200b"  # Zero-width space for button styling

# Navigation items configuration
NAVIGATION_ITEMS = (
    {
        "panel": SIDEBAR_CHAT_PANEL,
        "label": "Chat",
        "href": "#sidebar-chat-panel",
        "help": "Abrir seus chats",
        "icon": "chat",
    },
    {
        "panel": SIDEBAR_FILES_PANEL,
        "label": "Arquivos",
        "href": "#sidebar-files-panel",
        "help": "Abrir arquivos e uploads",
        "icon": "folder",
    },
)


def get_active_sidebar_panel() -> str:
    """Get the currently active sidebar panel, defaulting to Chat if invalid."""
    panel_name = str(st.session_state.get("sidebar_panel") or SIDEBAR_CHAT_PANEL).strip().lower()
    if panel_name not in {SIDEBAR_CHAT_PANEL, SIDEBAR_FILES_PANEL}:
        panel_name = SIDEBAR_CHAT_PANEL
        st.session_state.sidebar_panel = panel_name
    return panel_name


def set_active_sidebar_panel(panel_name: str) -> None:
    """Switch the active sidebar panel without affecting other app state."""
    st.session_state.sidebar_panel = panel_name


def _render_brand() -> None:
    st.markdown(
        f"""
        <div class="nav-rail-brand" aria-label="RAG Treino">
            <img src="{LOGO_DATA_URI}" alt="RAG Treino" />
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_nav_icon(icon_name: str) -> str:
    if icon_name == "folder":
        return (
            '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">'
            '<path d="M3.5 6.5h6.2l2 2h8.8v9.8a2.2 2.2 0 0 1-2.2 2.2H5.7a2.2 2.2 0 0 1-2.2-2.2V6.5Z" />'
            '<path d="M3.5 8.5h17" />'
            "</svg>"
        )
    return (
        '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">'
        '<path d="M5.5 5.5h13a2 2 0 0 1 2 2v8.3a2 2 0 0 1-2 2H9.2l-4.7 3v-3.1a2 2 0 0 1-1-1.7V7.5a2 2 0 0 1 2-2Z" />'
        "</svg>"
    )


# Esta rail concentra o icone do app e o seletor de paineis.
def render_navigation_rail() -> None:
    with st.container(key="sidebar_nav_rail"):
        with st.container(key="sidebar_nav_rail_header"):
            _render_brand()

        with st.container(key="sidebar_nav_rail_items"):
            nav_links = "".join(
                (
                    f'<a class="sidebar-nav-link sidebar-nav-link-{item["panel"]}" '
                    f'href="{item["href"]}" '
                    f'title="{item["help"]}" '
                    f'aria-label="{item["label"]}">'
                    f'<span class="sidebar-nav-icon">{_render_nav_icon(item["icon"])}</span>'
                    f'<span class="sidebar-nav-label">{item["label"]}</span>'
                    "</a>"
                )
                for item in NAVIGATION_ITEMS
            )
            st.markdown(f'<nav class="sidebar-nav-links">{nav_links}</nav>', unsafe_allow_html=True)
