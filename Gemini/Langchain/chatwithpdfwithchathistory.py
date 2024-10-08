import streamlit as st 
from langchain.chains import create_history_aware_retriever,create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_chroma import Chroma
from langchain_community.chat_message_histories import ChatMessageHistory 
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate , MessagesPlaceholder
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
import os 
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from dotenv import load_dotenv
load_dotenv()

os.environ["HF_TOKEN"] = os.getenv("HF_TOKEN")
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

st.title("COnversation RAG with PDF uploads")
st.write("Upload PDF and chat with their content")

api_key = st.text_input("Enter your GROQ API key:",type="password")

if api_key:
    llm = ChatGroq(groq_api_key=api_key,model_name="Gemma2:9b-It")

    session_id = st.text_input("Session ID",value="default_session")

    if "store" not in st.session_state:
        st.session_state.store = {}

    uploaded_files = st.file_uploader("Choose A PDF FIle " , type="pdf" , accept_multiple_files=False)

    if uploaded_files:
        documents = []
        for uploaded_file in uploaded_files:
            temppdf = f"./temp.pdf"
            with open(temppdf,"wb") as file:
                file.write(uploaded_file.getvalue())
                file_name = uploaded_file.name
            loader = PyPDFLoader(temppdf)
            docs = loader.load()
            documents.extend(docs)

        text_splitter = RecursiveCharacterTextSplitter(chunk_size = 5000 , chunk_overlap = 200)
        splits = text_splitter.split_documents(documents)
        vectorstore= Chroma.from_documents(documents=splits,embedding=embeddings)
        retriever = vectorstore.as_retriever()


        contextualize_q_system_prompt = ()
        contextualize_q_prompt = ChatPromptTemplate.from_template(
            [("system"),contextualize_q_system_prompt,
            MessagesPlaceholder("chat_history"),("human","{input}")]
        )
history_aware_retriever = create_history_aware_retriever(llm,retriever,contextualize_q_system_prompt)

system_prompt = (
   " {context}"
)

qa_prompt = ChatPromptTemplate.from_messages(
    [
        ("system",system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human","{input}")
    ]
)
question_answer_chain = create_stuff_documents_chain(llm,qa_prompt)
rag_chain = create_retrieval_chain(history_aware_retriever,question_answer_chain)

def get_session_history(session:str) -> BaseChatMessageHistory:
    if session_id not in st.session_state.store:
        st.session_state.store[session_id] = ChatMessageHistory()
    return st.session_state.store[session_id]

conversation_rag_chain = RunnableWithMessageHistory(
    rag_chain,get_session_history,
    input_messages_key="input",
    history_messages_key="chat_history",
    output_messages_key="answer"
)

user_input = st.text_input("Your question:")
if user_input:
    session_history = get_session_history(session_id)
    response = conversation_rag_chain.invoke(
        {"input":user_input},
        config={
            "configurable":{"session_id":session_id}
        },
    )
    st.write(st.session_state.store)
    st.success("Assistant:",response["answer"])
    st.write("Chat History:",session_history.messages)
