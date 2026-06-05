import { fetchPage } from "../api/client";
import SiteShell from "../layout/SiteShell";
import PageHero from "../components/ui/PageHero";
import GlassPanel from "../components/ui/GlassPanel";
import { PageError, PageLoading } from "../components/ui/PageStates";
import { usePageData } from "../hooks/usePageData";

interface RoleListItem {
  key: string;
  display_name: string;
  camp: string;
  camp_label: string;
  victory_goal: string;
}

interface RolesPageData {
  title: string;
  camps: Record<string, RoleListItem[]>;
  camp_stats: Record<string, number>;
  total: number;
}

export default function RolesPage() {
  const { data, loading, error } = usePageData(() => fetchPage<RolesPageData>("/pages/roles"));

  return (
    <SiteShell>
      {loading && <PageLoading />}
      {error && <PageError message={error} />}
      {data && (
        <>
          <PageHero title={data.title} subtitle={`共 ${data.total} 种角色`} eyebrow="角色图鉴" />
          <div className="mb-6 flex flex-wrap justify-center gap-2">
            {Object.entries(data.camp_stats).map(([camp, count]) => (
              <span
                key={camp}
                className="rounded border border-zinc-800 px-3 py-1 font-mono text-[10px] text-zinc-400"
              >
                {camp} × {count}
              </span>
            ))}
          </div>
          {Object.entries(data.camps).map(([camp, roles]) => (
            <div key={camp} className="mb-8">
              <h2 className="mb-3 font-serif text-sm font-black uppercase tracking-widest text-zinc-300">
                {camp}
              </h2>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {roles.map((role) => (
                  <GlassPanel key={role.key} title={role.display_name}>
                    <div className="mb-2 font-mono text-[9px] uppercase tracking-wider text-yellow-500/80">
                      {role.camp_label}
                    </div>
                    <p className="font-mono text-[10px] leading-relaxed text-zinc-500">{role.victory_goal}</p>
                  </GlassPanel>
                ))}
              </div>
            </div>
          ))}
        </>
      )}
    </SiteShell>
  );
}
