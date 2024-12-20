import json
import os
from typing import Type, Any

from langchain_core.retrievers import BaseRetriever
from langchain_core.tools import BaseTool
from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_openai import OpenAIEmbeddings
from pydantic import Field, BaseModel
from pymongo import MongoClient


class SpaceSearchInput(BaseModel):
    query: str = Field(description="Query for space search")
    areas: list[str] = Field(description="Areas of space (i.e. Brooklyn)")


class SpaceSearchTool(BaseTool):
    name: str = "SpaceSearch"
    description: str = "Search spaces given a detailed query"
    args_schema: Type[BaseModel] = SpaceSearchInput
    return_direct: bool = True

    retriever: BaseRetriever = Field(default=None)

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

        client = MongoClient(os.environ["DEV_MONGO_CONNECTION_STRING"])
        vector_store = MongoDBAtlasVectorSearch(
            collection=client["lab_dev"]["langchain_existing_embedding"],
            index_name="test_control_vector_store_index",
            relevance_score_fn="euclidean",
            embedding=OpenAIEmbeddings(model="text-embedding-3-large", dimensions=2048),
        )

        self.retriever = vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 20},
        )

    def _run(self, query: str, areas: str) -> str:
        query = query + "\n"
        query += "Area: " + ", ".join(areas) + "\n"
        document_list = self.retriever.invoke(query)

        search_results = []
        for document in document_list:
            search_result = ""
            search_result += "### Content ID\n"
            search_result += document.metadata.get("content_id") + "\n"
            search_result += "### Space\n"
            search_result += json.dumps(json.loads(document.page_content), indent=2) + "\n"

            search_results.append(search_result)

        return "\n".join(search_results)
