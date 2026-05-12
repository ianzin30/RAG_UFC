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
        "key": "sidebar_nav_chat_button",
        "help": "Abrir seus chats",
        "icon": ":material/chat_bubble_outline:",
    },
    {
        "panel": SIDEBAR_FILES_PANEL,
        "label": "Arquivos",
        "key": "sidebar_nav_files_button",
        "help": "Abrir arquivos e uploads",
        "icon": ":material/folder_open:",
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


def _render_rail_button(
    *,
    key: str,
    help_text: str,
    icon: str,
    is_active: bool = False,
    on_click=None,
) -> None:
    if st.button(
        ICON_ONLY_BUTTON_LABEL,
        key=key,
        help=help_text,
        type="primary" if is_active else "secondary",
        icon=icon,
        use_container_width=True,
    ):
        if on_click is not None:
            on_click()
        st.rerun()


def _render_brand() -> None:
    st.markdown(
        f"""
        <div class="nav-rail-brand" aria-label="RAG Treino">
            <img src="{LOGO_DATA_URI}" alt="RAG Treino" />
        </div>
        """,
        unsafe_allow_html=True,
    )


# Esta rail concentra o icone do app e o seletor de paineis.
def render_navigation_rail() -> None:
    active_panel = get_active_sidebar_panel()

    with st.container(key="sidebar_nav_rail"):
        with st.container(key="sidebar_nav_rail_header"):
            _render_brand()

        with st.container(key="sidebar_nav_rail_items"):
            for item in NAVIGATION_ITEMS:
                _render_rail_button(
                    key=item["key"],
                    help_text=item["help"],
                    icon=item["icon"],
                    is_active=active_panel == item["panel"],
                    on_click=lambda panel_name=item["panel"]: set_active_sidebar_panel(panel_name),
                )
