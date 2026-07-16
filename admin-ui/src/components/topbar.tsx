"use client";
// Topbar — user info + logout + theme toggle + language switcher

import { usePathname } from "next/navigation";
import { LogOut, Sun, Moon, Monitor, Languages } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { useTheme } from "@/lib/theme";
import { useI18n } from "@/lib/i18n";
import { ROLE_LABELS } from "@/lib/types";

// map path → label เดียวกับ NAV_ITEMS ใน sidebar (ให้หัวหน้าตรงกับเมนูที่เลือกอยู่)
// เรียงจาก path ยาว/เฉพาะเจาะจงที่สุดก่อน — "/" ปล่อยเป็น fallback Dashboard
const PATH_TITLES: Array<[string, string]> = [
  ["/devices", "Devices"],
  ["/groups", "Groups"],
  ["/contents", "Contents"],
  ["/presentations", "Presentations"],
  ["/plans", "Plans"],
  ["/schedules", "Schedules"],
  ["/tv-control", "TV Control"],
  ["/emergency", "Emergency"],
  ["/audit", "Audit log"],
  ["/users", "Users"],
];

export function Topbar({ title }: { title?: string }) {
  const { user, logout } = useAuth();
  const { theme, setTheme } = useTheme();
  const { lang, setLang, t } = useI18n();
  const pathname = usePathname();
  const routeTitle = PATH_TITLES.find(
    ([p]) => pathname === p || pathname.startsWith(`${p}/`),
  )?.[1];

  // cycle theme: light → dark → system → light
  const nextTheme = () => {
    if (theme === "light") setTheme("dark");
    else if (theme === "dark") setTheme("system");
    else setTheme("light");
  };

  const ThemeIcon = theme === "light" ? Sun : theme === "dark" ? Moon : Monitor;

  return (
    <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-3 dark:border-slate-700 dark:bg-slate-800">
      <div>
        <h1 className="text-base font-semibold text-slate-900 dark:text-slate-100">
          {title ?? t(routeTitle ?? "Dashboard")}
        </h1>
      </div>

      <div className="flex items-center gap-2">
        {/* Theme toggle */}
        <button
          onClick={nextTheme}
          className="rounded-md p-2 text-slate-500 hover:bg-slate-100 hover:text-slate-700 dark:text-slate-400 dark:hover:bg-slate-700 dark:hover:text-slate-200"
          title={`${t("Theme")}: ${theme}`}
          aria-label={t("Theme")}
        >
          <ThemeIcon className="h-4 w-4" />
        </button>

        {/* Language switcher */}
        <button
          onClick={() => setLang(lang === "th" ? "en" : "th")}
          className="flex items-center gap-1 rounded-md px-2 py-2 text-xs font-medium text-slate-500 hover:bg-slate-100 hover:text-slate-700 dark:text-slate-400 dark:hover:bg-slate-700 dark:hover:text-slate-200"
          title={t("Language")}
        >
          <Languages className="h-4 w-4" />
          {lang.toUpperCase()}
        </button>

        {user && (
          <div className="ml-2 text-right">
            <div className="text-sm font-medium text-slate-900 dark:text-slate-100">
              {user.full_name || user.username}
            </div>
            <div className="text-xs text-slate-500 dark:text-slate-400">
              {ROLE_LABELS[user.role]}
            </div>
          </div>
        )}

        <button
          onClick={() => void logout()}
          className="rounded-md p-2 text-slate-500 hover:bg-slate-100 hover:text-slate-700 dark:text-slate-400 dark:hover:bg-slate-700 dark:hover:text-slate-200"
          title={t("Logout")}
          aria-label={t("Logout")}
        >
          <LogOut className="h-4 w-4" />
        </button>
      </div>
    </header>
  );
}
