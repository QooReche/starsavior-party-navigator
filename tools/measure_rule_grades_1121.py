"""남은 가정 등급 규칙의 기본 경로 실행 횟수·결과 계측(2026-11-21). 단일 프로세스, 공개 standard 입력만.

python -X utf8 -I tools/measure_rule_grades_1121.py NAME
  옛 --legacy-target(가중 추첨 enemy_auto_target=weighted)은 11/22 코드째 삭제 — 태그 engine-legacy-final 에만 있음.
  결과: local/rule-grades/NAME.json (무시 폴더). 표준 출력엔 시나리오별 진행도·클리어·계측만.

계측(판 합계):
  rule1001         = 적 단일 대상 클라 규칙 1001 필터(NKM:7766-7809)
  ranked_priority  = 적 스킬 설명 「~가 가장 높은 적 우선」 근사가 후보를 고른 횟수
  enemy_cd_legacy  = 적 시작 쿨을 enemy_init_cd·enemy_init_cd_special 로 정한 슬롯 수
  enemy_spawn_flag_missing = 배치 표시가 없어 등급 규칙(보스 S/그 밖 A)으로 대신한 적 수
  nova_bursts      = 노바 버스트(수동 정책에서만; manual_burst 가 고르는 경로)
  unsup depth/cond = 안전 상한(max_depth)·파서 정책(unknown_cond)이 실제로 걸린 횟수
"""
import json
from collections import Counter
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from battlesim.api import simulate
from battlesim import mc as mcmod
from battlesim.mc import Battle, Unit

TEAM = ['gwen', 'amora', 'frey', 'claire']
CASES = [
    ('moon100', TEAM, {'stage': 'clo/달 회랑/FLOOR 100'}),
    ('sun200', TEAM, {'stage': 'clo/태양 회랑/FLOOR 200'}),
    ('sun250', TEAM, {'stage': 'clo/태양 회랑/FLOOR 250'}),
    ('cosmo-gille1', TEAM, {'stage': 'cosmo/길레/길레 1단계'}),
    ('raid-mogulus', TEAM, {'cosmo_raid': {'boss': 'mogulus', 'step': 3, 'level': 0}}),
    ('guild', TEAM, {'guild': {'level': 0}}),
]


def main():
    name = sys.argv[1]
    rows = []
    counts = Counter()
    orig = dict(run=Battle.run, filt=Battle.filter_pick,
                ranked=Battle.ranked_enemies, reset=Unit.reset_initial_cooldowns)

    def filt(self, att, pool, steps, ctx=None):
        if steps is mcmod.RULE1001:
            counts['rule1001'] += 1
        return orig['filt'](self, att, pool, steps, ctx)

    def ranked(self, desc, pool, priority=False):
        out = orig['ranked'](self, desc, pool, priority)
        if priority and out:
            counts['ranked_priority'] += 1
        return out

    def reset(self):
        if self.side == 1:
            if self.b.mc.get('enemy_spawn', 'data') != 'data':
                counts['enemy_cd_legacy'] += sum(1 for s in self.d.skills.values() if s.cd)
            elif getattr(self.d, 'spawn', None) is None:
                counts['enemy_spawn_flag_missing'] += 1
        return orig['reset'](self)

    def run(b):
        result = orig['run'](b)
        counts['nova_bursts'] += sum(b.nova_bursts.values())
        for k, v in b.unsup.items():
            if k.startswith(('depth:', 'cond:')):
                counts['unsup ' + k.split(':')[0]] += v
        return result

    for case, party, encounter in CASES:
        counts.clear()
        opts = dict(build='standard', n_runs=8, seed=20261121)
        with patch.object(Battle, 'run', run), \
             patch.object(Battle, 'filter_pick', filt), patch.object(Battle, 'ranked_enemies', ranked), \
             patch.object(Unit, 'reset_initial_cooldowns', reset):
            r = simulate(party, encounter, opts)
        assert r['outcome']['progress'] > 0, case
        scores = (r.get('cosmo_raid') or {}).get('score_runs') or (r.get('guild') or {}).get('score_runs')
        row = dict(name=case, encounter=encounter, clear_p=r['outcome']['clear_p'],
                   progress=r['outcome']['progress'],
                   compare=round(sum(scores) / len(scores), 4) if scores else round(100 * sum(r['prog_runs']) / len(r['prog_runs']), 4),
                   counts=dict(counts), assumptions=sorted(x['rule'] for x in r['assumptions_used']))
        rows.append(row)
        print(case, row['progress'], row['clear_p'], row['compare'], dict(counts), flush=True)
    dest = ROOT / 'local' / 'rule-grades'
    dest.mkdir(parents=True, exist_ok=True)
    (dest / (name + '.json')).write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
