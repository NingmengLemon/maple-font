#!/usr/bin/env python3
"""Report supplementary-plane CJK coverage in source and built fonts.

This audit is intentionally read-only. It helps decide whether a source-font
upgrade can provide Extension G through J before changing the build profile or
creating another system module.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fontTools.ttLib import TTFont


ROOT = Path(__file__).resolve().parent.parent
LOCALES = ("CN", "JP", "TC", "KR")
EXTENSION_RANGES = {
    "ExtG": (0x30000, 0x3134F),
    "ExtH": (0x31350, 0x323AF),
    "ExtI": (0x2EBF0, 0x2EE5F),
    "ExtJ": (0x323B0, 0x3347F),
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Report CJK Extension G-J cmap coverage without modifying fonts."
    )
    parser.add_argument(
        "--include-built",
        action="store_true",
        help="Also inspect fonts/NF-{locale} and fonts/NF-AllCJK when present.",
    )
    return parser


def count_ranges(font_path: Path) -> dict[str, int]:
    font = TTFont(font_path, lazy=True)
    try:
        cmap = font.getBestCmap() or {}
        return {
            name: sum(start <= codepoint <= end for codepoint in cmap)
            for name, (start, end) in EXTENSION_RANGES.items()
        }
    finally:
        font.close()


def source_path(locale: str) -> Path:
    config_path = ROOT / "source" / "cjk" / locale.lower() / f"config-{locale.lower()}.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    return (config_path.parent / config["source"]["path"]).resolve()


def print_counts(label: str, font_path: Path) -> None:
    counts = count_ranges(font_path)
    coverage = " ".join(f"{name}={count}" for name, count in counts.items())
    print(f"{label}: {font_path}\n  {coverage}")


def main() -> None:
    args = build_parser().parse_args()

    print("Source-font coverage")
    for locale in LOCALES:
        path = source_path(locale)
        print_counts(locale, path)

    if not args.include_built:
        return

    print("\nBuilt-font coverage")
    for locale in LOCALES:
        path = ROOT / "fonts" / f"NF-{locale}" / f"MapleMono-NF-{locale}-Regular.ttf"
        if path.is_file():
            print_counts(locale, path)
    merged_path = ROOT / "fonts" / "NF-AllCJK" / "MapleMono-NF-AllCJK-Regular.ttf"
    if merged_path.is_file():
        print_counts("AllCJK", merged_path)


if __name__ == "__main__":
    main()
