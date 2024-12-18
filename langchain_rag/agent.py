from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, END, StateGraph
from langgraph.prebuilt import ToolNode

from langchain_rag.node.general_llm import GeneralLLM
from langchain_rag.state import State
from langchain_rag.subgraph.space_search_subgraph import space_search_subgraph
from langchain_rag.tool import tools


def router(state: State):
    message = state["messages"][-1]
    if not isinstance(message, AIMessage):
        return END

    if len(message.tool_calls) == 1:
        tool_name = message.tool_calls[0]["name"]
        if tool_name == "SpaceSearch":
            return "space_search"
        else:
            return "tool"
    else:
        return END


def call_space_search(state: State):
    last_message_id = state["messages"][-1].id
    new_state = space_search_subgraph.invoke(state)

    last_message_index = len(new_state["messages"]) - 1
    while new_state["messages"][last_message_index].id != last_message_id:
        last_message_index -= 1

    return {"messages": new_state["messages"][last_message_index:]}


workflow = StateGraph(state_schema=State)

workflow.add_node("general_llm", GeneralLLM(tools=tools))
workflow.add_node("tool", ToolNode(tools=tools))
workflow.add_node("space_search", call_space_search)

workflow.add_edge(START, "general_llm")
workflow.add_conditional_edges("general_llm", router, ["tool", "space_search", END])

workflow.add_edge("tool", "general_llm")
workflow.add_edge("space_search", END)

checkpointer = MemorySaver()
agent = workflow.compile(checkpointer=checkpointer)
