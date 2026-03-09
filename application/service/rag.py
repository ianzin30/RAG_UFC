import os
from pathlib import Path

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import CharacterTextSplitter
from langchain_groq import ChatGroq

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser


class RAGService:
    def __init__(self, collection_name=None):
        self.project_root = Path(__file__).resolve().parents[2]
        self.collections_root = self.project_root / "data" / "collections"
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.llm = ChatGroq(api_key=os.getenv("GROQ_API_KEY"), model_name="llama-3.3-70b-versatile")
        self.text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=200)

        self.vector_store = None
        self.qa_chain = None  # will hold a Runnable (LCEL)

        if collection_name:
            self.load_collection(collection_name)

    def load_collection(self, collection_name):
        collection_path = self.collections_root / collection_name
        if not collection_path.exists():
            raise Exception(f"Collection '{collection_name}' not found.")

        loader = DirectoryLoader(
            str(collection_path),
            glob="**/*.md",
            show_progress=True,
            loader_cls=TextLoader,
            loader_kwargs={"encoding": "utf-8"},
        )
        documents = loader.load()
        if not documents:
            raise Exception(f"No documents found in collection '{collection_name}'.")

        chunks = self.text_splitter.split_documents(documents)
        self.vector_store = FAISS.from_documents(chunks, self.embeddings)

        retriever = self.vector_store.as_retriever(search_kwargs={"k": 5})

        def format_docs(docs):
            return "\n\n".join(d.page_content for d in docs)

        prompt = ChatPromptTemplate.from_messages([
            ("system", "Use the retrieved context to answer. If you don't know, say you don't know."),
            ("human", "Context:\n{context}\n\nQuestion:\n{question}\nAnswer:")
        ])

        # This IS your "QA chain" now (modern runnable)
        self.qa_chain = (
            {
                "context": retriever | format_docs,
                "question": RunnablePassthrough(),
            }
            | prompt
            | self.llm
            | StrOutputParser()
        )

    def ask_question(self, question: str) -> str:
        if not self.qa_chain:
            raise Exception("No collection loaded. Please load a collection before asking questions.")

        # Instead of .run(...)
        return self.qa_chain.invoke(question)
