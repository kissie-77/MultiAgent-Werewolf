import express from "express";
import path from "path";
import { createServer as createViteServer } from "vite";
import { GoogleGenAI } from "@google/genai";
import dotenv from "dotenv";

dotenv.config();

// Initialize Gemini API
const apiKey = process.env.GEMINI_API_KEY;
let aiClient: any = null;

function getGeminiClient() {
  if (!aiClient) {
    if (apiKey) {
      aiClient = new GoogleGenAI({
        apiKey: apiKey,
        httpOptions: {
          headers: {
            'User-Agent': 'aistudio-build',
          }
        }
      });
    } else {
      console.warn("GEMINI_API_KEY is not defined. AI player speeches will fallback to pre-written logic.");
    }
  }
  return aiClient;
}

const app = express();
const PORT = 3000;

app.use(express.json());

// Game State Types
interface Player {
  id: number;
  name: string;
  role: "预言家" | "女巫" | "猎人" | "狼人" | "村民";
  isUser: boolean;
  isAlive: boolean;
  avatarSeed: string; // for drawing custom woodcut card
  lastSpeech: string;
  statusNotes: string; // e.g. "已查验-好人" for Seer's self-notes
  votedFor?: number;
}

interface GameState {
  players: Player[];
  dayNumber: number;
  phase: "START_SCREEN" | "ROLE_CHOICE" | "NIGHT_WOLF" | "NIGHT_SEER" | "NIGHT_WITCH" | "DAY_ANNOUNCEMENT" | "DAY_DEBATE" | "DAY_VOTE" | "GAME_OVER";
  currentSpeakerId: number | null; // ID of player speaking
  countdown: number;
  speechLogs: { playerId: number; playerName: string; role: string; content: string; day: number; isNight: boolean }[];
  narration: string;
  winner: "WOLVES" | "VILLAGERS" | null;
  wolfKilledTarget: number | null;
  witchSaved: boolean;
  witchPoisonedTarget: number | null;
  seerVerifiedTarget: number | null;
  seerVerificationResult: "HUMAN" | "WEREWOLF" | null;
  victimId: number | null; // who died tonight
  discussionIndex: number; // sequential index of speaker list during day debate
  executionId: number | null; // who got voted out during day
  gameMode?: "llmOnly" | "humanVsAI";
  playerCount?: number;
}

