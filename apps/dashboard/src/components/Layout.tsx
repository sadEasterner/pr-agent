import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";

const links = [
  { to: "/", label: "Overview" },
  { to: "/pull-requests", label: "Pull Requests" },
  { to: "/findings", label: "Findings" },
  { to: "/repositories", label: "Repositories" },
  { to: "/trends", label: "Trends" },
  { to: "/settings", label: "Settings" },
  { to: "/admin", label: "Admin" },
];

export function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 border-b border-slate-200/80 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-6 py-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-lg font-semibold tracking-tight text-slate-900">PR Manager</p>
            <p className="text-xs text-slate-500">AI reviews are advisory. Humans control merge.</p>
          </div>
          <nav className="flex flex-wrap gap-1 text-sm">
            {links.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                end={link.to === "/"}
                className={({ isActive }) =>
                  [
                    "rounded-full px-3 py-1.5 transition-colors",
                    isActive
                      ? "bg-slate-900 font-medium text-white"
                      : "text-slate-500 hover:bg-slate-100 hover:text-slate-800",
                  ].join(" ")
                }
              >
                {link.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-6 py-8">{children}</main>
    </div>
  );
}
