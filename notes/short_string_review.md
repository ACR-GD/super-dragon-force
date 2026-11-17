# Shortened names: review

The game cuts these strings off at a fixed width (see `build/string_report.txt`).
Edit `notes/short_string_proposals.json` (change `en`, or copy in an alternative), then run
`python3 tools/apply_short_proposals.py --apply` and rebuild.

**Rule:** every short form abbreviates the full name (no renames), so screens and dialogue
always refer to the same thing. Names, items and spells are also inserted into dialogue
({CHAR1}, {ITEM}, {SPELL}), so the short forms appear in sentences too, e.g. "Sam obtained Rest.Frt."

**Place names are not shortened:** the map banner and dialogue keep the full names. Only the
save/load slot list uses short ones (`notes/save_screen_places.json`), listed at the end.


## terrain (4 letters)

| # | Current | Shows now as | Proposed | Alternatives | Note |
|---|---|---|---|---|---|
| `0x009` | Obstacle | `Obst` | **`Obst`** |  | 障礙 'obstacle' |
| `0x00a` | Ocean | `Ocea` | **`Ocn`** | `Ocea` |  |
| `0x00b` | Forest | `Fore` | **`Frst`** |  |  |
| `0x00c` | Unknown | `Unkn` | **`Unkn`** |  |  |
| `0x00e` | Building | `Buil` | **`Bldg`** |  |  |
| `0x00f` | Hills | `Hill` | **`Hill`** |  |  |
| `0x010` | Unknown | `Unkn` | **`Unkn`** |  |  |
| `0x011` | Mountains | `Moun` | **`Mtns`** |  |  |
| `0x012` | River | `Rive` | **`Rivr`** | `Rvr` |  |
| `0x013` | Grass | `Gras` | **`Gras`** | `Grss` |  |
| `0x015` | Unknown | `Unkn` | **`Unkn`** |  |  |
| `0x016` | Unknown | `Unkn` | **`Unkn`** |  |  |
| `0x018` | Shallows | `Shal` | **`Shlw`** | `Shal` |  |

## unit names (10 letters)

> Also used by battle messages ({CHAR1}/{CHAR2}), e.g. 'DemonArchr attacks!'. None of these monsters is named in the story dialogue.

| # | Current | Shows now as | Proposed | Alternatives | Note |
|---|---|---|---|---|---|
| `0x06a` | Roving Armor | `Roving Arm` | **`RovingArmr`** |  |  |
| `0x06b` | Scorpion Wasp | `Scorpion W` | **`ScorpWasp`** |  |  |
| `0x06c` | Demon Hunter | `Demon Hunt` | **`DemonHuntr`** |  |  |
| `0x075` | Demon Archer | `Demon Arch` | **`DemonArchr`** |  |  |
| `0x07d` | Evil Galahad | `Evil Galah` | **`EvlGalahad`** | `E.Galahad` | kept distinct from 0x065 'Galahad' |
| `0x07f` | Hunter Wasp | `Hunter Was` | **`HunterWasp`** |  |  |
| `0x086` | Demon Priest | `Demon Prie` | **`DemonPrst`** |  |  |
| `0x089` | Paradise Bird | `Paradise B` | **`Parad.Bird`** |  |  |
| `0x08a` | Ghost Assassin | `Ghost Assa` | **`GhostAssn.`** |  |  |
| `0x08e` | Metal Hunter | `Metal Hunt` | **`MetalHuntr`** |  |  |
| `0x08f` | Unicorn Man | `Unicorn Ma` | **`UnicornMan`** |  |  |
| `0x090` | Flame Centipede | `Flame Cent` | **`FlameCntpd`** |  |  |
| `0x091` | Kill Machine | `Kill Machi` | **`KillMachin`** | `Kill Mach.` |  |
| `0x094` | Phantom Sniper | `Phantom Sn` | **`PhntmSnipr`** |  |  |
| `0x095` | Fire Fiend Hound | `Fire Fiend` | **`FireFndHnd`** | `FireFHound` |  |
| `0x096` | Skeleton Warrior | `Skeleton W` | **`SkeletonWr`** |  |  |
| `0x098` | Five-Head Dragon | `Five-Head ` | **`5-HeadDrgn`** |  | 'Five' abbreviated as 5 |
| `0x09a` | Smoke Demon | `Smoke Demo` | **`SmokeDemon`** |  |  |
| `0x09b` | Evil Doruka | `Evil Doruk` | **`EvlDoruka`** | `E.Doruka` | matches EvlGalahad |

