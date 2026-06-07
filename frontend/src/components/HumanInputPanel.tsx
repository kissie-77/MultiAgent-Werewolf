import React, { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion } from "motion/react";
import { useGameStore } from "../store";
import type { HumanInputSelection } from "../lib/humanInput";

/**
 * Seat-view human decision panel. Driven entirely by `pendingInput` (the
 * `awaiting_input` bridge event captured in the store). Renders a control set
 * keyed by `pendingInput.kind`, folds the choice into a normalized payload via
 * `submitHumanInput`, and disappears once the request resolves.
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

  // Reset transient choices whenever a fresh request arrives.
  useEffect(() => {
    setPoisonTarget(null);
    setMultiSel([]);
    setSpeech("");
    setSubmitting(false);
    clearHumanInputError();
  }, [pendingInput?.request_id, clearHumanInputError]);

  if (!pendingInput) return null;

  const targets = pendingInput.valid_targets ?? [];

  const submit = async (selection: HumanInputSelection) => {
    if (submitting) return;
    setSubmitting(true);
    try {
      const result = await submitHumanInput(selection);
      if (!result.ok) {
        setSubmitting(false);
      }
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
      >
        <div className="relative bg-slate-950/95 bg-woodcut-dark border border-amber-700/50 rounded-xl shadow-[0_0_50px_rgba(0,0,0,0.8)] p-5 backdrop-blur-md">
          <div className="absolute top-2 left-2 w-3 h-3 border-t border-l border-amber-600/40" />
          <div className="absolute top-2 right-2 w-3 h-3 border-t border-r border-amber-600/40" />
          <div className="absolute bottom-2 left-2 w-3 h-3 border-b border-l border-amber-600/40" />
          <div className="absolute bottom-2 right-2 w-3 h-3 border-b border-r border-amber-600/40" />

          <div className="flex items-center justify-between mb-3 border-b border-amber-900/40 pb-2">
            <span className="font-serif text-sm font-black text-amber-500 uppercase tracking-widest drop-shadow">
              轮到你了 · Your Move
            </span>
            <span className="font-mono text-[10px] text-slate-500">座位 {pendingInput.seat}</span>
          </div>

          <p className="text-[12px] text-amber-100/90 leading-relaxed font-serif whitespace-pre-line mb-4">
            {pendingInput.prompt}
          </p>

          {humanInputError && (
            <p className="mb-3 px-3 py-2 rounded border border-red-500/40 bg-red-950/40 text-[11px] text-red-300 font-sans leading-relaxed">
              {humanInputError}
            </p>
          )}

          {/* seat: pick one target (or abstain) */}
          {pendingInput.kind === "seat" && (
            <div className="flex flex-col gap-3">
              <div className="flex flex-wrap gap-2">
                {targets.map((seat) => (
                  <button
                    key={seat}
                    type="button"
                    disabled={submitting}
                    onClick={() => submit({ kind: "seat", seat })}
                    className={`${seatBtn} ${seatBtnIdle}`}
                  >
                    {seat} 号
                  </button>
                ))}
              </div>
              <button
                type="button"
                disabled={submitting}
                onClick={() => submit({ kind: "seat", skip: true })}
                className="self-start px-3 py-1.5 rounded border border-slate-700 text-[11px] font-bold text-slate-400 hover:text-slate-200 hover:border-slate-500 transition-all cursor-pointer disabled:opacity-40"
              >
                弃票 / 跳过
              </button>
            </div>
          )}

          {/* witch: save / poison(target) / none */}
          {pendingInput.kind === "witch" && (
            <div className="flex flex-col gap-3">
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  disabled={submitting}
                  onClick={() => submit({ kind: "witch", action: "save" })}
                  className={`${seatBtn} ${seatBtnIdle}`}
                >
                  解药 · 救
                </button>
                <button
                  type="button"
                  disabled={submitting}
                  onClick={() => submit({ kind: "witch", action: "none" })}
                  className={`${seatBtn} ${seatBtnIdle}`}
                >
                  不行动
                </button>
              </div>
              <div className="flex flex-col gap-2 border-t border-amber-900/30 pt-3">
                <span className="font-mono text-[10px] text-purple-300/80 uppercase tracking-widest">
                  毒药目标 · Poison
                </span>
                <div className="flex flex-wrap gap-2">
                  {targets.map((seat) => (
                    <button
                      key={seat}
                      type="button"
                      disabled={submitting}
                      onClick={() => setPoisonTarget(seat)}
                      className={`${seatBtn} ${poisonTarget === seat ? seatBtnActive : seatBtnIdle}`}
                    >
                      {seat} 号
                    </button>
                  ))}
                </div>
                <button
                  type="button"
                  disabled={submitting || poisonTarget == null}
                  onClick={() => submit({ kind: "witch", action: "poison", seat: poisonTarget ?? undefined })}
                  className="self-start px-3 py-1.5 rounded border border-purple-600/60 text-[11px] font-bold text-purple-300 hover:bg-purple-900/30 transition-all cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  施毒
                </button>
              </div>
            </div>
          )}

          {/* yesno: 是 / 否 */}
          {pendingInput.kind === "yesno" && (
            <div className="flex gap-3">
              <button
                type="button"
                disabled={submitting}
                onClick={() => submit({ kind: "yesno", yes: true })}
                className={`${seatBtn} ${seatBtnIdle} flex-1`}
              >
                是 · Yes
              </button>
              <button
                type="button"
                disabled={submitting}
                onClick={() => submit({ kind: "yesno", yes: false })}
                className={`${seatBtn} ${seatBtnIdle} flex-1`}
              >
                否 · No
              </button>
            </div>
          )}

          {/* multi: pick several, then confirm */}
          {pendingInput.kind === "multi" && (
            <div className="flex flex-col gap-3">
              <div className="flex flex-wrap gap-2">
                {targets.map((seat) => (
                  <button
                    key={seat}
                    type="button"
                    disabled={submitting}
                    onClick={() => toggleMulti(seat)}
                    className={`${seatBtn} ${multiSel.includes(seat) ? seatBtnActive : seatBtnIdle}`}
                  >
                    {seat} 号
                  </button>
                ))}
              </div>
              <button
                type="button"
                disabled={submitting}
                onClick={() => submit({ kind: "multi", seats: multiSel })}
                className="self-start px-3 py-1.5 rounded border border-amber-600/60 text-[11px] font-bold text-amber-300 hover:bg-amber-900/30 transition-all cursor-pointer disabled:opacity-40"
              >
                确认提交
              </button>
            </div>
          )}

          {/* speech: free text */}
          {pendingInput.kind === "speech" && (
            <div className="flex flex-col gap-3">
              <textarea
                value={speech}
                onChange={(e) => setSpeech(e.target.value)}
                rows={3}
                placeholder="输入你的发言..."
                className="w-full bg-black/60 border border-slate-700 focus:border-amber-500/60 rounded p-3 text-sm text-amber-100 outline-none resize-none placeholder:text-slate-600"
              />
              <button
                type="button"
                disabled={submitting || speech.trim().length === 0}
                onClick={() => submit({ kind: "speech", text: speech.trim() })}
                className="self-end px-4 py-2 rounded border border-amber-600/60 text-[11px] font-bold text-amber-300 hover:bg-amber-900/30 transition-all cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
              >
                发言
              </button>
            </div>
          )}
        </div>
      </motion.div>
    </AnimatePresence>,
    document.body
  );
}
