from __future__ import annotations

import copy
import json
import os
import re
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, TOP, VERTICAL, X, Y, Button, Entry, Label, StringVar, Tk, Toplevel, messagebox
from tkinter import ttk


APP_DIR = Path(__file__).resolve().parent
DATA_FILE = APP_DIR / "flight_schedule.json"
SCHEMA_VERSION = 1

FIELD_LABELS = {
    "outbound_flight_no": "去程航班号",
    "return_flight_no": "返程航班号",
    "airport_code": "机场代码",
    "departure_time": "离港时间",
    "arrival_time": "到达时间",
    "aircraft_type": "机型",
    "airline": "航司",
    "country_or_region": "国家/地区",
}

REQUIRED_FIELDS = tuple(FIELD_LABELS.keys())
DATA_FIELDS = (
    "id",
    "outbound_flight_no",
    "return_flight_no",
    "airport_code",
    "departure_time",
    "arrival_time",
    "aircraft_type",
    "airline",
    "country_or_region",
    "route_pair_id",
    "source",
    "updated_at",
)

TIME_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")
AIRPORT_RE = re.compile(r"^[A-Z0-9]{3}$")


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def blank_record() -> dict[str, str]:
    return {
        "id": f"route-{uuid.uuid4().hex[:12]}",
        "outbound_flight_no": "",
        "return_flight_no": "",
        "airport_code": "",
        "departure_time": "",
        "arrival_time": "",
        "aircraft_type": "",
        "airline": "",
        "country_or_region": "",
        "route_pair_id": "",
        "source": "manual",
        "updated_at": now_iso(),
    }


def new_pair_id() -> str:
    return f"pair-{uuid.uuid4().hex[:12]}"


