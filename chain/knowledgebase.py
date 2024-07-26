import os, re, time
import json
from typing import Literal, List
from langchain_core.pydantic_v1 import (
    BaseModel,
    Field
)
from langchain.prompts import (
    PromptTemplate,
    FewShotPromptTemplate,
    ChatPromptTemplate,
)
from langchain_core.messages import AIMessage
from chain.llm import SimpleLLM
from utils import open_img

PREFIX_KNOWLEDGE_BASE_PROMPT = """
Use concise, clear, and trustworthy language.
You're a blueprint analysis expert for manufacturing companies. When given a blueprint image and additional information as input, analyze it in as much detail and professional manner as possible.
This is crucial for my career. If you do well, I'll give you a tip.

Identify the alphabets representing dimensions in the blueprint.
Determine what these dimensions mean based on the additional information.
Assign a brief title to each alphabet.

Do your best to clearly represent the dimensional information in the blueprint.
Use concise sentences.
"""
SUFFIX_KNOWLEDGE_BASE_PROMPT = """
Do not use BOLD(**)
Maintain the exact format provided in the example.
USE TOOLS AS MUCH AS YOU CAN
This task is crucial in the manufacturing field, so handle it with care.
"""
EXAMPLE_KNOWLEDGE_BASE_LIST = [
    {"example": "##Part name:Wing Nut_Type 1_M2\n\n##Classification:Nut>Wing Nut>Type 1\n\n##Dimensional Information:\nWidth: 4.0(A')\nHeight: 3.0(B')\nThickness: 2.0(C)\nTotal Length: 12.0(D)\nTotal Height: 6.0(H)\nHole Diameter: 2.5(G1)\n\n"},
    {"example": "##Part name:Stud Bolt_Type 1_M10x16\n\n##Classification:Bolt>Stud Bolt>Type 1\n\n##Dimensional Information:\nDiameter: 10.0(D)\nHead Diameter: 20.0(B)\nLength: 16.0(Bm)\nHead Height: 12.0(Z)\nHead Angle: 1.5(La)\nHead Length: 2.0(L)\n\n"},
    {"example": "##Part name:Slotted Countersunk Flat Head Screw_M10x16\n\n##Classification:Screw>Countersunk Head Screw>Slotted Countersunk Flat Head Screw\n\n##Dimensional Information:Diameter: 0.1(D)\nThread Diameter: 10.0(Dk)\nHead Height: 2.5(K)\nTotal Length: 16.0(C)\nHead Width: 5.5(N)\nSlot Depth: 1.5(T)\nScrew Head Diameter: 20.0(Z)\nThread Pitch: 2.0(L)\n\n"},
]

class KnowledgeBaseTemplateChain(SimpleLLM):
    
    KNOWLEDGEBASE_PROMPT_TEMPLATE = ChatPromptTemplate.from_messages(
        messages=[
            ("system", "{system_message}"),
            ("human",
            [
                {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,{base64_image}"}},
                {"type": "text", "text": "{features}"},
            ]
            ),
        ],
    )
    
    class DimensionalInfoTool(BaseModel):
        name:str = Field(description="Natural language text expressing each dimension means")
        alphabet:str = Field(description="Alphabets representing dimensions in the blueprint")
        value:float = Field(description="Dimension values in the blueprint")
        desc: str = Field(description="Super detailed description of dimension name without specific value")

    def __init__(
        self, 
        llm_type: Literal['google', 'openai', 'anthropic'],
        model_name: str = None,
        retry_count: int = 3,
    ):
        super().__init__(llm_type, model_name, retry_count)
        
        self.retry_count = retry_count
        self.system_message = self._make_sysmsg_with_fewshot(examples=EXAMPLE_KNOWLEDGE_BASE_LIST)
        self.chain = \
            self.KNOWLEDGEBASE_PROMPT_TEMPLATE \
            | self.llm.bind_tools(self.DimensionalInfoTool) \
            | self._parse_llm_output

    def _make_sysmsg_with_fewshot(self, examples:List[dict] = []):
        fewshot_prompt_template = FewShotPromptTemplate(
            prefix=PREFIX_KNOWLEDGE_BASE_PROMPT,
            examples=examples,
            suffix=SUFFIX_KNOWLEDGE_BASE_PROMPT,
            example_prompt=PromptTemplate(
                input_variables=["example"],
                template="{example}"
            )
        )
        return fewshot_prompt_template.format()

    def _parse_llm_output(self, llm_output:AIMessage):
        tools = llm_output.tool_calls
        if len(tools) == 0:
            raise ValueError("Knowledge base is None. RUN AGAIN or provide more information as input.")
        return [cur['args'] for cur in tools]
    
    def _clean_with_regex(self, text:str):
        text = text.replace('\\', '')
        text = re.sub(r'[^\w\s.,!?\'"\-]', '', text)
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        return text

    def update_sysmsg_with_fewshot(self, examples:List[dict] = []):
        self.system_message = self._make_sysmsg_with_fewshot(examples=examples)

    def invoke(self, image_path:str, features:dict):
        base64_image = open_img(image_path, mode="b64")
        
        for retry_idx in range(self.retry_count):
            try:
                output_list = self.chain.invoke({
                    "system_message":self.system_message,
                    "base64_image":base64_image,
                    "features":features,
                })
                break
            except ValueError as e:
                print(f"Retry({retry_idx})... cause{e}")
                time.sleep(5)
        
        cleaned_list = []
        for output in output_list:
            cleaned_output = {}
            for key, value in output.items():
                if isinstance(value, str):
                    value = self._clean_with_regex(value)
                cleaned_output[key] = value
            cleaned_list.append(cleaned_output)
        
        return {
            "part_type": features["part_type"],
            "classification": features["classification"],
            "dimension_details": cleaned_list,
            "metadata": {
                "blueprint":os.path.basename(image_path), 
                "ori_features":json.dumps(features, ensure_ascii=False)
            }
        }
    