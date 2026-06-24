# Frenchbee Flight Schedule Manager

A local Python desktop tool for managing airport flight route schedule data.

## Files

- `airport_flight_schedule.xlsx`: original workbook source.
- `flight_schedule.json`: converted local data file used by the app.
- `reference_options.json`: local dropdown dictionaries for aircraft types, airlines, and countries/regions.
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
- Flight numbers must be unique and use a two-character airline code plus 1-4 digits.
- Airline options include a required two-character code, which is automatically prefixed to outbound and return flight numbers.
- Airport codes must use three letters.
- Outbound departure and return arrival times are selected with separate hour and five-minute interval dropdowns.
- Search supports country/region filtering plus exact-time and time-range filters for outbound departure and return arrival.
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
