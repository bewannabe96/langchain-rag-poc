from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

from langchain_rag.prompt.load_prompt import load_agent_prompt
from langchain_rag.agent.space_recommend.tool.space_search_tool import SpaceSearchTool
from ..state import State

tools = [
    SpaceSearchTool(),
]

model = ChatOpenAI(model="gpt-4o", temperature=0).bind_tools(tools)

chat_prompt_template = ChatPromptTemplate.from_messages([
    load_agent_prompt("langchain_rag/agent/space_recommend/prompt/search.md"),
    MessagesPlaceholder(variable_name="messages"),
])


def search_node(state: State):
    prompt = chat_prompt_template.invoke(state)
    message = model.invoke(prompt)
    return {"messages": [message]}
