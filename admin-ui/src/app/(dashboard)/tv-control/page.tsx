"use client";
// TV control panel — เลือกจอ + ส่ง command (power/input/volume/etc)

import { useEffect, useState } from "react";
import { Power, Volume2, Tv } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import type { Device } from "@/lib/types";
import {
  Button,
  Card,
  CardBody,
  Select,
  StatusBadge,
  Empty,
  Spinner,
} from "@/components/ui";

const COMMANDS: { type: string; label: string; payload?: Record<string, unknown> }[] = [
  { type: "power_on", label: "เปิดจอ" },
  { type: "power_off", label: "ปิดจอ" },
  { type: "volume_up", label: "เพิ่มเสียง" },
  { type: "volume_down", label: "ลดเสียง" },
  { type: "mute", label: "ปิดเสียง" },
  { type: "input_hdmi1", label: "เปลี่ยนเป็น HDMI 1" },
  { type: "input_hdmi2", label: "เปลี่ยนเป็น HDMI 2" },
];

export default function TVControlPage() {
  const [devices, setDevices] = useState<Device[] | null>(null);
  const [selected, setSelected] = useState<string>("");
  const [busy, setBusy] = useState<string | null>(null);
  const [log, setLog] = useState<{ ts: Date; msg: string; ok: boolean }[]>([]);

  useEffect(() => {
    api
      .get<Device[]>("/devices")
      .then((list) => {
        setDevices(list);
        const online = list.find((d) => d.status === "online");
        if (online) setSelected(online.id);
      })
      .catch(() => setDevices([]));
  }, []);

  const send = async (cmd: { type: string; label: string; payload?: Record<string, unknown> }) => {
    if (!selected) return;
    setBusy(cmd.type);
    try {
      const res = await api.post<{ cmd_id: string }>(`/tv/devices/${selected}/commands`, {
        command_type: cmd.type,
        payload: cmd.payload ?? null,
        set_id: 1,
      });
      setLog((prev) => [
        { ts: new Date(), msg: `${cmd.label} → queued cmd_id=${res.cmd_id.slice(0, 8)}…`, ok: true },
        ...prev,
      ]);
    } catch (e) {
      setLog((prev) => [
        { ts: new Date(), msg: `${cmd.label} → ${e instanceof ApiError ? e.message : "error"}`, ok: false },
        ...prev,
      ]);
    } finally {
      setBusy(null);
    }
  };

  if (devices === null) {
    return (
      <div className="flex justify-center py-12">
        <Spinner className="h-5 w-5 text-brand-600" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-600">
        ส่ง command ควบคุม TV ผ่าน HDMI-CEC / RS-232 (§24)
      </p>

      <Card>
        <CardBody>
          <label className="mb-1 block text-sm font-medium">เลือกจอ</label>
          {devices.length === 0 ? (
            <Empty title="ยังไม่มีจอในระบบ" />
          ) : (
            <Select value={selected} onChange={(e) => setSelected(e.target.value)}>
              <option value="">— เลือก —</option>
              {devices.map((d) => (
                <option key={d.id} value={d.id} disabled={d.status !== "online"}>
                  {d.name} ({d.location || "—"}) — {d.status}
                </option>
              ))}
            </Select>
          )}
        </CardBody>
      </Card>

      {selected && (
        <Card>
          <CardBody>
            <div className="mb-2 flex items-center gap-2">
              <Tv className="h-4 w-4 text-brand-600" />
              <h3 className="text-sm font-semibold">คำสั่ง</h3>
            </div>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
              {COMMANDS.map((cmd) => (
                <Button
                  key={cmd.type}
                  variant="secondary"
                  loading={busy === cmd.type}
                  onClick={() => send(cmd)}
                  className="justify-start"
                >
                  {cmd.type.startsWith("power") && <Power className="h-3.5 w-3.5" />}
                  {cmd.type.startsWith("volume") || cmd.type === "mute" ? <Volume2 className="h-3.5 w-3.5" /> : null}
                  {cmd.label}
                </Button>
              ))}
            </div>
          </CardBody>
        </Card>
      )}

      {log.length > 0 && (
        <Card>
          <CardBody>
            <h3 className="mb-2 text-sm font-semibold">ประวัติคำสั่ง (session นี้)</h3>
            <ul className="space-y-1 font-mono text-xs">
              {log.map((entry, i) => (
                <li key={i} className={entry.ok ? "text-emerald-700" : "text-rose-700"}>
                  [{entry.ts.toLocaleTimeString("th-TH")}] {entry.msg}
                </li>
              ))}
            </ul>
          </CardBody>
        </Card>
      )}
    </div>
  );
}
