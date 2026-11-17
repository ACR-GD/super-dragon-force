#!/usr/bin/env python3
"""Check translated short strings (names, items, spells, menu labels) against the width of
the on-screen fields that display them.

The game prints these strings through a fixed-width field printer (w_bbf8 / w_bdfc): the
caller passes a width in 16px tiles and anything longer is silently CUT OFF (that is how
"Short Sword" became "Short Swor" in the battle menu). Each tile holds two English letters.

The fields below were found by tracing every call of those printers in the Forth code
(notes/forth_listing.txt). String ids in the code are one higher than the index in
notes/short_strings_en.json (the offset table starts with a sentinel), so each range below
is given as JSON indices.

Strings drawn with the *unlimited* printers (w_bbd8 / w_bbe8, ~90 call sites: dialogue-box
labels, shop headings, prompts) are not checked here: they are never cut, but could overlap
neighbouring text on screen.
"""
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (group, first JSON index, last JSON index, [(tiles, where it is shown, traced from)])
FIELDS = [
    ("terrain",      0x009, 0x018, [(2, "terrain button on the battle map", "w_207f8 -> w_c308")]),
    # Full place names: location banner. The save/load slot list (w_270f8, 5 tiles) uses the
    # separate short names in notes/save_screen_places.json (see check_save_screen).
    ("place names",  0x01d, 0x048, [(10, "location banner", "w_2137c -> w_bfb4")]),
    ("unit names",   0x04f, 0x09d, [(5, "unit lists, status screen, name buttons",
                                     "w_23a24 / w_23c34 / w_270f8 / w_bcb0 / w_c320")]),
    ("classes",      0x0a9, 0x0f7, [(3, "class column in unit lists", "w_23a24 -> w_23594")]),
    ("items",        0x12b, 0x170, [(5, "battle menu, item lists, shops", "w_1c0f8 / w_24334 / w_243d0 -> w_bc80"),
                                    (4, "equipment slots (weapon/armor/accessory)", "w_24c28 / w_245d8 -> w_bc98")]),
    ("spells",       0x171, 0x1ab, [(5, "spell lists", "w_23d8c -> w_bc80")]),
    ("stat label",   0x1af, 0x1af, [(4, "equipment screen stat label", "w_245d8 -> w_bc98")]),
    ("option values", 0x1cf, 0x1d3, [(3, "options menu values", ".OPTION_MENU -> w_2a438")]),
    ("music titles", 0x210, 0x22a, [(8, "options menu music test", ".OPTION_MENU -> w_2a420")]),
]

# The equipment-slot field only shows equippable items; consumables never appear there.
EQUIPMENT_ONLY_NOTE = "equipment slots"


def tiles(text: str) -> int:
    return math.ceil(len(text) / 2)


def check(strings):
    """Return (errors, warnings); each string is reported once, under the field that cuts it most."""
    errors, warnings = [], []
    for group, first, last, fields in FIELDS:
        for idx in range(first, last + 1):
            en = strings[idx].get("en", "") if idx < len(strings) else ""
            if not en:
                continue
            failing = [f for f in fields if tiles(en) > f[0]]
            if not failing:
                continue
            # Items that only overflow the equipment slots are a problem only if equippable.
            hard = [f for f in failing if EQUIPMENT_ONLY_NOTE not in f[1]]
            width, where, traced = min(hard or failing, key=lambda f: f[0])
            entry = (group, idx, en, width, en[: 2 * width], where, traced)
            (errors if hard else warnings).append(entry)
    return errors, warnings


SAVE_SCREEN_TILES = 4   # 8 letters: the place column sits in the left box (see patch_menu_layouts)

# Place-name variants that must not reappear in dialogue (canonical names are the ones in
# short_strings_en.json / glossary.json).
RETIRED_PLACE_NAMES = {
    "Pamiros Plains": "Pamius Plains", "Barcus Keep": "Barukus Keep", "Anson Castle": "Anson City",
    "Barusa City": "Barusa Castle", "Training Waterfall": "Training Falls",
    "Bridge of Lost Souls": "Bridge of Souls", "Gypsy Nomad Camp": "Gypsy Camp",
    "Tower of the Ancients": "Ancient Tower", "demon stronghold": "Demon Fortress",
}


def is_abbreviation(short: str, full: str) -> bool:
    """True if the letters/digits of `short` appear in order in `full` ('5' may stand for 'five')."""
    full_l = [c for c in full.lower().replace("five", "5") if c.isalnum()]
    it = iter(full_l)
    return all(c in it for c in short.lower() if c.isalnum())


def check_save_screen(strings):
    """Short place names for the save/load list: must fit and must abbreviate the full name."""
    path = os.path.join(ROOT, "notes", "save_screen_places.json")
    names = json.load(open(path, encoding="utf-8"))["names"]
    problems = []
    for key, short in names.items():
        full = strings[int(key, 16)]["en"]
        if tiles(short) > SAVE_SCREEN_TILES:
            problems.append(f"save screen #{key} {short!r} is longer than {2 * SAVE_SCREEN_TILES} letters")
        if full and not is_abbreviation(short, full):
            problems.append(f"save screen #{key} {short!r} is not an abbreviation of {full!r}")
    return problems


def check_dialogue_names():
    """Dialogue must use the canonical place names."""
    path = os.path.join(ROOT, "notes", "dialogue_en.json")
    problems = []
    for d in json.load(open(path, encoding="utf-8")):
        for old, new in RETIRED_PLACE_NAMES.items():
            if old in d.get("en", ""):
                problems.append(f"dialogue #{d['id']} says {old!r}; the canonical name is {new!r}")
    return problems


def report(errors, warnings, out=sys.stdout):
    print(f"Short-string field check: {len(errors)} strings will be cut off, "
          f"{len(warnings)} cut only if equippable", file=out)
    last_group = None
    for kind, items in (("CUT OFF", errors), ("CUT IF EQUIPPABLE", warnings)):
        for group, idx, en, width, shown, where, traced in items:
            if (kind, group) != last_group:
                print(f"\n[{kind}] {group} — {where}: {width} tiles = {2 * width} letters  ({traced})", file=out)
                last_group = (kind, group)
            print(f"   #{idx:#05x} {en!r:24} shows as {shown!r}", file=out)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    strings = json.load(open(os.path.join(ROOT, "notes", "short_strings_en.json"), encoding="utf-8"))
    errors, warnings = check(strings)
    report(errors, warnings)
    naming = check_save_screen(strings) + check_dialogue_names()
    for n in naming:
        print("  !", n)
    out_path = os.path.join(ROOT, "build", "string_report.txt")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        report(errors, warnings, f)
    strict = "--strict" in argv
    return 1 if naming or (errors and strict) else 0


if __name__ == "__main__":
    sys.exit(main())
