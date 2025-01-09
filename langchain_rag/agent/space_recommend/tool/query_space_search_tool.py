import json
import os
from typing import Type, Any
import yaml

from langchain_core.retrievers import BaseRetriever
from langchain_core.tools import BaseTool
from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_openai import OpenAIEmbeddings
from pydantic import Field, BaseModel
from pymongo import MongoClient


class QuerySpaceSearchToolArgs(BaseModel):
    query: str = Field(description="English query for space search")
    areas: list[str] = Field(description="Areas of space in English (i.e. Brooklyn)")


class QuerySpaceSearchTool(BaseTool):
    name: str = "QuerySpaceSearch"
    description: str = "Search spaces given a detailed query"
    args_schema: Type[BaseModel] = QuerySpaceSearchToolArgs
    return_direct: bool = True

    retriever: BaseRetriever = Field(default=None)
    ignore_keys: list[str] = ["coordinate", "businessStatuses", "operatingHours"]

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

    @staticmethod
    def convert_to_readable(key: str) -> str:
        remove_prefix = "space"
        remove_prefix_len = len(remove_prefix)

        if key.startswith(remove_prefix):
            key = key[remove_prefix_len:]

        result = key[0].upper()
        for char in key[1:]:
            result += (" " + char) if char.isupper() else char

        return result

    def _run(self, query: str, areas: str) -> str:
        query = query + "\n"
        query += "Area: " + ", ".join(areas) + "\n"
        document_list = self.retriever.invoke(query)

        search_results = []
        for document in document_list:
            json_doc = json.loads(document.page_content)

            transformed_doc = {"ID": document.metadata.get("space")["ref"]}
            for key, value in json_doc.items():
                if key not in self.ignore_keys:
                    new_key = self.convert_to_readable(key)
                    transformed_doc[new_key] = value

            search_results.append(transformed_doc)

        return yaml.dump(search_results, allow_unicode=True, sort_keys=False)
