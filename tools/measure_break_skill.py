"""브레이크 스킬 판별 계측(읽기 전용). ingame_check 의 입력·seed·실제 장착을 그대로 쓴다.

판마다 결과·전역 TURN·브레이크 스킬 발동 TURN·영역 시작/종료 TURN·포인트 적립 사건(대상·TURN·양)·
보스 격파 TURN 을 모은다. TURN = 그 행동이 시작될 때의 전역 행동 번호(화면 좌상단 TURN 과 같은 정의,
docs/op4212_gap_1121.md «선택 턴»). 집계만 화면에 찍고, 판별 원값은 --output(저장소 밖)에만 쓴다.

사용:
python -X utf8 -I tools/measure_break_skill.py --only op4212 --myinfo PATH --runs 1000 [--ov JSON] [--output 저장소밖.json]
"""
import argparse
from collections import Counter
from contextlib import ExitStack
import json
from pathlib import Path
import statistics
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools')]
import ingame_check as check
from battlesim.mc import Battle


def measure(stage, runs, seed, myinfo=None, override=None, bs_real=True):
    original = {k: getattr(Battle, k) for k in ('run', '_use_break_skill', '_add_break_points', '_tick_break_domain')}
    trials = []

    def cur(b):
        rec = b.__dict__.get('_bm')
        if rec is None:
            rec = b.__dict__['_bm'] = dict(uses=[], domain=[], points=[], boss_breaks=[], domain_open=None)
        return rec

    def use(b, actor=None):
        before = b.break_skill_uses
        r = original['_use_break_skill'](b, actor)
        if b.break_skill_uses > before:
            rec = cur(b)
            rec['uses'].append(b.global_turns)
            rec['domain_open'] = b.global_turns
        return r

    def add(b, v):
        before = b.break_points
        r = original['_add_break_points'](b, v)
        rec = cur(b)
        boss = bool(getattr(v.d, 'boss', False))
        rec['points'].append(dict(turn=b.global_turns, boss=boss, gained=b.break_points - before,
                                  cd=b.break_skill_cd, new_break=bool(v.sa == 0 and v.breaks and v.__dict__.get('_bm_seen') != v.breaks)))
        if boss and v.__dict__.get('_bm_seen') != v.breaks:
            rec['boss_breaks'].append(b.global_turns)
        v.__dict__['_bm_seen'] = v.breaks
        return r

    def tick(b, clock):
        was = b.break_domain_remaining
        r = original['_tick_break_domain'](b, clock)
        rec = cur(b)
        if was > 0 and b.break_domain_remaining == 0 and rec['domain_open'] is not None:
            rec['domain'].append((rec['domain_open'], b.global_turns))
            rec['domain_open'] = None
        return r

    def run(b):
        result = original['run'](b)
        rec = cur(b)
        trials.append(dict(result=b.result, turns=b.global_turns, uses=rec['uses'], domain=rec['domain'],
                           domain_open_at_end=rec['domain_open'], points=rec['points'], boss_breaks=rec['boss_breaks'],
                           points_gained=b.break_points_gained, points_left=b.break_points))
        return result

    with ExitStack() as scope:
        for name, fn in dict(run=run, _use_break_skill=use, _add_break_points=add, _tick_break_domain=tick).items():
            scope.enter_context(patch.object(Battle, name, fn))
        summary = check.run(stage, runs, override, seed, myinfo=myinfo, bs_real=bs_real)
    assert len(trials) == runs, (len(trials), runs)
    return summary, trials


def aggregate(trials):
    def agg(rows):
        if not rows:
            return None
        n = len(rows)
        uses = Counter(len(r['uses']) for r in rows)
        first = [r['uses'][0] for r in rows if r['uses']]
        second = [r['uses'][1] for r in rows if len(r['uses']) > 1]
        gaps = [r['uses'][i + 1] - r['uses'][i] for r in rows for i in range(len(r['uses']) - 1)]
        life = [e - s + 1 for r in rows for s, e in r['domain']]
        bb = [len(r['boss_breaks']) for r in rows]
        # 첫 발동 뒤 다시 3점이 찰 때까지(=두 번째 발동 가능 시점) 포인트가 모였는지
        after_first = [sum(p['gained'] for p in r['points'] if p['turn'] > r['uses'][0]) for r in rows if r['uses']]
        return dict(n=n, clear=round(sum(r['result'] == 'clear' for r in rows) / n, 4),
                    uses_mean=round(sum(len(r['uses']) for r in rows) / n, 3),
                    uses_dist={k: uses[k] for k in sorted(uses)},
                    first_turn_q10_50_90=check._q(first), second_turn_q10_50_90=check._q(second),
                    gap_q10_50_90=check._q(gaps), domain_life_turns=dict(Counter(life)),
                    turns_q10_50_90=check._q([r['turns'] for r in rows]),
                    points_gained_mean=round(sum(r['points_gained'] for r in rows) / n, 3),
                    boss_breaks_mean=round(statistics.mean(bb), 3),
                    boss_break_first_q=check._q([r['boss_breaks'][0] for r in rows if r['boss_breaks']]),
                    points_after_first_use_mean=round(statistics.mean(after_first), 3) if after_first else None)
    return dict(all=agg(trials), lost=agg([r for r in trials if r['result'] != 'clear']),
                clear=agg([r for r in trials if r['result'] == 'clear']))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--only', choices=check.SAMPLES, default='op4212')
    p.add_argument('--myinfo')
    p.add_argument('--runs', type=int, default=200)
    p.add_argument('--seed', type=int, default=7)
    p.add_argument('--ov', type=json.loads)
    p.add_argument('--output', type=Path, help='판별 원값 저장(저장소 밖만)')
    a = p.parse_args()
    if a.output is not None and a.output.resolve().is_relative_to(ROOT):
        p.error('판별 원값은 저장소 밖에만 저장')
    check.low_priority()
    summary, trials = measure(a.only, a.runs, a.seed, a.myinfo, a.ov)
    out = dict(stage=a.only, runs=a.runs, seed=a.seed, ov=a.ov, sim_clear=summary['sim_clear'],
               break_skill=summary['break_skill'], agg=aggregate(trials))
    print(json.dumps(out, ensure_ascii=False, indent=1))
    if a.output is not None:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(json.dumps(dict(out, trials=trials), ensure_ascii=False) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
