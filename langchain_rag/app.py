from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, END, StateGraph

from langchain_rag.agent.service_agent import service_agent
from langchain_rag.state import State


def call_service(state: State):
    last_message_id = state["messages"][-1].id

    agent_state = service_agent.invoke(state)

    last_message_index = len(agent_state["messages"]) - 1
    while agent_state["messages"][last_message_index].id != last_message_id:
        last_message_index -= 1

    return {"messages": agent_state["messages"][last_message_index:]}


workflow = StateGraph(state_schema=State)

workflow.add_node("service", call_service)

workflow.add_edge(START, "service")
workflow.add_edge("service", END)

checkpointer = MemorySaver()
app = workflow.compile(checkpointer=checkpointer)
