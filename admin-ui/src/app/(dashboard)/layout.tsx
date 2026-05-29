"use client";
// Route group `(dashboard)` — ทุก page ใต้นี้ ได้ Sidebar + Topbar อัตโนมัติ
// ไม่กระทบ URL (route group ไม่อยู่ใน path)

import { Sidebar } from "@/components/sidebar";
import { Topbar } from "@/components/topbar";
import { useAuth } from "@/lib/auth";
import { Spinner } from "@/components/ui";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();

  // กำลังโหลด /me — แสดง spinner เต็มจอ (กัน flash content)
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spinner className="h-6 w-6 text-brand-600" />
      </div>
    );
  }

  // ไม่มี user — AuthProvider จะ redirect ไป /login เอง
  if (!user) return null;

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex flex-1 flex-col">
        <Topbar />
        <main className="flex-1 overflow-y-auto bg-slate-50 p-6 dark:bg-slate-900">{children}</main>
      </div>
    </div>
  );
}
