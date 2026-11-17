#!/usr/bin/env python3
"""Build translated Super Dragon Force ROM for Super A'Can.

Pipeline:
1. Load original 16007 (Taiwan).bin and un-swap 16-bit words.
2. Install unified English/Chinese text engine patch at 0x000200 (exception vector padding).
3. Install English short strings at 0x045000 and update 9 pointer references.
4. Install English dialogue blocks (with LZSS compression) at 0x047000 and update 18 pointers at 0x0107EC.
5. Patch default hero names at 0x05E500 and update pointers at 0x05E0A0.
6. Byte-swap words back to hardware/MAME format.
7. Write build/Super-Dragon-Force_EN.bin and build/Super-Dragon-Force_EN.ips patch.
"""

import os
import sys
import json
import struct
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYS_PATH = os.path.join(BASE_DIR, "tools")
if SYS_PATH not in sys.path:
    sys.path.insert(0, SYS_PATH)

from romutil import load_prg, load_dat, u32
from lzss import compress, decompress

ORIG_ROM_PATH = os.path.join(BASE_DIR, "Super-Dragon-Force_Super-Acan_ZH-TW", "16007 (Taiwan).bin")
ORIG_DAT_PATH = os.path.join(BASE_DIR, "Super-Dragon-Force_Super-Acan_ZH-TW", "08002 (Taiwan).bin")
BUILD_DIR = os.path.join(BASE_DIR, "build")
OUT_ROM_PATH = os.path.join(BUILD_DIR, "Super-Dragon-Force_EN.bin")
OUT_DAT_PATH = os.path.join(BUILD_DIR, "Super-Dragon-Force_DAT_EN.bin")
OUT_IPS_PATH = os.path.join(BUILD_DIR, "Super-Dragon-Force_EN.ips")
OUT_DAT_IPS_PATH = os.path.join(BUILD_DIR, "Super-Dragon-Force_DAT_EN.ips")
CHECKSUMS_PATH = os.path.join(BUILD_DIR, "checksums.txt")

CONTROL_TAGS = {
    "{HERO}": 0x8000,
    "{NUM1}": 0x8001,
    "{CHAR1}": 0x8002,
    "{CHAR2}": 0x8003,
    "{GOLD}": 0x8004,
    "{PARTY}": 0x8005,
    "{CHAR3}": 0x8006,
    "{ITEM}": 0x8007,
    "{SPELL}": 0x8008,
    "{NUM2}": 0x800A,
    "{END}": 0xFFFF,
}

TAG_TILE_COUNT = {
    "{HERO}": 2,   # 'Sam ' = 2 tiles (4 chars)
    "{NUM1}": 1,   # 1 tile (2 chars)
    "{CHAR1}": 3,  # 3 tiles (6 chars)
    "{CHAR2}": 3,  # 3 tiles (6 chars)
    "{GOLD}": 1,   # 1 tile (2 chars)
    "{PARTY}": 3,  # 3 tiles (6 chars)
    "{CHAR3}": 3,  # 3 tiles (6 chars)
    "{ITEM}": 3,   # 3 tiles (6 chars)
    "{SPELL}": 3,  # 3 tiles (6 chars)
    "{NUM2}": 1,   # 1 tile (2 chars)
}

# ── Dialogue layout ──────────────────────────────────────────────────────────
# The game positions text purely by tile index (each 16x16 tile holds two 8px ASCII glyphs).
# Each message renderer installs its own index->position layout (found in the Forth code):
#   w_102d4 "dialogue": 16 tiles on line 1, then 15 per line (page = 46, then 45)
#   w_1b6e0 "narrow":   12 tiles per line (system messages, naming/options screen)
#   w_2df4c "battle":   16 tiles per line
# English is word-wrapped here at build time, and each line is ended with the NEWLINE
# control code (0x800B, implemented by the engine patch below), so variable-length
# names/items inserted by tags can never push the following text out of alignment.
NEWLINE = 0x800B

LAYOUTS = {
    "dialogue": [16, 15],   # first line, then all following lines
    "narrow":   [12, 12],
    "battle":   [16, 16],
}

# Worst-case width (in tiles) of each runtime substitution. Lines are packed assuming the
# longest possible value, so a substituted name can never overflow its line.
TAG_MAX_TILES = {
    "{HERO}": 3,   # player-chosen name, up to 5 characters
    "{CHAR1}": 8,  # character/monster names, up to 16 characters ("Five-Head Dragon")
    "{CHAR2}": 8,
    "{CHAR3}": 8,
    "{PARTY}": 8,
    "{ITEM}": 7,   # up to 14 characters ("Gatling Cannon")
    "{SPELL}": 5,  # up to 10 characters ("Antidote 1")
    "{NUM1}": 3,
    "{GOLD}": 3,
    "{NUM2}": 3,
}

def layout_for_message(msg_id: int, block: int) -> str:
    """Which renderer displays this message (traced from the callers of each renderer)."""
    if block == 0:
        return "narrow"                       # w_1b8b4 is called with ids 5..21
    if msg_id in (1756, 1757, 1758):
        return "narrow"                       # naming / options screen (0x6dc..0x6de)
    if 1710 <= msg_id <= 1763:
        return "battle"                       # battle messages via w_2e10c
    return "dialogue"                         # NPC dialogue, 1700-1704, endings 1764+

