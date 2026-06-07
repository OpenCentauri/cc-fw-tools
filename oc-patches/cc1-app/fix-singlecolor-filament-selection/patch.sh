#!/usr/bin/env bash
set -euo pipefail

# fix-singlecolor-filament-selection patch for CC1 app 1.4.46
# This patch forces the SET_ALL_CHANNELS_SAME handler to always write 0,
# preventing cmd_M749 from skipping the unload/load cycle on single-color prints.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PATCH_FILE="${SCRIPT_DIR}/fix-singlecolor-filament-selection-1.4.46.bsdiff"
STOCK_APP="${1:?Usage: $0 <path/to/stock/app-1.4.46>}"
OUTPUT_APP="${2:?Usage: $0 <stock> <output>}"

if [[ ! -f "$PATCH_FILE" ]]; then
    echo "ERROR: Patch file not found: $PATCH_FILE" >&2
    echo "Generate it first with generate_patch.py" >&2
    exit 1
fi

if ! command -v bspatch &>/dev/null; then
    echo "ERROR: bspatch not found in PATH" >&2
    exit 1
fi

bspatch "$STOCK_APP" "$OUTPUT_APP" "$PATCH_FILE"
echo "Patched app written to: $OUTPUT_APP"
