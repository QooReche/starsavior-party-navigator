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
import build4

NEW_NAMES = ('cry','verdict','cheer','sulk','shy','doze','think','magnify',
             'stamp','board','coffee','stakeout','zap')
NEW_CONTINUOUS = ('think','magnify','stamp','board','coffee','stakeout','zap')
BLINK_NAMES = ('ready','welcome','investigate','files','report','think',
               'shy','sulk','verdict','cheer')
ART4_NAMES = ('run','point','jump','guide2','present','train','charge','wait','peek','wake')
ART4_BLINKS = ('guide2','present','train','charge','wait','peek','wake')


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

    def test_official_style_legacy_portraits(self):
        for name in ('confident', 'thoughtful', 'notes'):
            master = ROOT/'tools/gwen_art/masters2'/(name+'.webp')
            self.assertLessEqual(master.stat().st_size, BUDGET['file_bytes'])
            with Image.open(master) as im:
                self.assertEqual(im.size, (640, 320))
            with Image.open(ART/(name+'.webp')) as im:
                self.assertEqual(im.size, (240, 240))
                self.assertEqual(im.n_frames, 3)
                durations = []
                for i in range(3):
                    im.seek(i); im.load(); durations.append(im.info['duration'])
                self.assertEqual(durations, [450, 220, 330])

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


