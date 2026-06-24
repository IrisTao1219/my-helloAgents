from typing import Dict, List, Optional
from agentscope.agent import ReActAgent
from collections import Counter



def format_player_list(players: List[ReActAgent], show_roles: bool = False) -> str:
    """格式化玩家列表为中文显示"""
    if not players:
        return "无玩家"

    if show_roles:
        return "、".join([f"{p.name}({getattr(p, 'role', '未知')})" for p in players])
    else:
        return "、".join([p.name for p in players])


def majority_vote_cn(votes: Dict[str, str]) -> tuple[str, int]:
    """中文版多数投票统计"""
    if not votes:
        return "无人", 0

    vote_counts = Counter(votes.values())
    most_voted = vote_counts.most_common(1)[0]

    return most_voted[0], most_voted[1]

def check_winning_cn(alive_players: List[ReActAgent], roles: Dict[str, str]) -> Optional[str]:
    """检查中文版游戏胜利条件"""
    alive_roles = [roles.get(p.name, "村民") for p in alive_players]
    werewolf_count = alive_roles.count("狼人")
    villager_count = len(alive_roles) - werewolf_count
    
    if werewolf_count == 0:
        return "好人阵营胜利！所有狼人已被淘汰！"
    elif werewolf_count >= villager_count:
        return "狼人阵营胜利！狼人数量已达到或超过好人！"
    
    return None


class GameRoles:
    ROLES = {
        "狼人": {
            "role": "狼人",
            "ability": "夜晚可以击杀一名玩家",
            "win_condition": "消灭所有好人或与好人数量相等",
            "team": "狼人阵营",
        },
        "预言家": {
            "role": "预言家",
            "ability": "每晚可以查验一名玩家的身份",
            "win_condition": "消灭所有狼人",
            "team": "好人阵营",
        },
        "女巫": {
            "role": "女巫",
            "ability": "拥有解药和毒药各一瓶，可以救人或杀人",
            "win_condition": "消灭所有狼人",
            "team": "好人阵营",
        },
        "猎人": {
            "role": "猎人",
            "ability": "被投票出局时可以开枪带走一名玩家",
            "win_condition": "消灭所有狼人",
            "team": "好人阵营",
        },
        "村民": {
            "role": "村民",
            "ability": "无特殊技能，依靠推理和投票",
            "win_condition": "消灭所有狼人",
            "team": "好人阵营",
        },
        "守护者": {
            "role": "守护者",
            "ability": "每晚可以守护一名玩家免受狼人攻击",
            "win_condition": "消灭所有狼人",
            "team": "好人阵营",
        },
    }

    @classmethod
    def get_role(cls, role: str) -> str:
        return cls.ROLES.get(role, {}).get("role", "none")

    @classmethod
    def get_role_ability(cls, role: str) -> str:
        return cls.ROLES.get(role, {}).get("ability", "无特殊技能")

    @classmethod
    def get_standard_setup(cls, player_count: int) -> List[str]:
        """获取标准角色配置"""
        if player_count == 6:
            return ["狼人", "狼人", "预言家", "女巫", "村民", "村民"]
        elif player_count == 8:
            return ["狼人", "狼人", "狼人", "预言家", "女巫", "猎人", "村民", "村民"]
        elif player_count == 9:
            return [
                "狼人",
                "狼人",
                "狼人",
                "预言家",
                "女巫",
                "猎人",
                "守护者",
                "村民",
                "村民",
            ]
        else:
            # 默认配置：约1/3狼人
            werewolf_count = max(1, player_count // 3)
            roles = ["狼人"] * werewolf_count

            # 添加神职
            remaining = player_count - werewolf_count
            if remaining >= 1:
                roles.append("预言家")
                remaining -= 1
            if remaining >= 1:
                roles.append("女巫")
                remaining -= 1
            if remaining >= 1:
                roles.append("猎人")
                remaining -= 1

            # 剩余为村民
            roles.extend(["村民"] * remaining)

            return roles

