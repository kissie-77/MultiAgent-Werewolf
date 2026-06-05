import { fetchPage } from "../api/client";
import SiteShell from "../layout/SiteShell";
import PageHero from "../components/ui/PageHero";
import GlassPanel from "../components/ui/GlassPanel";
import { PageError, PageLoading } from "../components/ui/PageStates";
import { usePageData } from "../hooks/usePageData";

interface PhaseFlowStep {
  order: number;
  title: string;
  description: string;
}

interface HowToPlayPageData {
  title: string;
  summary: string;
  phase_flow: PhaseFlowStep[];
}

export default function HowToPlayPage() {
  const { data, loading, error } = usePageData(() => fetchPage<HowToPlayPageData>("/pages/how-to-play"));

  return (
    <SiteShell>
      {loading && <PageLoading />}
      {error && <PageError message={error} />}
      {data && (
        <>
          <PageHero title={data.title} subtitle={data.summary} eyebrow="玩法" />
          <GlassPanel title="阶段流转">
            <ol className="space-y-4">
              {data.phase_flow.map((step) => (
                <li key={step.order} className="flex gap-4">
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded border border-yellow-500/30 bg-yellow-500/10 font-mono text-xs font-bold text-yellow-400">
                    {step.order}
                  </span>
                  <div>
                    <div className="font-serif text-sm font-bold text-zinc-200">{step.title}</div>
                    <p className="mt-1 font-mono text-[10px] text-zinc-500">{step.description}</p>
                  </div>
                </li>
              ))}
            </ol>
          </GlassPanel>
        </>
      )}
    </SiteShell>
  );
}
