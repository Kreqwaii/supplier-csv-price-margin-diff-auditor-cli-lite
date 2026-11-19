#!/usr/bin/env python3
"""Convenience runner for supplier-csv-price-margin-diff-auditor-cli-lite."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from margin_auditor.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
