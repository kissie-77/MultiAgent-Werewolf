from enum import Enum


class Camp(str, Enum):
    """表示游戏中各阵营的枚举。"""

    WEREWOLF = "werewolf"
    VILLAGER = "villager"
    NEUTRAL = "neutral"


class VictoryGoal(str, Enum):
    """角色定义中的胜利条件类别。"""

    WEREWOLF_PARITY = "werewolf_parity"
    VILLAGER_ELIMINATE_WEREWOLVES = "villager_eliminate_werewolves"
    NEUTRAL_LOVER = "neutral_lover"
    NEUTRAL_THIEF = "neutral_thief"
    NEUTRAL_WHITE_LOVER_WOLF = "neutral_white_lover_wolf"
    FOLLOW_ASSIGNED_CAMP = "follow_assigned_camp"


class ActionPriority(int, Enum):
    """表示夜间行动优先级的枚举。

    数值越大优先级越高（越先执行）。
    """

    CUPID = 100
    NIGHTMARE_WOLF = 98  # 须在其他角色之前行动以封印其技能
    THIEF = 95
    GUARD = 90
    WEREWOLF = 80
    WHITE_WOLF = 75
    WITCH = 70
    SEER = 60
    GRAVEYARD_KEEPER = 50
    RAVEN = 40


class GamePhase(str, Enum):
    """表示游戏各阶段的枚举。"""

    SETUP = "setup"
    NIGHT = "night"
    SHERIFF_ELECTION = "sheriff_election"
    DAY_DISCUSSION = "day_discussion"
    DAY_VOTING = "day_voting"
    ENDED = "ended"


class PlayerStatus(str, Enum):
    """表示玩家可拥有的特殊状态的枚举。"""

    ALIVE = "alive"
    DEAD = "dead"
    PROTECTED = "protected"
    POISONED = "poisoned"
    SAVED = "saved"
    CHARMED = "charmed"
    BLOCKED = "blocked"
    MARKED = "marked"
    REVEALED = "revealed"
    NO_VOTE = "no_vote"
    LOVER = "lover"
    SHERIFF = "sheriff"


class ActionType(str, Enum):
    """表示各类行动类型的枚举。"""

    WEREWOLF_KILL = "werewolf_kill"
    WITCH_SAVE = "witch_save"
    WITCH_POISON = "witch_poison"
    SEER_CHECK = "seer_check"
    GUARD_PROTECT = "guard_protect"
    CUPID_LINK = "cupid_link"
    RAVEN_MARK = "raven_mark"
    GRAVEYARD_KEEPER_CHECK = "graveyard_keeper_check"
    WHITE_WOLF_KILL = "white_wolf_kill"
    WOLF_BEAUTY_CHARM = "wolf_beauty_charm"
    NIGHTMARE_BLOCK = "nightmare_block"

    VOTE = "vote"
    SHERIFF_CAMPAIGN = "sheriff_campaign"
    SHERIFF_VOTE = "sheriff_vote"
    SHERIFF_TRANSFER = "sheriff_transfer"
    HUNTER_SHOOT = "hunter_shoot"
    KNIGHT_DUEL = "knight_duel"
    ALPHA_WOLF_SHOOT = "alpha_wolf_shoot"

    THIEF_CHOOSE = "thief_choose"
    MAGICIAN_SWAP = "magician_swap"


class EventType(str, Enum):
    """表示各类游戏事件类型的枚举。"""

    GAME_STARTED = "game_started"
    GAME_ENDED = "game_ended"
    PHASE_CHANGED = "phase_changed"
    ROUND_STARTED = "round_started"

    PLAYER_DIED = "player_died"
    PLAYER_REVIVED = "player_revived"
    ROLE_REVEALED = "role_revealed"
    ROLE_ACTING = "role_acting"

    WEREWOLF_KILLED = "werewolf_killed"
    WITCH_SAVED = "witch_saved"
    WITCH_POISONED = "witch_poisoned"
    SEER_CHECKED = "seer_checked"
    GUARD_PROTECTED = "guard_protected"

    VOTE_CAST = "vote_cast"
    VOTE_INTENTION_SNAPSHOT = "vote_intention_snapshot"
    VOTE_RESULT = "vote_result"
    PLAYER_ELIMINATED = "player_eliminated"

    SHERIFF_CAMPAIGN_STARTED = "sheriff_campaign_started"
    SHERIFF_CANDIDATE_SPEECH = "sheriff_candidate_speech"
    SHERIFF_VOTE_CAST = "sheriff_vote_cast"
    SHERIFF_ELECTED = "sheriff_elected"
    SHERIFF_TIE = "sheriff_tie"
    SHERIFF_BADGE_TRANSFERRED = "sheriff_badge_transferred"
    SHERIFF_BADGE_TORN = "sheriff_badge_torn"

    LOVERS_LINKED = "lovers_linked"
    LOVER_DIED = "lover_died"
    HUNTER_REVENGE = "hunter_revenge"
    KNIGHT_DUEL = "knight_duel"

    PLAYER_SPEECH = "player_speech"
    PLAYER_DISCUSSION = "player_discussion"

    MESSAGE = "message"
    ERROR = "error"
