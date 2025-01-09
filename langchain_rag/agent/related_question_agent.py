from typing import Any

from langchain_core.messages import BaseMessage, trim_messages
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from pydantic import BaseModel

from langchain_rag.message.related_question_suggest_message import RelatedQuestionSuggestMessage
from langchain_rag.prompt.load_prompt import load_agent_prompt
from langchain_rag.state import State


class SuggestOutput(BaseModel):
    suggestions: list[str]


suggest_model = ChatOpenAI(model="gpt-4o").with_structured_output(SuggestOutput)


class FilteredMessagesPlaceholder(MessagesPlaceholder):
    def format_messages(self, **kwargs: Any) -> list[BaseMessage]:
        messages = kwargs.get(self.variable_name, [])
        return trim_messages(
            messages,
            strategy="last",
            token_counter=len,
            max_tokens=6,
            start_on="human",
            end_on="ai",
            include_system=False,
            allow_partial=False,
        )


suggest_prompt_template = ChatPromptTemplate.from_messages([
    load_agent_prompt("langchain_rag/prompt/script/agent/related_question/suggest.md"),
    FilteredMessagesPlaceholder(variable_name="messages"),
])


def suggest_node(state: State):
    prompt = suggest_prompt_template.invoke(state)
    output: SuggestOutput = suggest_model.invoke(prompt)
    return {"messages": [RelatedQuestionSuggestMessage(content=output.model_dump_json())]}


builder = StateGraph(state_schema=State)

builder.add_node("suggest", suggest_node)

builder.add_edge(START, "suggest")
builder.add_edge("suggest", END)

related_question_agent = builder.compile()
