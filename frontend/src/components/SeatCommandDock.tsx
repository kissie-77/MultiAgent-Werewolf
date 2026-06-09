import React, { useEffect, useRef, useState } from "react";
import { useGameStore } from "../store";
import { soundManager } from "../audio/soundManager";
import { remainingSeconds } from "../lib/countdown";
import type { HumanInputSelection } from "../lib/humanInput";

/**
 * Persistent bottom command dock for the human seat view. Always mounted; morphs
 * by pendingInput.kind. Replaces the old HumanInputPanel raw-prompt modal.
 * Selection is mirrored through store.selectedTargetSeat (also reflected in the
 * left CardDeck sidebar and the 3D board pillar glow).
 */
export default function SeatCommandDock() {
  const pendingInput = useGameStore((s) => s.pendingInput);
  const submitHumanInput = useGameStore((s) => s.submitHumanInput);
  const humanInputError = useGameStore((s) => s.humanInputError);
  const clearHumanInputError = useGameStore((s) => s.clearHumanInputError);
  const selected = useGameStore((s) => s.selectedTargetSeat);
  const setSelected = useGameStore((s) => s.setSelectedTargetSeat);
  const players = useGameStore((s) => s.state?.players ?? []);
  const liveCue = useGameStore((s) => s.state?.liveCue ?? null);

  const [submitting, setSubmitting] = useState(false);
  const [multiSel, setMultiSel] = useState<number[]>([]);
  const [speech, setSpeech] = useState("");
  const [startedAtMs, setStartedAtMs] = useState(() => Date.now());
  const [nowMs, setNowMs] = useState(() => Date.now());

  const requestId = pendingInput?.request_id;
  const deadlineSec = pendingInput?.deadline ?? 0;

  useEffect(() => {
    setMultiSel([]);
    setSpeech("");
    setSubmitting(false);
    const t = Date.now();
    setStartedAtMs(t);
    setNowMs(t);
  }, [requestId]);

  useEffect(() => {
    if (!deadlineSec || deadlineSec <= 0) return;
    const id = setInterval(() => setNowMs(Date.now()), 500);
    return () => clearInterval(id);
  }, [requestId, deadlineSec]);

  const remaining = remainingSeconds(deadlineSec, startedAtMs, nowMs);

  const prevRemainingRef = useRef<number>(remaining);
  useEffect(() => {
    if (remaining !== prevRemainingRef.current) {
      if (remaining > 0 && remaining <= 10) soundManager.playUi("ui_tick");
      prevRemainingRef.current = remaining;
    }
  }, [remaining]);

  const expired = deadlineSec > 0 && remaining <= 0;
  const locked = submitting || expired;

  const nameOf = (seat: number) =>
    players.find((p) => p.id === seat)?.name ?? `P${seat}`;
  const isAlive = (seat: number) =>
    players.find((p) => p.id === seat)?.isAlive ?? true;

  const targets = pendingInput?.valid_targets ?? [];
  const targetMeta = pendingInput?.target_meta ?? [];
  const labelFor = (seat: number) =>
    targetMeta.find((m) => m.seat === seat)?.name ?? nameOf(seat);

  const submit = async (sel: HumanInputSelection) => {
    if (locked) return;
    setSubmitting(true);
    try {
      await submitHumanInput(sel);
    } finally {
      setSubmitting(false);
    }
  };

  const toggleMulti = (seat: number) =>
    setMultiSel((prev) =>
      prev.includes(seat) ? prev.filter((s) => s !== seat) : [...prev, seat]
    );

  const idleLabel = (() => {
    const ns = liveCue?.nightSkill;
    if (ns) return `${ns.playerName}（${ns.seat}号）夜间行动中…`;
    if (liveCue?.thinking) return `${liveCue.thinking.playerName}（${liveCue.thinking.seat}号）思考中…`;
    return "等待其他玩家行动…";
  })();

  const TargetCard = ({ seat, active, onClick }: { seat: number; active: boolean; onClick: () => void }) => (
    <button
      type="button"
      disabled={locked || !isAlive(seat)}
      onClick={onClick}
      className={`relative flex flex-col items-center gap-1 w-[68px] shrink-0 rounded-lg border-2 p-1.5 transition-all cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed ${
        active
          ? "border-amber-400 bg-amber-500/15 shadow-[0_0_16px_rgba(245,158,11,0.4)] scale-105"
          : "border-zinc-700 bg-black/40 hover:border-amber-600/60"
      }`}
    >
      <span className="font-serif text-lg font-black leading-none text-amber-200">{seat}</span>
      <span className="font-sans text-[10px] text-zinc-300 truncate w-full text-center">{labelFor(seat)}</span>
    </button>
  );

  return (
    <div className="absolute inset-x-0 bottom-0 z-[110] px-4 pb-4 pointer-events-none">
      <div className="mx-auto max-w-3xl pointer-events-auto bg-slate-950/92 bg-woodcut-dark border border-amber-700/50 rounded-xl shadow-[0_-8px_40px_rgba(0,0,0,0.7)] p-4 backdrop-blur-md">
        <div className="flex items-center justify-between gap-3 mb-3 border-b border-amber-900/40 pb-2">
          <span className="font-serif text-sm font-black text-amber-400 tracking-wide truncate">
            {pendingInput ? (pendingInput.question || pendingInput.title || "轮到你了") : idleLabel}
          </span>
          {pendingInput && deadlineSec > 0 && (
            <span
              className={`font-mono text-[11px] font-bold tabular-nums px-2 py-0.5 rounded border shrink-0 ${
                expired || remaining <= 10
                  ? "text-rose-300 border-rose-700/60 bg-rose-950/40 animate-pulse"
                  : "text-amber-300 border-amber-800/50 bg-amber-950/30"
              }`}
            >
              {expired ? "已超时" : `${remaining}s`}
            </span>
          )}
        </div>

        {humanInputError && (
          <div className="mb-3 px-3 py-2 rounded border border-rose-800/60 bg-rose-950/40 text-[11px] font-mono text-rose-200 flex items-center justify-between gap-2">
            <span>{humanInputError}</span>
            <button type="button" onClick={() => { soundManager.playUi("ui_panel_close"); clearHumanInputError(); }} className="underline shrink-0">关闭</button>
          </div>
        )}

        {!pendingInput && (
          <div className="flex items-center gap-2 text-zinc-500 font-mono text-[11px] py-1">
            <span className="flex gap-1">
              <span className="w-1.5 h-1.5 bg-amber-500/70 rounded-full animate-bounce" />
              <span className="w-1.5 h-1.5 bg-amber-500/70 rounded-full animate-bounce [animation-delay:120ms]" />
              <span className="w-1.5 h-1.5 bg-amber-500/70 rounded-full animate-bounce [animation-delay:240ms]" />
            </span>
            {idleLabel}
          </div>
        )}

        {pendingInput?.kind === "seat" && (
          <div className="flex flex-col gap-3">
            <div className="flex gap-2 overflow-x-auto pb-1">
              {targets.map((seat) => (
                <TargetCard key={seat} seat={seat} active={selected === seat} onClick={() => { soundManager.playUi("ui_click"); setSelected(selected === seat ? null : seat); }} />
              ))}
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                disabled={locked || selected == null}
                onClick={() => submit({ kind: "seat", seat: selected ?? undefined })}
                className="px-4 py-2 rounded border border-amber-600/70 text-xs font-bold text-amber-200 bg-amber-900/30 hover:bg-amber-800/40 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
              >
                确认目标{selected != null ? ` · ${selected}号` : ""}
              </button>
              {pendingInput.allow_skip !== false && (
                <button
                  type="button"
                  disabled={locked}
                  onClick={() => submit({ kind: "seat", skip: true })}
                  className="px-3 py-2 rounded border border-zinc-700 text-[11px] font-bold text-zinc-400 hover:text-zinc-200 cursor-pointer disabled:opacity-40"
                >
                  弃票 / 跳过
                </button>
              )}
            </div>
          </div>
        )}

        {pendingInput?.kind === "witch" && (
          <div className="flex flex-col gap-3">
            <div className="flex flex-wrap gap-2">
              {pendingInput.allow_witch_save !== false && (
                <button type="button" disabled={locked} onClick={() => submit({ kind: "witch", action: "save" })}
                  className="px-4 py-2 rounded border border-emerald-600/70 text-xs font-bold text-emerald-200 bg-emerald-900/25 hover:bg-emerald-800/40 cursor-pointer disabled:opacity-40">
                  使用解药
                </button>
              )}
              <button type="button" disabled={locked} onClick={() => submit({ kind: "witch", action: "none" })}
                className="px-4 py-2 rounded border border-zinc-700 text-xs font-bold text-zinc-300 hover:bg-zinc-800/40 cursor-pointer disabled:opacity-40">
                不行动
              </button>
            </div>
            {targets.length > 0 && (
              <div className="flex flex-col gap-2 border-t border-amber-900/30 pt-2">
                <span className="font-mono text-[10px] text-purple-300/80 uppercase tracking-widest">毒药目标</span>
                <div className="flex gap-2 overflow-x-auto pb-1">
                  {targets.map((seat) => (
                    <TargetCard key={seat} seat={seat} active={selected === seat} onClick={() => { soundManager.playUi("ui_click"); setSelected(selected === seat ? null : seat); }} />
                  ))}
                </div>
                <button type="button" disabled={locked || selected == null}
                  onClick={() => submit({ kind: "witch", action: "poison", seat: selected ?? undefined })}
                  className="self-start px-4 py-2 rounded border border-purple-600/70 text-xs font-bold text-purple-200 bg-purple-900/25 hover:bg-purple-800/40 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed">
                  确认施毒{selected != null ? ` · ${selected}号` : ""}
                </button>
              </div>
            )}
          </div>
        )}

        {pendingInput?.kind === "yesno" && (
          <div className="flex gap-3">
            <button type="button" disabled={locked} onClick={() => submit({ kind: "yesno", yes: true })}
              className="flex-1 px-4 py-2.5 rounded border border-amber-600/70 text-sm font-bold text-amber-200 bg-amber-900/30 hover:bg-amber-800/40 cursor-pointer disabled:opacity-40">
              是 · Yes
            </button>
            <button type="button" disabled={locked} onClick={() => submit({ kind: "yesno", yes: false })}
              className="flex-1 px-4 py-2.5 rounded border border-zinc-700 text-sm font-bold text-zinc-300 hover:bg-zinc-800/40 cursor-pointer disabled:opacity-40">
              否 · No
            </button>
          </div>
        )}

        {pendingInput?.kind === "multi" && (
          <div className="flex flex-col gap-3">
            {(pendingInput.multi_count ?? 0) > 0 && (
              <span className="font-mono text-[10px] text-zinc-500">需选择 {pendingInput.multi_count} 个不同座位</span>
            )}
            <div className="flex gap-2 overflow-x-auto pb-1">
              {targets.map((seat) => (
                <TargetCard key={seat} seat={seat} active={multiSel.includes(seat)} onClick={() => { soundManager.playUi("ui_click"); toggleMulti(seat); }} />
              ))}
            </div>
            <button type="button"
              disabled={locked || ((pendingInput.multi_count ?? 0) > 0 && multiSel.length !== pendingInput.multi_count)}
              onClick={() => submit({ kind: "multi", seats: multiSel })}
              className="self-start px-4 py-2 rounded border border-amber-600/70 text-xs font-bold text-amber-200 bg-amber-900/30 hover:bg-amber-800/40 cursor-pointer disabled:opacity-40">
              确认提交
            </button>
          </div>
        )}

        {pendingInput?.kind === "speech" && (
          <div className="flex flex-col gap-2">
            <textarea
              value={speech}
              onChange={(e) => setSpeech(e.target.value)}
              rows={3}
              placeholder="在此输入你的发言（完整中文，至少 15 字）…"
              className="w-full bg-black/60 border border-slate-700 focus:border-amber-500/60 rounded p-3 text-sm text-amber-100 outline-none resize-none placeholder:text-slate-600"
            />
            <button type="button" disabled={locked || speech.trim().length < 15}
              onClick={() => submit({ kind: "speech", text: speech.trim() })}
              className="self-end px-5 py-2 rounded border border-amber-600/70 text-xs font-bold text-amber-200 bg-amber-900/30 hover:bg-amber-800/40 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed">
              提交发言
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
