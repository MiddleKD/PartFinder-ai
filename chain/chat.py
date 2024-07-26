from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains.history_aware_retriever import create_history_aware_retriever
from langchain.chains import create_retrieval_chain

from llm import SimpleLLM
from retriever import DocRetrieverManager
from history import RunnableWithMessageHistory, get_session_history, HISTORY_STORE

from dotenv import load_dotenv
load_dotenv()

llm = SimpleLLM(llm_type="google")

retriever = DocRetrieverManager(
    collection_name="knowledgebase", 
    persist_directory="./chroma"
).as_retriever(
    search_type="similarity_score_threshold",
    search_kwargs={'k':5, 'score_threshold': 0.6}
)

contextualize_q_system_prompt = """Given a chat history and the latest user question \
which might reference context in the chat history, formulate a standalone question \
which can be understood without the chat history. Do NOT answer the question, \
just reformulate it if needed and otherwise return it as is.\
YOU MUST ANSWER IN ENGLISH"""
contextualize_q_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", contextualize_q_system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ]
)

history_aware_retriever = create_history_aware_retriever(
    llm, retriever, contextualize_q_prompt
)

system_prompt = (
"""
Instructions:
Use clear and reliable language.
You are an expert in manufacturing parts, and based on the additional information, answer as detailed and professionally as possible.
This is very important for my career; if you do well, I will give you a tip.

Procedure:
1. Understand the user's question intent.
2. Search for what the user wants in the additional information and answer.
3. Think of other helpful information to provide.
4. Summarize and recommend at least one suitable option.

Rules:
1. Answers must be based on additional information.
2. Avoid using the text "additional information" in the output.
3. Summarize and recommend at least one suitable option.
4. Use natural language not json or code.

Output Example:
Manufacturing part info output
Manufacturing part info output
Manufacturing part info output
...
{{Helpful information}}
{{Most suitable option}}

Additional Information:
{context}
"""
)
qa_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ]
)

qa_chain = create_stuff_documents_chain(llm, qa_prompt)

total_chain = RunnableWithMessageHistory(
    create_retrieval_chain(history_aware_retriever, qa_chain),
    get_session_history,
    input_messages_key="input",
    history_messages_key="chat_history",
    output_messages_key="answer",
)

out = total_chain.invoke(
    {"input": "Show me the bolt with a height greater than 10.0mm and smaller than 12.1mm.",},
    config={
        "configurable": {"session_id": "abc123"}
    },  # constructs a key "abc123" in `store`.
)

print(out)
print(out["answer"])
print(HISTORY_STORE)