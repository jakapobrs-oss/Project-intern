// TypeScript types ที่ตรงกับ Pydantic schemas ของ backend
// ดู backend/app/schemas/*.py และ models/*.py

export type Role =
  | "super_admin"
  | "admin"
  | "editor"
  | "approver"
  | "viewer"
  | "operator"
  | "device";

export interface User {
  id: string;
  username: string;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
  /** admin สั่งล็อกด้วยมือ — ปลดได้ด้วยคนเท่านั้น */
  is_locked: boolean;
  /** ระบบล็อกชั่วคราวเพราะกรอกรหัสผิดเกินกำหนด — ถึงเวลานี้แล้วปลดเอง (null = ไม่ได้ถูกล็อก) */
  locked_until: string | null;
  created_at: string;
  updated_at: string;
  last_login_at: string | null;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  expires_in: number;
}

// ===== Device =====
export type DeviceStatus = "unpaired" | "online" | "offline" | "error";
export type DevicePlatform =
  | "android_tv"
  | "android_tablet"
  | "rpi_kiosk"
  | "windows_pc"
  | "web_browser"
  | "unknown";

export interface Device {
  id: string;
  name: string;
  location: string;
  pairing_code: string | null;
  pairing_code_expires_at: string | null;
  paired_at: string | null;
  platform: DevicePlatform;
  mac_address: string | null;
  ip_address: string | null;
  serial_number: string | null;
  tv_brand: string | null;
  tv_model: string | null;
  status: DeviceStatus;
  app_version: string | null;
  last_heartbeat_at: string | null;
  last_manifest_version: string | null;
  cpu_percent: number | null;
  temperature_c: number | null;
  uptime_sec: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface PlayerGroup {
  id: string;
  name: string;
  description: string;
  device_ids: string[];
  created_at: string;
  updated_at: string;
}

// ===== Content =====
export type ContentType = "image" | "video" | "web" | "stream" | "text";
export type ApprovalStatus = "draft" | "pending" | "approved" | "rejected";

export interface Content {
  id: string;
  name: string;
  description: string;
  type: ContentType;
  storage_key: string | null;
  mime_type: string | null;
  file_size: number | null;
  sha256: string | null;
  width: number | null;
  height: number | null;
  duration_sec: number | null;
  thumbnail_key: string | null;
  url: string | null;
  approval_status: ApprovalStatus;
  approved_by: string | null;
  approved_at: string | null;
  rejection_reason: string | null;
  expires_at: string | null;
  created_by: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ===== Presentation =====
export interface PresentationZone {
  id: string;
  zone_key: string;
  content_id: string;
  params_json: Record<string, unknown>;
  order_index: number;
}

export interface PresentationZoneIn {
  zone_key: string;
  content_id: string;
  params_json?: Record<string, unknown>;
  order_index: number;
}

export interface Presentation {
  id: string;
  name: string;
  description: string;
  layout_json: Record<string, unknown>;
  duration_sec: number;
  created_by: string;
  created_at: string;
  updated_at: string;
  zones: PresentationZone[];
}

// ===== Plan (playlist) =====
export interface PlanItem {
  id: string;
  presentation_id: string;
  order_index: number;
  duration_sec_override: number | null;
}

export interface PlanItemIn {
  presentation_id: string;
  order_index: number;
  duration_sec_override?: number | null;
}

export interface Plan {
  id: string;
  name: string;
  description: string;
  created_by: string;
  created_at: string;
  updated_at: string;
  items: PlanItem[];
}

// ===== Schedule =====
export type ScheduleStatus =
  | "draft"
  | "pending_approval"
  | "active"
  | "paused"
  | "expired";

export interface Schedule {
  id: string;
  name: string;
  description: string;
  plan_id: string;
  player_group_id: string;
  start_at: string;
  end_at: string | null;
  repeat_rule: string | null;
  daily_window_start: string | null;
  daily_window_end: string | null;
  priority: number;
  status: ScheduleStatus;
  created_by: string;
  approved_by: string | null;
  approved_at: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ===== Emergency =====
export type EmergencyKind = "text" | "image" | "url";
export type EmergencyStatus = "draft" | "active" | "expired" | "cancelled";

export interface EmergencyBroadcast {
  id: string;
  title: string;
  kind: EmergencyKind;
  payload: Record<string, unknown>;
  target: Record<string, unknown>;
  status: EmergencyStatus;
  priority: number;
  starts_at: string | null;
  ends_at: string | null;
  requires_ack: boolean;
  acknowledged_at: string | null;
  created_by: string;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

// ===== Audit =====
export type AuditOutcome = "success" | "fail" | "denied";

export interface AuditLog {
  id: string;
  actor_type: string;
  actor_id: string | null;
  actor_label: string | null;
  action: string;
  target_type: string | null;
  target_id: string | null;
  outcome: AuditOutcome;
  ip_address: string | null;
  user_agent: string | null;
  message: string | null;
  extra: Record<string, unknown> | null;
  created_at: string;
}

// ===== Helper: role labels =====
export const ROLE_LABELS: Record<Role, string> = {
  super_admin: "Super Admin",
  admin: "Admin",
  editor: "Editor",
  approver: "Approver",
  viewer: "Viewer",
  operator: "Operator",
  device: "Device",
};

export const STATUS_LABELS: Record<DeviceStatus, string> = {
  online: "ออนไลน์",
  offline: "ออฟไลน์",
  error: "ผิดพลาด",
  unpaired: "ยังไม่ผูก",
};
