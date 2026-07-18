import { useState } from "react";
import { NavLink } from "react-router-dom";
import { Menu, X } from "lucide-react";
import type { SystemCapabilities } from "../types/domain";

const navItems = [
  { label: "Dashboard", to: "/" },
  { label: "Auditions", to: "/auditions" },
  { label: "Breakdowns", to: "/breakdowns" },
  { label: "Materials", to: "/materials" },
  { label: "Career Intelligence", to: "/career" },
  { label: "Analytics", to: "/analytics" },
  { label: "Relationships", to: "/relationships" },
  { label: "Calendar", to: "/calendar" },
  { label: "Journal", to: "/journal" },
  { label: "Profile", to: "/profile" },
  { label: "Settings", to: "/settings" }
];

export function TopNavigation({ capabilities }: { capabilities: SystemCapabilities | null }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const aiConfigured = capabilities?.flags.ai_configured ?? false;

  return (
    <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 backdrop-blur">
      <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-4">
        <div className="flex min-w-0 flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="min-w-0">
            <NavLink
              to="/"
              className="inline-block break-words text-xl font-bold text-ink transition hover:text-accent"
              onClick={() => setMenuOpen(false)}
            >
              The Working Actor OS
            </NavLink>
            <p className="mt-1 text-sm text-slate-600">
              {aiConfigured ? "Your AI-powered career operating system." : "Your actor career operating system. AI features are labeled when configured."}
            </p>
          </div>
          <div className="flex min-w-0 flex-wrap items-center gap-2">
            <button
              type="button"
              className="inline-flex items-center justify-center rounded-md border border-slate-300 bg-white p-2 text-slate-700 transition hover:bg-slate-50 md:hidden"
              onClick={() => setMenuOpen((current) => !current)}
              aria-expanded={menuOpen}
              aria-controls="mobile-workflow-navigation"
              aria-label={menuOpen ? "Close workflow navigation" : "Open workflow navigation"}
            >
              {menuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
          </div>
        </div>
        <nav className="hidden min-w-0 flex-wrap gap-2 md:flex" aria-label="Primary workflow navigation">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                `min-w-0 break-words rounded-md px-3 py-2 text-sm font-semibold transition ${
                  isActive ? "bg-accent text-white" : "text-slate-700 hover:bg-slate-100"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        {menuOpen && (
          <nav
            id="mobile-workflow-navigation"
            className="grid min-w-0 gap-1 rounded-md border border-slate-200 bg-white p-2 shadow-sm md:hidden"
            aria-label="Primary workflow navigation menu"
          >
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                onClick={() => setMenuOpen(false)}
                className={({ isActive }) =>
                  `min-w-0 rounded px-3 py-2 text-sm font-semibold transition ${
                    isActive ? "bg-accent text-white" : "text-slate-700 hover:bg-slate-100"
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        )}
      </div>
    </header>
  );
}
