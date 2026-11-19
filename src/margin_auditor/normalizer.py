"""Price string normalization to Decimal."""

from decimal import Decimal, InvalidOperation
import re

_CURRENCY_RE = re.compile(r"[^\d,.\-+]")


def parse_price(raw: str) -> Decimal:
    """Normalize messy supplier price strings into a Decimal.

    Handles:
    - Currency symbols & spaces: '$45.90', '€12,00', '1 299,50', '£ 1,299.50'
    - European comma decimals: '12,00', '1.299,50'
    - US dot decimals: '1,299.50', '45.90'
    """
    if raw is None:
        raise ValueError("Price value cannot be None")
    cleaned = raw.strip()
    if not cleaned:
        raise ValueError("Empty price string")

    # Remove currency symbols, whitespace, and non-numeric separators except . , + -
    cleaned = _CURRENCY_RE.sub("", cleaned)
    if not cleaned or cleaned in {"-", "+", ".", ","}:
        raise ValueError(f"Invalid price string: {raw!r}")

    has_comma = "," in cleaned
    has_dot = "." in cleaned

    if has_comma and has_dot:
        # Whichever appears last is the decimal separator
        if cleaned.rfind(",") > cleaned.rfind("."):
            # e.g. 1.299,50 -> 1299.50
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            # e.g. 1,299.50 -> 1299.50
            cleaned = cleaned.replace(",", "")
    elif has_comma:
        # e.g. 12,00 or 1 299,50 -> 12.00 / 1299.50
        # If multiple commas, treat all but last as thousand separators if last has <=2 digits
        parts = cleaned.split(",")
        if len(parts) > 2:
            cleaned = "".join(parts[:-1]) + "." + parts[-1]
        elif len(parts[1]) == 3 and len(parts[0].lstrip("-+")) >= 1 and len(parts[0].lstrip("-+")) <= 3:
            # Ambiguous like '1,200' -> treat as 1200 if 3 digits after comma
            cleaned = cleaned.replace(",", "")
        else:
            cleaned = cleaned.replace(",", ".")
    elif has_dot:
        parts = cleaned.split(".")
        if len(parts) > 2:
            cleaned = "".join(parts[:-1]) + "." + parts[-1]

    try:
        return Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError(f"Cannot parse price {raw!r} -> {cleaned!r}") from exc
