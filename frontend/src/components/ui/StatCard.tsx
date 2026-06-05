interface StatCardProps {
  label: string;
  value: string | number;
  unit?: string | null;
  hint?: string | null;
}

export default function StatCard({ label, value, unit, hint }: StatCardProps) {
  return (
    <div className="rounded border border-zinc-800/70 bg-zinc-950/60 p-4 text-center">
      <div className="font-mono text-[9px] uppercase tracking-widest text-zinc-500">{label}</div>
      <div className="mt-2 font-serif text-2xl font-black text-yellow-400">
        {value}
        {unit && <span className="ml-1 text-sm text-zinc-400">{unit}</span>}
      </div>
      {hint && <div className="mt-1 font-mono text-[9px] text-zinc-600">{hint}</div>}
    </div>
  );
}