def _units(token: str) -> list[str]:
    """Split a word into characters and {TAG}s."""
    out = []
    for part in re.split(r"(\{[A-Z0-9]+\})", token):
        if not part:
            continue
        if part in CONTROL_TAGS:
            out.append(part)
        else:
            out.extend(part)
    return out

def _pack(units: list[str]) -> tuple[list[int], int]:
    """Pack characters two-per-tile; tags must start on a tile boundary. Returns (words, est. tiles)."""
    words, tiles, pending = [], 0, None
    for u in units:
        if u in CONTROL_TAGS:
            if pending is not None:
                words.append((ord(pending) << 8) | 0x20); tiles += 1; pending = None
            words.append(CONTROL_TAGS[u]); tiles += TAG_MAX_TILES.get(u, 3)
        elif pending is None:
            pending = u
        else:
            words.append((ord(pending) << 8) | ord(u)); tiles += 1; pending = None
    if pending is not None:
        words.append((ord(pending) << 8) | 0x20); tiles += 1
    return words, tiles

def _join(tokens: list[list[str]]) -> list[str]:
    out = []
    for i, t in enumerate(tokens):
        if i:
            out.append(" ")
        out.extend(t)
    return out

def encode_dialogue_lines(text: str, layout: str = "dialogue") -> list[int]:
    """Word-wrap English text for the given renderer layout and encode it."""
    text = (text.replace("—", "-").replace("–", "-")
                .replace("“", '"').replace("”", '"')
                .replace("‘", "'").replace("’", "'")
                .replace("…", "..."))
    tokens = [_units(t) for t in re.split(r"\s+", text.strip()) if t]
    if not tokens:
        return []
    first_cap, cap = LAYOUTS[layout]

    lines: list[list[list[str]]] = []
    current: list[list[str]] = []
    for tok in tokens:
        width = first_cap if not lines else cap
        if _pack(_join(current + [tok]))[1] <= width:
            current.append(tok)
            continue
        if current:
            lines.append(current)
            current = []
            width = cap
        # A single word longer than a whole line has to be split.
        while _pack(tok)[1] > width:
            cut = len(tok)
            while cut > 1 and _pack(tok[:cut])[1] > width:
                cut -= 1
            lines.append([tok[:cut]])
            tok = tok[cut:]
            width = cap
        current = [tok]
    if current:
        lines.append(current)

    words: list[int] = []
    for i, line in enumerate(lines):
        w, tiles = _pack(_join(line))
        words.extend(w)
        if i == len(lines) - 1:
            break
        has_tag = any(u in CONTROL_TAGS for t in line for u in t)
        full = tiles == (first_cap if i == 0 else cap)
        if has_tag or not full:
            words.append(NEWLINE)   # engine advances to the start of the next line/page
    return words

def build_unified_text_engine(rom: bytearray):
    """Install native m68k GET_GLYPH_ADDR primitive at 0x000200 and patch w_c428 and w_be88."""
    # GET_GLYPH_ADDR native machine code (58 bytes)
    # Contract: ( char_code -- glyph_address )
    # TOS is replaced with the address of 30 bytes of 1bpp 16x16 bitmap.
    # If char_code < 0x800: returns 0x3e290 + char_code * 30 (Chinese font in ROM)
    # If char_code >= 0x800: unpacks (c1, c2), synthesizes 15 rows of 16-bit words into 0xFFE400, returns 0xFFE400.
    asm_bytes = bytearray([
        0x20, 0x16,                         # move.l (a6), d0
        0x0c, 0x80, 0x00, 0x00, 0x08, 0x00, # cmpi.l #0x800, d0
        0x64, 0x12,                         # bcc.b .is_ascii (offset +18 -> 0x000220)
        # Chinese (< 0x800):
        0xc0, 0xfc, 0x00, 0x1e,             # mulu.w #30, d0
        0x06, 0x80, 0x00, 0x03, 0xe2, 0x90, # addi.l #0x3e290, d0
        0x2c, 0x80,                         # move.l d0, (a6)
        0x2a, 0x5c,                         # movea.l (a4)+, a5
        0x20, 0x55,                         # movea.l (a5), a0
        0x4e, 0xd0,                         # jmp (a0)
        # .is_ascii: (0x000220)
        0x22, 0x00,                         # move.l d0, d1
        0xe0, 0x49,                         # lsr.w #8, d1
        0x02, 0x41, 0x00, 0x7f,             # andi.w #0x7f, d1
        0x02, 0x40, 0x00, 0x7f,             # andi.w #0x7f, d0
        0xe9, 0x49,                         # lsl.w #4, d1
        0xe9, 0x48,                         # lsl.w #4, d0
        0x41, 0xf9, 0x00, 0x03, 0xd2, 0x90, # lea 0x3d290.l, a0
        0x43, 0xf0, 0x10, 0x00,             # lea (a0, d1.w), a1
        0x45, 0xf0, 0x00, 0x00,             # lea (a0, d0.w), a2
        0x47, 0xf9, 0x00, 0xff, 0xe4, 0x00, # lea 0xffe400.l, a3
        0x74, 0x0e,                         # moveq #14, d2
        # .loop: (0x000246)
        0x16, 0xd9,                         # move.b (a1)+, (a3)+
        0x16, 0xda,                         # move.b (a2)+, (a3)+
        0x51, 0xca, 0xff, 0xfa,             # dbra d2, .loop (-6 bytes -> 0x000246)
        0x2c, 0xbc, 0x00, 0xff, 0xe4, 0x00, # move.l #0xffe400, (a6)
        0x2a, 0x5c,                         # movea.l (a4)+, a5
        0x20, 0x55,                         # movea.l (a5), a0
        0x4e, 0xd0                          # jmp (a0)
    ])

    # Write Forth primitive word at 0x000200: CFA points to 0x000204
    rom[0x000200:0x000204] = struct.pack(">I", 0x000204)
    rom[0x000204:0x000204 + len(asm_bytes)] = asm_bytes

    # Patch w_c428 (dialogue/message character blitter)
    # Replace: LIT 0x1e (8b), w_784 (4b), LIT 0x3e290 (8b), + (4b) = 24 bytes (0x00c42c..0x00c444)
    # With: GET_GLYPH_ADDR (0x000200), BRANCH (0x0005a4), offset 0x00000010, pad with zeros
    c428_patch = struct.pack(">6I", 0x000200, 0x0005a4, 0x00000010, 0x00000000, 0x00000000, 0x00000000)
    rom[0x00c42c:0x00c42c + len(c428_patch)] = c428_patch

    # Patch w_be88 (button/menu label character blitter)
    # Replace: LIT 0x1e (8b), w_784 (4b), LIT 0x3e290 (8b), + (4b) = 24 bytes (0x00bef8..0x00bf10)
    # With: GET_GLYPH_ADDR (0x000200), BRANCH (0x0005a4), offset 0x00000010, pad with zeros
    be88_patch = struct.pack(">6I", 0x000200, 0x0005a4, 0x00000010, 0x00000000, 0x00000000, 0x00000000)
    rom[0x00bef8:0x00bef8 + len(be88_patch)] = be88_patch

    install_newline_code(rom)
    print(f"  [+] Installed GET_GLYPH_ADDR at 0x000200 and patched w_c428 and w_be88")


