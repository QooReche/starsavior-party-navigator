# -*- coding: utf-8 -*-
"""인게임 실측(docs/ingame_samples.md)과 확률 엔진을 대조한다 — 「준 피해 ÷ 받은 피해」 비율·클리어 확률·아군 행동 수.

실측 판마다 사용자 능력치 화면 값(공·생·방·속도·치명 등)을 stats_override 로 넣고(화면이 없는 구원자는 남은 전투력 몫으로 표준 육성 배율),
재점화 버프는 전투력 보정 배율에 곱한다(api options.rekindle 과 같은 뜻). 규칙을 바꿔 보려면 --ov '{"basic_tough": 1}'.

사용: python -X utf8 -I tools/ingame_check.py [--runs 100] [--ov JSON] [--only 37-3] [--bs] [--myinfo PATH]
--myinfo = 비공개 내정보를 제자리에서 읽어 콘텐츠 규칙으로 최종 능력치·전투력을 계산한다.
이 경로는 build=none, stats_final=true이며 표준 육성·전투력 재배분을 사용하지 않는다.
--bs = 실측 장착 스킬 「큐브 과부하」 Lv.5 활성화(기본 미장착).
운영 기본값: 36-36=heal, 37-2~37-5=auto. --ov '{"nova_policy":"auto"}' 로 전부 순수 오토 대조 가능.
nova_burst.total/by_unit은 전체 판 합계, uses·heal·healing은 판 평균(실제 HP 회복, 초과 회복 제외).
2026-10-21 결과: 37-2(잡몹) 실제 4.13 vs 시뮬 4.11 일치 / 37-3·36-36(큰 보스) 실제 1.82·1.88 vs 시뮬 0.49·0.84 — 보스전만 과대(설명 docs/ingame_samples.md)
"""
import json
import os
import sys
import argparse
from collections import defaultdict
from unittest.mock import patch

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
    # 2026-10-23 장비 탐색(혹한의 습격 XVII, 권장 411,185): 에밀리(후)·프레이(전, 리더)·에데(전)·그웬(후), 오토, 브레이크 스킬 Lv.5.
    # 준 피해 = 104,384+416,393+70,328+16,189, 받은 피해 = 139,909+108,444+278,674+173,051. 65턴 이내 승리는 66/65로 실패. 쓰러진 구원자: 프레이·에데
    '17': ('equip', '혹한의 습격|혹한의 습격 XⅦ', ['emily', 'frey', 'haydee', 'gwen'], 'frey', 372610, 0, 607294, 700078, 66, 'clear'),
    # 같은 편성, 리더 에밀리: 준 피해 96,894+413,807+82,809+15,511, 받은 피해 143,408+118,794+256,474+229,524, TURN 69, 프레이·에데 쓰러짐
    '17e': ('equip', '혹한의 습격|혹한의 습격 XⅦ', ['emily', 'frey', 'haydee', 'gwen'], 'emily', 372610, 0, 609021, 748200, 69, 'clear'),
}
# 2026-10-21 사용자 확인: 36-36만 오토 선택 + 회복용 수동 버스트, 37구역은 순수 오토.
NOVA_POLICY = {name: ('heal' if name == '36-36' else 'auto') for name in SAMPLES}

from tools.runtime import low_priority


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


def myinfo_party(content, order, lead, path):
    """Read the private input in place; return only derived simulation inputs."""
    from battlesim.starsavior.myinfo_stats import final_stats, rule_for_content
    rule = rule_for_content(content)
    if rule is None:
        raise ValueError('No myinfo rule for content: ' + content)
    with open(path, encoding='utf-8-sig') as f:
        info = json.load(f)
    if info.get('format') != 'ss-myinfo-v1':
        raise ValueError('Expected ss-myinfo-v1')
    with open(os.path.join(ROOT, 'data', 'growth.json'), encoding='utf-8') as f:
        growth = json.load(f)
    with open(os.path.join(ROOT, 'data', 'saviors_index.json'), encoding='utf-8') as f:
        index = json.load(f)
    ids = {v['key']: int(k) for k, v in index.items() if not k.startswith('_') and v.get('key')}
    owned = {u['id']: u for u in info['units']}
    so = [order[1], order[2], order[0], order[3]]
    units, diagnostics = [], {}
    for key in so:
        uid = ids.get(key)
        if uid not in owned or str(uid) not in growth['units']:
            raise ValueError('Missing myinfo/growth unit: ' + key)
        result = final_stats(owned[uid], info, growth, rule)
        units.append(dict(key=key, build='none', stats_override=result['stats'],
                          stats_final=True, power=result['power'], myinfo_combat=result['combat']))
        diagnostics[key] = dict(missing=result['missing'], build_mismatch=result.get('build_mismatch', False))
    return dict(units=units, leader=so.index(lead) if lead in so else None), dict(rule=rule, units=diagnostics)


