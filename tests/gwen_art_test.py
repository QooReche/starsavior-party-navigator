"""Shipping art budgets, true alpha, calm frame timing and one-shot loop metadata."""
import unittest
from pathlib import Path
from PIL import Image, ImageChops

ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/'assets/ui_icons/gwen'


class GwenArt(unittest.TestCase):
    def test_served_budget_and_static_frames(self):
        files=[p for p in ART.iterdir() if p.suffix in ('.png','.webp') and not p.stem.endswith('_512')]
        self.assertLessEqual(sum(p.stat().st_size for p in files),640000)
        for p in files:
            self.assertLessEqual(p.stat().st_size,80000,p.name)
            with Image.open(p) as img:
                self.assertEqual(img.convert('RGBA').getchannel('A').getextrema(),(0,255),p.name)
                if p.suffix=='.png':
                    self.assertEqual(img.n_frames,1,p.name)

    def test_animations_are_distinct_and_one_shot(self):
        for name in ['investigate','files','walk','report','surprised','welcome','confident','thoughtful','notes','ready']:
            with Image.open(ART/(name+'.webp')) as img:
                self.assertTrue(2<=img.n_frames<=4,name)
                self.assertEqual(img.info['loop'],0 if name in ['investigate','files','walk'] else 1,name)
                frames=[];total=0
                for n in range(img.n_frames):
                    img.seek(n);frames.append(img.convert('RGBA'))
                    self.assertGreaterEqual(img.info['duration'],200,name)
                    total+=img.info['duration']
                self.assertTrue(any(ImageChops.difference(frames[0],f).convert('RGB').getbbox() for f in frames[1:]),name)
                self.assertEqual(total,1200 if name=='walk' else 1080 if name in ['files','investigate'] else 1000,name)


if __name__=='__main__':
    unittest.main()