def install_newline_code(rom: bytearray):
    """Add a NEWLINE text control code (0x800B) to the dialogue engine.

    NEWLINE_N (native primitive at 0x000260) pushes the number of tiles left on the current
    line, using the active layout (vector at $FFEFC8) and tile index ($FFEF3E). The tag
    handler w_10834 ends in a DROP for unknown codes; that DROP is replaced by TAGX, which
    handles 0x800B by calling w_10408 (the active "advance N tiles" vector, which also runs
    the game's own end-of-page pause/clear) and DROPs anything else as before.
    """
    DOCOL, LIT, OF, DROP, EXIT = 0x00049C, 0x000510, 0x0005C8, 0x000BD0, 0x0005E4
    W_ADVANCE = 0x010408
    IDX_VAR, LAYOUT_VAR = 0xFFEF3E, 0xFFEFC8
    LAYOUT_DIALOGUE, LAYOUT_NARROW = 0x0102D4, 0x01B6E0

    code = bytearray()
    code += struct.pack(">HI", 0x2039, IDX_VAR)          # 264 move.l IDX,d0
    code += struct.pack(">HI", 0x2239, LAYOUT_VAR)       # 26a move.l LAYOUT,d1
    code += bytes.fromhex("7410")                        # 270 moveq #16,d2
    code += struct.pack(">HI", 0x0C81, LAYOUT_DIALOGUE)  # 272 cmpi.l #dialogue,d1
    code += bytes.fromhex("6612")                        # 278 bne.b  fixed (28c)
    code += struct.pack(">HI", 0x0C80, 16)               # 27a cmpi.l #16,d0
    code += bytes.fromhex("6514")                        # 280 bcs.b  div (296)   line 1: 16 wide
    code += struct.pack(">HI", 0x0480, 16)               # 282 subi.l #16,d0
    code += bytes.fromhex("740F")                        # 288 moveq #15,d2       later lines: 15
    code += bytes.fromhex("600A")                        # 28a bra.b  div (296)
    code += struct.pack(">HI", 0x0C81, LAYOUT_NARROW)    # 28c fixed: cmpi.l #narrow,d1
    code += bytes.fromhex("6602")                        # 292 bne.b  div (296)
    code += bytes.fromhex("740C")                        # 294 moveq #12,d2
    code += bytes.fromhex("80C2")                        # 296 div: divu.w d2,d0
    code += bytes.fromhex("4840")                        # 298 swap d0            remainder
    code += bytes.fromhex("7200")                        # 29a moveq #0,d1
    code += bytes.fromhex("3200")                        # 29c move.w d0,d1
    code += bytes.fromhex("6706")                        # 29e beq.b  zero (2a6) already at line start
    code += bytes.fromhex("9481")                        # 2a0 sub.l d1,d2        N = width - pos
    code += bytes.fromhex("2D02")                        # 2a2 move.l d2,-(a6)
    code += bytes.fromhex("6002")                        # 2a4 bra.b  next (2a8)
    code += bytes.fromhex("42A6")                        # 2a6 zero: clr.l -(a6)
    code += bytes.fromhex("2A5C20554ED0")                # 2a8 NEXT
    NEWLINE_N = 0x000260
    assert len(code) == 0x2AE - 0x264
    rom[NEWLINE_N:NEWLINE_N + 4] = struct.pack(">I", NEWLINE_N + 4)
    rom[NEWLINE_N + 4:NEWLINE_N + 4 + len(code)] = code

    TAGX = 0x0002C0
    thread = [DOCOL, LIT, NEWLINE, OF, 0x10, NEWLINE_N, W_ADVANCE, EXIT, DROP, EXIT]
    rom[TAGX:TAGX + 4 * len(thread)] = struct.pack(f">{len(thread)}I", *thread)

    assert struct.unpack_from(">I", rom, 0x0109B4)[0] == DROP, "unexpected w_10834 layout"
    rom[0x0109B4:0x0109B8] = struct.pack(">I", TAGX)
    print("  [+] Installed NEWLINE control code (0x800B) at 0x000260 / tag handler 0x0002c0")

