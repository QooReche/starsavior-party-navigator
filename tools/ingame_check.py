# -*- coding: utf-8 -*-
"""인게임 실측(docs/ingame_samples.md)과 확률 엔진을 대조한다 — 「준 피해 ÷ 받은 피해」 비율·클리어 확률·아군 행동 수.

실측 판마다 사용자 능력치 화면 값(공·생·방·속도·치명 등)을 stats_override 로 넣고(화면이 없는 구원자는 남은 전투력 몫으로 표준 육성 배율),
재점화 버프는 전투력 보정 배율에 곱한다(api options.rekindle 과 같은 뜻). 규칙을 바꿔 보려면 --ov '{"basic_tough": 1}'.

사용: python -X utf8 -I tools/ingame_check.py [--runs 100] [--ov JSON] [--only 37-3] [--bs]
--bs = 실측 장착 스킬 「큐브 과부하」 Lv.5 활성화(기본 미장착).
운영 기본값: 36-36=heal, 37-2~37-5=auto. --ov '{"nova_policy":"auto"}' 로 전부 순수 오토 대조 가능.
nova_burst.total/by_unit은 전체 판 합계, uses·heal·healing은 판 평균(실제 HP 회복, 초과 회복 제외).
2026-10-21 결과: 37-2(잡몹) 실제 4.13 vs 시뮬 4.11 일치 / 37-3·36-36(큰 보스) 실제 1.82·1.88 vs 시뮬 0.49·0.84 — 보스전만 과대(설명 docs/ingame_samples.md)
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tools'))

# 사용자 능력치 화면(2026-10-21, Lv.342·공명 10). cr/cd/eh/er 은 1/10000
REAL = {
    'white-pearl-luna': dict(atk=12314, hp=66887, spd=181, cr=6820, cd=7020, eh=17400, er=1500, **{'def': 5206}),
    'wedding-carmen': dict(atk=9972, hp=119367, spd=151, cr=880, cd=6470, eh=10620, er=3216, **{'def': 5811}),
    'cristelle': dict(atk=17903, hp=60168, spd=157, cr=5610, cd=8450, eh=16804, er=2380, **{'def': 4798}),
    # 2026-10-21 2차(파티 전투력 411,163 = 네 명 화면 전투력 합과 정확히 일치)
    'claire': dict(atk=16002, hp=65538, spd=187, cr=5720, cd=11900, eh=11012, er=2412, **{'def': 4915}),
    'professor-m': dict(atk=15196, hp=61258, spd=179, cr=8330, cd=6400, eh=14744, er=2540, **{'def': 5053}),
    'waltz-asherah': dict(atk=9909, hp=95464, spd=183, cr=8730, cd=9710, eh=12268, er=1308, **{'def': 5522}),
}
TEAM2 = ['claire', 'waltz-asherah', 'wedding-carmen', 'professor-m']      # 화면 카드 순서(후열 클레어, 전열 아세라·카르멘, 후열 프로페서M)
# 실측 판: (콘텐츠, 탭|스테이지, 화면 카드 순서[후열1, 전열1, 전열2, 후열2], 리더, 파티 전투력, 재점화 단계, 준 피해, 받은 피해, TURN, 결과)
SAMPLES = {
    '36-36': ('op', '아가논 시가지|SECTOR 36-36', ['wedding-epindel', 'white-pearl-luna', 'wedding-carmen', 'cristelle'], None,
              394578, 3, 990889, 527628, 38, 'clear'),
    '37-2': ('op', '모나스티르 광장|SECTOR 37-2', ['wedding-epindel', 'white-pearl-luna', 'wedding-carmen', 'cristelle'], 'wedding-carmen',
             394578, 0, 1104681, 267286, 52, 'clear'),
    '37-3': ('op', '모나스티르 광장|SECTOR 37-3', ['wedding-epindel', 'white-pearl-luna', 'wedding-carmen', 'cristelle'], 'wedding-carmen',
             394578, 0, 895585, 492422, 43, 'clear'),
    '37-4': ('op', '모나스티르 광장|SECTOR 37-4', TEAM2, 'wedding-carmen', 411163, 0, 346440, 53172, 13, 'clear'),
    '37-5': ('op', '모나스티르 광장|SECTOR 37-5', TEAM2, 'wedding-carmen', 411163, 0, 713329, 170878, 22, 'clear'),
}
# 2026-10-21 사용자 확인: 36-36만 오토 선택 + 회복용 수동 버스트, 37구역은 순수 오토.
NOVA_POLICY = {name: ('heal' if name == '36-36' else 'auto') for name in SAMPLES}


def rebalance(spec, pw):
    """화면 능력치가 없는 구원자에게 «남은 전투력»(파티 전투력 − 화면 값 구원자들의 엔진 전투력)을 나눠 준다 — 공·생·방에 같은 배율
    (전투력 공식이 공·생·방에 선형이라 2번 반복이면 충분). codex 리뷰 2026-10-21: 안 하면 394,578 대신 398,170 으로 돌았다."""
    from battlesim.api import _norm_party, party_power
    from battlesim.starsavior.data import get_db
    db = get_db()
    fixed = [u for u in spec['units'] if u.get('stats_final')]
    free = [u for u in spec['units'] if not u.get('stats_final')]
    if not free:
        return
    target = pw - party_power(_norm_party({'units': fixed}, db, 'fixed', 'standard')[0])
    for _ in range(2):
        f = target / party_power(_norm_party({'units': free}, db, 'fixed', 'standard')[0])
        for u in free:
            so = u['stats_override']
            for k in ('atk', 'hp', 'def'):
                so[k] = round(so[k] * f)


def run(name, runs=100, ov=None, seed=7, bs=False):
    import gen_quick_calib as G
    from battlesim import quick, simulate
    ck, sk, order, lead, pw, rk, dealt, taken, turn, res = SAMPLES[name]
    q, pen = quick.load(ROOT)
    st = q['st'][ck][sk]
    spec = G.party_spec(q, pen, order, lead, list(order), pw / st['bp'], st)
    for u in spec['units']:
        if u['key'] in REAL:
            u['stats_override'] = dict(REAL[u['key']])
            u['stats_final'] = True          # 화면 값 = 최종값(상시 패시브 % 를 다시 곱하지 않음)
    rebalance(spec, pw)
    opt = dict(G.SIMOPT, n_runs=runs, seed=seed, rekindle=rk)
    if bs:
        opt['break_skill'] = {'name': '큐브 과부하', 'level': 5}
    opt['rules_override'] = dict(opt['rules_override'], nova_policy=NOVA_POLICY[name])
    opt['rules_override'].update(ov or {})  # --ov가 실측 운영 기본값보다 우선
    tab, nm = sk.split('|', 1)
    r = simulate(spec, {'stage': '%s/%s/%s' % (ck, tab, nm)}, opt)
    d = sum(v['dmg'] for v in r['per_unit'].values())
    t = sum(v['dmg_taken'] for v in r['per_unit'].values())
    acts = sum(v['actions'] for v in r['per_unit'].values())
    return dict(stage=name, real_ratio=round(dealt / taken, 2), sim_ratio=round(d / max(1.0, t), 2), sim_clear=r['outcome']['clear_p'],
                real=res, real_turn=turn, sim_ally_actions=round(acts, 1), foe_breaks=r['breaks']['foe'], ally_breaks=r['breaks']['ally'],
                break_skill=r['break_skill'], nova_policy=opt['rules_override']['nova_policy'],
                nova_burst=r['nova_burst'], heal=sum(v['heal'] for v in r['per_unit'].values()),
                healing={nm: dict(heal=v['heal'], shield=v['shield']) for nm, v in r['per_unit'].items()})


def main():
    runs = int(sys.argv[sys.argv.index('--runs') + 1]) if '--runs' in sys.argv else 100
    ov = json.loads(sys.argv[sys.argv.index('--ov') + 1]) if '--ov' in sys.argv else None
    only = sys.argv[sys.argv.index('--only') + 1] if '--only' in sys.argv else None
    for name in SAMPLES:
        if only and name != only:
            continue
        print(json.dumps(run(name, runs, ov, bs='--bs' in sys.argv), ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