def normalize_time(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    match = re.fullmatch(r"(\d{1,2}):(\d{2})(?::\d{2})?", value)
    if not match:
        raise ValueError("时间格式应为 HH:MM，例如 08:30。")
    hour = int(match.group(1))
    minute = int(match.group(2))
    if hour > 23 or minute > 59:
        raise ValueError("时间必须在 00:00 到 23:59 之间。")
    return f"{hour:02d}:{minute:02d}"


def normalize_record(record: dict) -> dict[str, str]:
    normalized = blank_record()
    normalized.update({key: "" if record.get(key) is None else str(record.get(key)) for key in DATA_FIELDS if key in record})
    normalized["id"] = normalized["id"] or f"route-{uuid.uuid4().hex[:12]}"
    normalized["outbound_flight_no"] = normalized["outbound_flight_no"].strip().upper()
    normalized["return_flight_no"] = normalized["return_flight_no"].strip().upper()
    normalized["airport_code"] = normalized["airport_code"].strip().upper()
    normalized["departure_time"] = normalize_time(normalized["departure_time"])
    normalized["arrival_time"] = normalize_time(normalized["arrival_time"])
    normalized["aircraft_type"] = normalized["aircraft_type"].strip()
    normalized["airline"] = normalized["airline"].strip()
    normalized["country_or_region"] = normalized["country_or_region"].strip()
    normalized["route_pair_id"] = normalized["route_pair_id"].strip()
    normalized["source"] = normalized["source"].strip() or "manual"
    normalized["updated_at"] = normalized["updated_at"].strip() or now_iso()
    return normalized


def missing_fields(record: dict[str, str]) -> list[str]:
    return [field for field in REQUIRED_FIELDS if not str(record.get(field, "")).strip()]


def route_info_complete(record: dict[str, str]) -> bool:
    return not missing_fields(record)


def needs_pairing(record: dict[str, str]) -> bool:
    return route_info_complete(record) and not record.get("route_pair_id", "").strip()


def route_status(record: dict[str, str]) -> str:
    if missing_fields(record):
        return "● 待补录"
    if needs_pairing(record):
        return "● 待关联"
    return "已关联"


def pair_display(record: dict[str, str]) -> str:
    pair_id = record.get("route_pair_id", "")
    return pair_id.replace("pair-", "") if pair_id else ""


def validate_record(record: dict[str, str]) -> None:
    airport_code = record.get("airport_code", "").strip().upper()
    if airport_code and not AIRPORT_RE.fullmatch(airport_code):
        raise ValueError("机场代码应为 3 位大写字母或数字。")
    normalize_time(record.get("departure_time", ""))
    normalize_time(record.get("arrival_time", ""))


def record_summary(record: dict[str, str]) -> str:
    flight_no = "/".join(part for part in (record.get("outbound_flight_no"), record.get("return_flight_no")) if part) or "未录入航班号"
    airport = record.get("airport_code") or "未录入机场"
    departure = record.get("departure_time") or "-"
    arrival = record.get("arrival_time") or "-"
    return f"{flight_no} | {airport} | 离港 {departure} | 到达 {arrival}"


def record_matches_criteria(record: dict[str, str], criteria: dict[str, str]) -> bool:
    flight_no = criteria.get("flight_no", "").strip().upper()
    airport_code = criteria.get("airport_code", "").strip().upper()
    departure_time = normalize_time(criteria.get("departure_time", ""))
    arrival_time = normalize_time(criteria.get("arrival_time", ""))

    if flight_no and flight_no not in {record.get("outbound_flight_no", "").upper(), record.get("return_flight_no", "").upper()}:
        return False
    if airport_code and airport_code != record.get("airport_code", "").upper():
        return False
    if departure_time and departure_time != record.get("departure_time", ""):
        return False
    if arrival_time and arrival_time != record.get("arrival_time", ""):
        return False
    return True


def has_active_criteria(criteria: dict[str, str]) -> bool:
    return any(str(value).strip() for value in criteria.values())


def expand_associated_records(records: list[dict[str, str]], matches: list[dict[str, str]]) -> list[dict[str, str]]:
    matched_ids = {record.get("id") for record in matches}
    pair_ids = {record.get("route_pair_id", "") for record in matches if record.get("route_pair_id", "").strip()}
    if not pair_ids:
        return matches
    return [
        record
        for record in records
        if record.get("id") in matched_ids or record.get("route_pair_id", "") in pair_ids
    ]


def filter_records(records: list[dict[str, str]], criteria: dict[str, str]) -> list[dict[str, str]]:
    matches = [record for record in records if record_matches_criteria(record, criteria)]
    if not has_active_criteria(criteria):
        return matches
    return expand_associated_records(records, matches)


def paired_group(records: list[dict[str, str]], record: dict[str, str]) -> list[dict[str, str]]:
    pair_id = record.get("route_pair_id", "")
    if not pair_id:
        return []
    return [item for item in records if item.get("route_pair_id") == pair_id]


def find_time_conflicts(records: list[dict[str, str]], candidate: dict[str, str], exclude_id: str | None = None) -> list[dict[str, str]]:
    conflicts: list[dict[str, str]] = []
    departure_time = candidate.get("departure_time", "")
    arrival_time = candidate.get("arrival_time", "")
    for record in records:
        if exclude_id and record.get("id") == exclude_id:
            continue
        if departure_time and record.get("departure_time") == departure_time:
            conflicts.append({"type": "离港", "time": departure_time, "record": record})
        if arrival_time and record.get("arrival_time") == arrival_time:
            conflicts.append({"type": "到达", "time": arrival_time, "record": record})
    return conflicts


def load_data(path: Path = DATA_FILE) -> dict:
    if not path.exists():
        return {"schema_version": SCHEMA_VERSION, "records": []}
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    records = [normalize_record(record) for record in data.get("records", [])]
    return {
        "schema_version": data.get("schema_version", SCHEMA_VERSION),
        "generated_from": data.get("generated_from", ""),
        "generated_at": data.get("generated_at", ""),
        "records": records,
    }


def save_data(data: dict, path: Path = DATA_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = copy.deepcopy(data)
    payload["schema_version"] = SCHEMA_VERSION
    payload["records"] = [normalize_record(record) for record in payload.get("records", [])]
    temp_name = ""
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False, prefix=".flight_schedule.", suffix=".tmp") as handle:
            temp_name = handle.name
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temp_name, path)
    except Exception:
        if temp_name and os.path.exists(temp_name):
            os.remove(temp_name)
        raise


