import requests
import os
from tavily import TavilyClient

def get_weather(city: str) -> str:
    """获取指定城市的天气信息"""
    # 这里使用一个免费的天气API示例，你可以替换为任何你喜欢的API
    url = f"http://wttr.in/{city}?format=j1"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            
            current_condition = data['current_condition'][0]
            weather_desc = current_condition['weatherDesc'][0]['value']
            temp_c = current_condition['temp_C']
            return f"天气: {weather_desc}, 温度: {temp_c}°C"
        else:
            return f"无法获取天气信息，状态码: {response.status_code}"
    except requests.exceptions.RequestException as e:
        # 处理网络错误
        return f"错误:查询天气时遇到网络问题 - {e}"
    except Exception as e:
        return f"获取天气信息时发生错误: {str(e)}"

def get_attraction(city: str, weather: str) -> str:
    """根据城市和天气推荐一个旅游景点"""
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return "错误: 未找到Tavily API密钥，请设置环境变量TAVILY_API_KEY"
    
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
        return f"调用Tavily API时发生错误: {str(e)}"
    
available_tools = {
    "get_weather": get_weather,
    "get_attraction": get_attraction
}