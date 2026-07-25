#!/usr/bin/env python3
"""Package an isolated Magisk / KernelSU experiment module from patched fonts."""

from __future__ import annotations

import argparse
import shutil
import zipfile
from pathlib import Path

FONT_PREFIX = "MapleMono-NF-AllCJK"


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
    return parser


def update_module_prop(
    path: Path,
    module_id: str,
    module_name: str,
    version: str,
) -> None:
    replacements = {
        "id": module_id,
        "name": module_name,
        "version": version,
    }
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

    update_module_prop(module_dir / "module.prop", module_id, module_name, version)
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
    )
    write_zip(args.module_dir, args.output)
    print(f"Packaged {len(copied)} patched fonts: {args.output}")


if __name__ == "__main__":
    main()