## classes (6 letters)

> Abbreviated, not renamed: the dialogue calls Carson 'the Berserker', Byron an 'apprentice', and the final boss 'the Archdemon'.

| # | Current | Shows now as | Proposed | Alternatives | Note |
|---|---|---|---|---|---|
| `0x0ab` | Warrior | `Warrio` | **`Warrr`** | `Warior`, `Wrrior` |  |
| `0x0ac` | Warrior | `Warrio` | **`Warrr`** | `Warior`, `Wrrior` |  |
| `0x0b9` | Mercenary | `Mercen` | **`Merc.`** |  |  |
| `0x0ba` | Mercenary | `Mercen` | **`Merc.`** |  |  |
| `0x0bb` | Berserker | `Berser` | **`Berskr`** |  |  |
| `0x0bf` | Spellblade | `Spellb` | **`SpBlde`** | `Splbld` |  |
| `0x0d7` | Spellblade | `Spellb` | **`SpBlde`** | `Splbld` |  |
| `0x0c4` | Inorganic | `Inorga` | **`Inorg.`** |  |  |
| `0x0c9` | Inorganic | `Inorga` | **`Inorg.`** |  |  |
| `0x0ca` | Inorganic | `Inorga` | **`Inorg.`** |  |  |
| `0x0d4` | Inorganic | `Inorga` | **`Inorg.`** |  |  |
| `0x0d6` | Inorganic | `Inorga` | **`Inorg.`** |  |  |
| `0x0df` | Inorganic | `Inorga` | **`Inorg.`** |  |  |
| `0x0e1` | Inorganic | `Inorga` | **`Inorg.`** |  |  |
| `0x0f4` | Inorganic | `Inorga` | **`Inorg.`** |  |  |
| `0x0da` | Demon Knight | `Demon ` | **`DmnKnt`** |  |  |
| `0x0e2` | Dark Knight | `Dark K` | **`DrkKnt`** |  |  |
| `0x0e5` | Apprentice | `Appren` | **`Apprnt`** |  |  |
| `0x0ed` | Apprentice | `Appren` | **`Apprnt`** |  |  |
| `0x0f6` | Apprentice | `Appren` | **`Apprnt`** |  |  |
| `0x0e8` | Machine | `Machin` | **`Mach.`** |  |  |
| `0x0eb` | Machine | `Machin` | **`Mach.`** |  |  |
| `0x0f7` | Archdemon | `Archde` | **`ArchDm`** | `Archdm` |  |

## items (8 letters)

> Conventions: Sw = sword, Bl = blade, Stf = staff, Frt = fruit. Also used by dialogue ({ITEM}), e.g. 'Sam obtained Rest.Frt.'

