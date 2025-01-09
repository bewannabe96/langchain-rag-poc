from typing import Optional, Any, TypedDict

from langgraph.graph import MessagesState


class AgentCall(TypedDict):
    name: str
    args: dict[str, Any]


class State(MessagesState):
    user_id: str
    language: str
    area: Optional[str]

    agent_call: Optional[AgentCall]
