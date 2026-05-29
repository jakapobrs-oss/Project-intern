"use client";
// Audit log viewer — admin/super_admin เท่านั้น
// filter ตาม action / outcome / actor_id / target_id

import { useEffect, useState } from "react";
import { Filter, RefreshCw } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import type { AuditLog, AuditOutcome } from "@/lib/types";
import {
  Button,
  Card,
  CardBody,
  Input,
  Select,
  StatusBadge,
  TBody,
  TD,
  TH,
  THead,
  Table,
  Empty,
  Spinner,
} from "@/components/ui";

// action verbs ที่ backend ใช้ — sync กับ services/audit_service.py
const ACTION_OPTIONS = [
  "",
  "auth.login",
  "auth.login_failed",
  "auth.refresh",
  "content.upload",
  "content.approve",
  "content.reject",
  "schedule.activate",
  "schedule.pause",
  "device.pair",
  "tv.command_sent",
  "emergency.create",
  "emergency.activate",
  "emergency.cancel",
  "rbac.denied",
];

export default function AuditPage() {
  const [logs, setLogs] = useState<AuditLog[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [action, setAction] = useState("");
  const [outcome, setOutcome] = useState<AuditOutcome | "">("");
  const [actorId, setActorId] = useState("");
  const [targetId, setTargetId] = useState("");

  const load = async () => {
    setError(null);
    const qs = new URLSearchParams();
    if (action) qs.set("action", action);
    if (outcome) qs.set("outcome", outcome);
    if (actorId) qs.set("actor_id", actorId);
    if (targetId) qs.set("target_id", targetId);
    qs.set("limit", "200");
    try {
      const list = await api.get<AuditLog[]>(`/audit/logs?${qs.toString()}`);
      setLogs(list);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "โหลดไม่สำเร็จ");
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-600">
        Audit log — บันทึก action ทุกอย่างใน system (append-only) §26 §31
      </p>

      {/* Filter bar */}
      <Card>
        <CardBody>
          <div className="flex flex-wrap items-end gap-3">
            <div className="min-w-[200px] flex-1">
              <label className="mb-1 block text-xs font-medium">Action</label>
              <Select value={action} onChange={(e) => setAction(e.target.value)}>
                {ACTION_OPTIONS.map((a) => (
                  <option key={a} value={a}>
                    {a || "ทุก action"}
                  </option>
                ))}
              </Select>
            </div>
            <div className="min-w-[140px]">
              <label className="mb-1 block text-xs font-medium">Outcome</label>
              <Select value={outcome} onChange={(e) => setOutcome(e.target.value as AuditOutcome | "")}>
                <option value="">ทุก outcome</option>
                <option value="success">success</option>
                <option value="fail">fail</option>
                <option value="denied">denied</option>
              </Select>
            </div>
            <div className="min-w-[180px] flex-1">
              <label className="mb-1 block text-xs font-medium">Actor ID</label>
              <Input value={actorId} onChange={(e) => setActorId(e.target.value)} placeholder="UUID" />
            </div>
            <div className="min-w-[180px] flex-1">
              <label className="mb-1 block text-xs font-medium">Target ID</label>
              <Input value={targetId} onChange={(e) => setTargetId(e.target.value)} placeholder="UUID" />
            </div>
            <Button onClick={load} size="md">
              <Filter className="h-3.5 w-3.5" /> ใช้ filter
            </Button>
            <Button variant="ghost" onClick={load} size="md">
              <RefreshCw className="h-3.5 w-3.5" />
            </Button>
          </div>
        </CardBody>
      </Card>

      {error && (
        <div className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
          {error}
        </div>
      )}

      {logs === null ? (
        <div className="flex justify-center py-12">
          <Spinner className="h-5 w-5 text-brand-600" />
        </div>
      ) : logs.length === 0 ? (
        <Empty title="ไม่พบ log ตรงเงื่อนไข" />
      ) : (
        <Table>
          <THead>
            <tr>
              <TH>เวลา</TH>
              <TH>Action</TH>
              <TH>Outcome</TH>
              <TH>Actor</TH>
              <TH>Target</TH>
              <TH>IP</TH>
              <TH>Message</TH>
            </tr>
          </THead>
          <TBody>
            {logs.map((log) => (
              <tr key={log.id} className="hover:bg-slate-50">
                <TD className="text-xs whitespace-nowrap">
                  {new Date(log.created_at).toLocaleString("th-TH")}
                </TD>
                <TD className="font-mono text-xs">{log.action}</TD>
                <TD>
                  <StatusBadge status={log.outcome} />
                </TD>
                <TD className="text-xs">
                  <div>{log.actor_label ?? log.actor_id ?? "—"}</div>
                  <div className="text-slate-400">{log.actor_type}</div>
                </TD>
                <TD className="text-xs">
                  {log.target_type && log.target_id ? (
                    <span>
                      {log.target_type}:<span className="font-mono">{log.target_id.slice(0, 8)}…</span>
                    </span>
                  ) : (
                    "—"
                  )}
                </TD>
                <TD className="text-xs text-slate-500">{log.ip_address ?? "—"}</TD>
                <TD className="max-w-md text-xs text-slate-600">
                  <div className="line-clamp-2">{log.message ?? ""}</div>
                </TD>
              </tr>
            ))}
          </TBody>
        </Table>
      )}
    </div>
  );
}