def build_short_strings(rom: bytearray):
    """Rebuild short string table and data at 0x045000 and update pointers."""
    strings_file = os.path.join(BASE_DIR, "notes", "short_strings_en.json")
    with open(strings_file, "r", encoding="utf-8") as f:
        strings = json.load(f)

    # Place short strings at 0x04d5f4 (start of original dialogue area, safely after
    # the 6502 sound driver at 0x04cc1e..0x04d5f4 and Chinese font at 0x03e290..0x04cc1e).
    NEW_STRINGS_ADDR = 0x04d5f4
    FREE_END = 0x05b496   # start of the last original (now unused) Chinese dialogue block

    # Short place names for the save/load slot list are appended after the regular strings,
    # so the location banner and the dialogue keep the full names (see save_screen_places.json).
    PLACE_FIRST = 0x01d
    save_names = json.load(open(os.path.join(BASE_DIR, "notes", "save_screen_places.json"), encoding="utf-8"))["names"]
    place_count = 0x049 - PLACE_FIRST
    extra = [{"en": save_names.get(f"{PLACE_FIRST + n:#05x}", strings[PLACE_FIRST + n].get("en", ""))}
             for n in range(place_count)]
    save_base_index = len(strings)               # JSON index of the first appended string
    strings = strings + extra
    # Extra label for the church menu: "$" instead of "Cash" (see patch_menu_layouts).
    global DOLLAR_STRING_ID
    DOLLAR_STRING_ID = len(strings) + 1          # string ids are JSON index + 1
    strings = strings + [{"en": "$"}]

    base_table_size = (len(strings) + 2) * 2

    offsets = [0]
    data = bytearray()
    for s in strings:
        offsets.append(base_table_size + len(data))
        en = s.get("en", "")
        if en:
            chars = list(en)
            if len(chars) % 2 != 0:
                chars.append(" ")
            for i in range(0, len(chars), 2):
                w = (ord(chars[i]) << 8) | ord(chars[i+1])
                data += struct.pack(">H", w)

    # Sentinel for the end of the last string
    offsets.append(base_table_size + len(data))
    assert len(offsets) == len(strings) + 2, f"Expected {len(strings) + 2} offsets, got {len(offsets)}"
    assert offsets[-1] < 0x10000, "string table exceeds 16-bit offsets"
    blob = struct.pack(f">{len(offsets)}H", *offsets) + data
    if NEW_STRINGS_ADDR + len(blob) > FREE_END:
        raise RuntimeError(f"Short strings overflow free space ({len(blob)} bytes)")
    rom[NEW_STRINGS_ADDR:NEW_STRINGS_ADDR + len(blob)] = blob

    # Point the save/load slot list (w_270f8: LIT 0x1e) at the appended short place names.
    # String ids are JSON index + 1, and the code adds the place number to the base id.
    SAVE_LIT = 0x0271ac
    assert struct.unpack_from(">II", rom, SAVE_LIT - 4) == (0x000510, 0x1e), "unexpected w_270f8 layout"
    rom[SAVE_LIT:SAVE_LIT + 4] = struct.pack(">I", save_base_index + 1)

    # Patch the 9 occurrences of 0x05cc22 to NEW_STRINGS_ADDR
    targets = [
        0x00a2e8, 0x00a300, 0x00a324,
        0x00bb24, 0x00bb3c, 0x00bb60,
        0x00be14, 0x00be3c, 0x00be60
    ]
    for t in targets:
        rom[t:t+4] = struct.pack(">I", NEW_STRINGS_ADDR)

    print(f"  [+] Installed {len(strings)} short strings at 0x{NEW_STRINGS_ADDR:06x} ({len(blob)} bytes)")

