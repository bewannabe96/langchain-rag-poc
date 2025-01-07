from typing import Optional

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.constants import START, END
from langgraph.graph import StateGraph

from langchain_rag.agent.space_question.hand_off import SpaceQuestionHandOff
from langchain_rag.agent.space_recommend.hand_off import SpaceRecommendHandOff
from langchain_rag.filtered_message_placeholder import FilteredMessagesPlaceholder
from langchain_rag.prompt.load_prompt import load_agent_prompt
from langchain_rag.state import State, AgentCall
from langchain_rag.tool.preference_persist_tool import PreferencePersistTool

tools = [
    PreferencePersistTool(),

    SpaceRecommendHandOff(),
    SpaceQuestionHandOff()
]

tool_dict = {tool.name: tool for tool in tools}

model = ChatOpenAI(model="gpt-4o", temperature=0).bind_tools(tools=tools)

prompt_template = ChatPromptTemplate.from_messages([
    load_agent_prompt("langchain_rag/agent/service/prompt/agent.md"),
    FilteredMessagesPlaceholder(variable_name="messages"),
])


def agent_node(state: State):
    prompt = prompt_template.invoke(state)
    message = model.invoke(prompt)
    return {"messages": [message]}


def tool_node(state: State):
    ai_message: AIMessage = state["messages"][-1]

    tool_messages: list[ToolMessage] = []
    agent_call: Optional[AgentCall] = None

    for tool_call in ai_message.tool_calls:
        tool_name = tool_call["name"]

        tool_message = tool_dict[tool_name].invoke(tool_call)
        tool_messages.append(tool_message)

        if "HandOff" in tool_name:
            agent_call = {
                "name": tool_name.replace("HandOff", ""),
                "args": tool_call["args"],
            }

    return {
        "messages": tool_messages,
        "agent_call": agent_call
    }


def tool_router(state: State):
    message = state["messages"][-1]
    if isinstance(message, AIMessage) and len(message.tool_calls) > 0:
        return "has_tool_calls"
    return "no_tool_calls"


def agent_router(state: State):
    return "no_agent_call" if state["agent_call"] is None else "has_agent_call"


builder = StateGraph(state_schema=State)

builder.add_node("agent", agent_node)
builder.add_node("tool", tool_node)

builder.add_edge(START, "agent")
builder.add_conditional_edges(
    "agent", tool_router,
    {"has_tool_calls": "tool", "no_tool_calls": END}
)
builder.add_conditional_edges(
    "tool", agent_router,
    {"has_agent_call": END, "no_agent_call": "agent"}
)

agent = builder.compile()
