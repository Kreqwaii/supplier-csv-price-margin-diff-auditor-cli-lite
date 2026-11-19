"""Margin, markup, and psychological rounding calculations."""

from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP


def calculate_target_price(
    cost: Decimal,
    mode: str = "margin",
    target_pct: Decimal = Decimal("30"),
) -> Decimal:
    """Calculate target retail price from cost.

    - margin mode: price = cost / (1 - target_pct / 100)
    - markup mode: price = cost * (1 + target_pct / 100)
    """
    if cost < Decimal("0"):
        raise ValueError("Cost cannot be negative")
    if mode == "margin":
        if target_pct >= Decimal("100"):
            raise ValueError("Target margin percentage must be < 100")
        denom = Decimal("1") - (target_pct / Decimal("100"))
        return (cost / denom).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if mode == "markup":
        factor = Decimal("1") + (target_pct / Decimal("100"))
        return (cost * factor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    raise ValueError(f"Unsupported pricing mode: {mode!r}")


def apply_psychological_rounding(price: Decimal, rule: str = "none") -> Decimal:
    """Apply psychological rounding to a price.

    Rules:
    - 'none': keep 2 decimal places
    - '.99': round up to nearest .99 (e.g. 14.12 -> 14.99)
    - '.90': round up to nearest .90 (e.g. 14.12 -> 14.90, 14.95 -> 15.90)
    - 'nearest10': round to nearest multiple of 10 (e.g. 44 -> 40.00, 46 -> 50.00)
    """
    if rule == "none":
        return price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if rule == ".99":
        whole = int(price)
        candidate = Decimal(f"{whole}.99")
        if candidate < price:
            candidate = Decimal(f"{whole + 1}.99")
        return candidate
    if rule == ".90":
        whole = int(price)
        candidate = Decimal(f"{whole}.90")
        if candidate < price:
            candidate = Decimal(f"{whole + 1}.90")
        return candidate
    if rule == "nearest10":
        tens = (price / Decimal("10")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        return (tens * Decimal("10")).quantize(Decimal("0.01"))
    raise ValueError(f"Unsupported rounding rule: {rule!r}")


def compute_margin_pct(cost: Decimal, retail: Decimal) -> Decimal:
    """Compute gross margin percentage: ((retail - cost) / retail) * 100."""
    if retail <= Decimal("0"):
        return Decimal("-100.00")
    margin = ((retail - cost) / retail) * Decimal("100")
    return margin.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
