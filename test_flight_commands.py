from __future__ import annotations

import copy
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

import flight_manager as fm
from flight_commands import default_country_code, expand_flight_numbers, missing_command_options


def command_options():
    return fm.normalized_reference_payload({
        "airlines": ["Spring Airlines"], "airline_codes": {"Spring Airlines": "9C"},
        "aircraft_types": ["A339"], "countries_or_regions": ["France", "USA", "China"],
    })


EXAMPLE = "PVG-CDG 9C809/10 1230/1900 A339-7 FR"
SECOND = "CAN-JFK 9C1239/40 0815/2200 A339-14 US"


class CommandParsingTests(unittest.TestCase):
    def test_flight_suffix_examples_and_full_numbers(self):
        for token, expected in {
            "9C1234/5": ("9C", "9C1234", "9C1235"),
            "9c1239/40": ("9C", "9C1239", "9C1240"),
            "9C809/10": ("9C", "9C809", "9C810"),
            "231/2": ("23", "231", "232"),
            "BF10/BF9": ("BF", "BF10", "BF9"),
        }.items():
            with self.subTest(token=token):
                self.assertEqual(expand_flight_numbers(token), expected)
        for token in ("9C12345/6", "9C１２/3", "9C12/BF13", "9C12", "C1/2"):
            with self.subTest(token=token), self.assertRaises(ValueError):
                expand_flight_numbers(token)

    def test_complete_example_and_multiple_lines(self):
        options = command_options()
        drafts = fm.recognize_commands(EXAMPLE + "\n\n" + SECOND, options)
        self.assertEqual([d.line_number for d in drafts], [1, 3])
        expected = {
            "departure_airport_code": "PVG", "airport_code": "CDG", "outbound_flight_no": "9C809",
            "return_flight_no": "9C810", "departure_time": "12:30", "arrival_time": "19:00",
            "aircraft_type": "A339", "weekly_frequency": "7", "country_or_region": "France",
            "airline": "Spring Airlines",
        }
        self.assertEqual({k: drafts[0].record[k] for k in expected}, expected)
        self.assertEqual(drafts[1].record["weekly_frequency"], "14")
        self.assertFalse(any(fm.validate_command_drafts(drafts, [], options)[0].values()))

    def test_invalid_syntax_order_values_and_duplicates(self):
        options = command_options()
        for text in (
            EXAMPLE + " EXTRA", "PVG-CDG 1230/1900 9C809/10 A339-7 FR", "PVG-CDG",
            EXAMPLE.replace("1230", "2460"), EXAMPLE.replace("1230", "1232"),
            EXAMPLE.replace("A339-7", "A339-0"), EXAMPLE.replace("A339-7", "A339--1"),
            EXAMPLE.replace("A339-7", "A339-1.5"), EXAMPLE.replace("A339-7", "A339-７"),
            EXAMPLE.replace("PVG", "PV1"), EXAMPLE.replace("9C809/10", "9C809/809"),
            EXAMPLE.replace("FR", "FRA"), EXAMPLE + "\n" + EXAMPLE,
        ):
            with self.subTest(text=text):
                drafts = fm.recognize_commands(text, options)
                self.assertTrue(any(fm.validate_command_drafts(drafts, [], options)[0].values()))
        existing = fm.recognize_commands(EXAMPLE, options)[0].record
        self.assertTrue(any(fm.validate_command_drafts(fm.recognize_commands(EXAMPLE, options), [existing], options)[0].values()))

    def test_unregistered_options_and_domestic_resolution(self):
        options = {"airlines": [], "aircraft_types": [], "countries_or_regions": []}
        text = EXAMPLE.replace("FR", "D")
        self.assertEqual(missing_command_options(text + "\n" + text, options), [
            ("airline", "9C", ""), ("aircraft_type", "A339", "A339"), ("country_or_region", "D", ""),
        ])
        self.assertTrue(fm.recognize_commands(text, options)[0].parse_errors)
        options = fm.register_command_option(options, "airline", "9C", "Spring Airlines")
        options = fm.register_command_option(options, "aircraft_type", "A339", "A339")
        options = fm.register_command_option(options, "country_or_region", "D", "China")
        self.assertEqual(options["domestic_country"], "China")
        self.assertEqual(options["countries_or_regions"], ["China"])
        self.assertEqual(missing_command_options(text, options), [])
        draft = fm.recognize_commands(text, options)[0]
        self.assertEqual(draft.record["country_or_region"], "China")
        self.assertFalse(draft.parse_errors)
        options = fm.register_command_option(options, "country_or_region", "FR", "France")
        self.assertEqual(fm.recognize_commands(EXAMPLE, options)[0].record["country_or_region"], "France")
        with self.assertRaises(ValueError):
            fm.register_command_option(options, "country_or_region", "US", "France")

    def test_ambiguous_codes_require_manual_selection(self):
        options = command_options()
        options["airlines"].append("Another Airline")
        options["airline_codes"]["Another Airline"] = "9C"
        draft = fm.recognize_commands(EXAMPLE, options)[0]
        self.assertTrue(draft.parse_errors)
        draft.record["airline"] = "Spring Airlines"
        draft.parse_errors.clear()
        self.assertFalse(any(fm.validate_command_drafts([draft], [], options)[0].values()))

    def test_country_codes_cover_all_legacy_countries(self):
        names = json.loads(Path(__file__).with_name("reference_options.json").read_text(encoding="utf-8"))["countries_or_regions"]
        self.assertEqual(len(names), 195)
        self.assertTrue(all(default_country_code(name) for name in names))
        self.assertEqual(len({default_country_code(name) for name in names}), len(names))
        self.assertEqual([default_country_code(name) for name in ("USA", "France", "UK", "UAE")], ["US", "FR", "GB", "AE"])

    def test_new_fields_validation_sort_search_and_pair_compatibility(self):
        options = command_options()
        first = fm.recognize_commands(EXAMPLE, options)[0].record
        second = fm.recognize_commands(SECOND, options)[0].record
        for value in ("1", "7", "14", "999999999999999999999"):
            fm.validate_record({**first, "weekly_frequency": value})
        for field, value in (("weekly_frequency", "-7"), ("weekly_frequency", "0"), ("departure_airport_code", "P1G")):
            with self.assertRaises(ValueError):
                fm.validate_record({**first, field: value})
        records = [first, second]
        self.assertEqual(fm.filter_records(records, {"departure_airport_code": "pvg", "airport_code": "cdg", "airline": "Spring Airlines", "departure_start": "12:00", "departure_end": "13:00"}), [first])
        groups = fm.sort_display_groups([[second], [first]], "weekly_frequency", "asc")
        self.assertEqual([g[0]["weekly_frequency"] for g in groups], ["7", "14"])
        self.assertFalse(fm.airports_compatible(first, {**first, "departure_airport_code": "CAN"}))
        self.assertTrue(fm.airports_compatible(first, {**first, "departure_airport_code": ""}))
        self.assertFalse(fm.find_time_conflicts([first], {**first, "departure_airport_code": "CAN"}))


class CommandStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "test.db"
        self.company = fm.create_company("Test Parent", self.path)
        self.other = fm.create_company("Other Parent", self.path)
        self.options = command_options()
        fm.save_reference_options(self.options, self.path, self.company["id"])

    def test_batch_persists_new_fields_and_pairs_without_touching_other_parent(self):
        other_record = {**fm.blank_record(), "airport_code": "LAX", "id": "other-parent-record"}
        fm.save_data({"records": [other_record]}, self.path, self.other["id"])
        drafts = fm.recognize_commands(EXAMPLE + "\n" + SECOND, self.options)
        self.assertEqual(fm.commit_command_drafts(drafts, self.company["id"], self.path), 2)
        records = fm.load_data(self.path, self.company["id"])["records"]
        self.assertEqual([r["weekly_frequency"] for r in records], ["7", "14"])
        self.assertEqual([r["departure_airport_code"] for r in records], ["PVG", "CAN"])
        self.assertTrue(all(r["route_pair_id"] and not fm.missing_fields(r) for r in records))
        self.assertEqual(len({r["route_pair_id"] for r in records}), 2)
        self.assertEqual(fm.filter_records(records, {"flight_no": "9C810"})[0]["outbound_flight_no"], "9C809")
        self.assertEqual(fm.load_data(self.path, self.other["id"])["records"], [other_record])
        with self.assertRaises(ValueError):
            fm.commit_command_drafts(drafts, self.company["id"], self.path)
        self.assertEqual(len(fm.load_data(self.path, self.company["id"])["records"]), 2)

    def test_batch_rollback_if_second_insert_fails(self):
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute("CREATE TRIGGER fail_second BEFORE INSERT ON flights WHEN NEW.airport_code = 'JFK' BEGIN SELECT RAISE(ABORT, 'simulated disk failure'); END")
        drafts = fm.recognize_commands(EXAMPLE + "\n" + SECOND, self.options)
        with self.assertRaises(sqlite3.Error):
            fm.commit_command_drafts(drafts, self.company["id"], self.path)
        self.assertEqual(fm.load_data(self.path, self.company["id"])["records"], [])

    def test_conflicts_require_acknowledgement_and_are_rechecked(self):
        drafts = fm.recognize_commands(EXAMPLE + "\n" + SECOND.replace("CAN-JFK", "PVG-JFK").replace("0815/2200", "1230/1900"), self.options)
        errors, warnings = fm.validate_command_drafts(drafts, [], self.options)
        self.assertFalse(any(errors.values()))
        self.assertTrue(any(warnings.values()))
        with self.assertRaises(ValueError):
            fm.commit_command_drafts(drafts, self.company["id"], self.path)
        self.assertEqual(fm.commit_command_drafts(drafts, self.company["id"], self.path, set(fm.command_messages(warnings))), 2)

    def test_registration_persistence_and_company_isolation(self):
        options = fm.register_command_option(self.options, "country_or_region", "D", "China")
        fm.save_reference_options(options, self.path, self.company["id"])
        loaded = fm.load_reference_options(self.path, self.company["id"])
        self.assertEqual(loaded["domestic_country"], "China")
        self.assertEqual(loaded["country_codes"]["France"], "FR")
        self.assertEqual(fm.load_reference_options(self.path, self.other["id"])["domestic_country"], "")

    def test_commit_rechecks_database_changes_since_preview(self):
        drafts = fm.recognize_commands(EXAMPLE, self.options)
        self.assertFalse(any(fm.validate_command_drafts(drafts, [], self.options)[0].values()))
        changed_options = copy.deepcopy(self.options)
        changed_options["aircraft_types"] = []
        fm.save_reference_options(changed_options, self.path, self.company["id"])
        with self.assertRaises(ValueError):
            fm.commit_command_drafts(drafts, self.company["id"], self.path)
        self.assertEqual(fm.load_data(self.path, self.company["id"])["records"], [])
        fm.save_reference_options(self.options, self.path, self.company["id"])
        conflict = fm.recognize_commands(EXAMPLE.replace("9C809/10", "9C900/1"), self.options)[0].record
        fm.save_data({"records": [conflict]}, self.path, self.company["id"])
        with self.assertRaises(ValueError):
            fm.commit_command_drafts(drafts, self.company["id"], self.path, set())
        self.assertEqual(len(fm.load_data(self.path, self.company["id"])["records"]), 1)

    def test_repository_database_migration_preserves_all_saved_values(self):
        source = Path(__file__).with_name("flight_schedule.db").resolve()
        target = Path(self.temp.name) / "shipped-copy.db"
        with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as connection:
            connection.row_factory = sqlite3.Row
            snapshots = {table: [dict(row) for row in connection.execute(f"SELECT * FROM {table}")] for table in ("flights", "companies", "reference_options", "app_settings")}
            with closing(sqlite3.connect(target)) as destination:
                connection.backup(destination)
        fm.ensure_database(target)
        with closing(sqlite3.connect(target)) as connection:
            connection.row_factory = sqlite3.Row
            for table, before in snapshots.items():
                columns = list(before[0]) if before else []
                if columns:
                    after = [dict(row) for row in connection.execute(f"SELECT {', '.join(columns)} FROM {table}")]
                    self.assertCountEqual(before, after, table)

    def test_import_blank_legacy_values_preserves_new_fields(self):
        fm.commit_command_drafts(fm.recognize_commands(EXAMPLE, self.options), self.company["id"], self.path)
        record = fm.load_data(self.path, self.company["id"])["records"][0]
        legacy = {key: value for key, value in record.items() if key not in {"departure_airport_code", "weekly_frequency"}}
        json_path = Path(self.temp.name) / "old.json"
        fm.save_data({"records": [legacy]}, json_path)
        fm.import_json_records_to_database(json_path, self.path, self.company["id"])
        loaded = fm.load_data(self.path, self.company["id"])["records"][0]
        self.assertEqual(loaded["weekly_frequency"], "7")
        self.assertEqual(loaded["departure_airport_code"], "PVG")

    def test_v1_migration_retains_records_options_and_is_idempotent(self):
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute("INSERT INTO flights(company_id,id,outbound_flight_no,airport_code,route_pair_id) VALUES (?, 'legacy', '9C809', 'CDG', 'pair-legacy')", (self.company["id"],))
            connection.execute("ALTER TABLE flights DROP COLUMN departure_airport_code")
            connection.execute("ALTER TABLE flights DROP COLUMN weekly_frequency")
            connection.execute("ALTER TABLE companies DROP COLUMN domestic_country")
            connection.execute("ALTER TABLE reference_options DROP COLUMN country_code")
        fm.ensure_database(self.path)
        first = fm.load_data(self.path, self.company["id"])["records"]
        fm.ensure_database(self.path)
        self.assertEqual(first, fm.load_data(self.path, self.company["id"])["records"])
        self.assertEqual(first[0]["outbound_flight_no"], "9C809")
        self.assertEqual(first[0]["route_pair_id"], "pair-legacy")
        self.assertEqual(first[0]["departure_airport_code"], "")
        self.assertEqual(first[0]["weekly_frequency"], "")
        self.assertEqual(fm.load_reference_options(self.path, self.company["id"])["country_codes"]["France"], "FR")
        self.assertEqual(fm.load_reference_options(self.path, self.company["id"])["airline_codes"], {"Spring Airlines": "9C"})


if __name__ == "__main__":
    unittest.main()
