#!/usr/bin/env python3
"""Validate / review / apply shortened short-string proposals.

    python3 tools/apply_short_proposals.py            # validate + write notes/short_string_review.md
    python3 tools/apply_short_proposals.py --apply    # also write the proposals into short_strings_en.json

To pick an alternative, or your own wording, edit "en" in notes/short_string_proposals.json.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_strings as C

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROPOSALS = os.path.join(ROOT, "notes", "short_string_proposals.json")
STRINGS = os.path.join(ROOT, "notes", "short_strings_en.json")
REVIEW = os.path.join(ROOT, "notes", "short_string_review.md")


def limit_for(idx: int) -> int | None:
    """Narrowest on-screen field (in letters) that shows string idx."""
    widths = [w for _, a, b, fields in C.FIELDS if a <= idx <= b for w, _, _ in fields]
    return 2 * min(widths) if widths else None


def load():
    data = json.load(open(PROPOSALS, encoding="utf-8"))
    entries = []
    for group, items in data.items():
        if group.startswith("_"):
            continue
        for key, v in items.items():
            if key.startswith("_"):
                continue
            entries.append((group, int(key, 16), v))
    return data, entries


def main():
    apply = "--apply" in sys.argv
    strings = json.load(open(STRINGS, encoding="utf-8"))
    data, entries = load()
    problems = []
    for group, idx, v in entries:
        lim = limit_for(idx)
        for text in [v["en"]] + v.get("alt", []):
            if lim is not None and C.tiles(text) > lim // 2:
                problems.append(f"#{idx:#05x} {text!r} is {len(text)} letters; field limit is {lim}")
            if not C.is_abbreviation(text, strings[idx]["en"]):
                problems.append(f"#{idx:#05x} {text!r} is not an abbreviation of {strings[idx]['en']!r} "
                                f"(would show a different name than the dialogue)")
            if not all(32 <= ord(c) < 127 for c in text):
                problems.append(f"#{idx:#05x} {text!r} has characters outside the game's ASCII font")

    # Simulate the result and re-run the field check.
    merged = [dict(s) for s in strings]
    for _, idx, v in entries:
        merged[idx]["en"] = v["en"]
    errors, warnings = C.check(merged)

    # Review document
    with open(REVIEW, "w", encoding="utf-8") as f:
        f.write("# Shortened names: review\n\n")
        f.write("The game cuts these strings off at a fixed width (see `build/string_report.txt`).\n")
        f.write("Edit `notes/short_string_proposals.json` (change `en`, or copy in an alternative), then run\n")
        f.write("`python3 tools/apply_short_proposals.py --apply` and rebuild.\n\n")
        f.write("**Rule:** every short form abbreviates the full name (no renames), so screens and dialogue\n")
        f.write("always refer to the same thing. Names, items and spells are also inserted into dialogue\n")
        f.write("({CHAR1}, {ITEM}, {SPELL}), so the short forms appear in sentences too, e.g. \"Sam obtained Rest.Frt.\"\n\n")
        f.write("**Place names are not shortened:** the map banner and dialogue keep the full names. Only the\n")
        f.write("save/load slot list uses short ones (`notes/save_screen_places.json`), listed at the end.\n\n")
        notes = {g: items.get("_note") for g, items in data.items() if not g.startswith("_")}
        last = None
        for group, idx, v in entries:
            if group != last:
                f.write(f"\n## {group}\n\n")
                if notes.get(group):
                    f.write(f"> {notes[group]}\n\n")
                f.write("| # | Current | Shows now as | Proposed | Alternatives | Note |\n|---|---|---|---|---|---|\n")
                last = group
            cur = strings[idx]["en"]
            lim = limit_for(idx)
            alts = ", ".join(f"`{a}`" for a in v.get("alt", []))
            f.write(f"| `{idx:#05x}` | {cur} | `{cur[:lim]}` | **`{v['en']}`** | {alts} | {v.get('note', '')} |\n")

    # Save-screen place names
    with open(REVIEW, "a", encoding="utf-8") as f:
        f.write("\n## save/load slot list place names (10 letters)\n\n| # | Map banner & dialogue | Save screen |\n|---|---|---|\n")
        for key, short in json.load(open(os.path.join(ROOT, "notes", "save_screen_places.json")))["names"].items():
            full = strings[int(key, 16)]["en"]
            if full:
                f.write(f"| `{key}` | {full} | `{short}` |\n")
    problems += C.check_save_screen(strings) + C.check_dialogue_names()
    print(f"{len(entries)} proposals; {len(problems)} problems; after applying: "
          f"{len(errors)} cut off, {len(warnings)} cut if equippable")
    for p in problems:
        print("  !", p)
    print(f"Review table: {os.path.relpath(REVIEW, ROOT)}")
    if problems:
        return 1
    if apply:
        import re
        gen_path = os.path.join(ROOT, "tools", "translate_short_strings.py")
        src = open(gen_path, encoding="utf-8").read()
        for _, idx, v in entries:
            strings[idx]["en"] = v["en"]
            sid = strings[idx]["id"]
            rx = re.compile(rf"^(\s*){sid}: (\"(?:[^\"\\\\]|\\\\.)*\"|'(?:[^'\\\\]|\\\\.)*'),", re.M)
            src, n = rx.subn(lambda m: f"{m.group(1)}{sid}: {json.dumps(v['en'], ensure_ascii=False)},", src, count=1)
            if not n:
                print(f"  ! generator has no entry for id {sid}")
        with open(STRINGS, "w", encoding="utf-8") as f:
            json.dump(strings, f, ensure_ascii=False, indent=2)
            f.write("\n")
        with open(gen_path, "w", encoding="utf-8") as f:
            f.write(src)
        print(f"Applied to {os.path.relpath(STRINGS, ROOT)} and tools/translate_short_strings.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
