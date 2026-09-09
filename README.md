# 航班航线管理程序

A local Python desktop tool for managing parent-company-isolated airport flight route schedule data.

## Files

- `airport_flight_schedule.xlsx`: original workbook source.
- `flight_schedule.db`: SQLite database used by the app.
- `flight_schedule.json`: legacy converted data file that can still be imported from the GUI.
- `reference_options.json`: legacy dropdown dictionaries migrated into SQLite on first database creation.
- `flight_manager.py`: Tkinter GUI for adding, searching, editing, deleting, and supplementing route records.
- `flight_commands.py`: offline command parsing and country/region code lookup.
- `test_flight_manager.py`: unit tests for import integrity, search, conflict detection, and JSON round-trip behavior.
- `FlightRouteManager.spec`: PyInstaller build configuration for the Windows executable.
- `flight_route_manager.ico`: desktop icon used by the app and executable.

## Run

```powershell
python flight_manager.py
```

The app reads and writes `flight_schedule.db` locally. If the database is missing, it is created automatically from the bundled starter data.
When migrating from an older JSON-based version, place the old `flight_schedule.json` next to the program before first launch, or use **从 JSON 导入旧数据** in the app. Blank fields in the JSON import will not overwrite existing completed database fields.

## Build EXE

Install PyInstaller in the Python environment you want to build with, then run:

```powershell
python -m PyInstaller FlightRouteManager.spec
```

The executable is created at `dist/FlightRouteManager.exe`. Keep `flight_schedule.db` next to the executable after first run; it is the user's editable local database.

## Main features

- Add, edit, delete, and precisely search route records.
- Startup parent-company login lets the user choose which parent company dataset to manage; no username or password is required.
- Parent-company add, rename, and delete actions live in the **管理母公司** dialog on the login screen.
- Optional keep-login behavior reopens the last selected parent company until the user logs out from the main window.
- Parent companies isolate flight records and local dropdown options from one another.
- The main management UI uses “subsidiary” for the company operating the route; subsidiaries are managed in the local dropdown manager and can have a two-character code.
- SQLite database storage with startup integrity checks and friendly database error messages.
- Backup and restore the SQLite database from the main window.
- Export the currently displayed routes to Excel `.xlsx` or CSV.
- Import legacy `flight_schedule.json` records from the main window.
- Manage subsidiaries and aircraft types directly from the main window toolbar.
- About window with software name, version, author, and GitHub link.
- Light and dark UI modes with comfortable non-pure-white/non-pure-black colors; the login screen follows the last saved mode.
- Main table UI preferences are stored locally in SQLite, including theme, hidden columns, and table zoom.
- The pending-completion reminder panel automatically hides when there is nothing to fix and reappears when missing or unpaired records exist.
- Right-click the main data table to hide or restore display columns without changing the underlying data.
- Main table rows use soft alternating colors while retaining status colors for missing or unpaired routes.
- Main table zoom controls adjust table font, row height, and column width from 80% to 140%.
- New records must include every required field before they can be saved.
- Flight numbers must be unique and use a two-character subsidiary code plus 1-4 digits.
- Subsidiary options include a required two-character code, which is automatically prefixed to outbound and return flight numbers.
- Airport codes must use three letters.
- Separate departure and destination airports, plus a positive-integer weekly frequency. Legacy `airport_code` continues to mean the destination airport for SQLite and JSON compatibility.
- Outbound departure and return arrival times are selected with separate hour and five-minute interval dropdowns.
- Search supports subsidiary, aircraft type, country/region filtering plus exact-time and time-range filters for outbound departure and return arrival.
- The main table collapses associated outbound/return records into one displayed route and supports three-state header sorting: ascending, descending, and default order.
- Aircraft type, subsidiary, and country/region fields are searchable dropdowns; typed text only filters choices and must match an existing option to save.
- Aircraft type and subsidiary options are managed in local popups and are limited to 25 characters; aircraft types, subsidiaries, and countries/regions can be renamed.
- Deleting a subsidiary or aircraft type also deletes all route records linked to it, including the associated outbound/return counterpart when a route is paired.
- Deleting a parent company, subsidiary, aircraft type, country/region, or paired route group requires an extra typed confirmation.
- Warn when outbound departure or return arrival times are already occupied.
- Mark records with missing required fields for later completion.
- Manually associate outbound and return flight records after legacy records are completed, using same-airport existing records as candidates.
- Automatically assigns an association ID when a newly added route has complete outbound and return information.
- When a legacy single-direction record is completed, the app tries to pair it with an existing same-airport complementary record and fills blank fields on the counterpart.
- When searching for one flight, associated outbound or return records are shown together.
- Deletions are only allowed for an associated outbound/return group, and the app deletes the group together.
- When editing an associated record, the app provides a direct button to open the corresponding flight record.

