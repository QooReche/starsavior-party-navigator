"""Approved cry face, untouched SD, source provenance and deterministic rebuild."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest
from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT/'tools/gwen_art'
ART = ROOT/'assets/ui_icons/gwen'
sys.path.insert(0, str(HERE))
import build2
import build5
import cry6


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class GwenArt6(unittest.TestCase):
    def test_approved_cry_pixels_and_real_sleeve_change(self):
        original = build2.cells(Image.open(build5.MASTERS/'st_cry.webp').convert('RGBA'), 3)
        edited = build5.master_frames('st_cry')
        for i, (src, dst) in enumerate(zip(original, edited)):
            delta = build5.difference_mask(src, dst)
            self.assertTrue(delta.getbbox(), 'Sleeve edit missing')
            visible = ImageChops.multiply(delta, src.getchannel('A').point(lambda a: 255 if a > 200 else 0))
            self.assertGreater(sum(bool(v) for v in visible.get_flattened_data()), 100,
                               'A sleeve edit must change visible cloth, not transparent RGB')
            self.assertFalse(ImageChops.multiply(delta, ImageChops.invert(cry6.sleeve_mask(i))).getbbox())
            self.assertEqual(src.crop((0, 0, 320, 150)).tobytes(), dst.crop((0, 0, 320, 150)).tobytes())
            self.assertEqual(src.getchannel('A').tobytes(), dst.getchannel('A').tobytes())
        for current, approved in [('st_cry.png', 'cry_base.png'), ('st_cry_blink.png', 'cry_blink.png')]:
            src = Image.open(cry6.PATCHES/approved).convert('RGBA')
            dst = Image.open(ART/current).convert('RGBA')
            delta = build5.difference_mask(src, dst)
            self.assertTrue(delta.getbbox())
            self.assertFalse(ImageChops.multiply(delta, ImageChops.invert(cry6.sleeve_mask(0, 240))).getbbox())
            self.assertEqual(src.getchannel('A').tobytes(), dst.getchannel('A').tobytes())

    def test_approved_sources_and_untouched_sd(self):
        record = json.loads((HERE/'provenance6.json').read_text(encoding='utf-8'))
        for path, expected in record['unchanged_sha256'].items():
            self.assertEqual(sha(ROOT/path), expected, path)
        for p in cry6.PATCHES.iterdir():
            self.assertLessEqual(p.stat().st_size, 80000, p.name)

    def test_generation_limits_and_references(self):
        prompts = json.loads((HERE/'prompts6.json').read_text(encoding='utf-8'))
        names = ('confident', 'thoughtful', 'notes') + build5.NAMES
        for name in names:
            calls = [c for c in prompts['calls'] if c['name'] == name]
            self.assertGreaterEqual(len(calls), 1, name)
            self.assertLessEqual(len(calls), 2, name)
            for c in calls:
                # Old art2 style is not a source; thoughtful edit uses its new output.
                self.assertFalse(any('masters2/' in r.replace('\\', '/') for r in c['reference_paths']))
        self.assertEqual(set(c['name'] for c in prompts['calls'] if c['name'].startswith('doya')),
                         {'doya10', 'doya18', 'doya25'})

    def test_full_portrait_rebuild_is_identical(self):
        paths = list(ART.glob('*.png')) + list(ART.glob('*.webp'))
        before = {p: sha(p) for p in paths}
        result = subprocess.run([sys.executable, '-B', '-X', 'utf8', str(HERE/'build6.py')],
                                cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertEqual(before, {p: sha(p) for p in paths})


if __name__ == '__main__':
    unittest.main()
