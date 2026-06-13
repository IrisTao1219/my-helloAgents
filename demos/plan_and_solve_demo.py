from agents.plan_and_solve_agent import PlanAndSolveAgent
from api_llm import MyOpenAIClient

if __name__ == "__main__":
    llm_client = MyOpenAIClient()
    
    agent = PlanAndSolveAgent(llm_client)

    question = "一个水果店周一卖出了15个苹果。周二卖出的苹果数量是周一的两倍。周三卖出的数量比周二少了5个。请问这三天总共卖出了多少个苹果？"
    agent.run(question)