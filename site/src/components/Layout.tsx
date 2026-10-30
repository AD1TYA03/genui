import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router";
import { LINKS } from "../lib/links";
import { GithubIcon } from "./icons";
import { Wordmark } from "./Logo";

const NAV = [
  { to: "/wander", label: "Wander" },
  { to: "/playground", label: "Playground" },
];

function Nav() {
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const { pathname } = useLocation();
  useEffect(() => setOpen(false), [pathname]);
  useEffect(() => {
    const on = () => setScrolled(window.scrollY > 8);
    on();
    window.addEventListener("scroll", on, { passive: true });
    return () => window.removeEventListener("scroll", on);
  }, []);
  return (
    <header
      className={`sticky top-0 z-50 border-b transition-colors duration-300 ${
        scrolled || open ? "border-line bg-ink/80 backdrop-blur-xl" : "border-transparent bg-transparent"
      }`}
    >
      <nav className="mx-auto flex h-16 max-w-6xl items-center gap-6 px-5 sm:px-8" aria-label="Main">
        <NavLink to="/" className="shrink-0 rounded-md" aria-label="genui home">
          <Wordmark />
        </NavLink>
        <div className="hidden items-center gap-1 md:flex">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              className={({ isActive }) =>
                `rounded-lg px-3 py-2 text-sm font-medium transition ${
                  isActive ? "bg-white/[0.06] text-fg" : "text-muted hover:text-fg"
                }`
              }
            >
              {n.label}
            </NavLink>
          ))}
        </div>
        <div className="ml-auto hidden items-center gap-2 md:flex">
          <a
            href={LINKS.pypi}
            target="_blank"
            rel="noreferrer"
            className="rounded-lg px-3 py-2 text-sm font-medium text-muted transition hover:text-fg"
          >
            PyPI
          </a>
          <a
            href={LINKS.npm}
            target="_blank"
            rel="noreferrer"
            className="rounded-lg px-3 py-2 text-sm font-medium text-muted transition hover:text-fg"
          >
            npm
          </a>
          <a
            href={LINKS.github}
            target="_blank"
            rel="noreferrer"
            className="ml-1 inline-flex items-center gap-2 rounded-lg border border-line-strong bg-white/[0.03] px-3.5 py-2 text-sm font-medium text-fg transition hover:border-white/25 hover:bg-white/[0.07]"
          >
            <GithubIcon /> GitHub
          </a>
        </div>
        <button
          className="ml-auto grid size-10 place-items-center rounded-lg text-muted hover:bg-white/5 hover:text-fg md:hidden"
          onClick={() => setOpen((o) => !o)}
          aria-expanded={open}
          aria-label="Toggle menu"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
            {open ? <path d="M6 6l12 12M18 6 6 18" /> : <path d="M4 7h16M4 12h16M4 17h16" />}
          </svg>
        </button>
      </nav>
      {open && (
        <div className="border-t border-line px-5 pb-5 pt-2 md:hidden">
          {[...NAV, { to: LINKS.github, label: "GitHub" }, { to: LINKS.pypi, label: "PyPI" }, { to: LINKS.npm, label: "npm" }].map(
            (n) =>
              n.to.startsWith("http") ? (
                <a key={n.to} href={n.to} target="_blank" rel="noreferrer" className="block rounded-lg px-3 py-3 text-muted hover:text-fg">
                  {n.label}
                </a>
              ) : (
                <NavLink key={n.to} to={n.to} className="block rounded-lg px-3 py-3 font-medium text-fg">
                  {n.label}
                </NavLink>
              ),
          )}
        </div>
      )}
    </header>
  );
}

function Footer() {
  return (
    <footer className="relative mt-24 border-t border-line">
      <div className="mx-auto grid max-w-6xl gap-10 px-5 py-14 sm:px-8 md:grid-cols-[1.4fr_1fr_1fr]">
        <div className="space-y-4">
          <Wordmark />
          <p className="max-w-sm text-sm leading-relaxed text-muted">
            Generative UI for Python agents. Free and MIT licensed. No account, no API key, no telemetry.
          </p>
          <p className="max-w-sm text-xs leading-relaxed text-dim">
            Community project, not affiliated with Thesys; built on OpenUI&rsquo;s MIT renderer.
          </p>
        </div>
        <div>
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-[0.14em] text-dim">Project</h3>
          <ul className="space-y-2 text-sm">
            <li><a className="text-muted hover:text-fg" href={LINKS.github} target="_blank" rel="noreferrer">GitHub</a></li>
            <li><a className="text-muted hover:text-fg" href={LINKS.pypi} target="_blank" rel="noreferrer">PyPI · genui-py</a></li>
            <li><a className="text-muted hover:text-fg" href={LINKS.npm} target="_blank" rel="noreferrer">npm · genui-react</a></li>
            <li><a className="text-muted hover:text-fg" href={LINKS.openui} target="_blank" rel="noreferrer">OpenUI Lang spec</a></li>
          </ul>
        </div>
        <div>
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-[0.14em] text-dim">Explore</h3>
          <ul className="space-y-2 text-sm">
            <li><NavLink className="text-muted hover:text-fg" to="/wander">Wander demo</NavLink></li>
            <li><NavLink className="text-muted hover:text-fg" to="/playground">Playground</NavLink></li>
            <li><a className="text-muted hover:text-fg" href={LINKS.example} target="_blank" rel="noreferrer">FastAPI + React example</a></li>
          </ul>
        </div>
      </div>
      <div className="border-t border-line">
        <div className="mx-auto flex max-w-6xl flex-col gap-2 px-5 py-6 text-xs text-dim sm:flex-row sm:items-center sm:justify-between sm:px-8">
          <span>© 2026 genui contributors · MIT License</span>
          <span>OpenUI spec and renderer © Thesys, MIT</span>
        </div>
      </div>
    </footer>
  );
}

export function Layout() {
  const { pathname } = useLocation();
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);
  return (
    <div className="relative flex min-h-dvh flex-col overflow-x-clip">
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[60] focus:rounded-md focus:bg-panel focus:px-3 focus:py-2">
        Skip to content
      </a>
      <Nav />
      <main id="main" className="flex-1">
        <Outlet />
      </main>
      {pathname !== "/playground" && <Footer />}
    </div>
  );
}
