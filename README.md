# Frenchbee Flight Schedule Manager

A local Python desktop tool for managing airport flight route schedule data.

## Files

- `airport_flight_schedule.xlsx`: original workbook source.
- `flight_schedule.json`: converted local data file used by the app.
- `flight_manager.py`: Tkinter GUI for adding, searching, editing, deleting, and supplementing route records.
- `test_flight_manager.py`: unit tests for import integrity, search, conflict detection, and JSON round-trip behavior.

## Run

```powershell
python flight_manager.py
```

The app only reads and writes `flight_schedule.json` locally.

## Main features

- Add, edit, delete, and precisely search route records.
- New records must include every required field before they can be saved.
- Flight numbers must use two letters plus 1-4 digits, and airport codes must use three letters.
- Times can be entered as `HH:MM` or four digits such as `0815`, which is saved as `08:15`.
- Warn when departure or arrival times are already occupied.
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
