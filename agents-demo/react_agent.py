import json
import re
from api_llm import MyOpenAIClient
from tool import ToolExecutor
from utils import load_prompt, re_group


class ReActAgent:
    def __init__(
        self,
        llm_client: MyOpenAIClient,
        tool_executor: ToolExecutor,
        max_steps: int = 3,
    ):
        self.llm_client = llm_client
        self.tool_executor = tool_executor
        self.history = []
        self.max_steps = max_steps

    def run(self, question: str):
        self.history = []
        current_step = 0

        while current_step < self.max_steps:
            current_step += 1
            print(f"\n--- Step {current_step} ---")

            tools_desc = self.tool_executor.getAvailableTools()
            history_str = "\n".join(self.history)
            REACT_PROMPT_TEMPLATE = load_prompt("prompts/react_prompt_template.md")
            prompt = REACT_PROMPT_TEMPLATE.format(
                question=question, tools=tools_desc, history=history_str
            )

            messages = [{"role": "user", "content": prompt}]
            response_text = self.llm_client.think(messages)  # pyright: ignore[reportArgumentType]

            if not response_text:
                print("⚠️错误 LLM没有返回任何内容，结束对话。")
                break

            thought, action = self._parse_output(response_text)

            if thought:
                print(f"🤔 思考: {thought}")

            if not action:
                print("⚠️ 错误: LLM的输出中未找到 Action 字段，流程终止。")
                break

            if action.startswith("Finish"):
                final_answer = re_group(r"Finish\[(.*)\]", action)
                print(f"\n🎉 任务完成，最终答案: {final_answer}\n")
                return final_answer

            tool_name, args = self._parse_action(action)
            if not tool_name or not args:
                continue

            print(f"🎬 行动: {tool_name} with args {args}")

            tool_function = self.tool_executor.getTool(tool_name)

            if not tool_function:
                observation = f"⚠️ 错误: 未找到工具 '{tool_name}'，请检查工具名称是否正确，并确保它已在 available_tools 中注册。"
            else:
                observation = tool_function(args)
            print(f"🔍 观察: {observation}")

            self.history.append(f"Action: {action}\nObservation: {observation}")

        print("达到最大步骤数，结束对话。")
        return None

    def _parse_output(self, text: str):
        """从LLM的输出中提取 Thought 和 Action"""
        thought_match = re.search(r"Thought:\s*(.*?)(?=\nAction:|$)", text, re.DOTALL)
        action_match = re.search(r"Action:\s*(.*?)$", text, re.DOTALL)

        thought = thought_match.group(1).strip() if thought_match else None
        action = action_match.group(1).strip() if action_match else None
        return thought, action

    def _parse_action(self, action_text: str):
        """解析Action字符串，提取工具名称和输入。
        """
        match = re.match(r"(\w+)\[(.*)\]", action_text, re.DOTALL)
        if match:
            return match.group(1), match.group(2)
        return None, None