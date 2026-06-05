import GlassPanel from "./GlassPanel";

export function PageLoading({ label = "召唤宿命之光..." }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-24 font-mono text-xs uppercase tracking-widest text-zinc-500">
      <div className="h-6 w-6 animate-spin rounded-full border-2 border-zinc-800 border-t-yellow-500" />
      <span>{label}</span>
    </div>
  );
}

export function PageError({ message }: { message: string }) {
  return (
    <GlassPanel title="⚠ 法阵断裂" className="mx-auto max-w-lg text-center">
      <p className="font-mono text-xs text-red-400">{message}</p>
      <p className="mt-3 font-mono text-[10px] text-zinc-500">
        请确认 werewolf-api 已在 8000 端口运行，或稍后重试。
      </p>
    </GlassPanel>
  );
}
