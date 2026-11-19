# supplier-csv-price-margin-diff-auditor-cli-lite

Zero-dependency Python 3.9+ CLI tool for e-commerce and wholesale teams to audit supplier CSV price list updates, detect sudden cost spikes, recalculate target retail prices with psychological rounding, and export clean Diff CSV, JSON, and Markdown reports.

## Features
- **100% Python 3.9+ stdlib only** (`csv`, `decimal`, `json`, `argparse`, `pathlib`, `unittest`).
- **Messy Price Normalization**: Handles `1 299,50`, `$45.90`, `€12,00`, `1,299.50`, and `1.299,50` cleanly using `Decimal`.
- **SKU Diffing**: Detects `ADDED`, `REMOVED`, `INCREASED`, `DECREASED`, and `UNCHANGED` SKUs.
- **Cost Spike & Margin Floor Alerts**: Flags `--max-hike-pct` spikes and `--min-margin-pct` / negative margin violations.
- **Pricing & Psychological Rounding**: Supports `margin` and `markup` modes with `.99`, `.90`, `nearest10`, or `none` rounding.
- **CI-Ready Exit Codes**: `0` = clean, `1` = policy violations detected, `2` = invalid input/config.

## Quickstart

```bash
py margin_auditor.py \
  --old examples/old_supplier.csv \
  --new examples/new_supplier.csv \
  --mode margin \
  --target-pct 30 \
  --min-margin-pct 15 \
  --max-hike-pct 10 \
  --round .99 \
  --out-csv out/diff.csv \
  --out-json out/summary.json \
  --out-md out/report.md
```

## Pricing Formulas

- **Margin mode** (`--mode margin`):
  $$\text{Target Retail} = \frac{\text{Cost}}{1 - \frac{\text{Target \%}}{100}}$$
- **Markup mode** (`--mode markup`):
  $$\text{Target Retail} = \text{Cost} \times \left(1 + \frac{\text{Target \%}}{100}\right)$$
- **Gross Margin %**:
  $$\text{Margin \%} = \frac{\text{Retail} - \text{Cost}}{\text{Retail}} \times 100$$

## Sample Diff Table

| SKU | Name | Status | Old Cost | New Cost | Diff % | Suggested Retail | Margin % | Flags |
|---|---|---|---:|---:|---:|---:|---:|---|
| SKU-1001 | Ergonomic Mouse | INCREASED | 18.50 | 19.00 | 2.70 | 27.99 | 32.12 | - |
| SKU-1002 | Mechanical Keyboard | INCREASED | 45.00 | 58.50 | 30.00 | 83.99 | 30.35 | COST_SPIKE |
| SKU-1003 | USB-C Hub 7-in-1 | DECREASED | 1299.50 | 1199.50 | -7.70 | 1713.99 | 30.02 | - |
| SKU-1004 | Webcam 1080p | UNCHANGED | 22.00 | 22.00 | 0.00 | 31.99 | 31.23 | - |
| SKU-1005 | Laptop Stand | REMOVED | 15.00 | - | - | - | - | - |
| SKU-1006 | Desk Mat XL | ADDED | - | 9.50 | - | 13.99 | 32.09 | - |

## Running Tests

```bash
py -m unittest discover -s tests -v
```

---

## Need Multi-Supplier Sync, Web Studio UI, Scheduled Auto-Imports & Telegram Price-Spike Alerts?

Upgrade to **Pro `CSV Price & Margin Sync Studio`** on our FunPay store:
👉 **https://funpay.com/users/20096179/**
