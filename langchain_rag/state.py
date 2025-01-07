from typing import Optional, Any

from langgraph.graph import MessagesState
from typing_extensions import TypedDict


class AgentCall(TypedDict):
    name: str
    args: dict[str, Any]


class State(MessagesState):
    language: str
    area: str

    agent_call: Optional[AgentCall]
