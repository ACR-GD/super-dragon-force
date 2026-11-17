"""Build the 1993-entry glyph-to-Unicode table using macOS Vision OCR
on both carrier phrases (two rendering thicknesses) and full corpus strings."""
import os, sys, re, json, subprocess, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from romutil import load_prg, u16, u32
from emu import Emu
from PIL import Image

p = load_prg()
FONT_BASE = 0x3e290
N_GLYPHS = 1993

def draw_glyph(pix, gx, gy, idx, scale=3, thick=1):
    if idx >= N_GLYPHS or idx <= 0:
        return
    base = FONT_BASE + idx * 30
    for r in range(15):
        w = u16(p, base + r * 2)
        for c in range(16):
            if (w >> (15 - c)) & 1:
                for dy in range(scale + thick):
                    for dx in range(scale + thick):
                        pix[gx + c * scale + dx, gy + r * scale + dy] = 0

def run_carrier_pass(thick=1, tag="t1"):
    # Carrier: 請(13) 選(14) 擇(15) 「(475) G 」(478) 的(59) 物(257) 品(269)
    prefix = [13, 14, 15, 475]
    suffix = [478, 59, 257, 269]
    scale = 3
    row_h = 24 * scale
    W = 14 * 18 * scale
    batch_size = 50
    results = {}
    img_paths = []
    batches = []
    for start in range(1, N_GLYPHS, batch_size):
        ids = list(range(start, min(N_GLYPHS, start + batch_size)))
        H = (len(ids) + 2) * row_h
        img = Image.new("L", (W, H), 255)
        pix = img.load()
        for i, g in enumerate(ids):
            y = (i + 1) * row_h
            seq = prefix + [g] + suffix
            for col_i, cid in enumerate(seq):
                draw_glyph(pix, (col_i + 1) * 18 * scale, y, cid, scale=scale, thick=thick)
        path = f"build/carrier_{tag}_{start:04d}.png"
        img.save(path)
        img_paths.append(path)
        batches.append((path, ids, H, row_h, scale))

    out = subprocess.check_output(["build/ocr_vision"] + img_paths).decode()
    by_file = collections.defaultdict(list)
    for line in out.splitlines():
        d = json.loads(line)
        by_file[d["file"]].append(d)

    for path, ids, H, row_h, scale in batches:
        for d in by_file[path]:
            yc = 1.0 - (d["y"] + d["h"] / 2)
            row_est = round((yc * H - 7 * scale) / row_h) - 1
            if 0 <= row_est < len(ids):
                g = ids[row_est]
                for cand in d["cands"]:
                    txt = cand["text"]
                    m = re.search(r"[「『\[](.)[」』\]]", txt)
                    if not m and len(txt) == 9 and txt.startswith("請選擇") and txt.endswith("的物品"):
                        ch = txt[4]
                    elif m:
                        ch = m.group(1)
                    elif len(txt) == 8 and txt.startswith("請選擇") and txt.endswith("的物品"):
                        ch = txt[3]
                    else:
                        continue
                    results.setdefault(g, []).append((ch, cand["conf"]))
    return results

print("Running carrier pass 1 (thick=1)...")
r1 = run_carrier_pass(thick=1, tag="t1")
print(f"  matched {len(r1)} / {N_GLYPHS-1}")
print("Running carrier pass 2 (thick=0)...")
r2 = run_carrier_pass(thick=0, tag="t0")
print(f"  matched {len(r2)} / {N_GLYPHS-1}")

# Combine votes
table = {0: "　"}
disagreements = []
missing = []
for g in range(1, N_GLYPHS):
    c1 = r1.get(g, [])
    c2 = r2.get(g, [])
    if c1 and c2:
        if c1[0][0] == c2[0][0]:
            table[g] = c1[0][0]
        else:
            table[g] = c1[0][0]
            disagreements.append((g, c1[0][0], c2[0][0]))
    elif c1:
        table[g] = c1[0][0]
    elif c2:
        table[g] = c2[0][0]
    else:
        table[g] = f"[{g:03x}]"
        missing.append(g)

print(f"Exact agreement between thick=1 and thick=0: {N_GLYPHS - 1 - len(disagreements) - len(missing)} / {N_GLYPHS - 1}")
print(f"Disagreements: {len(disagreements)}, Missing: {len(missing)}")
open("notes/glyph_table.json", "w", encoding="utf-8").write(
    json.dumps({str(k): v for k, v in sorted(table.items())}, ensure_ascii=False, indent=2)
)
for g, a, b in disagreements[:40]:
    print(f"  disagree g={g:4d} ({g:#05x}): t1={a} vs t0={b}")
print("Missing IDs:", missing)
