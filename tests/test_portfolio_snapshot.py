import csv
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "finance" / "scripts" / "portfolio_snapshot.py"
SPEC = importlib.util.spec_from_file_location("portfolio_snapshot", SCRIPT)
snapshot = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(snapshot)

FIELDS = ["symbol", "quantity", "price", "currency", "price_as_of", "fx_to_base"]
NOW = "2026-11-12T16:00:00Z"


class PortfolioSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "portfolio.csv"

    def row(self, **changes):
        result = {"symbol": "EXAMPLE_A", "quantity": "2", "price": "20", "currency": "USD",
                  "price_as_of": "2026-11-10T16:00:00Z", "fx_to_base": "1"}
        result.update(changes)
        return result

    def write(self, rows, fields=FIELDS, encoding="utf-8"):
        with self.path.open("w", encoding=encoding, newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    def analyze(self, **kwargs):
        return snapshot.build_snapshot(self.path, "USD", kwargs.pop("as_of", NOW), **kwargs)

    def codes(self, result):
        return {warning["code"] for warning in result["warnings"]}

    def test_cross_currency_values_weights_and_exposure(self):
        self.write([self.row(), self.row(symbol="EXAMPLE_B", quantity="3", price="40", currency="AUD", fx_to_base="0.5")])
        result = self.analyze()
        self.assertEqual(result["total_value_base"], "100")
        self.assertEqual([p["value_base"] for p in result["positions"]], ["40", "60"])
        self.assertEqual([p["weight_pct"] for p in result["positions"]], ["40", "60"])
        self.assertEqual(result["quote_currency_exposure"], [
            {"currency": "AUD", "value_base": "60", "weight_pct": "60"},
            {"currency": "USD", "value_base": "40", "weight_pct": "40"},
        ])
        self.assertEqual(self.codes(result), {"fx_time_unverified"})
        self.assertEqual(result["as_of"], "2026-11-12T16:00:00+00:00")

    def test_decimal_values_are_exact_and_percentages_are_rounded(self):
        self.write([self.row(quantity="0.1", price="0.2"), self.row(symbol="EXAMPLE_B", quantity="0.2", price="0.2")])
        result = self.analyze()
        self.assertEqual(result["total_value_base"], "0.06")
        self.assertEqual([p["weight_pct"] for p in result["positions"]], ["33.33333333", "66.66666667"])

    def test_all_zero_weights_are_null(self):
        self.write([self.row(quantity="0"), self.row(symbol="EXAMPLE_B", price="0")])
        result = self.analyze()
        self.assertEqual(result["total_value_base"], "0")
        self.assertTrue(all(p["weight_pct"] is None for p in result["positions"]))
        self.assertIsNone(result["quote_currency_exposure"][0]["weight_pct"])
        self.assertEqual(self.codes(result), {"zero_total", "zero_price"})

    def test_stale_price_threshold_uses_calendar_duration(self):
        self.write([self.row(price_as_of="2026-11-09T16:00:00Z")])
        self.assertNotIn("stale_price", self.codes(self.analyze()))
        self.assertIn("stale_price", self.codes(self.analyze(as_of="2026-11-12T16:00:01Z")))

    def test_same_instants_in_different_timezones_are_not_mixed_or_future(self):
        self.write([self.row(price_as_of="2026-11-13T03:00:00+11:00"),
                    self.row(symbol="EXAMPLE_B", price_as_of="2026-11-12T16:00:00Z")])
        self.assertEqual(self.analyze()["warnings"], [])

    def test_future_and_naive_timestamps_are_rejected(self):
        for value in ["2026-11-13T03:00:01+11:00", "2026-11-10T16:00:00", "2026-11-10", "bad"]:
            with self.subTest(value=value):
                self.write([self.row(price_as_of=value)])
                with self.assertRaises(ValueError):
                    self.analyze()
        self.write([self.row()])
        with self.assertRaisesRegex(ValueError, "timezone"):
            self.analyze(as_of="2026-11-12T16:00:00")

    def test_mixed_quote_times_produce_warning(self):
        self.write([self.row(), self.row(symbol="EXAMPLE_B", price_as_of="2026-11-10T17:00:00Z")])
        self.assertIn("mixed_price_times", self.codes(self.analyze()))

    def test_inconsistent_fx_rates_produce_warning(self):
        self.write([self.row(currency="AUD", fx_to_base="0.5"),
                    self.row(symbol="EXAMPLE_B", currency="AUD", fx_to_base="0.6")])
        result = self.analyze()
        self.assertEqual(result["total_value_base"], "44")
        self.assertEqual(self.codes(result), {"fx_time_unverified", "mixed_fx_rates"})

    def test_shipped_example_matches_hand_calculation(self):
        result = snapshot.build_snapshot(ROOT / "skills/finance/assets/portfolio.example.csv", "USD", NOW)
        self.assertEqual(result["total_value_base"], "100")
        self.assertEqual([p["weight_pct"] for p in result["positions"]], ["40", "60"])

    def test_invalid_numbers_are_rejected(self):
        for field in ["quantity", "price", "fx_to_base"]:
            for value in ["NaN", "Infinity", "-Infinity", "-1", "1_000", "", "1e99999999"]:
                with self.subTest(field=field, value=value):
                    self.write([self.row(currency="AUD", **{field: value})])
                    with self.assertRaises(ValueError):
                        self.analyze()

    def test_base_currency_blank_fx_is_one_and_other_rates_rejected(self):
        self.write([self.row(fx_to_base="")])
        self.assertEqual(self.analyze()["total_value_base"], "40")
        for currency, rate in [("USD", "2"), ("AUD", "0"), ("AUD", "")]:
            with self.subTest(currency=currency, rate=rate):
                self.write([self.row(currency=currency, fx_to_base=rate)])
                with self.assertRaises(ValueError):
                    self.analyze()

    def test_duplicate_identity_and_missing_symbols_are_rejected(self):
        self.write([self.row(), self.row(symbol="example_a")])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.analyze()
        self.write([self.row(symbol=" ")])
        with self.assertRaisesRegex(ValueError, "symbol"):
            self.analyze()

    def test_bom_and_reordered_headers(self):
        self.write([self.row()], fields=list(reversed(FIELDS)), encoding="utf-8-sig")
        self.assertEqual(self.analyze()["total_value_base"], "40")

    def test_empty_missing_duplicate_and_extra_headers_are_rejected(self):
        for contents in ["", ",".join(FIELDS) + "\n", "symbol,quantity\nA,2\n",
                         ",".join(FIELDS + ["price"]) + "\n", ",".join(FIELDS + ["unknown"]) + "\n"]:
            with self.subTest(contents=contents):
                self.path.write_text(contents, encoding="utf-8")
                with self.assertRaises(ValueError):
                    self.analyze()

    def test_malformed_csv_rows_are_rejected(self):
        for row in ["A,2,20,USD,2026-11-10T16:00:00Z", "A,2,20,USD,2026-11-10T16:00:00Z,1,extra", '"unterminated']:
            with self.subTest(row=row):
                self.path.write_text(",".join(FIELDS) + "\n" + row + "\n", encoding="utf-8")
                with self.assertRaises((ValueError, csv.Error)):
                    self.analyze()

    def test_bad_currency_and_negative_threshold_are_rejected(self):
        self.write([self.row(currency="US")])
        with self.assertRaisesRegex(ValueError, "currency"):
            self.analyze()
        self.write([self.row()])
        with self.assertRaisesRegex(ValueError, "max_age_days"):
            self.analyze(max_age_days=-1)

    def test_minor_units_and_currency_case_are_not_silently_converted(self):
        for currency in ["GBp", "GBX", "ZAc", "ZAC", "ILa", "ILA", "usd"]:
            with self.subTest(currency=currency):
                self.write([self.row(symbol="LSE:EXAMPLE", quantity="100", price="250", currency=currency, fx_to_base="1.3")])
                with self.assertRaisesRegex(ValueError, "currency"):
                    self.analyze()
        self.write([self.row(symbol="LSE:EXAMPLE", quantity="100", price="2.50", currency="GBP", fx_to_base="1.3")])
        self.assertEqual(self.analyze()["total_value_base"], "325")

    def test_values_exceeding_precision_fail_instead_of_silently_rounding(self):
        self.write([self.row(quantity="1.1234567890123456789012345678901234567890",
                             price="1.1234567890123456789012345678901234567890")])
        with self.assertRaisesRegex(ValueError, "precision"):
            self.analyze()

    def test_cli_success_and_failure_without_partial_output(self):
        self.write([self.row()])
        command = [sys.executable, str(SCRIPT), str(self.path), "--base-currency", "USD", "--as-of", NOW]
        good = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(good.returncode, 0, good.stderr)
        self.assertEqual(json.loads(good.stdout)["total_value_base"], "40")
        self.assertEqual(good.stderr, "")
        self.write([self.row(), self.row(symbol="EXAMPLE_B", quantity="bad")])
        bad = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(bad.returncode, 2)
        self.assertEqual(bad.stdout, "")
        self.assertIn("CSV line 3", bad.stderr)
        missing_base = subprocess.run([sys.executable, str(SCRIPT), str(self.path)], capture_output=True, text=True)
        self.assertEqual(missing_base.returncode, 2)
        self.assertEqual(missing_base.stdout, "")


if __name__ == "__main__":
    unittest.main()
