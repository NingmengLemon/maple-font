#!/usr/bin/env python3
"""Create isolated mobile-metric test copies of merged AllCJK fonts."""

from __future__ import annotations

import argparse
import shutil
from dataclasses import dataclass
from pathlib import Path

from scripts.font_ops.fonttools import TTFont, save_font_atomic


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE_DIR = PROJECT_ROOT / "fonts" / "NF-AllCJK"


@dataclass(frozen=True)
class VerticalMetricTarget:
    ascent: int
    descent: int
    line_gap: int
    head_y_max: int | None
    head_y_min: int | None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Copy and patch only the declared vertical metrics of AllCJK TTFs."
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=DEFAULT_SOURCE_DIR,
        help="Directory containing the verified merged AllCJK TTFs.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="New experiment directory; source fonts are never modified.",
    )
    parser.add_argument("--ascent", type=int, required=True)
    parser.add_argument("--descent", type=int, required=True)
    parser.add_argument("--line-gap", type=int, default=0)
    parser.add_argument(
        "--head-y-max",
        type=int,
        default=None,
        help="Optional experimental head.yMax override; defaults to retaining real bounds.",
    )
    parser.add_argument(
        "--head-y-min",
        type=int,
        default=None,
        help="Optional experimental head.yMin override; defaults to retaining real bounds.",
    )
    return parser


def validate_target(target: VerticalMetricTarget) -> None:
    if target.ascent <= target.descent:
        raise ValueError("Ascender must be greater than descender.")
    if target.line_gap < 0:
        raise ValueError("Line gap cannot be negative.")
    if (target.head_y_max is None) != (target.head_y_min is None):
        raise ValueError("head.yMax and head.yMin must be provided together.")
    if (
        target.head_y_max is not None
        and target.head_y_min is not None
        and target.head_y_max <= target.head_y_min
    ):
        raise ValueError("head.yMax must be greater than head.yMin.")


def patch_vertical_metrics(font: TTFont, target: VerticalMetricTarget) -> None:
    hhea = font.table("hhea")
    hhea.ascent = target.ascent
    hhea.descent = target.descent
    hhea.lineGap = target.line_gap

    os2 = font.table("OS/2")
    os2.sTypoAscender = target.ascent
    os2.sTypoDescender = target.descent
    os2.sTypoLineGap = target.line_gap
    os2.usWinAscent = target.ascent
    os2.usWinDescent = -target.descent

    if target.head_y_max is not None and target.head_y_min is not None:
        head = font.table("head")
        head.yMax = target.head_y_max
        head.yMin = target.head_y_min


def patch_fonts(
    source_dir: Path,
    output_dir: Path,
    target: VerticalMetricTarget,
) -> list[Path]:
    if source_dir.resolve() == output_dir.resolve():
        raise ValueError("Output directory must differ from source directory.")
    source_fonts = sorted(source_dir.glob("MapleMono-NF-AllCJK-*.ttf"))
    if not source_fonts:
        raise FileNotFoundError(f"No merged AllCJK TTFs found in {source_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)
    expected_names = {font_path.name for font_path in source_fonts}
    for stale_font in output_dir.glob("*.ttf"):
        if stale_font.name not in expected_names:
            stale_font.unlink()

    patched_paths = []
    for source_path in source_fonts:
        output_path = output_dir / source_path.name
        shutil.copy2(source_path, output_path)
        font = TTFont(output_path, recalcTimestamp=False)
        try:
            patch_vertical_metrics(font, target)
            save_font_atomic(font, output_path)
        finally:
            font.close()
        patched_paths.append(output_path)
    return patched_paths


def main() -> None:
    args = build_parser().parse_args()
    target = VerticalMetricTarget(
        args.ascent,
        args.descent,
        args.line_gap,
        args.head_y_max,
        args.head_y_min,
    )
    validate_target(target)
    patched_paths = patch_fonts(args.source_dir, args.output_dir, target)
    print(
        f"Patched {len(patched_paths)} fonts in {args.output_dir}: "
        f"hhea/Typo/Win=({target.ascent}, {target.descent}, {target.line_gap}), "
        f"head=({target.head_y_max}, {target.head_y_min})"
    )


if __name__ == "__main__":
    main()
