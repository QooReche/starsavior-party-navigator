"""Corrupt one art4 asset at a time, require failure, restore exact bytes."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
ART=ROOT/'assets/ui_icons/gwen'
FRAMES=Path(__file__).resolve().parent/'frames4'
LOG=ROOT/'_tmp/art4'


def webp_field(path,chunk,offset,value,length):
    data=bytearray(path.read_bytes())
    pos=12
    while pos+8<=len(data):
        size=int.from_bytes(data[pos+4:pos+8],'little')
        if data[pos:pos+4]==chunk:
            data[pos+8+offset:pos+8+offset+length]=value.to_bytes(length,'little')
            path.write_bytes(data)
            return
        pos+=8+size+(size%2)
    raise AssertionError('Missing WebP chunk')


def outside(path):
    with Image.open(path) as im:
        pic=im.convert('RGBA')
    pic.putpixel((1,1),(255,0,0,255));pic.save(path)


def floor(path):
    with Image.open(path) as im:
        src=im.convert('RGBA')
    pic=Image.new('RGBA',src.size);pic.alpha_composite(src,(0,-6));pic.save(path)


def opaque(path):
    with Image.open(path) as im:
        pic=im.convert('RGB')
    pic.save(path)


def still(path):
    with Image.open(path) as im:
        pic=im.convert('RGBA')
    pic.save(path,format='WEBP',quality=88,method=6)


def main():
    LOG.mkdir(parents=True,exist_ok=True)
    cases=[
        ('blink-identical',ART/'guide2_blink.png',lambda p:p.write_bytes((ART/'guide2.png').read_bytes()),'test_blinks_change_only_eyes','Blink is identical'),
        ('blink-outside',ART/'guide2_blink.png',outside,'test_blinks_change_only_eyes','Pixels outside eye mask changed'),
        ('run-floor',FRAMES/'run_1_512.png',floor,'test_run_floor_and_scale','Run baseline drift'),
        ('run-loop',ART/'run.webp',lambda p:webp_field(p,b'ANIM',4,1,2),'test_actions_frames_loop_and_duration','1 != 0'),
        ('point-duration',ART/'point.webp',lambda p:webp_field(p,b'ANMF',12,100,3),'test_actions_frames_loop_and_duration','Lists differ'),
        ('run-still',ART/'run.webp',still,'test_actions_frames_loop_and_duration','1 != 4'),
        ('point-opaque',ART/'point.png',opaque,'test_required_assets_size_alpha_and_budget','255, 255'),
        ('point-missing',ART/'point.png',lambda p:p.unlink(),'test_required_assets_size_alpha_and_budget','False is not true'),
        ('point-oversize',ART/'point.png',lambda p:p.write_bytes(p.read_bytes()+bytes(80001-p.stat().st_size)),'test_required_assets_size_alpha_and_budget','80001 not less than or equal to 80000'),
    ]
    results=[]
    for name,path,mutate,test,reason in cases:
        original=path.read_bytes()
        digest=hashlib.sha256(original).hexdigest()
        try:
            mutate(path)
            result=subprocess.run([sys.executable,'-B','-X','utf8','-I',
                'tests/gwen_art_test.py','GwenArt4.'+test],cwd=ROOT,
                capture_output=True,text=True,encoding='utf-8')
            output=result.stdout+result.stderr
            (LOG/f'mutation-{name}.log').write_text(output,encoding='utf-8')
            assert result.returncode!=0 and 'FAIL' in output and reason in output,(name,output)
        finally:
            path.write_bytes(original)
            assert hashlib.sha256(path.read_bytes()).hexdigest()==digest,'Restore failed'
        results.append({'case':name,'detected':True,'restored_sha256':digest})
        print(name+': detected, restored',flush=True)
    (LOG/'mutations.json').write_text(json.dumps(results,indent=2),encoding='utf-8')


if __name__=='__main__':
    main()
