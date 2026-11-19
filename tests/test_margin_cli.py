"""Unit tests for supplier-csv-price-margin-diff-auditor-cli-lite."""

import csv
from decimal import Decimal
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from margin_auditor.auditor import audit_price_lists, load_supplier_csv
from margin_auditor.cli import main
from margin_auditor.normalizer import parse_price
from margin_auditor.pricing import (
    apply_psychological_rounding,
    calculate_target_price,
    compute_margin_pct,
)
from margin_auditor.reporters import (
    render_markdown_report,
    write_diff_csv,
    write_json_report,
)


class TestNormalizer(unittest.TestCase):
    def test_us_dollar_format(self):
        self.assertEqual(parse_price("$45.90"), Decimal("45.90"))

    def test_euro_comma_format(self):
        self.assertEqual(parse_price("€12,00"), Decimal("12.00"))

    def test_space_thousands_comma_decimal(self):
        self.assertEqual(parse_price("1 299,50"), Decimal("1299.50"))

    def test_us_thousands_dot_decimal(self):
        self.assertEqual(parse_price("1,299.50"), Decimal("1299.50"))

    def test_eu_dot_thousands_comma_decimal(self):
        self.assertEqual(parse_price("1.299,50"), Decimal("1299.50"))

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            parse_price("   ")

    def test_none_raises(self):
        with self.assertRaises(ValueError):
            parse_price(None)  # type: ignore[arg-type]

    def test_invalid_text_raises(self):
        with self.assertRaises(ValueError):
            parse_price("N/A")


class TestPricing(unittest.TestCase):
    def test_margin_mode(self):
        self.assertEqual(
            calculate_target_price(Decimal("70.00"), mode="margin", target_pct=Decimal("30")),
            Decimal("100.00"),
        )

    def test_markup_mode(self):
        self.assertEqual(
            calculate_target_price(Decimal("50.00"), mode="markup", target_pct=Decimal("40")),
            Decimal("70.00"),
        )

    def test_invalid_margin_100_raises(self):
        with self.assertRaises(ValueError):
            calculate_target_price(Decimal("10.00"), mode="margin", target_pct=Decimal("100"))

    def test_negative_cost_raises(self):
        with self.assertRaises(ValueError):
            calculate_target_price(Decimal("-5.00"))

    def test_rounding_99_up(self):
        self.assertEqual(apply_psychological_rounding(Decimal("14.12"), ".99"), Decimal("14.99"))

    def test_rounding_90_rollover(self):
        self.assertEqual(apply_psychological_rounding(Decimal("14.95"), ".90"), Decimal("15.90"))

    def test_rounding_nearest10(self):
        self.assertEqual(apply_psychological_rounding(Decimal("46.20"), "nearest10"), Decimal("50.00"))
        self.assertEqual(apply_psychological_rounding(Decimal("44.20"), "nearest10"), Decimal("40.00"))

    def test_compute_margin_pct(self):
        self.assertEqual(compute_margin_pct(Decimal("70.00"), Decimal("100.00")), Decimal("30.00"))

    def test_compute_margin_pct_zero_retail(self):
        self.assertEqual(compute_margin_pct(Decimal("10.00"), Decimal("0.00")), Decimal("-100.00"))

    def test_rounding_none(self):
        self.assertEqual(apply_psychological_rounding(Decimal("14.126"), "none"), Decimal("14.13"))

    def test_unsupported_mode_raises(self):
        with self.assertRaises(ValueError):
            calculate_target_price(Decimal("10.00"), mode="invalid")

    def test_unsupported_rounding_raises(self):
        with self.assertRaises(ValueError):
            apply_psychological_rounding(Decimal("10.00"), rule="invalid")


class TestAuditorAndReporters(unittest.TestCase):
    def test_audit_detects_all_statuses_and_spike(self):
        old_rec = {
            "A": {"sku": "A", "name": "Item A", "cost": Decimal("10.00"), "retail": Decimal("15.00")},
            "B": {"sku": "B", "name": "Item B", "cost": Decimal("20.00"), "retail": Decimal("30.00")},
            "C": {"sku": "C", "name": "Item C", "cost": Decimal("30.00"), "retail": Decimal("45.00")},
        }
        new_rec = {
            "A": {"sku": "A", "name": "Item A", "cost": Decimal("15.00"), "retail": Decimal("15.00")},
            "B": {"sku": "B", "name": "Item B", "cost": Decimal("18.00"), "retail": Decimal("30.00")},
            "D": {"sku": "D", "name": "Item D", "cost": Decimal("12.00"), "retail": None},
        }
        report = audit_price_lists(old_rec, new_rec, max_hike_pct=Decimal("10"))
        s = report["summary"]
        self.assertEqual(s["added"], 1)
        self.assertEqual(s["removed"], 1)
        self.assertEqual(s["increased"], 1)
        self.assertEqual(s["decreased"], 1)
        self.assertEqual(s["hike_spikes"], 1)
        self.assertTrue(report["has_violations"])

    def test_below_floor_margin_flag(self):
        old_rec = {"A": {"sku": "A", "name": "Item A", "cost": Decimal("10.00"), "retail": None}}
        new_rec = {"A": {"sku": "A", "name": "Item A", "cost": Decimal("10.00"), "retail": None}}
        report = audit_price_lists(
            old_rec,
            new_rec,
            mode="markup",
            target_pct=Decimal("5"),
            min_margin_pct=Decimal("15"),
        )
        self.assertEqual(report["summary"]["below_floor_margin"], 1)
        self.assertTrue(report["has_violations"])

    def test_write_csv_json_and_markdown(self):
        old_rec = {"A": {"sku": "A", "name": "Item A", "cost": Decimal("10.00"), "retail": None}}
        new_rec = {"A": {"sku": "A", "name": "Item A", "cost": Decimal("10.00"), "retail": None}}
        report = audit_price_lists(old_rec, new_rec)
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            csv_path = tmp_path / "diff.csv"
            json_path = tmp_path / "summary.json"
            write_diff_csv(report, csv_path)
            write_json_report(report, json_path)

            with csv_path.open("r", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["sku"], "A")

            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(loaded["summary"]["unchanged"], 1)

            md = render_markdown_report(report)
            self.assertIn("# Supplier Price & Margin Diff Audit", md)


class TestCLI(unittest.TestCase):
    def test_cli_examples_returns_1_on_spike(self):
        root = Path(__file__).resolve().parent.parent
        with tempfile.TemporaryDirectory() as tmp:
            out_csv = Path(tmp) / "diff.csv"
            code = main([
                "--old", str(root / "examples" / "old_supplier.csv"),
                "--new", str(root / "examples" / "new_supplier.csv"),
                "--round", ".99",
                "--out-csv", str(out_csv),
            ])
            self.assertEqual(code, 1)
            self.assertTrue(out_csv.exists())

    def test_cli_clean_returns_0(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            old_csv = p / "old.csv"
            new_csv = p / "new.csv"
            old_csv.write_text("sku,name,cost\nS1,Widget,10.00\n", encoding="utf-8")
            new_csv.write_text("sku,name,cost\nS1,Widget,10.50\n", encoding="utf-8")
            code = main(["--old", str(old_csv), "--new", str(new_csv), "--max-hike-pct", "10"])
            self.assertEqual(code, 0)

    def test_cli_missing_file_returns_2(self):
        code = main(["--old", "nonexistent_old.csv", "--new", "nonexistent_new.csv"])
        self.assertEqual(code, 2)

    def test_load_supplier_csv_missing_columns_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.csv"
            bad.write_text("id,price\n1,10.00\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_supplier_csv(bad)


if __name__ == "__main__":
    unittest.main()