class FlightEditor(Toplevel):
    def __init__(self, app: "FlightManagerApp", record: dict[str, str] | None = None, focus_field: str | None = None):
        super().__init__(app.root)
        self.app = app
        self.original_id = record.get("id") if record else None
        self.record = copy.deepcopy(record) if record else blank_record()
        self.entries: dict[str, Entry] = {}
        self.title("编辑航线" if record else "新增航线")
        self.resizable(False, False)
        self.transient(app.root)
        self.grab_set()

        body = ttk.Frame(self, padding=16)
        body.pack(fill=BOTH, expand=True)

        ttk.Label(body, text="带红点的字段需要补录", foreground="#B91C1C").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))
        if self.original_id and self.app.get_counterparts(self.record):
            ttk.Label(
                body,
                text="该航线已有关联航班。修改后请同步检查对应的去程或回程航班。",
                foreground="#C2410C",
            ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 8))
            row_offset = 1
        else:
            row_offset = 0

        for row, field in enumerate(REQUIRED_FIELDS, start=1 + row_offset):
            label_text = FIELD_LABELS[field]
            if field in missing_fields(self.record):
                label_text = f"● {label_text}"
            label = ttk.Label(body, text=label_text, foreground="#B91C1C" if field in missing_fields(self.record) else "#111827")
            label.grid(row=row, column=0, sticky="e", padx=(0, 8), pady=5)
            variable = StringVar(value=self.record.get(field, ""))
            entry = ttk.Entry(body, textvariable=variable, width=30)
            entry.grid(row=row, column=1, sticky="we", pady=5)
            self.entries[field] = entry
            if field in {"departure_time", "arrival_time"}:
                ttk.Label(body, text="HH:MM", foreground="#6B7280").grid(row=row, column=2, sticky="w", padx=(8, 0))

        button_bar = ttk.Frame(body)
        button_bar.grid(row=len(REQUIRED_FIELDS) + 1 + row_offset, column=0, columnspan=3, sticky="e", pady=(14, 0))
        if self.original_id and self.app.get_counterparts(self.record):
            ttk.Button(button_bar, text="编辑对应航班", command=self.open_counterpart).pack(side=LEFT, padx=(0, 8))
        ttk.Button(button_bar, text="保存", command=self.save).pack(side=LEFT, padx=(0, 8))
        ttk.Button(button_bar, text="取消", command=self.destroy).pack(side=LEFT)

        target_field = focus_field or (missing_fields(self.record)[0] if missing_fields(self.record) else "outbound_flight_no")
        self.after(100, lambda: self.entries.get(target_field, next(iter(self.entries.values()))).focus_set())

    def collect_record(self) -> dict[str, str]:
        record = copy.deepcopy(self.record)
        for field, entry in self.entries.items():
            record[field] = entry.get()
        record["airport_code"] = record.get("airport_code", "").upper()
        record["outbound_flight_no"] = record.get("outbound_flight_no", "").upper()
        record["return_flight_no"] = record.get("return_flight_no", "").upper()
        record["updated_at"] = now_iso()
        return normalize_record(record)

    def open_counterpart(self) -> None:
        if self.original_id:
            self.app.open_counterpart_editor(self.original_id, parent=self)

    def save(self) -> None:
        try:
            record = self.collect_record()
            validate_record(record)
        except ValueError as exc:
            messagebox.showerror("输入有误", str(exc), parent=self)
            return

        if not self.original_id and missing_fields(record):
            first_missing = missing_fields(record)[0]
            messagebox.showerror(
                "信息未填写完整",
                "新增航线必须填写全部字段后才能保存。\n\n缺失：" + "、".join(FIELD_LABELS[field] for field in missing_fields(record)),
                parent=self,
            )
            self.entries[first_missing].focus_set()
            return

        if not self.original_id and route_info_complete(record) and not record.get("route_pair_id"):
            record["route_pair_id"] = new_pair_id()

        conflicts = find_time_conflicts(self.app.records, record, exclude_id=self.original_id)
        if conflicts:
            lines = []
            for conflict in conflicts[:12]:
                lines.append(f"{conflict['type']} {conflict['time']} 已占用：{record_summary(conflict['record'])}")
            if len(conflicts) > 12:
                lines.append(f"另有 {len(conflicts) - 12} 条冲突未显示。")
            message = "检测到时间占用：\n\n" + "\n".join(lines) + "\n\n是否仍然保存？"
            if not messagebox.askyesno("时间已占用", message, default=messagebox.NO, parent=self):
                return

        if self.original_id:
            for index, existing in enumerate(self.app.records):
                if existing.get("id") == self.original_id:
                    self.app.records[index] = record
                    break
        else:
            self.app.records.append(record)

        self.app.persist_and_refresh(select_id=record["id"])
        show_counterpart_prompt = bool(self.original_id and self.app.get_counterparts(record))
        if missing_fields(record):
            messagebox.showwarning("待补录提醒", "该航线仍有字段未录入，已在提醒区标记。", parent=self)
        elif needs_pairing(record):
            messagebox.showwarning("待关联提醒", "该航线资料已完整，请继续手动关联对应的去程或回程航班。", parent=self)
        elif show_counterpart_prompt:
            self.app.show_counterpart_prompt(record["id"], parent=self)
        self.destroy()


