from __future__ import annotations

import copy
import csv
import importlib
import json
import os
import re
import shutil
import sqlite3
import sys
import tempfile
import uuid
import webbrowser
import zipfile
from contextlib import closing
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape


def runtime_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.argv[0]).resolve().parent
    return Path(__file__).resolve().parent


def resource_dir() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def load_tkinter_runtime():
    if getattr(sys, "frozen", False):
        resources = resource_dir()
        if str(resources) not in sys.path:
            sys.path.insert(0, str(resources))
        os.environ.setdefault("TCL_LIBRARY", str(resources / "tcl" / "tcl8.6"))
        os.environ.setdefault("TK_LIBRARY", str(resources / "tcl" / "tk8.6"))
    tk_module = importlib.import_module("tkinter")
    ttk_module = importlib.import_module("tkinter.ttk")
    filedialog_module = importlib.import_module("tkinter.filedialog")
    messagebox_module = importlib.import_module("tkinter.messagebox")
    return tk_module, ttk_module, filedialog_module, messagebox_module


tk, ttk, filedialog, messagebox = load_tkinter_runtime()
BOTH = tk.BOTH
END = tk.END
LEFT = tk.LEFT
RIGHT = tk.RIGHT
TOP = tk.TOP
VERTICAL = tk.VERTICAL
X = tk.X
Y = tk.Y
Button = tk.Button
Entry = tk.Entry
Label = tk.Label
StringVar = tk.StringVar
Tk = tk.Tk
Toplevel = tk.Toplevel


APP_NAME = "Frenchbee Flight Manager"
APP_DISPLAY_NAME = "Frenchbee 航班航线管理"
APP_VERSION = "1.2.0"
APP_AUTHOR = "JoyWuST565"
GITHUB_URL = "https://github.com/JoyWuST565/Frenchbee"
APP_DIR = runtime_dir()
RESOURCE_DIR = resource_dir()
DB_FILE = APP_DIR / "flight_schedule.db"
BUNDLED_DB_FILE = RESOURCE_DIR / "flight_schedule.db"
RUNTIME_DATA_FILE = APP_DIR / "flight_schedule.json"
BUNDLED_DATA_FILE = RESOURCE_DIR / "flight_schedule.json"
DATA_FILE = RUNTIME_DATA_FILE if RUNTIME_DATA_FILE.exists() else BUNDLED_DATA_FILE
RUNTIME_REFERENCE_OPTIONS_FILE = APP_DIR / "reference_options.json"
BUNDLED_REFERENCE_OPTIONS_FILE = RESOURCE_DIR / "reference_options.json"
REFERENCE_OPTIONS_FILE = RUNTIME_REFERENCE_OPTIONS_FILE if RUNTIME_REFERENCE_OPTIONS_FILE.exists() else BUNDLED_REFERENCE_OPTIONS_FILE
APP_ICON_FILE = RESOURCE_DIR / "frenchbee_flight_manager.ico"
SCHEMA_VERSION = 1
DATABASE_SCHEMA_VERSION = 1
THEME_MODES = ("light", "dark")
TABLE_ZOOM_MIN = 80
TABLE_ZOOM_MAX = 140
TABLE_ZOOM_STEP = 10
DEFAULT_UI_SETTINGS = {
    "theme_mode": "light",
    "hidden_columns": "[]",
    "table_zoom": "100",
}
SUPPLEMENTARY_FIELDS = (
    "outbound_flight_no",
    "return_flight_no",
    "aircraft_type",
    "airline",
    "country_or_region",
    "route_pair_id",
)

FIELD_LABELS = {
    "airline": "航司",
    "outbound_flight_no": "去程航班号",
    "return_flight_no": "返程航班号",
    "airport_code": "机场代码",
    "departure_time": "去程离港时间",
    "arrival_time": "返程抵港时间",
    "aircraft_type": "机型",
    "country_or_region": "国家/地区",
}

REQUIRED_FIELDS = (
    "airline",
    "outbound_flight_no",
    "return_flight_no",
    "airport_code",
    "departure_time",
    "arrival_time",
    "aircraft_type",
    "country_or_region",
)
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
DISPLAY_COLUMNS = (
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
)
DISPLAY_HEADINGS = {
    "status": "状态",
    "outbound_flight_no": "去程航班号",
    "return_flight_no": "返程航班号",
    "airport_code": "机场",
    "departure_time": "去程离港",
    "arrival_time": "返程抵港",
    "aircraft_type": "机型",
    "airline": "航空公司",
    "country_or_region": "国家/地区",
    "route_pair_id": "关联ID",
}
DEFAULT_COLUMN_WIDTHS = {
    "status": 95,
    "outbound_flight_no": 100,
    "return_flight_no": 100,
    "airport_code": 70,
    "departure_time": 70,
    "arrival_time": 70,
    "aircraft_type": 90,
    "airline": 120,
    "country_or_region": 120,
    "route_pair_id": 95,
}
THEME_PALETTES = {
    "light": {
        "window": "#F4F1EA",
        "panel": "#ECEFF3",
        "field": "#FBFAF7",
        "text": "#1F2937",
        "muted": "#64748B",
        "heading": "#E3E8EF",
        "button": "#E6EBF1",
        "button_hover": "#D6DEE8",
        "row_even": "#FAFAF6",
        "row_odd": "#EEF4F8",
        "selected": "#C7D2FE",
        "selected_text": "#111827",
        "missing": "#B91C1C",
        "pairing": "#C2410C",
        "complete": "#047857",
        "link": "#2563EB",
    },
    "dark": {
        "window": "#1F2933",
        "panel": "#273442",
        "field": "#243140",
        "text": "#E5E7EB",
        "muted": "#B6C2CF",
        "heading": "#334155",
        "button": "#344256",
        "button_hover": "#41516A",
        "row_even": "#243140",
        "row_odd": "#2B3A4A",
        "selected": "#475569",
        "selected_text": "#F8FAFC",
        "missing": "#FCA5A5",
        "pairing": "#FDBA74",
        "complete": "#86EFAC",
        "link": "#93C5FD",
    },
}

TIME_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")
SIMPLE_TIME_RE = re.compile(r"^\d{4}$")
FLIGHT_NO_RE = re.compile(r"^[A-Z0-9]{2}\d{1,4}$")
FLIGHT_NO_DIGITS_RE = re.compile(r"^\d{1,4}$")
AIRLINE_CODE_RE = re.compile(r"^[A-Z0-9]{2}$")
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
        "allow_rename": True,
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
TIME_OPTIONS = [f"{hour}:{minute}" for hour in HOUR_OPTIONS for minute in MINUTE_OPTIONS]


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


def normalize_airline_code(value: str) -> str:
    code = str(value or "").strip().upper()
    if not code:
        return ""
    if not AIRLINE_CODE_RE.fullmatch(code):
        raise ValueError("航司二字代码必须由两位大写英文字母或阿拉伯数字组成，例如 BF、9C、G5、23。")
    return code


def normalize_airline_codes(airlines: list[str], codes: dict) -> dict[str, str]:
    normalized: dict[str, str] = {}
    airline_lookup = {airline.casefold(): airline for airline in airlines}
    for airline, code in (codes or {}).items():
        canonical = airline_lookup.get(str(airline).strip().casefold())
        if not canonical:
            continue
        normalized_code = str(code or "").strip().upper()
        if AIRLINE_CODE_RE.fullmatch(normalized_code):
            normalized[canonical] = normalized_code
    return normalized


class DatabaseStartupError(RuntimeError):
    pass


def is_database_path(path: Path) -> bool:
    return path.suffix.lower() in {".db", ".sqlite", ".sqlite3"}


def load_reference_options_json(path: Path = REFERENCE_OPTIONS_FILE) -> dict:
    if path.exists():
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    else:
        data = {}
    options = {
        config["category"]: normalize_options(data.get(config["category"], []), config["max_length"])
        for config in OPTION_FIELDS.values()
    }
    options["airline_codes"] = normalize_airline_codes(options["airlines"], data.get("airline_codes", {}))
    return options


def normalized_reference_payload(options: dict) -> dict:
    payload = {
        config["category"]: normalize_options(options.get(config["category"], []), config["max_length"])
        for config in OPTION_FIELDS.values()
    }
    payload["airline_codes"] = normalize_airline_codes(payload["airlines"], options.get("airline_codes", {}))
    return payload


def save_reference_options_json(options: dict, path: Path = REFERENCE_OPTIONS_FILE) -> None:
    payload = normalized_reference_payload(options)
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


