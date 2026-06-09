from typing import Any, Callable
from dotenv import load_dotenv
import requests
import os
from tavily import TavilyClient
from serpapi import Client as SerpApiClient

# 加载环境变量
load_dotenv()


def get_weather(city: str) -> str:
    """获取指定城市的天气信息"""
    # 这里使用一个免费的天气API示例，你可以替换为任何你喜欢的API
    url = f"http://wttr.in/{city}?format=j1"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()

            current_condition = data["current_condition"][0]
            weather_desc = current_condition["weatherDesc"][0]["value"]
            temp_c = current_condition["temp_C"]
            return f"天气: {weather_desc}, 温度: {temp_c}°C"
        else:
            return f"无法获取天气信息，状态码: {response.status_code}"
    except requests.exceptions.RequestException as e:
        # 处理网络错误
        return f"⚠️ 错误:查询天气时遇到网络问题 - {e}"
    except Exception as e:
        return f"⚠️ 获取天气信息时发生错误: {str(e)}"


def get_attraction(city: str, weather: str) -> str:
    """根据城市和天气推荐一个旅游景点"""
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return "⚠️ 错误: 未找到Tavily API密钥，请设置环境变量TAVILY_API_KEY"

    tavily = TavilyClient(api_key=api_key)

    query = f"'{city}'的天气是'{weather}'，请推荐一个适合这个天气的旅游景点，并简要说明理由。"

    try:
        response = tavily.search(query, include_answer=True)

        if response.get("answer"):
            return response["answer"]

        formatted_results = []
        for result in response.get("results", []):
            title = result.get("title", "无标题")
            formatted_results.append(f"- {title}: {result['content']}")

        if not formatted_results:
            return "没有找到相关的旅游景点推荐。"

        return "根据查询，以下是为您找到的一些信息：\n" + "\n".join(formatted_results)
    except Exception as e:
        return f"⚠️ 调用Tavily API时发生错误: {str(e)}"


def serp_search(query: str) -> str:
    """一个通用的搜索工具，可以根据查询返回相关信息"""
    print(f"🔍 正在执行【SerpApi】网页搜索： {query}")
    try:
        api_key = os.getenv("SERPAPI_API_KEY")

        if not api_key:
            return "⚠️ 错误: 未找到serpapi密钥，请设置环境变量SERPAPI_API_KEY"

        params = {"engine": "google", "q": query, "gl": "cn", "hl": "zh-cn"}

        client = SerpApiClient(api_key=api_key)
        results = client.search(params)
        if "knowledge_graph" in results and "description" in results["knowledge_graph"]:
            return results["knowledge_graph"]["description"]
        if "organic_results" in results and results["organic_results"]:
            snippets = [
                f"[{i + 1}]{res.get('title', '')}\n{res.get('snippet', '')}"
                for i, res in enumerate(results["organic_results"][:3])
            ]
            return "\n\n".join(snippets)

        return f"没有找到 '{query}' 的相关信息。"

    except Exception as e:
        return f"⚠️ 搜索时发生错误: {str(e)}"


available_tools = {
    "get_weather": get_weather,
    "get_attraction": get_attraction,
    "search": serp_search,
}


class ToolExecutor:
    """一个工具执行器，根据工具名称和参数调用对应的函数"""

    def __init__(self):
        self.tools: dict[str, dict[str, Any]] = {}

    def registerTool(self, name: str, description: str, func: Callable):
        """注册一个工具"""
        if name in self.tools:
            print(f"⚠️ 工具 '{name}' 已经注册，正在覆盖旧的定义。")
        self.tools[name] = {"description": description, "func": func}
        print(f"✅ 工具 '{name}' 注册成功。")

    def getTool(self, name: str) -> Callable:
        """根据工具名称获取对应的函数"""
        if name not in self.tools:
            raise ValueError(f"⚠️ 错误：工具 '{name}' 未注册。")
        return self.tools[name]["func"]

    def getAvailableTools(self) -> str:
        """返回所有可用工具的名称和描述"""
        return "\n".join(
            [f"{name}: {info['description']}" for name, info in self.tools.items()]
        )


if __name__ == "__main__":
    toolExecutor = ToolExecutor()
    toolExecutor.registerTool("get_weather", "获取指定城市的天气信息", get_weather)
    toolExecutor.registerTool(
        "get_attraction", "根据城市和天气推荐一个旅游景点", get_attraction
    )
    toolExecutor.registerTool(
        "search", "一个通用的搜索工具，可以根据查询返回相关信息", serp_search
    )

    print("\n --- 当前可用工具 ---")
    print(toolExecutor.getAvailableTools())

    print("\n--- 执行 Action: search['英伟达最新的GPU型号是什么'] ---")
    tool_name = "serp_search"
    tool_input = "英伟达最新的GPU型号是什么"

    tool_function = toolExecutor.getTool(tool_name)
    if tool_function:
        result = tool_function(tool_input)
        print("\n--- 工具执行结果 ---")
        print(result)
