from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

from langchain_rag.prompt.load_prompt import load_agent_prompt_v2
from ..state import State

model = ChatOpenAI(model="gpt-4o", temperature=0)

chat_prompt_template = ChatPromptTemplate.from_messages([
    load_agent_prompt_v2("langchain_rag/agent/space_question/prompt/answer.md"),
    MessagesPlaceholder(variable_name="messages"),
])


def answer_node(state: State):
    prompt = chat_prompt_template.invoke(state)
    message: AIMessage = model.invoke(prompt)
    return {"messages": [message]}
