# -*- coding: utf-8 -*-
"""엔진 공통 함수 통일(fable_unify 설계) 보강 기준선 — tools/diet_baseline.py 가 안 덮는 경로를 «수정 전 엔진»으로 고정한다.

  - 코스모 시즌 1023 보스 3종 + 지난 시즌 fixture 1022(벨그라스·티리아·카넬리아, tests/fixtures/cosmo_raid_1022.json)
  - 길드 레이드 알리시아의 지원 none + 5종(gust·focus·strike·mountain·fire)
  - 캐릭터 분기 표(marker_se·mc_semantics·mc 대상 규칙) 대상 구원자 14명 + smile 이 든 파티 4개(일반·회랑·코스모·길드)
  - 연쇄 발동: 기본 Battle 연쇄(_apply_chain_amount)·길드 연쇄(_chain)·코스모 응징 큐가
    실제로 탄 판이 있는지 compute(count=True) 로 센다(tests/unify_baseline_test.py 가 > 0 을 확인).
해시 방식은 diet_baseline 과 같다(api.simulate 결과 전체·raw_runs·runs, web.run_auto 문자열).

  python -X utf8 -I tools/unify_baseline.py            # 비교(불일치 0 이면 종료 코드 0)
  python -X utf8 -I tools/unify_baseline.py --write    # 다시 쓰기 — 엔진 결과가 «의도적으로» 바뀐 커밋에서만
"""
import argparse
import json
import os
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from diet_baseline import _h, BASE_OPT  # noqa: E402

GOLDEN = os.path.join(ROOT, 'tests', 'golden', 'unify_baseline.json')
FIXTURE_1022 = os.path.join(ROOT, 'tests', 'fixtures', 'cosmo_raid_1022.json')

# 캐릭터 분기 표 대상(fable_unify 4단계) 14명 + smile. 파티마다 시험 육성(standard)으로 진행도가 나는 조합.
SAVIOR_PARTIES = [
    ('M1', ['lyn', 'elisa', 'ceres', 'lydia']),
    ('M2', ['sunshine-cat-smile', 'wedding-epindel', 'lydia-moon-caster', 'gille']),
    ('M3', ['scarlet', 'cristelle', 'gwen', 'claire']),
    ('M4', ['tyria', 'trish', 'smile', 'fei']),
]
CHAIN_PARTY = ('C', ['fei', 'professor-m', 'emily', 'wedding-carmen'])
GUILD_PARTY = ('G', ['wedding-carmen', 'ceres-sun-supporter', 'amora', 'tyria'])
BELGRAS_PARTY = ('BG', ['frey', 'emily', 'rosaria', 'fei'])


def _cases():
    """(이름, encounter, web stage 인자, web extra, 파티 목록, 시드, 1022 fixture 여부)"""
    out = []
    for stage in ('op/NOA 상업지구/SECTOR 1-3', 'clo/달 회랑/FLOOR 100', 'cosmo/길레/길레 1단계'):
        nm = stage.split('/')[0] + '_' + stage.split('/')[-1].replace(' ', '')
        out.append((nm, {'stage': stage}, stage, {}, SAVIOR_PARTIES, (1, 2), False))
    for boss in ('mogulus', 'baskerville', 'disparity'):
        raid = {'boss': boss, 'step': 3, 'level': 0}
        out.append(('raid_' + boss, {'cosmo_raid': raid}, 'x', {'cosmo_raid': raid},
                    SAVIOR_PARTIES + [CHAIN_PARTY], (1,), False))
    for boss in ('belgras', 'tyria', 'carnelia'):
        for step, level in ((3, 0), (3, 8)):
            raid = {'boss': boss, 'step': step, 'level': level}
            out.append(('raid1022_%s_L%d' % (boss, level), {'cosmo_raid': raid}, 'x', {'cosmo_raid': raid},
                        [BELGRAS_PARTY, SAVIOR_PARTIES[3]], (1, 2), True))
    # 연쇄 EX(모굴루스 15+ no_shield_chain, 카넬리아 12+ punish). 즉시 경로(_imm) 케이스는 chain_timing 삭제(11/22)로 뺐음
    for boss, level, old in (('mogulus', 15, False), ('carnelia', 12, True)):
        raid = {'boss': boss, 'step': 3, 'level': level}
        out.append(('raidex_%s_L%d' % (boss, level), {'cosmo_raid': raid}, 'x', {'cosmo_raid': raid},
                    [CHAIN_PARTY, BELGRAS_PARTY, SAVIOR_PARTIES[2]], (1, 2), old))
    for sup in ('none', 'gust', 'focus', 'strike', 'mountain', 'fire'):
        for level in (1, 5):
            g = {'level': level, 'sets': [0, 0, 0, 0], 'support': sup}
            out.append(('guild_%s_L%d' % (sup, level), {'guild': g}, 'x', {'guild': g},
                        [GUILD_PARTY] + ([SAVIOR_PARTIES[1], SAVIOR_PARTIES[2]] if level == 1 else []), (1, 2), False))
    return out


