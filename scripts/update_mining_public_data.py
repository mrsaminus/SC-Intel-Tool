"""Refresh the minimal public Mining / Salvage runtime data bundle.

This maintainer-only helper copies only approved public runtime files from a
local mining reference checkout into app/assets/mining_public. It intentionally
does not copy the full reference_material tree.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


APPROVED_FILES = (
    (
        Path("Calculator") / "rock-breaking-calculator-data.json",
        Path("Calculator") / "rock-breaking-calculator-data.json",
    ),
    (
        Path("defaults") / "equipment_shops_cache_default.json",
        Path("defaults") / "equipment_shops_cache_default.json",
    ),
    (
        Path("assets") / "Mineral Stats" / "Mineral_Where.txt",
        Path("assets") / "Mineral Stats" / "Mineral_Where.txt",
    ),
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    root = repo_root()
    parser = argparse.ArgumentParser(
        description=(
            "Copy only approved public Mining / Salvage runtime files into "
            "app/assets/mining_public."
        )
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        default=root / "reference_material" / "mining_warchest",
        help="Local mining reference root to copy from.",
    )
    parser.add_argument(
        "--target-root",
        type=Path,
        default=root / "app" / "assets" / "mining_public",
        help="Public runtime data bundle target.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate that approved source files exist without copying.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_root = args.source_root.resolve()
    target_root = args.target_root.resolve()

    missing = []
    for source_relative, _target_relative in APPROVED_FILES:
        source_path = source_root / source_relative
        if not source_path.exists():
            missing.append(source_path)

    if missing:
        print("Missing approved source files:")
        for path in missing:
            print(f"  {path}")
        return 1

    if args.check:
        print("All approved Mining / Salvage public source files are present.")
        return 0

    for source_relative, target_relative in APPROVED_FILES:
        source_path = source_root / source_relative
        target_path = target_root / target_relative
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)
        print(f"Updated {target_path.relative_to(repo_root())}")

    print("Mining / Salvage public runtime data refreshed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
