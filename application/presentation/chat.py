import streamlit as st
from service.rag import RAGService

def show():

    st.header("Chat com Documentos")

    if not st.session_state.collection:
        st.info("Nenhuma coleção selecionada. Por favor, selecione uma coleção na barra lateral para começar a fazer perguntas.")
        return
    

    st.success(f"Coleção selecionada: **{st.session_state.collection}**")

    if "rag_service" not in st.session_state or st.session_state.rag_service is None:
        st.session_state.rag_service = RAGService()

        with st.spinner(f"Carregando coleção '{st.session_state.collection}'..."):
            st.session_state.rag_service.load_collection(st.session_state.collection)
            st.session_state.current_collection = st.session_state.collection
                
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    if prompt := st.chat_input("Faça uma pergunta sobre os documentos da coleção selecionada..."):
        st.chat_message("user").write(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("assistant"):
            with st.spinner("Pensando..."):
                try:
                    answer = st.session_state.rag_service.ask_question(prompt)
                    st.write(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                except Exception as e:
                    error_msg = f"Erro ao obter resposta: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
    if st.button("Limpar Conversa"):
        st.session_state.messages = []
        st.rerun()
