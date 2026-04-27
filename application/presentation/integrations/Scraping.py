"""
Web scraping integration - allows users to scrape documentation websites.

Provides UI for users to input a URL and collection name, then scrapes the website
and imports the documents into a collection for RAG querying.
"""

import streamlit as st
from service.scraping import ScrapingService


def show():
    """Display the web scraping interface."""
    st.header("Scraping de Documentações")
    st.caption("Cole a URL da documentação ou da página inicial do produto. O scraper vai priorizar a seção de docs.")

    # Display any previous scraping feedback
    feedback = st.session_state.pop("scrape_feedback", None)
    if feedback:
        st.success(feedback)

    scraper = ScrapingService()

    # Form for URL and collection name input
    with st.form("scraping_form"):
        url = st.text_input("URL da documentação para scraping:", placeholder="https://example.com/docs/")
        collection_name = st.text_input("Nome da coleção para salvar os dados:", placeholder="minha_colecao")
        submit_button = st.form_submit_button("Iniciar Scraping")

        if submit_button:
            if not url or not collection_name:
                st.warning("Por favor, preencha ambos os campos para iniciar o scraping.")
            else:
                with st.spinner("Realizando scraping..."):
                    result = scraper.scrape_website(url, collection_name)

                if isinstance(result, str):
                    st.success(result)
                elif isinstance(result, dict) and result.get("ok"):
                    files_saved = result.get("files", 0)
                    source = result.get("source", "unknown")
                    target_url = result.get("target_url")
                    st.session_state.scrape_feedback = (
                        f"{files_saved} arquivos salvos na coleção '{collection_name}' usando Firecrawl {source}"
                        + (f" a partir de '{target_url}'." if target_url else ".")
                    )
                    st.rerun()
                else:
                    error_msg = "Ocorreu um erro desconhecido durante o scraping."
                    if isinstance(result, dict):
                        error_msg = result.get("error") or result.get("message") or error_msg
                    st.error(error_msg)
