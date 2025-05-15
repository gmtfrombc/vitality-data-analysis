from __future__ import annotations

"""CLI wrapper for the gap-report helper.

Usage
-----
python -m scripts.generate_gap_report --condition obesity [--active-only] [--out /tmp/obesity_gap.csv]
"""

import argparse
from pathlib import Path


from app.utils.gap_report import get_condition_gap_report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Generate condition gap report (patients without diagnosis)"
    )
    parser.add_argument(
        "--condition",
        "-c",
        required=True,
        help="Condition term, e.g. 'obesity', 'prediabetes'",
    )
    parser.add_argument(
        "--active-only", "-a", action="store_true", help="Include only active patients"
    )
    parser.add_argument(
        "--out", "-o", help="Path to write CSV. Omit to print to stdout only."
    )

    args = parser.parse_args(argv)

    df = get_condition_gap_report(args.condition, active_only=args.active_only)

    if df.empty:
        print("No gaps detected – every patient already has the diagnosis coded.")
    else:
        print(df.to_string(index=False))

        if args.out:
            out_path = Path(args.out).expanduser().resolve()
            df.to_csv(out_path, index=False)
            print(f"\nCSV written to {out_path}\n")


if __name__ == "__main__":
    main()
