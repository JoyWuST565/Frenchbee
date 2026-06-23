from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from flight_manager import (
    DATA_FILE,
    blank_record,
    filter_records,
    find_time_conflicts,
    load_data,
    missing_fields,
    needs_pairing,
    normalize_time,
    paired_group,
    route_info_complete,
    save_data,
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
        self.assertEqual(normalize_time("6:30:00"), "06:30")
        self.assertEqual(normalize_time("06:30"), "06:30")
        with self.assertRaises(ValueError):
            normalize_time("24:00")

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
