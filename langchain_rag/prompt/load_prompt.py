from langchain_core.prompts import SystemMessagePromptTemplate


def load_system_prompt(node: str):
    prompt_text = ""

    with open(f"langchain_rag/prompt/role.md", "r", encoding="utf-8") as file:
        prompt_text += file.read()
        prompt_text += "\n---\n\n"

    with open(f"langchain_rag/prompt/terminology.md", "r", encoding="utf-8") as file:
        prompt_text += file.read()
        prompt_text += "\n---\n\n"

    with open(f"langchain_rag/prompt/basic-instructions.md", "r", encoding="utf-8") as file:
        prompt_text += file.read()
        prompt_text += "\n---\n\n"

    with open(f"langchain_rag/prompt/node/{node}.md", "r", encoding="utf-8") as file:
        prompt_text += file.read()

    return SystemMessagePromptTemplate.from_template(prompt_text)
