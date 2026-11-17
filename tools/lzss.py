"""LZSS compressor and decompressor for Super Dragon Force (68000 routine at 0x1648)."""
import struct

LEN_TABLE = {
    0: 3, 2: 10, 3: 2, 4: 5, 5: 4,
    12: 7, 13: 6, 14: 9, 15: 8,
}

def decompress(data: bytes, offset: int = 0) -> tuple[bytes, int]:
    """Decompress stream starting at data[offset:]. Returns (decompressed_bytes, next_offset)."""
    pos = offset
    out = bytearray()

    def read_u8():
        nonlocal pos
        b = data[pos]; pos += 1; return b

    def read_flag():
        b0 = read_u8(); b1 = read_u8()
        return b0 | (b1 << 8)

    d4 = read_flag()
    d3 = 15

    def get_bit():
        nonlocal d4, d3
        bit = d4 & 1
        d4 >>= 1
        d3 -= 1
        if d3 < 0:
            d4 = read_flag()
            d3 = 15
        return bit

    # Note: at 0x1680, roxr.w #1, d4 happens first, THEN dbra d3
    # When d3 hits -1 (after 16 shifts), it reloads d4 and d3=15 BEFORE testing carry!
    while True:
        if get_bit() == 0:
            out.append(read_u8())
            continue
        # Match or end
        d1 = (get_bit() << 1) | get_bit()
        if d1 != 0:
            d1 = (d1 << 1) | get_bit()
            if d1 >= 6:
                d1 = (d1 << 1) | get_bit()
        d2 = LEN_TABLE[d1]
        if d2 == 10:
            d0 = read_u8()
            if d0 == 0xFF:
                break
            d2 += d0
        # Decode distance
        if d2 == 2:
            dist_hi = 0
        else:
            if get_bit() == 1:
                dist_hi = 0
            else:
                v = (get_bit() << 2) | (get_bit() << 1) | get_bit()
                if v < 2:
                    dist_hi = v + 1
                else:
                    v = (v << 1) | get_bit()
                    if v < 8:
                        dist_hi = v - 1
                    else:
                        v = (v << 1) | get_bit()
                        if v < 0x17:
                            dist_hi = v - 9
                        else:
                            v = (v << 1) | get_bit()
                            dist_hi = v & 0xDF
        dist_lo = read_u8()
        dist = (dist_hi << 8) | dist_lo
        if dist == 0:
            dist = 0x10000
        for _ in range(d2):
            out.append(out[-dist])
    return bytes(out), pos


class _BitStreamEncoder:
    """Packs flag bits into little-endian 16-bit words interleaved with byte payloads,
    matching the exact reload timing of 0x1648 (reload happens right after the 16th bit is shifted)."""
    def __init__(self):
        self.buf = bytearray()
        self.flag_pos = None
        self.flag_val = 0
        self.bit_idx = 0
        self._alloc_flag()

    def _alloc_flag(self):
        self.flag_pos = len(self.buf)
        self.buf.extend(b"\x00\x00")
        self.flag_val = 0
        self.bit_idx = 0

    def put_bit(self, b: int):
        if b:
            self.flag_val |= (1 << self.bit_idx)
            self.buf[self.flag_pos] = self.flag_val & 0xFF
            self.buf[self.flag_pos + 1] = (self.flag_val >> 8) & 0xFF
        self.bit_idx += 1
        if self.bit_idx == 16:
            # In 0x1648, as soon as the 16th bit is shifted out (dbra d3 falls through),
            # the decompressor immediately reads the next 2 bytes from (a1)+ as the new flag word
            # BEFORE reading any byte payload triggered by that 16th bit!
            self._alloc_flag()

    def put_bits_msb(self, val: int, nbits: int):
        for i in range(nbits - 1, -1, -1):
            self.put_bit((val >> i) & 1)

    def put_byte(self, b: int):
        self.buf.append(b & 0xFF)

    def finish(self) -> bytes:
        # Emit end-of-stream: bit 1, then 010 (d1=2 -> d2=10), then byte 0xFF
        self.put_bit(1)
        self.put_bits_msb(0b010, 3)
        self.put_byte(0xFF)
        return bytes(self.buf)


LEN_CODE = {
    2: (0b011, 3),
    3: (0b00, 2),
    4: (0b101, 3),
    5: (0b100, 3),
    6: (0b1101, 4),
    7: (0b1100, 4),
    8: (0b1111, 4),
    9: (0b1110, 4),
}

def compress(raw: bytes) -> bytes:
    """Compress raw bytes into 0x1648 LZSS format."""
    enc = _BitStreamEncoder()
    n = len(raw)
    i = 0
    while i < n:
        # Search window (up to 767 bytes back for short distance codes, max 263 len)
        best_len = 1
        best_dist = 0
        max_l = min(263, n - i)
        w_start = max(0, i - 767)
        if max_l >= 2 and i > 0:
            sub = raw[i:i + max_l]
            # simple backward search
            p = raw.rfind(sub[:2], w_start, i + 1)
            while p != -1 and p < i:
                dist = i - p
                l = 2
                while l < max_l and raw[p + l] == raw[i + l]:
                    l += 1
                # dist >= 256 requires l >= 3
                if dist < 256 or l >= 3:
                    if l > best_len:
                        best_len = l
                        best_dist = dist
                        if l == max_l:
                            break
                if p == w_start:
                    break
                p = raw.rfind(sub[:2], w_start, p + 1)
        if best_len >= 2 and (best_dist < 256 or best_len >= 3):
            enc.put_bit(1)
            if best_len <= 9:
                code, nbits = LEN_CODE[best_len]
                enc.put_bits_msb(code, nbits)
            else:
                enc.put_bits_msb(0b010, 3)
                enc.put_byte(best_len - 10)
            if best_len == 2:
                enc.put_byte(best_dist & 0xFF)
            else:
                d_hi = best_dist >> 8
                d_lo = best_dist & 0xFF
                if d_hi == 0:
                    enc.put_bit(1)
                elif d_hi in (1, 2):
                    enc.put_bit(0)
                    enc.put_bits_msb(d_hi - 1, 3)
                enc.put_byte(d_lo)
            i += best_len
        else:
            enc.put_bit(0)
            enc.put_byte(raw[i])
            i += 1
    return enc.finish()
