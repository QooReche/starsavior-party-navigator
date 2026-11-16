"""Sleeve continuity, original face pixels, untouched portraits and edit limits."""
import hashlib
import json
from pathlib import Path
import sys
import unittest
from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT/'tools/gwen_art'
ART = ROOT/'assets/ui_icons/gwen'
sys.path.insert(0, str(HERE))
import build5
import build2
import sleeve7


def outside_bytes(im, mask):
    return Image.composite(Image.new('RGBA', im.size), im, mask).tobytes()


class GwenArt7(unittest.TestCase):
    def test_only_sleeve_source_pixels_change(self):
        for name in sleeve7.NAMES:
            for i, (src, dst) in enumerate(zip(build5.original_master_frames(name), build5.master_frames(name))):
                mask = sleeve7.sleeve_mask(name, i)
                self.assertEqual(outside_bytes(src, mask), outside_bytes(dst, mask))
                self.assertEqual(src.getchannel('A').tobytes(), dst.getchannel('A').tobytes())
                visible = ImageChops.multiply(build5.difference_mask(src, dst), src.getchannel('A'))
                self.assertGreater(sum(v > 200 for v in visible.get_flattened_data()), 100)

    def test_approved_png_pixels_outside_sleeve_and_untouched_assets(self):
        record = json.loads((HERE/'provenance7.json').read_text(encoding='utf-8'))
        for name, suffixes in record['preserved_outside_masks'].items():
            for suffix, expected in suffixes.items():
                with Image.open(ART/(name+suffix)) as im:
                    actual = outside_bytes(im.convert('RGBA'), sleeve7.sleeve_mask(name, size=240))
                self.assertEqual(hashlib.sha256(actual).hexdigest(), expected, name+suffix)
        for path, expected in record['unchanged_assets'].items():
            self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(), expected, path)

    def test_band_reaches_cuff_in_every_master_png_blink_and_webp_frame(self):
        for name in sleeve7.NAMES:
            pictures = [(f, i, 320, 'master') for i, f in enumerate(build5.master_frames(name))]
            for suffix in ('.png', '_blink.png', '.webp'):
                with Image.open(ART/(name+suffix)) as im:
                    for i in range(im.n_frames):
                        im.seek(i)
                        pictures.append((im.convert('RGBA'), i if i < 2 else 0, 240, suffix))
            for pic, frame, size, label in pictures:
                if name == 'st_point':
                    dx = (0, -1, 5)[frame]
                    # Sample the repaired gap from the cuff into the old band.
                    points = [(x+dx, 263) for x in range(145, 191)]
                else:
                    dx, dy = (18, 2) if frame == 1 else (0, 0)
                    points = [(x+dx, 250-(x-94)*.22+dy) for x in range(94, 167)]
                for x, y in points:
                    rgba = pic.getpixel((round(x*size/320), round(y*size/320)))
                    self.assertGreater(min(rgba[:3]), 160, (name, label, frame, x, y, rgba))
                    self.assertEqual(rgba[3], 255)

    def test_local_patch_budgets_and_generation_limit(self):
        for path in sleeve7.PATCHES.iterdir():
            self.assertLessEqual(path.stat().st_size, 80000)
        prompts = json.loads((HERE/'prompts7.json').read_text(encoding='utf-8'))
        self.assertEqual(set(c['name'] for c in prompts['calls']), set(sleeve7.NAMES + sleeve7.LEGACY_NAMES))
        for name in sleeve7.NAMES + sleeve7.LEGACY_NAMES:
            self.assertLessEqual(sum(c['name'] == name for c in prompts['calls']), 2)

    def test_thoughtful_action_inner_stripe_removed_only_locally(self):
        with Image.open(build2.MASTERS/'thoughtful.webp') as im:
            original = build2.cells(im.convert('RGBA'), 2)
        edited = sleeve7.apply('thoughtful', original)
        self.assertEqual(original[0].tobytes(), edited[0].tobytes())
        mask = sleeve7.sleeve_mask('thoughtful', 1)
        self.assertEqual(outside_bytes(original[1], mask), outside_bytes(edited[1], mask))
        self.assertEqual(original[1].getchannel('A').tobytes(), edited[1].getchannel('A').tobytes())
        with Image.open(ART/'thoughtful.webp') as im:
            im.seek(1)
            served = im.convert('RGBA')
        for x, y in ((73, 219), (69, 225), (64, 234), (58, 243)):
            self.assertGreater(min(original[1].getpixel((x, y))[:3]), 160)
            for pic, scale in ((edited[1], 1), (served, .75)):
                rgb = pic.getpixel((round(x*scale), round(y*scale)))[:3]
                self.assertLess(max(rgb), 160, (x, y, rgb))


if __name__ == '__main__':
    unittest.main()