// Initial state creator helper
function createInitialState(
  userRole: "预言家" | "女巫" | "猎人" | "狼人" | "村民" = "预言家",
  playerCount = 6,
  gameMode: "llmOnly" | "humanVsAI" = "humanVsAI",
  startImmediately = false
): GameState {
  const isPureLLM = gameMode === "llmOnly";

  // Dynamic role distribution depending on playerCount from 1 to 16:
  let roles: ("预言家" | "女巫" | "猎人" | "狼人" | "村民")[] = [];
  if (playerCount === 1) {
    roles = ["预言家"];
  } else if (playerCount === 2) {
    roles = ["狼人", "预言家"];
  } else if (playerCount === 3) {
    roles = ["狼人", "预言家", "女巫"];
  } else if (playerCount === 4) {
    roles = ["狼人", "预言家", "女巫", "村民"];
  } else {
    // playerCount >= 5
    // Seer, Witch, Hunter are always present
    roles = ["预言家", "女巫", "猎人"];
    // Proportional Wolf count
    let wolvesCount = 2;
    if (playerCount <= 6) {
      wolvesCount = 2;
    } else if (playerCount <= 11) {
      wolvesCount = 3;
    } else {
      wolvesCount = 4;
    }
    for (let w = 0; w < wolvesCount; w++) {
      roles.push("狼人");
    }
    // Fill the rest with villagers
    const villagersCount = playerCount - roles.length;
    for (let c = 0; c < villagersCount; c++) {
      roles.push("村民");
    }
  }

  let playerRoles = [...roles];

  if (!isPureLLM) {
    // If our preset doesn't have the user role
    if (!playerRoles.includes(userRole)) {
      const replIdx = playerRoles.findIndex(r => r !== "狼人" && r !== "村民");
      if (replIdx !== -1) {
        playerRoles[replIdx] = userRole;
      } else {
        playerRoles[0] = userRole;
      }
    }
  }

  // Shuffle utility
  const shuffleArray = (arr: any[]) => {
    const copy = [...arr];
    for (let i = copy.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [copy[i], copy[j]] = [copy[j], copy[i]];
    }
    return copy;
  };

  let assignedRoles: ("预言家" | "女巫" | "猎人" | "狼人" | "村民")[] = [];
  if (!isPureLLM) {
    // Human is Player 1 and is guaranteed userRole
    const restRoles = [...playerRoles];
    const firstMatch = restRoles.indexOf(userRole);
    if (firstMatch !== -1) {
      restRoles.splice(firstMatch, 1);
    }
    assignedRoles = [userRole, ...shuffleArray(restRoles)];
  } else {
    // Pure AI
    assignedRoles = shuffleArray(playerRoles);
  }

  const names = [
    "你", "尤里安 (Julian)", "希尔达 (Hilda)", "雷恩 (Reyn)",
    "奥菲利亚 (Ophelia)", "加里 (Gary)", "克洛伊 (Chloe)", "塞缪尔 (Samuel)",
    "巴塞洛缪 (Bartholomew)", "凡妮莎 (Vanessa)", "阿尔道斯 (Aldous)", "伊丽莎 (Eliza)",
    "马格努斯 (Magnus)", "克拉拉 (Clara)", "塞德里克 (Cedric)", "奥利维亚 (Olivia)"
  ];
  
  const seeds = [
    "vanguard_user", "whisperer", "gothic_witch", "bearded_hunter",
    "lady_gloom", "shady_outsider", "noble_seer", "stout_villager",
    "grim_executioner", "lady_whisper", "shady_bard", "gothic_girl",
    "old_magnus", "pure_nun", "noble_knight", "dark_maiden"
  ];

  const players: Player[] = [];
  for (let i = 0; i < playerCount; i++) {
    const isUser = !isPureLLM && i === 0;
    const nameStr = isUser 
      ? `你 (${names[i] || `席位 ${i + 1}`})`
      : `${names[i] || `席位 ${i + 1}`} ${isPureLLM && i === 0 ? "(AI主角)" : ""}`;

    players.push({
      id: i + 1,
      name: nameStr,
      role: assignedRoles[i] || "村民",
      isUser: isUser,
      isAlive: true,
      avatarSeed: seeds[i] || `avatar_${i}`,
      lastSpeech: isUser ? "正在整理思绪..." : "等待夜幕审判...",
      statusNotes: ""
    });
  }

  const firstSpeakerId = isPureLLM ? 1 : 2;

  return {
    players,
    dayNumber: 1,
    phase: startImmediately ? "DAY_DEBATE" : "START_SCREEN", // Dynamic start phase
    currentSpeakerId: firstSpeakerId,
    countdown: 30,
    speechLogs: [
      { playerId: 0, playerName: "审判长", role: "NARRATOR", content: "神圣审判法纪庄严。圆形大理石桌上弥漫着迷雾，宿命对决已经敲定，审判开始！", day: 1, isNight: false }
    ],
    narration: isPureLLM
      ? "黑夜退去，雾气弥漫。全体好人阵营与狼人阵营均为AI智能推演。请点击底部的下一步发言或启动自动推演！"
      : "第一天黎明已经到来，今日是个平安夜。圆形审判法案前雾气弥漫，请听尤里安（2号玩家）的质询发言。",
    winner: null,
    wolfKilledTarget: null,
    witchSaved: false,
    witchPoisonedTarget: null,
    seerVerifiedTarget: null,
    seerVerificationResult: null,
    victimId: null,
    discussionIndex: 0,
    executionId: null,
    gameMode,
    playerCount
  };
}

// Global active game state
let activeGameState: GameState = createInitialState("预言家", 6, "humanVsAI");

// Gemini API Quota management and rate limit cooldowns to prevent spamming 429 exceptions
let last429Time = 0;
const COOLDOWN_DURATION_MS = 60000; // 60 seconds of silent fallback after hitting a 429

// API to fetch current state
app.get("/api/game/state", (req, res) => {
  res.json(activeGameState);
});

// API to reset/restart the game
app.post("/api/game/reset", (req, res) => {
  const { userRole, playerCount, gameMode, startImmediately } = req.body;
  activeGameState = createInitialState(userRole || "预言家", playerCount || 6, gameMode || "humanVsAI", startImmediately ?? false);
  res.json(activeGameState);
});

// API to exit the game back to start screen
app.post("/api/game/exit", (req, res) => {
  activeGameState.phase = "START_SCREEN";
  res.json(activeGameState);
});

