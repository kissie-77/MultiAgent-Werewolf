const fs = require('fs');
let code = fs.readFileSync('server.ts', 'utf-8');

const target = `  // NIGHT SKILLS handling
  if (action === "NIGHT_KILL") {`;

const endTarget = `  if (action === "HUNTER_SHOOT") {`;

const startIdx = code.indexOf(target);
const endIdx = code.indexOf(endTarget);

if (startIdx !== -1 && endIdx !== -1) {
    const newCode = `  function advanceNightPhase(state: any, currentAction: string) {
    if (currentAction === "NIGHT_KILL") {
        const seer = state.players.find((p: any) => p.role === "预言家");
        if (seer && seer.isAlive) {
            state.phase = "NIGHT_SEER";
            state.narration = "群狼的猎杀已结束，血色之月隐入暗云。星宫的门扉洞开，【预言家请睁眼】... 你将勘破谁的灵魂？";
            if (!seer.isUser) {
                // AI Seer check: randomly inspects an alive suspicious target
                const validTargets = state.players.filter((p: any) => p.isAlive && p.role !== "预言家");
                const chosen = validTargets[Math.floor(Math.random() * validTargets.length)];
                state.seerVerifiedTarget = chosen.id;
                state.seerVerificationResult = chosen.role === "狼人" ? "WEREWOLF" : "HUMAN";
                seer.statusNotes = \`已查验\${chosen.id}号-\${chosen.role === "狼人" ? "狼人🐺" : "好人🛡️"}\`;
                return advanceNightPhase(state, "NIGHT_INSPECT");
            }
            return;
        } else {
            return advanceNightPhase(state, "NIGHT_INSPECT");
        }
    } else if (currentAction === "NIGHT_INSPECT") {
        const witch = state.players.find((p: any) => p.role === "女巫");
        if (witch && witch.isAlive) {
            state.phase = "NIGHT_WITCH";
            state.narration = "星空隐去，墨黑的巫术法阵亮起。女巫在釜底点燃烈焰，【女巫请睁眼】！今晚，有人已走到生死的边缘。您有一瓶解药与一瓶毒药，请做出你的抉择。";
            if (!witch.isUser) {
                // AI Witch: 50% action save, or poison someone
                if (Math.random() > 0.4 && state.wolfKilledTarget !== null) {
                    state.witchSaved = true;
                } else if (Math.random() > 0.7) {
                    const poisonOptions = state.players.filter((p: any) => p.isAlive && p.role !== "女巫");
                    state.witchPoisonedTarget = poisonOptions[Math.floor(Math.random() * poisonOptions.length)].id;
                }
                return advanceNightPhase(state, "NIGHT_SAVED_OR_POISON");
            }
            return;
        } else {
            return advanceNightPhase(state, "NIGHT_SAVED_OR_POISON");
        }
    } else if (currentAction === "NIGHT_SAVED_OR_POISON") {
        // Calculate Night casualties
        const killTarget = state.wolfKilledTarget;
        let dayVictimId = null;
        if (killTarget !== null && !state.witchSaved) {
            dayVictimId = killTarget;
        }
        if (state.witchPoisonedTarget !== null) {
            if (dayVictimId === null) {
                dayVictimId = state.witchPoisonedTarget;
            } else {
                dayVictimId = killTarget; // simplify
            }
        }

        state.victimId = dayVictimId;
        if (dayVictimId !== null) {
            const vPlayer = state.players.find((p: any) => p.id === dayVictimId);
            if (vPlayer) vPlayer.isAlive = false;
        }

        // Set stage to Day announcement
        state.phase = "DAY_ANNOUNCEMENT";
        state.currentSpeakerId = null;
        state.discussionIndex = 0;
        
        const casualtyText = dayVictimId !== null 
        ? \`悲报：黎明破晓，村民在圆形审判厅周围发现了倒在血泊中的【卡牌 \${dayVictimId} 号】。昨晚被无情杀害。\` 
        : "奇迹降临：旭日高升，今晚是一个平安夜。没有任何村民在睡梦中倒下！";
        state.narration = \`\${casualtyText} 请拉紧你们的披风。白昼讨论表决正式拉开帷幕，请点击底部的【石碑：进入辩论阶段】！\`;
        
        state.speechLogs.push({
            playerId: 0,
            playerName: "审判长",
            role: "NARRATOR",
            content: dayVictimId !== null ? \`第 \${state.dayNumber} 天白昼降临，\${dayVictimId}号玩家遇害惨死。\` : \`第 \${state.dayNumber} 天平安夜，无伤亡。\`,
            day: state.dayNumber,
            isNight: false
        });
    }
  }

  // NIGHT SKILLS handling
  if (action === "NIGHT_KILL") {
    const victim = targetId;
    if (victim) {
        activeGameState.wolfKilledTarget = victim;
    } else {
      // AI Wolf
      const validTargets = activeGameState.players.filter(p => p.isAlive && p.role !== "狼人");
      if (validTargets.length > 0) {
        activeGameState.wolfKilledTarget = validTargets[Math.floor(Math.random() * validTargets.length)].id;
      }
    }
    advanceNightPhase(activeGameState, "NIGHT_KILL");
    res.json(activeGameState);
    return;
  }

  if (action === "NIGHT_INSPECT") {
    if (targetId) {
      const chosen = activeGameState.players.find(p => p.id === targetId);
      if (chosen) {
        activeGameState.seerVerifiedTarget = targetId;
        activeGameState.seerVerificationResult = chosen.role === "狼人" ? "WEREWOLF" : "HUMAN";
        
        const user = activeGameState.players.find(p => p.isUser);
        if (user) user.statusNotes += \` | 查验\${targetId}号: \${chosen.role === "狼人" ? "狼人🐺" : "好人🛡️"}\`;
        chosen.statusNotes = \`已查验: \${chosen.role === "狼人" ? "狼人🐺" : "好人🛡️"}\`;
      }
    }
    advanceNightPhase(activeGameState, "NIGHT_INSPECT");
    res.json(activeGameState);
    return;
  }

  if (action === "NIGHT_SAVED_OR_POISON") {
    const { poisonTarget, saved } = req.body;
    activeGameState.witchSaved = saved;
    activeGameState.witchPoisonedTarget = poisonTarget;
    advanceNightPhase(activeGameState, "NIGHT_SAVED_OR_POISON");
    res.json(activeGameState);
    return;
  }

`;
    
    fs.writeFileSync('server.ts', code.substring(0, startIdx) + newCode + code.substring(endIdx));
    console.log("Successfully patched night cycle in server.ts");
} else {
    console.log("Failed to find target strings in server.ts");
}
