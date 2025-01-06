import os
from typing import Type, Any

from langchain_core.tools import BaseTool
from pydantic import Field, BaseModel
from pymongo import MongoClient
from pymongo.synchronous.collection import Collection


class SpaceRetrieveInput(BaseModel):
    space_names: list[str] = Field(description="Names of spaces to ask questions about")


class SpaceRetrieveTool(BaseTool):
    name: str = "SpaceRetrieve"
    description: str = "Retrieve space information that can be referenced while answer questions"
    args_schema: Type[BaseModel] = SpaceRetrieveInput
    return_direct: bool = True

    collection: Collection = Field(default=None)

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        client = MongoClient(os.environ["SPACE_VECTOR_STORE_MONGO_CONN_STR"])
        self.collection = client["prod"]["space"]

    def _run(self, space_names: list[str]) -> str:
        documents = []
        for space_name in space_names:
            documents += self.collection.aggregate([
                {
                    "$search": {
                        "index": "space_names_search",
                        "compound": {
                            "should": [
                                {"autocomplete": {"query": space_name, "path": "names.en"}},
                                {"autocomplete": {"query": space_name, "path": "names.ko"}}
                            ],
                            "minimumShouldMatch": 1,
                        },
                    },
                },
                {"$project": {"embeddingText": 1}},
                {"$limit": 5}
            ])

        search_results = []
        for doc in documents:
            if "embeddingText" not in doc:
                continue

            search_result = "**JSON formatted Space Document**\n"
            search_result += doc["embeddingText"] + "\n\n"

            search_results.append(search_result)

        return "\n".join(search_results)
