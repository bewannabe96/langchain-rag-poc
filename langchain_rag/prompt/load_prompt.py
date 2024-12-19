from langchain_core.prompts import SystemMessagePromptTemplate


def load_system_prompt(path: str):
    prompt_text = ""

    with open(f"langchain_rag/prompt/script/common.md", "r", encoding="utf-8") as file:
        prompt_text += file.read()
        prompt_text += "\n---\n\n"

    with open(f"langchain_rag/prompt/script/{path}.md", "r", encoding="utf-8") as file:
        prompt_text += file.read()

    return SystemMessagePromptTemplate.from_template(prompt_text)
