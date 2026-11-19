"""CLI entrypoint for supplier-csv-price-margin-diff-auditor-cli-lite."""

import argparse
from decimal import Decimal
from pathlib import Path
import sys
from typing import List, Optional

from .auditor import audit_price_lists, load_supplier_csv
from .reporters import (
    render_markdown_report,
    write_diff_csv,
    write_json_report,
    write_markdown_report,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="margin-auditor",
        description="Audit supplier CSV price list diffs, cost spikes, and target retail margins.",
    )
    parser.add_argument("--old", required=True, type=Path, help="Path to old supplier CSV")
    parser.add_argument("--new", required=True, type=Path, help="Path to new supplier CSV")
    parser.add_argument("--sku-col", default="sku", help="SKU column name (default: sku)")
    parser.add_argument("--cost-col", default="cost", help="Cost column name (default: cost)")
    parser.add_argument("--name-col", default="name", help="Product name column name (default: name)")
    parser.add_argument("--retail-col", default="retail", help="Existing retail column name (default: retail)")
    parser.add_argument("--delimiter", default=",", help="CSV delimiter (default: ,)")
    parser.add_argument(
        "--mode",
        choices=["margin", "markup"],
        default="margin",
        help="Pricing formula mode (default: margin)",
    )
    parser.add_argument("--target-pct", default="30", help="Target margin/markup %% (default: 30)")
    parser.add_argument("--min-margin-pct", default="15", help="Minimum allowed margin %% (default: 15)")
    parser.add_argument("--max-hike-pct", default="10", help="Flag cost increases above %% (default: 10)")
    parser.add_argument(
        "--round",
        dest="rounding_rule",
        choices=["none", ".99", ".90", "nearest10"],
        default="none",
        help="Psychological rounding rule (default: none)",
    )
    parser.add_argument("--out-csv", type=Path, help="Output diff CSV path")
    parser.add_argument("--out-json", type=Path, help="Output JSON summary path")
    parser.add_argument("--out-md", type=Path, help="Output Markdown report path")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        old_records = load_supplier_csv(
            args.old,
            sku_col=args.sku_col,
            cost_col=args.cost_col,
            name_col=args.name_col,
            retail_col=args.retail_col,
            delimiter=args.delimiter,
        )
        new_records = load_supplier_csv(
            args.new,
            sku_col=args.sku_col,
            cost_col=args.cost_col,
            name_col=args.name_col,
            retail_col=args.retail_col,
            delimiter=args.delimiter,
        )
        report = audit_price_lists(
            old_records=old_records,
            new_records=new_records,
            mode=args.mode,
            target_pct=Decimal(args.target_pct),
            min_margin_pct=Decimal(args.min_margin_pct),
            max_hike_pct=Decimal(args.max_hike_pct),
            rounding_rule=args.rounding_rule,
        )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    if args.out_csv:
        write_diff_csv(report, args.out_csv)
    if args.out_json:
        write_json_report(report, args.out_json)
    if args.out_md:
        write_markdown_report(report, args.out_md)

    if not (args.out_csv or args.out_json or args.out_md):
        print(render_markdown_report(report))

    return 1 if report["has_violations"] else 0


if __name__ == "__main__":
    sys.exit(main())
