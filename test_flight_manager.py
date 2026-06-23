from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from flight_manager import (
    DATA_FILE,
    HOUR_OPTIONS,
    MINUTE_OPTIONS,
    REFERENCE_OPTIONS_FILE,
    apply_airline_code_prefixes,
    blank_record,
    filter_records,
    filter_options,
    find_duplicate_flight_numbers,
    find_time_conflicts,
    load_data,
    load_reference_options,
    missing_fields,
    needs_pairing,
    normalize_airline_code,
    normalize_time,
    paired_group,
    route_info_complete,
    save_data,
    strong_pair_candidates,
    sync_blank_pair_fields,
    validate_record,
)


class FlightScheduleDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = load_data(DATA_FILE)
        cls.records = cls.data["records"]

    def test_imported_record_count(self) -> None:
        self.assertEqual(len(self.records), 86)
        self.assertEqual(sum(1 for record in self.records if record["departure_time"]), 43)
        self.assertEqual(sum(1 for record in self.records if record["arrival_time"]), 43)

    def test_original_workbook_values_are_preserved(self) -> None:
        departures = filter_records(self.records, {"airport_code": "RUN", "departure_time": "06:30"})
        arrivals = filter_records(self.records, {"airport_code": "JFK", "arrival_time": "05:05"})
        self.assertEqual(len(departures), 1)
        self.assertEqual(len(arrivals), 1)

    def test_imported_extra_fields_are_blank_placeholders(self) -> None:
        first = self.records[0]
        for field in ("outbound_flight_no", "return_flight_no", "aircraft_type", "airline", "country_or_region"):
            self.assertEqual(first[field], "")
        self.assertEqual(first["route_pair_id"], "")
        self.assertIn("outbound_flight_no", missing_fields(first))
        self.assertIn("aircraft_type", missing_fields(first))

    def test_exact_query_by_arrival_time_keeps_multiple_matches(self) -> None:
        arrivals = filter_records(self.records, {"arrival_time": "06:30"})
        self.assertEqual({record["airport_code"] for record in arrivals}, {"SXM", "YYZ"})

    def test_time_conflict_detection(self) -> None:
        candidate = {
            "id": "new",
            "departure_time": "06:30",
            "arrival_time": "06:30",
        }
        conflicts = find_time_conflicts(self.records, candidate)
        self.assertGreaterEqual(len(conflicts), 3)
        self.assertIn("离港", {conflict["type"] for conflict in conflicts})
        self.assertIn("到达", {conflict["type"] for conflict in conflicts})

    def test_associated_record_is_included_in_precise_flight_query(self) -> None:
        records = [
            {
                **blank_record(),
                "id": "outbound",
                "outbound_flight_no": "FB100",
                "return_flight_no": "",
                "airport_code": "JFK",
                "departure_time": "08:00",
                "arrival_time": "",
                "aircraft_type": "A350",
                "airline": "French bee",
                "country_or_region": "United States",
                "route_pair_id": "pair-test",
            },
            {
                **blank_record(),
                "id": "return",
                "outbound_flight_no": "",
                "return_flight_no": "FB101",
                "airport_code": "JFK",
                "departure_time": "",
                "arrival_time": "20:00",
                "aircraft_type": "A350",
                "airline": "French bee",
                "country_or_region": "United States",
                "route_pair_id": "pair-test",
            },
        ]
        result = filter_records(records, {"flight_no": "FB100"})
        self.assertEqual([record["id"] for record in result], ["outbound", "return"])

    def test_complete_unpaired_record_requires_manual_pairing(self) -> None:
        record = {
            **blank_record(),
            "outbound_flight_no": "FB200",
            "return_flight_no": "FB201",
            "airport_code": "LAX",
            "departure_time": "09:00",
            "arrival_time": "21:00",
            "aircraft_type": "A350",
            "airline": "French bee",
            "country_or_region": "United States",
        }
        self.assertTrue(route_info_complete(record))
        self.assertTrue(needs_pairing(record))
        record["route_pair_id"] = "pair-complete"
        self.assertFalse(needs_pairing(record))

    def test_paired_group_requires_pair_id(self) -> None:
        paired = [
            {**blank_record(), "id": "a", "route_pair_id": "pair-a"},
            {**blank_record(), "id": "b", "route_pair_id": "pair-a"},
            {**blank_record(), "id": "c", "route_pair_id": ""},
        ]
        self.assertEqual([record["id"] for record in paired_group(paired, paired[0])], ["a", "b"])
        self.assertEqual(paired_group(paired, paired[2]), [])

    def test_time_normalization(self) -> None:
        self.assertEqual(normalize_time("0815"), "08:15")
        self.assertEqual(normalize_time("6:30:00"), "06:30")
        self.assertEqual(normalize_time("06:30"), "06:30")
        with self.assertRaises(ValueError):
            normalize_time("24:00")
        with self.assertRaises(ValueError):
            normalize_time("08A5")

    def test_flight_number_airport_and_length_validation(self) -> None:
        record = {
            **blank_record(),
            "outbound_flight_no": "bf1",
            "return_flight_no": "BF1001",
            "airport_code": "jfk",
            "departure_time": "0815",
            "arrival_time": "19:30",
            "aircraft_type": "A350",
            "airline": "French bee",
            "country_or_region": "United States",
        }
        validate_record(record)
        validate_record({**record, "outbound_flight_no": "9C101", "return_flight_no": "231001"})
        with self.assertRaises(ValueError):
            validate_record({**record, "outbound_flight_no": "B!100"})
        with self.assertRaises(ValueError):
            validate_record({**record, "airport_code": "J1K"})
        with self.assertRaises(ValueError):
            validate_record({**record, "aircraft_type": "A" * 26})
        with self.assertRaises(ValueError):
            validate_record({**record, "airline": "A" * 26})
        with self.assertRaises(ValueError):
            validate_record({**record, "country_or_region": "A" * 51})

    def test_reference_options_include_current_sovereign_state_set(self) -> None:
        options = load_reference_options(REFERENCE_OPTIONS_FILE)
        countries = options["countries_or_regions"]
        self.assertEqual(len(countries), 195)
        self.assertIn("airline_codes", options)
        for country in ("USA", "UK", "UAE", "France", "Holy See", "Palestine"):
            self.assertIn(country, countries)

    def test_airline_code_normalization_and_prefixing(self) -> None:
        self.assertEqual(normalize_airline_code("bf"), "BF")
        self.assertEqual(normalize_airline_code("9c"), "9C")
        self.assertEqual(normalize_airline_code("23"), "23")
        with self.assertRaises(ValueError):
            normalize_airline_code("B")
        with self.assertRaises(ValueError):
            normalize_airline_code("B!")

        record = {**blank_record(), "airline": "French bee", "outbound_flight_no": "101", "return_flight_no": "BF102"}
        apply_airline_code_prefixes(record, {"French bee": "BF"})
        self.assertEqual(record["outbound_flight_no"], "BF101")
        self.assertEqual(record["return_flight_no"], "BF102")
        with self.assertRaises(ValueError):
            apply_airline_code_prefixes({**record, "outbound_flight_no": "AF101"}, {"French bee": "BF"})

    def test_duplicate_flight_number_detection(self) -> None:
        existing = [
            {**blank_record(), "id": "a", "outbound_flight_no": "BF101"},
            {**blank_record(), "id": "b", "return_flight_no": "BF102"},
        ]
        self.assertEqual(find_duplicate_flight_numbers(existing, {**blank_record(), "outbound_flight_no": "BF103"}), [])
        duplicates = find_duplicate_flight_numbers(existing, {**blank_record(), "outbound_flight_no": "BF101"})
        self.assertEqual(duplicates[0]["flight_no"], "BF101")
        self.assertEqual(find_duplicate_flight_numbers(existing, {**blank_record(), "outbound_flight_no": "BF101"}, exclude_id="a"), [])
        same_record = find_duplicate_flight_numbers(existing, {**blank_record(), "outbound_flight_no": "BF200", "return_flight_no": "BF200"})
        self.assertEqual(same_record[0]["field"], "same_record")

    def test_dropdown_filtering_prioritizes_prefix_then_contains(self) -> None:
        values = ["France", "South Africa", "Afghanistan", "Finland"]
        self.assertEqual(filter_options(values, "F"), ["France", "Finland", "South Africa", "Afghanistan"])

    def test_time_dropdown_options_cover_required_intervals(self) -> None:
        self.assertEqual(HOUR_OPTIONS[0], "00")
        self.assertEqual(HOUR_OPTIONS[-1], "23")
        self.assertEqual(MINUTE_OPTIONS, ["00", "05", "10", "15", "20", "25", "30", "35", "40", "45", "50", "55"])

    def test_strong_pair_candidate_uses_same_airport_and_complementary_time(self) -> None:
        original = {
            **blank_record(),
            "id": "source",
            "airport_code": "JFK",
            "departure_time": "08:00",
        }
        completed = {
            **original,
            "outbound_flight_no": "BF100",
            "return_flight_no": "BF101",
            "arrival_time": "20:00",
            "aircraft_type": "A350",
            "airline": "French bee",
            "country_or_region": "United States",
        }
        candidate = {
            **blank_record(),
            "id": "candidate",
            "airport_code": "JFK",
            "arrival_time": "20:00",
        }
        wrong_airport = {
            **blank_record(),
            "id": "wrong",
            "airport_code": "LAX",
            "arrival_time": "20:00",
        }
        result = strong_pair_candidates([completed, candidate, wrong_airport], completed, original)
        self.assertEqual([record["id"] for record in result], ["candidate"])

    def test_pair_sync_fills_blank_fields_without_overwriting_existing_values(self) -> None:
        source = {
            **blank_record(),
            "outbound_flight_no": "BF100",
            "return_flight_no": "BF101",
            "airport_code": "JFK",
            "departure_time": "08:00",
            "arrival_time": "20:00",
            "aircraft_type": "A350",
            "airline": "French bee",
            "country_or_region": "United States",
        }
        target = {
            **blank_record(),
            "airport_code": "JFK",
            "arrival_time": "20:00",
            "aircraft_type": "Existing type",
        }
        sync_blank_pair_fields(source, target)
        self.assertEqual(target["outbound_flight_no"], "BF100")
        self.assertEqual(target["return_flight_no"], "BF101")
        self.assertEqual(target["departure_time"], "08:00")
        self.assertEqual(target["aircraft_type"], "Existing type")

    def test_save_and_reload_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "flight_schedule.json"
            data = copy.deepcopy(self.data)
            save_data(data, path)
            loaded = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(len(loaded["records"]), 86)
            self.assertEqual(loaded["records"][0]["airport_code"], self.records[0]["airport_code"])


if __name__ == "__main__":
    unittest.main()
