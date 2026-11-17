"""Unicorn-based harness to run native 68k routines / Forth words from the Super Dragon Force ROM.

Memory map (Super A'Can, per MAME supracan.cpp):
  000000-3FFFFF cart ROM  (program ROM 16007 at 0, data ROM 08002 assumed at 0x200000 -- TBC)
  E80000-EFFFFF sound/IO   F00000-F3FFFF video regs/palette   F40000-F5FFFF VRAM
  FF0000-FFFFFF work RAM
"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from romutil import load_prg, load_dat
from unicorn import Uc, UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, UC_HOOK_CODE, UcError
from unicorn.m68k_const import *

NEXT_STOP = 0x3FFF00   # sentinel CFA region (unused area) -- we patch a fake prim here

class Emu:
    def __init__(self, dat_base=0x200000):
        self.mu = mu = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, cpu=UC_CPU_M68K_M68000)
        self.prg = load_prg()
        mu.mem_map(0x000000, 0x400000)
        mu.mem_write(0, self.prg)
        if dat_base is not None:
            mu.mem_write(dat_base, load_dat())
        mu.mem_map(0xE00000, 0x200000)      # IO + video + RAM (flat)
        # sentinel primitive: CFA at NEXT_STOP whose code is NEXT_STOP+4 (we stop when PC hits it)
        mu.mem_write(NEXT_STOP, struct.pack(">I", NEXT_STOP + 4) + b"\x4e\x71" * 4)
        # thread for running a single word: [word, STOP]
        self.thread = NEXT_STOP + 0x40

    def reg(self, r, v=None):
        if v is None: return self.mu.reg_read(r)
        self.mu.reg_write(r, v)

    def push(self, v):
        a6 = self.reg(UC_M68K_REG_A6) - 4
        self.mu.mem_write(a6, struct.pack(">I", v & 0xFFFFFFFF))
        self.reg(UC_M68K_REG_A6, a6)

    def pop(self):
        a6 = self.reg(UC_M68K_REG_A6)
        v = struct.unpack(">I", self.mu.mem_read(a6, 4))[0]
        self.reg(UC_M68K_REG_A6, a6 + 4)
        return v

    def stack(self):
        a6 = self.reg(UC_M68K_REG_A6); n = (self.DS_TOP - a6) // 4
        return [struct.unpack(">I", self.mu.mem_read(a6 + 4 * i, 4))[0] for i in range(n)]

    DS_TOP = 0xFFFB5C
    RS_TOP = 0xFFFFF0

    def reset_stacks(self):
        self.reg(UC_M68K_REG_A6, self.DS_TOP)
        self.reg(UC_M68K_REG_A7, self.RS_TOP)

    def run_word(self, cfa, args=(), max_insns=50_000_000):
        """Execute Forth word `cfa` with args pushed (first arg deepest). Returns resulting data stack (top first)."""
        mu = self.mu
        self.reg(UC_M68K_REG_SR, 0x2700)
        self.reset_stacks()
        for a in args: self.push(a)
        mu.mem_write(self.thread, struct.pack(">II", cfa, NEXT_STOP))
        self.reg(UC_M68K_REG_A4, self.thread)
        # perform NEXT ourselves: a5 = *(a4)+ ; pc = *a5
        self.reg(UC_M68K_REG_A4, self.thread + 4)
        self.reg(UC_M68K_REG_A5, cfa)
        code = struct.unpack(">I", mu.mem_read(cfa, 4))[0]
        mu.emu_start(code, NEXT_STOP + 4, count=max_insns)
        return self.stack()

    def read(self, addr, n): return bytes(self.mu.mem_read(addr, n))
