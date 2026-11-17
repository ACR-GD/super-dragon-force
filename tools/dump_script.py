"""Dump all Chinese text tables from Super Dragon Force using notes/glyph_table.json."""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from romutil import load_prg, u16, u32
import lzss

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GT_PATH = os.path.join(ROOT, "notes", "glyph_table.json")

FIXES = {
    0: "　",
    82: "場", 200: "怪", 231: "士", 298: "合", 322: "鬧", 346: "雹",
    366: "開", 392: "＜", 393: "－", 394: "＞", 415: "束", 443: "。",
    462: "名", 515: "歲", 519: "・", 557: "術", 560: "：", 571: "（",
    576: "）", 578: "’", 665: "熊", 671: "ㄅ", 682: "ㄆ", 697: "ㄇ",
    706: "ㄈ", 708: "夫", 715: "服", 717: "ㄉ", 723: "東", 726: "ㄊ",
    727: "土", 732: "廷", 740: "ㄋ", 745: "囡", 750: "ㄌ", 755: "吏",
    761: "ㄍ", 773: "ㄎ", 778: "刻", 785: "乎", 794: "ㄐ", 807: "ㄑ",
    810: "欠", 820: "ㄒ", 832: "ㄓ", 840: "助", 858: "ㄕ", 865: "ㄖ",
    876: "ㄗ", 898: "采", 901: "財", 904: "ㄙ", 913: "ㄚ", 914: "ㄜ",
    947: "ㄠ", 951: "敖", 955: "蘭", 956: "ㄡ", 958: "鷗", 963: "ㄢ",
    984: "也", 1075: "、", 1076: "・", 1249: "：", 1308: "庫", 1319: "掌",
    1328: "！", 1329: "？", 1330: "、", 1335: "又", 1388: "應", 1443: "殊",
    1455: "館", 1469: "追", 1475: "炭", 1515: "．", 1547: "拿", 1641: "簡",
    1705: "輩", 1770: "襲", 1779: "泊", 1784: "：", 1792: "妨", 1801: "彷",
    1804: "傻", 1831: "懊", 1871: "嗚", 1877: "治", 1878: "３", 1879: "０",
    1885: "屎", 1891: "蠢", 1893: "延", 1922: "迫", 1932: "仍", 1948: "優",
    1962: "臟", 1967: "鷹",
}

CTRL_NAMES = {
    0x8000: "{HERO}",
    0x8001: "{NUM1}",
    0x8002: "{CHAR1}",
    0x8003: "{CHAR2}",
    0x8004: "{GOLD}",
    0x8005: "{PARTY}",
    0x8006: "{CHAR3}",
    0x8007: "{ITEM}",
    0x8008: "{SPELL}",
    0x800A: "{NUM2}",
    0xFFFF: "{END}",
}

def load_glyph_table():
    gt = {int(k): v for k, v in json.load(open(GT_PATH, encoding="utf-8")).items()}
    gt.update(FIXES)
    json.dump({str(k): v for k, v in sorted(gt.items())}, open(GT_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return gt

def decode_words(words, gt):
    out = []
    for w in words:
        if w in CTRL_NAMES:
            out.append(CTRL_NAMES[w])
        elif w >= 0x8000:
            out.append(f"{{{w:#06x}}}")
        else:
            out.append(gt.get(w, f"[{w:03x}]"))
    return "".join(out)

def main():
    p = load_prg()
    gt = load_glyph_table()

    # 1. Short strings at 0x5cc22 (indices 1..748)
    SBASE = 0x5CC22
    short_list = []
    short_txt = []
    for i in range(1, 749):
        o1, o2 = u16(p, SBASE + 2 * i), u16(p, SBASE + 2 * (i + 1))
        words = [u16(p, SBASE + o) for o in range(o1, o2, 2)]
        text = decode_words(words, gt)
        short_list.append({"id": i, "hex_id": f"{i:#05x}", "len": len(words), "zh": text, "words": words})
        short_txt.append(f"[{i:03d} / {i:#05x}] (len={len(words):2d}): {text}")

    open(os.path.join(ROOT, "notes", "short_strings_zh.json"), "w", encoding="utf-8").write(
        json.dumps(short_list, ensure_ascii=False, indent=2)
    )
    open(os.path.join(ROOT, "notes", "short_strings_zh.txt"), "w", encoding="utf-8").write(
        "\n".join(short_txt) + "\n"
    )

    # 2. Dialogue messages at 0x107ec (18 blocks * 100 messages)
    TBASE = 0x107EC
    dlg_list = []
    dlg_txt = []
    for blk in range(18):
        src = u32(p, TBASE + 4 * blk)
        buf, _ = lzss.decompress(p, src)
        dlen = len(buf)
        for m in range(100):
            if 8 * m + 8 > dlen:
                break
            off = u32(buf, 8 * m)
            ln = u16(buf, 8 * m + 4)
            port = u16(buf, 8 * m + 6)
            mid = blk * 100 + m
            if ln != 0xFFFF and ln > 0 and off + 2 * ln <= dlen:
                words = [u16(buf, off + 2 * j) for j in range(ln)]
                text = decode_words(words, gt)
                dlg_list.append({
                    "id": mid, "hex_id": f"{mid:#06x}", "block": blk, "index": m,
                    "portrait": port, "len": ln, "zh": text, "words": words
                })
                dlg_txt.append(f"[{mid:04d} / {mid:#06x}] (port={port:3d}, len={ln:3d}): {text}")

    open(os.path.join(ROOT, "notes", "dialogue_zh.json"), "w", encoding="utf-8").write(
        json.dumps(dlg_list, ensure_ascii=False, indent=2)
    )
    open(os.path.join(ROOT, "notes", "dialogue_zh.txt"), "w", encoding="utf-8").write(
        "\n".join(dlg_txt) + "\n"
    )
    print(f"Dumped {len(short_list)} short strings and {len(dlg_list)} dialogue messages.")

if __name__ == "__main__":
    main()
