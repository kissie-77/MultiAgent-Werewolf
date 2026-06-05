import { fetchPage } from "../api/client";
import SiteShell from "../layout/SiteShell";
import PageHero from "../components/ui/PageHero";
import GlassPanel from "../components/ui/GlassPanel";
import { PageError, PageLoading } from "../components/ui/PageStates";
import { usePageData } from "../hooks/usePageData";

interface StrategyTip {
  title: string;
  content: string;
  tags: string[];
}

interface StrategyPageData {
  title: string;
  general_tips: StrategyTip[];
  role_tips: StrategyTip[];
}

function TipGrid({ tips }: { tips: StrategyTip[] }) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {tips.map((tip) => (
        <GlassPanel key={tip.title} title={tip.title}>
          <p className="mb-2 font-mono text-[11px] leading-relaxed text-zinc-400">{tip.content}</p>
          {tip.tags.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {tip.tags.map((tag) => (
                <span
                  key={tag}
                  className="rounded bg-purple-950/40 px-1.5 py-0.5 font-mono text-[8px] uppercase text-purple-300"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}
        </GlassPanel>
      ))}
    </div>
  );
}

export default function StrategyPage() {
  const { data, loading, error } = usePageData(() => fetchPage<StrategyPageData>("/pages/strategy"));

  return (
    <SiteShell>
      {loading && <PageLoading />}
      {error && <PageError message={error} />}
      {data && (
        <>
          <PageHero title={data.title} eyebrow="攻略" />
          {data.general_tips.length > 0 && (
            <section className="mb-8">
              <h2 className="mb-4 font-serif text-sm font-black uppercase tracking-widest text-zinc-400">
                通用策略
              </h2>
              <TipGrid tips={data.general_tips} />
            </section>
          )}
          {data.role_tips.length > 0 && (
            <section>
              <h2 className="mb-4 font-serif text-sm font-black uppercase tracking-widest text-zinc-400">
                角色策略
              </h2>
              <TipGrid tips={data.role_tips} />
            </section>
          )}
        </>
      )}
    </SiteShell>
  );
}
