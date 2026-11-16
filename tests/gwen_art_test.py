"""Shipping art budgets, true alpha, calm frame timing and one-shot loop metadata."""
import unittest
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from PIL import Image, ImageChops

ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/'assets/ui_icons/gwen'
BUDGET=json.loads((ROOT/'tools/gwen_art/budget.json').read_text(encoding='utf-8'))
sys.path.insert(0,str(ROOT/'tools/gwen_art'))
import build3

NEW_NAMES = ('cry','verdict','cheer','sulk','shy','doze','think','magnify',
             'stamp','board','coffee','stakeout','zap')
NEW_CONTINUOUS = ('think','magnify','stamp','board','coffee','stakeout','zap')
BLINK_NAMES = ('ready','welcome','investigate','files','report','think',
               'shy','sulk','verdict','cheer')


class GwenArt(unittest.TestCase):
    def test_served_budget_and_static_frames(self):
        files=[p for p in ART.iterdir() if p.suffix in ('.png','.webp') and not p.stem.endswith('_512')]
        self.assertLessEqual(sum(p.stat().st_size for p in files),BUDGET['served_bytes'])
        for p in files:
            self.assertLessEqual(p.stat().st_size,BUDGET['file_bytes'],p.name)
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

    def test_new_masters_and_assets(self):
        self.assertEqual(tuple(build3.NAMES),NEW_NAMES)
        for name in NEW_NAMES:
            with self.subTest(name=name):
                for suffix,size in (('_512.png',512),('.png',160),('.webp',160)):
                    path=ART/(name+suffix)
                    self.assertTrue(path.is_file(),path)
                    self.assertLessEqual(path.stat().st_size,BUDGET['file_bytes'],path)
                    with Image.open(path) as im:
                        self.assertEqual(im.size,(size,size))
                        alpha=im.convert('RGBA').getchannel('A')
                        self.assertEqual(alpha.getextrema(),(0,255))
                        x0,y0,x1,y1=alpha.getbbox()
                        self.assertGreater(min(x0,y0),0)
                        self.assertLess(max(x1,y1),size)
                        self.assertTrue(any(0<a<255 for a in alpha.get_flattened_data()),'Antialiased alpha edges required')

    def test_new_action_frames_and_timing(self):
        for name in NEW_NAMES:
            with self.subTest(name=name),Image.open(ART/(name+'.webp')) as im:
                self.assertEqual(im.n_frames,4)
                self.assertEqual(im.info['loop'],0 if name in NEW_CONTINUOUS else 1)
                frames=[];durations=[]
                for n in range(4):
                    im.seek(n);im.load()
                    frames.append(im.convert('RGBA'));durations.append(im.info['duration'])
                    self.assertEqual(frames[-1].getchannel('A').getextrema(),(0,255))
                self.assertEqual(durations,[300,200,200,300])
                self.assertTrue(any(build3.difference_mask(frames[0],f).getbbox() for f in frames[1:]))
                src=Image.open(ART/(name+'_512.png')).convert('RGBA')
                masters=build3.action_frames(name,src)
                self.assertEqual(masters[0].tobytes(),src.tobytes())
                self.assertEqual(masters[-1].tobytes(),src.tobytes())
                # Required motions stay local in the source, before lossy WebP.
                if name in ('zap','coffee','stakeout'):
                    box={'zap':(201,235,249,250),'coffee':(84,169,129,260),
                         'stakeout':(98,210,413,377)}[name]
                    allowed=Image.new('L',(512,512))
                    from PIL import ImageDraw
                    ImageDraw.Draw(allowed).rectangle(box,fill=255)
                    for frame in masters[1:]:
                        outside=ImageChops.multiply(build3.difference_mask(src,frame),ImageChops.invert(allowed))
                        self.assertFalse(outside.getbbox(),name)

    def test_blinks_are_eye_only_static_frames(self):
        self.assertEqual(tuple(build3.BLINK_NAMES),BLINK_NAMES)
        for name in BLINK_NAMES:
            with self.subTest(name=name):
                path=ART/(name+'_blink.png')
                self.assertTrue(path.is_file())
                with Image.open(path) as im:
                    self.assertEqual(im.size,(160,160))
                    self.assertEqual(im.n_frames,1)  # No 200ms animation rule for blinks.
                    blink=im.convert('RGBA')
                original=Image.open(ART/(name+'.png')).convert('RGBA')
                for src,closed,mask in ((original,blink,build3.eye_mask(name,160)),
                        (Image.open(ART/(name+'_512.png')).convert('RGBA'),
                         build3.blink_master(name),build3.eye_mask(name))):
                    changed=build3.difference_mask(src,closed)
                    self.assertTrue(changed.getbbox(),'Blink is identical to open image')
                    self.assertFalse(ImageChops.multiply(changed,ImageChops.invert(mask)).getbbox(),
                                     'Pixels outside eye mask changed')
                    self.assertEqual(src.getchannel('A').tobytes(),closed.getchannel('A').tobytes())
                    self.assertLess(sum(bool(v) for v in mask.get_flattened_data()),src.width*src.height*.04)
                self.assertEqual(blink.tobytes(),build3.blink_static(name).tobytes())
                patch=build3.PATCHES/(name+'_eyes_512.png')
                self.assertLessEqual(patch.stat().st_size,BUDGET['file_bytes'])

    def test_category_budgets_and_builder_validation(self):
        pairs=sum((ART/(n+s)).stat().st_size for n in NEW_NAMES for s in ('.png','.webp'))
        blinks=sum((ART/(n+'_blink.png')).stat().st_size for n in BLINK_NAMES)
        self.assertLessEqual(pairs,BUDGET['new_pairs_bytes'])
        self.assertLessEqual(blinks,BUDGET['blink_bytes'])
        build3.validate_outputs()

    def test_rebuild_is_byte_identical(self):
        paths=[ART/(n+s) for n in NEW_NAMES for s in ('_512.png','.png','.webp')]
        paths += [ART/(n+'_blink.png') for n in BLINK_NAMES]
        paths += sorted(build3.PATCHES.glob('*.png'))
        before={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
        result=subprocess.run([sys.executable,'-B','-X','utf8',str(ROOT/'tools/gwen_art/build3.py')],
                              cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertEqual(before,{p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})


if __name__=='__main__':
    unittest.main()
