import os
import streamlit as st
from dotenv import load_dotenv
from chain.chat import ChatManager
from utils import byte_to_b64
from uuid import uuid4

load_dotenv()
st.set_page_config(layout="wide")
st.title("Manufacturing Search Chat")

google_api_key = None
chatmanager = None
context_data_ids = []
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid4())

if os.getenv("GOOGLE_API_KEY") is None:
    st.session_state["GOOGLE_API_KEY"] = st.sidebar.text_input('GOOGLE API KEY', type='password')
else:
    st.session_state["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")

if "messages" not in st.session_state:
    st.session_state.messages = []

chat_column, data_column = st.columns(2)

with chat_column:
    chat_container = st.container(height=400)
    with chat_container.chat_message("assistant"):
        chat_container.markdown("This is chatbot!")
    for message in st.session_state.messages:
        with chat_container.chat_message(message["role"]):
            chat_container.markdown(message["content"])

    with st.container(height=200):
        prompt = st.chat_input("Input question!")
        upload_image = st.file_uploader("Choose blueprint image", type=["jpg", "jpeg", "png"], label_visibility="collapsed")

    chatmanger = None
    base64_image = None
    if prompt:    
        if chatmanger is None or (google_api_key != st.session_state.get("GOOGLE_API_KEY")):
            google_api_key = st.session_state.get("GOOGLE_API_KEY")

            if len(google_api_key) < 5:
                st.warning("Set 'GOOGLE API KEY' first")
                st.stop()
            else:
                os.environ["GOOGLE_API_KEY"] = google_api_key
                chatmanager = ChatManager(llm_type="google", retriver_doc_num=5)

        with chat_container.chat_message("user"):
            if upload_image is not None:
                chat_container.image(upload_image)
                base64_image = byte_to_b64(upload_image.getvalue())

            chat_container.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        try:
            with chat_container.chat_message("assistant"):
                stream = chatmanager.query_steam(
                    text=prompt,
                    base64_image=base64_image,
                    session_id=st.session_state.session_id
                )
                response = chat_container.write_stream(stream)
            context_data_ids = chatmanager.get_context(st.session_state.session_id)
            st.session_state.messages.append({"role": "assistant", "content": response})
        except:
            with chat_container.chat_message("assistant"):
                chat_container.write("Somethig is wrong. Try again later.")

    # Show me the bolt with a height greater than 10.0mm and smaller than 12.1mm."
import pandas as pd
from parse import parse_doc_to_df
with data_column:
    data_container = st.container(height=600)
    data_container.markdown("### Related datas:")
    print(context_data_ids)
    if chatmanager is not None:
        docs = chatmanager.get_docs_from_ids(context_data_ids)
        data_df = parse_doc_to_df(
            documents=docs,
            fields=[("metadata","blueprint"), ("page_content", "part_type"), ("page_content", "classification"), ("metadata","id")],
            img_root_dir="./data/bps"
        )

        data_container.data_editor(
            data_df,
            column_config={
                "blueprint": st.column_config.ImageColumn(
                    "Preview Image", help="Streamlit app preview screenshots"
                ),
                "part_type": st.column_config.TextColumn(
                    "Widgets",
                    help="Streamlit **widget** commands 🎈",
                    default="st.",
                    max_chars=50,
                    validate="^st\.[a-z_]+$",
                ),
                "classification": st.column_config.TextColumn(
                    "Widgets",
                    help="Streamlit **widget** commands 🎈",
                    default="st.",
                    max_chars=50,
                    validate="^st\.[a-z_]+$",
                ),
                "id": st.column_config.TextColumn(
                    "Widgets",
                    help="Streamlit **widget** commands 🎈",
                    default="st.",
                    max_chars=50,
                    validate="^st\.[a-z_]+$",
                )
            },
            hide_index=True,
        )