"""角色定义模式（名称、实现、阵营、胜利目标）。"""

from pydantic import Field, BaseModel

from llm_werewolf.game_runtime.types.enums import Camp, VictoryGoal


class RoleDefinition(BaseModel):
    """用于注册与提示词的声明式角色元数据。

    字段:
        name: 注册表键（如 ``Seer``），与角色类注册名一致。
        display_name: 向玩家展示的中文可读名称。
        implementation: 角色实现的导入路径 ``module:Class``。
        camp: 阵营 / 身份阵营。
        victory_goal: 用于文档与提示词的胜利条件类别。
    """

    name: str = Field(..., description="Registry key, e.g. Seer")
    display_name: str = Field(..., description="Chinese display name")
    implementation: str = Field(
        ...,
        description="Role class as module:Class, e.g. llm_werewolf.game_runtime.roles.villager:Seer",
    )
    camp: Camp = Field(..., description="Faction camp")
    victory_goal: VictoryGoal = Field(..., description="Victory objective category")
