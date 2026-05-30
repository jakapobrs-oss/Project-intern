#!/usr/bin/env python3
"""Render ER diagram (PNG + SVG) for Digital Signage Management System using graphviz."""
from graphviz import Digraph

g = Digraph("ER", format="png")
g.attr(rankdir="LR", splines="spline", nodesep="0.5", ranksep="1.1",
       bgcolor="white", fontname="Helvetica")
g.attr("node", shape="plaintext", fontname="Helvetica")
g.attr("edge", fontname="Helvetica", fontsize="10", color="#555555")

GROUPS = {
    "identity": "#E8D5F2",   # purple
    "device":   "#D5E8F2",   # blue
    "content":  "#FCE7C8",   # orange
    "playlist": "#D7F2D5",   # green
    "emergency":"#F2D5D5",   # red
}

def table(name, title, rows, color):
    cells = "".join(
        f'<TR><TD ALIGN="LEFT" PORT="{k}"><B>{k}</B></TD>'
        f'<TD ALIGN="LEFT">{t}</TD></TR>' for k, t in rows
    )
    label = (
        f'<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4">'
        f'<TR><TD COLSPAN="2" BGCOLOR="{color}"><B>{title}</B></TD></TR>'
        f'{cells}</TABLE>>'
    )
    g.node(name, label=label)

# ---- Identity & Audit ----
table("users", "users", [
    ("id", "uuid PK"), ("username", "string UK"), ("email", "string UK"),
    ("password_hash", "string"), ("role", "enum (7 roles)"),
    ("is_active", "bool"), ("is_locked", "bool"),
    ("failed_login_count", "int"), ("last_login_at", "datetime"),
], GROUPS["identity"])
table("audit_logs", "audit_logs", [
    ("id", "uuid PK"), ("actor_type", "string"), ("actor_id", "string (no FK)"),
    ("action", "string"), ("target_type", "string"), ("target_id", "string"),
    ("outcome", "enum"), ("created_at", "datetime"),
], GROUPS["identity"])

# ---- Devices ----
table("devices", "devices", [
    ("id", "uuid PK"), ("name", "string"), ("location", "string"),
    ("pairing_code", "string UK"), ("platform", "enum"),
    ("tv_brand", "string"), ("status", "enum"),
    ("last_heartbeat_at", "datetime"),
], GROUPS["device"])
table("player_groups", "player_groups", [
    ("id", "uuid PK"), ("name", "string UK"), ("description", "string"),
], GROUPS["device"])
table("player_group_members", "player_group_members", [
    ("player_group_id", "uuid PK,FK"), ("device_id", "uuid PK,FK"),
], GROUPS["device"])

# ---- Content & Composition ----
table("contents", "contents", [
    ("id", "uuid PK"), ("name", "string"), ("type", "enum"),
    ("storage_key", "string"), ("sha256", "string (dedupe)"),
    ("approval_status", "enum"), ("approved_by", "uuid FK"),
    ("created_by", "uuid FK"),
], GROUPS["content"])
table("presentations", "presentations", [
    ("id", "uuid PK"), ("name", "string"), ("layout_json", "json"),
    ("duration_sec", "int"), ("created_by", "uuid FK"),
], GROUPS["content"])
table("presentation_zones", "presentation_zones", [
    ("id", "uuid PK"), ("presentation_id", "uuid FK"),
    ("content_id", "uuid FK"), ("zone_key", "string"),
    ("params_json", "json"), ("order_index", "int"),
], GROUPS["content"])

# ---- Playlists & Schedules ----
table("plans", "plans", [
    ("id", "uuid PK"), ("name", "string UK"), ("created_by", "uuid FK"),
], GROUPS["playlist"])
table("plan_items", "plan_items", [
    ("id", "uuid PK"), ("plan_id", "uuid FK"),
    ("presentation_id", "uuid FK"), ("order_index", "int"),
    ("duration_sec_override", "int"),
], GROUPS["playlist"])
table("schedules", "schedules", [
    ("id", "uuid PK"), ("name", "string"), ("plan_id", "uuid FK"),
    ("player_group_id", "uuid FK"), ("start_at", "datetime"),
    ("end_at", "datetime"), ("repeat_rule", "RRULE"),
    ("priority", "int"), ("status", "enum"),
    ("created_by", "uuid FK"), ("approved_by", "uuid FK"),
], GROUPS["playlist"])

# ---- Emergency ----
table("emergency_broadcasts", "emergency_broadcasts", [
    ("id", "uuid PK"), ("title", "string"), ("kind", "enum"),
    ("payload", "json"), ("target", "json"), ("status", "enum"),
    ("priority", "int"), ("starts_at", "datetime"),
    ("ends_at", "datetime"), ("created_by", "uuid (no FK)"),
], GROUPS["emergency"])

# ---- Relationships ----
def rel(a, b, label, dashed=False):
    g.edge(a, b, label=label, style="dashed" if dashed else "solid",
           arrowhead="crow", arrowtail="none", dir="both", taillabel="1")

rel("users", "contents", "created_by")
rel("users", "contents", "approved_by")
rel("users", "presentations", "created_by")
rel("users", "plans", "created_by")
rel("users", "schedules", "created_by")
rel("users", "schedules", "approved_by")
rel("player_groups", "player_group_members", "members")
rel("devices", "player_group_members", "members")
rel("presentations", "presentation_zones", "has zones")
rel("contents", "presentation_zones", "shown in")
rel("plans", "plan_items", "ordered items")
rel("presentations", "plan_items", "referenced by")
rel("plans", "schedules", "scheduled as")
rel("player_groups", "schedules", "target")
rel("users", "audit_logs", "logical (no FK)", dashed=True)
rel("users", "emergency_broadcasts", "created_by (no FK)", dashed=True)

g.render("er-diagram", cleanup=True)        # er-diagram.png
g.format = "svg"
g.render("er-diagram", cleanup=True)         # er-diagram.svg
print("rendered er-diagram.png + er-diagram.svg")
