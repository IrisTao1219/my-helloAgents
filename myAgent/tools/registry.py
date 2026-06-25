from typing import Any, Callable, Dict, Optional

from myAgent.tools.base import Tool, ToolResponse


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._functions: Dict[str, Dict[str, Any]] = {}

    def register_tool(self, tool: Tool):
        if tool.name in self._tools:
            print(f"⚠️ 警告：工具 '{tool.name}' 已存在，将被覆盖。")
        
        self._tools[tool.name] = tool
        print(f"✅ 工具 '{tool.name}' 已注册。")

    def register_function(self, func: Callable, name: Optional[str] = None, description: Optional[str] = None):
        if name is None:
            name = func.__name__

        if description is None:
            import inspect
            doc = inspect.getdoc(func)
            if doc:
                description = doc.strip()
            else:
                description = f"执行函数 {name}"

        if name  in self._functions:
            print(f"⚠️ 警告：函数 '{name}' 已存在，将被覆盖。")
        else:
            self._functions[name] = {
                "description": description,
                "func": func,
            }
        
        print(f"✅ 函数 '{name}' 已注册。")


    def list_tools(self) -> list[str]:
        """列出所有工具名称"""
        return list(self._tools.keys()) + list(self._functions.keys())

    def clear(self):
        """清空所有工具"""
        self._tools.clear()
        self._functions.clear()
        print("🧹 所有工具已清空。")

    def get_tool(self, tool_name: str) -> Tool | None:
        return self._tools.get(tool_name)

    def get_function(self, name: str) -> Optional[Callable]:
        """获取工具函数"""
        func_info = self._functions.get(name)
        return func_info["func"] if func_info else None

    def get_tool_description(self) -> str:
        descriptions = []
        for tool in self._tools.values():
            descriptions.append(f"- {tool.name}: {tool.description}")
        
                # 函数工具描述
        for name, info in self._functions.items():
            descriptions.append(f"- 函数 {name}: {info['description']}")

        return "\n".join(descriptions) if descriptions else "暂无可用工具"

    async def execute_tool(self, tool_name: str, input_text: Any) -> ToolResponse:
        if tool_name in self._tools:
            tool = self._tools[tool_name]
        
            try:
                import json
                if isinstance(input_text, str):
                    try:
                        parameters = json.loads(input_text)
                        if not isinstance(parameters, dict):
                            parameters = {"input": parameters}  
                    except json.JSONDecodeError:
                        parameters = {"input": str(input_text)}
                elif isinstance(input_text, dict):
                    parameters = input_text
                else:
                    parameters = {"input": str(input_text)}

                response = await tool.async_run(parameters)

            except Exception as e:
                raise ValueError(f"⚠️ 警告：工具 '{tool_name}' 输入参数格式错误: {str(e)}")

        elif tool_name in self._functions:
            func = self.get_function(tool_name)

            print(f"执行函数 {func}，输入参数: {input_text}")
            
            if not func:
                raise ValueError(f"⚠️ 警告：函数 '{tool_name}' 不存在")
            
            try:
                response = func(input_text)
            except Exception as e:
                raise ValueError(f"⚠️ 警告：函数 '{tool_name}' 执行错误: {str(e)}")
        
        else:
            raise ValueError(f"⚠️ 警告：工具或函数 '{tool_name}' 不存在")

        return response

# 全局工具注册表
global_registry = ToolRegistry()
