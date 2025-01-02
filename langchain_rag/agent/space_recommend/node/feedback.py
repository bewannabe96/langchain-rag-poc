from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

from langchain_rag.prompt.load_prompt import load_agent_prompt
from ..state import State

feedback_model = ChatOpenAI(model="gpt-4o")

feedback_prompt_template = ChatPromptTemplate.from_messages([
    load_agent_prompt("agent/space_recommend/feedback"),
    MessagesPlaceholder(variable_name="messages"),
])


def feedback_node(state: State):
    prompt = feedback_prompt_template.invoke(state)
    message = feedback_model.invoke(prompt)
    return {"messages": [message]}