class PairDialog(Toplevel):
    def __init__(self, app: "FlightManagerApp", source: dict[str, str]):
        super().__init__(app.root)
        self.app = app
        self.source = source
        self.filter_text = StringVar()
        self.title("关联去程/回程航班")
        self.geometry("850x500")
        self.transient(app.root)
        self.grab_set()

        body = ttk.Frame(self, padding=14)
        body.pack(fill=BOTH, expand=True)

        ttk.Label(body, text="当前航线").pack(anchor="w")
        ttk.Label(body, text=record_summary(source), foreground="#111827").pack(anchor="w", pady=(0, 10))

        search_bar = ttk.Frame(body)
        search_bar.pack(fill=X, pady=(0, 8))
        ttk.Label(search_bar, text="筛选候选").pack(side=LEFT, padx=(0, 6))
        search_entry = ttk.Entry(search_bar, textvariable=self.filter_text, width=28)
        search_entry.pack(side=LEFT)
        search_entry.bind("<KeyRelease>", lambda _event: self.refresh_candidates())
        ttk.Button(search_bar, text="清空", command=self.clear_filter).pack(side=LEFT, padx=(8, 0))

        columns = ("summary", "status", "pair")
        self.candidates = ttk.Treeview(body, columns=columns, show="headings", selectmode="browse")
        self.candidates.heading("summary", text="候选航线")
        self.candidates.heading("status", text="状态")
        self.candidates.heading("pair", text="关联ID")
        self.candidates.column("summary", width=560, anchor="w")
        self.candidates.column("status", width=90, anchor="center")
        self.candidates.column("pair", width=120, anchor="center")
        self.candidates.pack(fill=BOTH, expand=True)
        self.candidates.bind("<Double-1>", lambda _event: self.apply_pair())

        button_bar = ttk.Frame(body)
        button_bar.pack(fill=X, pady=(10, 0))
        ttk.Button(button_bar, text="关联选中航线", command=self.apply_pair).pack(side=LEFT)
        ttk.Button(button_bar, text="关闭", command=self.destroy).pack(side=RIGHT)

        self.refresh_candidates()
        search_entry.focus_set()

    def clear_filter(self) -> None:
        self.filter_text.set("")
        self.refresh_candidates()

    def refresh_candidates(self) -> None:
        term = self.filter_text.get().strip().upper()
        self.candidates.delete(*self.candidates.get_children())
        for record in self.app.records:
            if record.get("id") == self.source.get("id"):
                continue
            summary = record_summary(record)
            searchable = " ".join(
                str(record.get(field, ""))
                for field in ("outbound_flight_no", "return_flight_no", "airport_code", "departure_time", "arrival_time")
            ).upper()
            if term and term not in searchable and term not in summary.upper():
                continue
            self.candidates.insert(
                "",
                END,
                iid=record["id"],
                values=(summary, route_status(record), pair_display(record)),
            )

    def apply_pair(self) -> None:
        selected = self.candidates.selection()
        if not selected:
            messagebox.showinfo("请选择候选航线", "请先选择要关联的去程或回程航班记录。", parent=self)
            return
        target_id = selected[0]
        if self.app.associate_records(self.source["id"], target_id, parent=self):
            self.destroy()


