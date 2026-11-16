"""Deliberately damage art5 outputs, require test failure, restore exact bytes."""
import hashlib
from pathlib import Path
import subprocess
import sys
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT/'assets/ui_icons/gwen'
LOGS = ROOT/'_tmp/art5'
PY = [sys.executable, '-B', '-X', 'utf8', '-I', 'tests/gwen_art5_test.py']


def mutate_image(path, kind):
    with Image.open(path) as im:
        pic = im.convert('RGBA')
    if kind == 'size':
        pic = pic.resize((120, 120))
    elif kind == 'alpha':
        pic.putalpha(255)
    elif kind == 'outside':
        pic.putpixel((1, 1), (255, 0, 255, 255))
    pic.save(path)


def riff_field(path, tag, offset, width, value):
    data = bytearray(path.read_bytes())
    pos = 12
    while pos < len(data):
        size = int.from_bytes(data[pos+4:pos+8], 'little')
        if data[pos:pos+4] == tag:
            start = pos+8+offset
            data[start:start+width] = value.to_bytes(width, 'little')
            path.write_bytes(data)
            return
        pos += 8+size+(size % 2)
    raise AssertionError('Missing RIFF chunk '+repr(tag))


def run_case(label, path, change, method, expected):
    original = path.read_bytes()
    try:
        change(path)
        result = subprocess.run(PY+['GwenArt5.'+method], cwd=ROOT, capture_output=True)
        output = result.stdout+result.stderr
        (LOGS/('mutation-'+label+'.log')).write_bytes(output)
        assert result.returncode != 0, label+' mutation survived'
        assert expected.encode() in output, label+' failed for unexpected reason'
        print(label+': detected', flush=True)
    finally:
        path.write_bytes(original)
        assert path.read_bytes() == original, label+' restore failed'


def main():
    LOGS.mkdir(parents=True, exist_ok=True)
    paths = list(ART.glob('st_*')) + list((ROOT/'tools/gwen_art/masters5').glob('*.webp'))
    before = {p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    png, webp, blink = (ART/('st_cry'+s) for s in ('.png', '.webp', '_blink.png'))
    cases = [
        ('missing', png, lambda p:p.unlink(), 'test_files_size_and_alpha', 'is_file'),
        ('size', png, lambda p:mutate_image(p, 'size'), 'test_files_size_and_alpha', '120'),
        ('alpha', png, lambda p:mutate_image(p, 'alpha'), 'test_files_size_and_alpha', '255'),
        ('file-budget', png, lambda p:p.write_bytes(p.read_bytes()+bytes(80000)), 'test_files_size_and_alpha', '80000'),
        ('frozen-action', webp, lambda p:Image.open(png).save(p, format='WEBP'), 'test_actions', '1 != 3'),
        ('loop', webp, lambda p:riff_field(p,b'ANIM',4,2,0), 'test_actions', '0 != 1'),
        ('duration', webp, lambda p:riff_field(p,b'ANMF',12,3,900), 'test_actions', '900'),
        ('blink-identical', blink, lambda p:p.write_bytes(png.read_bytes()), 'test_blinks', 'Blink is identical'),
        ('blink-outside', blink, lambda p:mutate_image(p,'outside'), 'test_blinks', 'Pixels outside eye mask changed'),
    ]
    for args in cases:
        run_case(*args)
    assert before == {p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    print(str(len(cases))+' mutations detected; all 40 asset/master files restored byte-for-byte.')


if __name__ == '__main__':
    main()
