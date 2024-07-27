from typing import Literal, Generator, List

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains.history_aware_retriever import create_history_aware_retriever
from langchain.chains import create_retrieval_chain
from langchain_core.documents import Document

from chain.llm import SimpleLLM
from chain.retriever import DocRetrieverManager
from chain.history import RunnableWithMessageHistory, get_session_history, HISTORY_STORE
from chain.prompt import (
    CONTEXT_SYSTEM_PROMPT,
    QUERY_SYSTEM_PROMPT,
)

class ChatManager:
    llm = None
    retriever_manager = None
    retriever = None
    context_prompt_template = None
    query_prompt_template = None
    chain = None
    context_store = {}

    def __init__(
        self,
        llm_type:Literal["google", "openai", "anthropic"], 
        model_name:str = None,
        retry_count:int = 3,
        retriver_doc_num:int = 10,
        score_threshold:float = 0.6,
    ) -> None:
        
        self.llm = SimpleLLM(
            llm_type=llm_type, 
            model_name=model_name, 
            retry_count=retry_count
        )

        self.retriever_manager = DocRetrieverManager(
            collection_name="knowledgebase", 
            persist_directory="./chroma"
        )
        self.set_retriever(retriver_doc_num, score_threshold)
        self.set_prompt_template(mode="text")
        self.set_chain()

    def set_prompt_template(self, mode:Literal["text", "multimodal"]="text"):
        if mode == "text":
            self.context_prompt_template = ChatPromptTemplate.from_messages(
                [
                    ("system", CONTEXT_SYSTEM_PROMPT),
                    MessagesPlaceholder("chat_history"),
                    ("human", "{input}")
                ]
            )

            self.query_prompt_template = ChatPromptTemplate.from_messages(
                [
                    ("system", QUERY_SYSTEM_PROMPT),
                    MessagesPlaceholder("chat_history"),
                    ("human", "{input}"),
                ]
            )
        elif mode == "multimodal":
            self.context_prompt_template = ChatPromptTemplate.from_messages(
                [
                    ("system", CONTEXT_SYSTEM_PROMPT),
                    MessagesPlaceholder("chat_history"),
                    ("human",
                    [
                        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,{base64_image}"}},
                        {"type": "text", "text": "{input}"},
                    ]
                    )
                ]
            )

            self.query_prompt_template = ChatPromptTemplate.from_messages(
                [
                    ("system", QUERY_SYSTEM_PROMPT),
                    MessagesPlaceholder("chat_history"),
                    ("human",
                    [
                        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,{base64_image}"}},
                        {"type": "text", "text": "{input}"},
                    ]
                    )
                ]
            )

    def set_retriever(self, retriver_doc_num:int = 10, score_threshold:float = 0.6):
        self.retriever = self.retriever_manager.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={'k':retriver_doc_num, 'score_threshold': score_threshold}
        )
    
    def set_chain(self):

        history_aware_retriever = create_history_aware_retriever(
            self.llm, self.retriever, self.context_prompt_template
        )

        qa_chain = create_stuff_documents_chain(self.llm, self.query_prompt_template)

        self.chain = RunnableWithMessageHistory(
            create_retrieval_chain(history_aware_retriever, qa_chain),
            get_session_history,
            input_messages_key="input",
            history_messages_key="chat_history",
            output_messages_key="answer",
        )
    
    def update_retriever(self, retriver_doc_num:int = 10, score_threshold:float = 0.6):
        self.set_retriever(retriver_doc_num=retriver_doc_num, score_threshold=score_threshold)
        self.set_chain()
    
    def update_prompt_template(self, mode:Literal["text", "multimodal"]="text"):
        self.set_prompt_template(mode=mode)
        self.set_chain()
    
    def update_context(self, session_id:str, context:List[Document]):
        ids = []
        for doc in context:
            if hasattr(doc, "metadata"):
                id = doc.metadata.get("id", None)
                if id is not None:
                    ids.append(id)
        self.context_store[session_id] = ids
    
    def get_context(self, session_id:str):
        return self.context_store.get(session_id, None)

    def get_docs_from_ids(self, ids:List[str]):
        return self.retriever_manager.get(ids, include=["documents", "metadatas"])

    def query(self, text:str, base64_image:str=None, session_id:str="abc123"):
        if base64_image == None:
            self.update_prompt_template(mode="text")
            inputs = {"input": text}
        else:
            self.update_prompt_template(mode="multimodal")
            inputs = {"input": text, "base64_image": base64_image}
        
        config = {
            "configurable": {"session_id": session_id},
        }
        output = self.chain.invoke(
            inputs,
            config=config
        )
        context = output["context"]

        if len(context) > 0:
            self.update_context(session_id, output["context"])
        
        return output["answer"]

    def query_steam(
            self,
            text: str,
            base64_image: str = None,
            session_id: str = "abc123"
        )-> Generator[Document, None, None]:
        if base64_image is None:
            self.update_prompt_template(mode="text")
            inputs = {"input": text}
        else:
            self.update_prompt_template(mode="multimodal")
            inputs = {"input": text, "base64_image": base64_image}
        
        config = {
            "configurable": {"session_id": session_id},
        }
        
        for chunk in self.chain.stream(inputs, config=config):
            if "answer" in chunk:
                yield chunk["answer"]
            if "context" in chunk:
                context = chunk["context"]
        
        if len(context) > 0:
            self.update_context(session_id, context)
