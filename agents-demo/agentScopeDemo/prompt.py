from typing import Optional

from pydantic import BaseModel, Field


def get_role_prompt(role: str):
    base_prompt = f"""你在这场狼人杀游戏中扮演{role}。

请严格按照以下JSON格式回复，不要添加任何其他文字：
{{
    "reach_agreement": true/false,
    "confidence_level": 1-10的数字,
    "key_evidence": "你的证据或观点"
}}

角色特点：
"""

    if role == "狼人":
        return (
            base_prompt
            + """
- 你是狼人阵营，目标是消灭所有好人
- 夜晚可以与其他狼人协商击杀目标
- 白天要隐藏身份，误导好人
"""
        )
    elif role == "预言家":
        return (
            base_prompt
            + """
- 你是好人阵营的预言家，目标是找出所有狼人
- 每晚可以查验一名玩家的真实身份
- 要合理公布查验结果，引导好人投票
"""
        )
    elif role == "女巫":
        return (
            base_prompt
            + """
- 你是好人阵营的女巫，拥有解药和毒药各一瓶
- 解药可以救活被狼人击杀的玩家
- 毒药可以毒杀一名玩家
- 要谨慎使用道具，在关键时刻发挥作用
"""
        )
    elif role == "猎人":
        return (
            base_prompt
            + """
- 你是好人阵营的猎人
- 被投票出局时可以开枪带走一名玩家
- 要在关键时刻使用技能，带走狼人
"""
        )
    else:  # 村民
        return (
            base_prompt
            + """
- 你是好人阵营的村民
- 没有特殊技能，只能通过推理和投票
- 要仔细观察，找出狼人的破绽
"""
        )
    

# 结构化模型
class DiscussionModel(BaseModel):
    reach_agreement: bool = Field(description="是否已达成一致意见")
    confidence_level: int = Field(description="对当前推理的信心程度(1-10)", ge=1, le=10)
    key_evidence: Optional[str] = Field(
        description="支持你观点的关键证据", default=None
    )


class WolfKillModel(BaseModel):
    target: str = Field(description="要击杀的玩家姓名")
    kill_strategy: str = Field(description="击杀策略说明")
    team_coordination: Optional[str] = Field(
        description="与狼队友的配合计划", default=None
    )


def get_seer_model_cn() -> type[BaseModel]:
    """获取中文版预言家模型"""

    class SeerModelCN(BaseModel):
        """中文版预言家查验格式"""

        target: str = Field(
            description="要查验的玩家姓名",
        )
        check_reason: str = Field(
            description="查验此人的原因",
        )
        priority_level: int = Field(description="查验优先级(1-10)", ge=1, le=10)

    return SeerModelCN


class WitchActionModelCN(BaseModel):
    """中文版女巫行动模型"""

    use_antidote: bool = Field(description="是否使用解药救人", default=False)
    use_poison: bool = Field(description="是否使用毒药杀人", default=False)
    target_name: Optional[str] = Field(
        description="目标玩家姓名（救人或毒杀的对象）", default=None
    )
    action_reason: Optional[str] = Field(description="行动理由", default=None)


def get_hunter_model_cn() -> type[BaseModel]:
    """获取中文版猎人模型"""

    class HunterModelCN(BaseModel):
        """中文版猎人开枪格式"""

        shoot: bool = Field(
            description="是否使用开枪技能",
        )
        target:str = Field(description="开枪目标玩家姓名")
        shoot_reason: Optional[str] = Field(description="开枪理由", default=None)

    return HunterModelCN


def get_vote_model_cn() -> type[BaseModel]:
    """获取中文版投票模型"""

    class VoteModelCN(BaseModel):
        """中文版投票输出格式"""

        vote: str = Field(
            description="你要投票淘汰的玩家姓名",
        )
        reason: str = Field(
            description="投票理由，简要说明为什么选择此人",
        )
        suspicion_level: int = Field(
            description="对被投票者的怀疑程度(1-10)", ge=1, le=10
        )

    return VoteModelCN
