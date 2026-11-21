"""chain_timing 통합 큐 전후(standard 공개 육성, 계정 자료 없음, 워커·브라우저 없음).

before = chain_timing=client_mapped(11/21 round2 기본값), after = 현재 기본(client_queue).
점수: 코스모 시즌 전투만 게임 점수, 나머지는 진행도×100. 같은 시드 8판 단일 프로세스.
"""
from collections import Counter
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from battlesim import api   # noqa: E402
from battlesim.mc import Battle   # noqa: E402

BASE = ['fei', 'amora', 'frey', 'claire']
CRIS = ['cristelle', 'smile', 'amora', 'claire']
CASES = [
    ('작전 6-7', BASE, {'stage': 'op/아가논 광장/SECTOR 6-7'}),
    ('작전(어려움) 4-6', BASE, {'stage': 'oph/NOA 행정지구/SECTOR 4-6'}),
    ('성간 회랑 28', BASE, {'stage': 'clo/성간 회랑/FLOOR 28'}),
    ('혹한의 습격 Ⅰ', BASE, {'stage': 'equip/혹한의 습격/혹한의 습격 Ⅰ'}),
    ('공허열반자 Ⅰ', BASE, {'stage': 'rush/공허열반자/공허열반자 Ⅰ'}),
    ('이형의 공세 Ⅰ', BASE, {'stage': 'clash/이형의 공세/이형의 공세 Ⅰ'}),
    ('코스모 길레 1단계(스테이지)', BASE, {'stage': 'cosmo/길레/길레 1단계'}),
    ('길드 BFB 1단계(스테이지)', BASE, {'stage': 'guild/BFB/길드 방어전 1단계'}),
    ('크리스텔·벨그라스 1단계(스테이지)', CRIS, {'stage': 'cosmo/벨그라스/벨그라스 1단계'}),
    ('크리스텔·모굴루스3', CRIS, {'cosmo_raid': {'boss': 'mogulus', 'step': 3, 'level': 0}}),
    ('크리스텔·회랑250', CRIS, {'stage': 'clo/태양 회랑/FLOOR 250'}),
]
KEYS = ('chain_timing_queued', 'chain_timing_applied', 'chain_timing_unmapped', 'chain_timing_mixed_fallback',
        'chain_timing_retarget', 'add_damage_queue_applied', 'belgras_fixed_applied')


def measure(cases=CASES, n_runs=8):
    rows = []
    original = Battle.run
    for name, party, encounter in cases:
        for mode, overrides in (('before', {'chain_timing': 'client_mapped'}), ('after', {})):
            counts = Counter()

            def run(b):
                result = original(b)
                counts.update(b.rule_hits)
                return result
            with patch.object(Battle, 'run', run):
                r = api.simulate(party, encounter, dict(build='standard', n_runs=n_runs, seed=20261121,
                                                       rules_override=overrides))
            scores = r.get('cosmo_raid', {}).get('score_runs') or [p * 100 for p in r['prog_runs']]
            row = dict(name=name, mode=mode, score=sum(scores) / len(scores), clear=r['outcome']['clear_p'],
                       counts={k: counts[k] for k in KEYS if counts[k]})
            rows.append(row)
            print(name, mode, round(row['score'], 5), row['clear'], row['counts'], flush=True)
    return rows


if __name__ == '__main__':
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    rows = measure()
    if out:
        out.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding='utf-8')
