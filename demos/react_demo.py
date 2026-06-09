
from agents import ReActAgent
from api_llm import MyOpenAIClient
from tool import ToolExecutor, get_attraction, get_weather, serp_search

if __name__ == "__main__":
    llm_client = MyOpenAIClient()
    toolExecutor = ToolExecutor()
    
    toolExecutor.registerTool("search", "一个通用的搜索工具，可以根据查询返回相关信息", serp_search)
    
    print("\n --- 当前可用工具 ---")
    print(toolExecutor.getAvailableTools())
    
    agent = ReActAgent(llm_client, toolExecutor, max_steps=5)

    question = "请告诉我北京当前的天气，并推荐一个适合这个天气的旅游景点。"
    agent.run(question)