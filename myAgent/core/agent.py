from typing import Dict, List, Optional

from .llm import MyLLM
from .message import Message


class Agent:
    def __init__(self, name: str, llm: MyLLM, system_prompt: Optional[str]=None, config: Optional[Dict[str, str]]=None):
        self.name = name
        self.llm = llm
        self.system_prompt = system_prompt
        self.config = config

        self._history: List[Message] = []

    def run(self, input_text: str, **kwargs):
        """运行智能体"""
        pass

    def add_message(self, message: Message):
        self._history.append(message)

    def clear_history(self):
        self._history.clear()

    def get_history(self) -> List[Message]:
        return self._history.copy()

    def __str__(self) -> str:
        return f"Agent(name={self.name}, provider={self.llm.provider})"
