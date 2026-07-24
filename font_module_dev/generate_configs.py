#!/usr/bin/env python3
"""Generate device-specific system font XML overlays from pulled OxygenOS samples.

The generator intentionally changes only the named UI families and the four CJK
fallback families. Every other family remains byte-for-byte semantically aligned
with the pulled device configuration.
"""

from __future__ import annotations

import argparse
import xml.etree.ElementTree as ElementTree
from collections.abc import Iterable
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SAMPLES_DIR = ROOT / "samples"
MODULE_DIR = ROOT / "module"
FONT_PREFIX = "MapleMono-NF-AllCJK"
DEFAULT_CONFIG_FILENAMES = (
    "font_fallback.xml",
    "fonts.xml",
    "fonts_base.xml",
    "fonts_ule.xml",
)

STYLE_WEIGHTS: tuple[tuple[str, str, int], ...] = (
    ("Thin", "ThinItalic", 100),
    ("ExtraLight", "ExtraLightItalic", 200),
    ("Light", "LightItalic", 300),
    ("Regular", "Italic", 400),
    ("Medium", "MediumItalic", 500),
    ("SemiBold", "SemiBoldItalic", 600),
    ("Bold", "BoldItalic", 700),
    ("ExtraBold", "ExtraBoldItalic", 800),
    ("ExtraBold", "ExtraBoldItalic", 900),
)

CJK_LANGS = frozenset({"zh-Hans", "zh-Hant,zh-Bopo", "ja", "ko"})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate Maple font configuration overlays from pulled XML samples."
    )
    parser.add_argument(
        "--samples-dir",
        type=Path,
        default=SAMPLES_DIR,
        help="Directory containing pulled font XML samples.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=MODULE_DIR,
        help="Module root directory for generated system XML overlays.",
    )
    parser.add_argument(
        "--configs",
        type=str,
        default=",".join(DEFAULT_CONFIG_FILENAMES),
        help="Comma-separated pulled configuration files to rewrite.",
    )
    return parser


def maple_filename(style: str) -> str:
    return f"{FONT_PREFIX}-{style}.ttf"


def make_font(weight: int, style: str, filename_style: str) -> ElementTree.Element:
    font = ElementTree.Element(
        "font",
        {
            "weight": str(weight),
            "style": style,
        },
    )
    font.text = maple_filename(filename_style)
    return font


def make_static_faces(*, include_italic: bool) -> list[ElementTree.Element]:
    faces: list[ElementTree.Element] = []
    for normal_style, italic_style, weight in STYLE_WEIGHTS:
        faces.append(make_font(weight, "normal", normal_style))
        if include_italic:
            faces.append(make_font(weight, "italic", italic_style))
    return faces


def family_font_filenames(family: ElementTree.Element) -> set[str]:
    filenames = set()
    for font in family.findall("font"):
        text = "".join(font.itertext()).strip()
        if text:
            filenames.add(text.split()[0])
    return filenames


def replace_family_fonts(
    root: ElementTree.Element,
    *,
    family_name: str,
    faces: Iterable[ElementTree.Element],
    required: bool,
) -> bool:
    for family in root.findall("family"):
        if family.get("name") != family_name:
            continue
        family[:] = list(faces)
        return True

    if required:
        raise ValueError(f"Missing required named family: {family_name}")
    return False


def replace_cjk_fallbacks(root: ElementTree.Element) -> int:
    replaced = 0
    for family in root.findall("family"):
        if family.get("lang") not in CJK_LANGS:
            continue
        if not any(
            filename.startswith(("NotoSansCJK", "SysSans-Hans", "SysSans-Hant"))
            for filename in family_font_filenames(family)
        ):
            continue
        # Keep the configuration shape that successfully booted on CPH2747.
        # A second same-language family changed framework fallback traversal on
        # this OxygenOS build and caused a boot loop during real-device testing.
        family[:] = make_static_faces(include_italic=False)
        replaced += 1

    if replaced != len(CJK_LANGS):
        raise ValueError(
            "Expected to replace four CJK fallbacks, "
            f"but replaced {replaced}: {sorted(CJK_LANGS)}"
        )
    return replaced


def rewrite_config(source_path: Path, output_path: Path) -> None:
    tree = ElementTree.parse(source_path)
    root = tree.getroot()
    if root.tag != "familyset":
        raise ValueError(f"Unexpected root element in {source_path}: {root.tag}")

    required_families = ("sans-serif", "monospace")
    optional_families = (
        "roboto",
        "roboto-flex",
        "sans-serif-condensed",
        "sys-sans-en",
        "op-sans-en",
    )
    for family_name in required_families:
        replace_family_fonts(
            root,
            family_name=family_name,
            faces=make_static_faces(include_italic=True),
            required=True,
        )
    for family_name in optional_families:
        replace_family_fonts(
            root,
            family_name=family_name,
            faces=make_static_faces(include_italic=True),
            required=False,
        )
    replace_cjk_fallbacks(root)

    ElementTree.indent(tree, space="    ")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(output_path, encoding="utf-8", xml_declaration=True)


def main() -> None:
    args = build_parser().parse_args()
    filenames = [name.strip() for name in args.configs.split(",") if name.strip()]
    if not filenames:
        raise ValueError("At least one configuration filename is required")

    for filename in filenames:
        source_path = args.samples_dir / filename
        if not source_path.is_file():
            raise FileNotFoundError(f"Missing pulled system font sample: {source_path}")
        partition = (
            "system_ext"
            if filename in {"fonts_base.xml", "fonts_ule.xml"}
            else "system"
        )
        output_path = args.output_dir / partition / "etc" / filename
        rewrite_config(source_path, output_path)
        print(f"Generated {output_path} from {source_path}")


if __name__ == "__main__":
    main()
