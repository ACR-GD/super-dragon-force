#!/bin/bash
# Frame-exact MAME capture for comparing against our emulator.
#   tools/mame_frames.sh <bios> <mode> "<frame:Button:holdframes,...>" "<from-to,from-to>" 
# Buttons are pressed on exact frame numbers (counted from boot) and snapshots are
# taken for every frame in the listed ranges, named by frame number.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BIOS="$1"; MODE="${2:-patched}"; PRESSES="${3:-}"; RANGES="${4:-}"
WORK="$ROOT/build/mame/$MODE"
HASH="$(dirname "$(find /opt/homebrew/Cellar/mame -name supracan.xml | head -1)")"
[ -d "$WORK/roms/supracan/slghtsag" ] || "$ROOT/tools/mame_test.sh" "$BIOS" "$MODE" 1 >/dev/null
rm -rf "$WORK/frames"; mkdir -p "$WORK/frames"
cat > "$WORK/frames.lua" << LUA
local NAMES = { Start = "1 Player Start", A = "P1 Button A", B = "P1 Button B", X = "P1 Button X",
                Up = "P1 Joypad Up", Down = "P1 Joypad Down", Left = "P1 Joypad Left", Right = "P1 Joypad Right" }
local presses, ranges = {}, {}
for item in ("$PRESSES"):gmatch("[^,]+") do
  local f, b, h = item:match("^(%d+):(%a+):?(%d*)$")
  if f then presses[tonumber(f)] = { b, tonumber(h) or 4 } end
end
for item in ("$RANGES"):gmatch("[^,]+") do
  local a, b = item:match("^(%d+)%-(%d+)$"); if a then ranges[#ranges+1] = { tonumber(a), tonumber(b) } end
end
local fields = {}
for _, port in pairs(manager.machine.ioport.ports) do for n, f in pairs(port.fields) do fields[n] = f end end
local frame, held, release_at, last_frame = 0, nil, 0, 0
for _, r in ipairs(ranges) do if r[2] > last_frame then last_frame = r[2] end end
for f, _ in pairs(presses) do if f > last_frame then last_frame = f end end
emu.register_frame_done(function()
  frame = frame + 1
  if held and frame >= release_at then held:set_value(0); held = nil end
  local p = presses[frame]
  if p and not held then local f = fields[NAMES[p[1]]]; if f then f:set_value(1); held = f; release_at = frame + p[2] end end
  for _, r in ipairs(ranges) do
    if frame >= r[1] and frame <= r[2] then
      manager.machine.video:snapshot()
    end
  end
  if frame > last_frame + 2 then manager.machine:exit() end
end)
LUA
cd "$WORK"
mame supracan slghtsag -rompath "$WORK/roms" -hashpath "$HASH" -snapshot_directory "$WORK/frames" -snapname "%i" \
     -video none -sound none -nothrottle -seconds_to_run 100000 -autoboot_script "$WORK/frames.lua" 2>&1 | grep -iE "error|exception" || true
# rename snapshots to their frame numbers
python3 - "$WORK/frames" "$RANGES" << 'PY'
import os, sys, glob
d, ranges = sys.argv[1], sys.argv[2]
frames = []
for item in ranges.split(','):
    a, b = map(int, item.split('-')); frames += list(range(a, b + 1))
files = sorted(glob.glob(os.path.join(d, '*.png')), key=lambda p: int(os.path.basename(p)[:-4]))
for f, fr in zip(files, frames):
    os.rename(f, os.path.join(d, f'f{fr:06d}.png'))
print(f"{len(files)} frames captured")
PY
