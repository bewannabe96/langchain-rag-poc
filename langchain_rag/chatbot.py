import os
from typing import Sequence

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.checkpoint.mongodb import MongoDBSaver
from langgraph.graph import START, END, StateGraph
from pymongo import MongoClient

from langchain_rag.agent.related_question_agent import related_question_agent
from langchain_rag.agent.service.agent import agent as service_agent
from langchain_rag.agent.space_question.agent import hand_off_to_agent as hand_off_to_space_question_agent
from langchain_rag.agent.space_recommend.agent import hand_off_to_agent as hand_off_to_space_recommend_agent
from langchain_rag.mongo_db_store import MongoDBStore
from langchain_rag.state import State


def filter_newly_generated_messages(updated_messages: Sequence[BaseMessage],
                                    original_messages: Sequence[BaseMessage] = None) -> Sequence[BaseMessage]:
    last_message_id = original_messages[-1].id if original_messages else None

    filtered: list[BaseMessage] = []
    for index in range(len(updated_messages) - 1, -1, -1):
        message = updated_messages[index]

        if last_message_id is not None and message.id == last_message_id:
            break

        if isinstance(message, HumanMessage):
            filtered.append(message)
        elif isinstance(message, AIMessage):
            if message.content != "":
                filtered.append(AIMessage(id=message.id, content=message.content))

    return filtered[::-1]


def default_state_node(state: State):
    return {
        "area": state["area"] if "area" in state else None,
        "agent_call": state["agent_call"] if "agent_call" in state else None,
    }


def call_service_agent(state: State):
    agent_state = service_agent.invoke(state)
    messages = filter_newly_generated_messages(agent_state["messages"], original_messages=state["messages"])

    return {
        "agent_call": agent_state["agent_call"] if "agent_call" in agent_state else None,
        "messages": messages
    }


def call_related_question_agent(state: State):
    agent_state = related_question_agent.invoke(state)
    messages = filter_newly_generated_messages(agent_state["messages"], original_messages=state["messages"])

    return {"messages": messages}


def agent_manager_node(state: State):
    agent_call = state["agent_call"]
    agent_name = agent_call["name"]
    agent_args = agent_call["args"]

    messages = []

    if agent_name == "SpaceRecommend":
        messages = hand_off_to_space_recommend_agent({**agent_args, "language": state.get("language")})
    elif agent_name == "SpaceQuestion":
        messages = hand_off_to_space_question_agent({**agent_args, "language": state.get("language")})

    messages = filter_newly_generated_messages(messages)
    return {"agent_call": None, "messages": messages}


workflow = StateGraph(state_schema=State)

workflow.add_node("default_state", default_state_node)
workflow.add_node("service_agent", call_service_agent)
workflow.add_node("related_question_agent", call_related_question_agent)
workflow.add_node("agent_manager", agent_manager_node)

workflow.add_edge(START, "default_state")
workflow.add_edge("default_state", "service_agent")
workflow.add_conditional_edges(
    "service_agent",
    lambda state: "agent_manager" if state["agent_call"] is not None else END,
    ["agent_manager", END],
)
workflow.add_edge("agent_manager", "related_question_agent")
workflow.add_edge("related_question_agent", END)

checkpointer = MongoDBSaver(
    MongoClient(os.getenv("SESSION_MONGO_CONN_STR")),
    db_name="daytrip_chatbot",
    checkpoint_collection_name="checkpoints",
    writes_collection_name="checkpoint_writes",
)
store = MongoDBStore(
    MongoClient(os.getenv("SESSION_MONGO_CONN_STR")),
    db_name="daytrip_chatbot",
    collection_name="memory",
)
chatbot = workflow.compile(checkpointer=checkpointer, store=store)
