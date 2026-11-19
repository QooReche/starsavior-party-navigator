# -*- coding: utf-8 -*-
"""PC 26752678 바스커빌: 실제 조각 SE 실행·경계·반복 병합 회귀."""
import copy
import json
import io
import math
import random
import sys
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from battlesim.api import _norm_party
from battlesim.mc import Battle, Ctx, Unit, line_kind, support_report
from battlesim.rules import MC_OPTS
from battlesim.starsavior import cosmo_raid as C, foe as F
from battlesim.starsavior.data import get_db
from tools.build_foe_clash import unverified_parts, db_shapes

HEART = '심장 마비(해제불가)'
COUNT = '심장 마비 중첩 카운팅 버프'
WILD = '억제된 야성(해제불가)'
MASTER = '바스커빌의 역작(해제불가)'
FANG = '무뎌진 송곳니(해제불가)'
ADR = '아드레날린(해제불가)'
COOL = '바스커빌의 괴수 쿨타임 체크용 버프'


def battle():
    waves, meta = C.build_waves('baskerville', 1, 0)
    defs, _ = _norm_party({'units': ['wedding-carmen', 'bunny-charlotte', 'amora', 'tyria']}, get_db(), 'fixed', 'standard')
    defs = [copy.copy(d) for d in defs]
    for d in defs:
        d.lines = []  # 표준 능력치 유지, 아군 회복 패시브·추가 발동은 개별 SE 시험에서 분리.
    b = Battle(defs, waves, random.Random(71), mc=dict(MC_OPTS, cosmo_raid_boss='on'),
               opts={'coop': False, 'forced_coop': False, 'nova': False}, turn_limit=meta['turn_limit'])
    b.spawn_wave()
    return b, b.gb.boss


def special(b, boss):
    return b.cast(boss, boss.d.skills['특수기'])


def hit(b, boss, ally):
    sk = C._skill('기본기', '피격 경로 시험', 1, 0, 0, tg='적 단일')
    return b.cast(ally, sk, target=boss)