def turn_comparison(dealt, taken, turn, sim_dealt, sim_taken, ally, enemy):
    """TURN is all selected unit turns, excluding out-of-turn skill casts.

    The real ally share is unknown. Its estimate uses the simulation's share;
    this is a diagnostic assumption, not an observed action count.
    """
    total = ally + enemy
    share = ally / total if total else 0.0
    estimated = turn * share
    real_rate = dealt / estimated if estimated else None
    sim_rate = sim_dealt / ally if ally else None
    return dict(sim_total_actions=round(total, 3),
                sim_total_actions_vs_turn=total / turn if turn else None,
                sim_total_actions_minus_turn=total - turn,
                sim_ally_action_share=share, real_estimated_ally_actions=estimated,
                real_taken_per_global_turn=taken / turn if turn else None,
                sim_taken_per_global_turn=sim_taken / total if total else None,
                real_estimated_dealt_per_ally_action=real_rate,
                sim_dealt_per_ally_action=sim_rate,
                estimated_ally_damage_ratio=real_rate / sim_rate if sim_rate else None)


def run(name, runs=100, ov=None, seed=7, bs=False, myinfo=None):
    import gen_quick_calib as G
    from battlesim import quick, simulate
    ck, sk, order, lead, pw, rk, dealt, taken, turn, res = SAMPLES[name]
    diagnostics = None
    if myinfo is not None:
        spec, diagnostics = myinfo_party(ck, order, lead, myinfo)
    else:
        q, pen = quick.load(ROOT)
        st = q['st'][ck][sk]
        spec = G.party_spec(q, order, lead, list(order), pw / st['bp'], st)
        for u in spec['units']:
            if u['key'] in REAL:
                u['stats_override'] = dict(REAL[u['key']])
                u['stats_final'] = True      # 화면 값 = 최종값(상시 패시브 % 재적용 안 함)
        rebalance(spec, pw)
    opt = dict(G.SIMOPT, n_runs=runs, seed=seed, rekindle=rk)
    if bs:
        opt['break_skill'] = {'name': '큐브 과부하', 'level': 5}
    opt['rules_override'] = dict(opt['rules_override'], nova_policy=NOVA_POLICY[name])
    opt['rules_override'].update(ov or {})  # --ov가 실측 운영 기본값보다 우선
    tab, nm = sk.split('|', 1)
    if myinfo is not None:
        opt['build'] = 'none'
    from battlesim import api
    measured = defaultdict(float)
    enemy_skills = defaultdict(lambda: defaultdict(int))

    class MeasuredBattle(api.Battle):
        def run(self):
            super().run()
            measured['ally'] += sum(u.actions for u in self.allies)
            measured['boss'] += sum(u.actions for u in self.all_foes if u.d.boss)
            measured['enemy'] += sum(u.actions for u in self.all_foes)
            for u in self.all_foes:
                for slot, count in u.cast_count.items():
                    enemy_skills[u.name][slot] += count
            return self

    with patch.object(api, 'Battle', MeasuredBattle):
        r = simulate(spec, {'stage': '%s/%s/%s' % (ck, tab, nm)}, opt)
    d = sum(v['dmg'] for v in r['per_unit'].values())
    t = sum(v['dmg_taken'] for v in r['per_unit'].values())
    acts = measured['ally'] / runs
    return dict(stage=name, runs=runs, seed=seed, real_ratio=round(dealt / taken, 2), sim_ratio=round(d / max(1.0, t), 2), sim_clear=r['outcome']['clear_p'],
                **turn_comparison(dealt, taken, turn, d, t, acts, measured['enemy'] / runs),
                real=res, real_turn=turn, sim_ally_actions=round(acts, 1), foe_breaks=r['breaks']['foe'], ally_breaks=r['breaks']['ally'],
                sim_boss_actions=round(measured['boss'] / runs, 2), sim_enemy_actions=round(measured['enemy'] / runs, 2),
                enemy_skills={k: {s: round(n / runs, 3) for s, n in v.items()} for k, v in enemy_skills.items()},
                sim_dealt=d, sim_taken=t, party_power=r['party']['power'], myinfo=diagnostics,
                party_penalty=r['party']['penalty'],
                per_unit={k: {f: v[f] for f in ('dmg', 'dmg_taken', 'actions')} for k, v in r['per_unit'].items()},
                break_skill=r['break_skill'], nova_policy=opt['rules_override']['nova_policy'],
                nova_burst=r['nova_burst'], heal=sum(v['heal'] for v in r['per_unit'].values()),
                healing={nm: dict(heal=v['heal'], shield=v['shield']) for nm, v in r['per_unit'].items()})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runs', type=int, default=100)
    p.add_argument('--seed', type=int, default=7)
    p.add_argument('--ov', type=json.loads)
    p.add_argument('--only', choices=SAMPLES)
    p.add_argument('--bs', action='store_true')
    p.add_argument('--myinfo', metavar='PATH', help='Private ss-myinfo-v1 file (no default)')
    args = p.parse_args()
    if args.runs < 1:
        p.error('--runs must be positive')
    low_priority()
    for name in SAMPLES:
        if args.only and name != args.only:
            continue
        print(json.dumps(run(name, args.runs, args.ov, args.seed, args.bs, args.myinfo), ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