def build_dialogue_blocks(rom: bytearray, dat_rom: bytearray):
    """Rebuild, compress, and install dialogue blocks into free space at 0x0e58c0 in DAT ROM (0x2e58c0 68k space)."""
    en_path = os.path.join(BASE_DIR, "notes", "dialogue_en.json")
    zh_path = os.path.join(BASE_DIR, "notes", "dialogue_zh.json")
    has_en = os.path.exists(en_path)

    with open(zh_path, "r", encoding="utf-8") as f:
        zh_data = json.load(f)

    en_data_by_id = {}
    if has_en:
        with open(en_path, "r", encoding="utf-8") as f:
            for item in json.load(f):
                en_data_by_id[item["id"]] = item

    # DAT ROM base in 68000 address space is 0x200000.
    # The last 108,364 bytes of 08002 (0x0e58b4..0x100000) are unused 0xFF.
    DAT_START_OFFSET = 0x0e58c0
    current_offset = DAT_START_OFFSET
    ptrs = []

    for block_num in range(18):
        block_items = [d for d in zh_data if d["block"] == block_num]
        by_index = {d["index"]: d for d in block_items}

        header_size = 100 * 8
        body = bytearray()
        headers = []

        for idx in range(100):
            if idx in by_index:
                d = by_index[idx]
                d_id = d["id"]
                en_item = en_data_by_id.get(d_id)
                en_text = en_item.get("en", "").strip() if en_item else ""

                if en_text:
                    words = encode_dialogue_lines(en_text, layout_for_message(d_id, block_num))
                else:
                    words = d["words"]

                offset = header_size + len(body)
                word_count = len(words)
                portrait = d["portrait"]
                body += struct.pack(f">{word_count}H", *words)
            else:
                offset = 0
                word_count = 0xffff
                portrait = 0xffff
            headers.append(struct.pack(">IHH", offset, word_count, portrait))

        uncompressed = b"".join(headers) + body
        if len(uncompressed) > 16384:
            raise RuntimeError(f"Dialogue block {block_num} uncompressed size {len(uncompressed)} exceeds 16KB WRAM buffer (16384 bytes)!")
        compressed = compress(uncompressed)

        # Ensure word alignment
        if len(compressed) % 2 != 0:
            compressed += b"\xff"

        # Check for overflow in DAT ROM
        if current_offset + len(compressed) > len(dat_rom):
            raise RuntimeError(f"Dialogue blocks overflowed DAT ROM at block {block_num}!")

        # Write compressed block into dat_rom
        dat_rom[current_offset:current_offset + len(compressed)] = compressed
        # 68000 CPU pointer: 0x200000 + offset
        ptrs.append(0x200000 + current_offset)
        current_offset += len(compressed)

    # Update pointer table at 0x0107EC in PRG ROM
    for i, p in enumerate(ptrs):
        rom[0x0107ec + i*4 : 0x0107ec + (i+1)*4] = struct.pack(">I", p)

    print(f"  [+] Compressed & installed 18 dialogue blocks in DAT ROM at 0x{DAT_START_OFFSET:06x}..0x{current_offset:06x} (CPU: 0x{0x200000+DAT_START_OFFSET:06x}..0x{0x200000+current_offset:06x}) ({current_offset - DAT_START_OFFSET} bytes)")

def patch_name_selection_and_defaults(rom: bytearray):
    """Patch name selection character grid to English alphabet and default names to 'Sam'."""
    # 0x05E0A0 table structure (each entry 8 bytes: offset u32, word_count u16, reserved u16):
    # Entries 0..11: Character pages (18 cols x 6 rows = 108 words per page)
    # Entry 12: Male default name
    # Entry 13: Female default name
    GRID_ADDR = 0x05E110
    MALE_NAME_ADDR = 0x05EB0C
    FEMALE_NAME_ADDR = 0x05EB12

    # 1. 108-slot English alphabet grid
    grid_rows = [
        "ABCDEFGHIJKLMNOPQR",
        "STUVWXYZ.,!?-/:'\" ",
        "abcdefghijklmnopqr",
        "stuvwxyz0123456789",
        "()[]<>&@#$%+=*~_  ",
        "                  ",
    ]
    grid_chars = "".join(grid_rows)
    assert len(grid_chars) == 108, f"Grid length must be 108, got {len(grid_chars)}"

    grid_words = [(ord(ch) << 8) | 0x20 for ch in grid_chars]
    grid_blob = struct.pack(">108H", *grid_words)
    rom[GRID_ADDR:GRID_ADDR + len(grid_blob)] = grid_blob

    # 2. Default name "Sam " (2 words: 'Sa', 'm ')
    # 2 words = 4 characters, matching TAG_ESTIMATED_LENGTHS["{HERO}"] = 4
    sam_blob = struct.pack(">2H", (ord('S') << 8) | ord('a'), (ord('m') << 8) | 0x20)
    rom[MALE_NAME_ADDR:MALE_NAME_ADDR + len(sam_blob)] = sam_blob
    rom[FEMALE_NAME_ADDR:FEMALE_NAME_ADDR + len(sam_blob)] = sam_blob

    # 3. Update table entries at 0x05E0A0
    for i in range(12):
        rom[0x05E0A0 + i*8 : 0x05E0A0 + (i+1)*8] = struct.pack(">IHH", GRID_ADDR - 0x05E0A0, 108, 0)

    # Male default name (idx 12)
    rom[0x05E0A0 + 12*8 : 0x05E0A0 + 13*8] = struct.pack(">IHH", MALE_NAME_ADDR - 0x05E0A0, 2, 0)
    # Female default name (idx 13)
    rom[0x05E0A0 + 13*8 : 0x05E0A0 + 14*8] = struct.pack(">IHH", FEMALE_NAME_ADDR - 0x05E0A0, 2, 0)

    print(f"  [+] Patched English name selection grid and default name 'Sam' at 0x{GRID_ADDR:06x}")

