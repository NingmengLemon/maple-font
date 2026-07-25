#!/usr/bin/env python3
"""Build a validated Magisk / KernelSU font module ZIP.

The module overlays only the pulled OxygenOS font configuration files and the
Maple Mono AllCJK files. It deliberately excludes legacy recovery installers:
Magisk and KernelSU managers already provide their own installation lifecycle.
"""

from __future__ import annotations

import argparse
import shutil
import xml.etree.ElementTree as ElementTree
import zipfile
from pathlib import Path

from generate_configs import DEFAULT_CONFIG_FILENAMES, FONT_PREFIX, rewrite_config


ROOT = Path(__file__).resolve().parent.parent
MODULE_DIR = Path(__file__).resolve().parent / "module"
SAMPLES_DIR = Path(__file__).resolve().parent / "samples"
FONTS_DIR = ROOT / "fonts" / "NF-AllCJK"
MODULE_FONTS_DIR = MODULE_DIR / "system" / "fonts"
VERSION = "v0.1.2-dev"

REQUIRED_MODULE_FILES = (
    Path("customize.sh"),
    Path("module.prop"),
    Path("service.sh"),
    Path("uninstall.sh"),
    Path("META-INF/com/google/android/update-binary"),
    Path("META-INF/com/google/android/updater-script"),
    Path("system/etc/font_fallback.xml"),
    Path("system/etc/fonts.xml"),
    Path("system_ext/etc/fonts_base.xml"),
    Path("system_ext/etc/fonts_ule.xml"),
)

PACKAGE_PATHS = (
    Path("customize.sh"),
    Path("module.prop"),
    Path("service.sh"),
    Path("uninstall.sh"),
    Path("META-INF"),
    Path("system"),
    Path("system_ext"),
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a validated Maple Mono OxygenOS 16 font module ZIP."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "font_module_dev" / f"maple-font-module-{VERSION}.zip",
        help="Destination ZIP path.",
    )
    parser.add_argument(
        "--skip-regenerate-configs",
        action="store_true",
        help="Use the existing generated XML instead of regenerating it from samples.",
    )
    return parser


def font_references(xml_path: Path) -> set[str]:
    root = ElementTree.parse(xml_path).getroot()
    references = set()
    for font in root.iter("font"):
        filename = "".join(font.itertext()).strip().split(maxsplit=1)
        if filename:
            references.add(filename[0])
    return references


def validate_module(font_files: set[str]) -> None:
    missing_files = [
        path for path in REQUIRED_MODULE_FILES if not (MODULE_DIR / path).is_file()
    ]
    if missing_files:
        joined = ", ".join(str(path) for path in missing_files)
        raise FileNotFoundError(f"Missing required module files: {joined}")

    expected_fonts = {
        filename
        for config_path in (
            MODULE_DIR / "system" / "etc" / "font_fallback.xml",
            MODULE_DIR / "system" / "etc" / "fonts.xml",
            MODULE_DIR / "system_ext" / "etc" / "fonts_base.xml",
            MODULE_DIR / "system_ext" / "etc" / "fonts_ule.xml",
        )
        for filename in font_references(config_path)
        if filename.startswith(FONT_PREFIX)
    }
    missing_fonts = sorted(expected_fonts - font_files)
    extra_fonts = sorted(font_files - expected_fonts)
    if missing_fonts or extra_fonts:
        messages = []
        if missing_fonts:
            messages.append(
                f"XML references missing Maple files: {', '.join(missing_fonts)}"
            )
        if extra_fonts:
            messages.append(
                f"Module contains unreferenced Maple files: {', '.join(extra_fonts)}"
            )
        raise ValueError("; ".join(messages))


def copy_fonts() -> set[str]:
    source_fonts = sorted(FONTS_DIR.glob(f"{FONT_PREFIX}-*.ttf"))
    if not source_fonts:
        raise FileNotFoundError(
            f"No merged fonts found in {FONTS_DIR}. Run merge_cjk_locales.py first."
        )

    MODULE_FONTS_DIR.mkdir(parents=True, exist_ok=True)
    expected_names = {path.name for path in source_fonts}
    for stale_font in MODULE_FONTS_DIR.glob("*.ttf"):
        if stale_font.name not in expected_names:
            stale_font.unlink()

    copied = 0
    for source_font in source_fonts:
        destination = MODULE_FONTS_DIR / source_font.name
        if (
            not destination.exists()
            or source_font.stat().st_size != destination.stat().st_size
            or source_font.stat().st_mtime_ns > destination.stat().st_mtime_ns
        ):
            shutil.copy2(source_font, destination)
            copied += 1

    total_size = sum(path.stat().st_size for path in source_fonts)
    print(
        f"[2/4] Synced {len(source_fonts)} fonts ({copied} copied, "
        f"{total_size / 1024 / 1024:.1f} MiB)"
    )
    return expected_names


def iter_package_files() -> list[Path]:
    files = []
    for package_path in PACKAGE_PATHS:
        path = MODULE_DIR / package_path
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(sorted(child for child in path.rglob("*") if child.is_file()))
    return sorted(files)


def write_zip(output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for file_path in iter_package_files():
            archive.write(file_path, file_path.relative_to(MODULE_DIR).as_posix())


def main() -> None:
    args = build_parser().parse_args()

    if not args.skip_regenerate_configs:
        for filename in DEFAULT_CONFIG_FILENAMES:
            partition = (
                "system_ext"
                if filename in {"fonts_base.xml", "fonts_ule.xml"}
                else "system"
            )
            rewrite_config(
                SAMPLES_DIR / filename,
                MODULE_DIR / partition / "etc" / filename,
            )
        print("[1/4] Regenerated XML overlays from pulled device samples")
    else:
        print("[1/4] Kept existing generated XML overlays")

    font_files = copy_fonts()
    validate_module(font_files)
    print("[3/4] Validated module layout and Maple XML/font references")

    write_zip(args.output)
    print(
        f"[4/4] Created {args.output} ({args.output.stat().st_size / 1024 / 1024:.1f} MiB)"
    )


if __name__ == "__main__":
    main()