| # | Current | Shows now as | Proposed | Alternatives | Note |
|---|---|---|---|---|---|
| `0x12d` | Cypress Club | `Cypress ` | **`Cyp.Club`** |  |  |
| `0x12e` | Mage Wand | `Mage Wan` | **`MageWand`** |  |  |
| `0x12f` | Force Staff | `Force St` | **`ForceStf`** |  |  |
| `0x130` | Bolt Staff | `Bolt Sta` | **`Bolt Stf`** |  |  |
| `0x131` | Dragon Staff | `Dragon S` | **`DragnStf`** |  |  |
| `0x133` | Stone Axe | `Stone Ax` | **`StoneAxe`** |  |  |
| `0x135` | Battle Axe | `Battle A` | **`BattleAx`** |  |  |
| `0x136` | Great Axe | `Great Ax` | **`GreatAxe`** |  |  |
| `0x137` | Demon Axe | `Demon Ax` | **`DemonAxe`** |  |  |
| `0x13b` | Steel Bow | `Steel Bo` | **`SteelBow`** |  |  |
| `0x13d` | Flame Bow | `Flame Bo` | **`FlameBow`** |  |  |
| `0x140` | Alloy Dirk | `Alloy Di` | **`AlloyDrk`** |  |  |
| `0x141` | Holy Dirk | `Holy Dir` | **`HolyDirk`** |  |  |
| `0x142` | Moth Knife | `Moth Kni` | **`MothKnfe`** |  |  |
| `0x143` | Fiend Dagger | `Fiend Da` | **`FiendDgr`** |  |  |
| `0x144` | Short Sword | `Short Sw` | **`Short Sw`** |  |  |
| `0x145` | Bronze Sword | `Bronze S` | **`BronzeSw`** |  |  |
| `0x146` | Steel Sword | `Steel Sw` | **`Steel Sw`** |  |  |
| `0x147` | Allure Blade | `Allure B` | **`AllureBl`** |  |  |
| `0x148` | Zombie Blade | `Zombie B` | **`ZombieBl`** |  |  |
| `0x149` | Dragon Blade | `Dragon B` | **`DragonBl`** |  |  |
| `0x14a` | Snake Sword | `Snake Sw` | **`Snake Sw`** |  |  |
| `0x14b` | Falcon Blade | `Falcon B` | **`FalconBl`** |  |  |
| `0x14c` | Evil Bane | `Evil Ban` | **`EvilBane`** |  |  |
| `0x14d` | Chaos Blade | `Chaos Bl` | **`Chaos Bl`** |  |  |
| `0x14e` | Twin Blade | `Twin Bla` | **`Twin Bl`** |  |  |
| `0x150` | Restore Fruit | `Restore ` | **`Rest.Frt`** |  |  |
| `0x151` | Antidote Herb | `Antidote` | **`Antidote`** |  |  |
| `0x152` | Moon Herb | `Moon Her` | **`MoonHerb`** |  |  |
| `0x153` | Alarm Clock | `Alarm Cl` | **`AlrmClck`** |  |  |
| `0x154` | Holy Water | `Holy Wat` | **`Holy Wtr`** |  |  |
| `0x155` | Ward Charm | `Ward Cha` | **`WardChrm`** |  |  |
| `0x156` | Warp Leaf | `Warp Lea` | **`WarpLeaf`** |  |  |
| `0x157` | Magic Water | `Magic Wa` | **`MagicWtr`** |  |  |
| `0x158` | Sage Fruit | `Sage Fru` | **`Sage Frt`** |  |  |
| `0x159` | Power Seed | `Power Se` | **`PowrSeed`** |  |  |
| `0x15a` | Speed Seed | `Speed Se` | **`SpdSeed`** |  |  |
| `0x15b` | Agility Seed | `Agility ` | **`AgilSeed`** |  |  |
| `0x15c` | Guard Seed | `Guard Se` | **`GrdSeed`** |  |  |
| `0x15d` | Life Acorn | `Life Aco` | **`LifeAcrn`** |  |  |
| `0x15e` | Mystic Fruit | `Mystic F` | **`Myst.Frt`** |  |  |
| `0x15f` | Scorpion Tail | `Scorpion` | **`ScorpTl`** |  |  |
| `0x161` | Photon Cannon | `Photon C` | **`PhotonCn`** |  |  |
| `0x162` | Beast Fang | `Beast Fa` | **`BstFang`** |  |  |
| `0x163` | Venom Tail | `Venom Ta` | **`VnmTail`** |  |  |
| `0x164` | Octo Tentacle | `Octo Ten` | **`OctoTent`** |  |  |
| `0x165` | Poison Fang | `Poison F` | **`PoisFang`** |  |  |
| `0x167` | Dragon Claw | `Dragon C` | **`DrgnClaw`** |  |  |
| `0x168` | Gatling Cannon | `Gatling ` | **`GatlngCn`** |  |  |
| `0x169` | Metal Claw | `Metal Cl` | **`MetlClaw`** |  |  |
| `0x16a` | Gold Coin | `Gold Coi` | **`GoldCoin`** |  |  |

