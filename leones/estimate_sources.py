"""Discover and store unvalidated public estimates for LEONES web display.

One responsibility: maintain a small weekly input file and clearly mark every
entry as external/unvalidated. This is research material, not Atlas evidence.
It does not promote estimates into model facts or Router decisions.
"""

import argparse
import csv
from datetime import date
from pathlib import Path

FIELDS = ["date", "model", "hardware", "quantization", "metric", "estimate", "source", "status", "notes"]
STATUS = "external-unvalidated"


def append_estimate(path: Path, values: dict[str, str]) -> None:
    """Append one externally sourced estimate with an explicit status."""
    path.parent.mkdir(parents=True, exist_ok=True)
    new_file = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=FIELDS)
        if new_file:
            writer.writeheader()
        row = {field: values.get(field, "") for field in FIELDS}
        row["date"] = row["date"] or date.today().isoformat()
        row["status"] = STATUS
        writer.writerow(row)


def main() -> None:
    parser = argparse.ArgumentParser(description="Add an unvalidated external estimate.")
    parser.add_argument("--file", default="web/data/external_estimates.csv")
    for field in FIELDS[1:7]:
        parser.add_argument(f"--{field.replace('_', '-')}", default="")
    parser.add_argument("--notes", default="")
    args = parser.parse_args()
    values = vars(args)
    append_estimate(Path(args.file), values)


if __name__ == "__main__":
    main()