class FlightManagerApp:
    def __init__(self, root: Tk):
        self.root = root
        self.root.title("航班航线本地管理")
        self.root.geometry("1180x760")
        self.data = load_data()
        self.records: list[dict[str, str]] = self.data["records"]
        self.current_results: list[dict[str, str]] = []
        self.search_vars = {
            "flight_no": StringVar(),
            "airport_code": StringVar(),
            "departure_time": StringVar(),
            "arrival_time": StringVar(),
        }
        self.status_var = StringVar()
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root_frame = ttk.Frame(self.root, padding=12)
        root_frame.pack(fill=BOTH, expand=True)

        search_frame = ttk.LabelFrame(root_frame, text="精准查询", padding=10)
        search_frame.pack(fill=X)

        search_fields = [
            ("flight_no", "航班号"),
            ("airport_code", "机场代码"),
            ("departure_time", "离港时间"),
            ("arrival_time", "到达时间"),
        ]
        for col, (key, label_text) in enumerate(search_fields):
            ttk.Label(search_frame, text=label_text).grid(row=0, column=col * 2, sticky="e", padx=(0, 6))
            entry = ttk.Entry(search_frame, textvariable=self.search_vars[key], width=14)
            entry.grid(row=0, column=col * 2 + 1, sticky="w", padx=(0, 14))
            entry.bind("<Return>", lambda _event: self.apply_search())

        ttk.Button(search_frame, text="查询", command=self.apply_search).grid(row=0, column=8, padx=(4, 6))
        ttk.Button(search_frame, text="清空", command=self.clear_search).grid(row=0, column=9, padx=(0, 6))
        ttk.Button(search_frame, text="新增航线", command=self.add_record).grid(row=0, column=10, padx=(0, 6))
        ttk.Button(search_frame, text="编辑选中", command=self.edit_selected).grid(row=0, column=11, padx=(0, 6))
        ttk.Button(search_frame, text="关联选中", command=self.pair_selected).grid(row=0, column=12, padx=(0, 6))
        ttk.Button(search_frame, text="取消关联", command=self.clear_selected_pair).grid(row=0, column=13, padx=(0, 6))
        ttk.Button(search_frame, text="删除选中", command=self.delete_selected).grid(row=0, column=14)

        content = ttk.PanedWindow(root_frame, orient="horizontal")
        content.pack(fill=BOTH, expand=True, pady=(12, 8))

        table_frame = ttk.Frame(content)
        reminder_frame = ttk.LabelFrame(content, text="待补录提醒", padding=10)
        content.add(table_frame, weight=4)
        content.add(reminder_frame, weight=2)

        columns = (
            "status",
            "outbound_flight_no",
            "return_flight_no",
            "airport_code",
            "departure_time",
            "arrival_time",
            "aircraft_type",
            "airline",
            "country_or_region",
            "route_pair_id",
            "source",
        )
        self.table = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        headings = {
            "status": "状态",
            "outbound_flight_no": "去程航班号",
            "return_flight_no": "返程航班号",
            "airport_code": "机场",
            "departure_time": "离港",
            "arrival_time": "到达",
            "aircraft_type": "机型",
            "airline": "航司",
            "country_or_region": "国家/地区",
            "route_pair_id": "关联ID",
            "source": "来源",
        }
        widths = {
            "status": 95,
            "outbound_flight_no": 100,
            "return_flight_no": 100,
            "airport_code": 70,
            "departure_time": 70,
            "arrival_time": 70,
            "aircraft_type": 90,
            "airline": 110,
            "country_or_region": 120,
            "route_pair_id": 95,
            "source": 120,
        }
        for column in columns:
            self.table.heading(column, text=headings[column])
            self.table.column(column, width=widths[column], anchor="center", stretch=column in {"airline", "country_or_region", "source"})

        yscroll = ttk.Scrollbar(table_frame, orient=VERTICAL, command=self.table.yview)
        self.table.configure(yscrollcommand=yscroll.set)
        self.table.pack(side=LEFT, fill=BOTH, expand=True)
        yscroll.pack(side=RIGHT, fill=Y)
        self.table.tag_configure("missing", foreground="#B91C1C")
        self.table.tag_configure("pairing", foreground="#C2410C")
        self.table.tag_configure("complete", foreground="#065F46")
        self.table.bind("<Double-1>", lambda _event: self.edit_selected())

        self.reminder_note = ttk.Label(reminder_frame, text="单击待补录项打开编辑；单击待关联项打开关联窗口。", foreground="#B91C1C", wraplength=320)
        self.reminder_note.pack(anchor="w", pady=(0, 8))
        reminder_columns = ("summary", "missing")
        self.reminders = ttk.Treeview(reminder_frame, columns=reminder_columns, show="headings", selectmode="browse", height=18)
        self.reminders.heading("summary", text="航线")
        self.reminders.heading("missing", text="提醒事项")
        self.reminders.column("summary", width=210, anchor="w")
        self.reminders.column("missing", width=210, anchor="w")
        reminder_scroll = ttk.Scrollbar(reminder_frame, orient=VERTICAL, command=self.reminders.yview)
        self.reminders.configure(yscrollcommand=reminder_scroll.set)
        self.reminders.pack(side=LEFT, fill=BOTH, expand=True)
        reminder_scroll.pack(side=RIGHT, fill=Y)
        self.reminders.tag_configure("missing", foreground="#B91C1C")
        self.reminders.tag_configure("pairing", foreground="#C2410C")
        self.reminders.bind("<ButtonRelease-1>", self.open_reminder_from_click)

        status_bar = ttk.Frame(root_frame)
        status_bar.pack(fill=X)
        ttk.Label(status_bar, textvariable=self.status_var, foreground="#374151").pack(side=LEFT)
        ttk.Label(status_bar, text=f"数据文件：{DATA_FILE.name}", foreground="#6B7280").pack(side=RIGHT)

    def apply_search(self) -> None:
        try:
            self.refresh()
        except ValueError as exc:
            messagebox.showerror("查询条件有误", str(exc), parent=self.root)

    def clear_search(self) -> None:
        for variable in self.search_vars.values():
            variable.set("")
        self.refresh()

    def get_criteria(self) -> dict[str, str]:
        return {key: variable.get() for key, variable in self.search_vars.items()}

    def refresh(self, select_id: str | None = None) -> None:
        criteria = self.get_criteria()
        self.current_results = filter_records(self.records, criteria)
        self.table.delete(*self.table.get_children())
        for record in self.current_results:
            missing = missing_fields(record)
            status = route_status(record)
            values = (
                status,
                record.get("outbound_flight_no", ""),
                record.get("return_flight_no", ""),
                record.get("airport_code", ""),
                record.get("departure_time", ""),
                record.get("arrival_time", ""),
                record.get("aircraft_type", ""),
                record.get("airline", ""),
                record.get("country_or_region", ""),
                pair_display(record),
                record.get("source", ""),
            )
            tag = "missing" if missing else "pairing" if needs_pairing(record) else "complete"
            self.table.insert("", END, iid=record["id"], values=values, tags=(tag,))
        self.refresh_reminders()
        if select_id and self.table.exists(select_id):
            self.table.selection_set(select_id)
            self.table.focus(select_id)
            self.table.see(select_id)
        missing_count = sum(1 for record in self.records if missing_fields(record))
        pairing_count = sum(1 for record in self.records if needs_pairing(record))
        self.status_var.set(f"共 {len(self.records)} 条记录，当前显示 {len(self.current_results)} 条，待补录 {missing_count} 条，待关联 {pairing_count} 条")

    def refresh_reminders(self) -> None:
        self.reminders.delete(*self.reminders.get_children())
        for record in self.records:
            missing = missing_fields(record)
            if missing:
                labels = "缺失：" + "、".join(FIELD_LABELS[field] for field in missing)
                self.reminders.insert("", END, iid=record["id"], values=(record_summary(record), labels), tags=("missing",))
            elif needs_pairing(record):
                self.reminders.insert("", END, iid=record["id"], values=(record_summary(record), "需关联去程/回程航班"), tags=("pairing",))

    def persist_and_refresh(self, select_id: str | None = None) -> None:
        self.data["records"] = self.records
        save_data(self.data)
        self.refresh(select_id=select_id)

    def selected_record(self) -> dict[str, str] | None:
        selected = self.table.selection()
        if not selected:
            messagebox.showinfo("请选择记录", "请先在主列表中选择一条航线记录。", parent=self.root)
            return None
        record_id = selected[0]
        return next((record for record in self.records if record.get("id") == record_id), None)

    def add_record(self) -> None:
        FlightEditor(self)

    def edit_selected(self) -> None:
        record = self.selected_record()
        if record:
            FlightEditor(self, record)

    def edit_record_by_id(self, record_id: str, focus_field: str | None = None) -> None:
        record = next((item for item in self.records if item.get("id") == record_id), None)
        if not record:
            return
        self.table.selection_set(record_id) if self.table.exists(record_id) else None
        FlightEditor(self, record, focus_field=focus_field)

    def pair_selected(self) -> None:
        record = self.selected_record()
        if record:
            self.open_pair_dialog(record)

    def open_pair_dialog(self, record: dict[str, str]) -> None:
        if missing_fields(record):
            messagebox.showwarning("请先补录", "该航线仍有必填信息未录入，请补录完整后再关联去程或回程航班。", parent=self.root)
            FlightEditor(self, record, focus_field=missing_fields(record)[0])
            return
        PairDialog(self, record)

    def get_counterparts(self, record: dict[str, str]) -> list[dict[str, str]]:
        return [item for item in paired_group(self.records, record) if item.get("id") != record.get("id")]

    def open_counterpart_editor(self, record_id: str, parent=None) -> None:
        record = next((item for item in self.records if item.get("id") == record_id), None)
        if not record:
            return
        counterparts = self.get_counterparts(record)
        if not counterparts:
            messagebox.showinfo("暂无对应航班", "该记录当前没有可跳转的对应去程或回程航班。", parent=parent or self.root)
            return
        if len(counterparts) > 1:
            messagebox.showinfo("存在多个关联记录", "该关联组存在多条对应记录，将打开第一条；也可在主列表中逐条选择编辑。", parent=parent or self.root)
        FlightEditor(self, counterparts[0])

    def show_counterpart_prompt(self, record_id: str, parent=None) -> None:
        record = next((item for item in self.records if item.get("id") == record_id), None)
        if not record or not self.get_counterparts(record):
            return
        prompt = Toplevel(self.root)
        prompt.title("检查对应航班")
        prompt.resizable(False, False)
        prompt.transient(self.root)
        prompt.grab_set()

        body = ttk.Frame(prompt, padding=16)
        body.pack(fill=BOTH, expand=True)
        ttk.Label(body, text="该航线已保存。请同步检查并修改其对应的去程或回程航班。", foreground="#C2410C", wraplength=360).pack(anchor="w", pady=(0, 10))
        ttk.Label(body, text=record_summary(record), wraplength=360).pack(anchor="w", pady=(0, 12))
        button_bar = ttk.Frame(body)
        button_bar.pack(fill=X)
        ttk.Button(button_bar, text="编辑对应航班", command=lambda: (prompt.destroy(), self.open_counterpart_editor(record_id))).pack(side=LEFT)
        ttk.Button(button_bar, text="稍后处理", command=prompt.destroy).pack(side=RIGHT)

    def associate_records(self, source_id: str, target_id: str, parent=None) -> bool:
        source = next((item for item in self.records if item.get("id") == source_id), None)
        target = next((item for item in self.records if item.get("id") == target_id), None)
        if not source or not target:
            messagebox.showerror("关联失败", "未找到需要关联的航线记录。", parent=parent or self.root)
            return False
        source_pair = source.get("route_pair_id", "")
        target_pair = target.get("route_pair_id", "")
        pair_id = source_pair or target_pair or new_pair_id()

        if source_pair and target_pair and source_pair != target_pair:
            if not messagebox.askyesno(
                "合并关联",
                "两条记录已有不同关联。是否将两个关联组合并为同一组？",
                default=messagebox.NO,
                parent=parent or self.root,
            ):
                return False
            for record in self.records:
                if record.get("route_pair_id") == target_pair:
                    record["route_pair_id"] = pair_id
                    record["updated_at"] = now_iso()

        for record in (source, target):
            record["route_pair_id"] = pair_id
            record["updated_at"] = now_iso()
        self.persist_and_refresh(select_id=source_id)
        messagebox.showinfo("关联完成", "已关联所选去程/回程航班。检索其中任一航班时，对应航班也会一起显示。", parent=parent or self.root)
        return True

    def clear_selected_pair(self) -> None:
        record = self.selected_record()
        if not record:
            return
        pair_id = record.get("route_pair_id", "")
        if not pair_id:
            messagebox.showinfo("无需取消", "该记录当前没有关联航班。", parent=self.root)
            return
        related = [item for item in self.records if item.get("route_pair_id") == pair_id]
        if not messagebox.askyesno(
            "取消关联",
            f"确定取消该关联组吗？共有 {len(related)} 条记录会被取消关联。",
            default=messagebox.NO,
            parent=self.root,
        ):
            return
        for item in related:
            item["route_pair_id"] = ""
            item["updated_at"] = now_iso()
        self.persist_and_refresh(select_id=record["id"])

    def delete_selected(self) -> None:
        record = self.selected_record()
        if not record:
            return
        group = paired_group(self.records, record)
        if not group:
            messagebox.showwarning(
                "不允许单独删除",
                "该记录尚未关联对应的去程或回程航班。系统只允许删除一对往返航班，请先完成关联后再删除。",
                parent=self.root,
            )
            return
        lines = "\n".join(f"- {record_summary(item)}" for item in group)
        if not messagebox.askyesno(
            "确认删除往返航班",
            "删除操作将一并删除该关联组内的去程/回程航班，不允许仅删除其中任一单个航班。\n\n"
            f"将删除 {len(group)} 条记录：\n{lines}\n\n是否一键删除整组？",
            default=messagebox.NO,
            parent=self.root,
        ):
            return
        delete_ids = {item["id"] for item in group}
        self.records = [item for item in self.records if item.get("id") not in delete_ids]
        self.persist_and_refresh()

    def open_reminder_from_click(self, event) -> None:
        row_id = self.reminders.identify_row(event.y)
        if not row_id:
            return
        record = next((item for item in self.records if item.get("id") == row_id), None)
        if not record:
            return
        if missing_fields(record):
            self.edit_record_by_id(row_id, focus_field=missing_fields(record)[0])
        elif needs_pairing(record):
            self.open_pair_dialog(record)


def main() -> None:
    root = Tk()
    ttk.Style().theme_use("clam")
    app = FlightManagerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
