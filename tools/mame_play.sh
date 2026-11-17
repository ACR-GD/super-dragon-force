#!/bin/bash
# Play the patched translation in MAME (normal window, sound on).
#   tools/mame_play.sh            # patched English build
#   tools/mame_play.sh original   # original Chinese game
# Run tools/mame_test.sh once first; it prepares build/mame/<mode>/roms.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MODE="${1:-patched}"
ROMS="$ROOT/build/mame/$MODE/roms"
HASH="$(dirname "$(find /opt/homebrew/Cellar/mame -name supracan.xml | head -1)")"
[ -d "$ROMS/supracan/slghtsag" ] || { echo "Run tools/mame_test.sh <bios> $MODE first"; exit 1; }
cd "$ROOT/build/mame/$MODE"
exec mame supracan slghtsag -rompath "$ROMS" -hashpath "$HASH" -window -skip_gameinfo "${@:2}"
