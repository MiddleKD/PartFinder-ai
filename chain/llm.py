import os
from typing import Literal
from langchain_core.language_models import LanguageModelInput

class SimpleLLM:
    def __init__(
            self, 
            llm_type:Literal["google", "openai", "anthropic"], 
            model_name:str = None
        ):
        if llm_type == "google":
            from langchain_google_genai import ChatGoogleGenerativeAI
            os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")
            if model_name is None:
                llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0)
            else:
                llm = ChatGoogleGenerativeAI(model=model_name, temperature=0)
        elif llm_type == "openai":
            from langchain_openai import ChatOpenAI
            os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
            if model_name is None:
                llm = ChatOpenAI(temperature=0)
            else:
                llm = ChatOpenAI(model=model_name, temperature=0)
        elif llm_type == "anthropic":
            from langchain_anthropic import ChatAnthropic
            os.environ["ANTHROPIC_API_KEY"] = os.getenv("ANTHROPIC_API_KEY")
            if model_name is None:
                llm = ChatAnthropic(model="claude-3-sonnet-20240229", temperature=0)
            else:
                llm = ChatAnthropic(model=model_name, temperature=0)
        self.llm = llm

    def invoke(self, llm_input:LanguageModelInput):
        return self.llm.invoke(llm_input)