// Helper: Dynamic fallback woodcut-themed speech developer when Gemini is not available or rate-limited
function getFallbackSpeech(player: Player, state: GameState): string {
  const aliveOthers = state.players.filter(p => p.isAlive && p.id !== player.id);
  const otherIds = aliveOthers.map(p => p.id);
  
  // Dynamic pick of others
  const targetId1 = otherIds.length > 0 ? otherIds[Math.floor(Math.random() * otherIds.length)] : 2;
  const targetId2 = otherIds.length > 1 ? otherIds[(Math.floor(Math.random() * (otherIds.length - 1)) + 1) % otherIds.length] : 3;
  const targetId3 = otherIds.length > 2 ? otherIds[(Math.floor(Math.random() * (otherIds.length - 2)) + 2) % otherIds.length] : 5;

  const targetName1 = state.players.find(p => p.id === targetId1)?.name || `玩家 ${targetId1}`;
  const targetName2 = state.players.find(p => p.id === targetId2)?.name || `玩家 ${targetId2}`;
  const targetName3 = state.players.find(p => p.id === targetId3)?.name || `玩家 ${targetId3}`;

  const genericSpeeches: Record<string, string[]> = {
    "狼人": [
      `昨晚血月当空，我们好人应该冷静抱团。依我拙见，【${targetName1}】发言时词句闪烁、极其反常，一直在强带节奏，非常像一只披着羊皮的倒钩狼。我底牌是尊尊厚实的好人，建议预言家顺手查验他，莫要放过任何破绽！`,
      `听完这一圈刀剑相交的辩论，我觉得【${targetName1}】和【${targetName2}】双狼结构已经呼之欲出了。特别是刚才【${targetName1}】发言时眼底有一丝不易察觉的冷笑。今天白昼惩戒，我这一票定会砸在他头上。`,
      `作为一介清白好人，昨晚的空刀让我高度怀疑有女巫暗中解救。但我看【${targetName2}】一直在试探女巫的银水，贼眉鼠眼地挑唆对立。你今晚若不吃毒，今天白昼就直接上绞刑台吧！`,
      `这世道充斥谎言，难道大家看不出【${targetName1}】在强穿预言家的神职衣服吗？他自称有金水，实则逻辑漏洞百出。不要再被他的迷魂阵干扰，本局首归票锁定他，将黑夜的恶狼当场揭发！`
    ],
    "预言家": [
      `大家请将目光投向我的神圣之镜！昨晚我连夜摸了【${targetName1}】的底细，镜中白羽洁净——他是【金水】好人，大家切莫踩错。接下来我的警徽流会覆盖【${targetName2}】和【${targetName3}】，跟着真预言家，不迷路！`,
      `我是全场唯一的真预言家，其余跳身份的都是邪祟！昨晚我直接探查了【${targetName1}】的底细，显露他是【查杀】（铁狼一只）！请悍跳狼别再狡辩，今天全体好人全票集中归票他，黑夜的罪恶该在白昼清算了！`,
      `昨夜迷雾散去，我顺手查验了【${targetName1}】的良知。他是【好人】，铁好人！我的警徽流极厚：一验【${targetName2}】，二验【${targetName3}】。如果我今晚遇害，请好人坚守这个阵线，铺平胜利道路！`
    ],
    "女巫": [
      `我的双生药水瓶中，一瓶盛着起死回生的琼浆，一瓶装着销骨噬肉的烈毒。昨晚平安夜，我的生死银水暂且不爆。但我警告【${targetName1}】，你挑衅我的言辞极度悬虚，今夜你若敢继续作乱，我必叫你尝尝我的剧毒！`,
      `真正的女巫从不守株待兔。昨晚的受害者虽然已被解救，但场上的恶狼已经等不及要冲锋了。今天好人们听真预言家指挥。如果没人带队，今天我们就集火【${targetName1}】，他的发言里藏着浓重野心。`
    ],
    "猎人": [
      `我怀抱中这杆狂野的淬银铁枪，随时能击穿黑夜！哪个嘴硬的狼崽子想尝尝银弹的滋味？如果我这轮被公投出局，大不了同归于尽，我定会在临死前枪毙【${targetName1}】。要送死的狼，尽管来投我！`,
      `我是猎人，我的白银枪膛已经上膛。今天大家放平心态，静听真预言家和女巫排队。谁若是敢强行带票【${targetName1}】来动我这个金刚铁神牌，我保证让你先倒在审判会前面！`
    ],
    "村民": [
      `我只是一名无辜、惊恐的落暮村民，没有神力，唯有一双辨别谎言真伪的冷眸。刚才【${targetName1}】发言强行为自己开脱，甚至拉踩无辜的【${targetName2}】。我觉得他发言极不作好，必有猫腻！`,
      `这场审判充满欺骗，真正的恶行已然隐没在迷雾。昨夜流血，我们好人本就势弱。依我看来，【${targetName1}】刚才的发言处处挑拨，意图把票引向真神.我提议，今天先全票打飞【${targetName1}】，绝不能让他蛊惑人心。`,
      `在圆形石桌旁，我感到窒息。为何【${targetName1}】的论调和昨晚狂吠的一模一样？我的直觉指引我，你一定是狼人假扮的平民。大家别听他混淆警徽流，本轮我们投【${targetName1}】自证清白！`
    ]
  };

  const pool = genericSpeeches[player.role] || genericSpeeches["村民"];
  return pool[Math.floor(Math.random() * pool.length)];
}

