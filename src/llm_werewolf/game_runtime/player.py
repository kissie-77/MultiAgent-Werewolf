from llm_werewolf.game_runtime.types import Camp, PlayerInfo, PlayerStatus, RoleProtocol, AgentProtocol


class Player:
    """表示狼人杀游戏中的一名玩家。"""

    def __init__(
        self,
        player_id: str,
        name: str,
        role: type[RoleProtocol],
        agent: AgentProtocol | None = None,
        ai_model: str = "unknown",
    ) -> None:
        """初始化玩家。

        Args:
            player_id: 玩家唯一标识。
            name: 显示名称。
            role: 分配给该玩家的角色。
            agent: 控制该玩家的 AI 智能体（可选）。
            ai_model: 所使用的 AI 模型名称。
        """
        self.player_id = player_id
        self.name = name
        self.role = role(self)
        self.agent = agent
        self.ai_model = ai_model

        self._alive = True
        self.statuses: set[PlayerStatus] = {PlayerStatus.ALIVE}
        self.lover_partner_id: str | None = None

        self.can_vote_flag = True

    def is_alive(self) -> bool:
        """检查玩家是否存活。

        Returns:
            bool: 存活则为 True。
        """
        return self._alive

    def kill(self) -> None:
        """将玩家标记为死亡。"""
        self._alive = False
        self.statuses.discard(PlayerStatus.ALIVE)
        self.statuses.add(PlayerStatus.DEAD)

    def revive(self) -> None:
        """复活玩家（例如女巫解药）。"""
        self._alive = True
        self.statuses.discard(PlayerStatus.DEAD)
        self.statuses.add(PlayerStatus.ALIVE)
        if self.has_status(PlayerStatus.NO_VOTE):
            self.can_vote_flag = True
            self.remove_status(PlayerStatus.NO_VOTE)

    def add_status(self, status: PlayerStatus) -> None:
        """为玩家添加状态。

        Args:
            status: 要添加的状态。
        """
        self.statuses.add(status)

    def remove_status(self, status: PlayerStatus) -> None:
        """移除玩家状态。

        Args:
            status: 要移除的状态。
        """
        self.statuses.discard(status)

    def has_status(self, status: PlayerStatus) -> bool:
        """检查玩家是否具有指定状态。

        Args:
            status: 要检查的状态。

        Returns:
            bool: 具有该状态则为 True。
        """
        return status in self.statuses

    def can_vote(self) -> bool:
        """检查玩家是否可以投票。

        Returns:
            bool: 可以投票则为 True。
        """
        return self._alive and self.can_vote_flag

    def disable_voting(self) -> None:
        """剥夺玩家的投票权。"""
        self.can_vote_flag = False
        self.add_status(PlayerStatus.NO_VOTE)

    def set_lover(self, partner_id: str) -> None:
        """将玩家与另一玩家设为恋人。

        Args:
            partner_id: 恋人伙伴的玩家 ID。
        """
        self.lover_partner_id = partner_id
        self.add_status(PlayerStatus.LOVER)

    def is_lover(self) -> bool:
        """检查玩家是否为恋人。

        Returns:
            bool: 是恋人则为 True。
        """
        return self.has_status(PlayerStatus.LOVER)

    def is_sheriff(self) -> bool:
        """检查玩家是否为警长。

        Returns:
            bool: 是警长则为 True。
        """
        return self.has_status(PlayerStatus.SHERIFF)

    def make_sheriff(self) -> None:
        """使该玩家成为警长。"""
        self.add_status(PlayerStatus.SHERIFF)

    def remove_sheriff(self) -> None:
        """移除该玩家的警长身份。"""
        self.remove_status(PlayerStatus.SHERIFF)

    def get_vote_weight(self) -> float:
        """获取玩家投票权重。

        Returns:
            float: 警长为 1.5，其他为 1.0。
        """
        return 1.5 if self.is_sheriff() else 1.0

    def get_public_info(self) -> PlayerInfo:
        """获取玩家的公开信息。

        Returns:
            PlayerInfo: 公开的玩家信息。
        """
        return PlayerInfo(
            player_id=self.player_id,
            name=self.name,
            is_alive=self._alive,
            statuses=self.statuses.copy(),
            ai_model=self.ai_model,
        )

    def get_private_notes(self, game_state: object | None = None) -> list[str]:
        """获取该玩家有权知晓的私密事实。"""
        if hasattr(self.role, "get_private_notes"):
            return self.role.get_private_notes(game_state)
        return []

    def get_role_name(self) -> str:
        """获取玩家角色名称。

        Returns:
            str: 角色名称。
        """
        return self.role.name

    def get_camp(self) -> Camp:
        """获取玩家阵营。

        Returns:
            Camp: 阵营枚举。
        """
        return self.role.camp

    def __str__(self) -> str:
        """玩家的字符串表示。

        Returns:
            str: 玩家名称与存活状态。
        """
        status = "alive" if self._alive else "dead"
        return f"{self.name} ({status})"

    def __repr__(self) -> str:
        """玩家的 repr 表示。

        Returns:
            str: 玩家表示。
        """
        return f"Player(id={self.player_id}, name={self.name}, role={self.role.name})"
