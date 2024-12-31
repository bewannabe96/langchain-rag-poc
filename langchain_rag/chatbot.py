import os
from typing import Sequence

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.checkpoint.mongodb import MongoDBSaver
from langgraph.graph import START, END, StateGraph
from pymongo import MongoClient

from langchain_rag.agent.related_question_agent import related_question_agent
from langchain_rag.agent.service_agent import service_agent
from langchain_rag.agent.space_search_agent import space_search_agent
from langchain_rag.state import State

agent_dict = {
    "space_search": space_search_agent,
}


def filter_newly_generated_messages(original_messages: Sequence[BaseMessage],
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

        elif isinstance(message, ToolMessage):
            continue

        else:
            filtered.append(message)

    return filtered


def call_service_agent(state: State):
    agent_state = service_agent.invoke(state)
    messages = filter_newly_generated_messages(state["messages"], agent_state["messages"])

    return {
        "agent_calls": agent_state["agent_calls"],
        "messages": messages
    }


def call_related_question_agent(state: State):
    agent_state = related_question_agent.invoke(state)
    messages = filter_newly_generated_messages(state["messages"], agent_state["messages"])

    return {
        "agent_calls": agent_state["agent_calls"],
        "messages": messages
    }


def agent_manager_node(state: State):
    agent_name = state["agent_calls"][0]
    agent_state = agent_dict[agent_name].invoke(state)
    messages = filter_newly_generated_messages(state["messages"], agent_state["messages"])

    return {
        "agent_calls": state["agent_calls"][1:],
        "messages": messages
    }


workflow = StateGraph(state_schema=State)

workflow.add_node("service_agent", call_service_agent)
workflow.add_node("related_question_agent", call_related_question_agent)
workflow.add_node("agent_manager", agent_manager_node)

workflow.add_edge(START, "service_agent")
workflow.add_conditional_edges(
    "service_agent",
    lambda state: "agent_manager" if len(state["agent_calls"]) > 0 else END,
    ["agent_manager", END],
)
workflow.add_conditional_edges(
    "agent_manager",
    lambda state: "agent_manager" if len(state["agent_calls"]) > 0 else "related_question_agent",
    ["agent_manager", "related_question_agent"],
)
workflow.add_edge("related_question_agent", END)

checkpointer = MongoDBSaver(
    MongoClient(os.getenv("SESSION_MONGO_CONN_STR")),
    db_name="daytrip_chatbot",
    checkpoint_collection_name="checkpoints",
    writes_collection_name="checkpoint_writes",
)
chatbot = workflow.compile(checkpointer=checkpointer)