CASES = _cases()
N_RUNS = 6


def _counters(cnt):
    """연쇄 경로 호출 수를 세는 감싸기(값은 그대로 돌려줌 — 결과 해시 불변). 되돌리기 함수 반환."""
    from battlesim import mc
    from battlesim.starsavior import guild_bfb
    saved = []

    def wrap(obj, name, tag):
        f = getattr(obj, name)
        saved.append((obj, name, f))

        def g(*a, **k):
            cnt[tag] += 1
            return f(*a, **k)
        setattr(obj, name, g)
    wrap(mc.Battle, '_apply_chain_amount', 'battle_chain')
    wrap(mc.Battle, 'queue_punish', 'queue_punish')
    wrap(guild_bfb.Controller, '_chain', 'guild_chain')

    def undo():
        for obj, name, f in saved:
            setattr(obj, name, f)
    return undo


def compute(only=None, count=False):
    from battlesim.api import simulate
    from battlesim import web
    from battlesim.starsavior import cosmo_raid
    out, cnt, per = {}, Counter(), {}
    undo = _counters(cnt) if count else None
    try:
        for case in CASES:
            name, enc, stage, extra, parties, seeds, old = case
            base = BASE_OPT
            if only and not any(w in name for w in only):
                continue
            cosmo_raid.use_data(FIXTURE_1022 if old else None)
            for pk, units in parties:
                for seed in seeds:
                    key = '%s/%s/s%d' % (name, pk, seed)
                    before = Counter(cnt)
                    party = {'units': list(units), 'leader': 0}
                    o = dict(base, n_runs=N_RUNS, seed=seed, per_run=True, raw_runs=True)
                    r = simulate(party, enc, o)
                    full = {k: v for k, v in r.items() if k != 'runtime_ms_per_run'}
                    w = web.run_auto(stage, party, N_RUNS, seed, json.dumps(dict(base, raw_runs=True, **extra)))
                    out[key] = dict(raw_runs=_h(r['raw_runs']), per_run=_h(r['runs']), result=_h(full), web=_h(w),
                                    clear=r['outcome']['clear_p'], prog=r['outcome'].get('progress'))
                    if count:
                        per[key] = dict(cnt - before)
    finally:
        cosmo_raid.use_data(None)
        if undo:
            undo()
    return (out, cnt, per) if count else out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--count', action='store_true', help='연쇄 경로 호출 수도 출력')
    ap.add_argument('only', nargs='*')
    a = ap.parse_args()
    if a.write and a.only:
        ap.error('--write 는 전체 케이스로만')
    sys.path.insert(0, ROOT)
    if a.count:
        got, cnt, per = compute(a.only, count=True)
        print(json.dumps(dict(cnt), ensure_ascii=False))
        for k, v in per.items():
            print(k, got[k]['prog'], got[k]['clear'], v)
    else:
        got = compute(a.only)
    if a.write:
        doc = dict(_note='엔진 공통 함수 통일 보강 기준선(tools/unify_baseline.py --write). 코스모(1022 fixture 포함)·길드 지원 6종·'
                         '분기 표 구원자. %d판, 표준 육성, rules_override power_penalty=model. 해시 = sha256 앞 20자' % N_RUNS,
                   cases=got)
        with open(GOLDEN, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(doc, f, ensure_ascii=False, indent=1, sort_keys=True)
            f.write('\n')
        print('저장', GOLDEN, len(got), '케이스')
        return 0
    want = json.load(open(GOLDEN, encoding='utf-8'))['cases']
    bad = [k for k in got if got[k] != want.get(k)]
    print('케이스 %d / 불일치 %d %s' % (len(got), len(bad), bad[:5]))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
