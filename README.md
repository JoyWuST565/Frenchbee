# Frenchbee Flight Schedule Manager

A local Python desktop tool for managing airport flight route schedule data.

## Files

- `airport_flight_schedule.xlsx`: original workbook source.
- `flight_schedule.db`: SQLite database used by the app.
- `flight_schedule.json`: legacy converted data file that can still be imported from the GUI.
- `reference_options.json`: legacy dropdown dictionaries migrated into SQLite on first database creation.
- `flight_manager.py`: Tkinter GUI for adding, searching, editing, deleting, and supplementing route records.
- `test_flight_manager.py`: unit tests for import integrity, search, conflict detection, and JSON round-trip behavior.
- `FrenchbeeFlightManager.spec`: PyInstaller build configuration for the Windows executable.
- `frenchbee_flight_manager.ico`: desktop icon used by the app and executable.

## Run

```powershell
python flight_manager.py
```

The app reads and writes `flight_schedule.db` locally. If the database is missing, it is created automatically from the bundled starter data.
When migrating from an older JSON-based version, place the old `flight_schedule.json` next to the program before first launch, or use **从 JSON 导入旧数据** in the app. Blank fields in the JSON import will not overwrite existing completed database fields.

## Build EXE

Install PyInstaller in the Python environment you want to build with, then run:

```powershell
python -m PyInstaller FrenchbeeFlightManager.spec
```

The executable is created at `dist/FrenchbeeFlightManager.exe`. Keep `flight_schedule.db` next to the executable after first run; it is the user's editable local database.

## Main features

- Add, edit, delete, and precisely search route records.
- SQLite database storage with startup integrity checks and friendly database error messages.
- Backup and restore the SQLite database from the main window.
- Export the currently displayed routes to Excel `.xlsx` or CSV.
- Import legacy `flight_schedule.json` records from the main window.
- About window with software name, version, author, and GitHub link.
- Light and dark UI modes with comfortable non-pure-white/non-pure-black colors.
- Main table UI preferences are stored locally in SQLite, including theme, hidden columns, and table zoom.
- The pending-completion reminder panel automatically hides when there is nothing to fix and reappears when missing or unpaired records exist.
- Right-click the main data table to hide or restore display columns without changing the underlying data.
- Main table rows use soft alternating colors while retaining status colors for missing or unpaired routes.
- Main table zoom controls adjust table font, row height, and column width from 80% to 140%.
- New records must include every required field before they can be saved.
- Flight numbers must be unique and use a two-character airline code plus 1-4 digits.
- Airline options include a required two-character code, which is automatically prefixed to outbound and return flight numbers.
- Airport codes must use three letters.
- Outbound departure and return arrival times are selected with separate hour and five-minute interval dropdowns.
- Search supports airline, aircraft type, country/region filtering plus exact-time and time-range filters for outbound departure and return arrival.
- The main table collapses associated outbound/return records into one displayed route and supports three-state header sorting: ascending, descending, and default order.
- Aircraft type, airline, and country/region fields are searchable dropdowns; typed text only filters choices and must match an existing option to save.
- Aircraft type and airline options are managed in local popups and are limited to 25 characters; countries/regions are limited to 50 characters and can also be renamed.
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

## Notes

The source workbook does not include flight numbers, aircraft type, airline, or country/region data. Imported records keep those fields blank as placeholders, and the GUI marks incomplete records for later completion.

The source workbook also does not provide a reliable outbound/return pairing. Existing imported records remain unpaired until the user manually associates them in the GUI.
