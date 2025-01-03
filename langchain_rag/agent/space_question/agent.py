from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langgraph.constants import START, END
from langgraph.graph import StateGraph

from langchain_rag.agent.space_question.node.answer import answer_node
from langchain_rag.agent.space_question.node.retrieve import retrieve_node
from langchain_rag.agent.space_question.state import State


def answer_router(state: State):
    message = state["messages"][-1]
    if isinstance(message, ToolMessage):
        return "answer"
    return END


builder = StateGraph(state_schema=State)

builder.add_node("retrieve", retrieve_node)
builder.add_node("answer", answer_node)

builder.add_edge(START, "retrieve")
builder.add_conditional_edges("retrieve", answer_router, ["answer", END])
builder.add_edge("answer", END)

agent = builder.compile()


def hand_off_to_agent(args: dict, language: str) -> list[BaseMessage]:
    state = agent.invoke(
        State(
            language=language,
            messages=[HumanMessage(content=args["question"])],
        )
    )

    return [AIMessage(id=message.id, content=message.content)
            for message in state["messages"]
            if isinstance(message, AIMessage) and message.content != ""]
