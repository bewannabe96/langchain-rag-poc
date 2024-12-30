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

        client = MongoClient(os.environ["MONGO_CONNECTION_STRING"])
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

    def _run(self, query: str, areas: str) -> str:
        query = query + "\n"
        query += "Area: " + ", ".join(areas) + "\n"
        document_list = self.retriever.invoke(query)

        search_results = []
        for document in document_list:
            search_result = ""
            search_result += "### Space ID\n"
            search_result += document.metadata.get("space")["ref"] + "\n"
            search_result += "### JSON formatted Space Information\n"
            search_result += document.page_content + "\n"

            search_results.append(search_result)

        return "\n".join(search_results)
