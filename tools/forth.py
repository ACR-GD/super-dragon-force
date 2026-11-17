"""Decompiler for the indirect-threaded Forth used by Super Dragon Force.

Register model (68000):  a4 = IP, a5 = W (current CFA), a6 = data stack, a7 = return stack.
NEXT = movea.l (a4)+,a5 ; movea.l (a5),a0 ; jmp (a0)
A colon definition is a CFA whose cell is 0x49c (DOCOL), followed by a thread of CFAs.
"""
import sys, os, re, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from romutil import load_prg, u32

DOCOL = 0x49C

# name, number of inline cells, kind ('rel' relative branch, 'abs' absolute addr, 'lit', 'str')
PRIMS = {
    0x510: ("LIT", 1, "lit"),
    0x51C: ("2LIT", 2, "lit"),
    0x52C: ("(DO)", 1, "abs"),
    0x54C: ("(?DO)", 1, "abs"),
    0x560: ("LEAVE", 0, None),
    0x570: ("(LOOP)", 1, "rel"),
    0x590: ("(+LOOP)", 1, "rel"),
    0x5A4: ("BRANCH", 1, "rel"),
    0x5B0: ("0BRANCH", 1, "rel"),
    0x5C8: ("(OF)", 1, "rel"),
    0x5E4: ("EXIT", 0, None),
    0xEF4: ("EXIT'", 0, None),
    0x4E8: ("(\")", 0, "str"),        # inline counted string follows
    0x8A0: ("+", 0, None),
    0x8B0: ("-", 0, None),
    0x8C0: ("1+", 0, None),
    0x8CC: ("1-", 0, None),
    0x8D8: ("2+", 0, None),
    0x8E4: ("2-", 0, None),
    0xA2C: ("AND", 0, None),
    0xAE0: ("0=", 0, None),
    0xB70: ("I", 0, None),
    0xB94: ("I'", 0, None),
    0xBD0: ("DROP", 0, None),
    0xBDC: ("SWAP", 0, None),
    0xCB0: ("C@", 0, None),
}

class Forth:
    def __init__(self, rom=None):
        self.p = rom if rom is not None else load_prg()
        self.names = {k: v[0] for k, v in PRIMS.items()}
        self.load_names()

    def load_names(self, path=None):
        path = path or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "notes", "names.txt")
        if os.path.exists(path):
            for line in open(path, encoding="utf-8"):
                line = line.split("#")[0].strip()
                if not line: continue
                a, n = line.split(None, 1)
                self.names[int(a, 16)] = n.strip()

    def kind(self, cfa):
        c = u32(self.p, cfa)
        if c == DOCOL: return "colon"
        if c == cfa + 4: return "prim"
        return f"cf_{c:x}"

    def name(self, cfa):
        if cfa in self.names: return self.names[cfa]
        if cfa >= len(self.p) - 4: return f"?{cfa:x}"
        k = self.kind(cfa)
        if k == "colon": return f"w_{cfa:x}"
        if k == "prim": return f"p_{cfa:x}"
        return f"{k}_{cfa:x}"

    def decompile(self, cfa, maxcells=4000):
        """Yield (addr, text) for a colon definition, stopping at the final EXIT."""
        p = self.p
        a = cfa + 4
        out = []
        targets = set()
        maxbranch = a
        n = 0
        while n < maxcells:
            n += 1
            w = u32(p, a)
            nm = self.name(w)
            info = PRIMS.get(w)
            if info:
                _, ninl, kind = info
                if kind == "str":
                    ln = p[a + 4]
                    s = p[a + 5:a + 5 + ln]
                    try: t = s.decode("big5")
                    except Exception: t = s.decode("latin1")
                    out.append((a, f'(") "{t}"'))
                    a = (a + 5 + ln + 3) & ~3
                    continue
                args = []
                for i in range(ninl):
                    v = u32(p, a + 4 + 4 * i)
                    if kind == "rel":
                        tgt = (a + 4 + v) & 0xFFFFFFFF
                        targets.add(tgt); maxbranch = max(maxbranch, tgt)
                        args.append(f"->{tgt:x}")
                    elif kind == "abs":
                        targets.add(v); maxbranch = max(maxbranch, v)
                        args.append(f"=>{v:x}")
                    else:
                        args.append(f"{v:#x}" if v > 9 else str(v))
                out.append((a, nm + (" " + " ".join(args) if args else "")))
                a += 4 + 4 * ninl
                if w in (0x5E4, 0xEF4) and a > maxbranch:
                    break
                continue
            out.append((a, nm))
            a += 4
        return out, targets

    def listing(self, cfa):
        out, targets = self.decompile(cfa)
        lines = [f": {self.name(cfa)}   ( {cfa:06x} )"]
        for a, t in out:
            mark = f"{a:06x}:" + ("*" if a in targets else " ")
            lines.append(f"  {mark} {t}")
        return "\n".join(lines)

    def all_colons(self):
        p = self.p
        refs = collections.Counter()
        for o in range(0, 0x60000, 2):
            v = u32(p, o)
            if 0x400 <= v < 0x60000: refs[v] += 1
        return [o for o in range(0x400, 0x60000, 2) if u32(p, o) == DOCOL and refs[o] > 0]

    def callers(self, target):
        p = self.p
        res = []
        for o in range(0, 0x60000, 2):
            if u32(p, o) == target:
                res.append(o)
        return res

if __name__ == "__main__":
    f = Forth()
    if len(sys.argv) > 1:
        for x in sys.argv[1:]:
            print(f.listing(int(x, 16))); print()
    else:
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "notes", "forth_listing.txt"), "w", encoding="utf-8") as fh:
            for c in f.all_colons():
                fh.write(f.listing(c) + "\n\n")
