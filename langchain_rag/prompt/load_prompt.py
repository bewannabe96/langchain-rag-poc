from langchain_core.prompts import SystemMessagePromptTemplate


def load_agent_prompt(path: str):
    prompt_text = ""

    with open(f"langchain_rag/prompt/script/common.md", "r", encoding="utf-8") as file:
        prompt_text += file.read()
        prompt_text += "\n---\n\n"

    with open(path, "r", encoding="utf-8") as file:
        prompt_text += file.read()

    return SystemMessagePromptTemplate.from_template(prompt_text, template_format="jinja2")