## music titles (16 letters)

| # | Current | Shows now as | Proposed | Alternatives | Note |
|---|---|---|---|---|---|
| `0x228` | Epilogue of Legends | `Epilogue of Lege` | **`Epilog of Legend`** | `EpilogueOfLegnds` |  |

## save/load slot list place names (10 letters)

| # | Map banner & dialogue | Save screen |
|---|---|---|
| `0x01e` | Santa Cruz Castle | `SC Castle` |
| `0x01f` | Santa Cruz Town | `SC Town` |
| `0x020` | Castle - Shrine | `Cst-Shrine` |
| `0x021` | Ancient Shrine | `Anc.Shrine` |
| `0x022` | Training Falls | `Trng Falls` |
| `0x023` | Castle - Maran | `Cst-Maran` |
| `0x024` | Maran Village | `Maran Vil.` |
| `0x025` | Barusa Castle | `Barusa Cst` |
| `0x026` | Barusa - Danto | `Barusa-Dnt` |
| `0x027` | Danto Town | `Danto Town` |
| `0x028` | Danto Cave | `Danto Cave` |
| `0x029` | Fiend Army Camp | `Fiend Camp` |
| `0x02a` | Royal Cathedral | `Royal Cath` |
| `0x02b` | Iron Town | `Iron Town` |
| `0x02c` | Iron Town Mine | `Iron Mine` |
| `0x02d` | Pamius Plains | `Pamius Pl.` |
| `0x02e` | Bridge of Souls | `Brdg.Souls` |
| `0x02f` | Gypsy Camp | `Gypsy Camp` |
| `0x030` | Basque Highlands | `Basque Hl.` |
| `0x031` | Gypsy Village | `Gypsy Vil.` |
| `0x032` | Demon Fortress | `Demon Fort` |
| `0x033` | Secret Port | `SecretPort` |
| `0x034` | Port - Water | `Port-Water` |
| `0x035` | Water Castle | `Water Cst.` |
| `0x036` | Sunken Shrine | `SunkShrine` |
| `0x037` | Water - Draken | `Water-Drkn` |
| `0x038` | Draken Village | `Draken Vil` |
| `0x039` | Draken - Dragon Den | `Drkn-D.Den` |
| `0x03a` | Dragon Den | `Dragon Den` |
| `0x03b` | Draken - Barukus | `Drkn-Brks` |
| `0x03c` | Barukus Keep | `BarukusKp` |
| `0x03d` | Anson City | `Anson City` |
| `0x03e` | Anson - Tower | `Anson-Twr` |
| `0x03f` | Ancient Tower | `Anc. Tower` |
| `0x040` | Ancient Sanctuary | `Anc.Sanct.` |
| `0x041` | Anson - Ruin City | `Anson-Ruin` |
| `0x042` | Forgotten City | `ForgotCity` |
| `0x043` | Mages Lair 1F | `MageLair1F` |
| `0x044` | Mages Lair 2F | `MageLair2F` |
| `0x045` | Floating Keep 1F | `FloatKp 1F` |
| `0x046` | Floating Keep 2F | `FloatKp 2F` |
| `0x047` | Floating Keep 3F | `FloatKp 3F` |
| `0x048` | Maran Battlefield | `Maran Bttl` |
