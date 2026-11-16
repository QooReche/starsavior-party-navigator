"""Upper-body Gwen assets: budgets, true alpha, one-shot timing, eye isolation."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest
from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT/'assets/ui_icons/gwen'
sys.path.insert(0, str(ROOT/'tools/gwen_art'))
import build5

NAMES = ('st_cry', 'st_verdict', 'st_cheer', 'st_ok', 'st_point',
         'st_shy', 'st_sulk', 'st_wink', 'st_zap', 'st_welcome')
BUDGET = json.loads((ROOT/'tools/gwen_art/budget.json').read_text(encoding='utf-8'))


def digest(paths):
    return {p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


class GwenArt5(unittest.TestCase):
    def test_files_size_and_alpha(self):
        self.assertEqual(tuple(build5.NAMES), NAMES)
        for name in NAMES:
            paths = [(build5.MASTERS/(name+'.webp'), (960, 320))]
            paths += [(ART/(name+suffix), (240, 240)) for suffix in ('.png', '.webp', '_blink.png')]
            for path, size in paths:
                with self.subTest(path=path.name, folder=path.parent.name):
                    self.assertTrue(path.is_file(), path)
                    self.assertLessEqual(path.stat().st_size, BUDGET['file_bytes'], path)
                    with Image.open(path) as im:
                        self.assertEqual(im.size, size)
                        if path.suffix == '.png' or path.parent == build5.MASTERS:
                            self.assertEqual(im.n_frames, 1)
                        for i in range(im.n_frames):
                            im.seek(i)
                            alpha = im.convert('RGBA').getchannel('A')
                            self.assertEqual(alpha.getextrema(), (0, 255))
                            self.assertTrue(any(0 < a < 255 for a in alpha.get_flattened_data()))
                            # All silhouettes remain inset; reject clipped canvas edges.
                            x0, y0, x1, y1 = alpha.getbbox()
                            self.assertGreater(min(x0, y0), 0)
                            self.assertLess(x1, size[0])
                            self.assertLess(y1, size[1])
                            values = list(alpha.get_flattened_data())
                            self.assertGreater(values.count(0), size[0]*size[1]*.25)
                            self.assertGreater(values.count(255), size[0]*size[1]*.15)

    def test_actions(self):
        for name in NAMES:
            with self.subTest(name=name), Image.open(ART/(name+'.webp')) as im:
                self.assertEqual(im.n_frames, 3)
                self.assertEqual(im.info['loop'], 1)
                frames, times = [], []
                for i in range(im.n_frames):
                    im.seek(i); im.load()
                    frames.append(im.convert('RGBA'))
                    times.append(im.info['duration'])
                self.assertEqual(times, [450, 220, 330])
                self.assertEqual(sum(times), 1000)
                # A meaningful decoded change, not just encoder noise.
                delta = ImageChops.difference(frames[0], frames[1])
                changed = sum(max(pixel) > 20 for pixel in delta.get_flattened_data())
                self.assertGreater(changed, 20, 'Action frames are identical')
                masters = build5.action_frames(name)
                self.assertEqual(masters[0].tobytes(), masters[-1].tobytes())
                self.assertTrue(build5.difference_mask(masters[0], masters[1]).getbbox())
                if name in ('st_wink', 'st_zap'):
                    outside = ImageChops.multiply(build5.difference_mask(masters[0], masters[1]),
                                                  ImageChops.invert(build5.motion_mask(name)))
                    self.assertFalse(outside.getbbox(), 'Local motion escaped mask')

    def test_blinks(self):
        for name in NAMES:
            with self.subTest(name=name):
                original = Image.open(ART/(name+'.png')).convert('RGBA')
                blink = Image.open(ART/(name+'_blink.png')).convert('RGBA')
                for src, closed, mask in (
                    (original, blink, build5.eye_mask(name, 240)),
                    (build5.master_frames(name)[0], build5.blink_master(name), build5.eye_mask(name)),
                ):
                    changed = build5.difference_mask(src, closed)
                    self.assertTrue(changed.getbbox(), 'Blink is identical to base image')
                    self.assertFalse(ImageChops.multiply(changed, ImageChops.invert(mask)).getbbox(),
                                     'Pixels outside eye mask changed')
                    self.assertEqual(src.getchannel('A').tobytes(), closed.getchannel('A').tobytes())
                    self.assertLess(sum(bool(v) for v in mask.get_flattened_data()), src.width*src.height*.04)
                self.assertEqual(blink.tobytes(), build5.blink_static(name).tobytes())

    def test_budgets_and_validation(self):
        sizes = build5.validate_outputs()
        self.assertEqual(len(sizes), 30)
        self.assertLessEqual(sum(sizes.values()), BUDGET['art5']['served_bytes'])
        served = [p for p in ART.iterdir() if p.suffix in ('.png', '.webp') and not p.stem.endswith('_512')]
        self.assertLessEqual(sum(p.stat().st_size for p in served), BUDGET['served_bytes'])

    def test_rebuild_and_existing_assets_unchanged(self):
        paths = list(ART.glob('*.png')) + list(ART.glob('*.webp')) + list(build5.MASTERS.glob('*.webp'))
        before = digest(paths)
        result = subprocess.run([sys.executable, '-B', '-X', 'utf8', str(ROOT/'tools/gwen_art/build5.py')],
                                cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertEqual(before, digest(paths))
        self.assertEqual(set(paths), set(ART.glob('*.png')) | set(ART.glob('*.webp')) |
                         set(build5.MASTERS.glob('*.webp')))


if __name__ == '__main__':
    unittest.main()
