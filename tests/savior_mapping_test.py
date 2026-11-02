# -*- coding: utf-8 -*-
"""세레스·기본/개화 자동 대상 회귀. 선택: CERES_AUDIT_STATIC=<표 저장소>로 원본 대조.

원본 대조는 표만 읽으며 계정 자료를 사용하지 않는다.
"""
import json
import os
import random
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from p3_test import battle, give, unit
from savior_fix_test import setup, test_ceres_targets
from battlesim.mc import Battle
from battlesim.metrics import unit_def
from battlesim.rules import MC_OPTS
from battlesim.starsavior.data import get_db
from tools.build_auto_skill import build, build_lines, build_no_preemptive, form_bindings

FORMS = {1501: 'besta', 1502: 'annah', 1506: 'marcille', 1507: 'vera',
         1508: 'naru', 1509: 'bunny-claire', 1510: 'bunny-scarlet', 1511: 'clarissa'}
BLOOM = '@개화(SSR)'


def auto_line(owner, slot, text):
    return next(ln for ln in owner.d.lines if ln.slot == slot and text in ln.raw)


class SaviorMappingTest(unittest.TestCase):
    def test_identity_and_eight_forms(self):
        db = get_db()
        for key, uid, title, role in [('ceres', 1033, '서부 탈환대', '스트라이커'),
                                      ('ceres-sun-supporter', 1059, '샤프 앤 스위트', '서포터')]:
            u = db.units[key]
            self.assertEqual((u['id'], u['n'], u['ti'], u['r']), (uid, '세레스', title, role))
        pairs = {u['id']: key.removesuffix(BLOOM) for key, u in db.units.items() if key.endswith(BLOOM)}
        self.assertEqual(pairs, FORMS)
        for uid, key in FORMS.items():
            self.assertEqual(db.units[key]['id'], uid)
            self.assertEqual(db.units[key + BLOOM]['v'], '개화(SSR)')
        self.assertEqual(MC_OPTS['ally_variant_mapping'], 'data')

    def vera(self, bloom=False, legacy=False):
        b = battle([unit_def('vera' + (BLOOM if bloom else '')),
                    unit('moon', element='달', hp=100000),
                    unit('sun', element='태양', hp=100000)], [unit('foe', hp=10**9)],
                   mc={'ally_variant_mapping': 'legacy' if legacy else 'data'})
        return b, b.allies[0]

    def test_base_vera_delivery_only_buffed_and_one_turn(self):
        for buffed in (False, True):
            b, a = self.vera()
            if buffed:
                give(b.allies[2], '보호막').shield = 100
            ln = auto_line(a, '궁극기', '무작위 효과')
            self.assertEqual(b.line_spec(a, ln), {'one': False, 'f': ['buffed'], 'ally': True})
            b.cast(a, a.d.skills['궁극기'])
            delivered = [{k for k, e in x.eff.items() if k in ('공격력 증가', '방어력 증가', '속도 증가', '지속 회복')}
                         for x in b.allies]
            self.assertEqual([len(x) for x in delivered], [0, 0, 1 if buffed else 0])
            if buffed:
                self.assertEqual(next(b.allies[2].eff[k].dur for k in delivered[2]), 1)
            self.assertEqual(a.cast_count['궁극기'], 1)

    def test_bloom_vera_heal_follows_element_not_buff(self):
        outcomes = {}
        for legacy in (False, True):
            b, a = self.vera(bloom=True, legacy=legacy)
            give(b.allies[2], '보호막').shield = 100
            for x in b.allies:
                x.hp = x.maxhp * .1
            before = [x.hp for x in b.allies]
            ln = auto_line(a, '궁극기', '받는 회복량 +30%')
            expected = ['buffed'] if legacy else [['elem', '달']]
            self.assertEqual(b.line_spec(a, ln)['f'], expected)
            b.cast(a, a.d.skills['궁극기'])
            healed = [x.hp - hp for x, hp in zip(b.allies, before)]
            self.assertGreater(min(healed), 0)
            outcomes[legacy] = healed
            self.assertEqual(a.stack('냉각'), 3)
            for x in b.allies:
                gifts = [e for k, e in x.eff.items() if k in ('공격력 증가', '방어력 증가', '속도 증가', '지속 회복') and e.src is a]
                self.assertEqual(len(gifts), 1)
                self.assertEqual(gifts[0].dur, 2)
        self.assertGreater(outcomes[False][1], outcomes[False][2])
        self.assertLess(outcomes[True][1], outcomes[True][2])

    def test_bloom_besta_shield_chooses_lowest_hp(self):
        b = battle([unit_def('besta' + BLOOM), unit('strong', atk=100000, hp=20000), unit('hurt', atk=1)],
                   [unit('foe', hp=10**9)])
        a = b.allies[0]
        # 비율 동률이면 최대 생명력이 낮은 쪽. 설명문 근사는 앞자리 strong을 고름.
        b.allies[1].hp = 2000
        b.allies[2].hp = 1000
        b.cast(a, a.d.skills['특수기'])
        self.assertGreater(b.allies[2].eff['보호막'].shield, 0)
        self.assertFalse(b.allies[1].has('보호막'))

    def test_bloom_annah_gauge_random_other_ally(self):
        recipients = set()
        for seed in range(16):
            b = battle([unit_def('annah' + BLOOM), unit('strong', atk=100000), unit('weak', atk=1)],
                       [unit('foe', hp=10**9)], seed=seed)
            a = b.allies[0]
            b.cast(a, a.d.skills['기본기'])
            self.assertEqual(a.gauge, 0)
            got = [x.pos for x in b.allies if x.gauge == 1500]
            self.assertEqual(len(got), 1)
            recipients.update(got)
        self.assertEqual(recipients, {1, 2})
        # build 26314877은 후보 생성 때 자신을 제외함. 혼자면 대상 없음.
        b = battle([unit_def('annah' + BLOOM)], [unit('foe', hp=10**9)])
        a = b.allies[0]
        ln = auto_line(a, '고유 패시브', '행동 게이지 15%p 증가')
        self.assertTrue(b.line_spec(a, ln)['exclude_self'])
        b.cast(a, a.d.skills['기본기'])
        self.assertEqual(a.gauge, 0)

    def test_ceres_cooling_gauge_and_status(self):
        for stacks in range(6):
            b, a, f = setup('ceres')
            a.d.stats['hit'] = 100000
            f.gauge = 10000
            if stacks:
                give(a, '냉각', stacks=stacks).maxs = 5
            b.cast(a, a.d.skills['궁극기'], target=f)
            self.assertGreater(f.maxhp - f.hp, 0)
            self.assertEqual(f.gauge, 8000 - 1000 * stacks)
            self.assertEqual(a.stack('냉각'), 0)
            self.assertEqual(f.eff['기절'].dur, 1)
            self.assertEqual(a.eff['서부의 바람'].dur, 3)
            self.assertEqual(a.eff['서부의 바람'].props['속도%'], 25)
        ok, detail = test_ceres_targets()
        self.assertTrue(ok, detail)

    def test_ceres_battle_start_and_first_auto_skill(self):
        b = Battle([unit_def('ceres')], [[unit('foe', hp=10**6, atk=1)]], random.Random(1), max_turns=3)
        seen = []
        cast = b.cast

        def watch(u, sk, *args, **kwargs):
            if u.side == 0:
                seen.append((u.stack('냉각'), sk.slot))
            return cast(u, sk, *args, **kwargs)

        b.cast = watch
        b.run()
        self.assertGreater(b.progress(), 0)
        self.assertGreater(len(seen), 0)
        self.assertEqual(seen[0], (2, '특수기'))
        self.assertEqual(b.allies[0].d.passive['atkp'], .15)

    def test_ceres_special_and_frozen_bonus(self):
        b, a, f = setup('ceres')
        a.d.stats['hit'] = 100000
        give(f, '공격력 증가', {'공격력%': 50})
        b.cast(a, a.d.skills['특수기'])
        self.assertFalse(f.has('공격력 증가'))
        self.assertEqual((f.stack('빙결'), f.eff['빙결'].dur, f.eff['고립'].dur), (2, 2, 2))
        self.assertEqual(a.stack('냉각'), 1)
        for slot in ('기본기', '특수기', '궁극기'):
            damage = []
            for frozen in (False, True):
                b, a, f = setup('ceres')
                a.d.stats['cr'] = 0
                if frozen:
                    give(f, '빙결', harmful=True)
                b.cast(a, a.d.skills[slot], target=f)
                damage.append(f.maxhp - f.hp)
            self.assertGreater(min(damage), 0)
            if slot == '특수기':
                self.assertEqual(*damage)
            else:
                self.assertGreater(damage[1], damage[0])


