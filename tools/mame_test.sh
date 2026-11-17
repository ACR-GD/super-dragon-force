#!/bin/bash
# Run the patched translation in MAME (headless) and save screenshots for review.
#
#   tools/mame_test.sh /path/to/supracan(.zip or folder) [original|patched] [seconds]
#
# Needs MAME's Super A'Can system ROMs (supracan.zip: internal_68k.bin, internal_6502_1.bin,
# internal_6502_2.bin, umc6650.bin), dumped from your own console. They are not included.
# Screenshots land in build/mame/<mode>/.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BIOS="${1:?usage: tools/mame_test.sh /path/to/supracan.zip [original|patched] [seconds]}"
MODE="${2:-patched}"
SECONDS_TO_RUN="${3:-150}"
HASH="$(dirname "$(find /opt/homebrew/Cellar/mame -name supracan.xml | head -1)")"

WORK="$ROOT/build/mame/$MODE"
rm -rf "$WORK" && mkdir -p "$WORK/roms/supracan/slghtsag" "$WORK/snap"
if [ -d "$BIOS" ]; then
  cp "$BIOS"/*.bin "$WORK/roms/supracan/"      # folder with the four system ROM files
else
  cp "$BIOS" "$WORK/roms/supracan.zip"
fi
if [ "$MODE" = original ]; then
  cp "$ROOT/Super-Dragon-Force_Super-Acan_ZH-TW/16007 (Taiwan).bin" "$WORK/roms/supracan/slghtsag/16007.0"
  cp "$ROOT/Super-Dragon-Force_Super-Acan_ZH-TW/08002 (Taiwan).bin" "$WORK/roms/supracan/slghtsag/08007.1"
else
  cp "$ROOT/build/Super-Dragon-Force_EN.bin"     "$WORK/roms/supracan/slghtsag/16007.0"
  cp "$ROOT/build/Super-Dragon-Force_DAT_EN.bin" "$WORK/roms/supracan/slghtsag/08007.1"
fi

# Lua: screenshot every 5 s; press Start/B on the same schedule our emulator tests use
# (title -> new game -> gender -> name -> into the intro dialogue and first town).
cat > "$WORK/script.lua" << 'LUA'
-- Same sequence as the emulator tests: title -> Start -> Start -> B -> B -> X -> Start,
-- then B every 3 s to page through the intro dialogue into the first town.
local NAMES = { Start = "1 Player Start", A = "P1 Button A", B = "P1 Button B", X = "P1 Button X",
                Up = "P1 Joypad Up", Down = "P1 Joypad Down", Left = "P1 Joypad Left", Right = "P1 Joypad Right" }
local presses = { [62]="Start", [66]="Start", [70]="B", [74]="B", [78]="X", [82]="Start" }
for t = 86, 130, 3 do presses[t] = "B" end
-- SCRIPT env var can append more: "t:Button,t:Button[,hold]" e.g. "140:Right:2,143:B"
local holds = {}
for item in (os.getenv("SCRIPT") or ""):gmatch("[^,]+") do
  local t, b, h = item:match("^(%d+):(%a+):?([%d%.]*)$")
  if t then presses[tonumber(t)] = b; holds[tonumber(t)] = tonumber(h) or 0.15 end
end
local fields = {}
for _, port in pairs(manager.machine.ioport.ports) do
  for fname, f in pairs(port.fields) do fields[fname] = f end
end
local next_shot, held, held_until = 0, nil, 0
emu.register_frame_done(function()
  local t = manager.machine.time.seconds
  if t >= next_shot then manager.machine.video:snapshot(); next_shot = next_shot + 5 end
  if held and t >= held_until then held:set_value(0); held = nil end
  local s = math.floor(t)
  local name = presses[s]
  if name and not held then
    local f = fields[NAMES[name]]
    if f then f:set_value(1); held = f; held_until = t + (holds[s] or 0.15); presses[s] = nil end
  end
end)
LUA

cd "$WORK"
mame supracan slghtsag -rompath "$WORK/roms" -hashpath "$HASH" \
     -snapshot_directory "$WORK/snap" -snapname "%i" \
     -video none -sound none -nothrottle -seconds_to_run "$SECONDS_TO_RUN" \
     -autoboot_script "$WORK/script.lua" 2>&1 | grep -v -E "^$" | tail -20
echo "Screenshots: $WORK/snap"