def connect_database(path: Path = DB_FILE) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def create_database_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS flights (
            id TEXT PRIMARY KEY,
            outbound_flight_no TEXT NOT NULL DEFAULT '',
            return_flight_no TEXT NOT NULL DEFAULT '',
            airport_code TEXT NOT NULL DEFAULT '',
            departure_time TEXT NOT NULL DEFAULT '',
            arrival_time TEXT NOT NULL DEFAULT '',
            aircraft_type TEXT NOT NULL DEFAULT '',
            airline TEXT NOT NULL DEFAULT '',
            country_or_region TEXT NOT NULL DEFAULT '',
            route_pair_id TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL DEFAULT 'manual',
            updated_at TEXT NOT NULL DEFAULT '',
            display_order INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS reference_options (
            category TEXT NOT NULL,
            value TEXT NOT NULL,
            airline_code TEXT NOT NULL DEFAULT '',
            display_order INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (category, value)
        );
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """
    )
    connection.execute(
        "INSERT OR REPLACE INTO metadata(key, value) VALUES(?, ?)",
        ("database_schema_version", str(DATABASE_SCHEMA_VERSION)),
    )
    for key, value in DEFAULT_UI_SETTINGS.items():
        connection.execute(
            "INSERT OR IGNORE INTO app_settings(key, value) VALUES(?, ?)",
            (key, value),
        )


def check_database_integrity(path: Path = DB_FILE) -> None:
    try:
        with closing(connect_database(path)) as connection:
            result = connection.execute("PRAGMA integrity_check").fetchone()
            if not result or result[0] != "ok":
                raise DatabaseStartupError(f"数据库完整性检查失败：{result[0] if result else '无返回结果'}")
            tables = {
                row["name"]
                for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
            required = {"metadata", "flights", "reference_options"}
            missing = required - tables
            if missing:
                raise DatabaseStartupError("数据库缺少必要数据表：" + "、".join(sorted(missing)))
    except sqlite3.DatabaseError as exc:
        raise DatabaseStartupError(
            "数据库文件无法打开，可能已损坏或不是有效的 SQLite 文件。\n\n"
            f"文件位置：{path}\n错误信息：{exc}\n\n"
            "请使用“恢复备份”功能恢复一个有效备份，或保留当前文件后重新创建数据库。"
        ) from exc


def load_json_data(path: Path = DATA_FILE) -> dict:
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


def save_json_data(data: dict, path: Path) -> None:
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


def write_records_to_database(connection: sqlite3.Connection, records: list[dict[str, str]]) -> None:
    connection.execute("DELETE FROM flights")
    for index, record in enumerate(records):
        normalized = normalize_record(record)
        connection.execute(
            """
            INSERT INTO flights(
                id, outbound_flight_no, return_flight_no, airport_code, departure_time,
                arrival_time, aircraft_type, airline, country_or_region, route_pair_id,
                source, updated_at, display_order
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            tuple(normalized[field] for field in DATA_FIELDS) + (index,),
        )


def useful_legacy_field_count(records: list[dict[str, str]]) -> int:
    return sum(
        1
        for record in records
        for field in SUPPLEMENTARY_FIELDS
        if str(record.get(field, "")).strip()
    )


def merge_import_record(existing: dict[str, str] | None, incoming: dict[str, str]) -> dict[str, str]:
    if not existing:
        return incoming
    merged = copy.deepcopy(existing)
    for field in DATA_FIELDS:
        incoming_value = incoming.get(field, "")
        if field in {"id", "updated_at"}:
            merged[field] = incoming_value or merged.get(field, "")
        elif str(incoming_value).strip():
            merged[field] = incoming_value
    merged["updated_at"] = incoming.get("updated_at") or now_iso()
    return normalize_record(merged)


def upsert_records_to_database(connection: sqlite3.Connection, records: list[dict[str, str]], preserve_existing_on_blank: bool = False) -> int:
    max_order = connection.execute("SELECT COALESCE(MAX(display_order), -1) FROM flights").fetchone()[0]
    imported = 0
    for offset, record in enumerate(records, start=1):
        normalized = normalize_record(record)
        current = connection.execute("SELECT * FROM flights WHERE id = ?", (normalized["id"],)).fetchone()
        current_order = current["display_order"] if current else None
        if preserve_existing_on_blank and current:
            normalized = merge_import_record(dict(current), normalized)
        display_order = current_order if current_order is not None else max_order + offset
        connection.execute(
            """
            INSERT INTO flights(
                id, outbound_flight_no, return_flight_no, airport_code, departure_time,
                arrival_time, aircraft_type, airline, country_or_region, route_pair_id,
                source, updated_at, display_order
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                outbound_flight_no=excluded.outbound_flight_no,
                return_flight_no=excluded.return_flight_no,
                airport_code=excluded.airport_code,
                departure_time=excluded.departure_time,
                arrival_time=excluded.arrival_time,
                aircraft_type=excluded.aircraft_type,
                airline=excluded.airline,
                country_or_region=excluded.country_or_region,
                route_pair_id=excluded.route_pair_id,
                source=excluded.source,
                updated_at=excluded.updated_at,
                display_order=excluded.display_order
            """,
            tuple(normalized[field] for field in DATA_FIELDS) + (display_order,),
        )
        imported += 1
    return imported


def write_reference_options_to_database(connection: sqlite3.Connection, options: dict) -> None:
    payload = normalized_reference_payload(options)
    connection.execute("DELETE FROM reference_options")
    airline_codes = payload.get("airline_codes", {})
    for field, config in OPTION_FIELDS.items():
        category = config["category"]
        for index, value in enumerate(payload.get(category, [])):
            connection.execute(
                "INSERT INTO reference_options(category, value, airline_code, display_order) VALUES (?, ?, ?, ?)",
                (category, value, airline_codes.get(value, "") if field == "airline" else "", index),
            )


def create_database_from_payload(path: Path, data: dict | None = None, options: dict | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(connect_database(path)) as connection:
        create_database_schema(connection)
        write_records_to_database(connection, (data or {}).get("records", []))
        write_reference_options_to_database(connection, options or {})
        for key in ("schema_version", "generated_from", "generated_at"):
            value = str((data or {}).get(key, SCHEMA_VERSION if key == "schema_version" else ""))
            connection.execute("INSERT OR REPLACE INTO metadata(key, value) VALUES(?, ?)", (key, value))
        connection.commit()


def legacy_json_candidates() -> list[Path]:
    candidates: list[Path] = []
    for path in (RUNTIME_DATA_FILE, BUNDLED_DATA_FILE):
        if path.exists() and path not in candidates:
            candidates.append(path)
    return candidates


def reference_options_for_legacy_json(json_path: Path) -> dict:
    if json_path.parent == RUNTIME_REFERENCE_OPTIONS_FILE.parent and RUNTIME_REFERENCE_OPTIONS_FILE.exists():
        return load_reference_options_json(RUNTIME_REFERENCE_OPTIONS_FILE)
    return load_reference_options_json(REFERENCE_OPTIONS_FILE)


def best_legacy_json_data() -> tuple[Path | None, dict]:
    best_path: Path | None = None
    best_data: dict = {"schema_version": SCHEMA_VERSION, "records": []}
    best_score = -1
    for path in legacy_json_candidates():
        try:
            data = load_json_data(path)
        except (OSError, json.JSONDecodeError, ValueError):
            continue
        score = useful_legacy_field_count(data.get("records", []))
        if score > best_score:
            best_path = path
            best_data = data
            best_score = score
    return best_path, best_data


def maybe_import_runtime_legacy_json(path: Path = DB_FILE) -> int:
    if path.resolve() != DB_FILE.resolve() or not RUNTIME_DATA_FILE.exists():
        return 0
    try:
        data = load_json_data(RUNTIME_DATA_FILE)
    except (OSError, json.JSONDecodeError, ValueError):
        return 0
    if useful_legacy_field_count(data.get("records", [])) == 0:
        return 0
    with closing(connect_database(path)) as connection:
        imported = upsert_records_to_database(connection, data.get("records", []), preserve_existing_on_blank=True)
        connection.execute("INSERT OR REPLACE INTO metadata(key, value) VALUES(?, ?)", ("legacy_json_imported_from", str(RUNTIME_DATA_FILE)))
        connection.commit()
    return imported


def ensure_database(path: Path = DB_FILE) -> None:
    if path.exists():
        check_database_integrity(path)
        with closing(connect_database(path)) as connection:
            create_database_schema(connection)
            connection.commit()
        maybe_import_runtime_legacy_json(path)
        return
    is_primary_database = path.resolve() == DB_FILE.resolve()
    legacy_path, legacy_data = best_legacy_json_data() if is_primary_database else (None, {"schema_version": SCHEMA_VERSION, "records": []})
    if is_primary_database and legacy_path and useful_legacy_field_count(legacy_data.get("records", [])) > 0:
        create_database_from_payload(path, legacy_data, reference_options_for_legacy_json(legacy_path))
        check_database_integrity(path)
        return
    if is_primary_database and BUNDLED_DB_FILE.exists() and BUNDLED_DB_FILE.resolve() != path.resolve():
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(BUNDLED_DB_FILE, path)
        maybe_import_runtime_legacy_json(path)
        check_database_integrity(path)
        return
    data = legacy_data if is_primary_database else {"schema_version": SCHEMA_VERSION, "records": []}
    options = load_reference_options_json(REFERENCE_OPTIONS_FILE) if is_primary_database else {}
    create_database_from_payload(path, data, options)
    check_database_integrity(path)


def load_reference_options(path: Path = DB_FILE) -> dict:
    if not is_database_path(path):
        return load_reference_options_json(path)
    ensure_database(path)
    options = {config["category"]: [] for config in OPTION_FIELDS.values()}
    airline_codes: dict[str, str] = {}
    with closing(connect_database(path)) as connection:
        for row in connection.execute("SELECT category, value, airline_code FROM reference_options ORDER BY display_order, value"):
            category = row["category"]
            value = row["value"]
            if category in options:
                options[category].append(value)
                if category == OPTION_FIELDS["airline"]["category"] and row["airline_code"]:
                    airline_codes[value] = row["airline_code"]
    options = {
        config["category"]: normalize_options(options.get(config["category"], []), config["max_length"])
        for config in OPTION_FIELDS.values()
    }
    options["airline_codes"] = normalize_airline_codes(options["airlines"], airline_codes)
    return options


def save_reference_options(options: dict, path: Path = DB_FILE) -> None:
    if not is_database_path(path):
        save_reference_options_json(options, path)
        return
    payload = {
        config["category"]: normalize_options(options.get(config["category"], []), config["max_length"])
        for config in OPTION_FIELDS.values()
    }
    payload["airline_codes"] = normalize_airline_codes(payload["airlines"], options.get("airline_codes", {}))
    ensure_database(path)
    with closing(connect_database(path)) as connection:
        write_reference_options_to_database(connection, payload)
        connection.commit()


def filter_options(values: list[str], term: str, limit: int | None = 80) -> list[str]:
    term = term.strip().casefold()
    if not term:
        return values[:] if limit is None else values[:limit]
    starts = [value for value in values if value.casefold().startswith(term)]
    contains = [value for value in values if term in value.casefold() and value not in starts]
    results = starts + contains
    return results if limit is None else results[:limit]


def normalize_theme_mode(value: str) -> str:
    value = str(value or "").strip().lower()
    return value if value in THEME_MODES else DEFAULT_UI_SETTINGS["theme_mode"]


def clamp_table_zoom(value: str | int) -> int:
    try:
        zoom = int(value)
    except (TypeError, ValueError):
        zoom = int(DEFAULT_UI_SETTINGS["table_zoom"])
    zoom = max(TABLE_ZOOM_MIN, min(TABLE_ZOOM_MAX, zoom))
    return int(round(zoom / TABLE_ZOOM_STEP) * TABLE_ZOOM_STEP)


def normalize_hidden_columns(value: str | list[str] | tuple[str, ...] | set[str]) -> list[str]:
    if isinstance(value, str):
        try:
            raw = json.loads(value)
        except json.JSONDecodeError:
            raw = []
    else:
        raw = list(value)
    hidden: list[str] = []
    for column in raw:
        if column in DISPLAY_COLUMNS and column not in hidden:
            hidden.append(column)
    if len(hidden) >= len(DISPLAY_COLUMNS):
        hidden = hidden[:-1]
    return hidden


def visible_display_columns(hidden_columns: list[str] | tuple[str, ...] | set[str]) -> tuple[str, ...]:
    hidden = set(normalize_hidden_columns(list(hidden_columns)))
    visible = tuple(column for column in DISPLAY_COLUMNS if column not in hidden)
    return visible or (DISPLAY_COLUMNS[0],)


def load_ui_settings(path: Path = DB_FILE) -> dict[str, object]:
    ensure_database(path)
    values = dict(DEFAULT_UI_SETTINGS)
    with closing(connect_database(path)) as connection:
        create_database_schema(connection)
        for row in connection.execute("SELECT key, value FROM app_settings"):
            if row["key"] in values:
                values[row["key"]] = row["value"]
        connection.commit()
    return {
        "theme_mode": normalize_theme_mode(values.get("theme_mode", "")),
        "hidden_columns": normalize_hidden_columns(values.get("hidden_columns", "[]")),
        "table_zoom": clamp_table_zoom(values.get("table_zoom", "100")),
    }


def save_ui_settings(settings: dict[str, object], path: Path = DB_FILE) -> None:
    ensure_database(path)
    payload = {
        "theme_mode": normalize_theme_mode(str(settings.get("theme_mode", DEFAULT_UI_SETTINGS["theme_mode"]))),
        "hidden_columns": json.dumps(
            normalize_hidden_columns(settings.get("hidden_columns", [])),
            ensure_ascii=False,
        ),
        "table_zoom": str(clamp_table_zoom(settings.get("table_zoom", DEFAULT_UI_SETTINGS["table_zoom"]))),
    }
    with closing(connect_database(path)) as connection:
        create_database_schema(connection)
        for key, value in payload.items():
            connection.execute("INSERT OR REPLACE INTO app_settings(key, value) VALUES(?, ?)", (key, value))
        connection.commit()


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
            raise ValueError(f"{FIELD_LABELS[field]}应由两位航司代码和 1 至 4 位数字组成，例如 BF1、9C101、G51001。")
    airport_code = record.get("airport_code", "").strip().upper()
    if airport_code and not AIRPORT_RE.fullmatch(airport_code):
        raise ValueError("机场代码应为三个英文字母，例如 RUN、JFK。")
    for field, config in OPTION_FIELDS.items():
        if len(record.get(field, "")) > config["max_length"]:
            raise ValueError(f"{FIELD_LABELS[field]}长度不能超过 {config['max_length']} 个字符。")
    normalize_time(record.get("departure_time", ""))
    normalize_time(record.get("arrival_time", ""))


def apply_airline_code_prefixes(record: dict[str, str], airline_codes: dict[str, str]) -> None:
    airline = record.get("airline", "").strip()
    code = airline_codes.get(airline, "")
    if not airline or not code:
        return
    for field in ("outbound_flight_no", "return_flight_no"):
        value = record.get(field, "").strip().upper()
        if not value:
            continue
        if FLIGHT_NO_DIGITS_RE.fullmatch(value):
            record[field] = f"{code}{value}"
            continue
        if FLIGHT_NO_RE.fullmatch(value) and not value.startswith(code):
            raise ValueError(f"{FIELD_LABELS[field]}必须以所选航司的二字代码 {code} 开头，或仅输入 1 至 4 位数字。")
        record[field] = value


def find_duplicate_flight_numbers(
    records: list[dict[str, str]],
    candidate: dict[str, str],
    exclude_id: str | None = None,
    exclude_pair_id: str | None = None,
) -> list[dict[str, str]]:
    candidate_numbers = [
        (field, candidate.get(field, "").strip().upper())
        for field in ("outbound_flight_no", "return_flight_no")
        if candidate.get(field, "").strip()
    ]
    if len({number for _, number in candidate_numbers}) != len(candidate_numbers):
        return [{"flight_no": candidate_numbers[0][1], "record": candidate, "field": "same_record"}]

    duplicates: list[dict[str, str]] = []
    for field, number in candidate_numbers:
        for record in records:
            if exclude_id and record.get("id") == exclude_id:
                continue
            if exclude_pair_id and record.get("route_pair_id") == exclude_pair_id:
                continue
            for existing_field in ("outbound_flight_no", "return_flight_no"):
                if number == record.get(existing_field, "").strip().upper():
                    duplicates.append({"flight_no": number, "record": record, "field": existing_field, "candidate_field": field})
    return duplicates


def record_summary(record: dict[str, str]) -> str:
    flight_no = "/".join(part for part in (record.get("outbound_flight_no"), record.get("return_flight_no")) if part) or "未录入航班号"
    airport = record.get("airport_code") or "未录入机场"
    departure = record.get("departure_time") or "-"
    arrival = record.get("arrival_time") or "-"
    return f"{flight_no} | {airport} | 去程离港 {departure} | 返程抵港 {arrival}"


def normalize_search_time(value: str, label: str) -> str:
    if not str(value or "").strip():
        return ""
    time_value = normalize_time(value)
    if time_value not in TIME_OPTIONS:
        raise ValueError(f"{label}必须从 00:00 至 23:55、每 5 分钟一个间隔的下拉列表中选择。")
    return time_value


def time_in_range(value: str, start: str, end: str) -> bool:
    if not start and not end:
        return True
    if not value:
        return False
    if start and end and start > end:
        raise ValueError("时间段开始时间不能晚于结束时间。")
    if start and value < start:
        return False
    if end and value > end:
        return False
    return True


def record_matches_criteria(record: dict[str, str], criteria: dict[str, str]) -> bool:
    flight_no = criteria.get("flight_no", "").strip().upper()
    airport_code = criteria.get("airport_code", "").strip().upper()
    airline = criteria.get("airline", "").strip().casefold()
    aircraft_type = criteria.get("aircraft_type", "").strip().casefold()
    country_or_region = criteria.get("country_or_region", "").strip().casefold()
    departure_time = normalize_search_time(criteria.get("departure_time", ""), "去程离港时间")
    arrival_time = normalize_search_time(criteria.get("arrival_time", ""), "返程抵港时间")
    departure_start = normalize_search_time(criteria.get("departure_start", ""), "去程离港开始时间")
    departure_end = normalize_search_time(criteria.get("departure_end", ""), "去程离港结束时间")
    arrival_start = normalize_search_time(criteria.get("arrival_start", ""), "返程抵港开始时间")
    arrival_end = normalize_search_time(criteria.get("arrival_end", ""), "返程抵港结束时间")

    if flight_no and flight_no not in {record.get("outbound_flight_no", "").upper(), record.get("return_flight_no", "").upper()}:
        return False
    if airport_code and airport_code != record.get("airport_code", "").upper():
        return False
    if airline and airline != record.get("airline", "").strip().casefold():
        return False
    if aircraft_type and aircraft_type != record.get("aircraft_type", "").strip().casefold():
        return False
    if country_or_region and country_or_region != record.get("country_or_region", "").strip().casefold():
        return False
    if departure_time and departure_time != record.get("departure_time", ""):
        return False
    if arrival_time and arrival_time != record.get("arrival_time", ""):
        return False
    if not time_in_range(record.get("departure_time", ""), departure_start, departure_end):
        return False
    if not time_in_range(record.get("arrival_time", ""), arrival_start, arrival_end):
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


def grouped_display_records(records: list[dict[str, str]]) -> list[list[dict[str, str]]]:
    groups: list[list[dict[str, str]]] = []
    seen_pairs: set[str] = set()
    for record in records:
        pair_id = record.get("route_pair_id", "")
        if pair_id:
            if pair_id in seen_pairs:
                continue
            seen_pairs.add(pair_id)
            groups.append([item for item in records if item.get("route_pair_id") == pair_id])
        else:
            groups.append([record])
    return groups


def group_unique_values(group: list[dict[str, str]], field: str) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for record in group:
        value = str(record.get(field, "")).strip()
        key = value.casefold()
        if value and key not in seen:
            values.append(value)
            seen.add(key)
    return values


def group_display_value(group: list[dict[str, str]], field: str) -> str:
    if not group:
        return ""
    if field == "status":
        if any(missing_fields(record) for record in group):
            return "● 待补录"
        if any(needs_pairing(record) for record in group):
            return "● 待关联"
        return "已关联" if any(record.get("route_pair_id") for record in group) else route_status(group[0])
    if field == "route_pair_id":
        return pair_display(group[0])
    return " / ".join(group_unique_values(group, field))


def group_row_id(group: list[dict[str, str]]) -> str:
    pair_id = group[0].get("route_pair_id", "") if group else ""
    if pair_id:
        return f"pair:{pair_id}"
    return f"record:{group[0].get('id', '')}" if group else "record:"


def sort_display_groups(groups: list[list[dict[str, str]]], column: str | None, direction: str | None) -> list[list[dict[str, str]]]:
    if not column or direction not in {"asc", "desc"}:
        return groups
    return sorted(
        groups,
        key=lambda group: (not group_display_value(group, column), group_display_value(group, column).casefold()),
        reverse=direction == "desc",
    )


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
            conflicts.append({"type": "去程离港", "time": departure_time, "record": record})
        if arrival_time and record.get("arrival_time") == arrival_time:
            conflicts.append({"type": "返程抵港", "time": arrival_time, "record": record})
    return conflicts


def load_data(path: Path = DB_FILE) -> dict:
    if not is_database_path(path):
        return load_json_data(path)
    ensure_database(path)
    with closing(connect_database(path)) as connection:
        metadata = {
            row["key"]: row["value"]
            for row in connection.execute("SELECT key, value FROM metadata")
        }
        records = [
            normalize_record(dict(row))
            for row in connection.execute(
                """
                SELECT id, outbound_flight_no, return_flight_no, airport_code,
                       departure_time, arrival_time, aircraft_type, airline,
                       country_or_region, route_pair_id, source, updated_at
                FROM flights
                ORDER BY display_order, id
                """
            )
        ]
    return {
        "schema_version": int(metadata.get("schema_version", SCHEMA_VERSION) or SCHEMA_VERSION),
        "generated_from": metadata.get("generated_from", ""),
        "generated_at": metadata.get("generated_at", ""),
        "records": records,
    }


def save_data(data: dict, path: Path = DB_FILE) -> None:
    if not is_database_path(path):
        save_json_data(data, path)
        return
    ensure_database(path)
    with closing(connect_database(path)) as connection:
        create_database_schema(connection)
        write_records_to_database(connection, data.get("records", []))
        for key in ("schema_version", "generated_from", "generated_at"):
            value = str(data.get(key, SCHEMA_VERSION if key == "schema_version" else ""))
            connection.execute("INSERT OR REPLACE INTO metadata(key, value) VALUES(?, ?)", (key, value))
        connection.commit()


def import_json_records_to_database(json_path: Path, db_path: Path = DB_FILE) -> int:
    data = load_json_data(json_path)
    records = data.get("records", [])
    if not records:
        raise ValueError("所选 JSON 文件中没有可导入的航班记录。")
    ensure_database(db_path)
    with closing(connect_database(db_path)) as connection:
        imported = upsert_records_to_database(connection, records, preserve_existing_on_blank=True)
        connection.commit()
        return imported


def column_letter(index: int) -> str:
    letters = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def xlsx_cell_xml(row_index: int, col_index: int, value: str) -> str:
    cell_ref = f"{column_letter(col_index)}{row_index}"
    text = escape(str(value or ""))
    return f'<c r="{cell_ref}" t="inlineStr"><is><t>{text}</t></is></c>'


def write_xlsx(path: Path, headers: list[str], rows: list[list[str]]) -> None:
    sheet_rows = [headers] + rows
    sheet_xml_rows = []
    for row_index, row in enumerate(sheet_rows, start=1):
        cells = "".join(xlsx_cell_xml(row_index, col_index, value) for col_index, value in enumerate(row, start=1))
        sheet_xml_rows.append(f'<row r="{row_index}">{cells}</row>')
    dimension = f"A1:{column_letter(len(headers))}{max(1, len(sheet_rows))}"
    worksheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<dimension ref="{dimension}"/>'
        '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>'
        '<sheetData>'
        + "".join(sheet_xml_rows)
        + "</sheetData></worksheet>"
    )
    styles_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>'
        '<fills count="1"><fill><patternFill patternType="none"/></fill></fills>'
        '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs>'
        "</styleSheet>"
    )
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
            "</Types>",
        )
        archive.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            "</Relationships>",
        )
        archive.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="航班数据" sheetId="1" r:id="rId1"/></sheets></workbook>',
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
            "</Relationships>",
        )
        archive.writestr("xl/worksheets/sheet1.xml", worksheet_xml)
        archive.writestr("xl/styles.xml", styles_xml)


