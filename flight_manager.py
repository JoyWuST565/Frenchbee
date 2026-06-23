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
REFERENCE_OPTIONS_FILE = APP_DIR / "reference_options.json"
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
SIMPLE_TIME_RE = re.compile(r"^\d{4}$")
FLIGHT_NO_RE = re.compile(r"^[A-Z]{2}\d{1,4}$")
AIRPORT_RE = re.compile(r"^[A-Z]{3}$")
OPTION_FIELDS = {
    "aircraft_type": {
        "category": "aircraft_types",
        "label": "机型",
        "max_length": 25,
        "allow_rename": False,
    },
    "airline": {
        "category": "airlines",
        "label": "航司",
        "max_length": 25,
        "allow_rename": False,
    },
    "country_or_region": {
        "category": "countries_or_regions",
        "label": "国家/地区",
        "max_length": 50,
        "allow_rename": True,
    },
}
OPTION_CATEGORIES = {config["category"]: field for field, config in OPTION_FIELDS.items()}
HOUR_OPTIONS = [f"{hour:02d}" for hour in range(24)]
MINUTE_OPTIONS = [f"{minute:02d}" for minute in range(0, 60, 5)]


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


def normalize_options(values: list[str], max_length: int) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for value in values:
        item = str(value).strip()
        if not item or len(item) > max_length:
            continue
        key = item.casefold()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(item)
    return sorted(normalized, key=str.casefold)


def load_reference_options(path: Path = REFERENCE_OPTIONS_FILE) -> dict[str, list[str]]:
    if path.exists():
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    else:
        data = {}
    return {
        config["category"]: normalize_options(data.get(config["category"], []), config["max_length"])
        for config in OPTION_FIELDS.values()
    }


def save_reference_options(options: dict[str, list[str]], path: Path = REFERENCE_OPTIONS_FILE) -> None:
    payload = {
        config["category"]: normalize_options(options.get(config["category"], []), config["max_length"])
        for config in OPTION_FIELDS.values()
    }
    temp_name = ""
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False, prefix=".reference_options.", suffix=".tmp") as handle:
            temp_name = handle.name
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temp_name, path)
    except Exception:
        if temp_name and os.path.exists(temp_name):
            os.remove(temp_name)
        raise


def filter_options(values: list[str], term: str, limit: int = 80) -> list[str]:
    term = term.strip().casefold()
    if not term:
        return values[:limit]
    starts = [value for value in values if value.casefold().startswith(term)]
    contains = [value for value in values if term in value.casefold() and value not in starts]
    return (starts + contains)[:limit]


