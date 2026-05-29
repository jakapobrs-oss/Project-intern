"use client";
// Schedules — list + create wizard (Plan + Group + datetime + RRULE) + approve + pause

import { useEffect, useState } from "react";
import { Check, Pause, RefreshCw, Plus } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { useAuth, hasRole } from "@/lib/auth";
import type { Schedule, Plan, PlayerGroup } from "@/lib/types";
import {
  Button, Input, Select, Modal, Textarea, StatusBadge,
  TBody, TD, TH, THead, Table, Empty, Spinner,
} from "@/components/ui";
import { useToast } from "@/components/toast";

export default function SchedulesPage() {
  const { user } = useAuth();
  const toast = useToast();
  const canApprove = hasRole(user, "super_admin", "admin", "approver");
  const canEdit = hasRole(user, "super_admin", "admin", "editor");

  const [items, setItems] = useState<Schedule[] | null>(null);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [groups, setGroups] = useState<PlayerGroup[]>([]);
  const [createOpen, setCreateOpen] = useState(false);

  const load = async () => {
    try {
      const [s, p, g] = await Promise.all([
        api.get<Schedule[]>("/schedules"),
        api.get<Plan[]>("/plans"),
        api.get<PlayerGroup[]>("/groups"),
      ]);
      setItems(s); setPlans(p); setGroups(g);
    } catch (e) {
      toast.error("โหลดข้อมูลไม่สำเร็จ", e instanceof ApiError ? e.message : undefined);
    }
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, []);

  const handleApprove = async (s: Schedule) => {
    try {
      const updated = await api.post<Schedule>(`/schedules/${s.id}/approve`);
      setItems((prev) => prev?.map((x) => (x.id === s.id ? updated : x)) ?? null);
      toast.success(`Activated: ${s.name}`);
    } catch (e) {
      toast.error("approve ไม่สำเร็จ", e instanceof ApiError ? e.message : undefined);
    }
  };

  const handlePause = async (s: Schedule) => {
    try {
      const updated = await api.post<Schedule>(`/schedules/${s.id}/pause`);
      setItems((prev) => prev?.map((x) => (x.id === s.id ? updated : x)) ?? null);
      toast.success(`Paused: ${s.name}`);
    } catch (e) {
      toast.error("pause ไม่สำเร็จ", e instanceof ApiError ? e.message : undefined);
    }
  };

  const planNameById = (id: string) => plans.find((p) => p.id === id)?.name ?? id.slice(0, 8);
  const groupNameById = (id: string) => groups.find((g) => g.id === id)?.name ?? id.slice(0, 8);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-600">
          ตารางเล่น — ผูก Plan ↔ Player Group + ช่วงเวลา + priority (§23)
        </p>
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={load}>
            <RefreshCw className="h-3.5 w-3.5" /> รีเฟรช
          </Button>
          {canEdit && (
            <Button size="sm" onClick={() => setCreateOpen(true)}>
              <Plus className="h-3.5 w-3.5" /> สร้าง schedule
            </Button>
          )}
        </div>
      </div>

      {items === null ? (
        <div className="flex justify-center py-12">
          <Spinner className="h-5 w-5 text-brand-600" />
        </div>
      ) : items.length === 0 ? (
        <Empty title="ยังไม่มี schedule" description="กด 'สร้าง schedule' เพื่อผูก plan กับ group" />
      ) : (
        <Table>
          <THead>
            <tr>
              <TH>ชื่อ</TH>
              <TH>Plan</TH>
              <TH>กลุ่มจอ</TH>
              <TH>Priority</TH>
              <TH>เริ่ม / สิ้นสุด</TH>
              <TH>Daily window</TH>
              <TH>สถานะ</TH>
              <TH className="text-right">การจัดการ</TH>
            </tr>
          </THead>
          <TBody>
            {items.map((s) => (
              <tr key={s.id} className="hover:bg-slate-50">
                <TD>
                  <div className="font-medium">{s.name}</div>
                  {s.description && <div className="text-xs text-slate-500">{s.description}</div>}
                </TD>
                <TD className="text-xs">{planNameById(s.plan_id)}</TD>
                <TD className="text-xs">{groupNameById(s.player_group_id)}</TD>
                <TD>{s.priority}</TD>
                <TD className="text-xs">
                  <div>{new Date(s.start_at).toLocaleString("th-TH")}</div>
                  {s.end_at && <div className="text-slate-400">→ {new Date(s.end_at).toLocaleString("th-TH")}</div>}
                </TD>
                <TD className="text-xs">
                  {s.daily_window_start && s.daily_window_end
                    ? `${s.daily_window_start} – ${s.daily_window_end}`
                    : "ตลอดวัน"}
                  {s.repeat_rule && <div className="text-slate-400 font-mono">{s.repeat_rule}</div>}
                </TD>
                <TD>
                  <StatusBadge status={s.status} />
                </TD>
                <TD className="text-right">
                  {canApprove && (s.status === "pending_approval" || s.status === "draft") && (
                    <Button size="sm" variant="ghost" onClick={() => handleApprove(s)}>
                      <Check className="h-3.5 w-3.5 text-emerald-600" /> Activate
                    </Button>
                  )}
                  {canEdit && s.status === "active" && (
                    <Button size="sm" variant="ghost" onClick={() => handlePause(s)}>
                      <Pause className="h-3.5 w-3.5" /> Pause
                    </Button>
                  )}
                </TD>
              </tr>
            ))}
          </TBody>
        </Table>
      )}

      <CreateScheduleModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        plans={plans}
        groups={groups}
        onCreated={(s) => setItems((prev) => (prev ? [s, ...prev] : [s]))}
      />
    </div>
  );
}

