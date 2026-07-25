# Maple Mono developer shortcuts
# Run `just --list` to see all recipes.

# Keep the POSIX default on Unix-like systems and use PowerShell on Windows.
set shell := ["sh", "-cu"]
set windows-shell := ["powershell.exe", "-NoLogo", "-NoProfile", "-Command"]

# Show available recipes.
default:
    @just --list

# Check formatting, lint, types, and the Python unit suite.
check:
    uv run ruff format --check .
    uv run ruff check .
    uv run pyrefly check
    uv run python -m unittest discover -s scripts/tests

# Generate OpenType feature files.
fea:
    uv run task.py fea

# Print the planned default font build without writing outputs.
build-dry:
    uv run build.py --dry

# Build all styles as hinted Nerd Font CJK TTFs for one locale.
# available locales: cn, jp, kr, tc
build-cjk locale="cn":
    uv run build.py --cjk {{ locale }} --format ttf --cache

# Rebuild a locale's standalone CJK variable and static base assets.
cjk-base locale="cn":
    uv run task.py cjk --config source/cjk/{{ locale }}/config-{{ locale }}.json

# Audit Extension G/H/I/J coverage in sources and built regular faces.
cjk-audit:
    uv run python font_module_dev/audit_cjk_extensions.py --include-built

# Print the planned full AllCJK merge and fail if inputs are missing.
merge-dry:
    uv run python merge_cjk_locales.py --dry

# Merge all 16 locale faces into AllCJK (CN > JP > TC > KR priority).
merge-all-cjk:
    uv run python merge_cjk_locales.py

# Regenerate XML overlays, sync the 16 AllCJK faces, validate, and package the module.
module:
    uv run python font_module_dev/build_module.py

# Execute the staged local release workflow: CJK base, merge, audit, and module package.
module-release:
    just cjk-base cn
    just merge-all-cjk
    just cjk-audit
    just module

# Verify font-module code, focused tests, and the final Git diff.
module-check:
    uv run ruff format --check font_module_dev/build_module.py font_module_dev/audit_cjk_extensions.py font_module_dev/generate_configs.py
    uv run ruff check font_module_dev/build_module.py font_module_dev/audit_cjk_extensions.py font_module_dev/generate_configs.py
    uv run python -m unittest scripts.tests.test_cjk_locale_merge
    git diff --check
    git diff --stat
    git status --short
