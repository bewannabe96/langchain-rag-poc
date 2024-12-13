import json
import os
from typing import TypedDict, Sequence, Optional, Type, Annotated

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.messages import BaseMessage, ToolMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import BaseTool
from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, END, StateGraph, add_messages
from pydantic import Field, BaseModel
from pymongo import MongoClient

from langchain_rag.prompt.load_prompt import load_system_prompt

# Vector Store & Retriever
client = MongoClient(os.environ["DEV_MONGO_CONNECTION_STRING"])
vector_store = MongoDBAtlasVectorSearch(
    collection=client["lab_dev"]["langchain_existing_embedding"],
    index_name="test_control_vector_store_index",
    relevance_score_fn="euclidean",
    embedding=OpenAIEmbeddings(model="text-embedding-3-large", dimensions=2048),
)
retriever = vector_store.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 20},
)


# Space Search Tool
class SpaceSearchInput(BaseModel):
    query: str = Field(..., description="query string")


class SpaceSearchTool(BaseTool):
    name: str = "SpaceSearch"
    description: str = "Search spaces given a detailed query"
    args_schema: Type[BaseModel] = SpaceSearchInput
    return_direct: bool = True

    def _run(self, query: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        document_list = retriever.invoke(query)

        search_results = []
        for document in document_list:
            search_result = ""
            search_result += "### Content ID\n"
            search_result += document.metadata.get("content_id") + "\n"
            search_result += "### Space\n"
            search_result += json.dumps(json.loads(document.page_content), indent=2) + "\n"

            search_results.append(search_result)

        return "\n".join(search_results)


content_search_tool = SpaceSearchTool(name="SpaceSearch")


# Model
class Recommendation(BaseModel):
    content_id: str
    reason: str


class RecommendationOutput(BaseModel):
    results: list[Recommendation]


model = ChatOpenAI(model="gpt-4o", temperature=0)
model_with_tools = model.bind_tools([content_search_tool])

json_model = ChatOpenAI(model="gpt-4o", temperature=0, model_kwargs={"response_format": {"type": "json_object"}})
structured_model = json_model.with_structured_output(RecommendationOutput)

general_prompt_template = ChatPromptTemplate.from_messages([
    load_system_prompt("general"),
    MessagesPlaceholder(variable_name="messages"),
])

recommendation_generation_prompt_template = ChatPromptTemplate.from_messages([
    load_system_prompt("recommendation-generation"),
    MessagesPlaceholder(variable_name="messages"),
])

recommendation_feedback_prompt_template = ChatPromptTemplate.from_messages([
    load_system_prompt("recommendation-feedback"),
    MessagesPlaceholder(variable_name="messages"),
])


# LangGraph
class State(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    language: str


def call_model(state: State):
    input_messages = general_prompt_template.invoke(state)
    ai_message = model_with_tools.invoke(input_messages)
    return {"messages": [ai_message]}


def should_use_tool(state: State) -> bool:
    last_message = state["messages"][-1]
    if not isinstance(last_message, AIMessage):
        return False

    return len(last_message.tool_calls) > 0


def use_tool(state: State):
    last_message: AIMessage = state["messages"][-1]

    tool_messages: list[ToolMessage] = []
    for tool_call in last_message.tool_calls:
        tool_message: ToolMessage = content_search_tool.invoke(tool_call)
        tool_messages.append(tool_message)

    return {"messages": tool_messages}


def generate_recommendation(state: State):
    input_messages = recommendation_generation_prompt_template.invoke(state)
    recommendation_output: RecommendationOutput = structured_model.invoke(input_messages)
    return {"messages": [AIMessage(content=recommendation_output.model_dump_json())]}


def ask_recommendation_feedback(state: State):
    input_messages = recommendation_feedback_prompt_template.invoke(state)
    ai_message = model.invoke(input_messages)
    return {"messages": [ai_message]}


workflow = StateGraph(state_schema=State)

workflow.add_node("main", call_model)
workflow.add_node("use_tool", use_tool)
workflow.add_node("generate_recommendation", generate_recommendation)
workflow.add_node("ask_recommendation_feedback", ask_recommendation_feedback)

workflow.add_edge(START, "main")
workflow.add_conditional_edges(
    "main",
    should_use_tool,
    {True: "use_tool", False: END}
)
workflow.add_edge("use_tool", "generate_recommendation")
workflow.add_edge("generate_recommendation", "ask_recommendation_feedback")
workflow.add_edge("ask_recommendation_feedback", END)

checkpointer = MemorySaver()
agent = workflow.compile(checkpointer=checkpointer)