// ===== Schedule create wizard =====
const RRULE_PRESETS = [
  { id: "", label: "ครั้งเดียว (ไม่ repeat)" },
  { id: "FREQ=DAILY", label: "ทุกวัน" },
  { id: "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR", label: "วันจันทร์-ศุกร์" },
  { id: "FREQ=WEEKLY;BYDAY=SA,SU", label: "วันเสาร์-อาทิตย์" },
  { id: "FREQ=WEEKLY", label: "ทุกสัปดาห์ (วันเดียวกัน)" },
  { id: "FREQ=MONTHLY", label: "ทุกเดือน" },
];

function toIsoLocal(dt: Date): string {
  // input[type=datetime-local] ต้องการรูปแบบ YYYY-MM-DDTHH:MM (no tz)
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${dt.getFullYear()}-${pad(dt.getMonth() + 1)}-${pad(dt.getDate())}T${pad(dt.getHours())}:${pad(dt.getMinutes())}`;
}

function CreateScheduleModal({
  open, onClose, plans, groups, onCreated,
}: {
  open: boolean;
  onClose: () => void;
  plans: Plan[];
  groups: PlayerGroup[];
  onCreated: (s: Schedule) => void;
}) {
  const toast = useToast();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [planId, setPlanId] = useState("");
  const [groupId, setGroupId] = useState("");
  const [startAt, setStartAt] = useState(toIsoLocal(new Date()));
  const [endAt, setEndAt] = useState("");
  const [repeatRule, setRepeatRule] = useState("");
  const [dailyStart, setDailyStart] = useState("");
  const [dailyEnd, setDailyEnd] = useState("");
  const [priority, setPriority] = useState(100);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open) return;
    setName(""); setDescription(""); setPlanId(""); setGroupId("");
    setStartAt(toIsoLocal(new Date()));
    setEndAt(""); setRepeatRule(""); setDailyStart(""); setDailyEnd("");
    setPriority(100);
  }, [open]);

  const handleSubmit = async () => {
    if (!name.trim()) return toast.error("ระบุชื่อ schedule");
    if (!planId) return toast.error("เลือก plan");
    if (!groupId) return toast.error("เลือกกลุ่มจอ");
    if (!startAt) return toast.error("ระบุเวลาเริ่ม");
    if ((dailyStart && !dailyEnd) || (!dailyStart && dailyEnd)) {
      return toast.error("Daily window: ระบุทั้งเริ่มและสิ้นสุด หรือเว้นว่างทั้งคู่");
    }

    setLoading(true);
    const body = {
      name: name.trim(),
      description: description.trim(),
      plan_id: planId,
      player_group_id: groupId,
      start_at: new Date(startAt).toISOString(),
      end_at: endAt ? new Date(endAt).toISOString() : null,
      repeat_rule: repeatRule || null,
      daily_window_start: dailyStart || null,
      daily_window_end: dailyEnd || null,
      priority,
    };
    try {
      const s = await api.post<Schedule>("/schedules", body);
      onCreated(s);
      toast.success(`สร้างสำเร็จ (status: ${s.status})`);
      onClose();
    } catch (e) {
      toast.error("สร้างไม่สำเร็จ", e instanceof ApiError ? e.message : undefined);
    } finally {
      setLoading(false);
    }
  };

  if ((plans.length === 0 || groups.length === 0) && open) {
    return (
      <Modal open={open} onClose={onClose} title="ยังไม่พร้อมสร้าง schedule"
        footer={<Button onClick={onClose}>ปิด</Button>}>
        <p className="text-sm">ต้องมี:</p>
        <ul className="ml-5 mt-1 list-disc text-sm">
          {plans.length === 0 && <li>Plan อย่างน้อย 1 ตัว — <a href="/plans" className="text-brand-600 underline">สร้าง</a></li>}
          {groups.length === 0 && <li>Player Group อย่างน้อย 1 กลุ่ม — <a href="/groups" className="text-brand-600 underline">สร้าง</a></li>}
        </ul>
      </Modal>
    );
  }

  return (
    <Modal open={open} onClose={onClose} title="สร้าง schedule ใหม่"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>ยกเลิก</Button>
          <Button onClick={handleSubmit} loading={loading}>สร้าง</Button>
        </>
      }
    >
      <div className="space-y-3">
        <div>
          <label className="mb-1 block text-sm font-medium">ชื่อ schedule *</label>
          <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="เช่น โฆษณาช่วงเช้า" />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">คำอธิบาย</label>
          <Textarea rows={2} value={description} onChange={(e) => setDescription(e.target.value)} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="mb-1 block text-sm font-medium">Plan *</label>
            <Select value={planId} onChange={(e) => setPlanId(e.target.value)}>
              <option value="">— เลือก —</option>
              {plans.map((p) => (
                <option key={p.id} value={p.id}>{p.name} ({p.items.length} items)</option>
              ))}
            </Select>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">กลุ่มจอ *</label>
            <Select value={groupId} onChange={(e) => setGroupId(e.target.value)}>
              <option value="">— เลือก —</option>
              {groups.map((g) => (
                <option key={g.id} value={g.id}>{g.name} ({g.device_ids.length} จอ)</option>
              ))}
            </Select>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="mb-1 block text-sm font-medium">เริ่ม *</label>
            <Input type="datetime-local" value={startAt} onChange={(e) => setStartAt(e.target.value)} />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">สิ้นสุด (optional)</label>
            <Input type="datetime-local" value={endAt} onChange={(e) => setEndAt(e.target.value)} />
          </div>
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">Repeat (RRULE)</label>
          <Select value={repeatRule} onChange={(e) => setRepeatRule(e.target.value)}>
            {RRULE_PRESETS.map((r) => (
              <option key={r.id} value={r.id}>{r.label}</option>
            ))}
          </Select>
        </div>
        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="mb-1 block text-sm font-medium">Daily start (HH:MM)</label>
            <Input value={dailyStart} onChange={(e) => setDailyStart(e.target.value)} placeholder="08:00" />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Daily end (HH:MM)</label>
            <Input value={dailyEnd} onChange={(e) => setDailyEnd(e.target.value)} placeholder="18:00" />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Priority (0-1000)</label>
            <Input type="number" min={0} max={1000} value={priority}
              onChange={(e) => setPriority(Number(e.target.value))} />
          </div>
        </div>
        <p className="rounded bg-slate-100 px-2 py-1.5 text-xs text-slate-600">
          💡 Editor สร้าง → status = pending_approval (รอ approver). Admin สร้าง → active เลย
        </p>
      </div>
    </Modal>
  );
}
