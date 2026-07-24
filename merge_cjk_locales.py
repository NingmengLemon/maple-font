#!/usr/bin/env python3
"""
Merge multiple locale NF-CJK font files into a single all-inclusive font file.

Glyphs from higher-priority locales are preserved when codepoint conflicts occur
across locales (e.g. CN glyphs override JP glyphs for the same codepoint).

Prerequisites:
    uv run build.py --cjk cn,jp,tc,kr --format ttf

Usage:
    uv run python merge_cjk_locales.py
    uv run python merge_cjk_locales.py --locales CN,JP,TC,KR
    uv run python merge_cjk_locales.py --locales CN,JP --output-suffix SuperCJK
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

# --- Internal imports (require running from the project root) ---
from scripts.config.resolver import resolve_default_build_config
from scripts.font_ops.fonttools import TTFont
from scripts.font_ops.merge import merge_ttfonts
from scripts.font_ops.names import parse_style_name, update_font_names
from scripts.utils.logging import configure_logging, logger

# All 16 weight-style combinations produced by a full build.
ALL_STYLES: tuple[str, ...] = (
    "Thin",
    "ThinItalic",
    "ExtraLight",
    "ExtraLightItalic",
    "Light",
    "LightItalic",
    "Regular",
    "Italic",
    "Medium",
    "MediumItalic",
    "SemiBold",
    "SemiBoldItalic",
    "Bold",
    "BoldItalic",
    "ExtraBold",
    "ExtraBoldItalic",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Merge NF-CJK locale fonts into one all-inclusive font file",
    )
    parser.add_argument(
        "--locales",
        type=str,
        default="CN,JP,TC,KR",
        help=(
            "Comma-separated locale list in **priority order**. "
            "The first locale has the highest priority; its glyphs survive "
            "codepoint conflicts. Default: CN,JP,TC,KR"
        ),
    )
    parser.add_argument(
        "--base-dir",
        type=str,
        default="fonts",
        help="Root output directory containing NF-{LOCALE} subdirectories. Default: fonts",
    )
    parser.add_argument(
        "--output-suffix",
        type=str,
        default="AllCJK",
        help="Suffix used in the output directory and font family name. Default: AllCJK",
    )
    parser.add_argument(
        "--styles",
        type=str,
        default=None,
        help=(
            "Comma-separated styles to merge (e.g. Regular,Bold). "
            "Default: all 16 styles"
        ),
    )
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help=(
            "Continue when a requested locale/style input is missing. "
            "Without this flag, missing inputs fail the merge to avoid "
            "mislabeling an incomplete output as AllCJK."
        ),
    )
    parser.add_argument(
        "--dry",
        action="store_true",
        help="Print what would be merged without writing output files",
    )
    return parser


def resolve_font_path(base_dir: Path, locale: str, style: str) -> Path:
    """Resolve the path to a pre-built NF-CJK font file.

    Expected naming: ``fonts/NF-{LOCALE}/MapleMono-NF-{LOCALE}-{Style}.ttf``
    """
    nf_dir = base_dir / f"NF-{locale.upper()}"
    return nf_dir / f"MapleMono-NF-{locale.upper()}-{style}.ttf"


def merge_chain(
    base_path: Path,
    extra_paths: list[Path],
    output_path: Path,
) -> None:
    """Merge *extra_paths* into *base_path* in order, writing *output_path*.

    ``merge_ttfonts`` keeps glyphs already present in the base font, so the
    first locale's glyphs take precedence. Intermediate files are removed even
    if a merge or save operation fails.
    """
    current = str(base_path)
    temp_files: list[Path] = []

    try:
        for index, extra_path in enumerate(extra_paths):
            logger.debug(
                "  merge: base=%s  extra=%s",
                Path(current).name,
                extra_path.name,
            )
            merged = merge_ttfonts(current, str(extra_path))
            try:
                if index == len(extra_paths) - 1:
                    merged.save(output_path)
                    logger.info(
                        "  → %s  (%d glyphs)",
                        output_path.name,
                        merged["maxp"].numGlyphs,
                    )
                else:
                    temp = output_path.parent / f".merge_tmp_{index}_{output_path.name}"
                    merged.save(temp)
                    temp_files.append(temp)
                    current = str(temp)
            finally:
                merged.close()
    finally:
        for temp in temp_files:
            temp.unlink(missing_ok=True)


def update_names(
    font: TTFont,
    output_suffix: str,
    style: str,
) -> None:
    """Rewrite font naming tables to reflect the merged CJK family."""
    font_config = resolve_default_build_config()

    # Derive the Nerd Font symbol (e.g. "NF", "NFM", "NFP") from the config.
    nf_symbol = font_config.get_nf_variant().symbol  # "NF" for default
    family_name = f"{font_config.family_name} {nf_symbol} {output_suffix}"
    postscript_prefix = f"{font_config.family_name_compact}-{nf_symbol}-{output_suffix}"

    style_prefix, style_2, style_17, is_skip_subfamily, _is_italic = parse_style_name(
        style_name_compact=style
    )
    postscript_name = f"{postscript_prefix}-{style}"

    update_font_names(
        font=font,
        font_config=font_config,
        family_name=f"{family_name}{style_prefix}",
        style_name=style_2,
        full_name=f"{family_name} {style_17}",
        postscript_name=postscript_name,
        is_skip_subfamily=is_skip_subfamily,
        preferred_family_name=family_name,
        preferred_style_name=style_17,
    )


def main() -> None:
    configure_logging()
    args = build_parser().parse_args()

    locales = [loc.strip().upper() for loc in args.locales.split(",") if loc.strip()]
    if len(locales) < 2:
        logger.error("Need at least 2 locales to merge (got %d)", len(locales))
        sys.exit(1)
    if len(locales) != len(set(locales)):
        logger.error("Locales must be unique: %s", ", ".join(locales))
        sys.exit(1)

    styles = (
        [style.strip() for style in args.styles.split(",") if style.strip()]
        if args.styles
        else list(ALL_STYLES)
    )
    invalid_styles = sorted(set(styles).difference(ALL_STYLES))
    if invalid_styles:
        logger.error("Unsupported styles: %s", ", ".join(invalid_styles))
        sys.exit(1)

    base_dir = Path(args.base_dir)
    output_suffix = args.output_suffix
    output_dir = base_dir / f"NF-{output_suffix}"

    # ------------------------------------------------------------------
    # Dry-run: report what would happen and exit.
    # ------------------------------------------------------------------
    if args.dry:
        print(f"Locales (priority): {' > '.join(locales)}")
        print(f"Styles: {', '.join(styles)}")
        print(f"Output: {output_dir}/")
        for style in styles:
            inputs = [resolve_font_path(base_dir, locale, style) for locale in locales]
            missing = [path for path in inputs if not path.exists()]
            if missing:
                for path in missing:
                    print(f"  [{style}] ✗ MISSING: {path}")
                if not args.allow_missing:
                    continue
            present = [path for path in inputs if path.exists()]
            if not present:
                print(f"  [{style}] ✗ no usable locale input")
                continue
            output_name = f"MapleMono-NF-{output_suffix}-{style}.ttf"
            print(
                f"  [{style}] base={present[0].name} + {len(present) - 1} extras → {output_name}"
            )
        return

    # ------------------------------------------------------------------
    # Merge
    # ------------------------------------------------------------------
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(
        "Merging %d locales (%s) into %s",
        len(locales),
        " > ".join(locales),
        output_dir,
    )

    for style in styles:
        input_paths = [resolve_font_path(base_dir, locale, style) for locale in locales]
        missing_paths = [path for path in input_paths if not path.exists()]
        if missing_paths and not args.allow_missing:
            missing_text = ", ".join(str(path) for path in missing_paths)
            logger.error(
                "[%s] Refusing incomplete merge; missing: %s", style, missing_text
            )
            sys.exit(1)

        available_paths = [path for path in input_paths if path.exists()]
        if not available_paths:
            logger.error("[%s] No usable locale input", style)
            sys.exit(1)
        if missing_paths:
            logger.warning(
                "[%s] Proceeding with --allow-missing; missing: %s",
                style,
                ", ".join(str(path) for path in missing_paths),
            )

        base_path, *extra_paths = available_paths
        output_path = output_dir / f"MapleMono-NF-{output_suffix}-{style}.ttf"

        if not extra_paths:
            logger.info("[%s] No extras – copying base verbatim", style)
            shutil.copy2(base_path, output_path)
        else:
            logger.info(
                "[%s] Merging: base=%s + %d extra(s)",
                style,
                base_path.name,
                len(extra_paths),
            )
            merge_chain(base_path, extra_paths, output_path)

        # Rewrite family / postscript names to the merged identity.
        font = TTFont(output_path, recalcTimestamp=False)
        try:
            update_names(font, output_suffix, style)
            font.save(output_path)
        finally:
            font.close()

    logger.info("Done – merged fonts saved to %s", output_dir.resolve())


if __name__ == "__main__":
    main()
