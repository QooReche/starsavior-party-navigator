"""작전 42-12 TURN 1 〈영혼 구속〉 효과 적중 판정 항목 계측(읽기 전용).

ingame_check 와 같은 입력·시드로 돌리고 Battle.roll_hit 에 가로채기만 건다(계산 불변).
전역 턴 1(보스 특수기)에서 굴린 판정마다 시전자 효과 적중·대상 효과 저항·절대 저항·상성 항·최종 확률을 모은다.
원값은 저장소 밖에만 쓴다. 공개 문서엔 비율만 옮긴다.
"""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools')]
import ingame_check as check
from battlesim.mc import Battle, ELEM_BEATS, ELEM_LOSES
from battlesim.engine import calc_hit
from battlesim import rules as _rules


def terms(b, owner, ctx, x):
    """mc.roll_hit 과 같은 식으로 항목을 다시 계산(엔진 값과 같은지 확인용)."""
    hit = owner.d.stats.get('eh', 10000) / 10000.0 + owner.d.passive['eh'] + owner.mods()['eh']
    if ctx is not None and ctx.src is owner:
        hit += ctx.eh
    xm = x.mods()
    er = x.d.stats.get('er', 0) / 10000.0 + xm['er']
    elem = 0.0
    if owner.element and x.element:
        if ELEM_BEATS.get(owner.element) == x.element:
            elem = _rules.ELEM_HIT
        elif ELEM_LOSES.get(owner.element) == x.element:
            elem = -_rules.ELEM_HIT
    der = x.d.stats.get('der', 0) / 10000.0 + xm['der']
    dhit = owner.d.stats.get('dhit', 0) / 10000.0
    adher = x.d.stats.get('adher', 0) / 10000.0 if ELEM_LOSES.get(owner.element) == x.element else 0.0
    a = hit - er + elem
    bb = dhit - der - adher
    return dict(caster=owner.name, caster_elem=owner.element, target=x.name, target_elem=x.element,
                eh=round(hit, 4), eh_base=owner.d.stats.get('eh', 10000), eh_passive=owner.d.passive['eh'],
                eh_mod=owner.mods()['eh'], er=round(er, 4), er_base=x.d.stats.get('er', 0), er_mod=xm['er'],
                der=round(der, 4), elem=elem, a=round(a, 4), b=round(bb, 4), p=round(calc_hit(a, bb), 4))


def measure(stage, runs, seed, myinfo, override=None):
    orig = Battle.roll_hit
    orig_run = Battle.run
    per = defaultdict(Counter)   # (효과, 대상) -> Counter(rolls, hits)
    sample = {}
    battles = []                 # 판마다 (결과, {대상: 적중 여부})

    def roll_hit(b, owner, ctx, x, name):
        r = orig(b, owner, ctx, x, name)
        if b.global_turns <= 1 and owner.side != x.side:
            key = (name, x.name)
            per[key]['rolls'] += 1
            per[key]['hits'] += int(r)
            b.__dict__.setdefault('_t1', {})[x.name] = bool(r)
            if key not in sample:
                sample[key] = terms(b, owner, ctx, x)
        return r

    def run(b):
        res = orig_run(b)
        battles.append((b.result, dict(b.__dict__.get('_t1', {}))))
        return res

    with patch.object(Battle, 'roll_hit', roll_hit), patch.object(Battle, 'run', run):
        summary = check.run(stage, runs, override, seed, myinfo=myinfo, bs_real=True)
    assert len(battles) == runs, (len(battles), runs)
    rows = []
    for (eff, tgt), c in sorted(per.items(), key=lambda kv: (str(kv[0][0]), kv[0][1])):
        rows.append(dict(effect=eff, rolls=c['rolls'], hit_rate=round(c['hits'] / c['rolls'], 4),
                         **sample[(eff, tgt)]))
    # 저항(빗나감) 수별 판 비율·클리어율, 그리고 «프로페서M 만 걸림» 판
    by_resist = defaultdict(Counter)
    for result, t1 in battles:
        k = sum(1 for v in t1.values() if not v)
        by_resist[k]['n'] += 1
        by_resist[k]['clear'] += int(result == 'clear')
        if t1 and [n for n, v in t1.items() if v] == ['프로페서M']:
            by_resist['only_pm']['n'] += 1
            by_resist['only_pm']['clear'] += int(result == 'clear')
    wins = sum(1 for r, _ in battles if r == 'clear')
    resist_table = {str(k): dict(share=round(c['n'] / runs, 4), clear=round(c['clear'] / c['n'], 4) if c['n'] else None,
                                 share_of_wins=round(c['clear'] / wins, 4) if wins else None)
                    for k, c in sorted(by_resist.items(), key=lambda kv: str(kv[0]))}
    return dict(stage=stage, runs=runs, seed=seed, sim_clear=summary.get('sim_clear'), rows=rows, resist_table=resist_table)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--only', choices=check.SAMPLES, default='op4212')
    p.add_argument('--myinfo', required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--runs', type=int, default=1000)
    p.add_argument('--seed', type=int, default=7)
    p.add_argument('--ov', type=json.loads)
    a = p.parse_args()
    if a.output.resolve().is_relative_to(ROOT):
        p.error('비공개 결과는 저장소 밖에만')
    if a.output.resolve() == Path(a.myinfo).resolve():
        p.error('입력 파일을 덮어쓰지 않음')
    check.low_priority()
    out = measure(a.only, a.runs, a.seed, a.myinfo, a.ov)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print('clear', out['sim_clear'], 'saved', a.output)
    for r in out['rows']:
        print(f"{r['effect']} -> {r['target']}: 굴림 {r['rolls']} 실측 {r['hit_rate']:.3f} 식 {r['p']:.3f} "
              f"(a={r['a']:+.2f} b={r['b']:+.2f} 상성={r['elem']:+.1f})")
    for k, v in out['resist_table'].items():
        print(f"저항 {k}: 판 {v['share']:.4f} 클리어 {v['clear']} 이긴 판 중 {v['share_of_wins']}")


if __name__ == '__main__':
    main()
