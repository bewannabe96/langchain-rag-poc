import json
import os
from typing import Type, Any

from langchain_core.retrievers import BaseRetriever
from langchain_core.tools import BaseTool
from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_openai import OpenAIEmbeddings
from pydantic import Field, BaseModel
from pymongo import MongoClient


class SpaceRetrieveInput(BaseModel):
    space_names: list[str] = Field(description="Names of spaces to ask questions about")


class SpaceRetrieveTool(BaseTool):
    name: str = "SpaceRetrieve"
    description: str = "Retrieve space information that can be referenced while answer questions"
    args_schema: Type[BaseModel] = SpaceRetrieveInput
    return_direct: bool = True

    retriever: BaseRetriever = Field(default=None)

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

        client = MongoClient(os.environ["SPACE_VECTOR_STORE_MONGO_CONN_STR"])
        vector_store = MongoDBAtlasVectorSearch(
            collection=client["prod"]["space_embedding"],
            index_name="space_vector_store_index",
            relevance_score_fn="cosine",
            embedding=OpenAIEmbeddings(model="text-embedding-3-large", dimensions=3072),
            text_key="text",
            embedding_key="embedding",
        )

        self.retriever = vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 20},
        )

    def _run(self, space_names: list[str]) -> str:
        query = json.dumps({"space_names": space_names})
        document_list = self.retriever.invoke(query)

        search_results = []
        for document in document_list:
            search_result = ""
            search_result += "**Space ID**\n"
            search_result += document.metadata.get("space")["ref"] + "\n"
            search_result += "**JSON formatted Space Information**\n"
            search_result += document.page_content + "\n"

            search_results.append(search_result)

        return "\n".join(search_results)
