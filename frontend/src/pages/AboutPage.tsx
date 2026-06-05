import { fetchPage } from "../api/client";
import SiteShell from "../layout/SiteShell";
import PageHero from "../components/ui/PageHero";
import GlassPanel from "../components/ui/GlassPanel";
import { PageError, PageLoading } from "../components/ui/PageStates";
import { usePageData } from "../hooks/usePageData";

interface ContentSection {
  heading: string;
  body: string;
}

interface AboutPageData {
  title: string;
  summary: string;
  sections: ContentSection[];
  tech_stack: string[];
}

export default function AboutPage() {
  const { data, loading, error } = usePageData(() => fetchPage<AboutPageData>("/pages/about"));

  return (
    <SiteShell>
      {loading && <PageLoading />}
      {error && <PageError message={error} />}
      {data && (
        <>
          <PageHero title={data.title} subtitle={data.summary} eyebrow="关于" />
          <div className="grid gap-4 lg:grid-cols-2">
            {data.sections.map((section) => (
              <GlassPanel key={section.heading} title={section.heading}>
                <p className="whitespace-pre-wrap font-mono text-[11px] leading-relaxed text-zinc-400">
                  {section.body}
                </p>
              </GlassPanel>
            ))}
            {data.tech_stack.length > 0 && (
              <GlassPanel title="技术栈">
                <div className="flex flex-wrap gap-2">
                  {data.tech_stack.map((t) => (
                    <span
                      key={t}
                      className="rounded border border-zinc-800 bg-zinc-950/60 px-2 py-1 font-mono text-[10px] text-zinc-400"
                    >
                      {t}
                    </span>
                  ))}
                </div>
              </GlassPanel>
            )}
          </div>
        </>
      )}
    </SiteShell>
  );
}
