import React from "react";
import { MvpPlayer, PlayerScore, TurningPoint } from "../api/types";
import { Crown, Trophy, Target, Sparkles, TrendingUp, ShieldCheck, ShieldAlert, Moon, Sun, Vote } from "lucide-react";
import { motion } from "motion/react";
import ReactMarkdown from "react-markdown";

interface MvpTabProps {
  mvpRanking: MvpPlayer[];
  scores: PlayerScore[];
  turningPoints: TurningPoint[];
  reportMarkdown: string;
  runModel: string;
}

export default function MvpTab({ mvpRanking, scores, turningPoints, reportMarkdown, runModel }: MvpTabProps) {
  // 合并 MVP 和得分数据
  const mergedPlayers = scores.map(score => {
    const mvpInfo = mvpRanking.find(m => m.playerName === score.playerName);
    // 若无阵营字段，根据角色粗略判断阵营
    const camp = ['狼人', 'Werewolf', 'Wolf'].some(w => score.role.includes(w)) ? 'WEREWOLF' : 'GOOD';
    return {
      ...score,
      camp,
      rank: mvpInfo?.rank || 99,
      isMvp: mvpInfo?.isMvp || false,
    };
  }).sort((a, b) => a.rank - b.rank);

  const overallMvp = mergedPlayers.find(p => p.isMvp) || mergedPlayers[0];
  const goodMvp = mergedPlayers.filter(p => p.camp === 'GOOD').sort((a, b) => b.totalScore - a.totalScore)[0];
  const wolfMvp = mergedPlayers.filter(p => p.camp === 'WEREWOLF').sort((a, b) => b.totalScore - a.totalScore)[0];

  const maxStat = Math.max(1, ...mergedPlayers.map(p => Math.max(p.logicSpeechScore, p.deceptionMisleaderScore, p.cooperationRate, p.gameSurvivalScore)));

  const StatBar = ({ label, value }: { label: string, value: number }) => (
    <div className="flex items-center gap-3">
      <div className="w-16 font-mono text-[10px] text-zinc-500 uppercase">{label}</div>
      <div className="w-8 text-right font-mono text-xs text-zinc-300">{value.toFixed(0)}</div>
      <div className="flex-1 h-1.5 bg-zinc-900 rounded-full overflow-hidden">
        <div className="h-full bg-amber-500" style={{ width: `${(value / maxStat) * 100}%` }} />
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Top Row: MVP Spotlight & Camp MVP */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* TOP-LEFT: MVP Spotlight */}
        <div className="border border-zinc-900 bg-zinc-950/60 rounded p-6 flex flex-col sm:flex-row gap-6 relative overflow-hidden">
          <div className="absolute top-0 left-0 w-1 h-full bg-amber-500" />
          <div className="flex-1 space-y-4">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-amber-500/10 border border-amber-500/30 rounded flex items-center justify-center text-amber-500 shrink-0">
                <Crown className="w-6 h-6" />
              </div>
              <div>
                <div className="text-[10px] font-mono text-amber-500 tracking-widest uppercase mb-1">Rank-1 ∙ MVP</div>
                <h3 className="font-serif text-2xl font-black text-zinc-100 flex items-center gap-2">
                  {overallMvp?.playerName}
                </h3>
                <div className="flex items-center gap-2 mt-1">
                  <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${overallMvp?.camp === 'WEREWOLF' ? 'bg-red-500/10 text-red-500 border-red-500/30' : 'bg-blue-500/10 text-blue-400 border-blue-500/30'}`}>
                    {overallMvp?.role}
                  </span>
                  <span className="text-[10px] font-mono text-zinc-500 uppercase px-1.5 py-0.5 border border-zinc-800 rounded bg-zinc-900">
                    {runModel}
                  </span>
                </div>
              </div>
              <div className="ml-auto text-right">
                <div className="font-mono text-3xl font-black text-amber-500">{overallMvp?.totalScore.toFixed(1)}</div>
                <div className="text-[10px] font-sans text-zinc-500 tracking-widest">综合得分</div>
              </div>
            </div>
            
            <div className="space-y-2.5 pt-4 border-t border-zinc-900/60">
              <StatBar label="公开说服" value={overallMvp?.logicSpeechScore || 0} />
              <StatBar label="暗夜伪装" value={overallMvp?.deceptionMisleaderScore || 0} />
              <StatBar label="策略协同" value={overallMvp?.cooperationRate || 0} />
              <StatBar label="生存结果" value={overallMvp?.gameSurvivalScore || 0} />
            </div>
          </div>
        </div>

        {/* TOP-RIGHT: Camp MVP */}
        <div className="border border-zinc-900 bg-zinc-950/60 rounded p-6 flex flex-col justify-center space-y-6">
          <div className="text-xs font-sans text-zinc-500 tracking-widest text-center">阵营破局者</div>
          
          <div className="flex items-center justify-between border border-blue-500/20 bg-blue-500/5 p-4 rounded">
             <div className="flex items-center gap-3">
               <ShieldCheck className="w-5 h-5 text-blue-400" />
               <div>
                  <div className="text-[10px] font-sans text-blue-400/70 mb-0.5">好人阵营</div>
                  <div className="font-bold text-blue-100 flex items-center gap-1.5 font-sans">
                    {goodMvp?.playerName} <span className="text-xs text-blue-400/80 font-normal">({goodMvp?.role})</span>
                  </div>
               </div>
             </div>
             <div className="font-mono text-lg font-bold text-blue-400">
               {goodMvp?.totalScore.toFixed(1)}
             </div>
          </div>

          <div className="flex items-center justify-between border border-red-500/20 bg-red-500/5 p-4 rounded">
             <div className="flex items-center gap-3">
               <ShieldAlert className="w-5 h-5 text-red-500" />
               <div>
                  <div className="text-[10px] font-sans text-red-500/70 mb-0.5">狼人阵营</div>
                  <div className="font-bold text-red-100 flex items-center gap-1.5 font-sans">
                    {wolfMvp?.playerName} <span className="text-xs text-red-400/80 font-normal">({wolfMvp?.role})</span>
                  </div>
               </div>
             </div>
             <div className="font-mono text-lg font-bold text-red-500">
               {wolfMvp?.totalScore.toFixed(1)}
             </div>
          </div>
        </div>
      </div>

      {/* MIDDLE: RankTable */}
      <div className="border border-zinc-900 bg-zinc-950/40 rounded overflow-x-auto">
         <table className="w-full text-left font-mono min-w-[700px]">
           <thead className="bg-zinc-900/30 text-[10px] text-zinc-500 uppercase tracking-widest">
             <tr>
               <th className="font-normal px-4 py-3 w-12 text-center">#</th>
               <th className="font-normal px-4 py-3">玩家</th>
               <th className="font-normal px-4 py-3">身份</th>
               <th className="font-normal px-4 py-3">阵营</th>
               <th className="font-normal px-4 py-3 text-right text-amber-500">综合</th>
               <th className="font-normal px-4 py-3 text-right">说服</th>
               <th className="font-normal px-4 py-3 text-right">伪装夜战</th>
               <th className="font-normal px-4 py-3 text-right">策略</th>
               <th className="font-normal px-4 py-3 text-right">结果</th>
             </tr>
           </thead>
           <tbody className="text-xs divide-y divide-zinc-900/50">
             {mergedPlayers.map((p, idx) => (
               <tr key={idx} className={`font-sans hover:bg-zinc-900/30 transition-colors ${p.camp === 'WEREWOLF' ? 'bg-red-500/[0.02]' : 'bg-blue-500/[0.02]'}`}>
                 <td className="px-4 py-3 text-center text-zinc-500 font-mono">{idx + 1}</td>
                 <td className="px-4 py-3 font-bold text-zinc-200">
                   {p.playerName}
                   {p.isMvp && <Crown className="inline w-3 h-3 text-amber-500 ml-1.5 -translate-y-0.5" />}
                 </td>
                 <td className="px-4 py-3 text-zinc-400">{p.role}</td>
                 <td className="px-4 py-3">
                   {p.camp === 'WEREWOLF' ? (
                     <span className="text-red-500">🐺 狼人</span>
                   ) : (
                     <span className="text-blue-400">✨ 好人</span>
                   )}
                 </td>
                 <td className="px-4 py-3 text-right font-mono font-bold text-amber-500">{p.totalScore.toFixed(1)}</td>
                 <td className="px-4 py-3 text-right font-mono text-zinc-400">{p.logicSpeechScore.toFixed(1)}</td>
                 <td className="px-4 py-3 text-right font-mono text-zinc-400">{p.deceptionMisleaderScore.toFixed(1)}</td>
                 <td className="px-4 py-3 text-right font-mono text-zinc-400">{p.cooperationRate.toFixed(1)}</td>
                 <td className="px-4 py-3 text-right font-mono text-zinc-400">{p.gameSurvivalScore.toFixed(1)}</td>
               </tr>
             ))}
           </tbody>
         </table>
      </div>

      {/* BOTTOM ROW: TurningPoints + MarkdownPanel */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* BOTTOM-LEFT: TurningPoints Timeline */}
        <div className="border border-zinc-900 bg-zinc-950/60 rounded p-6">
           <h3 className="font-serif text-sm font-black tracking-widest text-[#eae5db] uppercase mb-6 flex items-center gap-2">
             <TrendingUp className="w-4 h-4 text-amber-500" />
             战局转折点 (Turning Points)
           </h3>
           <div className="relative pl-6 space-y-6">
              <div className="absolute top-2 bottom-2 left-2 w-px bg-zinc-800" />
              {turningPoints.map((tp, idx) => {
                 const isFinal = idx === turningPoints.length - 1;
                 const isGoodWin = isFinal && tp.title.includes("好人胜");
                 
                 let Icon = Sparkles;
                 if (tp.title.includes("夜")) Icon = Moon;
                 else if (tp.title.includes("白") || tp.title.includes("天")) Icon = Sun;
                 else if (tp.desc.includes("死") || tp.desc.includes("出局")) Icon = ShieldAlert;
                 else if (tp.desc.includes("投票") || tp.title.includes("投票")) Icon = Vote;
                 
                 return (
                   <div key={idx} className="relative">
                      <div className={`absolute -left-[28px] w-6 h-6 rounded-full flex items-center justify-center border ${isFinal ? (isGoodWin ? 'bg-emerald-500/20 border-emerald-500/50 text-emerald-400' : 'bg-red-500/20 border-red-500/50 text-red-500') : 'bg-zinc-900 border-zinc-700 text-zinc-400'}`}>
                         <Icon className="w-3 h-3" />
                      </div>
                      <div className={`text-xs font-mono mb-1 ${isFinal ? (isGoodWin ? 'text-emerald-400' : 'text-red-500') : 'text-zinc-500'}`}>
                        {tp.title}
                      </div>
                      <div className="text-sm text-zinc-300 font-sans leading-relaxed">
                        {tp.desc}
                      </div>
                   </div>
                 );
              })}
           </div>
        </div>

        {/* BOTTOM-RIGHT: MarkdownPanel */}
        <div className="border border-zinc-900 bg-[#0a0a0a] rounded p-6 markdown-body">
           <h3 className="font-serif text-sm font-black tracking-widest text-[#eae5db] uppercase mb-4 flex items-center gap-2 border-b border-zinc-900 pb-2">
             <Target className="w-4 h-4 text-amber-500" />
             AI 教练深度赛评
           </h3>
           <div className="prose prose-invert prose-sm max-w-none text-zinc-300 font-sans leading-relaxed prose-headings:font-serif prose-headings:font-bold prose-headings:tracking-wide prose-strong:text-amber-500/90 prose-a:text-blue-400">
             <ReactMarkdown>{reportMarkdown}</ReactMarkdown>
           </div>
        </div>
      </div>

    </div>
  );
}