class GwenArt4(unittest.TestCase):
    def test_required_assets_size_alpha_and_budget(self):
        self.assertEqual(build4.NAMES,ART4_NAMES)
        for path in build4.output_paths():
            with self.subTest(path=path):
                self.assertTrue(path.is_file(),path)
                self.assertLessEqual(path.stat().st_size,BUDGET['file_bytes'])
                with Image.open(path) as im:
                    size=512 if path.stem.endswith('_512') else 160
                    self.assertEqual(im.size,(size,size))
                    if path.suffix=='.png':
                        self.assertEqual(im.n_frames,1)
                    for i in range(im.n_frames):
                        im.seek(i)
                        alpha=im.convert('RGBA').getchannel('A')
                        self.assertEqual(alpha.getextrema(),(0,255))
                        if path.parent != build4.PATCHES:  # Eye patches deliberately use binary masks.
                            self.assertTrue(any(0<a<255 for a in alpha.get_flattened_data()))
                        box=alpha.getbbox()
                        self.assertGreater(min(box[:2]),0)
                        self.assertLess(max(box[2:]),size)
        pairs=sum((ART/(n+s)).stat().st_size for n in ART4_NAMES for s in ('.png','.webp'))
        blinks=sum((ART/(n+'_blink.png')).stat().st_size for n in ART4_BLINKS)
        self.assertLessEqual(pairs,BUDGET['art4_pairs_bytes'])
        self.assertLessEqual(blinks,BUDGET['art4_blink_bytes'])

    def test_actions_frames_loop_and_duration(self):
        for name in ART4_NAMES:
            with self.subTest(name=name),Image.open(ART/(name+'.webp')) as im:
                expected=[200]*4 if name=='run' else [400,600] if name=='jump' else [300,200,200,300]
                self.assertEqual(im.n_frames,len(expected))
                self.assertEqual(im.info['loop'],0 if name in ('run','wait','charge') else 1)
                frames=[];durations=[]
                for i in range(im.n_frames):
                    im.seek(i);im.load()
                    frames.append(im.convert('RGBA'));durations.append(im.info['duration'])
                self.assertEqual(durations,expected)
                self.assertTrue(any(build3.difference_mask(frames[0],f).getbbox() for f in frames[1:]))
                if name in ('run','jump'):
                    self.assertEqual(len({f.tobytes() for f in frames}),len(expected))

    def test_run_floor_and_scale(self):
        masters=build4.action_frames('run')
        self.assertEqual(len(masters),4)
        self.assertEqual(len({m.tobytes() for m in masters}),4)
        for size,frames in ((512,masters),(160,self._decoded('run'))):
            floors=[f.getchannel('A').point(lambda a:255 if a>=128 else 0).getbbox()[3] for f in frames]
            self.assertEqual(len(set(floors)),1,('Run baseline drift',size,floors))
            self.assertEqual(floors[0],482 if size==512 else 151)
        # Scale stays comparable; profile direction is checked on the visual sheet.
        heights=[m.getchannel('A').getbbox()[3]-m.getchannel('A').getbbox()[1] for m in masters]
        self.assertLess(max(heights)-min(heights),55)

    @staticmethod
    def _decoded(name):
        with Image.open(ART/(name+'.webp')) as im:
            frames=[]
            for i in range(im.n_frames):
                im.seek(i);frames.append(im.convert('RGBA'))
            return frames

    def test_blinks_change_only_eyes(self):
        self.assertEqual(build4.BLINK_NAMES,ART4_BLINKS)
        for name in ART4_BLINKS:
            with self.subTest(name=name):
                original=build4.load(ART/(name+'.png'))
                blink=build4.load(ART/(name+'_blink.png'))
                for src,closed,mask in ((original,blink,build4.eye_mask(name,160)),
                        (build4.load(ART/(name+'_512.png')),build4.blink_master(name),build4.eye_mask(name))):
                    diff=build3.difference_mask(src,closed)
                    self.assertTrue(diff.getbbox(),'Blink is identical to open image')
                    self.assertFalse(ImageChops.multiply(diff,ImageChops.invert(mask)).getbbox(),
                                     'Pixels outside eye mask changed')
                    self.assertEqual(src.getchannel('A').tobytes(),closed.getchannel('A').tobytes())
                    self.assertLess(sum(bool(v) for v in mask.get_flattened_data()),src.width*src.height*.04)
                self.assertEqual(blink.tobytes(),build4.blink_static(name).tobytes())

    def test_motion_semantics_and_locality(self):
        for name,box in (('wait',(195,405,302,485)),('charge',(245,280,274,295))):
            src=build4.load(ART/(name+'_512.png'))
            from PIL import ImageDraw
            allowed=Image.new('L',src.size)
            ImageDraw.Draw(allowed).rectangle(box,fill=255)
            frames=build4.action_frames(name,src)
            self.assertEqual(frames[0].tobytes(),frames[-1].tobytes())
            for frame in frames[1:3]:
                diff=build3.difference_mask(src,frame)
                self.assertTrue(diff.getbbox(),name+' must move')
                self.assertFalse(ImageChops.multiply(diff,ImageChops.invert(allowed)).getbbox(),name)
        src=build4.load(ART/'train_512.png')
        lifted=build4.action_frames('train',src)[2]
        # Dumbbell/glove silhouette rises, while face and feet stay unchanged.
        def weight_top(frame):
            # Neutral gray weights, excluding the purple hair in the same box.
            rows=[]
            for y in range(235,315):
                pixels=[frame.getpixel((x,y)) for x in range(95,185)]
                count=sum(a>200 and abs(r-g)<8 and max(r,g,b)-min(r,g,b)<24 and 65<r<165
                          for r,g,b,a in pixels)
                if count>=5:
                    rows.append(y)
            self.assertTrue(rows,'Dumbbell weight is missing')
            return min(rows)
        self.assertLess(weight_top(lifted),weight_top(src)-10)
        self.assertEqual(src.crop((220,0,512,250)).tobytes(),lifted.crop((220,0,512,250)).tobytes())
        self.assertEqual(src.crop((0,370,512,512)).tobytes(),lifted.crop((0,370,512,512)).tobytes())
        air,land=build4.action_frames('jump')
        self.assertLess(air.getchannel('A').getbbox()[3],land.getchannel('A').getbbox()[3]-30)
        self.assertEqual(land.getchannel('A').point(lambda a:255 if a>=128 else 0).getbbox()[3],482)
        wake=build4.action_frames('wake')
        self.assertEqual(wake[0].tobytes(),build4.blink_master('wake').tobytes())
        self.assertEqual(wake[-1].tobytes(),build4.load(ART/'wake_512.png').tobytes())

    def test_builder_validation_and_reproducibility(self):
        build4.validate_outputs()
        paths=build4.output_paths()
        before={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
        result=subprocess.run([sys.executable,'-B','-X','utf8',str(ROOT/'tools/gwen_art/build4.py')],
                              cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertEqual(before,{p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})


if __name__=='__main__':
    unittest.main()
