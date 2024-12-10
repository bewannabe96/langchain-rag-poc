import os
from typing import TypedDict, Sequence, Optional, Type, Annotated

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.messages import BaseMessage, ToolMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, MessagesPlaceholder
from langchain_core.tools import BaseTool
from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, END, StateGraph, add_messages
from pydantic import Field, BaseModel
from pymongo import MongoClient

# Vector Store & Retriever
client = MongoClient(os.environ["DEV_MONGO_CONNECTION_STRING"])
vector_store = MongoDBAtlasVectorSearch(
    collection=client["lab_dev"]["langchain_embedding"],
    index_name="test_vector_store_index",
    relevance_score_fn="cosine",
    embedding=OpenAIEmbeddings(model="text-embedding-3-small", dimensions=1536),
)
retriever = vector_store.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 20},
)


# Content Search Tool
class ContentSearchInput(BaseModel):
    query: str = Field(..., description="query string")


class ContentSearchTool(BaseTool):
    name: str = "ContentSearch"
    description: str = "search for places given a detailed query"
    args_schema: Type[BaseModel] = ContentSearchInput
    return_direct: bool = True

    def _run(self, query: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        document_list = retriever.invoke(query)

        search_results = []
        for document in document_list:
            search_result = ""
            search_result += "[Content ID]\n"
            search_result += document.metadata.get("content_id") + "\n"
            search_result += "[Summary]\n"
            search_result += document.page_content + "\n"

            search_results.append(search_result)

        return "\n".join(search_results)


content_search_tool = ContentSearchTool(name="ContentSearch")

# Model
model = ChatOpenAI(model="gpt-4o")
model_with_tools = model.bind_tools([content_search_tool])

# Prompt
system_prompt = SystemMessagePromptTemplate.from_template("""
You are an AI concierge designed to help users plan their activities.
Follow these steps in your conversation:

1. Basic Rules:
   - Respond in {language}
   - Maintain a polite and empathetic tone
   - Start with a warm greeting

2. Information Gathering:
   Collect the following details one by one through natural conversation
   - Who? (alone/friends/family etc.)
   - Where? (specific region/area)
   - What? (dining/drinks/activities etc.)
   - When? (date/time/preferences)

3. Place Recommendations:
   - Use "Content Search" tool to find places and generate suggestions
   - Suggest up to 3 places
   - Use only information from retrieved documents
   - If no suitable places found:
     * Suggest nearby alternatives
     * Encourage user to create their own posts

4. Response Format:
   - Provide recommendations in JSON format
   - Example: {{"<content-id>": "<reason for recommendation>"}}
""")

prompt_template = ChatPromptTemplate.from_messages([
    system_prompt,
    MessagesPlaceholder(variable_name="messages"),
])


# LangGraph
class State(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    language: str


def call_model(state: State):
    input_messages = prompt_template.invoke(state)
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


def generate_final_response(state: State):
    input_messages = prompt_template.invoke(state)
    ai_message = model_with_tools.invoke(input_messages)
    return {"messages": [ai_message]}


workflow = StateGraph(state_schema=State)

workflow.add_node("model", call_model)
workflow.add_node("tool", use_tool)
workflow.add_node("final_response", generate_final_response)

workflow.add_edge(START, "model")
workflow.add_conditional_edges(
    "model",
    should_use_tool,
    {True: "tool", False: END}
)
workflow.add_edge("tool", "final_response")
workflow.add_edge("final_response", END)

memory = MemorySaver()
agent = workflow.compile(checkpointer=memory)
