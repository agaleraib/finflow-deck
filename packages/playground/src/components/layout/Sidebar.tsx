/**
 * App-level sidebar. Mirrors the FinFlow mockup `.sidebar` block.
 * Single active item ("Uniqueness Playground") with placeholder
 * disabled items so the sidebar feels like part of a larger app.
 *
 * Features:
 *   - Collapsible via chevron button at the bottom (icon-only when collapsed)
 *   - Light/dark theme toggle in the bottom bar
 *   - Lucide icons throughout
 */

import { useState } from "react";
import {
  FlaskConical,
  Newspaper,
  Settings,
  Radio,
  BarChart3,
  Globe,
  Sun,
  Moon,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useTheme } from "../../hooks/useTheme";

interface NavItem {
  icon: LucideIcon;
  label: string;
  active?: boolean;
  disabled?: boolean;
}

interface NavSection {
  label: string;
  items: NavItem[];
}

const NAV_SECTIONS: NavSection[] = [
  {
    label: "WORKSTREAMS",
    items: [
      { icon: FlaskConical, label: "Uniqueness Playground", active: true },
      { icon: Newspaper, label: "Sources", disabled: true },
      { icon: Settings, label: "Content Pipeline", disabled: true },
      { icon: Radio, label: "Publishers", disabled: true },
    ],
  },
  {
    label: "PRODUCT",
    items: [
      { icon: BarChart3, label: "Dashboard", disabled: true },
      { icon: Globe, label: "Translation Engine", disabled: true },
    ],
  },
];

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const { theme, toggle } = useTheme();

  return (
    <aside
      className="sidebar-root"
      data-collapsed={collapsed || undefined}
    >
      {/* Nav sections */}
      <div className="sidebar-nav">
        {NAV_SECTIONS.map((section) => (
          <div key={section.label} style={{ marginBottom: "var(--sp-6)" }}>
            {!collapsed && <div className="sidebar-label">{section.label}</div>}
            {section.items.map((item) => (
              <div
                key={item.label}
                className={`sidebar-item${item.active ? " active" : ""}`}
                style={
                  item.disabled
                    ? { opacity: 0.4, cursor: "default" }
                    : undefined
                }
                title={collapsed ? item.label : undefined}
              >
                <span className="sidebar-icon">
                  <item.icon size={16} />
                </span>
                {!collapsed && <span>{item.label}</span>}
              </div>
            ))}
          </div>
        ))}
      </div>

      {/* Bottom bar — theme toggle + collapse */}
      <div className="sidebar-bottom">
        <button
          className="sidebar-bottom-btn"
          onClick={toggle}
          title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
        >
          {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
        </button>

        <button
          className="sidebar-bottom-btn"
          onClick={() => setCollapsed((c) => !c)}
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? (
            <PanelLeftOpen size={16} />
          ) : (
            <PanelLeftClose size={16} />
          )}
        </button>
      </div>
    </aside>
  );
}
