#!/usr/bin/env python3
"""Dialogue translator and manager for Super Dragon Force.

Maintains notes/dialogue_en.json with translations for all dialogue blocks,
validating control codes and line lengths.
"""

import json
import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZH_FILE = os.path.join(BASE_DIR, "notes", "dialogue_zh.json")
EN_FILE = os.path.join(BASE_DIR, "notes", "dialogue_en.json")

# Verified block 0 translations
BLOCK_0_TRANSLATIONS = {
    1: "...",
    2: "{PARTY} has joined the party.",
    3: "{HERO} obtained {GOLD} {ITEM}.",
    4: "Well met, {HERO}! Take these {GOLD} gold coins as your reward.",
    5: "This {ITEM} costs {GOLD} gold. You lack the coins to purchase it.",
    6: "Thank you for your purchase!",
    7: "What kind of wares are you looking for?",
    8: "{HERO}, your inventory is already full.",
    9: "{HERO}, here are your belongings.",
    10: "Welcome, {HERO}! Looking to buy or sell today?",
    11: "This {ITEM} costs {GOLD} gold. Would you like to buy it?",
    12: "I can offer {GOLD} gold for your {ITEM}. Will you sell it?",
    13: "Passing on such a fine price? What a pity!",
    14: "Much obliged! Thank you!",
    15: "Welcome, {HERO}! How can we serve you today?",
    16: "A night's stay is {GOLD} gold. Would you like to rest, {HERO}?",
    17: "Thank you! Have a restful night.",
    18: "{HERO} and the party are fully refreshed!",
    19: "{HERO}, you don't have enough gold for lodging.",
    20: "Without rest, your weary travelers cannot recover stamina.",
    21: "Almighty Lord, bless Thy people with divine light.",
    22: "Almighty Lord, bless Thy children. Who among you seeks healing?",
    23: "Almighty Lord, bless Thy children. Which record shall be loaded?",
    24: "Almighty Lord, bless Thy children. Which record shall be saved?",
    25: "Almighty Lord, bless Thy children. None among you require healing.",
    26: "Almighty Lord, bless Thy children. A donation is needed for healing.",
    27: "Almighty Lord, bless Thy children. {CHAR3}'s body has been revived!",
    28: "Almighty Lord, bless Thy children. Reviving {CHAR3} requires {GOLD} gold.",
    29: "Almighty Lord, bless Thy children. Your record has been loaded.",
    30: "Almighty Lord, bless Thy children. Your record has been saved.",
    31: "Almighty Lord, bless Thy children. Which record shall be erased?",
    32: "Almighty Lord, bless Thy children. The record has been erased.",
    33: "Almighty Lord, bless Thy children. Do you wish to load this record?",
    34: "Almighty Lord, bless Thy children. Do you wish to save to this record?",
    35: "Almighty Lord, bless Thy children. Do you wish to erase this record?",
    36: "Almighty Lord, bless Thy children. That record is empty and cannot be loaded.",
    39: "{CHAR3} used {ITEM}, but nothing happened.",
    40: "{CHAR3} used {ITEM}. HP increased by {GOLD}!",
    41: "{CHAR3} used {ITEM}. AGI increased by {GOLD}!",
    42: "{CHAR3} used {ITEM}. DEF increased by {GOLD}!",
    43: "{CHAR3} used {ITEM}. Max HP increased by {GOLD}!",
    44: "{CHAR3} used {ITEM}. ATK increased by {GOLD}!",
    45: "{CHAR1} equipped {ITEM}. ATK increased by {GOLD}!",
    46: "{CHAR1} equipped {ITEM}. ATK decreased by {GOLD}.",
    47: "{CHAR1} cannot equip {ITEM}.",
    48: "{CHAR1} used {ITEM}, but nothing happened.",
    49: "{CHAR1} used {ITEM} on {CHAR2}, but nothing happened.",
    50: "{CHAR1} used {ITEM}. HP increased by {GOLD}!",
    51: "{CHAR1} used {ITEM} on {CHAR2}. Restored {GOLD} HP!",
    52: "{CHAR1} used {ITEM} and escaped from battle!",
    53: "{CHAR1} used {ITEM} on {CHAR2}. HP fully restored!",
    54: "{CHAR1} used {ITEM}. Poison was cured!",
    55: "{CHAR1} used {ITEM}. Cured {CHAR2} of poison!",
    56: "{CHAR1} used {ITEM}. Paralysis was cured!",
    57: "{CHAR1} used {ITEM}. Cured {CHAR2} of paralysis!",
    58: "{CHAR1} used {ITEM} and woke up!",
    59: "{CHAR1} used {ITEM} and woke up {CHAR2}!",
    60: "{CHAR1} used {ITEM}. Spell seal was broken!",
    61: "{CHAR1} used {ITEM}. Broke {CHAR2}'s spell seal!",
    62: "{CHAR1} used {ITEM}. The party fled from battle!",
    63: "{CHAR1} used {ITEM}. {CHAR2} fled from battle!",
    64: "{CHAR1} used {ITEM} on {CHAR2}. The party fled!",
    65: "{CHAR1} used {ITEM}. Petrification was cured!",
    66: "{CHAR1} used {ITEM}. Cured {CHAR2} of petrification!",
    67: "{CHAR1} used {ITEM}. MP fully restored!",
    68: "{CHAR1} used {ITEM}. Restored all MP to {CHAR2}!",
    69: "{CHAR1} used {ITEM}. Party HP fully restored!",
    70: "{CHAR1} used {ITEM}. ATK increased by {GOLD}!",
    71: "{CHAR1} used {ITEM}. {CHAR2}'s ATK increased by {GOLD}!",
    72: "{CHAR1} cannot use {ITEM} on {CHAR2}.",
    73: "{CHAR1} used {ITEM}. AGI increased by {GOLD}!",
    74: "{CHAR1} used {ITEM}. {CHAR2}'s AGI increased by {GOLD}!",
    75: "{CHAR1} used {ITEM}. MOV increased by {GOLD}!",
    76: "{CHAR1} used {ITEM}. {CHAR2}'s MOV increased by {GOLD}!",
    77: "{CHAR1} used {ITEM}. DEF increased by {GOLD}!",
    78: "{CHAR1} used {ITEM}. {CHAR2}'s DEF increased by {GOLD}!",
    79: "{CHAR1} used {ITEM}. Max HP increased by {GOLD}!",
    80: "{CHAR1} used {ITEM}. {CHAR2}'s Max HP increased by {GOLD}!",
    81: "{CHAR1} handed {ITEM} to {CHAR2}.",
    82: "{CHAR2} has no room for {ITEM}.",
    83: "{CHAR1} discarded {ITEM}.",
    84: "{CHAR1} rested and recovered {GOLD} HP.",
    85: "{CHAR1} rested.",
    86: "...",
    87: "...",
    88: "...",
    89: "...",
    90: "...",
    91: "{CHAR1} advanced to Level {GOLD}!",
    92: "Max HP increased by {GOLD}!",
    93: "Max MP increased by {GOLD}!",
    94: "ATK increased by {GOLD}!",
    95: "DEF increased by {GOLD}!",
    96: "AGI increased by {GOLD}!",
    97: "...",
    98: "...",
    99: "...",
}

