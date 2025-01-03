from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

from langchain_rag.prompt.load_prompt import load_agent_prompt_v2
from ..state import State
from ..tool.space_retrieve_tool import SpaceRetrieveTool

space_retrieve_tool = SpaceRetrieveTool()

model = ChatOpenAI(model="gpt-4o", temperature=0).bind_tools(tools=[
    space_retrieve_tool
])

chat_prompt_template = ChatPromptTemplate.from_messages([
    load_agent_prompt_v2("langchain_rag/agent/space_question/prompt/retrieve.md"),
    MessagesPlaceholder(variable_name="messages"),
])


def retrieve_node(state: State):
    out_messages = []

    prompt = chat_prompt_template.invoke(state)

    message: AIMessage = model.invoke(prompt)
    out_messages.append(message)

    if len(message.tool_calls) > 0:
        for tool_call in message.tool_calls:
            if tool_call["name"] == "SpaceRetrieve":
                tool_message = space_retrieve_tool.invoke(tool_call)
                out_messages.append(tool_message)

    return {"messages": out_messages}
