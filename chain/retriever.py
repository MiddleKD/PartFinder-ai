import os
import json
import copy
import hashlib

from typing import List, Dict, Literal, Any
from chromadb.api import ClientAPI
from chromadb.config import Settings
from langchain.pydantic_v1 import BaseModel, Field
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_community.retrievers import TavilySearchAPIRetriever
from langchain_core.vectorstores.base import VectorStoreRetriever

class WebsearchRetriever(TavilySearchAPIRetriever):

    class ToolSchema(BaseModel):
        query:str = Field(description="Simple query to obtain additional information on web.")

    def __init__(self, max_results=1):
        super().__init__(k=max_results)

    def as_tool(self):
        return super().as_tool(
            args_schema=self.ToolSchema,
            name="web_search",
            description="Obtaining additional information by searching the web."
        )

class DocRetrieverManager(Chroma):

    class ToolSchema(BaseModel):
        query:str = Field(description="Query to accurately search for the manufacturing parts the user is looking for")

    def __init__(
        self, 
        collection_name: str = "knowledgebase", 
        model_type: Literal['google', 'openai'] = "google",
        model_name: str = None,
        persist_directory: str | None = None, 
        client_settings: Settings | None = None, 
        collection_metadata: Dict | None = None, 
        client: ClientAPI | None = None
    ) -> None:
        
        if model_type == "google":
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
            if model_name is None:
                emb_model = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
            else:
                emb_model = GoogleGenerativeAIEmbeddings(model=model_name)
        elif model_type == "openai":
            from langchain_openai import OpenAIEmbeddings
            if model_name is None:
                emb_model = OpenAIEmbeddings()
            else:
                emb_model = OpenAIEmbeddings(model=model_name)

        super().__init__(
            collection_name=collection_name,
            embedding_function=emb_model,
            persist_directory=persist_directory,
            client_settings=client_settings,
            collection_metadata=collection_metadata,
            client=client
        )

    def _check_is_knowledgebase(self, inputs:List[dict]):
        for input in inputs:
            req_keys = {"part_type", "classification", "dimension_details", "metadata"}
            req_metadata_keys = {"blueprint", "ori_features"}
            req_dim_detail_keys = {"name", "alphabet", "value", "desc"}

            if not all(key in input for key in req_keys):
                raise ValueError("Input dict is not valid for knowledgebase.")
            if not all(key in input["metadata"] for key in req_metadata_keys):
                raise ValueError("Input['metadata'] is not valid for knowledgebase.")
            for dim_detail in input["dimension_details"]:
                if not all(key in dim_detail for key in req_dim_detail_keys):
                    raise ValueError("Input['dimension_details'] is not valid for knowledgebase.")
            
    def _to_document(self, inputs:List[dict]):
        docs = []
        for input in inputs:
            metadata = input.pop("metadata")
            page_content = json.dumps(input, ensure_ascii=False)
            doc = Document(page_content=page_content, metadata=metadata)
            docs.append(doc)
        return docs

    def _generate_sha256_id(self, input:Any):
        return hashlib.sha256(str(input).encode('utf-8')).hexdigest()
    
    def _check_feature_template_match(self, to_check_input:dict, template:dict):
        to_check_input = to_check_input.copy()

        eq_part_type = to_check_input["part_type"] == template["part_type"]
        eq_classification = to_check_input["classification"] == template["classification"]
        
        to_check_input.pop("part_type")
        to_check_input.pop("classification")
        alphabet_list_in = set(to_check_input.keys())
        alphabet_list_tp = set(cur["alphabet"] for cur in template["dimension_details"])
        ok_alphabets = all(elem in alphabet_list_tp for elem in alphabet_list_in)

        if all([eq_part_type, eq_classification, ok_alphabets]):
            return True
        else:
            return False

    def _insert_feature_into_template(self, features:dict, template:dict, mode:Literal["safe", "greedy"]="safe"):
        template = copy.deepcopy(template)

        result = {}
        for key, value in template.items():
            if key == "dimension_details":
                dimension_details = []
                for cur in template[key]:
                    if cur["alphabet"] not in features.keys():
                        if mode == "safe":
                            continue
                        else:
                            dimension_details.append(cur)
                    else:
                        dimension_details.append({
                            'name': cur["name"],
                            'value': features[cur["alphabet"]],
                            'alphabet': cur["alphabet"],
                            'desc': cur["desc"]
                        })
                result[key] = dimension_details
            else:
                if key in features.keys():
                    result[key] = features[key]
                else:
                    result[key] = value
        
        return result
    
    def insert_feature_list_into_template(
        self, 
        features_list:List[dict],
        template:dict,
        insert_mode:Literal["safe", "greedy"]="safe",
        check_template_matched:bool = True
    ):
        formed_features_list = []
        for features in features_list:
            if check_template_matched == True:
                if self._check_feature_template_match(features, template) == False:
                    raise ValueError("Data features and generated template does not matched")
            
            formed_features = self._insert_feature_into_template(features, template, mode=insert_mode)
            formed_features_list.append(formed_features)
        
        return formed_features_list

    def insert_dict(self, inputs:List[dict], check_is_kb:bool=True):
        
        if check_is_kb == True:
            self._check_is_knowledgebase(inputs)
            ids = [self._generate_sha256_id(
                    [input["part_type"], 
                    input["classification"], 
                    input["metadata"]["ori_features"]]
                 ) for input in inputs]
            for input, id in zip(inputs, ids):
                input["metadata"]["id"] = id
        docs = self._to_document(inputs)
        
        if check_is_kb == True:
            self.add_documents(docs, ids=ids)
        else:
            self.add_documents(docs)

    def as_retriever(self, **kwargs: Any) -> VectorStoreRetriever:
        return super().as_retriever(**kwargs)

    def as_tool(self, **kwargs):
        retriever = self.as_retriever(**kwargs)
        return retriever.as_tool(
            args_schema=self.ToolSchema,
            name="manufacturing_part_search",
            description="Searching for manufacturing parts in the database based on dimensional queries."
        )