def write_csv(path: Path, headers: list[str], rows: list[list[str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)


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
        self.code_text = StringVar()
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

        table_columns = ("value", "code") if self.field == "airline" else ("value",)
        self.table = ttk.Treeview(body, columns=table_columns, show="headings", selectmode="browse")
        self.table.heading("value", text=self.config_info["label"])
        self.table.column("value", anchor="w", width=350 if self.field == "airline" else 460)
        if self.field == "airline":
            self.table.heading("code", text="二字代码")
            self.table.column("code", anchor="center", width=90)
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

        if self.field == "airline":
            code_form = ttk.Frame(body)
            code_form.pack(fill=X, pady=(8, 0))
            ttk.Label(code_form, text="二字代码").pack(side=LEFT, padx=(0, 6))
            code_entry = ttk.Entry(
                code_form,
                textvariable=self.code_text,
                width=8,
                validate="key",
                validatecommand=(self.register(self.limit_airline_code), "%P"),
            )
            code_entry.pack(side=LEFT)
            ttk.Label(code_form, text="仅限两位大写字母或数字，如 BF、9C、G5、23", style="Muted.TLabel").pack(side=LEFT, padx=(8, 0))

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

    def limit_airline_code(self, value: str) -> bool:
        return len(value) <= 2 and all(char.isalnum() and char.isascii() for char in value)

    def clear_search(self) -> None:
        self.search_text.set("")
        self.refresh()

    def refresh(self) -> None:
        self.table.delete(*self.table.get_children())
        self.item_values = {}
        for index, value in enumerate(filter_options(self.values(), self.search_text.get(), limit=500)):
            item_id = f"item-{index}"
            self.item_values[item_id] = value
            if self.field == "airline":
                self.table.insert("", END, iid=item_id, values=(value, self.app.airline_code_for(value)))
            else:
                self.table.insert("", END, iid=item_id, values=(value,))

    def load_selected(self) -> None:
        selected = self.table.selection()
        if selected:
            value = self.item_values.get(selected[0], "")
            self.value_text.set(value)
            if self.field == "airline":
                self.code_text.set(self.app.airline_code_for(value))

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

    def validate_airline_code_value(self) -> str | None:
        if self.field != "airline":
            return ""
        if not self.code_text.get().strip():
            messagebox.showerror("航司代码为空", "请为该航司填写二字代码。", parent=self)
            return None
        try:
            return normalize_airline_code(self.code_text.get())
        except ValueError as exc:
            messagebox.showerror("航司代码有误", str(exc), parent=self)
            return None

    def persist(self) -> None:
        self.app.options[self.category] = normalize_options(self.app.options.get(self.category, []), self.config_info["max_length"])
        save_reference_options(self.app.options)
        self.refresh()
        self.app.refresh_search_option_combos()
        if self.on_change:
            self.on_change()

    def add_value(self) -> None:
        value = self.validate_new_value(self.value_text.get())
        if not value:
            return
        code = self.validate_airline_code_value()
        if code is None:
            return
        self.app.options.setdefault(self.category, []).append(value)
        if self.field == "airline":
            self.app.options.setdefault("airline_codes", {})[value] = code
        self.persist()
        self.value_text.set(value)

    def rename_selected(self) -> None:
        selected = self.table.selection()
        if not selected:
            messagebox.showinfo("请选择项目", "请先选择要修改的名称。", parent=self)
            return
        old_value = self.item_values.get(selected[0], "")
        new_value = self.value_text.get().strip()
        if old_value.casefold() == new_value.casefold():
            if not new_value:
                messagebox.showerror("名称为空", "请输入名称。", parent=self)
                return
            if len(new_value) > self.config_info["max_length"]:
                messagebox.showerror("名称过长", f"名称长度不能超过 {self.config_info['max_length']} 个字符。", parent=self)
                return
        else:
            new_value = self.validate_new_value(new_value)
        if not new_value:
            return
        code = self.validate_airline_code_value()
        if code is None:
            return
        values = [new_value if value == old_value else value for value in self.values()]
        self.app.options[self.category] = values
        if self.field == "airline":
            self.app.options.setdefault("airline_codes", {}).pop(old_value, None)
            self.app.options.setdefault("airline_codes", {})[new_value] = code
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
        if self.field == "airline":
            self.app.options.setdefault("airline_codes", {}).pop(value, None)
            self.code_text.set("")
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
        self.variables: dict[str, StringVar] = {}
        self.time_variables: dict[str, tuple[StringVar, StringVar]] = {}
        self.field_widgets: dict[str, object] = {}
        self.readonly_fields: set[str] = set()
        self.supplement_mode = bool(self.original_id and missing_fields(self.record))
        self.title("编辑航线" if record else "新增航线")
        self.resizable(False, False)
        self.transient(app.root)
        self.grab_set()

        body = ttk.Frame(self, padding=16)
        body.pack(fill=BOTH, expand=True)

        ttk.Label(body, text="带红点的字段需要补录", style="Danger.TLabel").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))
        if self.original_id and self.app.get_counterparts(self.record):
            ttk.Label(
                body,
                text="该航线已有关联航班。修改后请同步检查对应的去程或返程航班。",
                style="Warning.TLabel",
            ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 8))
            row_offset = 1
        else:
            row_offset = 0

        for row, field in enumerate(REQUIRED_FIELDS, start=1 + row_offset):
            label_text = FIELD_LABELS[field]
            if field in missing_fields(self.record):
                label_text = f"● {label_text}"
            label = ttk.Label(body, text=label_text, style="Danger.TLabel" if field in missing_fields(self.record) else "TLabel")
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
                self.variables[field] = variable
                entry = ttk.Entry(body, textvariable=variable, width=30)
                entry.grid(row=row, column=1, sticky="we", pady=5)
                self.entries[field] = entry
                self.field_widgets[field] = entry

        button_bar = ttk.Frame(body)
        button_bar.grid(row=len(REQUIRED_FIELDS) + 1 + row_offset, column=0, columnspan=3, sticky="e", pady=(14, 0))
        if self.original_id and self.app.get_counterparts(self.record):
            ttk.Button(button_bar, text="编辑对应航班", command=self.open_counterpart).pack(side=LEFT, padx=(0, 8))
        ttk.Button(button_bar, text="保存", command=self.save).pack(side=LEFT, padx=(0, 8))
        ttk.Button(button_bar, text="取消", command=self.destroy).pack(side=LEFT)

        target_field = focus_field or (missing_fields(self.record)[0] if missing_fields(self.record) else "outbound_flight_no")
        if self.field_widgets:
            self.after(100, lambda: self.focus_editor_field(target_field))

    def focus_editor_field(self, field: str) -> None:
        widget = self.field_widgets.get(field)
        if widget is None:
            widget = next(iter(self.field_widgets.values()))
        widget.focus_set()

    def create_time_selector(self, parent: ttk.Frame, row: int, field: str) -> None:
        frame = ttk.Frame(parent)
        frame.grid(row=row, column=1, sticky="w", pady=5)
        value = self.record.get(field, "")
        hour_value, minute_value = ("", "")
        if value and TIME_RE.fullmatch(value):
            hour_value, minute_value = value.split(":")
        hour_var = StringVar(value=hour_value)
        minute_var = StringVar(value=minute_value)
        self.time_variables[field] = (hour_var, minute_var)
        hour_combo = ttk.Combobox(frame, width=5, values=HOUR_OPTIONS, textvariable=hour_var)
        minute_values = MINUTE_OPTIONS if not minute_value or minute_value in MINUTE_OPTIONS else sorted({*MINUTE_OPTIONS, minute_value})
        minute_combo = ttk.Combobox(frame, width=5, values=minute_values, textvariable=minute_var)
        hour_combo.pack(side=LEFT)
        ttk.Label(frame, text="时").pack(side=LEFT, padx=(4, 8))
        minute_combo.pack(side=LEFT)
        ttk.Label(frame, text="分").pack(side=LEFT, padx=(4, 0))
        hour_combo.bind("<KeyRelease>", lambda _event, combo=hour_combo: self.filter_static_combo(combo, HOUR_OPTIONS))
        minute_combo.bind("<KeyRelease>", lambda _event, combo=minute_combo: self.filter_static_combo(combo, MINUTE_OPTIONS))
        self.time_widgets[field] = (hour_combo, minute_combo)
        self.field_widgets[field] = hour_combo
        ttk.Label(parent, text="每 5 分钟", style="Muted.TLabel").grid(row=row, column=2, sticky="w", padx=(8, 0))

    def create_option_selector(self, parent: ttk.Frame, row: int, field: str) -> None:
        config = OPTION_FIELDS[field]
        variable = StringVar(value=self.record.get(field, ""))
        self.variables[field] = variable
        combo = ttk.Combobox(
            parent,
            textvariable=variable,
            width=27,
            values=filter_options(self.app.option_values_for_field(field), variable.get(), limit=500),
            validate="key",
            validatecommand=(self.register(lambda value, limit=config["max_length"]: len(value) <= limit), "%P"),
        )
        combo.grid(row=row, column=1, sticky="we", pady=5)
        combo.bind("<KeyRelease>", lambda _event, item=field: self.filter_option_combo(item))
        combo.bind("<Button-1>", lambda _event, item=field: self.filter_option_combo(item))
        if field == "airline":
            combo.bind("<<ComboboxSelected>>", lambda _event: self.on_airline_selected())
        self.option_combos[field] = combo
        self.field_widgets[field] = combo
        ttk.Button(parent, text="管理", command=lambda item=field: self.open_option_manager(item)).grid(row=row, column=2, sticky="w", padx=(8, 0))

    def filter_static_combo(self, combo: ttk.Combobox, values: list[str]) -> None:
        combo.configure(values=filter_options(values, combo.get(), limit=len(values)))

    def filter_option_combo(self, field: str) -> None:
        combo = self.option_combos[field]
        combo.configure(values=filter_options(self.app.option_values_for_field(field), combo.get(), limit=500))

    def refresh_option_combos(self) -> None:
        for field in self.option_combos:
            self.filter_option_combo(field)

    def open_option_manager(self, field: str) -> None:
        OptionManagerDialog(self.app, field, on_change=self.refresh_option_combos)

    def on_airline_selected(self) -> None:
        airline = self.option_combos.get("airline").get().strip() if "airline" in self.option_combos else ""
        code = self.app.airline_code_for(airline)
        if not code:
            return
        for field in ("outbound_flight_no", "return_flight_no"):
            entry = self.entries.get(field)
            if not entry:
                continue
            value = entry.get().strip().upper()
            if FLIGHT_NO_DIGITS_RE.fullmatch(value):
                entry.delete(0, END)
                entry.insert(0, f"{code}{value}")
            elif not value:
                entry.insert(0, code)
            elif FLIGHT_NO_RE.fullmatch(value) and not value.startswith(code):
                entry.delete(0, END)
                entry.insert(0, f"{code}{value[2:]}")

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
        self.app.apply_airline_code_prefixes(record)
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
            self.focus_editor_field(first_missing)
            return

        if not self.original_id and route_info_complete(record) and not record.get("route_pair_id"):
            record["route_pair_id"] = new_pair_id()

        duplicate_flights = find_duplicate_flight_numbers(
            self.app.records,
            record,
            exclude_id=self.original_id,
            exclude_pair_id=record.get("route_pair_id", ""),
        )
        if duplicate_flights:
            lines = []
            for duplicate in duplicate_flights[:8]:
                if duplicate.get("field") == "same_record":
                    lines.append(f"{duplicate['flight_no']} 在本条记录内重复。")
                else:
                    lines.append(f"{duplicate['flight_no']} 已存在：{record_summary(duplicate['record'])}")
            if len(duplicate_flights) > 8:
                lines.append(f"另有 {len(duplicate_flights) - 8} 条重复未显示。")
            messagebox.showerror("航班号重复", "不允许出现完全一致的航班号，请修改后再保存。\n\n" + "\n".join(lines), parent=self)
            return

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
            messagebox.showwarning("待关联提醒", "该航线资料已完整，请继续手动关联对应的去程或返程航班。", parent=self)
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
        self.title("关联去程/返程航班")
        self.geometry("850x500")
        self.transient(app.root)
        self.grab_set()

        body = ttk.Frame(self, padding=14)
        body.pack(fill=BOTH, expand=True)

        ttk.Label(body, text="当前航线").pack(anchor="w")
        ttk.Label(body, text=record_summary(source)).pack(anchor="w", pady=(0, 10))
        if notice:
            ttk.Label(body, text=notice, style="Warning.TLabel", wraplength=780).pack(anchor="w", pady=(0, 10))

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
            messagebox.showinfo("请选择候选航线", "请先选择要关联的去程或返程航班记录。", parent=self)
            return
        target_id = selected[0]
        if self.app.associate_records(self.source["id"], target_id, parent=self):
            self.destroy()


