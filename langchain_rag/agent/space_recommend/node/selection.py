from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from langchain_rag.prompt.load_prompt import load_agent_prompt
from ..message.space_recommendation_message import SpaceRecommendationMessage
from ..state import State


class Selection(BaseModel):
    space_id: str
    reason: str


class SelectionOutput(BaseModel):
    results: list[Selection]


selection_model = ChatOpenAI(
    model="gpt-4o", temperature=0
).with_structured_output(SelectionOutput)

selection_prompt_template = ChatPromptTemplate.from_messages([
    load_agent_prompt("langchain_rag/agent/space_recommend/prompt/selection.md"),
    MessagesPlaceholder(variable_name="messages"),
])


def selection_node(state: State):
    prompt = selection_prompt_template.invoke(state)
    output: SelectionOutput = selection_model.invoke(prompt)
    return {"messages": [SpaceRecommendationMessage(content=output.model_dump_json())]}
