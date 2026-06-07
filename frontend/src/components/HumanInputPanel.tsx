import React, { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion } from "motion/react";
import { useGameStore } from "../store";
import type { HumanInputSelection } from "../lib/humanInput";
import { remainingSeconds } from "../lib/countdown";
import { hintForInput, titleForInput } from "../lib/humanPrompt";

/**
 * Seat-view human decision panel. Driven by `pendingInput` (awaiting_input SSE).
 * Shows sanitized prompts from the backend — never raw LLM observation text.
 */
export default function HumanInputPanel() {
  const pendingInput = useGameStore((s) => s.pendingInput);
  const submitHumanInput = useGameStore((s) => s.submitHumanInput);
  const humanInputError = useGameStore((s) => s.humanInputError);
  const clearHumanInputError = useGameStore((s) => s.clearHumanInputError);

  const [submitting, setSubmitting] = useState(false);
  const [poisonTarget, setPoisonTarget] = useState<number | null>(null);
  const [multiSel, setMultiSel] = useState<number[]>([]);
  const [speech, setSpeech] = useState("");
  const [startedAtMs, setStartedAtMs] = useState<number>(() => Date.now());
  const [nowMs, setNowMs] = useState<number>(() => Date.now());

  const requestId = pendingInput?.request_id;
  const deadlineSec = pendingInput?.deadline ?? 0;

  useEffect(() => {
    setPoisonTarget(null);
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

  if (!pendingInput) return null;

  const targets = pendingInput.valid_targets ?? [];
  const remaining = remainingSeconds(deadlineSec, startedAtMs, nowMs);
  const expired = deadlineSec > 0 && remaining <= 0;
  const locked = submitting || expired;
  const title = titleForInput(pendingInput);
  const hint = hintForInput(pendingInput);
  const canSave = pendingInput.allow_witch_save !== false;
  const multiNeed = pendingInput.multi_count ?? 0;

  const submit = async (selection: HumanInputSelection) => {
    if (locked) return;
    setSubmitting(true);
    try {
      await submitHumanInput(selection);
    } finally {
      setSubmitting(false);
    }
  };

  const toggleMulti = (seat: number) => {
    setMultiSel((prev) =>
      prev.includes(seat) ? prev.filter((s) => s !== seat) : [...prev, seat]
    );
  };

  const seatBtn =
    "px-3 py-2 rounded border text-sm font-mono font-bold transition-all cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed";
  const seatBtnIdle =
    "bg-black/40 border-slate-700 text-slate-300 hover:border-amber-500/60 hover:text-amber-300 hover:bg-amber-900/20";
  const seatBtnActive =
    "bg-amber-500/20 border-amber-500/70 text-amber-300 shadow-[0_0_10px_rgba(245,158,11,0.2)]";

  return createPortal(
    <AnimatePresence>
      <motion.div
        key={pendingInput.request_id}
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: 24 }}
        transition={{ duration: 0.25, ease: "easeOut" }}
        className="fixed bottom-6 left-1/2 -translate-x-1/2 z-[120] w-full max-w-lg px-4"
        role="dialog"
        aria-label={title}
      >
        <div className="relative bg-slate-950/95 bg-woodcut-dark border border-amber-700/50 rounded-xl shadow-[0_0_50px_rgba(0,0,0,0.8)] p-5 backdrop-blur-md">
          <div className="absolute top-2 left-2 w-3 h-3 border-t border-l border-amber-600/40" />
          <div className="absolute top-2 right-2 w-3 h-3 border-t border-r border-amber-600/40" />
          <div className="absolute bottom-2 left-2 w-3 h-3 border-b border-l border-amber-600/40" />
          <div className="absolute bottom-2 right-2 w-3 h-3 border-b border-r border-amber-600/40" />

          <div className="flex items-center justify-between mb-2 border-b border-amber-900/40 pb-2">
            <span className="font-serif text-sm font-black text-amber-500 tracking-widest drop-shadow">
              {title}
            </span>
            <div className="flex items-center gap-3">
              {deadlineSec > 0 && (
                <span
                  className={`font-mono text-[11px] font-bold tabular-nums px-2 py-0.5 rounded border ${
                    expired
                      ? "text-rose-300 border-rose-700/60 bg-rose-950/40"
                      : remaining <= 10
                        ? "text-rose-300 border-rose-700/60 bg-rose-950/40 animate-pulse"
                        : "text-amber-300 border-amber-800/50 bg-amber-950/30"
                  }`}
                  aria-label="决策倒计时"
                >
                  {expired ? "已超时" : `${remaining}s`}
                </span>
              )}
            </div>
          </div>

          {hint && (
            <p className="text-[11px] text-amber-200/70 font-sans mb-3 leading-relaxed">
              {hint}
            </p>
          )}

          {pendingInput.prompt?.trim() && (
            <div className="mb-4 px-3 py-2.5 rounded border border-amber-900/30 bg-black/30">
              <p className="text-[10px] font-mono text-amber-600/80 uppercase tracking-widest mb-1.5">
                当前局势
              </p>
              <p className="text-[12px] text-amber-100/90 leading-relaxed font-serif whitespace-pre-line">
                {pendingInput.prompt}
              </p>
            </div>
          )}

          {humanInputError && (
            <div className="mb-4 px-3 py-2 rounded border border-rose-800/60 bg-rose-950/40 text-[11px] font-mono text-rose-200 flex items-center justify-between gap-2">
              <span>{humanInputError}</span>
              <button type="button" onClick={clearHumanInputError} className="text-rose-300 hover:text-white underline shrink-0">
                关闭
              </button>
            </div>
          )}

          {expired && (
            <div className="mb-4 px-3 py-2 rounded border border-rose-800/60 bg-rose-950/40 text-[11px] font-mono text-rose-200">
              决策超时，系统将按规则自动兜底，请稍候…
            </div>
          )}

          {submitting && (
            <div className="mb-4 px-3 py-2 rounded border border-amber-800/40 bg-amber-950/20 text-[11px] font-mono text-amber-200/90">
              已提交，等待裁定…
            </div>
          )}

          {pendingInput.kind === "seat" && (
            <div className="flex flex-col gap-3">
              <p className="text-[10px] font-mono text-zinc-500 uppercase tracking-widest">可选目标</p>
              <div className="flex flex-wrap gap-2">
                {targets.map((seat) => (
                  <button
                    key={seat}
                    type="button"
                    disabled={locked}
                    onClick={() => submit({ kind: "seat", seat })}
                    className={`${seatBtn} ${seatBtnIdle}`}
                  >
                    {seat} 号
                  </button>
                ))}
              </div>
              {pendingInput.allow_skip !== false && (
                <button
                  type="button"
                  disabled={locked}
                  onClick={() => submit({ kind: "seat", skip: true })}
                  className="self-start px-3 py-1.5 rounded border border-slate-700 text-[11px] font-bold text-slate-400 hover:text-slate-200 hover:border-slate-500 transition-all cursor-pointer disabled:opacity-40"
                >
                  弃票 / 跳过
                </button>
              )}
            </div>
          )}

          {pendingInput.kind === "witch" && (
            <div className="flex flex-col gap-3">
              <div className="flex flex-wrap gap-2">
                {canSave && (
                  <button
                    type="button"
                    disabled={locked}
                    onClick={() => submit({ kind: "witch", action: "save" })}
                    className={`${seatBtn} ${seatBtnIdle}`}
                  >
                    使用解药
                  </button>
                )}
                <button
                  type="button"
                  disabled={locked}
                  onClick={() => submit({ kind: "witch", action: "none" })}
                  className={`${seatBtn} ${seatBtnIdle}`}
                >
                  不行动
                </button>
              </div>
              {targets.length > 0 && (
                <div className="flex flex-col gap-2 border-t border-amber-900/30 pt-3">
                  <span className="font-mono text-[10px] text-purple-300/80 uppercase tracking-widest">
                    毒药目标
                  </span>
                  <div className="flex flex-wrap gap-2">
                    {targets.map((seat) => (
                      <button
                        key={seat}
                        type="button"
                        disabled={locked}
                        onClick={() => setPoisonTarget(seat)}
                        className={`${seatBtn} ${poisonTarget === seat ? seatBtnActive : seatBtnIdle}`}
                      >
                        {seat} 号
                      </button>
                    ))}
                  </div>
                  <button
                    type="button"
                    disabled={locked || poisonTarget == null}
                    onClick={() => submit({ kind: "witch", action: "poison", seat: poisonTarget ?? undefined })}
                    className="self-start px-3 py-1.5 rounded border border-purple-600/60 text-[11px] font-bold text-purple-300 hover:bg-purple-900/30 transition-all cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    确认施毒
                  </button>
                </div>
              )}
            </div>
          )}

          {pendingInput.kind === "yesno" && (
            <div className="flex gap-3">
              <button
                type="button"
                disabled={locked}
                onClick={() => submit({ kind: "yesno", yes: true })}
                className={`${seatBtn} ${seatBtnIdle} flex-1`}
              >
                是
              </button>
              <button
                type="button"
                disabled={locked}
                onClick={() => submit({ kind: "yesno", yes: false })}
                className={`${seatBtn} ${seatBtnIdle} flex-1`}
              >
                否
              </button>
            </div>
          )}

          {pendingInput.kind === "multi" && (
            <div className="flex flex-col gap-3">
              {multiNeed > 0 && (
                <p className="text-[10px] font-mono text-zinc-500">需选择 {multiNeed} 个不同座位</p>
              )}
              <div className="flex flex-wrap gap-2">
                {targets.map((seat) => (
                  <button
                    key={seat}
                    type="button"
                    disabled={locked}
                    onClick={() => toggleMulti(seat)}
                    className={`${seatBtn} ${multiSel.includes(seat) ? seatBtnActive : seatBtnIdle}`}
                  >
                    {seat} 号
                  </button>
                ))}
              </div>
              <button
                type="button"
                disabled={locked || (multiNeed > 0 && multiSel.length !== multiNeed)}
                onClick={() => submit({ kind: "multi", seats: multiSel })}
                className="self-start px-3 py-1.5 rounded border border-amber-600/60 text-[11px] font-bold text-amber-300 hover:bg-amber-900/30 transition-all cursor-pointer disabled:opacity-40"
              >
                确认提交
              </button>
            </div>
          )}

          {pendingInput.kind === "speech" && (
            <div className="flex flex-col gap-3">
              <textarea
                value={speech}
                onChange={(e) => setSpeech(e.target.value)}
                rows={4}
                placeholder="在此输入你的发言（完整中文，至少 15 字）…"
                className="w-full bg-black/60 border border-slate-700 focus:border-amber-500/60 rounded p-3 text-sm text-amber-100 outline-none resize-none placeholder:text-slate-600"
              />
              <button
                type="button"
                disabled={locked || speech.trim().length < 15}
                onClick={() => submit({ kind: "speech", text: speech.trim() })}
                className="self-end px-4 py-2 rounded border border-amber-600/60 text-[11px] font-bold text-amber-300 hover:bg-amber-900/30 transition-all cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
              >
                提交发言
              </button>
            </div>
          )}
        </div>
      </motion.div>
    </AnimatePresence>,
    document.body
  );
}
