"""
Chat history display for the sidebar.

Handles organizing chats into time-based sections (Today, Yesterday, Older)
and rendering the chat list with controls for switching between chats.
"""

from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

from presentation import chat_sessions


def parse_chat_session_datetime(chat: dict[str, object]) -> datetime:
    """Parse chat timestamp from session data, defaulting to current time if missing."""
    raw_timestamp = (
        str(chat.get("updated_at") or "").strip()
        or str(chat.get("created_at") or "").strip()
    )
    if raw_timestamp.endswith("Z"):
        raw_timestamp = f"{raw_timestamp[:-1]}+00:00"
    try:
        timestamp = datetime.fromisoformat(raw_timestamp) if raw_timestamp else None
    except ValueError:
        timestamp = None

    if timestamp is None:
        timestamp = datetime.now(timezone.utc)
    elif timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)


def build_chat_history_sections(
    chat_items: list[dict[str, object]],
    *,
    now: datetime | None = None,
) -> list[dict[str, object]]:
    """Organize chats into time-based sections: Today, Yesterday, Older."""
    reference = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).date()
    grouped: dict[str, list[tuple[datetime, dict[str, object]]]] = {
        "Today": [],
        "Yesterday": [],
        "Older": [],
    }

    for chat in list(chat_items or []):
        timestamp = parse_chat_session_datetime(chat)
        age_in_days = (reference - timestamp.date()).days
        if age_in_days <= 0:
            section_label = "Today"
        elif age_in_days == 1:
            section_label = "Yesterday"
        else:
            section_label = "Older"
        grouped[section_label].append((timestamp, chat))

    sections = []
    for label in ("Today", "Yesterday", "Older"):
        items = sorted(grouped[label], key=lambda item: item[0], reverse=True)
        if items:
            sections.append({"label": label, "items": [chat for _, chat in items]})
    return sections


# Este botao cria novas conversas sem repetir o visual pesado dos cards antigos.
def render_new_chat_button(default_collection, default_model: str | None) -> None:
    with st.container(key="chat_history_new_button"):
        if st.button(
            "Novo chat",
            key="new_chat_button",
            use_container_width=True,
            icon=":material/add:",
        ):
            created, message = chat_sessions.create_new_chat(
                default_collection=default_collection,
                default_model=st.session_state.get("model_name") or default_model,
            )
            st.session_state.chat_feedback = "Novo chat criado." if created else message
            st.rerun()


# Este cabecalho reduz o topo do painel para um titulo simples e facil de escanear.
def render_chat_history_header() -> None:
    st.markdown(
        """
        <div class="chat-history-header">
            <div class="chat-history-eyebrow">RAG Treino</div>
            <div class="chat-history-title">Chat</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# Esta linha renderiza uma sessao individual com clique principal e menu secundario.
def render_chat_history_item(item: dict[str, object], default_collection, default_model: str | None) -> None:
    is_active_chat = item["id"] == st.session_state.get("active_chat_id")
    row_key_prefix = "chat_history_row_active" if is_active_chat else "chat_history_row"

    with st.container(key=f"{row_key_prefix}_{item['id']}"):
        row_col, actions_col = st.columns([0.88, 0.12], vertical_alignment="center")

        with row_col:
            if st.button(
                str(item["title"]),
                key=f"chat_session_{item['id']}",
                use_container_width=True,
                type="primary" if is_active_chat else "tertiary",
                help=str(item["title"]),
            ):
                chat_sessions.activate_chat(str(item["id"]))
                st.rerun()

        with actions_col:
            with st.popover("...", use_container_width=True):
                rename_key = f"rename_chat_input_{item['id']}"
                new_title = st.text_input(
                    "Renomear chat",
                    value=str(item["title"]),
                    key=rename_key,
                )
                if st.button("Salvar nome", key=f"rename_chat_save_{item['id']}", use_container_width=True):
                    renamed, message = chat_sessions.rename_chat(str(item["id"]), new_title)
                    st.session_state.chat_feedback = "Chat renomeado." if renamed else message
                    st.rerun()
                if st.button("Excluir chat", key=f"delete_chat_{item['id']}", use_container_width=True):
                    deleted, message = chat_sessions.delete_chat(
                        str(item["id"]),
                        default_collection=default_collection,
                        default_model=st.session_state.get("model_name") or default_model,
                    )
                    st.session_state.chat_feedback = "Chat excluido." if deleted else message
                    st.rerun()


# Esta secao desenha o grupo temporal e todas as linhas compactas abaixo dele.
def render_chat_history_section(
    section: dict[str, object],
    *,
    default_collection,
    default_model: str | None,
) -> None:
    st.markdown(
        f"""
        <div class="chat-history-section-header">
            <span class="chat-history-section-title">{section["label"]}</span>
            <span class="chat-history-section-caret">&#709;</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    for item in list(section.get("items") or []):
        render_chat_history_item(item, default_collection, default_model)


# Esta composicao monta o painel inteiro com cabecalho leve, botao e grupos.
def render_chat_history(default_collection, default_model: str | None) -> None:
    render_chat_history_header()
    render_new_chat_button(default_collection, default_model)

    sections = build_chat_history_sections(chat_sessions.get_chat_sessions())
    if not sections:
        st.caption("Nenhum chat.")
        return

    for section in sections:
        render_chat_history_section(
            section,
            default_collection=default_collection,
            default_model=default_model,
        )
