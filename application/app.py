import streamlit as st
from pathlib import Path
from dotenv import load_dotenv
from presentation import scraping
from presentation import chat
from presentation import google_drive

PROJECT_ROOT = Path(__file__).resolve().parents[1]

load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "collection" not in st.session_state:
    st.session_state.collection = None
if "mode" not in st.session_state:
    st.session_state.mode = "Chat"
if "mode_selector" not in st.session_state:
    st.session_state.mode_selector = st.session_state.mode

if "pending_mode" in st.session_state:
    st.session_state.mode = st.session_state.pending_mode
    st.session_state.mode_selector = st.session_state.pending_mode
    del st.session_state.pending_mode


def sync_mode():
    st.session_state.mode = st.session_state.mode_selector

st.set_page_config(
    page_title="My Streamlit App",
    page_icon=":rocket:",
    layout="wide",
)
st.title("RAG Treino!")

with st.expander("Sobre o projeto"):
    st.write(
        """
        Este projeto é um exemplo de aplicação Streamlit com RAG para demonstrar a criação de uma interface interativa. 
        """
    )

with st.sidebar:
    st.header("Coleções")
    st.radio("Modo:", ("Chat", "Scraping", "Google Drive"), key="mode_selector", on_change=sync_mode)

    st.divider()
    st.subheader("Coleções disponíveis")

    collections_dir = PROJECT_ROOT / "data" / "collections"
    if collections_dir.exists():
        collections = sorted(f.name for f in collections_dir.iterdir() if f.is_dir())

        for collection in collections:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(collection)
            with col2:
                if st.button("Selecionar", key=f"use_{collection}"):
                    st.session_state.collection = collection
                    st.session_state.current_collection = None
                    st.session_state.messages = []
                    st.session_state.rag_service = None
                    st.session_state.pending_mode = "Chat"
                    st.rerun()

if st.session_state.mode == "Scraping":
    scraping.show()
if st.session_state.mode == "Chat":
    chat.show()
if st.session_state.mode == "Google Drive":
    google_drive.show()
