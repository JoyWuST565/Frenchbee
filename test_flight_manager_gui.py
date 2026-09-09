"""Opt-in native Tk workflow checks, always using an isolated database.

RUN_FLIGHT_GUI_TESTS=1 python -B -m unittest -v test_flight_manager_gui
"""

from __future__ import annotations

import inspect
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import flight_manager as fm
from test_flight_commands import EXAMPLE, command_options


@unittest.skipUnless(os.environ.get("RUN_FLIGHT_GUI_TESTS") == "1", "Opt-in native GUI checks")
class FlightGuiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = Path(self.temp.name) / "gui.db"
        fm.create_database_from_payload(self.db)
        original_db = fm.DB_FILE
        for value in vars(fm).values():
            if inspect.isfunction(value) and value.__module__ == fm.__name__ and value.__defaults__:
                defaults = tuple(self.db if item == original_db else item for item in value.__defaults__)
                self.enterContext(patch.object(value, "__defaults__", defaults))
        self.enterContext(patch.object(fm, "DB_FILE", self.db))
        self.enterContext(patch.object(fm, "RUNTIME_DATA_FILE", Path(self.temp.name) / "absent.json"))
        self.company = fm.create_company("GUI Test Parent")
        fm.save_reference_options(command_options(), company_id=self.company["id"])
        self.root = fm.Tk()
        self.addCleanup(self.root.destroy)
        self.callback_errors = []
        self.root.report_callback_exception = lambda *error: self.callback_errors.append(error)
        self.root.after(30000, self.root.quit)
        self.app = fm.FlightManagerApp(self.root, self.company)
        self.root.update()
        self.messages = {}
        for name in ("showinfo", "showwarning", "showerror"):
            self.messages[name] = self.enterContext(patch.object(fm.messagebox, name))

    def screenshot(self, name, window):
        directory = os.environ.get("FLIGHT_GUI_SCREENSHOTS")
        if directory:
            from PIL import ImageGrab
            window.lift()
            window.update()
            target = Path(directory)
            target.mkdir(parents=True, exist_ok=True)
            x, y = window.winfo_rootx(), window.winfo_rooty()
            ImageGrab.grab(bbox=(x, y, x + window.winfo_width(), y + window.winfo_height())).save(target / (name + ".png"))

    def test_commands_registration_editing_and_commit(self):
        self.assertEqual(tuple(self.app.table["columns"]), fm.DISPLAY_COLUMNS)
        self.assertEqual([self.app.table.heading(column, "text") for column in fm.DISPLAY_COLUMNS], [
            "去程航班号", "返程航班号", "出发机场", "到达机场", "去程离港", "返程抵港", "机型", "班期", "国家/地区",
        ])
        self.assertIn("departure_airport_code", self.app.search_vars)
        dialog = fm.CommandEntryDialog(self.app)
        dialog.command_text.insert("1.0", EXAMPLE)
        self.root.update()
        dialog.recognize()
        self.root.update()
        self.assertTrue(dialog.confirm_button.instate(["!disabled"]))
        self.screenshot("command-preview", dialog)
        dialog.results.selection_set("1")

        def edit_preview():
            editor = next(child for child in dialog.winfo_children() if isinstance(child, fm.FlightEditor))
            self.assertEqual(editor.variables["departure_airport_code"].get(), "PVG")
            self.assertEqual(editor.variables["weekly_frequency"].get(), "7")
            editor.variables["weekly_frequency"].set("21")
            self.screenshot("command-editor", editor)
            editor.save()

        self.root.after(50, edit_preview)
        dialog.edit_result()
        self.assertEqual(dialog.drafts[0].record["weekly_frequency"], "21")
        self.assertEqual(fm.load_data(company_id=self.company["id"])["records"], [])
        dialog.command_text.insert("end", " EXTRA")
        self.root.update()
        self.assertTrue(dialog.confirm_button.instate(["disabled"]))
        dialog.recognize()
        self.assertTrue(dialog.confirm_button.instate(["disabled"]))
        dialog.command_text.delete("1.0", "end")
        dialog.command_text.insert("1.0", EXAMPLE)
        self.root.update()
        dialog.recognize()
        dialog.confirm()
        self.assertEqual(len(fm.load_data(company_id=self.company["id"])["records"]), 1)
        self.assertEqual(len(self.app.table.get_children()), 1)
        editor = fm.FlightEditor(self.app, self.app.records[0])
        self.assertEqual(editor.variables["departure_airport_code"].get(), "PVG")
        self.assertEqual(editor.variables["weekly_frequency"].get(), "7")
        editor.variables["weekly_frequency"].set("14")
        editor.save()
        self.assertEqual(fm.load_data(company_id=self.company["id"])["records"][0]["weekly_frequency"], "14")

        dialog = fm.CommandEntryDialog(self.app)
        text = "PVG-CAN ZZ100/1 0900/1800 B738-14 D"
        dialog.command_text.insert("1.0", text)
        registrations = []

        def register_missing():
            for child in dialog.winfo_children():
                if isinstance(child, fm.CommandReferenceDialog):
                    registrations.append(child.field)
                    child.name_var.set({"airline": "Test Subsidiary", "aircraft_type": "B738", "country_or_region": "China"}[child.field])
                    child.save()
                    break
            if len(registrations) < 3:
                self.root.after(50, register_missing)

        self.root.after(50, register_missing)
        dialog.recognize()
        self.assertEqual(registrations, ["airline", "aircraft_type", "country_or_region"])
        self.assertTrue(dialog.confirm_button.instate(["!disabled"]))
        options = fm.load_reference_options(company_id=self.company["id"])
        self.assertEqual(options["domestic_country"], "China")
        self.assertIn("B738", options["aircraft_types"])
        self.assertEqual(options["airline_codes"]["Test Subsidiary"], "ZZ")
        self.assertEqual(len(fm.load_data(company_id=self.company["id"])["records"]), 1)
        dialog.confirm()
        records = fm.load_data(company_id=self.company["id"])["records"]
        self.assertEqual(len(records), 2)
        self.assertTrue(all(record["route_pair_id"] for record in records))
        self.app.search_vars["departure_airport_code"].set("PVG")
        self.app.search_vars["airport_code"].set("CAN")
        self.app.apply_search()
        self.assertEqual(len(self.app.table.get_children()), 1)
        headers, rows = self.app.current_export_rows()
        self.assertEqual(headers[2:4], ["出发机场", "到达机场"])
        self.assertEqual(rows[0][7], "14")
        self.app.clear_search()
        self.app.toggle_sort("weekly_frequency")
        self.screenshot("main-light", self.root)
        self.app.toggle_theme()
        self.screenshot("main-dark", self.root)

        manager = fm.OptionManagerDialog(self.app, "country_or_region")
        manager.update()
        self.screenshot("country-manager", manager)
        france_id = next(key for key, value in manager.item_values.items() if value == "France")
        manager.table.selection_set(france_id)
        manager.load_selected()
        manager.value_text.set("Another France")
        manager.add_value()
        self.messages["showerror"].assert_called_once()
        self.messages["showerror"].reset_mock()
        self.assertNotIn("Another France", manager.values())
        item_id = next(key for key, value in manager.item_values.items() if value == "China")
        manager.table.selection_set(item_id)
        manager.load_selected()
        manager.value_text.set("Domestic Region")
        manager.rename_selected()
        renamed = fm.load_reference_options(company_id=self.company["id"])
        self.assertEqual(renamed["domestic_country"], "Domestic Region")
        self.assertEqual(renamed["country_codes"]["Domestic Region"], "CN")
        self.assertIn("Domestic Region", [record["country_or_region"] for record in fm.load_data(company_id=self.company["id"])["records"]])
        manager.destroy()
        self.root.update()
        self.assertFalse(self.callback_errors)
        self.messages["showerror"].assert_not_called()


if __name__ == "__main__":
    unittest.main()
