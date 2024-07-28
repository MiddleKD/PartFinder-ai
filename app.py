import os
import streamlit as st
from dotenv import load_dotenv
from chain.chat import ChatManager
import pandas as pd
from utils import byte_to_b64, open_img
from uuid import uuid4
from parse import parse_dict_to_df

load_dotenv()

st.set_page_config(layout="wide")
st.markdown("""## 📐🔍PartFinder AI\n**Speak Blueprint:** AI-Powered Intuitive Manufacturing Parts Search System""")

context_data_ids = None

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid4())

if os.getenv("GOOGLE_API_KEY") is not None:
    os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")

if "avatar_icon" not in st.session_state:
    st.session_state.avatar_icon = {
        "user": open_img("./assets/user.jpg", mode="pil"),
        "assistant": open_img("./assets/assistant.jpg", mode="pil")
    }

@st.dialog("API error")
def error_modal(message):
    st.write(message)

sidebar_container = st.sidebar.container()
with sidebar_container:
    google_api_key_input = st.text_input('GOOGLE API KEY', type='password', value="")
    
    with st.container(border=True):
        st.markdown("### Text example")
        st.markdown("`Show me the bolt with a height greater than 10.0mm and smaller than 15.0mm.`")
    with st.container(border=True):
        st.markdown("### Image example")
        st.image(open_img("./assets/example_image.jpg", mode="bytes"))
        st.markdown("`Search some nuts with a 'D' greater than 3.0mm.`")

if len(google_api_key_input) >= 30:
    os.environ["GOOGLE_API_KEY"] = google_api_key_input
    if "chatmanager" in st.session_state:
        del st.session_state["chatmanager"]
elif google_api_key_input == "":
    pass
else:
    error_modal("Your API key is wrong format.")

if "chatmanager" not in st.session_state and len(os.environ.get("GOOGLE_API_KEY", "")) >= 30:
    st.session_state.chatmanager = ChatManager(llm_type="google", retriver_doc_num=5)

if "messages" not in st.session_state:
    st.session_state.messages = []

chat_column, data_column = st.columns(2)

with chat_column:
    chat_container = st.container(height=400)
    if ("chatmanager" in st.session_state):
        with chat_container.chat_message("assistant", avatar=st.session_state.avatar_icon["assistant"]):
            chat_container.markdown("Hi! This is PartFinder AI. Let me help you find manufacturing parts.")
    for message in st.session_state.messages:
        with chat_container.chat_message(message["role"], avatar=st.session_state.avatar_icon[message["role"]]):
            chat_container.markdown(message["content"])

    with st.container(height=200):
        prompt = st.chat_input("Input question!")
        upload_image = st.file_uploader("Choose blueprint image", type=["jpg", "jpeg", "png"], label_visibility="collapsed")

    if prompt:
        
        if ("chatmanager" not in st.session_state):
            error_modal("Set 'GOOGLE API KEY' first")
        else:
            base64_image = None
            with chat_container.chat_message("user", avatar=st.session_state.avatar_icon["user"]):
                if upload_image is not None:
                    chat_container.image(upload_image)
                    base64_image = byte_to_b64(upload_image.getvalue())

                chat_container.markdown(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})

            try:
                with chat_container.chat_message("assistant", avatar=st.session_state.avatar_icon["assistant"]), st.spinner('Wait for it...'):
                    stream = st.session_state.chatmanager.query_steam(
                        text=prompt,
                        base64_image=base64_image,
                        session_id=st.session_state.session_id
                    )
                    response = chat_container.write_stream(stream)
                context_data_ids = st.session_state.chatmanager.get_context(st.session_state.session_id)
                st.session_state.messages.append({"role": "assistant", "content": response})
            except:
                error_modal("Somethig is wrong. Try again later.")

with data_column:
    data_container = st.container(height=600)
    data_container.markdown("**Related datas:**")
    
    if "chatmanager" in st.session_state and context_data_ids is not None:
        datas = st.session_state.chatmanager.get_docs_from_ids(context_data_ids)

        data_df = parse_dict_to_df(
            datas=datas,
            fields=[
                ("documents", "part_type"),
                ("documents", "classification"),
                ("metadatas", "id"),
                ("metadatas", "blueprint"),
                ("documents", "dimension_details"),
                ("metadatas", "ori_features"),
            ],
        )
        st.session_state.df = data_df
    
    if "df" in st.session_state:
        event = data_container.dataframe(
            st.session_state.df,
            height=200,
            column_order=("part_type", "classification", "id"),
            column_config={
                "part_type": st.column_config.Column(
                    "Name",
                    disabled=True,
                ),
                "classification": st.column_config.Column(
                    "Classification",
                    disabled=True,
                ),
                "id": st.column_config.Column(
                    "DB id",
                    width="small",
                    disabled=True,
                ),
            },
            hide_index=True,
            on_select="rerun",
            selection_mode=["single-row"]
        )

        selected_rows = event.selection["rows"]
        if len(selected_rows) != 0:
            selected_record = st.session_state.df.iloc[selected_rows]

            dc_c1, dc_c2 = data_container.columns(2)
            dc_c1.markdown("**Blueprint:**")
            dc_c1.image(
                open_img(os.path.join(os.getenv("BLUEPRINT_DIR"), selected_record["blueprint"].values[0]), mode="bytes"),
                caption=selected_record['part_type'].values[0]
            )
            dc_c1.markdown("**Original data:**")
            dc_c1.json(selected_record['ori_features'].values[0], expanded=False)
            
            dc_c2.markdown("**Generated data:**")
            dc_c2.dataframe(
                pd.DataFrame(selected_record["dimension_details"].values[0]),
                column_config={
                    "name": st.column_config.Column(
                        "Name",
                        width="small",
                        disabled=True,
                    ),
                    "value": st.column_config.Column(
                        "Value",
                        width="small",
                        disabled=True,
                    ),
                    "alphabet": st.column_config.Column(
                        "Alias",
                        width="small",
                        disabled=True,
                    ),
                    "desc": st.column_config.Column(
                        "Describe",
                        disabled=True,
                    ),
                },
                hide_index=True
            )
