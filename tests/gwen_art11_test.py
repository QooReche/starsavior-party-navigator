"""Forearm continuity and preservation of the approved art10 pixels."""
import hashlib
import json
from pathlib import Path
import sys
import unittest
from PIL import Image, ImageChops, ImageStat

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT/'tools/gwen_art'
BUDGET = json.loads((HERE/'budget.json').read_text(encoding='utf-8'))
ART = ROOT/'assets/ui_icons/gwen'
sys.path.insert(0, str(HERE))
import sleeve11


def pictures(root, stem):
    for suffix in ('.png', '.webp', '_blink.png'):
        with Image.open(root/(stem+suffix)) as im:
            for i in range(im.n_frames):
                im.seek(i)
                yield suffix, i if i < 2 else 0, im.convert('RGBA')


def outside(im, mask):
    return Image.composite(Image.new('RGBA', im.size), im, mask).tobytes()


def continuous(pic, side):
    """One white component must connect upper arm, elbow, forearm and cuff."""
    if side == 'left':
        roi = (42, 160, 93, 212)
        boxes = [(50,166,58,174),(45,184,52,192),(50,197,59,204),
                 (64,202,72,208),(83,198,91,205)]
    else:
        roi = (149, 160, 194, 212)
        boxes = [(181,166,188,174),(184,185,192,194),(178,199,186,207),
                 (162,200,170,207),(151,197,160,205)]
    white = set()
    for y in range(roi[1], roi[3]):
        for x in range(roi[0], roi[2]):
            r, g, b, a = pic.getpixel((x, y))
            if min(r,g,b) > 160 and max(r,g,b)-min(r,g,b) < 65 and a > 200:
                white.add((x, y))
    while white:
        seed = white.pop()
        seen, todo = {seed}, [seed]
        while todo:
            x, y = todo.pop()
            for dx, dy in ((-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)):
                p = x+dx, y+dy
                if p in white:
                    white.remove(p); seen.add(p); todo.append(p)
        if all(sum(x0 <= x < x1 and y0 <= y < y1 for x,y in seen) >= 3
               for x0,y0,x1,y1 in boxes):
            return True
    return False


class GwenArt11(unittest.TestCase):
    def test_both_lower_bands_reach_cuffs_in_all_five_frames(self):
        for label, frame, pic in pictures(ART, 'st_shy'):
            for side in ('left', 'right'):
                self.assertTrue(continuous(pic, side), (label, frame, side))
        # The original omission must fail on each side, not merely alter a hash.
        for label, frame, pic in pictures(sleeve11.PATCHES, 'st_shy_base'):
            for side in ('left', 'right'):
                self.assertFalse(continuous(pic, side), (label, frame, side))

    def test_approved_pixels_and_alpha(self):
        before = list(pictures(sleeve11.PATCHES, 'st_shy_base'))
        after = list(pictures(ART, 'st_shy'))
        self.assertEqual(len(before), 5)
        self.assertEqual(len(after), 5)
        for (label, frame, src), (_, _, dst) in zip(before, after):
            mask = sleeve11.sleeve_mask(frame)
            repaired = sleeve11.repair(src, frame)
            self.assertEqual(outside(src, mask), outside(repaired, mask))
            self.assertEqual(src.getchannel('A').tobytes(), dst.getchannel('A').tobytes())
            if label != '.webp':
                self.assertEqual(outside(src, mask), outside(dst, mask))
            else:
                delta = ImageChops.difference(src, dst).convert('RGB')
                delta.paste((0,0,0), mask=mask)
                self.assertLess(max(ImageStat.Stat(delta).mean), 2.5)
            # Independent boxes: approved C face, clasped gloves, waist/torso.
            for box in ((65,35,166,110),(95,165,144,193),(98,212,140,230)):
                self.assertEqual(src.crop(box).tobytes(), repaired.crop(box).tobytes())
                if label != '.webp':
                    self.assertEqual(src.crop(box).tobytes(), dst.crop(box).tobytes())

    def test_provenance_and_untouched_portraits(self):
        record = json.loads((HERE/'provenance11.json').read_text(encoding='utf-8'))
        for path, expected in {**record['originals'], **record['unchanged']}.items():
            raw = (ROOT/path).read_bytes()
            # The art11 record hashed faces.json on Windows before Git's LF normalization.
            # Preserve its recorded hash and exact content, accepting only newline conversion.
            if path.endswith('.json'):
                raw = raw.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')
            self.assertEqual(hashlib.sha256(raw).hexdigest(), expected, path)
        for path in sleeve11.PATCHES.iterdir():
            self.assertLessEqual(path.stat().st_size, BUDGET['file_bytes'], path.name)


if __name__ == '__main__':
    unittest.main()