## Test

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m unittest -v
```

Native GUI workflow checks use an isolated test database:

```powershell
$env:RUN_FLIGHT_GUI_TESTS='1'
python -B -m unittest -v test_flight_manager_gui
```

## 1.3 命令录入

主界面顶部新增 **使用命令录入**。一行一条命令，必须依次填写以下五组数据，以空格分隔：

```text
出发机场-到达机场 往返航班号 去程离港/返程抵港 机型-班期 国家或地区代码
PVG-CDG 9C809/10 1230/1900 A339-7 FR
CAN-JFK 9C1239/40 0815/2200 A339-14 US
PVG-CAN 9C1234/5 0900/1800 A339-7 D
```

- `9C809/10` 展开为 `9C809/9C810`；`9C1234/5` 展开为 `9C1234/9C1235`；`9C1239/40` 展开为 `9C1239/9C1240`。简写替换去程数字部分末尾的相应位数，也支持完整形式 `9C809/9C810`。
- 两个机场均为三个英文字母，航班号含两位字母/数字子公司代码。小写字母自动规范化。
- 时间必须为四位 ASCII 数字，小时 00–23、分钟 00/05/10/…/55；班期为每周班数，允许 14 等大于 7 的正整数。
- 机型严格匹配现有名称；若机型名称包含空格，可将整个第四组加引号，如 `"Airbus A350-7"`。
- `FR`、`US` 等代码从当前母公司的国家/地区列表匹配。未登记的子公司代码、机型或国家/地区会弹出补充登记窗口，用户确认后保存到当前母公司的选项数据。
- `D` 不预设国家。首次使用时弹窗要求指定国家/地区；允许选择已有项或新增名称，随后保存该母公司的 `D` 对应关系。可在 **管理国家/地区 → 设为国内（D）** 中更改。
- **识别命令** 后显示预览、错误和时间占用明细。可通过 **编辑识别结果** 修正任意字段；预览编辑不会直接写入航线数据库。修改命令文本后必须重新识别。
- 航班号与数据库或本批次重复、缺漏或格式错误时，**确认录入** 不可用；同一出发机场的时间占用须单独确认。全部校验通过后，整批航线在一个事务中保存，每条往返航线自动获得关联 ID。
- 补充登记的选项即时保存；航线仅在点击 **确认录入** 后保存。重命名选项时会同步更新引用它的航线名称以及 `D` 对应关系。
- 主表默认列顺序为：去程航班号、返程航班号、出发机场、到达机场、去程离港、返程抵港、机型、班期、国家/地区。班期按数值排序，查询和导出同步支持新增字段。

启动时自动为旧 SQLite 数据库增加缺少的字段。原有机场代码、航班号、关联 ID 和母公司数据保持原值；旧记录的出发机场及班期留空并提醒补录。导入旧 JSON 的空白字段不会覆盖已经填写的新字段。

离线国家代码对应关系覆盖原有 195 个国家名称，并兼容部分地区及常用英文名称。代码依据 [ISO 3166 alpha-2](https://www.iso.org/iso-3166-country-codes.html)，英文名称/代码核对来源为 [Unicode CLDR territories](https://github.com/unicode-org/cldr-json/blob/main/cldr-json/cldr-localenames-full/main/en/territories.json)（2026-09-10）。程序运行时无需联网查询。

## Notes

The source workbook does not include flight numbers, aircraft type, subsidiary, or country/region data. Imported records keep those fields blank as placeholders, and the GUI marks incomplete records for later completion.

The source workbook also does not provide a reliable outbound/return pairing. Existing imported records remain unpaired until the user manually associates them in the GUI.
