"""Shared helpers for Super Dragon Force ROM work."""
import os, struct
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIG = os.path.join(ROOT, "Super-Dragon-Force_Super-Acan_ZH-TW")
PRG_FILE = os.path.join(ORIG, "16007 (Taiwan).bin")
DAT_FILE = os.path.join(ORIG, "08002 (Taiwan).bin")

def swap16(b: bytes) -> bytes:
    a = bytearray(b); a[0::2], a[1::2] = b[1::2], b[0::2]; return bytes(a)

def load_prg() -> bytes:
    """Program ROM in 68k (big-endian) order."""
    return swap16(open(PRG_FILE, "rb").read())

def load_dat(swapped=True) -> bytes:
    d = open(DAT_FILE, "rb").read()
    return swap16(d) if swapped else d

def u16(b, o): return struct.unpack_from(">H", b, o)[0]
def u32(b, o): return struct.unpack_from(">I", b, o)[0]

def disasm(code: bytes, base: int, start: int, count=40):
    import capstone
    md = capstone.Cs(capstone.CS_ARCH_M68K, capstone.CS_MODE_M68K_000)
    out = []
    for i in md.disasm(code[start - base:], start):
        out.append(f"{i.address:06x}: {i.bytes.hex():<20} {i.mnemonic} {i.op_str}")
        if len(out) >= count: break
    return "\n".join(out)
