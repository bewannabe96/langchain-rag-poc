from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

from langchain_rag.prompt.load_prompt import load_system_prompt
from langchain_rag.state import State


class GeneralLLM:
    def __init__(self, tools: list) -> None:
        self.model = ChatOpenAI(model="gpt-4o", temperature=0).bind_tools(tools)
        self.prompt_template = ChatPromptTemplate.from_messages([
            load_system_prompt("general"),
            MessagesPlaceholder(variable_name="messages"),
        ])

    def __call__(self, state: State):
        prompt = self.prompt_template.invoke(state)
        message = self.model.invoke(prompt)
        return {"messages": [message]}
