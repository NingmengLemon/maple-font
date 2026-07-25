#!/usr/bin/env python3
"""Audit vertical metrics and glyph bounds for candidate mobile font builds."""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTCollection

from scripts.font_ops.fonttools import TTFont, adapt_ttfont


@dataclass(frozen=True)
class VerticalMetrics:
    file: str
    face_index: int | None
    units_per_em: int
    hhea_ascent: int
    hhea_descent: int
    typo_ascender: int
    typo_descender: int
    typo_line_gap: int
    win_ascent: int
    win_descent: int
    head_y_max: int
    head_y_min: int
    glyph_y_max: float | None
    glyph_y_min: float | None
    glyphs_above_hhea: int
    glyphs_below_hhea: int


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Report declared vertical metrics and actual glyph bounds."
    )
    parser.add_argument("font", nargs="+", type=Path, help="TTF or TTC font file.")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write the JSON report to this path instead of stdout.",
    )
    return parser


def iter_fonts(path: Path) -> Iterable[tuple[TTFont, int | None]]:
    if path.suffix.lower() == ".ttc":
        collection = TTCollection(path, lazy=True)
        try:
            for index, font in enumerate(collection.fonts):
                yield adapt_ttfont(font), index
        finally:
            collection.close()
        return

    font = TTFont(path, lazy=True)
    try:
        yield font, None
    finally:
        font.close()


def audit_font(font: TTFont, path: Path, face_index: int | None) -> VerticalMetrics:
    glyph_set = font.getGlyphSet()
    glyph_y_min: float | None = None
    glyph_y_max: float | None = None
    glyphs_above_hhea = 0
    glyphs_below_hhea = 0
    hhea = font.table("hhea")

    for glyph in glyph_set.values():
        pen = BoundsPen(glyph_set)
        glyph.draw(pen)
        if pen.bounds is None:
            continue
        _, y_min, _, y_max = pen.bounds
        glyph_y_min = y_min if glyph_y_min is None else min(glyph_y_min, y_min)
        glyph_y_max = y_max if glyph_y_max is None else max(glyph_y_max, y_max)
        glyphs_above_hhea += y_max > hhea.ascent
        glyphs_below_hhea += y_min < hhea.descent

    os2 = font.table("OS/2")
    head = font.table("head")
    return VerticalMetrics(
        file=str(path),
        face_index=face_index,
        units_per_em=head.unitsPerEm,
        hhea_ascent=hhea.ascent,
        hhea_descent=hhea.descent,
        typo_ascender=os2.sTypoAscender,
        typo_descender=os2.sTypoDescender,
        typo_line_gap=os2.sTypoLineGap,
        win_ascent=os2.usWinAscent,
        win_descent=os2.usWinDescent,
        head_y_max=head.yMax,
        head_y_min=head.yMin,
        glyph_y_max=glyph_y_max,
        glyph_y_min=glyph_y_min,
        glyphs_above_hhea=glyphs_above_hhea,
        glyphs_below_hhea=glyphs_below_hhea,
    )


def main() -> None:
    args = build_parser().parse_args()
    reports = [
        asdict(audit_font(font, path, face_index))
        for path in args.font
        for font, face_index in iter_fonts(path)
    ]
    report = json.dumps(reports, ensure_ascii=False, indent=2)
    if args.output is None:
        print(report)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(f"{report}\n", encoding="utf-8")


if __name__ == "__main__":
    main()
