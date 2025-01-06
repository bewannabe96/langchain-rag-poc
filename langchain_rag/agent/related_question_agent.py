from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from pydantic import BaseModel

from langchain_rag.filtered_message_placeholder import FilteredMessagesPlaceholder
from langchain_rag.message.related_question_suggest_message import RelatedQuestionSuggestMessage
from langchain_rag.prompt.load_prompt import load_agent_prompt
from langchain_rag.state import State


class SuggestOutput(BaseModel):
    suggestions: list[str]


suggest_prompt_template = ChatPromptTemplate.from_messages([
    load_agent_prompt("langchain_rag/prompt/script/agent/related_question/suggest.md"),
    FilteredMessagesPlaceholder(variable_name="messages"),
])

suggest_model = ChatOpenAI(model="gpt-4o").with_structured_output(SuggestOutput)


def suggest_node(state: State):
    prompt = suggest_prompt_template.invoke(state)
    output: SuggestOutput = suggest_model.invoke(prompt)
    return {"messages": [RelatedQuestionSuggestMessage(content=output.model_dump_json())]}


builder = StateGraph(state_schema=State)

builder.add_node("suggest", suggest_node)

builder.add_edge(START, "suggest")
builder.add_edge("suggest", END)

related_question_agent = builder.compile()
