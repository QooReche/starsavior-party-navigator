"""Compose the extracted Auto Journey background; input is a private PNG directory.

Usage: python tools/build_journey_lane.py <extracted PNG directory>
Only the cropped WebP is distributed. See tools/gwen_art/lane.md.
"""
import argparse
from pathlib import Path
from PIL import Image

LAYERS = ['BG', 'CLOUD', 'BACK02', 'BACK01', 'BOTTOM_02', 'BOTTOM', 'FRONT']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('source', type=Path)
    args = ap.parse_args()
    scene = Image.new('RGBA', (2048, 948))
    for name in LAYERS:
        layer = Image.open(args.source / ('AUTO_JOURNEY_00_' + name + '.png')).convert('RGBA')
        assert layer.size == scene.size
        # Adapt the pavement to the bottom of the website's reserved track.
        scene.alpha_composite(layer, (0, 280 if name == 'BOTTOM' else 0))
    scene = scene.crop((0, 500, 2048, 935)).resize((1600, 340), Image.Resampling.LANCZOS).convert('RGB')
    dest = Path(__file__).resolve().parents[1] / 'assets/ui_icons/journey_lane.webp'
    scene.save(dest, 'WEBP', quality=75, method=6)
    assert dest.stat().st_size <= 80000
    print(dest.name, scene.size, dest.stat().st_size)


if __name__ == '__main__':
    main()
