"""Expression visibility at 120px, local edits, preserved clothes and provenance."""
import hashlib
import json
from pathlib import Path
import sys
import unittest
from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT/'tools/gwen_art'
BUDGET = json.loads((HERE/'budget.json').read_text(encoding='utf-8'))
ART = ROOT/'assets/ui_icons/gwen'
sys.path.insert(0, str(HERE))
import build2
import build5
import face9
import sleeve7
import sleeve11


def outside(im, mask):
    return Image.composite(Image.new('RGBA', im.size), im, mask).tobytes()


def feature_count(im, box, blush=False):
    small = im.resize((120, 120), Image.Resampling.LANCZOS)
    return sum(a > 200 and r > 170 and g > 120 and r > b and r-g > (35 if blush else 5)
               for r, g, b, a in small.crop(box).get_flattened_data())


class GwenArt9(unittest.TestCase):
    def test_source_edit_is_local_and_costume_is_unchanged(self):
        for name in face9.NAMES:
            with Image.open(build5.MASTERS/(name+'.webp')) as im:
                original = sleeve7.apply(name, build2.cells(im.convert('RGBA'), 3))
            for src, dst in zip(original, build5.master_frames(name)):
                self.assertEqual(outside(src, face9.face_mask(name)), outside(dst, face9.face_mask(name)))
                self.assertEqual(src.getchannel('A').tobytes(), dst.getchannel('A').tobytes())
                self.assertEqual(src.crop((0, 155, 320, 320)).tobytes(), dst.crop((0, 155, 320, 320)).tobytes())
                delta = ImageChops.difference(src, dst).convert('RGB')
                self.assertGreater(sum(max(p) > 30 for p in delta.get_flattened_data()), 300)

    def test_png_and_blink_preserve_original_body(self):
        for name in face9.NAMES:
            src = Image.open(face9.PATCHES/(name+'-before.png')).convert('RGBA')
            for suffix in ('.png', '_blink.png'):
                dst = Image.open(ART/(name+suffix)).convert('RGBA')
                mask = face9.face_mask(name, 240)
                if name == 'st_shy':
                    # Art11 owns only the lower sleeves; its independent test
                    # still checks the approved art10 face and all other pixels.
                    mask = ImageChops.lighter(mask, sleeve11.sleeve_mask())
                self.assertEqual(outside(src, mask), outside(dst, mask))
                # Preserve the historical body assertion except the new sleeve repair.
                body_src, body_dst = src, dst
                if name == 'st_shy':
                    body_src, body_dst = (Image.composite(Image.new('RGBA', im.size), im, sleeve11.sleeve_mask()) for im in (src, dst))
                self.assertEqual(body_src.crop((0, 120, 240, 240)).tobytes(), body_dst.crop((0, 120, 240, 240)).tobytes())

    def test_restrained_cheeks_and_visible_face_edit_at_120px(self):
        # PM rejected inflation/deep blush. Bound the former witness regions;
        # expression readability is reviewed in _tmp/_art10.png, not classified here.
        for name, boxes, blush in (
            ('st_sulk', [(38,43,45,52)], False),
            ('st_shy', [(44,40,56,48),(59,37,72,46)], True),
        ):
            before = Image.open(face9.PATCHES/(name+'-before.png')).convert('RGBA')
            after = Image.open(ART/(name+'.png')).convert('RGBA')
            self.assertEqual(before.getchannel('A').tobytes(), after.getchannel('A').tobytes())
            for box in boxes:
                self.assertLessEqual(feature_count(after, box, blush), 8 if blush else 2)
            # A full rollback must fail even though it also has natural cheeks.
            small_delta = ImageChops.difference(before.resize((120,120)), after.resize((120,120)))
            changed = sum(max(p[:3]) > 25 for p in small_delta.crop((44,31,74,53)).get_flattened_data())
            self.assertGreater(changed, 30, name)

    def test_original_provenance_budgets_and_call_limit(self):
        record = json.loads((HERE/'provenance9.json').read_text(encoding='utf-8'))
        for filename, expected in record['before_sha256'].items():
            self.assertEqual(hashlib.sha256((face9.PATCHES/filename).read_bytes()).hexdigest(), expected)
        for name, expected in record['original_masters_sha256'].items():
            self.assertEqual(hashlib.sha256((build5.MASTERS/(name+'.webp')).read_bytes()).hexdigest(), expected)
        for path in face9.PATCHES.iterdir():
            self.assertLessEqual(path.stat().st_size, BUDGET['file_bytes'], path.name)
        calls = json.loads((HERE/'prompts10.json').read_text(encoding='utf-8'))['calls']
        self.assertEqual(set(c['name'] for c in calls), set(face9.NAMES))
        for name in face9.NAMES:
            self.assertTrue(1 <= sum(c['name'] == name for c in calls) <= 2)


if __name__ == '__main__':
    unittest.main()
