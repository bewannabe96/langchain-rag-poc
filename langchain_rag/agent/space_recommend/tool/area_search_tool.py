import os
from typing import TypedDict, Optional, Annotated

import yaml
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from pydantic import BaseModel
from pymongo import MongoClient


class SelectionOutput(BaseModel):
    area_id: Optional[str]


class State(TypedDict):
    area: str

    translated_area: Optional[str]
    documents: Optional[list[dict]]
    area_id: Optional[str]


client = MongoClient(os.environ["SPACE_VECTOR_STORE_MONGO_CONN_STR"])


def search_node(state: State):
    cursor = client["daytrip_area"]["node"].aggregate([
        {
            "$search": {
                "index": "area_node_name_search",
                "compound": {
                    "should": [
                        {"autocomplete": {"query": state["area"], "path": "name.en"}},
                        {"autocomplete": {"query": state["area"], "path": "name.ko"}}
                    ],
                    "minimumShouldMatch": 1,
                },
            }
        },
        {"$limit": 20},
        {"$project": {"_id": 1, "name": 1}}
    ])

    return {
        "documents": [{
            "id": str(doc["_id"]),
            "name": doc["name"]
        } for doc in cursor]
    }


def selection_node(state: State):
    prompt_template = ChatPromptTemplate.from_messages([
        SystemMessage(content=f"Return the document corresponding to the area {state['area']} "
                              f"from the documents provided by the user.\n"
                              f"If no matching document is found, leave the response empty.\n"
                              f"There MUST be no false positives."),
        HumanMessage(content=yaml.dump(state["documents"], allow_unicode=True, sort_keys=False))
    ])
    model = ChatOpenAI(model="gpt-4o", temperature=0).with_structured_output(SelectionOutput)

    prompt = prompt_template.invoke({})
    selection_output: SelectionOutput = model.invoke(prompt)

    return {"area_id": selection_output.area_id}


builder = StateGraph(state_schema=State)

builder.add_node("search", search_node)
builder.add_node("selection", selection_node)

builder.add_edge(START, "search")
builder.add_edge("search", "selection")
builder.add_edge("selection", END)

agent = builder.compile()


@tool
def AreaSearch(
        area_name: Annotated[str, "Localized name of area"]
) -> Optional[str]:
    """
    Search for area ID by area name
    """

    agent_state = agent.invoke({"area": area_name})
    return agent_state["area_id"]
