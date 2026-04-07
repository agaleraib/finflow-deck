import { NavLink } from "react-router-dom";
import { cn } from "../../lib/cn";

const NAV_ITEMS = [
  { label: "Command Center", path: "/dashboard", section: "Operations" },
  { label: "Pipeline Monitor", path: "/pipeline", section: "Operations" },
  { label: "Reports", path: "/reports", section: "Content" },
  { label: "Glossary", path: "/glossary", section: "Content" },
];

export function Sidebar() {
  let currentSection = "";

  return (
    <aside className="w-[240px] border-r border-border bg-bg-sidebar flex flex-col">
      <nav className="flex-1 py-4">
        {NAV_ITEMS.map((item) => {
          const showSection = item.section !== currentSection;
          if (showSection) currentSection = item.section;

          return (
            <div key={item.path}>
              {showSection && (
                <div className="px-5 pt-4 pb-2">
                  <span className="text-[10px] font-semibold tracking-[2px] uppercase text-text-muted">
                    {item.section}
                  </span>
                </div>
              )}
              <NavLink
                to={item.path}
                className={({ isActive }) =>
                  cn(
                    "flex items-center px-5 py-2 text-sm transition-colors duration-fast",
                    "border-l-2 border-transparent",
                    isActive
                      ? "text-text-primary border-l-accent bg-accent-subtle"
                      : "text-text-secondary hover:text-text-primary hover:bg-bg-hover"
                  )
                }
              >
                {item.label}
              </NavLink>
            </div>
          );
        })}
      </nav>

      <div className="p-4 border-t border-border">
        <div className="text-[10px] text-text-muted tracking-widest uppercase">
          Prototype Demo
        </div>
        <div className="text-[11px] text-text-secondary mt-1">
          OANDA Profile
        </div>
      </div>
    </aside>
  );
}
