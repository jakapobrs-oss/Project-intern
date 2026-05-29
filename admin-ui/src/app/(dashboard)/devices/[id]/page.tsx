"use client";
// Device detail — telemetry + manifest version + pairing info + เป็นสมาชิกกลุ่มไหน
// Route: /devices/[id]

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Cpu, Thermometer, Clock, Wifi, Tv, Key, RefreshCw } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { useAuth, hasRole } from "@/lib/auth";
import type { Device, PlayerGroup } from "@/lib/types";
import { STATUS_LABELS } from "@/lib/types";
import {
  Button, Card, CardBody, StatusBadge, Spinner, Badge,
} from "@/components/ui";
import { useToast } from "@/components/toast";

export default function DeviceDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { user } = useAuth();
  const toast = useToast();
  const canManage = hasRole(user, "super_admin", "admin");

  const [device, setDevice] = useState<Device | null>(null);
  const [groups, setGroups] = useState<PlayerGroup[]>([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const [d, g] = await Promise.all([
        api.get<Device>(`/devices/${params.id}`),
        api.get<PlayerGroup[]>("/groups"),
      ]);
      setDevice(d);
      setGroups(g.filter((x) => x.device_ids.includes(params.id)));
    } catch (e) {
      toast.error("โหลดไม่สำเร็จ", e instanceof ApiError ? e.message : undefined);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [params.id]);

  const handleRegenerate = async () => {
    if (!device || !confirm(`รีเซ็ต pairing code ของ "${device.name}"?`)) return;
    try {
      const d = await api.post<Device>(`/devices/${device.id}/regenerate-pairing`);
      setDevice(d);
      toast.success("รีเซ็ต pairing code สำเร็จ");
    } catch (e) {
      toast.error("รีเซ็ตไม่สำเร็จ", e instanceof ApiError ? e.message : undefined);
    }
  };

  if (loading) {
    return <div className="flex justify-center py-12"><Spinner className="h-5 w-5 text-brand-600" /></div>;
  }
  if (!device) {
    return <div className="text-sm text-slate-500">ไม่พบจอนี้</div>;
  }

  const lastHbAgoMin = device.last_heartbeat_at
    ? Math.floor((Date.now() - new Date(device.last_heartbeat_at).getTime()) / 60_000)
    : null;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Button variant="ghost" size="sm" onClick={() => router.push("/devices")}>
          <ArrowLeft className="h-3.5 w-3.5" /> กลับ
        </Button>
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={load}>
            <RefreshCw className="h-3.5 w-3.5" />
          </Button>
          {canManage && device.status === "unpaired" && (
            <Button size="sm" onClick={handleRegenerate}>
              <Key className="h-3.5 w-3.5" /> รีเซ็ต pairing
            </Button>
          )}
        </div>
      </div>

      {/* Header card */}
      <Card>
        <CardBody>
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-xl font-semibold">{device.name}</h2>
              <p className="mt-0.5 text-sm text-slate-500">{device.location || "ไม่ระบุตำแหน่ง"}</p>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <StatusBadge status={device.status} />
                <Badge variant="info">{device.platform}</Badge>
                {device.tv_brand && <Badge>{device.tv_brand} {device.tv_model}</Badge>}
              </div>
            </div>
            {device.pairing_code && (
              <div className="rounded-lg bg-slate-900 px-4 py-3 text-center">
                <div className="text-[10px] uppercase text-slate-400">Pairing code</div>
                <div className="font-mono text-2xl font-bold tracking-widest text-emerald-300">
                  {device.pairing_code}
                </div>
                {device.pairing_code_expires_at && (
                  <div className="mt-1 text-[10px] text-slate-400">
                    หมดอายุ {new Date(device.pairing_code_expires_at).toLocaleString("th-TH")}
                  </div>
                )}
              </div>
            )}
          </div>
        </CardBody>
      </Card>

      {/* Telemetry grid */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Metric
          icon={<Cpu className="h-5 w-5 text-brand-600" />}
          label="CPU"
          value={device.cpu_percent !== null ? `${device.cpu_percent.toFixed(1)}%` : "—"}
        />
        <Metric
          icon={<Thermometer className="h-5 w-5 text-amber-600" />}
          label="อุณหภูมิ"
          value={device.temperature_c !== null ? `${device.temperature_c.toFixed(1)}°C` : "—"}
        />
        <Metric
          icon={<Clock className="h-5 w-5 text-emerald-600" />}
          label="Uptime"
          value={device.uptime_sec !== null ? formatUptime(device.uptime_sec) : "—"}
        />
        <Metric
          icon={<Wifi className="h-5 w-5 text-sky-600" />}
          label="Heartbeat ล่าสุด"
          value={lastHbAgoMin !== null ? `${lastHbAgoMin} นาทีที่แล้ว` : "—"}
          warn={lastHbAgoMin !== null && lastHbAgoMin > 5}
        />
      </div>

      {/* Info grid */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card>
          <CardBody>
            <h3 className="mb-3 text-sm font-semibold">Hardware</h3>
            <KV k="MAC address" v={device.mac_address || "—"} />
            <KV k="IP address" v={device.ip_address || "—"} />
            <KV k="Serial" v={device.serial_number || "—"} />
            <KV k="App version" v={device.app_version || "—"} />
          </CardBody>
        </Card>

        <Card>
          <CardBody>
            <h3 className="mb-3 text-sm font-semibold">Sync</h3>
            <KV k="Manifest version" v={device.last_manifest_version ? <span className="font-mono">{device.last_manifest_version}</span> : "—"} />
            <KV k="Paired at" v={device.paired_at ? new Date(device.paired_at).toLocaleString("th-TH") : "—"} />
            <KV k="Created at" v={new Date(device.created_at).toLocaleString("th-TH")} />
            <KV k="Updated at" v={new Date(device.updated_at).toLocaleString("th-TH")} />
          </CardBody>
        </Card>
      </div>

      {/* Member groups */}
      <Card>
        <CardBody>
          <h3 className="mb-3 text-sm font-semibold">เป็นสมาชิกในกลุ่ม ({groups.length})</h3>
          {groups.length === 0 ? (
            <p className="text-sm text-slate-500">
              ไม่ได้อยู่ในกลุ่มไหน — schedule จะไม่ส่งถึงจอนี้
              {canManage && <> · <a href="/groups" className="text-brand-600 underline">จัดการกลุ่ม</a></>}
            </p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {groups.map((g) => (
                <a key={g.id} href="/groups"
                   className="rounded-full bg-brand-50 px-3 py-1 text-xs font-medium text-brand-700 hover:bg-brand-100">
                  {g.name}
                </a>
              ))}
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  );
}

function Metric({
  icon, label, value, warn,
}: {
  icon: React.ReactNode;
  label: string;
  value: React.ReactNode;
  warn?: boolean;
}) {
  return (
    <Card className={warn ? "border-amber-300 bg-amber-50" : ""}>
      <CardBody>
        <div className="flex items-center gap-3">
          {icon}
          <div>
            <div className="text-xs text-slate-500">{label}</div>
            <div className="text-lg font-semibold">{value}</div>
          </div>
        </div>
      </CardBody>
    </Card>
  );
}

function KV({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between border-b border-slate-100 py-1.5 last:border-0">
      <span className="text-xs text-slate-500">{k}</span>
      <span className="text-sm text-slate-900">{v}</span>
    </div>
  );
}

function formatUptime(sec: number): string {
  const d = Math.floor(sec / 86400);
  const h = Math.floor((sec % 86400) / 3600);
  const m = Math.floor((sec % 3600) / 60);
  if (d > 0) return `${d}d ${h}h`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}