class FlightManagerApp:
    def __init__(self, root: Tk):
        self.root = root
        ensure_database()
        self.root.title(f"{APP_DISPLAY_NAME} v{APP_VERSION}")
        self.root.geometry("1280x780")
        if APP_ICON_FILE.exists():
            try:
                self.root.iconbitmap(str(APP_ICON_FILE))
            except Exception:
                pass
        self.data = load_data()
        self.records: list[dict[str, str]] = self.data["records"]
        self.options = load_reference_options()
        self.ui_settings = load_ui_settings()
        self.theme_mode = str(self.ui_settings["theme_mode"])
        self.hidden_columns = list(self.ui_settings["hidden_columns"])
        self.table_zoom = int(self.ui_settings["table_zoom"])
        self.current_results: list[dict[str, str]] = []
        self.current_display_groups: list[list[dict[str, str]]] = []
        self.search_vars = {
            "flight_no": StringVar(),
            "airport_code": StringVar(),
            "airline": StringVar(),
            "aircraft_type": StringVar(),
            "country_or_region": StringVar(),
            "departure_time": StringVar(),
            "departure_start": StringVar(),
            "departure_end": StringVar(),
            "arrival_time": StringVar(),
            "arrival_start": StringVar(),
            "arrival_end": StringVar(),
        }
        self.search_option_combos: dict[str, ttk.Combobox] = {}
        self.search_time_combos: list[ttk.Combobox] = []
        self.table_row_records: dict[str, list[dict[str, str]]] = {}
        self.record_to_row_id: dict[str, str] = {}
        self.sort_column: str | None = None
        self.sort_direction: str | None = None
        self.table_headings: dict[str, str] = {}
        self.status_var = StringVar()
        self.zoom_text = StringVar(value=f"{self.table_zoom}%")
        self.style = ttk.Style(self.root)
        self.style.theme_use("clam")
        self.theme_button: ttk.Button | None = None
        self.content: ttk.PanedWindow | None = None
        self.reminder_frame: ttk.LabelFrame | None = None
        self.reminder_visible = False
        self._build_ui()
        self.apply_theme()
        self.apply_display_columns()
        self.apply_table_zoom()
        self.refresh()

    def _build_ui(self) -> None:
        root_frame = ttk.Frame(self.root, padding=12)
        root_frame.pack(fill=BOTH, expand=True)

        search_frame = ttk.LabelFrame(root_frame, text="精准查询", padding=10)
        search_frame.pack(fill=X)

        search_inputs = ttk.Frame(search_frame)
        search_inputs.grid(row=0, column=0, sticky="w")
        search_options = ttk.Frame(search_frame)
        search_options.grid(row=1, column=0, sticky="w", pady=(8, 0))
        search_times = ttk.Frame(search_frame)
        search_times.grid(row=2, column=0, sticky="w", pady=(8, 0))
        search_buttons = ttk.Frame(search_frame)
        search_buttons.grid(row=3, column=0, sticky="w", pady=(8, 0))
        utility_buttons = ttk.Frame(search_frame)
        utility_buttons.grid(row=4, column=0, sticky="w", pady=(8, 0))
        search_frame.columnconfigure(0, weight=1)

        for key, label_text, width in (
            ("flight_no", "航班号", 14),
            ("airport_code", "机场代码", 10),
        ):
            ttk.Label(search_inputs, text=label_text).pack(side=LEFT, padx=(0, 6))
            entry = ttk.Entry(search_inputs, textvariable=self.search_vars[key], width=width)
            entry.pack(side=LEFT, padx=(0, 14))
            entry.bind("<Return>", lambda _event: self.apply_search())

        self.add_search_option_combo(search_options, "航空公司", "airline", 20)
        self.add_search_option_combo(search_options, "机型", "aircraft_type", 18)
        self.add_search_option_combo(search_options, "国家/地区", "country_or_region", 20)

        self.add_search_time_combo(search_times, "去程离港", "departure_time")
        self.add_search_time_combo(search_times, "返程抵港", "arrival_time")
        ttk.Label(search_times, text="去程离港 从").pack(side=LEFT, padx=(8, 6))
        self.add_search_time_combo(search_times, "", "departure_start")
        ttk.Label(search_times, text="至").pack(side=LEFT, padx=(0, 6))
        self.add_search_time_combo(search_times, "", "departure_end")
        ttk.Label(search_times, text="返程抵港 从").pack(side=LEFT, padx=(8, 6))
        self.add_search_time_combo(search_times, "", "arrival_start")
        ttk.Label(search_times, text="至").pack(side=LEFT, padx=(0, 6))
        self.add_search_time_combo(search_times, "", "arrival_end")

        for text, command in (
            ("查询", self.apply_search),
            ("清空", self.clear_search),
            ("新增航线", self.add_record),
            ("编辑选中", self.edit_selected),
            ("关联选中", self.pair_selected),
            ("取消关联", self.clear_selected_pair),
            ("删除选中", self.delete_selected),
        ):
            ttk.Button(search_buttons, text=text, command=command).pack(side=LEFT, padx=(0, 6))

        for text, command in (
            ("备份数据库", self.backup_database),
            ("恢复备份", self.restore_database_backup),
            ("导出 Excel/CSV", self.export_visible_data),
            ("从 JSON 导入旧数据", self.import_legacy_json),
            ("关于", self.show_about),
        ):
            ttk.Button(utility_buttons, text=text, command=command).pack(side=LEFT, padx=(0, 6))
        ttk.Separator(utility_buttons, orient=VERTICAL).pack(side=LEFT, fill=Y, padx=(4, 10))
        self.theme_button = ttk.Button(utility_buttons, text="", command=self.toggle_theme)
        self.theme_button.pack(side=LEFT, padx=(0, 6))
        ttk.Label(utility_buttons, text="表格缩放").pack(side=LEFT, padx=(4, 6))
        ttk.Button(utility_buttons, text="−", width=3, command=self.zoom_out).pack(side=LEFT, padx=(0, 2))
        ttk.Label(utility_buttons, textvariable=self.zoom_text, width=5, anchor="center").pack(side=LEFT, padx=(2, 2))
        ttk.Button(utility_buttons, text="+", width=3, command=self.zoom_in).pack(side=LEFT, padx=(2, 2))
        ttk.Button(utility_buttons, text="重置", command=self.reset_zoom).pack(side=LEFT, padx=(4, 0))

        self.content = ttk.PanedWindow(root_frame, orient="horizontal")
        self.content.pack(fill=BOTH, expand=True, pady=(12, 8))

        table_frame = ttk.Frame(self.content)
        self.reminder_frame = ttk.LabelFrame(self.content, text="待补录提醒", padding=10)
        self.content.add(table_frame, weight=4)
        self.content.add(self.reminder_frame, weight=2)
        self.reminder_visible = True

        columns = DISPLAY_COLUMNS
        self.table = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse", style="Main.Treeview")
        self.table_headings = dict(DISPLAY_HEADINGS)
        for column in columns:
            self.table.heading(column, text=self.sort_heading_text(column), command=lambda item=column: self.toggle_sort(item))
            self.table.column(column, width=DEFAULT_COLUMN_WIDTHS[column], anchor="center", stretch=column in {"airline", "country_or_region"})

        yscroll = ttk.Scrollbar(table_frame, orient=VERTICAL, command=self.table.yview)
        self.table.configure(yscrollcommand=yscroll.set)
        self.table.pack(side=LEFT, fill=BOTH, expand=True)
        yscroll.pack(side=RIGHT, fill=Y)
        self.table.bind("<Double-1>", lambda _event: self.edit_selected())
        self.table.bind("<Button-3>", self.show_column_menu)
        self.table.bind("<Control-Button-1>", self.show_column_menu)

        self.reminder_note = ttk.Label(self.reminder_frame, text="单击待补录项打开编辑；单击待关联项打开关联窗口。", style="Danger.TLabel", wraplength=320)
        self.reminder_note.pack(anchor="w", pady=(0, 8))
        reminder_columns = ("summary", "missing")
        self.reminders = ttk.Treeview(self.reminder_frame, columns=reminder_columns, show="headings", selectmode="browse", height=18)
        self.reminders.heading("summary", text="航线")
        self.reminders.heading("missing", text="提醒事项")
        self.reminders.column("summary", width=210, anchor="w")
        self.reminders.column("missing", width=210, anchor="w")
        reminder_scroll = ttk.Scrollbar(self.reminder_frame, orient=VERTICAL, command=self.reminders.yview)
        self.reminders.configure(yscrollcommand=reminder_scroll.set)
        self.reminders.pack(side=LEFT, fill=BOTH, expand=True)
        reminder_scroll.pack(side=RIGHT, fill=Y)
        self.reminders.bind("<ButtonRelease-1>", self.open_reminder_from_click)

        status_bar = ttk.Frame(root_frame)
        status_bar.pack(fill=X)
        ttk.Label(status_bar, textvariable=self.status_var, style="Status.TLabel").pack(side=LEFT)
        ttk.Label(status_bar, text=f"数据库：{DB_FILE.name}", style="Muted.TLabel").pack(side=RIGHT)

    def sort_heading_text(self, column: str) -> str:
        label = self.table_headings.get(column, column)
        if self.sort_column != column:
            return label
        marker = " ↑" if self.sort_direction == "asc" else " ↓" if self.sort_direction == "desc" else ""
        return f"{label}{marker}"

    def update_sort_headings(self) -> None:
        for column in self.table["columns"]:
            self.table.heading(column, text=self.sort_heading_text(column), command=lambda item=column: self.toggle_sort(item))

    def toggle_sort(self, column: str) -> None:
        if self.sort_column != column:
            self.sort_column = column
            self.sort_direction = "asc"
        elif self.sort_direction == "asc":
            self.sort_direction = "desc"
        else:
            self.sort_column = None
            self.sort_direction = None
        self.update_sort_headings()
        self.refresh()

    def palette(self) -> dict[str, str]:
        return THEME_PALETTES[self.theme_mode if self.theme_mode in THEME_PALETTES else "light"]

    def persist_ui_settings(self) -> None:
        save_ui_settings(
            {
                "theme_mode": self.theme_mode,
                "hidden_columns": self.hidden_columns,
                "table_zoom": self.table_zoom,
            }
        )

    def apply_theme(self) -> None:
        palette = self.palette()
        self.root.configure(background=palette["window"])
        self.style.configure(".", background=palette["window"], foreground=palette["text"], font=("Segoe UI", 9))
        self.style.configure("TFrame", background=palette["window"])
        self.style.configure("TLabelframe", background=palette["window"], bordercolor=palette["heading"])
        self.style.configure("TLabelframe.Label", background=palette["window"], foreground=palette["text"], font=("Segoe UI", 9, "bold"))
        self.style.configure("TLabel", background=palette["window"], foreground=palette["text"])
        self.style.configure("Status.TLabel", background=palette["window"], foreground=palette["text"])
        self.style.configure("Muted.TLabel", background=palette["window"], foreground=palette["muted"])
        self.style.configure("Danger.TLabel", background=palette["window"], foreground=palette["missing"])
        self.style.configure("Warning.TLabel", background=palette["window"], foreground=palette["pairing"])
        self.style.configure("Link.TLabel", background=palette["window"], foreground=palette["link"])
        self.style.configure("TButton", background=palette["button"], foreground=palette["text"], padding=(8, 4))
        self.style.map("TButton", background=[("active", palette["button_hover"])])
        self.style.configure("TEntry", fieldbackground=palette["field"], foreground=palette["text"], insertcolor=palette["text"])
        self.style.configure("TCombobox", fieldbackground=palette["field"], foreground=palette["text"], arrowcolor=palette["text"])
        self.style.configure("Treeview", background=palette["field"], fieldbackground=palette["field"], foreground=palette["text"])
        self.style.configure("Treeview.Heading", background=palette["heading"], foreground=palette["text"], font=("Segoe UI", 9, "bold"))
        self.style.map("Treeview", background=[("selected", palette["selected"])], foreground=[("selected", palette["selected_text"])])
        self.style.map("Main.Treeview", background=[("selected", palette["selected"])], foreground=[("selected", palette["selected_text"])])
        self.apply_table_zoom()
        self.configure_table_tags()
        self.update_theme_button()

    def configure_table_tags(self) -> None:
        if not hasattr(self, "table"):
            return
        palette = self.palette()
        for state, foreground in (
            ("missing", palette["missing"]),
            ("pairing", palette["pairing"]),
            ("complete", palette["complete"]),
        ):
            for parity, background in (("even", palette["row_even"]), ("odd", palette["row_odd"])):
                self.table.tag_configure(f"{state}_{parity}", foreground=foreground, background=background)
        if hasattr(self, "reminders"):
            self.reminders.tag_configure("missing", foreground=palette["missing"], background=palette["row_even"])
            self.reminders.tag_configure("pairing", foreground=palette["pairing"], background=palette["row_odd"])

    def update_theme_button(self) -> None:
        if self.theme_button is None:
            return
        self.theme_button.configure(text="浅色模式" if self.theme_mode == "dark" else "深色模式")

    def toggle_theme(self) -> None:
        self.theme_mode = "light" if self.theme_mode == "dark" else "dark"
        self.apply_theme()
        self.persist_ui_settings()
        self.refresh()

    def apply_table_zoom(self) -> None:
        if not hasattr(self, "table"):
            return
        self.table_zoom = clamp_table_zoom(self.table_zoom)
        scale = self.table_zoom / 100
        body_size = max(8, int(round(9 * scale)))
        heading_size = max(8, int(round(9 * scale)))
        row_height = max(22, int(round(26 * scale)))
        self.style.configure("Main.Treeview", font=("Segoe UI", body_size), rowheight=row_height)
        self.style.configure("Main.Treeview.Heading", font=("Segoe UI", heading_size, "bold"))
        for column, width in DEFAULT_COLUMN_WIDTHS.items():
            self.table.column(
                column,
                width=max(48, int(round(width * scale))),
                anchor="center",
                stretch=column in {"airline", "country_or_region"},
            )
        self.zoom_text.set(f"{self.table_zoom}%")

    def set_table_zoom(self, value: int) -> None:
        self.table_zoom = clamp_table_zoom(value)
        self.apply_table_zoom()
        self.persist_ui_settings()

    def zoom_in(self) -> None:
        self.set_table_zoom(self.table_zoom + TABLE_ZOOM_STEP)

    def zoom_out(self) -> None:
        self.set_table_zoom(self.table_zoom - TABLE_ZOOM_STEP)

    def reset_zoom(self) -> None:
        self.set_table_zoom(int(DEFAULT_UI_SETTINGS["table_zoom"]))

    def apply_display_columns(self) -> None:
        if not hasattr(self, "table"):
            return
        self.hidden_columns = normalize_hidden_columns(self.hidden_columns)
        self.table.configure(displaycolumns=visible_display_columns(self.hidden_columns))

    def show_column_menu(self, event) -> None:
        menu = tk.Menu(self.root, tearoff=False)
        hidden = set(self.hidden_columns)
        for column in DISPLAY_COLUMNS:
            visible_var = tk.BooleanVar(value=column not in hidden)
            menu.add_checkbutton(
                label=DISPLAY_HEADINGS[column],
                variable=visible_var,
                command=lambda item=column, var=visible_var: self.set_column_visibility(item, var.get()),
            )
        menu.add_separator()
        menu.add_command(label="显示全部列", command=self.show_all_columns)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def set_column_visibility(self, column: str, visible: bool) -> None:
        hidden = set(normalize_hidden_columns(self.hidden_columns))
        current_visible = [item for item in DISPLAY_COLUMNS if item not in hidden]
        if not visible:
            if column not in hidden and len(current_visible) <= 1:
                messagebox.showwarning("至少保留一列", "数据表至少需要保留一列可见。", parent=self.root)
                return
            hidden.add(column)
        else:
            hidden.discard(column)
        self.hidden_columns = normalize_hidden_columns([column for column in DISPLAY_COLUMNS if column in hidden])
        if self.sort_column in hidden:
            self.sort_column = None
            self.sort_direction = None
            self.update_sort_headings()
        self.apply_display_columns()
        self.persist_ui_settings()

    def show_all_columns(self) -> None:
        self.hidden_columns = []
        self.apply_display_columns()
        self.persist_ui_settings()

    def update_reminder_visibility(self, has_items: bool) -> None:
        if self.content is None or self.reminder_frame is None:
            return
        if has_items and not self.reminder_visible:
            self.content.add(self.reminder_frame, weight=2)
            self.reminder_visible = True
        elif not has_items and self.reminder_visible:
            self.content.forget(self.reminder_frame)
            self.reminder_visible = False

    def add_search_option_combo(self, parent: ttk.Frame, label_text: str, field: str, width: int) -> None:
        ttk.Label(parent, text=label_text).pack(side=LEFT, padx=(0, 6))
        combo = ttk.Combobox(
            parent,
            textvariable=self.search_vars[field],
            width=width,
            values=filter_options(self.option_values_for_field(field), "", limit=500),
        )
        combo.pack(side=LEFT, padx=(0, 14))
        combo.bind("<KeyRelease>", lambda _event, item=field: self.filter_search_option_combo(item))
        combo.bind("<Button-1>", lambda _event, item=field: self.filter_search_option_combo(item))
        combo.bind("<Return>", lambda _event: self.apply_search())
        self.search_option_combos[field] = combo

    def add_search_time_combo(self, parent: ttk.Frame, label_text: str, key: str) -> None:
        if label_text:
            ttk.Label(parent, text=label_text).pack(side=LEFT, padx=(0, 6))
        combo = ttk.Combobox(parent, textvariable=self.search_vars[key], width=7, values=TIME_OPTIONS)
        combo.pack(side=LEFT, padx=(0, 8))
        combo.bind("<KeyRelease>", lambda _event, item=combo: self.filter_search_time_combo(item))
        combo.bind("<Button-1>", lambda _event, item=combo: self.filter_search_time_combo(item))
        combo.bind("<Return>", lambda _event: self.apply_search())
        self.search_time_combos.append(combo)

    def filter_search_option_combo(self, field: str) -> None:
        combo = self.search_option_combos.get(field)
        if combo is None:
            return
        combo.configure(
            values=filter_options(
                self.option_values_for_field(field),
                combo.get(),
                limit=500,
            )
        )

    def refresh_search_option_combos(self) -> None:
        for field in self.search_option_combos:
            self.filter_search_option_combo(field)

    def filter_search_time_combo(self, combo: ttk.Combobox) -> None:
        combo.configure(values=filter_options(TIME_OPTIONS, combo.get(), limit=len(TIME_OPTIONS)))

    def apply_search(self) -> None:
        try:
            self.refresh()
        except ValueError as exc:
            messagebox.showerror("查询条件有误", str(exc), parent=self.root)

    def clear_search(self) -> None:
        for variable in self.search_vars.values():
            variable.set("")
        for field in self.search_option_combos:
            self.filter_search_option_combo(field)
        for combo in self.search_time_combos:
            self.filter_search_time_combo(combo)
        self.refresh()

    def get_criteria(self) -> dict[str, str]:
        return {key: variable.get() for key, variable in self.search_vars.items()}

    def option_values_for_field(self, field: str) -> list[str]:
        config = OPTION_FIELDS[field]
        values = list(self.options.get(config["category"], []))
        values.extend(record.get(field, "") for record in self.records if record.get(field, ""))
        return normalize_options(values, config["max_length"])

    def airline_code_for(self, airline: str) -> str:
        return self.options.get("airline_codes", {}).get(airline.strip(), "")

    def apply_airline_code_prefixes(self, record: dict[str, str]) -> None:
        apply_airline_code_prefixes(record, self.options.get("airline_codes", {}))

    def validate_selected_options(self, record: dict[str, str]) -> None:
        for field in OPTION_FIELDS:
            value = record.get(field, "").strip()
            if not value:
                continue
            allowed = set(self.option_values_for_field(field))
            if value not in allowed:
                raise ValueError(f"{FIELD_LABELS[field]}必须从下拉列表中选择。若需要新增，请点击旁边的“管理”按钮。")

    def reload_from_database(self, select_id: str | None = None) -> None:
        self.data = load_data()
        self.records = self.data["records"]
        self.options = load_reference_options()
        self.refresh_search_option_combos()
        self.refresh(select_id=select_id)

    def current_export_rows(self) -> tuple[list[str], list[list[str]]]:
        headers = [DISPLAY_HEADINGS[column] for column in DISPLAY_COLUMNS]
        rows = [
            [group_display_value(group, column) for column in DISPLAY_COLUMNS]
            for group in self.current_display_groups
        ]
        return headers, rows

    def backup_database(self) -> None:
        try:
            ensure_database()
        except DatabaseStartupError as exc:
            messagebox.showerror("数据库无法备份", str(exc), parent=self.root)
            return
        default_name = f"flight_schedule_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        target = filedialog.asksaveasfilename(
            parent=self.root,
            title="备份数据库",
            initialfile=default_name,
            defaultextension=".db",
            filetypes=[("SQLite 数据库", "*.db"), ("所有文件", "*.*")],
        )
        if not target:
            return
        try:
            shutil.copy2(DB_FILE, target)
        except OSError as exc:
            messagebox.showerror("备份失败", f"无法写入备份文件：\n{exc}", parent=self.root)
            return
        messagebox.showinfo("备份完成", f"数据库已备份到：\n{target}", parent=self.root)

    def restore_database_backup(self) -> None:
        source = filedialog.askopenfilename(
            parent=self.root,
            title="恢复数据库备份",
            filetypes=[("SQLite 数据库", "*.db;*.sqlite;*.sqlite3"), ("所有文件", "*.*")],
        )
        if not source:
            return
        source_path = Path(source)
        try:
            check_database_integrity(source_path)
        except DatabaseStartupError as exc:
            messagebox.showerror("备份文件不可用", str(exc), parent=self.root)
            return
        if not messagebox.askyesno(
            "确认恢复备份",
            "恢复备份会用所选数据库替换当前数据库。程序会先自动保存一份当前数据库的安全备份。\n\n是否继续？",
            default=messagebox.NO,
            parent=self.root,
        ):
            return
        try:
            safety_backup = DB_FILE.with_name(f"flight_schedule_before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
            if DB_FILE.exists():
                shutil.copy2(DB_FILE, safety_backup)
            shutil.copy2(source_path, DB_FILE)
            self.reload_from_database()
        except (OSError, DatabaseStartupError) as exc:
            messagebox.showerror("恢复失败", f"无法恢复数据库备份：\n{exc}", parent=self.root)
            return
        messagebox.showinfo("恢复完成", "数据库备份已恢复，主界面数据已刷新。", parent=self.root)

    def export_visible_data(self) -> None:
        headers, rows = self.current_export_rows()
        if not rows:
            messagebox.showinfo("无可导出数据", "当前查询结果为空，没有可导出的航线。", parent=self.root)
            return
        target = filedialog.asksaveasfilename(
            parent=self.root,
            title="导出当前显示数据",
            initialfile=f"flight_schedule_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            defaultextension=".xlsx",
            filetypes=[("Excel 工作簿", "*.xlsx"), ("CSV 文件", "*.csv")],
        )
        if not target:
            return
        target_path = Path(target)
        if target_path.suffix.lower() not in {".xlsx", ".csv"}:
            target_path = target_path.with_suffix(".xlsx")
        try:
            if target_path.suffix.lower() == ".csv":
                write_csv(target_path, headers, rows)
            else:
                write_xlsx(target_path, headers, rows)
        except OSError as exc:
            messagebox.showerror("导出失败", f"无法写入导出文件：\n{exc}", parent=self.root)
            return
        messagebox.showinfo("导出完成", f"当前显示数据已导出到：\n{target_path}", parent=self.root)

    def import_legacy_json(self) -> None:
        source = filedialog.askopenfilename(
            parent=self.root,
            title="从 JSON 导入旧数据",
            filetypes=[("JSON 数据文件", "*.json"), ("所有文件", "*.*")],
        )
        if not source:
            return
        if not messagebox.askyesno(
            "确认导入",
            "将从所选 JSON 文件导入航班记录。相同 ID 的记录会更新，新的 ID 会新增。\n\n是否继续？",
            default=messagebox.NO,
            parent=self.root,
        ):
            return
        try:
            imported = import_json_records_to_database(Path(source))
            self.reload_from_database()
        except (OSError, ValueError, json.JSONDecodeError, DatabaseStartupError) as exc:
            messagebox.showerror("导入失败", f"无法导入所选 JSON 文件：\n{exc}", parent=self.root)
            return
        messagebox.showinfo("导入完成", f"已导入或更新 {imported} 条航班记录。", parent=self.root)

    def show_about(self) -> None:
        about = Toplevel(self.root)
        about.title("关于")
        about.resizable(False, False)
        about.transient(self.root)
        about.grab_set()
        if APP_ICON_FILE.exists():
            try:
                about.iconbitmap(str(APP_ICON_FILE))
            except Exception:
                pass

        body = ttk.Frame(about, padding=18)
        body.pack(fill=BOTH, expand=True)
        ttk.Label(body, text=APP_DISPLAY_NAME, font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0, 8))
        ttk.Label(body, text=f"版本：{APP_VERSION}").pack(anchor="w", pady=2)
        ttk.Label(body, text=f"作者：{APP_AUTHOR}").pack(anchor="w", pady=2)
        ttk.Label(body, text=f"数据库：{DB_FILE}").pack(anchor="w", pady=2)
        ttk.Label(body, text="GitHub：").pack(anchor="w", pady=(10, 2))
        link = ttk.Label(body, text=GITHUB_URL, style="Link.TLabel", cursor="hand2")
        link.pack(anchor="w")
        link.bind("<Button-1>", lambda _event: webbrowser.open(GITHUB_URL))
        ttk.Button(body, text="关闭", command=about.destroy).pack(anchor="e", pady=(14, 0))

    def refresh(self, select_id: str | None = None) -> None:
        criteria = self.get_criteria()
        self.current_results = filter_records(self.records, criteria)
        self.current_display_groups = sort_display_groups(
            grouped_display_records(self.current_results),
            self.sort_column,
            self.sort_direction,
        )
        self.table_row_records = {}
        self.record_to_row_id = {}
        self.table.delete(*self.table.get_children())
        for index, group in enumerate(self.current_display_groups):
            row_id = group_row_id(group)
            self.table_row_records[row_id] = group
            for record in group:
                self.record_to_row_id[record["id"]] = row_id
            missing = any(missing_fields(record) for record in group)
            pairing = any(needs_pairing(record) for record in group)
            values = (
                group_display_value(group, "status"),
                group_display_value(group, "outbound_flight_no"),
                group_display_value(group, "return_flight_no"),
                group_display_value(group, "airport_code"),
                group_display_value(group, "departure_time"),
                group_display_value(group, "arrival_time"),
                group_display_value(group, "aircraft_type"),
                group_display_value(group, "airline"),
                group_display_value(group, "country_or_region"),
                group_display_value(group, "route_pair_id"),
            )
            state = "missing" if missing else "pairing" if pairing else "complete"
            parity = "even" if index % 2 == 0 else "odd"
            tag = f"{state}_{parity}"
            self.table.insert("", END, iid=row_id, values=values, tags=(tag,))
        self.refresh_reminders()
        if select_id:
            row_id = self.record_to_row_id.get(select_id, select_id)
            if self.table.exists(row_id):
                self.table.selection_set(row_id)
                self.table.focus(row_id)
                self.table.see(row_id)
        self.update_sort_headings()
        missing_count = sum(1 for record in self.records if missing_fields(record))
        pairing_count = sum(1 for record in self.records if needs_pairing(record))
        self.status_var.set(
            f"共 {len(self.records)} 条数据记录，当前显示 {len(self.current_display_groups)} 条航线，待补录 {missing_count} 条，待关联 {pairing_count} 条"
        )

    def refresh_reminders(self) -> None:
        self.reminders.delete(*self.reminders.get_children())
        reminder_count = 0
        for record in self.records:
            missing = missing_fields(record)
            if missing:
                labels = "缺失：" + "、".join(FIELD_LABELS[field] for field in missing)
                self.reminders.insert("", END, iid=record["id"], values=(record_summary(record), labels), tags=("missing",))
                reminder_count += 1
            elif needs_pairing(record):
                self.reminders.insert("", END, iid=record["id"], values=(record_summary(record), "需关联去程/返程航班"), tags=("pairing",))
                reminder_count += 1
        self.update_reminder_visibility(reminder_count > 0)

    def persist_and_refresh(self, select_id: str | None = None) -> None:
        self.data["records"] = self.records
        save_data(self.data)
        self.refresh(select_id=select_id)

    def selected_record(self) -> dict[str, str] | None:
        selected = self.table.selection()
        if not selected:
            messagebox.showinfo("请选择记录", "请先在主列表中选择一条航线记录。", parent=self.root)
            return None
        group = self.table_row_records.get(selected[0], [])
        if not group:
            return None
        record_id = group[0].get("id", "")
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
        row_id = self.record_to_row_id.get(record_id)
        self.table.selection_set(row_id) if row_id and self.table.exists(row_id) else None
        FlightEditor(self, record, focus_field=focus_field)

    def pair_selected(self) -> None:
        record = self.selected_record()
        if record:
            self.open_pair_dialog(record)

    def open_pair_dialog(self, record: dict[str, str]) -> None:
        if missing_fields(record):
            messagebox.showwarning("请先补录", "该航线仍有必填信息未录入，请补录完整后再关联去程或返程航班。", parent=self.root)
            FlightEditor(self, record, focus_field=missing_fields(record)[0])
            return
        PairDialog(self, record, notice="请从机场代码相同的现有航班中选择对应的去程或返程航班。")

    def try_auto_pair_existing(self, record_id: str, original_record: dict[str, str]) -> None:
        record = next((item for item in self.records if item.get("id") == record_id), None)
        if not record or record.get("route_pair_id") or not route_info_complete(record):
            return
        candidates = strong_pair_candidates(self.records, record, original_record)
        if len(candidates) == 1:
            self.associate_records(record_id, candidates[0]["id"], show_message=False)
            messagebox.showinfo(
                "已自动关联",
                "已根据机场代码和补录的对应去程离港/返程抵港时间，将该航班与现有单程记录关联，并同步补齐对方空白字段。",
                parent=self.root,
            )
            return
        if len(candidates) > 1:
            notice = "找到多个同机场、同对应时间的候选航班，请手动选择要关联的去程或返程航班。"
        else:
            notice = "未找到唯一的自动匹配项。请从机场代码相同的现有航班中手动选择对应的去程或返程航班。"
        PairDialog(self, record, notice=notice)

    def get_counterparts(self, record: dict[str, str]) -> list[dict[str, str]]:
        return [item for item in paired_group(self.records, record) if item.get("id") != record.get("id")]

    def open_counterpart_editor(self, record_id: str, parent=None) -> None:
        record = next((item for item in self.records if item.get("id") == record_id), None)
        if not record:
            return
        counterparts = self.get_counterparts(record)
        if not counterparts:
            messagebox.showinfo("暂无对应航班", "该记录当前没有可跳转的对应去程或返程航班。", parent=parent or self.root)
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
        ttk.Label(body, text="该航线已保存。请同步检查并修改其对应的去程或返程航班。", style="Warning.TLabel", wraplength=360).pack(anchor="w", pady=(0, 10))
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
            messagebox.showerror("关联失败", "仅允许关联机场代码相同的去程/返程航班。", parent=parent or self.root)
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
            messagebox.showinfo("关联完成", "已关联所选去程/返程航班，并同步补齐对方空白字段。检索其中任一航班时，对应航班也会一起显示。", parent=parent or self.root)
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
                "该记录尚未关联对应的去程或返程航班。系统只允许删除一对往返航班，请先完成关联后再删除。",
                parent=self.root,
            )
            return
        lines = "\n".join(f"- {record_summary(item)}" for item in group)
        if not messagebox.askyesno(
            "确认删除往返航班",
            "删除操作将一并删除该关联组内的去程/返程航班，不允许仅删除其中任一单个航班。\n\n"
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
    try:
        FlightManagerApp(root)
    except DatabaseStartupError as exc:
        messagebox.showerror("数据库无法打开", str(exc), parent=root)
        root.destroy()
        return
    root.mainloop()


if __name__ == "__main__":
    main()