class BaskervilleClientTest(unittest.TestCase):
    def test_conversion_and_parser(self):
        doc = json.loads((ROOT / 'data/foe_cosmo_extra.json').read_text(encoding='utf-8'))
        self.assertEqual(doc['check']['converted'], 37)
        self.assertEqual(doc['unmodeled'], [])
        raw = (ROOT / 'rawdata/foe.js').read_text(encoding='utf-8')
        shapes = db_shapes(json.JSONDecoder().raw_decode(raw[raw.index('__SSD.foe=') + len('__SSD.foe='):])[0])
        ids = []
        for sk in doc['s']:
            self.assertEqual(sk['ef'], [r['ef'] for r in sk['se']])
            self.assertEqual([r['order'] for r in sk['se']], list(range(len(sk['se']))))
            for se in sk['se']:
                ids.append(se['id'])
                self.assertEqual(unverified_parts(se['ef'], shapes), [])
                self.assertIn(se['executor'], ('engine', 'cosmo'))
        self.assertEqual(len(set(ids)), 37)
        self.assertTrue(unverified_parts('[스킬 사용 후] 자신에게 미지원 문법 1', shapes))
        b, boss = battle()
        self.assertTrue(all(line_kind(ln) != 'unmodeled' for ln in b.lines_of(boss)))
        report = support_report([boss.d])
        self.assertFalse(report, report)

    def test_hp_instances_and_last_hit(self):
        b, boss = battle()
        ally = b.allies[0]
        ally.hp = ally.maxhp * .1
        low = ally.hp
        special(b, boss)
        self.assertEqual(ally.hp, low)
        for x in b.allies:
            self.assertEqual(x.stack(HEART), 4)
            self.assertIsNotNone(x.eff[COUNT].inst)
            self.assertEqual(len(x.eff[COUNT].inst), 4)
            self.assertEqual(x.maxhp, math.floor(x.maxhp0 * .4 + 1e-8))
            self.assertLessEqual(x.hp, x.maxhp)
        for n in (3, 2, 1):
            hit(b, boss, ally)
            self.assertEqual(ally.stack(HEART), n)
            self.assertEqual(len(ally.eff[COUNT].inst), n)
            self.assertEqual(ally.hp, low)  # 개별 해제 자체는 회복하지 않음.
            self.assertEqual(b.allies[1].stack(HEART), 4)  # Caster=실제 공격자.
        hit(b, boss, ally)
        self.assertFalse(ally.has(HEART))
        self.assertNotIn(COUNT, ally.eff)
        self.assertEqual(ally.hp, ally.maxhp0)
        self.assertTrue(ally.has(ADR))
        self.assertEqual(boss.stack(FANG), 1)
        self.assertNotIn('생명력 회복 체크용 버프', ally.eff)

    def test_recovery_modifiers(self):
        b, boss = battle()
        special(b, boss)
        x = b.allies[0]
        x.hp = 1
        b.put_eff(x, '회복 감소', {'받는 회복량': -50}, src=boss, cat='debuff')
        for _ in range(4):
            hit(b, boss, x)
        self.assertAlmostEqual(x.hp, 1 + x.maxhp * .5, delta=1)
        self.assertTrue(x.has(ADR))

    def test_specific_objects(self):
        for removed in (0, 1, 4, 9, 16):
            b, boss = battle()
            special(b, boss)
            for i in range(removed):
                x = b.allies[i // 4]
                b._dispel_n_ordered(x, [COUNT], 1)
                b.dirty(x)
            ctx = Ctx(boss, boss, boss.d.skills['궁극기'])
            b.run_own(boss, ctx, 'own_pre')
            self.assertAlmostEqual(ctx.inc, (16 - removed) * .1)
        # 같은 이름의 IsLevel 한 객체는 중첩수와 무관하게 1개임.
        b, boss = battle()
        b.put_eff(b.allies[0], COUNT, {}, maxs=20, add=8)
        ctx = Ctx(boss, boss, boss.d.skills['궁극기'])
        b.run_own(boss, ctx, 'own_pre')
        self.assertAlmostEqual(ctx.inc, .1)

    def test_forced_stun_and_reverse_change(self):
        b, boss = battle()
        special(b, boss)
        x = b.allies[0]
        x.d = copy.copy(x.d)
        x.d.immune = {'기절', '도발', '수면', '침묵', '강화 불가', '스킬 쿨타임 증가'}
        b.put_eff(x, '면역', {}, src=x)
        b.put_eff(x, '기절 면역', {}, src=x)
        # 타격 피해와 분리해서 궁극기 종료 SE 순서·강제 면역 우회를 검증.
        ctx = Ctx(boss, boss, boss.d.skills['궁극기'])
        ctx.targets = list(b.allies)
        b.run_own(boss, ctx, 'own_post')
        self.assertTrue(x.has('기절'))
        self.assertFalse(x.has(HEART))
        self.assertNotIn(COUNT, x.eff)
        self.assertFalse(boss.has(MASTER))
        self.assertEqual(boss.skill_overrides['특수기'].name, '핏빛 절규')
        self.assertEqual(boss.cd['특수기'], 0)
        b.fire(boss, 'own_ts', Ctx(boss, boss, None))
        self.assertEqual(boss.cd['특수기'], 1)
        self.assertFalse(boss.has(COOL))

    def test_zero_speed_duration_and_cooldown(self):
        b, boss = battle()
        self.assertEqual(b.choose_skill(boss)[0].slot, '특수기')
        b._act_turn(boss)  # 실제 자동 선택·부여한 턴 종료까지 실행.
        self.assertEqual(boss.spd(), 0)
        self.assertEqual(boss.eff[WILD].dur, 2)
        self.assertFalse(boss.eff[WILD].fresh)
        self.assertEqual(boss.cd['특수기'], 0)
        self.assertIn('특수기', boss.skill_overrides)
        self.assertEqual(boss.skill_overrides['특수기'].name, '파멸의 숨결')
        b.fire(boss, 'enemy_ts', Ctx(boss, b.allies[0], None))
        self.assertEqual(boss.gauge, 2500)
        self.assertEqual(boss.cd['특수기'], 1)
        self.assertFalse(boss.has(COOL))
        b.fire(boss, 'foe_post_na', Ctx(boss, b.allies[0], C._skill('특수기', '비공격', 0, 0, 0, attack=False)))
        self.assertEqual(boss.gauge, 7500)
        b.fire(boss, 'enemy_ts', Ctx(boss, b.allies[0], None))
        self.assertGreaterEqual(boss.gauge, 10000)
        self.assertIs(b.pick_next(b.alive(0) + b.alive(1))[0], boss)
        # 부여한 턴 종료 이후 상태에서 두 번 자기 턴이 와야 사라짐.
        b._act_turn(boss)
        self.assertEqual(boss.eff[WILD].dur, 1)
        self.assertEqual(boss.spd(), 0)
        b._act_turn(boss)
        self.assertFalse(boss.has(WILD))
        self.assertGreater(boss.spd(), 0)
        self.assertEqual(b.choose_skill(boss)[0].slot, '궁극기')

    def test_armor_flag_and_unlimited(self):
        b, boss = battle()
        special(b, boss)
        sa = boss.sa
        hit(b, boss, b.allies[0])
        self.assertEqual(boss.sa, sa)
        self.assertGreater(b.rule_hits['superarmor_damage_ban'], 0)
        self.assertEqual(MC_OPTS['superarmor_damage_ban'], 'off')
        self.assertEqual(MC_OPTS['fixstats_speed_zero'], 'off')
        ln = next(x for x in b.lines_of(boss) if '중첩 상한 없음' in x.raw)
        for _ in range(12):
            b.exec_line(boss, ln, Ctx(boss, boss, boss.d.skills['기본기']))
        self.assertEqual(boss.stack(ln.eff['name']), 12)

    def test_death_cleanup_and_kill_condition(self):
        b, boss = battle()
        special(b, boss)
        hp = [x.hp for x in b.allies]
        b.kill(boss, b.allies[0])
        for x, before in zip(b.allies, hp):
            self.assertFalse(x.has(HEART))
            self.assertNotIn(COUNT, x.eff)
            self.assertEqual(x.maxhp, x.maxhp0)
            self.assertEqual(x.hp, before)
        b, boss = battle()
        ln = next(x for x in b.lines_of(boss) if '중첩 상한 없음' in x.raw)
        victim = b.allies[0]
        victim.hp = 1
        ctx = b.cast(boss, boss.d.skills['기본기'], target=victim)
        self.assertTrue(ctx.kill)
        self.assertEqual(boss.stack(ln.eff['name']), 1)
        ctx = b.cast(boss, boss.d.skills['기본기'], target=b.allies[1])
        self.assertFalse(ctx.kill)
        self.assertEqual(boss.stack(ln.eff['name']), 1)

    def test_partial_stage_merge_idempotent(self):
        doc = json.loads((ROOT / 'data/foe_cosmo_extra.json').read_text(encoding='utf-8'))
        raw = dict(u=[], s=[], x=[], ak=[], g=[dict(k='cosmo', tabs=[dict(t=doc['u'][0]['n'], s=[dict(n=doc['g'][0]['tabs'][0]['s'][0]['n'], w=[])])])])
        self.assertTrue(F.merge_extra(raw, doc))
        self.assertEqual(len(raw['g']), 1)
        stages = raw['g'][0]['tabs'][0]['s']
        self.assertEqual(len(stages), 3)
        self.assertEqual(stages[0]['w'], [])
        self.assertEqual(len(raw['_extra_aux']['spawn']), 2)
        snapshot = copy.deepcopy(raw)
        self.assertFalse(F.merge_extra(raw, [doc, doc]))
        self.assertEqual(raw, snapshot)

    def test_fragment_indexes_and_clash_golden(self):
        from tests.foe_clash_test import merge
        raw_text = (ROOT / 'rawdata/foe.js').read_text(encoding='utf-8')
        raw = json.JSONDecoder().raw_decode(raw_text[raw_text.index('__SSD.foe=') + len('__SSD.foe='):])[0]
        clash = json.loads((ROOT / 'data/foe_clash.json').read_text(encoding='utf-8'))
        cosmo = json.loads((ROOT / 'data/foe_cosmo_extra.json').read_text(encoding='utf-8'))
        old = merge(raw, clash)  # 기존 단일 조각 병합 결과와 격전 전체 인덱스를 비교.
        merged = copy.deepcopy(raw)
        F.merge_extra(merged, [clash, cosmo])
        self.assertEqual(merged['u'][:len(old['u'])], old['u'])
        self.assertEqual(merged['s'][:len(old['s'])], old['s'])
        self.assertEqual(merged['x'][:len(old['x'])], old['x'])
        self.assertEqual(next(g for g in merged['g'] if g['k'] == 'clash'), next(g for g in old['g'] if g['k'] == 'clash'))
        self.assertEqual(merged['_extra_aux']['summon_groups'], clash['aux']['summon_groups'])
        for step in (1, 2, 3):
            st, waves = F.stage_waves('cosmo', '바스커빌의 괴수', '바스커빌의 괴수 %d단계' % step)
            d = waves[0][0]
            self.assertEqual(d.game_slot, 2)
            self.assertEqual(d.spawn, 'S')
            self.assertEqual(d.client_model, 'baskerville')
            self.assertEqual(len(d.client_skills), 7)


def mutations():
    """실제 구현을 일시 교체하여 새 시험이 실패하는지 검사하고 patch 문맥 종료 때 복원한다."""
    original_se, original_add = C.Controller.execute_se, Battle.add_effect
    original_spd, original_tough = Unit.spd, Battle.tough_hit
    original_dirty, original_batch, original_forced = Battle.dirty, Battle.run_batch, Battle._forced
    def skip_op(op):
        def mutated(self, owner, ln, ctx):
            if ln.eff['meta']['op'] != op:
                return original_se(self, owner, ln, ctx)
        return mutated
    def no_unique(self, owner, x, eff, ctx, **kw):
        info = owner.d.effect_info.get(eff['name'], {})
        with patch.dict(info, unique=False):
            return original_add(self, owner, x, eff, ctx, **kw)
    def no_zero(self):
        with patch.dict(self.b.mc, fixstats_speed_zero='off'):
            return original_spd(self)
    def no_armor(self, a, v, ctx):
        with patch.dict(self.mc, superarmor_damage_ban='off'):
            return original_tough(self, a, v, ctx)
    def no_clamp(self, u):
        old = u.hp
        result = original_dirty(self, u)
        u.hp = old
        return result
    def batch_conditions(self, owner, lines, ctx):
        if getattr(owner.d, 'client_model', None) == 'baskerville':
            for ln in [ln for ln in lines if self.line_ok(owner, ln, ctx)]:
                self.exec_line(owner, ln, ctx)
        else:
            original_batch(self, owner, lines, ctx)
    def no_se_force(self, owner, name=None):
        if name == '기절':
            return False
        return original_forced(self, owner, name)
    cases = [
        ('교체 제거', C.Controller, 'execute_se', skip_op('change_skill'), 'test_zero_speed_duration_and_cooldown'),
        ('개수 배율 제거', C.Controller, 'execute_se', skip_op('specific_count'), 'test_specific_objects'),
        ('개별 해제 제거', C.Controller, 'execute_se', skip_op('delete_count'), 'test_hp_instances_and_last_hit'),
        ('쿨 증가 제거', C.Controller, 'execute_se', skip_op('cool_up'), 'test_zero_speed_duration_and_cooldown'),
        ('독립 객체 제거', Battle, 'add_effect', no_unique, 'test_hp_instances_and_last_hit'),
        ('속도 고정 제거', Unit, 'spd', no_zero, 'test_zero_speed_duration_and_cooldown'),
        ('강인도 플래그 제거', Battle, 'tough_hit', no_armor, 'test_armor_flag_and_unlimited'),
        ('HP 절삭 제거', Battle, 'dirty', no_clamp, 'test_hp_instances_and_last_hit'),
        ('SE 조건 사전 판정', Battle, 'run_batch', batch_conditions, 'test_hp_instances_and_last_hit'),
        ('강제 적용 제거', Battle, '_forced', no_se_force, 'test_forced_stun_and_reverse_change'),
    ]
    for name, cls, attr, fn, test in cases:
        with patch.object(cls, attr, fn):
            result = unittest.TextTestRunner(stream=io.StringIO()).run(unittest.TestSuite([BaskervilleClientTest(test)]))
        if result.wasSuccessful():
            raise AssertionError('변이를 검출하지 못함: ' + name)
        print('검출', name, '실패', len(result.failures), '오류', len(result.errors))
        if result.errors:
            raise AssertionError('의미 있는 단언 실패 대신 실행 오류: ' + result.errors[0][1])
    result = unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(BaskervilleClientTest))
    if not result.wasSuccessful():
        raise AssertionError('변이 복원 후 시험 실패')
    print('변이 %d/%d 검출, 원복 후 전체 통과' % (len(cases), len(cases)))


if __name__ == '__main__':
    if '--mutations' in sys.argv:
        mutations()
    else:
        unittest.main()
