"""Create a synthetic patient database for interactive exploration.

Run:
    python scripts/create_mock_db.py --path mock_patient_data.db

The script re-uses the ``SyntheticDataGenerator`` class that powers the
``SyntheticSelfTestLoop`` so clinicians get the exact same deterministic
dataset that the automated tests rely on.

After the DB is created, launch the Panel app (or any CLI query) with:

    export MH_DB_PATH=mock_patient_data.db
    python run.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
import sqlite3
import logging

# ---------------------------------------------------------------------------
# Ensure project root is on ``sys.path`` so we can import tests.golden.*
# ---------------------------------------------------------------------------

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# SyntheticDataGenerator lives inside the test package.  Importing from tests is
# acceptable for developer tooling – the generator has no testing-only
# side-effects.
try:
    from tests.golden.synthetic_self_test import SyntheticDataGenerator  # type: ignore
except ModuleNotFoundError as exc:  # pragma: no cover
    print(
        "Unable to import SyntheticDataGenerator – ensure you are running from the repository root."
    )
    raise SystemExit(1) from exc

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("create_mock_db")


def _parse_args(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description="Create a deterministic synthetic SQLite DB for the Metabolic Health app."
    )
    parser.add_argument(
        "--path",
        "-p",
        default="mock_patient_data.db",
        help="Destination path for the new SQLite file (default: %(default)s)",
    )
    parser.add_argument(
        "--overwrite",
        "-f",
        action="store_true",
        help="Overwrite existing file if it already exists.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None):  # noqa: D401 – entrypoint helper
    args = _parse_args(argv)
    db_path = Path(args.path).expanduser().resolve()

    if db_path.exists() and not args.overwrite:
        logger.error("%s already exists – use --overwrite to replace it", db_path)
        sys.exit(1)

    # Remove existing file if user asked for overwrite
    if db_path.exists():
        db_path.unlink()

    # ------------------------------------------------------------------
    # Build database
    # ------------------------------------------------------------------
    generator = SyntheticDataGenerator(str(db_path))
    generator.create_database()
    generator.generate_synthetic_data()

    # Quick sanity check
    conn = sqlite3.connect(db_path)
    tables = [
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table';"
        ).fetchall()
    ]
    conn.close()

    logger.info(
        "Synthetic database created at %s with tables: %s", db_path, ", ".join(tables)
    )
    logger.info("Set MH_DB_PATH=%s before launching the app to use this DB.", db_path)


if __name__ == "__main__":  # pragma: no cover – scripting
    main()
