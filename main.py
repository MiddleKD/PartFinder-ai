from chain.chat import ChatManager
from dotenv import load_dotenv

load_dotenv()

chat_manager = ChatManager("google")

context = None
for chunk in chat_manager.query_steam("Show me the bolt with a height greater than 10.0mm and smaller than 12.1mm."):
    if chunk["type"] == "answer":
        print(chunk["content"], end="", flush=True)
    elif chunk["type"] == "context":
        context = chunk["content"]

print(len(context), context[0].page_content, context[0].metadata)
from langchain_core.documents.base import Document
# for chunk in chat_manager.query_steam(
#     "Search some nuts with a 'D' greater than 2.0mm and smaller than 4.5mm.",
#     image_path="./data/bps/나비너트1종.jpg"):
#     if chunk["type"] == "answer":
#         print(chunk["content"], end="", flush=True)
#     elif chunk["type"] == "context":
#         context = chunk["content"]

# print(len(context))