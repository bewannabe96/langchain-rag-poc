from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel

from langchain_rag.prompt.load_prompt import load_system_prompt
from langchain_rag.state import State
from langchain_rag.tool import tools


class Recommendation(BaseModel):
    content_id: str
    content_type: str
    reason: str


class RecommendationOutput(BaseModel):
    results: list[Recommendation]


model = ChatOpenAI(model="gpt-4o", temperature=0)
structured_model = ChatOpenAI(model="gpt-4o", temperature=0, model_kwargs={"response_format": {"type": "json_object"}})\
    .with_structured_output(RecommendationOutput)

recommendation_generation_prompt_template = ChatPromptTemplate.from_messages([
    load_system_prompt("recommendation-generation"),
    MessagesPlaceholder(variable_name="messages"),
])

recommendation_feedback_prompt_template = ChatPromptTemplate.from_messages([
    load_system_prompt("recommendation-feedback"),
    MessagesPlaceholder(variable_name="messages"),
])


def generate_recommendation(state: State):
    input_messages = recommendation_generation_prompt_template.invoke(state)
    recommendation_output: RecommendationOutput = structured_model.invoke(input_messages)
    return {"messages": [AIMessage(content=recommendation_output.model_dump_json())]}


def ask_recommendation_feedback(state: State):
    input_messages = recommendation_feedback_prompt_template.invoke(state)
    ai_message = model.invoke(input_messages)
    return {"messages": [ai_message]}


builder = StateGraph(state_schema=State)

builder.add_node("tool_use", ToolNode(tools=tools))
builder.add_node("generate_recommendation", generate_recommendation)
builder.add_node("ask_recommendation_feedback", ask_recommendation_feedback)

builder.add_edge(START, "tool_use")
builder.add_edge("tool_use", "generate_recommendation")
builder.add_edge("generate_recommendation", "ask_recommendation_feedback")
builder.add_edge("ask_recommendation_feedback", END)

space_search_subgraph = builder.compile()
