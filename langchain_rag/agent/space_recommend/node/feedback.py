from typing import Any

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

from langchain_rag.prompt.load_prompt import load_agent_prompt
from ..state import State

feedback_model = ChatOpenAI(model="gpt-4o")


class FilteredMessagesPlaceholder(MessagesPlaceholder):
    def format_messages(self, **kwargs: Any) -> list[BaseMessage]:
        messages = kwargs.get(self.variable_name, [])

        filtered = []
        for message in messages:
            if isinstance(message, HumanMessage):
                filtered.append(message)
            elif isinstance(message, AIMessage):
                if message.content != "":
                    filtered.append(AIMessage(content=message.content))
        return filtered


feedback_prompt_template = ChatPromptTemplate.from_messages([
    load_agent_prompt("langchain_rag/agent/space_recommend/prompt/feedback.md"),
    FilteredMessagesPlaceholder(variable_name="messages"),
])


def feedback_node(state: State):
    prompt = feedback_prompt_template.invoke(state)
    message = feedback_model.invoke(prompt)
    return {"messages": [message]}
