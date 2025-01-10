import json
import os
from typing import Annotated

import yaml
from langchain_core.tools import tool
from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_openai import OpenAIEmbeddings
from pymongo import MongoClient

from langchain_rag.agent.space_recommend.tool.area_search_tool import AreaSearch

client = MongoClient(os.environ["SPACE_VECTOR_STORE_MONGO_CONN_STR"])
vector_store = MongoDBAtlasVectorSearch(
    collection=client["prod"]["space_embedding"],
    index_name="space_vector_store_index",
    relevance_score_fn="cosine",
    embedding=OpenAIEmbeddings(model="text-embedding-3-large", dimensions=3072),
    text_key="text",
    embedding_key="embedding",
)

retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 20})


def convert_to_readable(key: str) -> str:
    remove_prefix = "space"
    remove_prefix_len = len(remove_prefix)

    if key.startswith(remove_prefix):
        key = key[remove_prefix_len:]

    result = key[0].upper()
    for char in key[1:]:
        result += (" " + char) if char.isupper() else char

    return result


@tool
def QuerySpaceSearch(
        query: Annotated[str, "English query for space search"],
        area: Annotated[str, "Localized area of space"],
) -> str:
    """
    Search spaces given a detailed query
    """

    area_id = AreaSearch(area)

    pre_filter = None

    if area_id is None:
        query = (f"{query}\n"
                 f"Area: {area}\n")
    else:
        pre_filter = {"areaIds": area_id}

    document_list = retriever.invoke(query, pre_filter=pre_filter)

    search_results = []
    ignore_keys: list[str] = ["coordinate", "businessStatuses", "operatingHours"]
    for document in document_list:
        json_doc = json.loads(document.page_content)

        transformed_doc = {"ID": document.metadata.get("space")["ref"]}
        for key, value in json_doc.items():
            if key not in ignore_keys:
                new_key = convert_to_readable(key)
                transformed_doc[new_key] = value

        search_results.append(transformed_doc)

    return yaml.dump(search_results, allow_unicode=True, sort_keys=False)
