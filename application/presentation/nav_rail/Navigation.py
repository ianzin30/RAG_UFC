"""Left navigation rail for the switchable sidebar panels."""

import streamlit as st

from presentation.shared.Config import LOGO_DATA_URI
from presentation.shared.Theme import get_active_theme_name, toggle_app_theme


SIDEBAR_CHAT_PANEL = "chat"
SIDEBAR_FILES_PANEL = "files"
ICON_ONLY_BUTTON_LABEL = "\u200b"
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


# Este helper garante que o painel ativo sempre seja um dos paines conhecidos.
def get_active_sidebar_panel() -> str:
    panel_name = str(st.session_state.get("sidebar_panel") or SIDEBAR_CHAT_PANEL).strip().lower()
    if panel_name not in {SIDEBAR_CHAT_PANEL, SIDEBAR_FILES_PANEL}:
        panel_name = SIDEBAR_CHAT_PANEL
        st.session_state.sidebar_panel = panel_name
    return panel_name


# Esta escrita troca o painel visivel sem alterar o restante do estado do app.
def set_active_sidebar_panel(panel_name: str) -> None:
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


# Esta rail concentra o icone do app, o seletor de paineis e o toggle de tema.
def render_navigation_rail() -> None:
    active_panel = get_active_sidebar_panel()
    active_theme = get_active_theme_name()

    with st.container(key="sidebar_nav_rail"):
        with st.container(key="sidebar_nav_rail_header"):
            st.markdown(
                f"""
                <div class="nav-rail-brand" aria-label="RAG Treino">
                    <img src="{LOGO_DATA_URI}" alt="RAG Treino" />
                </div>
                """,
                unsafe_allow_html=True,
            )

        with st.container(key="sidebar_nav_rail_items"):
            for item in NAVIGATION_ITEMS:
                _render_rail_button(
                    key=item["key"],
                    help_text=item["help"],
                    icon=item["icon"],
                    is_active=active_panel == item["panel"],
                    on_click=lambda panel_name=item["panel"]: set_active_sidebar_panel(panel_name),
                )

        with st.container(key="sidebar_nav_rail_footer"):
            _render_rail_button(
                key="sidebar_nav_theme_button",
                help_text="Alternar entre tema claro e escuro",
                icon=":material/dark_mode:" if active_theme == "dark" else ":material/light_mode:",
                on_click=toggle_app_theme,
            )
