"""시즌 재생성으로 학습 기본값·상한·확대 배수가 되돌아가지 않도록 검사."""
import json
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[1]
config = runpy.run_path(str(ROOT / 'tools/build_cosmo_raid.py'))['SEARCH']
data = json.loads((ROOT / 'data/cosmo_raid.json').read_text(encoding='utf8'))['search']
assert config == data, '빌더 SEARCH와 공개 탐색 설정이 다름'
assert config['learned']['value'] is True
assert config['learned']['maxScoreCombos'] == 2_000_000
assert config['learned']['fallbackMultiplier'] == 4
assert config['maxCombos'] == 363_000
print('PASS learned default/config parity')
