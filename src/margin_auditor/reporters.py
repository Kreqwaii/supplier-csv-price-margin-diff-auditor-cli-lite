"""Output reporters: Diff CSV, JSON summary, and Markdown report."""

import csv
import json
from pathlib import Path
from typing import Any, Dict, List


CSV_FIELDS = [
    "sku",
    "name",
    "status",
    "old_cost",
    "new_cost",
    "cost_diff_pct",
    "old_retail",
    "suggested_retail",
    "new_margin_pct",
    "flags",
]


def write_diff_csv(report: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    diffs: List[Dict[str, Any]] = report["diffs"]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in diffs:
            out = dict(row)
            out["flags"] = ";".join(row.get("flags") or [])
            writer.writerow(out)


def write_json_report(report: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)


def render_markdown_report(report: Dict[str, Any]) -> str:
    s = report["summary"]
    lines = [
        "# Supplier Price & Margin Diff Audit",
        "",
        "## Summary",
        f"- **Total SKUs:** {s['total_skus']}",
        f"- **Added:** {s['added']} | **Removed:** {s['removed']}",
        f"- **Increased:** {s['increased']} | **Decreased:** {s['decreased']} | **Unchanged:** {s['unchanged']}",
        f"- **Cost Spike Flags:** {s['hike_spikes']}",
        f"- **Below-Floor Margin:** {s['below_floor_margin']} | **Negative Margin:** {s['negative_margin']}",
        "",
        "## SKU Diffs",
        "",
        "| SKU | Name | Status | Old Cost | New Cost | Diff % | Suggested Retail | Margin % | Flags |",
        "|---|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for d in report["diffs"]:
        flags = ", ".join(d["flags"]) if d["flags"] else "-"
        lines.append(
            f"| {d['sku']} | {d['name']} | {d['status']} | "
            f"{d['old_cost'] or '-'} | {d['new_cost'] or '-'} | {d['cost_diff_pct'] or '-'} | "
            f"{d['suggested_retail'] or '-'} | {d['new_margin_pct'] or '-'} | {flags} |"
        )
    lines.append("")
    return "\n".join(lines)


def write_markdown_report(report: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_markdown_report(report), encoding="utf-8")
