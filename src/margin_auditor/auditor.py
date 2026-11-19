"""Core CSV loading and supplier price/margin diff auditing."""

import csv
from dataclasses import dataclass, asdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Dict, List, Optional

from .normalizer import parse_price
from .pricing import (
    apply_psychological_rounding,
    calculate_target_price,
    compute_margin_pct,
)


@dataclass
class SkuDiffRecord:
    sku: str
    name: str
    status: str  # ADDED, REMOVED, INCREASED, DECREASED, UNCHANGED
    old_cost: Optional[str]
    new_cost: Optional[str]
    cost_diff_pct: Optional[str]
    old_retail: Optional[str]
    suggested_retail: Optional[str]
    new_margin_pct: Optional[str]
    flags: List[str]

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def load_supplier_csv(
    path: Path,
    sku_col: str = "sku",
    cost_col: str = "cost",
    name_col: str = "name",
    retail_col: str = "retail",
    delimiter: str = ",",
) -> Dict[str, Dict[str, object]]:
    """Load a supplier CSV into a dict keyed by SKU."""
    records: Dict[str, Dict[str, object]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        if not reader.fieldnames or sku_col not in reader.fieldnames or cost_col not in reader.fieldnames:
            raise ValueError(
                f"CSV {path} must contain columns {sku_col!r} and {cost_col!r}. Found: {reader.fieldnames}"
            )
        for row in reader:
            sku = (row.get(sku_col) or "").strip()
            if not sku:
                continue
            cost = parse_price(row[cost_col])
            name = (row.get(name_col) or "").strip()
            retail_raw = (row.get(retail_col) or "").strip() if retail_col in reader.fieldnames else ""
            retail = parse_price(retail_raw) if retail_raw else None
            records[sku] = {
                "sku": sku,
                "name": name,
                "cost": cost,
                "retail": retail,
            }
    return records


def audit_price_lists(
    old_records: Dict[str, Dict[str, object]],
    new_records: Dict[str, Dict[str, object]],
    mode: str = "margin",
    target_pct: Decimal = Decimal("30"),
    min_margin_pct: Decimal = Decimal("15"),
    max_hike_pct: Decimal = Decimal("10"),
    rounding_rule: str = "none",
) -> Dict[str, object]:
    """Compare old vs new supplier price lists and return diff records + summary."""
    all_skus = sorted(set(old_records.keys()) | set(new_records.keys()))
    diffs: List[SkuDiffRecord] = []

    counts = {
        "total_skus": len(all_skus),
        "added": 0,
        "removed": 0,
        "increased": 0,
        "decreased": 0,
        "unchanged": 0,
        "hike_spikes": 0,
        "below_floor_margin": 0,
        "negative_margin": 0,
    }

    for sku in all_skus:
        old_item = old_records.get(sku)
        new_item = new_records.get(sku)
        flags: List[str] = []

        if old_item is None and new_item is not None:
            counts["added"] += 1
            new_cost: Decimal = new_item["cost"]  # type: ignore[assignment]
            raw_target = calculate_target_price(new_cost, mode=mode, target_pct=target_pct)
            suggested = apply_psychological_rounding(raw_target, rule=rounding_rule)
            margin_pct = compute_margin_pct(new_cost, suggested)
            if margin_pct < Decimal("0"):
                flags.append("NEGATIVE_MARGIN")
                counts["negative_margin"] += 1
            elif margin_pct < min_margin_pct:
                flags.append("BELOW_FLOOR_MARGIN")
                counts["below_floor_margin"] += 1

            diffs.append(
                SkuDiffRecord(
                    sku=sku,
                    name=str(new_item["name"]),
                    status="ADDED",
                    old_cost=None,
                    new_cost=f"{new_cost:.2f}",
                    cost_diff_pct=None,
                    old_retail=None,
                    suggested_retail=f"{suggested:.2f}",
                    new_margin_pct=f"{margin_pct:.2f}",
                    flags=flags,
                )
            )
            continue

        if new_item is None and old_item is not None:
            counts["removed"] += 1
            old_cost: Decimal = old_item["cost"]  # type: ignore[assignment]
            old_retail: Optional[Decimal] = old_item["retail"]  # type: ignore[assignment]
            diffs.append(
                SkuDiffRecord(
                    sku=sku,
                    name=str(old_item["name"]),
                    status="REMOVED",
                    old_cost=f"{old_cost:.2f}",
                    new_cost=None,
                    cost_diff_pct=None,
                    old_retail=f"{old_retail:.2f}" if old_retail is not None else None,
                    suggested_retail=None,
                    new_margin_pct=None,
                    flags=flags,
                )
            )
            continue

        assert old_item is not None and new_item is not None
        old_cost = old_item["cost"]  # type: ignore[assignment]
        new_cost = new_item["cost"]  # type: ignore[assignment]
        old_retail = old_item["retail"]  # type: ignore[assignment]

        if old_cost > Decimal("0"):
            diff_pct = (((new_cost - old_cost) / old_cost) * Decimal("100")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        else:
            diff_pct = Decimal("0.00")

        if new_cost > old_cost:
            status = "INCREASED"
            counts["increased"] += 1
            if diff_pct > max_hike_pct:
                flags.append("COST_SPIKE")
                counts["hike_spikes"] += 1
        elif new_cost < old_cost:
            status = "DECREASED"
            counts["decreased"] += 1
        else:
            status = "UNCHANGED"
            counts["unchanged"] += 1

        raw_target = calculate_target_price(new_cost, mode=mode, target_pct=target_pct)
        suggested = apply_psychological_rounding(raw_target, rule=rounding_rule)

        # If old_retail exists and is lower than new cost, check margin on old_retail too
        margin_pct = compute_margin_pct(new_cost, suggested)
        if old_retail is not None:
            existing_margin = compute_margin_pct(new_cost, old_retail)
            if existing_margin < Decimal("0"):
                flags.append("OLD_RETAIL_NEGATIVE_MARGIN")

        if margin_pct < Decimal("0"):
            flags.append("NEGATIVE_MARGIN")
            counts["negative_margin"] += 1
        elif margin_pct < min_margin_pct:
            flags.append("BELOW_FLOOR_MARGIN")
            counts["below_floor_margin"] += 1

        diffs.append(
            SkuDiffRecord(
                sku=sku,
                name=str(new_item["name"] or old_item["name"]),
                status=status,
                old_cost=f"{old_cost:.2f}",
                new_cost=f"{new_cost:.2f}",
                cost_diff_pct=f"{diff_pct:.2f}",
                old_retail=f"{old_retail:.2f}" if old_retail is not None else None,
                suggested_retail=f"{suggested:.2f}",
                new_margin_pct=f"{margin_pct:.2f}",
                flags=flags,
            )
        )

    has_violations = (
        counts["hike_spikes"] > 0
        or counts["below_floor_margin"] > 0
        or counts["negative_margin"] > 0
    )

    return {
        "summary": counts,
        "has_violations": has_violations,
        "diffs": [d.to_dict() for d in diffs],
    }
