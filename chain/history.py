from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

from langchain_core.chat_history import BaseChatMessageHistory

class TruncatedChatMessageHistory(ChatMessageHistory):
    max_length = 5

    def __init__(self):
        super().__init__()
        
    def add_messages(self, new_msg):
        if len(self.messages) >= self.max_length:
            self.messages.pop(0)
        super().add_messages(new_msg)
        
HISTORY_STORE = {}
def get_session_history(session_id:str):
    if session_id not in HISTORY_STORE:
        HISTORY_STORE[session_id] = TruncatedChatMessageHistory()
    return HISTORY_STORE[session_id]
