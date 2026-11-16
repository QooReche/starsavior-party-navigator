"""Notes sleeves must reach both cuffs without changing original decoded pixels elsewhere."""
import hashlib
import json
from pathlib import Path
import sys
import unittest
from PIL import Image, ImageChops, ImageStat

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT/'tools/gwen_art'
ART = ROOT/'assets/ui_icons/gwen'
sys.path.insert(0, str(HERE))
import sleeve8


def pictures(root, stem):
    with Image.open(root/(stem+'.png')) as im:
        yield im.convert('RGBA'), 0
    with Image.open(root/(stem+'.webp')) as im:
        for i in range(im.n_frames):
            im.seek(i)
            yield im.convert('RGBA'), i if i < 2 else 0


def outside(im, mask):
    # WebP discards hidden RGB at alpha=0; all visible RGBA must remain exact.
    visible = im.getchannel('A').point(lambda a: 255 if a else 0)
    canonical = Image.composite(im, Image.new('RGBA', im.size), visible)
    return Image.composite(Image.new('RGBA', im.size), canonical, mask).tobytes()


def connected_band(pic, frame, side):
    """All shoulder/elbow/cuff waypoints must belong to one white cloth component."""
    mask = sleeve8.sleeve_mask(frame)
    points = ([(64 if frame else 66, 146), (56, 182), (58, 194), (69, 188), (83, 177)]
              if side == 'left' else [(180, 148), (180, 165), (184, 182), (185, 196), (180, 203), (169, 198), (162, 195)])
    white = set()
    for y in range(140, 212):
        for x in range(43, 194):
            r, g, b, a = pic.getpixel((x, y))
            if mask.getpixel((x, y)) and min(r, g, b) > 155 and max(r, g, b)-min(r, g, b) < 65 and a > 200:
                white.add((x, y))
    start = points[0]
    if start not in white:
        return False
    seen, pending = {start}, [start]
    while pending:
        x, y = pending.pop()
        for dx, dy in ((-1,0),(1,0),(0,-1),(0,1),(-1,-1),(1,1),(-1,1),(1,-1)):
            p = (x+dx, y+dy)
            if p in white and p not in seen:
                seen.add(p)
                pending.append(p)
    return all(p in seen for p in points)


class GwenArt8(unittest.TestCase):
    def test_exact_original_pixels_and_alpha(self):
        original = list(pictures(sleeve8.PATCHES, 'notes_base'))
        current = list(pictures(ART, 'notes'))
        self.assertEqual(len(current), 4)  # static, open, closed-eye blink, return
        for frame_index, ((src, i), (dst, _)) in enumerate(zip(original, current)):
            mask = sleeve8.sleeve_mask(i)
            if frame_index == 0:
                self.assertEqual(outside(src, mask), outside(dst, mask))
            else:
                delta = ImageChops.difference(src, dst).convert("RGB")
                delta.paste((0,0,0), mask=mask)
                self.assertLess(max(ImageStat.Stat(delta).mean), 2.5)
            self.assertEqual(src.getchannel('A').tobytes(), dst.getchannel('A').tobytes())
            # Independent protected boxes: face, pencil hand, notebook, holding hand.
            for box in ((65,35,168,108),(93,133,116,164),(112,146,150,180),(126,157,155,178)):
                a, b = src.crop(box), dst.crop(box)
                if frame_index == 0:
                    self.assertEqual(outside(a, Image.new('L', a.size)), outside(b, Image.new('L', b.size)), (i,box))
                else:
                    self.assertLess(max(ImageStat.Stat(ImageChops.difference(a,b).convert('RGB')).mean), 3.0)

    def test_both_bands_are_continuous_in_every_served_frame(self):
        for pic, i in pictures(ART, 'notes'):
            for side in ('left', 'right'):
                self.assertTrue(connected_band(pic, i, side), (i, side))

    def test_original_provenance_and_uniform_budget(self):
        record = json.loads((HERE/'provenance8.json').read_text(encoding='utf-8'))
        for suffix in ('.png','.webp'):
            self.assertEqual(hashlib.sha256((sleeve8.PATCHES/('notes_base'+suffix)).read_bytes()).hexdigest(),
                             record['original_assets']['assets/ui_icons/gwen/notes'+suffix])
        self.assertEqual(hashlib.sha256((HERE/'masters2/notes.webp').read_bytes()).hexdigest(), record['original_master_sha256'])
        budget = json.loads((HERE/'budget.json').read_text(encoding='utf-8'))
        self.assertNotIn('file_overrides', budget)
        self.assertNotIn('file_overrides_reason', budget)
        self.assertEqual(budget['file_bytes'],80000)
        self.assertEqual(budget['served_bytes'],1450000+budget['art4_pairs_bytes']+budget['art4_blink_bytes']+budget['art5']['served_bytes'])
        self.assertLessEqual((ART/'notes.webp').stat().st_size,budget['file_bytes'])
        prompts = json.loads((HERE/'prompts8.json').read_text(encoding='utf-8'))
        self.assertLessEqual(len(prompts['calls']),2)


if __name__ == '__main__':
    unittest.main()
