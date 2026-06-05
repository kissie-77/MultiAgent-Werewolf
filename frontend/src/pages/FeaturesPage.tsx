import { fetchPage } from "../api/client";
import SiteShell from "../layout/SiteShell";
import PageHero from "../components/ui/PageHero";
import GlassPanel from "../components/ui/GlassPanel";
import { PageError, PageLoading } from "../components/ui/PageStates";
import { usePageData } from "../hooks/usePageData";

interface FeatureCard {
  key: string;
  title: string;
  description: string;
  bullets: string[];
}

interface FeaturesPageData {
  title: string;
  summary: string;
  feature_cards: FeatureCard[];
}

export default function FeaturesPage() {
  const { data, loading, error } = usePageData(() => fetchPage<FeaturesPageData>("/pages/features"));

  return (
    <SiteShell>
      {loading && <PageLoading />}
      {error && <PageError message={error} />}
      {data && (
        <>
          <PageHero title={data.title} subtitle={data.summary} eyebrow="平台能力" />
          <div className="grid gap-4 md:grid-cols-2">
            {data.feature_cards.map((card) => (
              <GlassPanel key={card.key} title={card.title}>
                <p className="mb-3 font-mono text-[11px] text-zinc-400">{card.description}</p>
                <ul className="space-y-1 font-mono text-[10px] text-zinc-500">
                  {card.bullets.map((b) => (
                    <li key={b}>· {b}</li>
                  ))}
                </ul>
              </GlassPanel>
            ))}
          </div>
        </>
      )}
    </SiteShell>
  );
}
