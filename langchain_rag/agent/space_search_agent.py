from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel

from langchain_rag.filtered_message_placeholder import FilteredMessagesPlaceholder
from langchain_rag.message.space_recommendation_message import SpaceRecommendationMessage
from langchain_rag.prompt.load_prompt import load_agent_prompt
from langchain_rag.state import State
from langchain_rag.tool.space_search_tool import SpaceSearchTool

tools = [
    SpaceSearchTool()
]


class Selection(BaseModel):
    content_id: str
    reason: str


class SelectionOutput(BaseModel):
    results: list[Selection]


search_model = ChatOpenAI(
    model="gpt-4o", temperature=0,
).bind_tools(tools)

selection_model = ChatOpenAI(
    model="gpt-4o", temperature=0
).with_structured_output(SelectionOutput)

feedback_model = ChatOpenAI(
    model="gpt-4o", temperature=0,
).bind_tools(tools)

search_prompt_template = ChatPromptTemplate.from_messages([
    load_agent_prompt("agent/space_search/search"),
    FilteredMessagesPlaceholder(variable_name="messages"),
])

selection_prompt_template = ChatPromptTemplate.from_messages([
    load_agent_prompt("agent/space_search/selection"),
    FilteredMessagesPlaceholder(variable_name="messages"),
])

feedback_prompt_template = ChatPromptTemplate.from_messages([
    load_agent_prompt("agent/space_search/feedback"),
    FilteredMessagesPlaceholder(variable_name="messages"),
])


def search_node(state: State):
    prompt = search_prompt_template.invoke(state)
    message = search_model.invoke(prompt)
    return {"messages": [message]}


def selection_node(state: State):
    prompt = selection_prompt_template.invoke(state)
    output: SelectionOutput = selection_model.invoke(prompt)
    return {"messages": [SpaceRecommendationMessage(content=output.model_dump_json())]}


def feedback_node(state: State):
    prompt = feedback_prompt_template.invoke(state)
    message = feedback_model.invoke(prompt)
    return {"messages": [message]}


def tool_router(state: State):
    message = state["messages"][-1]
    if isinstance(message, AIMessage) and len(message.tool_calls) > 0:
        return "has_tool_calls"
    return "no_tool_calls"


builder = StateGraph(state_schema=State)

builder.add_node("search", search_node)
builder.add_node("selection", selection_node)
builder.add_node("feedback", feedback_node)
builder.add_node("tool", ToolNode(tools=tools))

builder.add_edge(START, "search")
builder.add_conditional_edges(
    "search", tool_router,
    {"has_tool_calls": "tool", "no_tool_calls": END}
)
builder.add_edge("tool", "selection")
builder.add_edge("selection", "feedback")
builder.add_edge("feedback", END)

space_search_agent = builder.compile()
