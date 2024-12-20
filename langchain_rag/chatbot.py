from typing import Sequence

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, END, StateGraph
from pydantic import BaseModel

from langchain_rag.agent.service_agent import service_agent
from langchain_rag.agent.space_search_agent import space_search_agent
from langchain_rag.state import State

agent_dict = {
    "space_search": space_search_agent,
}


def filter_messages(original_messages: Sequence[BaseMessage],
                    updated_messages: Sequence[BaseMessage]) -> Sequence[BaseMessage]:
    last_message_id = original_messages[-1].id

    last_message_index = len(updated_messages) - 1
    while updated_messages[last_message_index].id != last_message_id:
        last_message_index -= 1

    filtered: list[BaseMessage] = []
    for message in updated_messages[last_message_index:]:
        if isinstance(message, HumanMessage):
            filtered.append(message)
        elif isinstance(message, AIMessage):
            if message.content != "":
                filtered.append(AIMessage(id=message.id, content=message.content))

    return filtered


class SwitchOutput(BaseModel):
    should_continue: bool


service_switch_model = ChatOpenAI(
    model="gpt-4o", temperature=0,
).with_structured_output(SwitchOutput)


def service_switch_node(state: State):
    continue_service = True

    if isinstance(state["messages"][-1], AIMessage):
        output: SwitchOutput = service_switch_model.invoke(state["messages"])
        continue_service = output.should_continue

    return {
        "continue_service": continue_service
    }


def call_service_agent(state: State):
    agent_state = service_agent.invoke(state)
    messages = filter_messages(state["messages"], agent_state["messages"])

    return {
        "agent_calls": agent_state["agent_calls"],
        "messages": messages
    }


def agent_manager_node(state: State):
    agent_name = state["agent_calls"][0]
    agent_state = agent_dict[agent_name].invoke(state)
    messages = filter_messages(state["messages"], agent_state["messages"])

    return {
        "agent_calls": state["agent_calls"][1:],
        "messages": messages
    }


workflow = StateGraph(state_schema=State)

workflow.add_node("service_switch", service_switch_node)
workflow.add_node("agent_manager", agent_manager_node)
workflow.add_node("service_agent", call_service_agent)

workflow.add_edge(START, "service_switch")
workflow.add_conditional_edges(
    "service_switch",
    lambda state: "service_agent" if state["continue_service"] else END,
    ["service_agent", END],
)
workflow.add_conditional_edges(
    "service_agent",
    lambda state: "agent_manager" if len(state["agent_calls"]) > 0 else END,
    ["agent_manager", END],
)
workflow.add_conditional_edges(
    "agent_manager",
    lambda state: "agent_manager" if len(state["agent_calls"]) > 0 else "service_switch",
    ["agent_manager", "service_switch"],
)

checkpointer = MemorySaver()
chatbot = workflow.compile(checkpointer=checkpointer)