def patch_title_screen_buttons(rom: bytearray):
    """Patch title screen menu buttons to English (START, OPTIONS, CONTINUE)."""
    from PIL import Image, ImageDraw, ImageFont
    import numpy as np

    MAP_ADDR = 0x18ac06
    TILES_ADDR = 0x18ae12
    TILES_END = 0x18bb9c

    dec_map, _ = decompress(rom, MAP_ADDR)
    dec_tiles, _ = decompress(rom, TILES_ADDR)

    font_path = "/System/Library/Fonts/Supplemental/Arial Black.ttf"

    def make_button(text, font_size):
        W, H = 96, 24
        mask = Image.new("L", (W, H), 0)
        draw = ImageDraw.Draw(mask)
        font = ImageFont.truetype(font_path, font_size)
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        tx = (W - tw) // 2 - bbox[0]
        ty = (H - th) // 2 - bbox[1] - 1
        draw.text((tx, ty), text, fill=255, font=font)

        outline_mask = Image.new("L", (W, H), 0)
        odraw = ImageDraw.Draw(outline_mask)
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx != 0 or dy != 0:
                    odraw.text((tx + dx, ty + dy), text, fill=255, font=font)

        arr_text = np.array(mask)
        arr_out = np.array(outline_mask)
        idx_img = np.zeros((H, W), dtype=np.uint8)

        for y in range(H):
            for x in range(W):
                if arr_text[y, x] > 100:
                    rel_y = (y - 3) / 18.0
                    if rel_y < 0.2: val = 143
                    elif rel_y < 0.4: val = 142
                    elif rel_y < 0.65: val = 140
                    elif rel_y < 0.85: val = 138
                    else: val = 136
                    idx_img[y, x] = val
                elif arr_out[y, x] > 80:
                    idx_img[y, x] = 130
                elif arr_out[y, x] > 20:
                    idx_img[y, x] = 128
        return idx_img

    btn_start = make_button("START", 15)
    btn_opt = make_button("OPTIONS", 14)
    btn_cont = make_button("CONTINUE", 13)

    def to_tiles(arr):
        tiles = []
        for r in range(3):
            for c in range(12):
                tile = bytearray(64)
                for py in range(8):
                    for px in range(8):
                        tile[py * 8 + px] = arr[r * 8 + py, c * 8 + px]
                tiles.append(tile)
        return tiles

    tiles_start = to_tiles(btn_start)
    tiles_opt = to_tiles(btn_opt)
    tiles_cont = to_tiles(btn_cont)

    new_tiles = bytearray(dec_tiles)
    for i, t in enumerate(tiles_start):
        off = 25 * 64 + i * 64
        new_tiles[off:off+64] = t

    for i, t in enumerate(tiles_cont):
        off = 61 * 64 + i * 64
        new_tiles[off:off+64] = t

    for i, t in enumerate(tiles_opt):
        off = 97 * 64 + i * 64
        new_tiles[off:off+64] = t

    words = list(struct.unpack(f">{len(dec_map)//2}H", dec_map))

    # START (unselected: 184..219, selected: 292..327)
    for i in range(36):
        words[184 + i] = 25 + i
        words[292 + i] = 25 + i

    # CONTINUE (unselected: 220..255, selected: 328..363)
    for i in range(36):
        words[220 + i] = 61 + i
        words[328 + i] = 61 + i

    # OPTIONS (unselected: 256..291, selected: 364..399)
    for i in range(36):
        words[256 + i] = 97 + i
        words[364 + i] = 97 + i

    new_map = struct.pack(f">{len(words)}H", *words)

    comp_map = compress(new_map)
    comp_tiles = compress(new_tiles)

    map_space = TILES_ADDR - MAP_ADDR
    assert len(comp_map) <= map_space, f"comp_map {len(comp_map)} > {map_space}"
    rom[MAP_ADDR:MAP_ADDR + len(comp_map)] = comp_map
    rom[MAP_ADDR + len(comp_map):TILES_ADDR] = b"\xff" * (map_space - len(comp_map))

    tiles_space = TILES_END - TILES_ADDR
    assert len(comp_tiles) <= tiles_space, f"comp_tiles {len(comp_tiles)} > {tiles_space}"
    rom[TILES_ADDR:TILES_ADDR + len(comp_tiles)] = comp_tiles
    rom[TILES_ADDR + len(comp_tiles):TILES_END] = b"\xff" * (tiles_space - len(comp_tiles))

    # Set default title menu selection to 0 (START GAME) instead of 1 (CONTINUE)
    # Forth w_3bd28 at 0x03bd6c (LIT 0x00000510, value at 0x03bd70): LIT 1 -> LIT 0
    rom[0x03bd70:0x03bd74] = struct.pack(">I", 0)

    print(f"  [+] Patched English title screen buttons (START, CONTINUE, OPTIONS) at 0x{MAP_ADDR:06x}/0x{TILES_ADDR:06x}")
    print(f"  [+] Set default title menu cursor selection to START (0)")