def normalize_time(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    if SIMPLE_TIME_RE.fullmatch(value):
        hour = int(value[:2])
        minute = int(value[2:])
        if hour > 23 or minute > 59:
            raise ValueError("简易时间必须为 0000 到 2359 之间的四位数字。")
        return f"{hour:02d}:{minute:02d}"
    match = re.fullmatch(r"(\d{1,2}):(\d{2})(?::\d{2})?", value)
    if not match:
        raise ValueError("时间格式应为 HH:MM 或四位数字，例如 08:30 或 0815。")
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
    for field in ("outbound_flight_no", "return_flight_no"):
        flight_no = record.get(field, "").strip().upper()
        if flight_no and not FLIGHT_NO_RE.fullmatch(flight_no):
            raise ValueError(f"{FIELD_LABELS[field]}应由两位英文字母和 1 至 4 位数字组成，例如 BF1、BF101、BF1001。")
    airport_code = record.get("airport_code", "").strip().upper()
    if airport_code and not AIRPORT_RE.fullmatch(airport_code):
        raise ValueError("机场代码应为三个英文字母，例如 RUN、JFK。")
    for field, config in OPTION_FIELDS.items():
        if len(record.get(field, "")) > config["max_length"]:
            raise ValueError(f"{FIELD_LABELS[field]}长度不能超过 {config['max_length']} 个字符。")
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


def same_airport_candidates(records: list[dict[str, str]], source: dict[str, str]) -> list[dict[str, str]]:
    airport_code = source.get("airport_code", "")
    if not airport_code:
        return []
    return [
        record
        for record in records
        if record.get("id") != source.get("id") and record.get("airport_code") == airport_code
    ]


def strong_pair_candidates(records: list[dict[str, str]], source: dict[str, str], original: dict[str, str] | None = None) -> list[dict[str, str]]:
    candidates = same_airport_candidates(records, source)
    original = original or source
    had_departure_only = bool(original.get("departure_time")) and not original.get("arrival_time")
    had_arrival_only = bool(original.get("arrival_time")) and not original.get("departure_time")
    if had_departure_only and source.get("arrival_time"):
        return [record for record in candidates if not record.get("route_pair_id") and record.get("arrival_time") == source.get("arrival_time")]
    if had_arrival_only and source.get("departure_time"):
        return [record for record in candidates if not record.get("route_pair_id") and record.get("departure_time") == source.get("departure_time")]
    return []


def sync_blank_pair_fields(left: dict[str, str], right: dict[str, str]) -> None:
    for field in REQUIRED_FIELDS:
        left_value = str(left.get(field, "")).strip()
        right_value = str(right.get(field, "")).strip()
        if left_value and not right_value:
            right[field] = left_value
        elif right_value and not left_value:
            left[field] = right_value
    timestamp = now_iso()
    left["updated_at"] = timestamp
    right["updated_at"] = timestamp


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


class OptionManagerDialog(Toplevel):
    def __init__(self, app: "FlightManagerApp", field: str, on_change=None):
        super().__init__(app.root)
        self.app = app
        self.field = field
        self.config_info = OPTION_FIELDS[field]
        self.category = self.config_info["category"]
        self.on_change = on_change
        self.search_text = StringVar()
        self.value_text = StringVar()
        self.item_values: dict[str, str] = {}
        self.title(f"{self.config_info['label']}管理")
        self.geometry("520x460")
        self.transient(app.root)
        self.grab_set()

        body = ttk.Frame(self, padding=14)
        body.pack(fill=BOTH, expand=True)

        top = ttk.Frame(body)
        top.pack(fill=X, pady=(0, 8))
        ttk.Label(top, text="检索").pack(side=LEFT, padx=(0, 6))
        search_entry = ttk.Entry(top, textvariable=self.search_text, width=30)
        search_entry.pack(side=LEFT, fill=X, expand=True)
        search_entry.bind("<KeyRelease>", lambda _event: self.refresh())
        ttk.Button(top, text="清空", command=self.clear_search).pack(side=LEFT, padx=(8, 0))

        self.table = ttk.Treeview(body, columns=("value",), show="headings", selectmode="browse")
        self.table.heading("value", text=self.config_info["label"])
        self.table.column("value", anchor="w", width=460)
        self.table.pack(fill=BOTH, expand=True, pady=(0, 10))
        self.table.bind("<<TreeviewSelect>>", lambda _event: self.load_selected())

        form = ttk.Frame(body)
        form.pack(fill=X)
        ttk.Label(form, text=f"名称（≤{self.config_info['max_length']}字符）").pack(side=LEFT, padx=(0, 6))
        value_entry = ttk.Entry(
            form,
            textvariable=self.value_text,
            width=28,
            validate="key",
            validatecommand=(self.register(self.limit_value), "%P"),
        )
        value_entry.pack(side=LEFT, fill=X, expand=True)

        buttons = ttk.Frame(body)
        buttons.pack(fill=X, pady=(10, 0))
        ttk.Button(buttons, text="新增", command=self.add_value).pack(side=LEFT, padx=(0, 8))
        if self.config_info["allow_rename"]:
            ttk.Button(buttons, text="修改选中", command=self.rename_selected).pack(side=LEFT, padx=(0, 8))
        ttk.Button(buttons, text="删除选中", command=self.delete_selected).pack(side=LEFT)
        ttk.Button(buttons, text="关闭", command=self.destroy).pack(side=RIGHT)

        self.refresh()
        search_entry.focus_set()

    def values(self) -> list[str]:
        return self.app.options.get(self.category, [])

    def limit_value(self, value: str) -> bool:
        return len(value) <= self.config_info["max_length"]

    def clear_search(self) -> None:
        self.search_text.set("")
        self.refresh()

    def refresh(self) -> None:
        self.table.delete(*self.table.get_children())
        self.item_values = {}
        for index, value in enumerate(filter_options(self.values(), self.search_text.get(), limit=500)):
            item_id = f"item-{index}"
            self.item_values[item_id] = value
            self.table.insert("", END, iid=item_id, values=(value,))

    def load_selected(self) -> None:
        selected = self.table.selection()
        if selected:
            self.value_text.set(self.item_values.get(selected[0], ""))

    def validate_new_value(self, value: str) -> str | None:
        value = value.strip()
        if not value:
            messagebox.showerror("名称为空", "请输入名称。", parent=self)
            return None
        if len(value) > self.config_info["max_length"]:
            messagebox.showerror("名称过长", f"名称长度不能超过 {self.config_info['max_length']} 个字符。", parent=self)
            return None
        if value.casefold() in {item.casefold() for item in self.values()}:
            messagebox.showerror("名称重复", "该名称已存在。", parent=self)
            return None
        return value

    def persist(self) -> None:
        self.app.options[self.category] = normalize_options(self.app.options.get(self.category, []), self.config_info["max_length"])
        save_reference_options(self.app.options)
        self.refresh()
        if self.on_change:
            self.on_change()

    def add_value(self) -> None:
        value = self.validate_new_value(self.value_text.get())
        if not value:
            return
        self.app.options.setdefault(self.category, []).append(value)
        self.persist()
        self.value_text.set(value)

    def rename_selected(self) -> None:
        selected = self.table.selection()
        if not selected:
            messagebox.showinfo("请选择项目", "请先选择要修改的名称。", parent=self)
            return
        old_value = self.item_values.get(selected[0], "")
        new_value = self.validate_new_value(self.value_text.get())
        if not new_value:
            return
        values = [new_value if value == old_value else value for value in self.values()]
        self.app.options[self.category] = values
        self.persist()
        self.value_text.set(new_value)

    def delete_selected(self) -> None:
        selected = self.table.selection()
        if not selected:
            messagebox.showinfo("请选择项目", "请先选择要删除的名称。", parent=self)
            return
        value = self.item_values.get(selected[0], "")
        if not messagebox.askyesno("确认删除", f"确定删除“{value}”吗？已在航班记录中使用的值不会被自动修改。", default=messagebox.NO, parent=self):
            return
        self.app.options[self.category] = [item for item in self.values() if item != value]
        self.persist()
        self.value_text.set("")


class FlightEditor(Toplevel):
    def __init__(self, app: "FlightManagerApp", record: dict[str, str] | None = None, focus_field: str | None = None):
        super().__init__(app.root)
        self.app = app
        self.original_id = record.get("id") if record else None
        self.record = copy.deepcopy(record) if record else blank_record()
        self.entries: dict[str, Entry] = {}
        self.option_combos: dict[str, ttk.Combobox] = {}
        self.time_widgets: dict[str, tuple[ttk.Combobox, ttk.Combobox]] = {}
        self.readonly_fields: set[str] = set()
        self.supplement_mode = bool(self.original_id and missing_fields(self.record))
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
            if self.supplement_mode and self.record.get(field, ""):
                self.readonly_fields.add(field)
                value_label = ttk.Label(body, text=self.record.get(field, ""), width=30, anchor="w", relief="sunken", padding=(4, 2))
                value_label.grid(row=row, column=1, sticky="we", pady=5)
            elif field in {"departure_time", "arrival_time"}:
                self.create_time_selector(body, row, field)
            elif field in OPTION_FIELDS:
                self.create_option_selector(body, row, field)
            else:
                variable = StringVar(value=self.record.get(field, ""))
                entry = ttk.Entry(body, textvariable=variable, width=30)
                entry.grid(row=row, column=1, sticky="we", pady=5)
                self.entries[field] = entry

        button_bar = ttk.Frame(body)
        button_bar.grid(row=len(REQUIRED_FIELDS) + 1 + row_offset, column=0, columnspan=3, sticky="e", pady=(14, 0))
        if self.original_id and self.app.get_counterparts(self.record):
            ttk.Button(button_bar, text="编辑对应航班", command=self.open_counterpart).pack(side=LEFT, padx=(0, 8))
        ttk.Button(button_bar, text="保存", command=self.save).pack(side=LEFT, padx=(0, 8))
        ttk.Button(button_bar, text="取消", command=self.destroy).pack(side=LEFT)

        target_field = focus_field or (missing_fields(self.record)[0] if missing_fields(self.record) else "outbound_flight_no")
        if self.entries:
            self.after(100, lambda: self.entries.get(target_field, next(iter(self.entries.values()))).focus_set())

    def create_time_selector(self, parent: ttk.Frame, row: int, field: str) -> None:
        frame = ttk.Frame(parent)
        frame.grid(row=row, column=1, sticky="w", pady=5)
        value = self.record.get(field, "")
        hour_value, minute_value = ("", "")
        if value and TIME_RE.fullmatch(value):
            hour_value, minute_value = value.split(":")
        hour_combo = ttk.Combobox(frame, width=5, values=HOUR_OPTIONS, textvariable=StringVar(value=hour_value))
        minute_values = MINUTE_OPTIONS if not minute_value or minute_value in MINUTE_OPTIONS else sorted({*MINUTE_OPTIONS, minute_value})
        minute_combo = ttk.Combobox(frame, width=5, values=minute_values, textvariable=StringVar(value=minute_value))
        hour_combo.pack(side=LEFT)
        ttk.Label(frame, text="时").pack(side=LEFT, padx=(4, 8))
        minute_combo.pack(side=LEFT)
        ttk.Label(frame, text="分").pack(side=LEFT, padx=(4, 0))
        hour_combo.bind("<KeyRelease>", lambda _event, combo=hour_combo: self.filter_static_combo(combo, HOUR_OPTIONS))
        minute_combo.bind("<KeyRelease>", lambda _event, combo=minute_combo: self.filter_static_combo(combo, MINUTE_OPTIONS))
        self.time_widgets[field] = (hour_combo, minute_combo)
        ttk.Label(parent, text="每 5 分钟", foreground="#6B7280").grid(row=row, column=2, sticky="w", padx=(8, 0))

    def create_option_selector(self, parent: ttk.Frame, row: int, field: str) -> None:
        config = OPTION_FIELDS[field]
        variable = StringVar(value=self.record.get(field, ""))
        combo = ttk.Combobox(
            parent,
            textvariable=variable,
            width=27,
            values=filter_options(self.app.option_values_for_field(field), variable.get()),
            validate="key",
            validatecommand=(self.register(lambda value, limit=config["max_length"]: len(value) <= limit), "%P"),
        )
        combo.grid(row=row, column=1, sticky="we", pady=5)
        combo.bind("<KeyRelease>", lambda _event, item=field: self.filter_option_combo(item))
        combo.bind("<Button-1>", lambda _event, item=field: self.filter_option_combo(item))
        self.option_combos[field] = combo
        ttk.Button(parent, text="管理", command=lambda item=field: self.open_option_manager(item)).grid(row=row, column=2, sticky="w", padx=(8, 0))

    def filter_static_combo(self, combo: ttk.Combobox, values: list[str]) -> None:
        combo.configure(values=filter_options(values, combo.get(), limit=len(values)))

    def filter_option_combo(self, field: str) -> None:
        combo = self.option_combos[field]
        combo.configure(values=filter_options(self.app.option_values_for_field(field), combo.get()))

    def refresh_option_combos(self) -> None:
        for field in self.option_combos:
            self.filter_option_combo(field)

    def open_option_manager(self, field: str) -> None:
        OptionManagerDialog(self.app, field, on_change=self.refresh_option_combos)

    def collect_time(self, field: str) -> str:
        hour_combo, minute_combo = self.time_widgets[field]
        hour = hour_combo.get().strip()
        minute = minute_combo.get().strip()
        if not hour and not minute:
            return ""
        if hour not in HOUR_OPTIONS or minute not in MINUTE_OPTIONS:
            raise ValueError(f"{FIELD_LABELS[field]}必须从小时 00-23 和分钟 00-55 的下拉列表中选择。")
        return f"{hour}:{minute}"

    def collect_record(self) -> dict[str, str]:
        record = copy.deepcopy(self.record)
        for field, entry in self.entries.items():
            record[field] = entry.get()
        for field, combo in self.option_combos.items():
            record[field] = combo.get()
        for field in self.time_widgets:
            record[field] = self.collect_time(field)
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
            self.app.validate_selected_options(record)
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

        original_snapshot = copy.deepcopy(self.record)
        self.app.persist_and_refresh(select_id=record["id"])
        if self.original_id and route_info_complete(record) and not record.get("route_pair_id"):
            self.destroy()
            self.app.root.after(50, lambda: self.app.try_auto_pair_existing(record["id"], original_snapshot))
            return
        show_counterpart_prompt = bool(self.original_id and self.app.get_counterparts(record))
        if missing_fields(record):
            messagebox.showwarning("待补录提醒", "该航线仍有字段未录入，已在提醒区标记。", parent=self)
        elif needs_pairing(record):
            messagebox.showwarning("待关联提醒", "该航线资料已完整，请继续手动关联对应的去程或回程航班。", parent=self)
        elif show_counterpart_prompt:
            self.app.show_counterpart_prompt(record["id"], parent=self)
        self.destroy()


class PairDialog(Toplevel):
    def __init__(self, app: "FlightManagerApp", source: dict[str, str], notice: str = "", same_airport_only: bool = True):
        super().__init__(app.root)
        self.app = app
        self.source = source
        self.notice = notice
        self.same_airport_only = same_airport_only
        self.filter_text = StringVar()
        self.title("关联去程/回程航班")
        self.geometry("850x500")
        self.transient(app.root)
        self.grab_set()

        body = ttk.Frame(self, padding=14)
        body.pack(fill=BOTH, expand=True)

        ttk.Label(body, text="当前航线").pack(anchor="w")
        ttk.Label(body, text=record_summary(source), foreground="#111827").pack(anchor="w", pady=(0, 10))
        if notice:
            ttk.Label(body, text=notice, foreground="#C2410C", wraplength=780).pack(anchor="w", pady=(0, 10))

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
            if self.same_airport_only and record.get("airport_code") != self.source.get("airport_code"):
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
        self.options = load_reference_options()
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

    def option_values_for_field(self, field: str) -> list[str]:
        config = OPTION_FIELDS[field]
        values = list(self.options.get(config["category"], []))
        values.extend(record.get(field, "") for record in self.records if record.get(field, ""))
        return normalize_options(values, config["max_length"])

    def validate_selected_options(self, record: dict[str, str]) -> None:
        for field in OPTION_FIELDS:
            value = record.get(field, "").strip()
            if not value:
                continue
            allowed = set(self.option_values_for_field(field))
            if value not in allowed:
                raise ValueError(f"{FIELD_LABELS[field]}必须从下拉列表中选择。若需要新增，请点击旁边的“管理”按钮。")

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
        PairDialog(self, record, notice="请从机场代码相同的现有航班中选择对应的去程或回程航班。")

    def try_auto_pair_existing(self, record_id: str, original_record: dict[str, str]) -> None:
        record = next((item for item in self.records if item.get("id") == record_id), None)
        if not record or record.get("route_pair_id") or not route_info_complete(record):
            return
        candidates = strong_pair_candidates(self.records, record, original_record)
        if len(candidates) == 1:
            self.associate_records(record_id, candidates[0]["id"], show_message=False)
            messagebox.showinfo(
                "已自动关联",
                "已根据机场代码和补录的对应起降时间，将该航班与现有单程记录关联，并同步补齐对方空白字段。",
                parent=self.root,
            )
            return
        if len(candidates) > 1:
            notice = "找到多个同机场、同对应时间的候选航班，请手动选择要关联的去程或回程航班。"
        else:
            notice = "未找到唯一的自动匹配项。请从机场代码相同的现有航班中手动选择对应的去程或回程航班。"
        PairDialog(self, record, notice=notice)

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

    def associate_records(self, source_id: str, target_id: str, parent=None, show_message: bool = True) -> bool:
        source = next((item for item in self.records if item.get("id") == source_id), None)
        target = next((item for item in self.records if item.get("id") == target_id), None)
        if not source or not target:
            messagebox.showerror("关联失败", "未找到需要关联的航线记录。", parent=parent or self.root)
            return False
        if source.get("airport_code") != target.get("airport_code"):
            messagebox.showerror("关联失败", "仅允许关联机场代码相同的去程/回程航班。", parent=parent or self.root)
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
        sync_blank_pair_fields(source, target)
        self.persist_and_refresh(select_id=source_id)
        if show_message:
            messagebox.showinfo("关联完成", "已关联所选去程/回程航班，并同步补齐对方空白字段。检索其中任一航班时，对应航班也会一起显示。", parent=parent or self.root)
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
