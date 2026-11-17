#!/usr/bin/env python3
"""Compare one of our emulator frames (.ppm, 320x240) against a MAME snapshot (320x224).
MAME shows scanlines 8..231. Prints the share of differing pixels and writes a diff image."""
import sys
from PIL import Image, ImageChops
ours = Image.open(sys.argv[1]).convert('RGB').crop((0, 8, 320, 232))
mame = Image.open(sys.argv[2]).convert('RGB')
if mame.size != (320, 224):
    mame = mame.resize((320, 224))
diff = ImageChops.difference(ours, mame).convert('L').point(lambda v: 255 if v > 24 else 0)
n = diff.histogram()[255]   # pixels marked as different
print(f"{n} / {320*224} pixels differ ({100*n/(320*224):.1f}%)")
out = sys.argv[3] if len(sys.argv) > 3 else '/tmp/diff.png'
g = Image.new('RGB', (960, 224)); g.paste(ours, (0, 0)); g.paste(mame, (320, 0)); g.paste(diff.convert('RGB'), (640, 0)); g.save(out)
