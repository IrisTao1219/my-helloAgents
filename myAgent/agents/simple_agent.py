
from typing import Dict, Iterator, List, Optional

from myAgent.core import Agent, Message, MyLLM


class MyAgent(Agent):
    def __init__(self, name: str, llm: MyLLM, system_prompt: Optional[str] = None, config: Optional[Dict[str, str]] = None):
        super().__init__(name, llm, system_prompt, config)

    def stream_run(self, input_text: str, **kwargs) -> Iterator[str]:
        print(f"🌊 {self.name} 开始流式处理: {input_text}")

        messages = self._build_messages(input_text)

        llm_response = self.llm.stream_invoke(messages, **kwargs)

        full_response = ""
        for chunk in llm_response:
            full_response += chunk
            yield chunk

        self.add_message(Message(input_text, "user"))
        self.add_message(Message(full_response, "assistant"))
        print(f"✅ {self.name} 流式响应完成")



    def _build_messages(self, input_text: str) -> List[Dict[str, str]]:
        messages = []

        if self.system_prompt:
            messages.append(Message(self.system_prompt, "system"))

        for msg in self._history:
            messages.append(Message(msg.content, msg.role))

        messages.append(Message(input_text, "user"))
        return messages