def apply_ips(orig_data: bytes, patch: bytes) -> bytes:
    """Apply an IPS patch (used to verify the patches we ship)."""
    assert patch[:5] == b"PATCH"
    out = bytearray(orig_data); pos = 5
    while patch[pos:pos + 3] != b"EOF":
        off = int.from_bytes(patch[pos:pos + 3], "big"); size = int.from_bytes(patch[pos + 3:pos + 5], "big"); pos += 5
        if size == 0:  # RLE record
            run = int.from_bytes(patch[pos:pos + 2], "big"); out[off:off + run] = patch[pos + 2:pos + 3] * run; pos += 3
        else:
            out[off:off + size] = patch[pos:pos + size]; pos += size
    return bytes(out)

def create_ips_patch(orig_data: bytes, patched_data: bytes, out_path: str):
    """Create a standard IPS patch file and verify it reproduces the patched data."""
    assert len(orig_data) == len(patched_data)
    assert len(orig_data) <= 0x1000000, "IPS offsets are 24-bit"
    patch = bytearray(b"PATCH")
    i = 0
    n = len(orig_data)
    while i < n:
        if orig_data[i] == patched_data[i]:
            i += 1
            continue
        start = i
        while i < n and (orig_data[i] != patched_data[i] or (i + 1 < n and orig_data[i+1] != patched_data[i+1])):
            if i - start >= 65535:
                break
            i += 1
        # Offset 0x454F46 spells "EOF" and would end the patch early; start the record 1 byte sooner.
        if start == 0x454F46:
            start -= 1
        length = i - start
        # Write record: 3-byte offset, 2-byte size, data
        patch += struct.pack(">BH", start >> 16, start & 0xFFFF)
        patch += struct.pack(">H", length)
        patch += patched_data[start:start + length]
    patch += b"EOF"

    if apply_ips(orig_data, bytes(patch)) != bytes(patched_data):
        raise SystemExit(f"[!] IPS self-test failed for {out_path}")
    with open(out_path, "wb") as f:
        f.write(patch)
    print(f"  [+] Created IPS patch: {out_path} ({len(patch)} bytes, verified)")

DOLLAR_STRING_ID = None

def patch_lit(rom: bytearray, cell: int, expected: int, new: int):
    """Change the value of a Forth `LIT n` whose LIT cell is at `cell`."""
    lit, val = struct.unpack_from(">II", rom, cell)
    assert lit == 0x000510 and val == expected, f"unexpected code at {cell:#08x}: {lit:#x} {val:#x}"
    struct.pack_into(">I", rom, cell + 4, new)

def patch_menu_layouts(rom: bytearray):
    """Fit the English labels of the church and CONTINUE menus inside their boxes.

    The original places every label 5 columns apart, sized for two Chinese characters, and
    'Save' already straddled the box divider in the original. English needs more room, so the
    church menu shows '$' instead of 'Cash' and all labels move into the boxes:
        left box : $ 2120  Heal  Save      right box: Load  Erase  Exit
    Columns are 8-pixel units; the left box holds columns 2-18, the right box 21-38.
    """
    # Church: w_26510        cell      old    new
    patch_lit(rom, 0x026528, 0x1b5, DOLLAR_STRING_ID)   # "Cash" -> "$"
    for cell, old, new in [(0x026534, 0x06, 0x03),   # amount
                           (0x026550, 0x0d, 0x09),   # Heal
                           (0x026570, 0x12, 0x0e),   # Save
                           (0x026590, 0x17, 0x16),   # Load
                           (0x0265b0, 0x1c, 0x1b),   # Erase
                           (0x0265d0, 0x21, 0x21)]:  # Exit (unchanged)
        patch_lit(rom, cell, old, new)
    # CONTINUE screen: w_21e38
    for cell, old, new in [(0x021e3c, 0x17, 0x16), (0x021e5c, 0x1c, 0x1b), (0x021e7c, 0x21, 0x21)]:
        patch_lit(rom, cell, old, new)
    # The green cursor highlight reads its own positions from a table shared by both menus
    # (cf_4b4_26c84, data at $26C88): {x, y} words for Exit, Erase, Load, Save, Heal, with
    # x = (label column + 1) * 8. Keep it in step with the labels above.
    HIGHLIGHT = 0x026C88
    for i, (old_col, new_col) in enumerate([(0x21, 0x21), (0x1c, 0x1b), (0x17, 0x16), (0x12, 0x0e), (0x0d, 0x09)]):
        x_old = struct.unpack_from(">H", rom, HIGHLIGHT + i * 4)[0]
        assert x_old == (old_col + 1) * 8, f"unexpected highlight table entry {i}: {x_old:#x}"
        struct.pack_into(">H", rom, HIGHLIGHT + i * 4, (new_col + 1) * 8)
    # Save/load record list (w_270f8): number / hero name / place / time. Originally the place
    # straddled the box divider. Hero names are at most 5 letters, so the left box holds the
    # record number (3-wide right-aligned field at 1, digit in column 3), the name (5-9) and an
    # 8-letter place (11-18); the time is centred in the right box (25-32).
    for cell, old, new in [(0x027124, 0x02, 0x01),   # record number field
                           (0x027160, 0x06, 0x05),   # hero name
                           (0x0271e4, 0x06, 0x05),   # "<EMPTY>"
                           (0x027188, 0x11, 0x0b),   # place
                           (0x0271b8, 0x1c, 0x19)]:  # time
        patch_lit(rom, cell, old, new)
    # Its row highlight (SELECT_SRAM_FILE, 32 px wide) sits at x = 3 * 8; start it inside the frame.
    patch_lit(rom, 0x0268b0, 0x03, 0x02)
    print("  [+] Fitted church / CONTINUE menu labels inside their boxes")

