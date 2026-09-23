import type { Metadata } from "next";
import "./globals.css";
import Link from "next/link";
import {
  Layers,
  Activity,
  ShieldCheck,
  TrendingDown,
  ClipboardCheck,
  Trophy,
  Github,
  Zap,
} from "lucide-react";

export const metadata: Metadata = {
  title: "EvoEval: Agent Evolution & Safety Drift Benchmark",
  description: "Measuring Safety Drift, Retention, and Proxy Reward Hacking in Self-Evolving Code Agents",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const navItems = [
    { href: "/", label: "Runs Overview", icon: Layers },
    { href: "/drift", label: "Drift Explorer", icon: Activity },
    { href: "/leaderboard", label: "Group Leaderboard", icon: Trophy },
    { href: "/audit", label: "Audit Workbench", icon: ClipboardCheck },
  ];

  return (
    <html lang="en" className="dark">
      <body className="bg-background text-slate-100 flex min-h-screen">
        {/* Sidebar Nav */}
        <aside className="w-64 border-r border-surface-border bg-surface/50 flex flex-col justify-between shrink-0 hidden md:flex p-5">
          <div>
            {/* Logo / Branding */}
            <div className="flex items-center gap-2.5 pb-6 border-b border-surface-border mb-6">
              <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-pink-500 flex items-center justify-center text-white shadow-lg shadow-indigo-500/20">
                <Zap size={20} className="fill-white" />
              </div>
              <div>
                <h1 className="font-extrabold text-base tracking-tight text-white flex items-center gap-1.5">
                  EvoEval <span className="text-[10px] uppercase font-bold px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">v0.1</span>
                </h1>
                <p className="text-[11px] text-slate-400 font-medium">Safety Drift Benchmark</p>
              </div>
            </div>

            {/* Navigation Links */}
            <nav className="space-y-1.5">
              {navItems.map((item) => {
                const Icon = item.icon;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-semibold text-slate-300 hover:text-white hover:bg-surface-card transition-all"
                  >
                    <Icon size={18} className="text-slate-400 group-hover:text-indigo-400" />
                    {item.label}
                  </Link>
                );
              })}
            </nav>
          </div>

          {/* Footer info */}
          <div className="pt-4 border-t border-surface-border text-xs text-slate-400 space-y-2">
            <div className="flex items-center justify-between">
              <span>Taxonomy:</span>
              <span className="font-mono text-indigo-400 font-bold">G1 – G6</span>
            </div>
            <div className="flex items-center justify-between">
              <span>Benchmark:</span>
              <span className="font-mono text-slate-300">100 Tasks</span>
            </div>
            <div className="pt-2 text-[11px] text-slate-400">
              NeurIPS 2024 Evaluation Framework
            </div>
          </div>
        </aside>

        {/* Main Content Area */}
        <main className="flex-1 flex flex-col min-w-0 overflow-y-auto">
          <header className="h-16 border-b border-surface-border bg-surface/30 backdrop-blur-md px-6 flex items-center justify-between shrink-0">
            <div className="flex items-center gap-3">
              <span className="text-xs uppercase font-mono tracking-wider text-slate-400">
                Evaluation Environment:
              </span>
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Active Local Jail & Sandbox
              </span>
            </div>

            <div className="flex items-center gap-3">
              <span className="text-xs font-mono text-slate-400">Backend API :8000</span>
              <div className="h-4 w-px bg-surface-border" />
              <a
                href="https://github.com/evoeval/evoeval"
                target="_blank"
                rel="noreferrer"
                className="text-xs text-slate-400 hover:text-white flex items-center gap-1.5 font-medium transition-colors"
              >
                <Github size={15} /> Docs
              </a>
            </div>
          </header>

          <div className="p-6 md:p-8 max-w-7xl mx-auto w-full space-y-8">
            {children}
          </div>
        </main>
      </body>
    </html>
  );
}
