"use client";
// Contents — list + upload (file) + approve/reject workflow

import { useEffect, useRef, useState } from "react";
import { Upload, Check, X, RefreshCw } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { useAuth, hasRole } from "@/lib/auth";
import type { Content } from "@/lib/types";
import {
  Button,
  Card,
  CardBody,
  Input,
  Modal,
  StatusBadge,
  TBody,
  TD,
  TH,
  THead,
  Table,
  Empty,
  Spinner,
  Textarea,
} from "@/components/ui";
import { useToast } from "@/components/toast";

export default function ContentsPage() {
  const { user } = useAuth();
  const toast = useToast();
  const canUpload = hasRole(user, "super_admin", "admin", "editor");
  const canApprove = hasRole(user, "super_admin", "admin", "approver");

  const [items, setItems] = useState<Content[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [rejectFor, setRejectFor] = useState<Content | null>(null);

  const load = async () => {
    try {
      const list = await api.get<Content[]>("/contents");
      setItems(list);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "โหลด contents ไม่สำเร็จ");
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleSubmitForApproval = async (c: Content) => {
    try {
      const updated = await api.post<Content>(`/contents/${c.id}/submit`);
      setItems((prev) => prev?.map((x) => (x.id === c.id ? updated : x)) ?? null);
      toast.success("ส่งอนุมัติแล้ว");
    } catch (e) {
      toast.error("ส่งอนุมัติไม่สำเร็จ", e instanceof ApiError ? e.message : undefined);
    }
  };

  const handleApprove = async (c: Content) => {
    try {
      const updated = await api.post<Content>(`/contents/${c.id}/approve`, { approve: true });
      setItems((prev) => prev?.map((x) => (x.id === c.id ? updated : x)) ?? null);
      toast.success(`อนุมัติ "${c.name}"`);
    } catch (e) {
      toast.error("อนุมัติไม่สำเร็จ", e instanceof ApiError ? e.message : undefined);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-600">
          จัดการสื่อ (ภาพ / วิดีโอ / URL) + อนุมัติก่อนนำไปเล่น (§22)
        </p>
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={load}>
            <RefreshCw className="h-3.5 w-3.5" /> รีเฟรช
          </Button>
          {canUpload && (
            <Button size="sm" onClick={() => setUploadOpen(true)}>
              <Upload className="h-3.5 w-3.5" /> อัปโหลด
            </Button>
          )}
        </div>
      </div>

      {error && (
        <div className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
          {error}
        </div>
      )}

      {items === null ? (
        <div className="flex justify-center py-12">
          <Spinner className="h-5 w-5 text-brand-600" />
        </div>
      ) : items.length === 0 ? (
        <Empty title="ยังไม่มีสื่อ" description="กด 'อัปโหลด' เพื่อเพิ่มสื่อใหม่" />
      ) : (
        <Table>
          <THead>
            <tr>
              <TH>ชื่อ</TH>
              <TH>ประเภท</TH>
              <TH>ขนาด</TH>
              <TH>สถานะอนุมัติ</TH>
              <TH>วันที่สร้าง</TH>
              <TH className="text-right">การจัดการ</TH>
            </tr>
          </THead>
          <TBody>
            {items.map((c) => (
              <tr key={c.id} className="hover:bg-slate-50">
                <TD>
                  <div className="font-medium text-slate-900">{c.name}</div>
                  {c.description && (
                    <div className="text-xs text-slate-500 line-clamp-1">{c.description}</div>
                  )}
                </TD>
                <TD className="text-xs uppercase">{c.type}</TD>
                <TD className="text-xs">{c.file_size ? humanSize(c.file_size) : "—"}</TD>
                <TD>
                  <StatusBadge status={c.approval_status} />
                  {c.approval_status === "rejected" && c.rejection_reason && (
                    <div className="mt-0.5 text-xs text-rose-600">{c.rejection_reason}</div>
                  )}
                </TD>
                <TD className="text-xs text-slate-500">
                  {new Date(c.created_at).toLocaleDateString("th-TH")}
                </TD>
                <TD className="text-right">
                  {canUpload && c.approval_status === "draft" && (
                    <Button size="sm" variant="secondary" onClick={() => handleSubmitForApproval(c)}>
                      ส่งอนุมัติ
                    </Button>
                  )}
                  {canApprove && c.approval_status === "pending" && (
                    <>
                      <Button size="sm" variant="ghost" onClick={() => handleApprove(c)}>
                        <Check className="h-3.5 w-3.5 text-emerald-600" /> อนุมัติ
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => setRejectFor(c)}>
                        <X className="h-3.5 w-3.5 text-rose-600" /> ปฏิเสธ
                      </Button>
                    </>
                  )}
                </TD>
              </tr>
            ))}
          </TBody>
        </Table>
      )}

      <UploadModal
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        onUploaded={(c) => {
          setItems((prev) => (prev ? [c, ...prev] : [c]));
        }}
      />

      <RejectModal
        content={rejectFor}
        onClose={() => setRejectFor(null)}
        onRejected={(c) => {
          setItems((prev) => prev?.map((x) => (x.id === c.id ? c : x)) ?? null);
          setRejectFor(null);
        }}
      />
    </div>
  );
}

function UploadModal({
  open,
  onClose,
  onUploaded,
}: {
  open: boolean;
  onClose: () => void;
  onUploaded: (c: Content) => void;
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const reset = () => {
    setName("");
    setDescription("");
    setFile(null);
    setError(null);
  };

  const handleSubmit = async () => {
    setError(null);
    if (!file || !name.trim()) {
      setError("กรอก ชื่อ + เลือกไฟล์");
      return;
    }
    const form = new FormData();
    form.set("name", name.trim());
    form.set("description", description);
    form.set("file", file);
    setLoading(true);
    try {
      const c = await api.upload<Content>("/contents/upload", form);
      onUploaded(c);
      reset();
      onClose();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "อัปโหลดไม่สำเร็จ");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      open={open}
      onClose={() => {
        reset();
        onClose();
      }}
      title="อัปโหลดสื่อใหม่"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            ยกเลิก
          </Button>
          <Button onClick={handleSubmit} loading={loading}>
            อัปโหลด
          </Button>
        </>
      }
    >
      <div className="space-y-3">
        <div>
          <label className="mb-1 block text-sm font-medium">ชื่อ *</label>
          <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="ชื่อที่จะแสดงในระบบ" />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">คำอธิบาย</label>
          <Textarea
            rows={2}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="(ไม่บังคับ)"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">ไฟล์ *</label>
          <input
            ref={inputRef}
            type="file"
            accept="image/*,video/*"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="block w-full text-sm text-slate-700 file:mr-3 file:rounded file:border-0 file:bg-slate-100 file:px-3 file:py-1.5 file:text-sm file:font-medium hover:file:bg-slate-200"
          />
          {file && (
            <p className="mt-1 text-xs text-slate-500">
              {file.name} ({humanSize(file.size)})
            </p>
          )}
        </div>
        {error && <div className="text-sm text-rose-600">{error}</div>}
      </div>
    </Modal>
  );
}

function RejectModal({
  content,
  onClose,
  onRejected,
}: {
  content: Content | null;
  onClose: () => void;
  onRejected: (c: Content) => void;
}) {
  const [reason, setReason] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!content) {
      setReason("");
      setError(null);
    }
  }, [content]);

  if (!content) return null;

  const handleReject = async () => {
    if (!reason.trim()) {
      setError("ระบุเหตุผลในการปฏิเสธ");
      return;
    }
    setLoading(true);
    try {
      const updated = await api.post<Content>(`/contents/${content.id}/approve`, {
        approve: false,
        rejection_reason: reason.trim(),
      });
      onRejected(updated);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "ปฏิเสธไม่สำเร็จ");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      open={!!content}
      onClose={onClose}
      title={`ปฏิเสธ: ${content.name}`}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            ยกเลิก
          </Button>
          <Button variant="danger" onClick={handleReject} loading={loading}>
            ปฏิเสธ
          </Button>
        </>
      }
    >
      <div className="space-y-2">
        <label className="block text-sm font-medium">เหตุผล *</label>
        <Textarea rows={3} value={reason} onChange={(e) => setReason(e.target.value)} />
        {error && <div className="text-sm text-rose-600">{error}</div>}
      </div>
    </Modal>
  );
}

function humanSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 ** 3) return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
  return `${(bytes / 1024 ** 3).toFixed(2)} GB`;
}
