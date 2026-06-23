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

## Test

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m unittest -v
```

## Notes

The source workbook does not include flight numbers, aircraft type, airline, or country/region data. Imported records keep those fields blank as placeholders, and the GUI marks incomplete records for later completion.
