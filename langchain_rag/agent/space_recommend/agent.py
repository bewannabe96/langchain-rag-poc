from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode

from langchain_rag.agent.space_recommend.node.feedback import feedback_node
from langchain_rag.agent.space_recommend.node.search import search_node, tools as search_tools
from langchain_rag.agent.space_recommend.node.selection import selection_node
from langchain_rag.agent.space_recommend.state import State


def search_tool_router(state: State):
    message = state["messages"][-1]
    if isinstance(message, AIMessage) and len(message.tool_calls) > 0:
        return "search_tool"
    return END


builder = StateGraph(state_schema=State)

builder.add_node("search", search_node)
builder.add_node("search_tool", ToolNode(tools=search_tools))
builder.add_node("selection", selection_node)
builder.add_node("feedback", feedback_node)

builder.add_edge(START, "search")
builder.add_conditional_edges("search", search_tool_router, ["search_tool", END])
builder.add_edge("search_tool", "selection")
builder.add_edge("selection", "feedback")
builder.add_edge("feedback", END)

agent = builder.compile()


def hand_off_to_agent(args: dict) -> list[BaseMessage]:
    state = agent.invoke(
        State(
            language=args["language"],
            messages=[HumanMessage(content=args["query"])],
            exclude_space_ids=','.join(args["exclude_space_ids"]),
        )
    )

    return [AIMessage(id=message.id, content=message.content)
            for message in state["messages"]
            if isinstance(message, AIMessage) and message.content != ""]