@unittest.skipUnless(os.environ.get('CERES_AUDIT_STATIC'), '선택: 비공개 표 대조 경로 없음')
class StaticMappingTest(unittest.TestCase):
    def test_builder_reproduces_public_data_and_all_eight_pairs(self):
        static = Path(os.environ['CERES_AUDIT_STATIC'])
        data = json.loads((ROOT / 'data/auto_skill.json').read_text(encoding='utf8'))
        index = json.loads((ROOT / 'data/saviors_index.json').read_text(encoding='utf8'))
        keys = {int(k): v['key'] for k, v in index.items() if not k.startswith('_') and v.get('key')}
        book = json.loads((ROOT / 'rawdata/databook_main.json').read_text(encoding='utf8'))['units']
        bindings = list(form_bindings(static / 'tables', keys, list(reversed(book))))
        bloom = {bu['id']: ids for key, bu, u, ids in bindings if key.endswith(BLOOM)}
        self.assertEqual(set(bloom), set(FORMS))
        skills = {s['m_SkillStrID']: s for n in (1, 2) for s in json.loads(
            (static / ('tables/SKILL_TEMPLET_%d.json' % n)).read_text(encoding='utf8'))['Data']}
        for key, bu, u, ids in bindings:
            if bu['id'] not in FORMS:
                continue
            group = bu['id'] + (100 if key.endswith(BLOOM) else 0)
            self.assertEqual([skills[s]['SkillLevelGroup'] for s in ids], [group * 10 + i for i in range(1, 5)])
        units, order = build(static)
        self.assertEqual((units, order), (data['units'], data['order']))
        self.assertEqual(build_lines(static, Counter()), data['variant_lines'])
        self.assertEqual(build_lines(static, Counter(), legacy=True), data['lines'])
        self.assertEqual(build_lines(static, Counter(), client=True), data['client_variant_lines'])
        self.assertEqual(build_lines(static, Counter(), legacy=True, client=True), data['client_lines'])
        self.assertEqual(build_no_preemptive(static), data['no_preemptive'])

    def test_skill_numbers_match_client_for_ceres_and_sixteen_forms(self):
        tables = Path(os.environ['CERES_AUDIT_STATIC']) / 'tables'

        def load(name):
            return json.loads((tables / (name + '.json')).read_text(encoding='utf8'))['Data']

        skills = {s['m_SkillStrID']: s for n in (1, 2) for s in load('SKILL_TEMPLET_%d' % n)}
        damages = {r['DTStrID']: r for r in load('DAMAGE_TEMPLET')}
        heals = {r['HtStrId']: r for r in load('HEAL_TEMPLET')}
        reductions = Counter()
        for n in (1, 2):
            for row in load('SKILL_LEVEL_GROUP_TEMPLET_%d' % n):
                reductions[row['SkillLevelGroupID']] += row.get('SkillLevelCoolTurnReduce', 0)
        book = list(get_db().units.values())
        keys = dict(FORMS)
        keys[1033] = 'ceres'
        count = 0
        target = {'NSTT_ENEMY_ONE': '적 단일', 'NSTT_ENEMY_ALL': '적 전체',
                  'NSTT_ALLY_ONE': '아군 단일', 'NSTT_ALLY_ALL': '아군 전체',
                  'NSTT_MYSELF': '자신', 'NSTT_INVALID': '-'}
        for key, bu, _, ids in form_bindings(tables, keys, book):
            by_slot = {s['sl']: s for s in bu['sk']}
            for slot, sid in zip(('기본기', '특수기', '궁극기', '고유 패시브'), ids):
                with self.subTest(key=key, slot=slot):
                    raw, client = by_slot[slot], skills[sid]
                    self.assertEqual(raw['tg'], target[client['m_TARGET_TYPE']])
                    self.assertEqual(raw.get('cdm', raw.get('cd', 0)),
                                     client['m_CoolTurn'] - reductions[client['SkillLevelGroup']])
                    if client.get('DTStrID'):
                        row = damages[client['DTStrID']]
                        self.assertEqual(raw['cf'], [row.get(k, 0) for k in ('AtkFactor', 'HpFactor', 'DefFactor', 'SpeedFactor')])
                    if client.get('HtStrId'):
                        row = heals[client['HtStrId']]
                        self.assertEqual(raw['hl'], '생명력×%g%%' % (row['HpFactor'] / 100))
                    count += 1
        self.assertEqual(count, 68)


if __name__ == '__main__':
    unittest.main()
