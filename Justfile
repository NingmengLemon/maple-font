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
# Each locale writes only under source/cjk/<locale>/, so independent locales are safe to run together.
cjk-base locale="cn":
    uv run task.py cjk --config source/cjk/{{ locale }}/config-{{ locale }}.json

# Rebuild CN, JP, TC, and KR CJK base caches concurrently.
# Each child still uses config.json's pool_size workers; keep JUST_JOBS * pool_size
# at or below the physical-core count to avoid memory pressure and disk contention.
[parallel]
cjk-bases: (cjk-base "cn") (cjk-base "jp") (cjk-base "tc") (cjk-base "kr")

# Build all CJK output faces from the base caches in one process.
# Do not run separate build-cjk recipes concurrently: they share fonts/ and build-cache.json.
build-all-cjk:
    uv run build.py --cjk cn,jp,tc,kr --format ttf --cache

# Audit Extension G/H/I/J coverage in sources and built regular faces.
cjk-audit:
    uv run python font_module_dev/audit_cjk_extensions.py --include-built

# Inspect declared vertical metrics and actual outline bounds before device testing.
vertical-audit font="fonts/NF-AllCJK/MapleMono-NF-AllCJK-Regular.ttf":
    uv run python -m font_module_dev.audit_vertical_metrics {{ font }}

# Dry-run a compact CJK experiment without changing the verified fonts/ tree.
mobile-dry line_height="0.95" output_dir="font_module_dev/experiments/line-height-0.95":
    uv run build.py --cjk cn,jp,tc,kr --format ttf --no-hinted --line-height {{ line_height }} --output-dir {{ output_dir }} --dry

# Copy and patch the final AllCJK faces into a separate mobile-metric experiment.
mobile-patch ascent="970" descent="-300" experiment="ascent-970":
    uv run python -m font_module_dev.patch_vertical_metrics --ascent {{ ascent }} --descent {{ descent }} --output-dir font_module_dev/experiments/{{ experiment }}/fonts

# Package an isolated module with a distinct ID from an experiment directory.
mobile-module experiment="ascent-970" version="metrics-a970-d300":
    uv run python -m font_module_dev.package_experiment_module --fonts-dir font_module_dev/experiments/{{ experiment }}/fonts --module-dir font_module_dev/experiments/{{ experiment }}/module --output font_module_dev/experiments/{{ experiment }}/maple-font-{{ experiment }}.zip --module-id maple-font-{{ experiment }} --module-name "Maple Mono NF AllCJK {{ experiment }}" --version {{ version }}

# Print the planned full AllCJK merge and fail if inputs are missing.
merge-dry:
    uv run python merge_cjk_locales.py --dry

# Merge all 16 locale faces into AllCJK (CN > JP > TC > KR priority).
merge-all-cjk:
    uv run python merge_cjk_locales.py

# Regenerate XML overlays, sync the 16 AllCJK faces, validate, and package the module.
module:
    uv run python font_module_dev/build_module.py

# Execute the staged local release workflow: parallel CJK bases, shared output build,
# merge, audit, and module package. On the current 16-core host, start with: just --jobs 4 module-release
module-release:
    just cjk-bases
    just build-all-cjk
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