def write_checksums(files: dict):
    import hashlib, zlib
    lines = []
    for name, data in files.items():
        lines.append(f"{name}\n  size  {len(data)}\n  crc32 {zlib.crc32(data) & 0xFFFFFFFF:08x}\n"
                     f"  sha1  {hashlib.sha1(data).hexdigest()}\n")
    with open(CHECKSUMS_PATH, "w") as f:
        f.write("\n".join(lines))
    print(f"  [+] Wrote {CHECKSUMS_PATH}")

def main():
    print("[*] Building English Super Dragon Force ROM...")
    os.makedirs(BUILD_DIR, exist_ok=True)

    # 1. Load clean PRG ROM (Big-Endian un-swapped) and DAT ROM
    prg = bytearray(load_prg())
    print(f"  [+] Loaded clean PRG ROM ({len(prg)} bytes)")

    # The DAT dump is stored byte-swapped like the PRG dump; patch it in 68k order.
    dat = bytearray(load_dat(swapped=True))
    print(f"  [+] Loaded clean DAT ROM ({len(dat)} bytes)")

    # 2. Text Engine
    build_unified_text_engine(prg)

    # 3. Short Strings (at 0x04d5f4 in PRG ROM)
    build_short_strings(prg)

    # 4. Dialogue Blocks (at 0x0e58c0 in DAT ROM)
    build_dialogue_blocks(prg, dat)

    patch_menu_layouts(prg)

    # 5. Name Selection & Default Names
    patch_name_selection_and_defaults(prg)

    # 6. Title Screen Menu Buttons
    patch_title_screen_buttons(prg)

    # 7. Byte-swap 16-bit words for MAME / console format
    mame_rom = bytearray(len(prg))
    for i in range(0, len(prg), 2):
        mame_rom[i] = prg[i+1]
        mame_rom[i+1] = prg[i]

    # Save output PRG ROM
    with open(OUT_ROM_PATH, "wb") as f:
        f.write(mame_rom)
    print(f"  [+] Saved patched PRG ROM: {OUT_ROM_PATH} ({len(mame_rom)} bytes)")

    # Save output DAT ROM (swapped back to the dump's byte order)
    mame_dat = bytearray(len(dat))
    mame_dat[0::2], mame_dat[1::2] = dat[1::2], dat[0::2]
    with open(OUT_DAT_PATH, "wb") as f:
        f.write(mame_dat)
    print(f"  [+] Saved patched DAT ROM: {OUT_DAT_PATH} ({len(dat)} bytes)")

    # 8. Create IPS patch from original clean PRG ROM dump
    with open(ORIG_ROM_PATH, "rb") as f:
        orig_raw = f.read()
    create_ips_patch(orig_raw, mame_rom, OUT_IPS_PATH)
    with open(ORIG_DAT_PATH, "rb") as f:
        orig_dat_raw = f.read()
    create_ips_patch(orig_dat_raw, mame_dat, OUT_DAT_IPS_PATH)
    write_checksums({
        "16007 (Taiwan).bin  (original program ROM - patch with Super-Dragon-Force_EN.ips)": orig_raw,
        "08002 (Taiwan).bin  (original data ROM - patch with Super-Dragon-Force_DAT_EN.ips)": orig_dat_raw,
        "Super-Dragon-Force_EN.bin  (patched program ROM)": bytes(mame_rom),
        "Super-Dragon-Force_DAT_EN.bin  (patched data ROM)": bytes(mame_dat),
    })

    import check_wrap
    if check_wrap.main() != 0:
        raise SystemExit("[!] Dialogue word-wrap check failed (see above)")

    # Short strings (names/items/menus) vs. the width of the fields that display them,
    # and place names: one canonical name each, abbreviations only on the save screen.
    import check_strings, io
    naming = check_strings.check_save_screen(json.load(open(os.path.join(BASE_DIR, "notes", "short_strings_en.json"), encoding="utf-8"))) \
        + check_strings.check_dialogue_names()
    if naming:
        print("\n".join("  ! " + n for n in naming))
        raise SystemExit("[!] Place-name consistency check failed")
    strict = "--strict" in sys.argv
    errors, warnings = check_strings.check(json.load(open(os.path.join(BASE_DIR, "notes", "short_strings_en.json"), encoding="utf-8")))
    with open(os.path.join(BUILD_DIR, "string_report.txt"), "w") as f:
        check_strings.report(errors, warnings, f)
    if errors or warnings:
        print(f"[!] {len(errors)} short strings are cut off on screen, {len(warnings)} more if equippable "
              f"(details: build/string_report.txt)")
        if errors and strict:
            raise SystemExit("[!] --strict: short strings must fit their on-screen fields")
    print("[*] Build completed successfully!")

if __name__ == "__main__":
    main()
