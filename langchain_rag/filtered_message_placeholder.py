from typing import Any

from langchain_core.messages import BaseMessage
from langchain_core.prompts.chat import MessagesPlaceholder

from langchain_rag.message.related_question_suggest_message import RelatedQuestionSuggestMessage


class FilteredMessagesPlaceholder(MessagesPlaceholder):
    def format_messages(self, **kwargs: Any) -> list[BaseMessage]:
        messages = kwargs.get(self.variable_name, [])

        filtered = []
        for message in messages:
            if isinstance(message, RelatedQuestionSuggestMessage):
                continue

            filtered.append(message)

        kwargs[self.variable_name] = filtered
        return super().format_messages(**kwargs)