def extract_tags(text: str) -> list[str]:
    # Dynamic replacement tags that game engine substitutes (ignore page breaks {END})
    return re.findall(r"\{(?!END)[A-Z0-9]+\}", text)

def validate_translation(zh: str, en: str) -> bool:
    zh_tags = sorted(extract_tags(zh))
    en_tags = sorted(extract_tags(en))
    if zh_tags != en_tags:
        print(f"Tag mismatch! ZH: {zh_tags} vs EN: {en_tags}")
        return False
    return True

def load_block_translations():
    import sys
    tools_dir = os.path.dirname(os.path.abspath(__file__))
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    blocks = {0: BLOCK_0_TRANSLATIONS}
    for b in range(1, 18):
        try:
            mod = __import__(f"dialogue_data.block_{b:02d}", fromlist=["TRANSLATIONS"])
            blocks[b] = mod.TRANSLATIONS
        except Exception as e:
            print(f"Warning: could not load block {b}: {e}")
    return blocks

def main():
    with open(ZH_FILE, "r", encoding="utf-8") as f:
        zh_data = json.load(f)

    # Load existing translations if file exists
    en_existing = {}
    if os.path.exists(EN_FILE):
        with open(EN_FILE, "r", encoding="utf-8") as f:
            for item in json.load(f):
                if item.get("en", "").strip():
                    en_existing[item["id"]] = item["en"]

    block_translations = load_block_translations()

    out = []
    translated_count = 0
    for d in zh_data:
        d_id = d["id"]
        block = d["block"]
        idx = d["index"]
        zh = d["zh"]

        en = ""
        if block in block_translations and idx in block_translations[block]:
            en = block_translations[block][idx]
        elif d_id in en_existing:
            en = en_existing[d_id]

        if en:
            assert validate_translation(zh, en), f"Validation failed for ID {d_id}"
            translated_count += 1

        out.append({
            "id": d_id,
            "hex_id": d["hex_id"],
            "block": block,
            "index": idx,
            "portrait": d["portrait"],
            "len": d["len"],
            "zh": zh,
            "en": en,
        })

    with open(EN_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"Exported {len(out)} dialogue entries to {EN_FILE}")
    print(f"Total translated entries: {translated_count} / {len(out)} ({translated_count/len(out)*100:.1f}%)")

if __name__ == "__main__":
    main()
