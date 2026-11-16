"""Prove cry preservation, sleeve presence, SD hashes and legacy timing tests fail."""
import hashlib
from pathlib import Path
import subprocess
import sys
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
ART = ROOT/'assets/ui_icons/gwen'


def change_pixel(path):
    im = Image.open(path).convert('RGBA')
    im.putpixel((120, 70), (255, 0, 0, 255))
    im.save(path)


def remove_sleeve_edit(path):
    # Replace patch pixels with their exact approved source: the edit disappears.
    im = Image.open(HERE/'masters5/st_cry.webp').convert('RGBA')
    im.save(path, lossless=True, exact=True, method=6)


def wrong_timing(path):
    with Image.open(path) as im:
        frames = []
        for i in range(3):
            im.seek(i); frames.append(im.convert('RGBA'))
    frames[0].save(path, save_all=True, append_images=frames[1:],
                   duration=[400, 220, 330], loop=1, quality=88, method=6)


def main():
    cases = [
        ('cry-face', ART/'st_cry.png', change_pixel, 'gwen_art6_test.py',
         'GwenArt6.test_approved_cry_pixels_and_real_sleeve_change'),
        ('missing-sleeves', HERE/'patches6/cry_sleeves.webp', remove_sleeve_edit,
         'gwen_art6_test.py', 'GwenArt6.test_approved_cry_pixels_and_real_sleeve_change'),
        ('sd-modified', ART/'cry.png', change_pixel, 'gwen_art6_test.py',
         'GwenArt6.test_approved_sources_and_untouched_sd'),
        ('legacy-timing', ART/'confident.webp', wrong_timing, 'gwen_art_test.py',
         'GwenArt.test_official_style_legacy_portraits'),
    ]
    output = ROOT/'_tmp/art6'
    for label, path, mutate, test_file, test_name in cases:
        backup = path.read_bytes()
        try:
            mutate(path)
            result = subprocess.run([sys.executable, '-B', '-X', 'utf8', '-I',
                                     str(ROOT/'tests'/test_file), test_name],
                                    cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
            (output/('mutation-'+label+'.log')).write_text(result.stdout+result.stderr, encoding='utf-8')
            assert result.returncode != 0 and 'FAIL:' in result.stderr, (label, result.stdout, result.stderr)
            print(label, 'detected')
        finally:
            path.write_bytes(backup)
        assert hashlib.sha256(path.read_bytes()).digest() == hashlib.sha256(backup).digest()


if __name__ == '__main__':
    main()