// Helper: AI action generator using Gemini API
async function askGeminiForSpeech(player: Player, state: GameState): Promise<string> {
  const client = getGeminiClient();
  if (!client) {
    return getFallbackSpeech(player, state);
  }

  // Check if we are currently under rate limiting cooldown
  const now = Date.now();
  if (now - last429Time < COOLDOWN_DURATION_MS) {
    const remainingSecs = Math.ceil((COOLDOWN_DURATION_MS - (now - last429Time)) / 1000);
    console.log(`[Gemini RateLimit] Silent bypass activated. Next try in ${remainingSecs}s. Self-providing immersive woodcut-themed monologue.`);
    return getFallbackSpeech(player, state);
  }

  // Construct context
  const alivePlayersInfo = state.players
    .map(p => `玩家 ${p.id} (${p.name}): 职业为 [${p.isUser ? p.role : "未知"}]，状态: ${p.isAlive ? "存活" : "死亡"}`)
    .join("\n");

  const speechHistory = state.speechLogs
    .slice(-10)
    .map(log => `【${log.playerName} (玩家 ${log.playerId})】: "${log.content}"`)
    .join("\n");

  const prompt = `你正在参与一场经典的 ${state.players.length} 人阿尔法黑白版画风格狼人杀对决。
你负责扮演：
- 角色：【玩家 ${player.id} (${player.name})】
- 你的真实桌上身份：【${player.role}】（注意：除非你是真预言家或被逼穿衣服，否则不要轻易泄露身份；如果你是狼人，你必须伪装好人，并试图拉踩或者泼脏水给好人，或者悍跳预言家发金水或查杀！）

当前游戏局势：
- 当前天数：第 ${state.dayNumber} 天白昼。
- 存活玩家及当前所知：
${alivePlayersInfo}

最近讨论记录：
${speechHistory}

你的目标：
请根据你的身份和场上局势，写一段 **符合狼人杀高玩辩论逻辑且充满悬疑黑帮漫画、木版画、石雕刻厚重宿命感** 的发言。
要求：
1. 语言必须阴沉、犀利、警觉、偏见、冷酷，符合暗黑漫画对立感（非可爱Q版，非现代科技赛博朋克）。
2. 字数限制在 90-140 字，简洁有力，留足空间。
3. 必须包含具体的狼人杀高玩逻辑学术语（例如：警徽流、金水、查杀、倒钩狼、冲锋狼、悍跳、穿衣服、归票、银水、平安夜）。
4. 以高能漫画台词般结尾。
5. 只能输出扮演角色的发言文字，不要含任何系统标签或括号说明。`;

  try {
    const response = await client.models.generateContent({
      model: "gemini-3.5-flash",
      contents: prompt,
      config: {
        systemInstruction: "你是一个狼人杀高玩，能扮演各种心理承受极强的游戏角色写出充满推理深度与浓郁版画暗黑风张力的发言台词。只输出台词本身，不允许额外回复。",
        temperature: 0.85,
      }
    });
    
    return response.text?.trim() || getFallbackSpeech(player, state);
  } catch (err: any) {
    const errMsg = String(err);
    if (errMsg.includes("429") || errMsg.includes("RESOURCE_EXHAUSTED") || errMsg.includes("quota")) {
      last429Time = Date.now();
      console.warn(`[Gemini API] Quota or rate limit exceeded. Activating fallback bypass cooldown for ${COOLDOWN_DURATION_MS / 1000}s.`);
    } else {
      console.warn("[Gemini API] Failed to generate content, falling back to woodcut speech engine:", errMsg);
    }
    return getFallbackSpeech(player, state);
  }
}

