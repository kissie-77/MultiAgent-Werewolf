import { Link } from "react-router-dom";
import SiteShell from "../layout/SiteShell";
import PageHero from "../components/ui/PageHero";

interface PlaceholderPageProps {
  title: string;
  eyebrow?: string;
}

export default function PlaceholderPage({ title, eyebrow }: PlaceholderPageProps) {
  return (
    <SiteShell>
      <PageHero eyebrow={eyebrow} title={title} subtitle="页面开发中，风格将与启动页保持一致。">
        <Link
          to="/"
          className="rounded border border-zinc-800 bg-black/50 px-5 py-2 font-mono text-[10px] font-bold uppercase tracking-widest text-yellow-400 hover:bg-zinc-900"
        >
          返回启动页
        </Link>
      </PageHero>
    </SiteShell>
  );
}
