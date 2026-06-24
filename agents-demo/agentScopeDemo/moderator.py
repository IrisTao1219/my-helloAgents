from typing import List

from agentscope.agent import AgentBase
from agentscope.message import Msg

def format_player_list_str(players: List[str]) -> str:
    """格式化玩家姓名列表"""
    if not players:
        return "无人"
    return "、".join(players)

class GameModerator(AgentBase):
    def __init__(self) -> None:
        super().__init__()
        self.name = "游戏主持人"
        self.game_log: List[str] = []

    async def announce(self, content: str) -> Msg:
        content=f"📢 {content}"
        msg = Msg(
            name=self.name,
            content=content,
            role="system"
        )
        self.game_log.append(content)
        await self.print(msg)
        return msg
    
    async def night_announcement(self, round_num: int) -> Msg:
        """夜晚阶段公告"""
        content = f"🌙 第{round_num}夜降临，天黑请闭眼..."
        return await self.announce(content)
    
    async def day_announcement(self, round_num: int) -> Msg:
        """白天阶段公告"""
        content = f"☀️ 第{round_num}天天亮了，请大家睁眼..."
        return await self.announce(content)
       
    async def death_announcement(self, dead_players: List[str]) -> Msg:
        """死亡公告"""
        if not dead_players:
            content = "昨夜平安无事，无人死亡。"
        else:
            content = f"昨夜，{format_player_list_str(dead_players)}不幸遇害。"
        return await self.announce(content)
    
    async def vote_result_announcement(self, voted_out: str, vote_count: int) -> Msg:
        """投票结果公告"""
        content = f"投票结果：{voted_out}以{vote_count}票被淘汰出局。"
        return await self.announce(content)
    
    async def game_over_announcement(self, winner: str) -> Msg:
        """游戏结束公告"""
        content = f"🎉 游戏结束！{winner}"
        return await self.announce(content)