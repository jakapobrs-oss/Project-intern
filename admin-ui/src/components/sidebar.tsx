"use client";
// Sidebar — navigation หลัก พร้อม role-based visibility

import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";
import {
  LayoutDashboard,
  Monitor,
  FileImage,
  CalendarClock,
  AlertTriangle,
  ScrollText,
  Users,
  Tv,
  Layers,
  ListOrdered,
  Boxes,
} from "lucide-react";
import { useAuth, hasRole } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";
import type { Role } from "@/lib/types";

interface NavItem {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  // ถ้า roles ว่าง → ทุกคนเห็น
  roles?: Role[];
}

// label = key สำหรับ i18n.t() lookup — เป็นภาษาอังกฤษทั้งหมด
// คำแปลไทยอยู่ใน i18n.tsx → DICTIONARIES.th
const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/devices", label: "Devices", icon: Monitor },
  { href: "/groups", label: "Groups", icon: Boxes },
  { href: "/contents", label: "Contents", icon: FileImage },
  { href: "/presentations", label: "Presentations", icon: Layers },
  { href: "/plans", label: "Plans", icon: ListOrdered },
  { href: "/schedules", label: "Schedules", icon: CalendarClock },
  {
    href: "/tv-control",
    label: "TV Control",
    icon: Tv,
    roles: ["super_admin", "admin", "operator"],
  },
  {
    href: "/emergency",
    label: "Emergency",
    icon: AlertTriangle,
    roles: ["super_admin", "admin", "operator"],
  },
  {
    href: "/audit",
    label: "Audit log",
    icon: ScrollText,
    roles: ["super_admin", "admin"],
  },
  {
    href: "/users",
    label: "Users",
    icon: Users,
    roles: ["super_admin"],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user } = useAuth();
  const { t } = useI18n();

  return (
    <aside className="hidden w-64 shrink-0 border-r border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800 md:flex md:flex-col">
      <div className="border-b border-slate-200 px-5 py-4 dark:border-slate-700">
        <div className="text-lg font-bold text-brand-700 dark:text-brand-500">📺 Signage Admin</div>
        <div className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">ระบบจัดการจอประชาสัมพันธ์</div>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-4">
        <ul className="space-y-0.5">
          {NAV_ITEMS.filter((item) => !item.roles || hasRole(user, ...item.roles)).map((item) => {
            const Icon = item.icon;
            const active =
              pathname === item.href ||
              (item.href !== "/" && pathname.startsWith(item.href));
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={clsx(
                    "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                    active
                      ? "bg-brand-50 text-brand-700 dark:bg-brand-700/20 dark:text-brand-300"
                      : "text-slate-700 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-700",
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {t(item.label)}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </aside>
  );
}
