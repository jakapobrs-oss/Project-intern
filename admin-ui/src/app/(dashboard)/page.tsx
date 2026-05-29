"use client";
// Dashboard — สรุปสถานะระบบเร็ว ๆ (Phase 6 minimal — Phase 7 จะเพิ่ม metric chart)

import { useEffect, useState } from "react";
import { Monitor, AlertTriangle, FileImage, CalendarClock } from "lucide-react";
import { api } from "@/lib/api";
import type { Device, EmergencyBroadcast, Content, Schedule } from "@/lib/types";
import { Card, CardBody, Spinner } from "@/components/ui";

interface Stats {
  devices: { total: number; online: number; offline: number; unpaired: number };
  emergencies: { active: number };
  contents: { total: number; pending: number };
  schedules: { active: number };
}

async function loadStats(): Promise<Stats> {
  // ดึงข้อมูล parallel เพื่อความเร็ว
  const [devices, emergencies, contents, schedules] = await Promise.all([
    api.get<Device[]>("/devices"),
    api.get<EmergencyBroadcast[]>("/emergency/?status_filter=active"),
    api.get<Content[]>("/contents"),
    api.get<Schedule[]>("/schedules"),
  ]);

  return {
    devices: {
      total: devices.length,
      online: devices.filter((d) => d.status === "online").length,
      offline: devices.filter((d) => d.status === "offline").length,
      unpaired: devices.filter((d) => d.status === "unpaired").length,
    },
    emergencies: { active: emergencies.length },
    contents: {
      total: contents.length,
      pending: contents.filter((c) => c.approval_status === "pending").length,
    },
    schedules: { active: schedules.filter((s) => s.status === "active").length },
  };
}

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadStats()
      .then(setStats)
      .catch((e) => setError(e.message ?? "โหลดข้อมูลล้มเหลว"));
  }, []);

  if (error) {
    return (
      <div className="rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
        {error}
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="flex items-center justify-center py-16">
        <Spinner className="h-6 w-6 text-brand-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          icon={<Monitor className="h-6 w-6 text-brand-600" />}
          label="จอทั้งหมด"
          value={stats.devices.total}
          subtitle={`ออนไลน์ ${stats.devices.online} / ออฟไลน์ ${stats.devices.offline}`}
        />
        <StatCard
          icon={<AlertTriangle className="h-6 w-6 text-rose-600" />}
          label="แจ้งเตือนฉุกเฉินที่ active"
          value={stats.emergencies.active}
          highlight={stats.emergencies.active > 0}
        />
        <StatCard
          icon={<FileImage className="h-6 w-6 text-amber-600" />}
          label="สื่อรออนุมัติ"
          value={stats.contents.pending}
          subtitle={`สื่อทั้งหมด ${stats.contents.total}`}
        />
        <StatCard
          icon={<CalendarClock className="h-6 w-6 text-emerald-600" />}
          label="ตารางเล่นที่ active"
          value={stats.schedules.active}
        />
      </div>

      {/* Device breakdown */}
      <Card>
        <CardBody>
          <h2 className="mb-3 text-sm font-semibold text-slate-700">สถานะจอ</h2>
          <div className="grid grid-cols-3 gap-3 text-sm">
            <DeviceStat label="ออนไลน์" value={stats.devices.online} color="bg-emerald-500" />
            <DeviceStat label="ออฟไลน์" value={stats.devices.offline} color="bg-slate-400" />
            <DeviceStat label="ยังไม่ผูก" value={stats.devices.unpaired} color="bg-amber-500" />
          </div>
        </CardBody>
      </Card>
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
  subtitle,
  highlight,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  subtitle?: string;
  highlight?: boolean;
}) {
  return (
    <Card className={highlight ? "border-rose-300 bg-rose-50" : ""}>
      <CardBody>
        <div className="flex items-start gap-3">
          <div>{icon}</div>
          <div className="flex-1">
            <div className="text-xs text-slate-500">{label}</div>
            <div className="text-2xl font-semibold text-slate-900">{value}</div>
            {subtitle && <div className="mt-0.5 text-xs text-slate-500">{subtitle}</div>}
          </div>
        </div>
      </CardBody>
    </Card>
  );
}

function DeviceStat({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div>
      <div className="flex items-center gap-2">
        <span className={`inline-block h-2.5 w-2.5 rounded-full ${color}`} />
        <span className="text-slate-600">{label}</span>
      </div>
      <div className="mt-1 text-xl font-semibold">{value}</div>
    </div>
  );
}
