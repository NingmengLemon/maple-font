#!/usr/bin/env python3
"""Package an isolated Magisk / KernelSU experiment module from patched fonts."""

from __future__ import annotations

import argparse
import shutil
import zipfile
from pathlib import Path

from font_module_dev.generate_configs import DEFAULT_CONFIG_FILENAMES, rewrite_config


FONT_PREFIX = "MapleMono-NF-AllCJK"
SAMPLES_DIR = Path(__file__).resolve().parent / "samples"
CONFIG_PARTITIONS = {
    "font_fallback.xml": "system",
    "fonts.xml": "system",
    "fonts_base.xml": "system_ext",
    "fonts_ule.xml": "system_ext",
}


PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_MODULE_DIR = Path(__file__).resolve().parent / "module"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Package an isolated module without changing the stable module tree."
    )
    parser.add_argument("--fonts-dir", type=Path, required=True)
    parser.add_argument("--module-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--module-id", required=True)
    parser.add_argument("--module-name", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument(
        "--preserve-cjk",
        action="store_true",
        help="Regenerate XML overlays while retaining original CJK fallback families.",
    )
    parser.add_argument(
        "--ui-families",
        type=str,
        default=None,
        help="Comma-separated named UI families to replace during XML regeneration.",
    )
    parser.add_argument(
        "--generic-fallback-font",
        type=str,
        default=None,
        help=(
            "Optional existing system font filename to add after the generic "
            "Noto Symbols fallback. Intended only for isolated fallback experiments."
        ),
    )
    parser.add_argument(
        "--description",
        default=None,
        help="Optional module.prop description override.",
    )
    return parser


def update_module_prop(
    path: Path,
    module_id: str,
    module_name: str,
    version: str,
    description: str | None,
) -> None:
    replacements = {
        "id": module_id,
        "name": module_name,
        "version": version,
    }
    if description is not None:
        replacements["description"] = description
    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text(
        "\n".join(
            f"{key}={replacements.get(key, value)}"
            for line in lines
            for key, _, value in (line.partition("="),)
        )
        + "\n",
        encoding="utf-8",
    )


def source_fonts(fonts_dir: Path) -> list[Path]:
    fonts = sorted(fonts_dir.glob(f"{FONT_PREFIX}-*.ttf"))
    if len(fonts) != 16:
        raise ValueError(
            f"Expected 16 patched AllCJK fonts in {fonts_dir}, found {len(fonts)}"
        )
    return fonts


def stage_module(
    fonts_dir: Path,
    module_dir: Path,
    module_id: str,
    module_name: str,
    version: str,
    description: str | None,
    preserve_cjk: bool,
    ui_families: tuple[str, ...] | None,
    generic_fallback_font: str | None,
) -> list[Path]:
    if module_dir.resolve() == TEMPLATE_MODULE_DIR.resolve():
        raise ValueError(
            "Experiment module directory must not be the stable module template."
        )
    fonts = source_fonts(fonts_dir)
    shutil.rmtree(module_dir, ignore_errors=True)
    shutil.copytree(
        TEMPLATE_MODULE_DIR, module_dir, ignore=shutil.ignore_patterns("fonts")
    )

    target_fonts_dir = module_dir / "system" / "fonts"
    target_fonts_dir.mkdir(parents=True)
    copied = []
    for font in fonts:
        destination = target_fonts_dir / font.name
        shutil.copy2(font, destination)
        copied.append(destination)

    if preserve_cjk or ui_families is not None or generic_fallback_font is not None:
        for filename in DEFAULT_CONFIG_FILENAMES:
            rewrite_config(
                SAMPLES_DIR / filename,
                module_dir / CONFIG_PARTITIONS[filename] / "etc" / filename,
                preserve_cjk=preserve_cjk,
                ui_families=ui_families,
                generic_fallback_font=generic_fallback_font,
            )

    update_module_prop(
        module_dir / "module.prop",
        module_id,
        module_name,
        version,
        description,
    )
    return copied


def write_zip(module_dir: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for file_path in sorted(
            path for path in module_dir.rglob("*") if path.is_file()
        ):
            archive.write(file_path, file_path.relative_to(module_dir).as_posix())


def main() -> None:
    args = build_parser().parse_args()
    copied = stage_module(
        args.fonts_dir,
        args.module_dir,
        args.module_id,
        args.module_name,
        args.version,
        args.description,
        args.preserve_cjk,
        (
            tuple(name.strip() for name in args.ui_families.split(",") if name.strip())
            if args.ui_families is not None
            else None
        ),
        args.generic_fallback_font,
    )
    write_zip(args.module_dir, args.output)
    print(f"Packaged {len(copied)} patched fonts: {args.output}")


if __name__ == "__main__":
    main()
