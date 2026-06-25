import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from myAgent.tools.response import ToolResponse


class ToolStatus(Enum):
    """工具执行状态枚举"""
    SUCCESS = "success"  # 任务完全按预期执行
    PARTIAL = "partial"  # 结果可用但存在折扣（截断、回退、部分失败）
    ERROR = "error"      # 无有效结果（致命错误）

@dataclass
class ToolParameter:
    name: str
    description: str
    type: str
    required: bool = False
    default: Optional[Any] = None

class Tool(ABC):
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def run(self, parameters: Dict[str, str]) -> ToolResponse:
        pass

    async def async_run(self, parameters: Dict[str, str]) -> ToolResponse:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self.run(parameters))

    @abstractmethod
    def get_parameters(self) -> List[ToolParameter]:
        pass

    def validate_parameters(self, parameters: Dict[str, str]) -> bool:
        required_params = [p.name for p in self.get_parameters() if p.required]
        return all(param in parameters for param in required_params)

    def to_openai_schema(self) -> Dict[str, Any]:
        parameters = self.get_parameters()

        properties = {}
        # required = []

        for param in parameters:
            prop = {
                "type": param.type,
                "description": param.description,
                "required": param.required,
            }

            if param.default is not None:
                prop["description"] = f"{param.description} (default: {param.default})"

            if param.type == "array":
                prop["items"] = {"type": "string"} # 默认字符串数组

            # if param.required:
            #     required.append(param.name)

            properties[param.name] = prop
            
            
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": properties,
            }
        }