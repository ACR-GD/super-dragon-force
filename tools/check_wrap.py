#!/usr/bin/env python3
"""Verify dialogue word-wrap against a model of the game's text engine.

For every translated message, render it the way the engine does (tile-index layouts,
tag relocation at the box edge, NEWLINE) with both the shortest and longest possible tag
values, then check that no line overflows and no word is split across lines.
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_rom as B

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WIDTH = {"dialogue": lambda i: (0, i) if i < 16 else (1 + (i - 16) // 15, (i - 16) % 15),
         "narrow":   lambda i: (i // 12, i % 12),
         "battle":   lambda i: (i // 16, i % 16)}
LINE_W = {"dialogue": lambda ln: 16 if ln == 0 else 15, "narrow": lambda ln: 12, "battle": lambda ln: 16}
# Column (in 8px units) the engine uses for the box-edge check in w_1065c / w_1074c.
XCOL = {"dialogue": lambda ln, c: (2 if ln == 0 else 4) + 2 * c, "narrow": lambda ln, c: 1 + 2 * c,
        "battle": lambda ln, c: 2 + 2 * c}

def tag_values(mode):
    long = {"{HERO}": "Alexa", "{CHAR1}": "Five-Head Dragon", "{CHAR2}": "Five-Head Dragon",
            "{CHAR3}": "Five-Head Dragon", "{PARTY}": "Raymond", "{ITEM}": "Gatling Cannon",
            "{SPELL}": "Antidote 1", "{NUM1}": "99999", "{GOLD}": "99999", "{NUM2}": "99999"}
    short = {k: "Al" if k == "{HERO}" else ("9" if "NUM" in k or k == "{GOLD}" else "Eve") for k in long}
    return long if mode == "long" else short

def render(words, layout, tags):
    inv = {v: k for k, v in B.CONTROL_TAGS.items()}
    cells = {}      # (line, col) -> 2 chars
    idx = 0
    def put(s2):
        nonlocal idx
        cells[WIDTH[layout](idx)] = s2
        idx += 1
    for w in words:
        if w == B.NEWLINE:
            ln, c = WIDTH[layout](idx)
            if c:
                idx += LINE_W[layout](ln) - c
        elif w >= 0x8000:
            val = tags[inv[w]]
            val += " " * (len(val) % 2)
            n = len(val) // 2
            ln, c = WIDTH[layout](idx)
            x = XCOL[layout](ln, c)
            if x + 2 * n > 0x22:                       # engine moves the tag down a line
                idx += (0x22 - x) // 2
            for i in range(n):
                put(val[2 * i:2 * i + 2])
        else:
            put(chr(w >> 8) + chr(w & 0xFF))
    lines = {}
    for (ln, c), s2 in cells.items():
        lines.setdefault(ln, {})[c] = s2
    out = []
    for ln in range(max(lines) + 1 if lines else 0):
        row = lines.get(ln, {})
        out.append("".join(row.get(c, "  ") for c in range(max(row) + 1 if row else 0)) if row else "")
    return out

def problems(text, words, layout, tags):
    lines = render(words, layout, tags)
    errs = []
    for ln, s in enumerate(lines):
        if len(s) > 2 * LINE_W[layout](ln):
            errs.append(f"line {ln} overflows: {s!r}")
    expanded = text
    for k, v in tags.items():
        expanded = expanded.replace(k, v)
    expanded = (expanded.replace("—", "-").replace("–", "-").replace("“", '"').replace("”", '"')
                .replace("‘", "'").replace("’", "'").replace("…", "..."))
    # Walk the expanded text and the rendered lines together (ignoring extra spaces).
    # A line break is a split if the characters on either side were adjacent in the text.
    flat = "\n".join(l.rstrip() for l in lines)
    src = re.sub(r"\s+", " ", expanded.strip())
    i = 0
    prev_nl = False
    for ch in flat:
        if ch == "\n":
            prev_nl = True
            continue
        if ch == " ":
            continue
        while i < len(src) and src[i] == " ":
            i += 1
        if i >= len(src) or src[i] != ch:
            errs.append(f"text mismatch near {src[max(0,i-10):i+10]!r}")
            break
        if prev_nl and i > 0 and src[i - 1] != " ":
            errs.append(f"word split: ...{src[max(0,i-8):i]}|{src[i:i+8]}...")
        prev_nl = False
        i += 1
    return errs, lines

def main():
    zh = {d["id"]: d for d in json.load(open(os.path.join(ROOT, "notes", "dialogue_zh.json")))}
    en = json.load(open(os.path.join(ROOT, "notes", "dialogue_en.json")))
    bad, total, examples = 0, 0, []
    for item in en:
        text = item.get("en", "").strip()
        if not text or item["id"] not in zh:
            continue
        layout = B.layout_for_message(item["id"], zh[item["id"]]["block"])
        words = B.encode_dialogue_lines(text, layout)
        total += 1
        errs = []
        for mode in ("short", "long"):
            e, lines = problems(text, words, layout, tag_values(mode))
            errs += [f"[{mode}] {x}" for x in e]
        if errs:
            bad += 1
            if len(examples) < 8:
                examples.append((item["id"], layout, errs[:3], render(words, layout, tag_values("long"))))
    print(f"{total} messages checked, {bad} with wrapping problems")
    for mid, layout, errs, lines in examples:
        print(f"\n#{mid} ({layout}): {errs}")
        for l in lines: print("   |" + l + "|")
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main())