// API for progressive simulation loop
app.post("/api/game/action", async (req, res) => {
  const { action, targetId, text } = req.body;
  
  if (action === "SPEECH_SUBMIT") {
    // User submits their speech
    const user = activeGameState.players.find(p => p.isUser);
    if (user && user.isAlive) {
      user.lastSpeech = text || "我无可奉告，我的灵魂是纯洁的好人。";
      activeGameState.speechLogs.push({
        playerId: user.id,
        playerName: user.name,
        role: user.role,
        content: user.lastSpeech,
        day: activeGameState.dayNumber,
        isNight: false
      });
    }

    // Move state to voting or next speaker
    activeGameState.phase = "DAY_VOTE";
    activeGameState.narration = "所有玩家发言结束，圆形审判法阵被暗红色萤光激活。现在开始公投，请在卡牌列表中选择一名你怀疑的凶手并按下【封印印章】进行投票！";
    activeGameState.currentSpeakerId = null;
    res.json(activeGameState);
    return;
  }

  if (action === "USER_VOTE") {
    // User votes for targetId
    const voter = activeGameState.players.find(p => p.isUser);
    const userCanVote = voter && voter.isAlive && targetId !== undefined && targetId !== null;

    if (userCanVote && voter) {
      voter.votedFor = targetId;
    }

    // AI players generate votes randomly or logical-bias based
    // Calculate final votes
    const voteCounts: Record<number, number> = {};
    activeGameState.players.forEach(p => {
      if (p.isAlive) {
        if (p.isUser) {
          if (userCanVote && targetId !== undefined && targetId !== null) {
            voteCounts[targetId] = (voteCounts[targetId] || 0) + 1;
          }
        } else {
          // AI vote: bias slightly against suspect or user, or random alive player
          const aliveOthers = activeGameState.players.filter(o => o.isAlive && o.id !== p.id);
          if (aliveOthers.length > 0) {
            let aiVoteTarget = aliveOthers[Math.floor(Math.random() * aliveOthers.length)].id;
            // Wolves tend to vote together
            if (p.role === "狼人") {
              const wolfPartner = activeGameState.players.find(o => o.role === "狼人" && o.id !== p.id);
              if (wolfPartner && wolfPartner.votedFor) {
                aiVoteTarget = wolfPartner.votedFor;
              }
            }
            p.votedFor = aiVoteTarget;
            voteCounts[aiVoteTarget] = (voteCounts[aiVoteTarget] || 0) + 1;
          }
        }
      }
    });

    // Find who gets executed
    let maxVotes = 0;
    let executeTargetId = -1;
    let isTie = false;

    Object.entries(voteCounts).forEach(([pid, count]) => {
      const id = parseInt(pid);
      if (count > maxVotes) {
        maxVotes = count;
        executeTargetId = id;
        isTie = false;
      } else if (count === maxVotes) {
        isTie = true;
      }
    });

    // Execute target
    let executionText = "";
    if (executeTargetId !== -1 && !isTie) {
      const executedPlayer = activeGameState.players.find(p => p.id === executeTargetId);
      if (executedPlayer) {
        executedPlayer.isAlive = false;
        activeGameState.executionId = executeTargetId;
        executionText = `${executedPlayer.name} 获得了最高表决票数数位（${maxVotes} 票），圆形审判法阵射出惨白色辉芒，将其禁锢在荒芜石柱，判处放逐。其遗言：'${executedPlayer.lastSpeech.substring(0, 20)}...'`;
        
        // Push to logs
        activeGameState.speechLogs.push({
          playerId: 0,
          playerName: "审判长",
          role: "NARRATOR",
          content: `${executedPlayer.name} 在白昼公投中被公决流放，高呼不公！`,
          day: activeGameState.dayNumber,
          isNight: false
        });
      }
    } else {
      activeGameState.executionId = null;
      executionText = "审判会中发生激烈的质疑和分票，最终票数持平，议事桌陷入深沉的僵持。今日无人被流放！";
      activeGameState.speechLogs.push({
        playerId: 0,
        playerName: "审判长",
        role: "NARRATOR",
        content: "白昼表决票数持平，今日无人流放，夜色冷酷地逼近。",
        day: activeGameState.dayNumber,
        isNight: false
      });
    }

    // Check game over
    const aliveWolves = activeGameState.players.filter(p => p.isAlive && p.role === "狼人").length;
    const aliveGood = activeGameState.players.filter(p => p.isAlive && p.role !== "狼人").length;

    if (aliveWolves === 0) {
      activeGameState.phase = "GAME_OVER";
      activeGameState.winner = "VILLAGERS";
      activeGameState.narration = `${executionText} 晨星闪耀，所有恶狼均已被净化审判！大理石桌上的神圣符文重新绽放耀眼的光芒，【村民好人阵营获得了胜利】！`;
    } else if (aliveWolves >= aliveGood) {
      activeGameState.phase = "GAME_OVER";
      activeGameState.winner = "WOLVES";
      activeGameState.narration = `${executionText} 暮色四起，荒野巨狼撕咬下虚伪好人的外皮。狼牙的血迹已染红了圆形石桌，【狼人阵营篡夺了最终的胜利】！`;
    } else {
      // Advance to NEXT NIGHT
      activeGameState.dayNumber += 1;
      activeGameState.phase = "NIGHT_WOLF";
      activeGameState.narration = `${executionText} 白光散去，血红之月再次悬挂在石堡中央。浓黑的剧毒雾气弥漫了圆形议事厅。【夜幕降临】，群狼正在潜行，好人请闭眼...`;
      activeGameState.wolfKilledTarget = null;
      activeGameState.witchSaved = false;
      activeGameState.witchPoisonedTarget = null;
      activeGameState.seerVerifiedTarget = null;
      activeGameState.seerVerificationResult = null;
      activeGameState.players.forEach(p => p.votedFor = undefined);
    }

    res.json(activeGameState);
    return;
  }

  if (action === "SIMULATE_NEXT_SPEAKER") {
    // Progress discussions sequence index
    const debateSquad = activeGameState.players.filter(p => p.isAlive && !p.isUser);
    
    if (activeGameState.discussionIndex < debateSquad.length) {
      const currentSpeaker = debateSquad[activeGameState.discussionIndex];
      // Speak AI
      activeGameState.currentSpeakerId = currentSpeaker.id;
      const speech = await askGeminiForSpeech(currentSpeaker, activeGameState);
      
      currentSpeaker.lastSpeech = speech;
      activeGameState.speechLogs.push({
        playerId: currentSpeaker.id,
        playerName: currentSpeaker.name,
        role: currentSpeaker.role,
        content: speech,
        day: activeGameState.dayNumber,
        isNight: false
      });

      activeGameState.discussionIndex += 1;
      activeGameState.narration = `卡牌 ${currentSpeaker.id} 号（${currentSpeaker.name}）眼神凛冽，发言称："${speech.substring(0, 30)}..." 请点击下方【羊皮纸：下一步发言】继续聚焦！`;
    } else {
      // User's turn to speak if user is alive!
      const user = activeGameState.players.find(p => p.isUser);
      if (user && user.isAlive) {
        activeGameState.currentSpeakerId = user.id;
        activeGameState.narration = "议桌的微光对准了你。你是目前全场关注的中心！请在下方发言输入栏留下你犀利的辩护，并点击【羊皮纸：确认发言】！";
      } else {
        // User is dead or skipped
        activeGameState.phase = "DAY_VOTE";
        activeGameState.narration = "所有玩家发言结束，圆形审判法阵被激活。请在卡牌列表中选择一名你怀疑的狼人，按下【封印印章】进行投票！";
        activeGameState.currentSpeakerId = null;
      }
    }
    res.json(activeGameState);
    return;
  }

  // NIGHT SKILLS handling
  if (action === "NIGHT_KILL") {
    // Werewolf User or AI action
    const victim = targetId;
    activeGameState.wolfKilledTarget = victim;
    
    // Auto speed up night phase to the next action Seer
    const seer = activeGameState.players.find(p => p.role === "预言家");
    if (seer && seer.isAlive && !seer.isUser) {
      // AI Seer check: randomly inspects an alive suspicious target
      const validTargets = activeGameState.players.filter(p => p.isAlive && p.role !== "预言家");
      const chosen = validTargets[Math.floor(Math.random() * validTargets.length)];
      activeGameState.seerVerifiedTarget = chosen.id;
      activeGameState.seerVerificationResult = chosen.role === "狼人" ? "WEREWOLF" : "HUMAN";
      // Update seer private notes
      seer.statusNotes = `已查验${chosen.id}号-${chosen.role === "狼人" ? "狼人" : "好人"}`;
    }
    
    // Witch AI Action (if Witch is AI and alive)
    const witch = activeGameState.players.find(p => p.role === "女巫");
    if (witch && witch.isAlive && !witch.isUser) {
      // AI Witch: 50% action save, or poison someone
      if (Math.random() > 0.4 && activeGameState.wolfKilledTarget) {
        activeGameState.witchSaved = true;
      } else if (Math.random() > 0.7) {
        const poisonOptions = activeGameState.players.filter(p => p.isAlive && p.role !== "女巫");
        activeGameState.witchPoisonedTarget = poisonOptions[Math.floor(Math.random() * poisonOptions.length)].id;
      }
    }

    // Calculate Night casualties
    const killTarget = activeGameState.wolfKilledTarget;
    let dayVictimId: number | null = null;
    if (killTarget !== null && !activeGameState.witchSaved) {
      dayVictimId = killTarget;
    }
    if (activeGameState.witchPoisonedTarget !== null) {
      if (dayVictimId === null) {
        dayVictimId = activeGameState.witchPoisonedTarget;
      } else {
        // Can support multi casualties, but let's keep it simple for 6p (at most 1 death log report)
        dayVictimId = killTarget; // simplify
      }
    }

    activeGameState.victimId = dayVictimId;
    if (dayVictimId !== null) {
      const vPlayer = activeGameState.players.find(p => p.id === dayVictimId);
      if (vPlayer) vPlayer.isAlive = false;
    }

    // Set stage to Day announcement
    activeGameState.phase = "DAY_ANNOUNCEMENT";
    activeGameState.currentSpeakerId = null;
    activeGameState.discussionIndex = 0;
    
    const casualtyText = dayVictimId !== null 
      ? `悲报：黎明破晓，村民在圆形审判厅周围发现了倒在血泊中的【卡牌 ${dayVictimId} 号】。昨晚被无情杀害。` 
      : "奇迹降临：旭日高升，今晚是一个平安夜。没有任何村民在睡梦中倒下！";
    activeGameState.narration = `${casualtyText} 请拉紧你们的披风。白昼讨论表决正式拉开帷幕，请点击底部的【石碑：进入辩论阶段】！`;
    
    activeGameState.speechLogs.push({
      playerId: 0,
      playerName: "审判长",
      role: "NARRATOR",
      content: dayVictimId !== null ? `第 ${activeGameState.dayNumber} 天白昼降临，${dayVictimId}号玩家遇害惨死。` : `第 ${activeGameState.dayNumber} 天平安夜，无伤亡。`,
      day: activeGameState.dayNumber,
      isNight: false
    });

    res.json(activeGameState);
    return;
  }

  // Seer action manual (if User is Seer)
  if (action === "NIGHT_INSPECT") {
    const chosen = activeGameState.players.find(p => p.id === targetId);
    if (chosen) {
      activeGameState.seerVerifiedTarget = targetId;
      activeGameState.seerVerificationResult = chosen.role === "狼人" ? "WEREWOLF" : "HUMAN";
      
      const user = activeGameState.players.find(p => p.isUser);
      if (user) {
        user.statusNotes += ` | 查验${targetId}号: ${chosen.role === "狼人" ? "狼人🐺" : "好人🛡️"}`;
      }

      // Fast-forward night cycle
      activeGameState.phase = "DAY_ANNOUNCEMENT";
      const killTarget = Math.floor(Math.random() * 6) + 1; // simulation of werewolf kill
      const aliveGoodExceptWolf = activeGameState.players.filter(p => p.isAlive && p.role !== "狼人");
      const targetKill = aliveGoodExceptWolf[Math.floor(Math.random() * aliveGoodExceptWolf.length)].id;
      
      activeGameState.victimId = targetKill;
      const deadPlayer = activeGameState.players.find(p => p.id === targetKill);
      if (deadPlayer) deadPlayer.isAlive = false;

      activeGameState.narration = `预言明镜揭示：玩家 ${targetId} 号的灵魂是【${chosen.role === "狼人" ? "亵渎的邪恶狼人" : "神圣无辜的好人"}】！黎明显现，昨晚牺牲的死者是卡牌 ${targetKill} 号村民。点击底部【石碑：进入大讨论】进行审问！`;
      activeGameState.currentSpeakerId = null;
      activeGameState.discussionIndex = 0;
    }
    res.json(activeGameState);
    return;
  }

  if (action === "NIGHT_SAVED_OR_POISON") {
    // If User is Witch
    const { poisonTarget, saved } = req.body;
    activeGameState.witchSaved = saved;
    activeGameState.witchPoisonedTarget = poisonTarget;

    let killed = 1; // simulated wolf kill target
    activeGameState.victimId = saved ? poisonTarget : killed;

    if (activeGameState.victimId) {
      const dead = activeGameState.players.find(p => p.id === activeGameState.victimId);
      if (dead) dead.isAlive = false;
    }

    activeGameState.phase = "DAY_ANNOUNCEMENT";
    activeGameState.narration = `药水倾注完毕。清晨的钟声震耳敲响，圆形审判法阵被光芒撕碎。今晚的牺牲者是 [卡牌 ${activeGameState.victimId || "无"} 号]。白昼的喧嚣已至，点击底部【石碑：进入大讨论】!`;
    activeGameState.currentSpeakerId = null;
    activeGameState.discussionIndex = 0;

    res.json(activeGameState);
    return;
  }

  if (action === "HUNTER_SHOOT") {
    const target = activeGameState.players.find(p => p.id === targetId);
    if (!target || !target.isAlive) {
      return res.status(400).json({ error: "无效的射击目标！" });
    }

    target.isAlive = false;
    
    // Add immersive narration and logs
    activeGameState.narration = `📣 【绝死带杀绝击】 伴随着回荡大厅的银色枪鸣，负伤的猎人高傲拉栓，将滚烫的银质弹壳抛落在地。圣洁的白银灵能子弹携裹猎人的怒火瞬间贯穿了 [玩家 ${targetId} 号 ${target.name}]的胸膛！将其拖入冰冷的长眠...`;
    
    activeGameState.speechLogs.push({
      playerId: 0,
      playerName: "审判长",
      role: "NARRATOR",
      content: `钢枪猎人启动绝命余烬：击发子弹狙击了 [玩家 ${targetId} 号] (${target.name})！`,
      day: activeGameState.dayNumber,
      isNight: false
    });

    // Recalculate game over
    const aliveWolves = activeGameState.players.filter(p => p.isAlive && p.role === "狼人").length;
    const aliveGood = activeGameState.players.filter(p => p.isAlive && p.role !== "狼人").length;

    if (aliveWolves === 0) {
      activeGameState.phase = "GAME_OVER";
      activeGameState.winner = "VILLAGERS";
      activeGameState.narration += `\n🌟 圣银弹丸驱散了最后的黑暗。剩余的村民欢呼雀跃，在誓言怒枪下粉碎了狼祸，【好人阵营获得了神圣胜利】！`;
    } else if (aliveWolves >= aliveGood) {
      activeGameState.phase = "GAME_OVER";
      activeGameState.winner = "WOLVES";
      activeGameState.narration += `\n🩸 猎手虽带走了仇敌，但法阵中最后的狼啸依然打破了黎明的宁静。好人抵抗土崩瓦解，【狼人阵营血洗村落取得了胜利】！`;
    }

    res.json(activeGameState);
    return;
  }

  if (action === "TRANSITION_TO_DEBATE") {
    // Move from DAY_ANNOUNCEMENT to DAY_DEBATE
    activeGameState.phase = "DAY_DEBATE";
    activeGameState.discussionIndex = 0;
    
    const firstSpeaker = activeGameState.players.filter(p => p.isAlive && !p.isUser)[0];
    if (firstSpeaker) {
      activeGameState.currentSpeakerId = firstSpeaker.id;
      activeGameState.narration = `辩论大门开启！玩家 ${firstSpeaker.id} 号正在直视各位。请见并听取其见解。点击【羊皮纸：下一步发言】让下一个人论述！`;
    } else {
      // User is the only alive one
      activeGameState.currentSpeakerId = 1;
      activeGameState.narration = "场上除你之外的好人神色慌乱，由你首先主导辩护！请在底部拼写并发表你的终极言论。";
    }
    res.json(activeGameState);
    return;
  }

  res.json(activeGameState);
});

// Serve static assets or bundle inside async bootstrap
async function bootstrap() {
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  // Bind to Port 3000
  app.listen(PORT, "0.0.0.0", () => {
    console.log(`[Werewolf Backend] Standing trial on port ${PORT}`);
  });
}

bootstrap().catch((err) => {
  console.error("Failed to bootstrap server:", err);
});
