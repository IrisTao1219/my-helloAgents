import re
from typing import Dict, Iterator, List, Optional

from myAgent.core import Agent, Message, MyLLM
from myAgent.tools.registry import ToolRegistry


class SimpleAgent(Agent):
    def __init__(
        self,
        name: str,
        llm: MyLLM,
        system_prompt: Optional[str] = None,
        config: Optional[Dict[str, str]] = None,
        tool_registry: Optional["ToolRegistry"] = None,
        enable_tool_calling: bool = True
    ):
        super().__init__(name, llm, system_prompt, config)
        self.tool_registry = tool_registry
        self.enable_tool_calling = enable_tool_calling and tool_registry is not None

    def run(self, input_text: str, max_tool_iteration: int = 3, **kwargs) -> str:
        """运行智能体"""
        print(f"🤖 {self.name} 正在处理: {input_text}")

        messages = []

        enhanced_system_prompt = self._get_enhanced_system_prompt()
        messages.append(Message(enhanced_system_prompt, "system"))
        for msg in self._history:
            messages.append(Message(msg.content, msg.role))

        messages.append(Message(input_text, "user"))

        if not self.enable_tool_calling:
            response = self.llm.invoke(messages, **kwargs).content
            self.add_message(Message(input_text, "user"))
            self.add_message(Message(response, "assistant"))
            print(f"✅ {self.name} 响应完成")
            return response

        else:
            return self._run_with_tools(messages, input_text, max_tool_iteration, **kwargs)

    def _get_enhanced_system_prompt(self)->str:
        base_prompt = self.system_prompt or "你是一个有用的AI助手。"

        if not self.enable_tool_calling or not self.tool_registry:
            return base_prompt

        tools_section = "\n\n## 可用工具\n"
        tools_section += "你可以使用以下工具来帮助回答：\n"

        tools_description = self.tool_registry.get_tool_description()
        tools_section += tools_description +"\n"

        tools_section += "\n## 工具调用格式\n"
        tools_section += "当需要使用工具时，请使用以下格式：\n"
        tools_section += "`[TOOL_CALL:{tool_name}:{parameters}]`\n"
        tools_section += "例如：`[TOOL_CALL:search:Python编程]` 或 `[TOOL_CALL:memory:recall=用户信息]`\n\n"
        tools_section += "工具调用结果会自动插入到对话中，然后你可以基于结果继续回答。\n"

        return base_prompt + tools_section

        

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

    def _run_with_tools(self, messages: list, input_text: str, max_tool_iterations: int, **kwargs) -> str:
        """运行包含工具的流式处理"""
        current_iteration = 0
        final_response = ""

        while current_iteration < max_tool_iterations:

            response = self.llm.invoke(messages, **kwargs).content
            
            tool_calls = self._parse_tool_calls(response)

            if tool_calls:
                print(f"检测到 {len(tool_calls)} 个工具调用")
                tool_results = []
                clean_response = response

                for call in tool_calls:
                    result = self._execute_tool_call(call['tool_name'], call['parameters'])
                    tool_results.append(result)
                    clean_response = clean_response.replace(call['original'], "")

                messages.append(Message(clean_response, "assistant"))

                tool_results_text = "\n\n".join(tool_results)
                messages.append(Message(f"🔧 工具调用结果：\n{tool_results_text}\n\n请基于这些结果给出完整的回答。", "user"))

                current_iteration += 1
                continue

            # 没有工具调用，这是最终回答
            final_response = response
            break

        if current_iteration >= max_tool_iterations and not final_response:
            final_response = f"❌ 超过 {max_tool_iterations} 次工具调用，未找到有效结果。"

        return final_response

    def _parse_tool_calls(self, text: str) ->list:
        pattern = r'\[TOOL_CALL:([^:]+):([^\]]+)\]'
        matches = re.findall(pattern, text)
        
        tool_calls = []
        for tool_name, parameters in matches:
            tool_calls.append({
                'tool_name': tool_name.strip(),
                'parameters': parameters.strip(),
                'original': f"[TOOL_CALL:{tool_name}:{parameters}]"
            })

        return tool_calls

    def _execute_tool_call(self, tool_name: str, parameters: str) -> str:
        """执行工具调用"""
        if not self.tool_registry:
            return "❌ 错误：未配置工具注册表"

        try:
            # 智能参数解析
            if tool_name == 'calculator':
                # 计算器工具直接传入表达式
                result = self.tool_registry.execute_tool(tool_name, parameters)
            else:
                # 其他工具使用智能参数解析
                param_dict = self._parse_tool_parameters(tool_name, parameters)
                tool = self.tool_registry.get_tool(tool_name)
                if not tool:
                    return f"❌ 错误：未找到工具 '{tool_name}'"
                result = tool.run(param_dict)

            return f"🔧 工具 {tool_name} 执行结果：\n{result}"

        except Exception as e:
            return f"❌ 工具调用失败：{str(e)}"

    def _parse_tool_parameters(self, tool_name: str, parameters: str) -> dict:
        """智能解析工具参数"""
        param_dict = {}

        if '=' in parameters:
            # 格式: key=value 或 action=search,query=Python
            if ',' in parameters:
                # 多个参数：action=search,query=Python,limit=3
                pairs = parameters.split(',')
                for pair in pairs:
                    if '=' in pair:
                        key, value = pair.split('=', 1)
                        param_dict[key.strip()] = value.strip()
            else:
                # 单个参数：key=value
                key, value = parameters.split('=', 1)
                param_dict[key.strip()] = value.strip()
        else:
            # 直接传入参数，根据工具类型智能推断
            if tool_name == 'search':
                param_dict = {'query': parameters}
            elif tool_name == 'memory':
                param_dict = {'action': 'search', 'query': parameters}
            else:
                param_dict = {'input': parameters}

        return param_dict