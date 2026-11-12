"""격전 의뢰: 실제 로더·소환·강제 협공·보스 처치 종료. 공개 합성 입력만 사용."""
import copy
import json
from pathlib import Path
import random
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from battlesim.mc import Battle, Ctx
from battlesim import simulate
from battlesim.api import _norm_encounter
from battlesim.web import run_auto
from battlesim.metrics import unit_def
from battlesim.starsavior.myinfo_stats import rule_for_content
from battlesim.starsavior import foe as F
from simkit import give, unit

TABS = ['폐쇄된 심상', '이형의 공세', '거짓된 계약']
COOP = '[스킬 사용 후] (조건: 내 공격 후 [사용 스킬: 기본기]) 자신 제외 아군 1명(자동 지정)에게 〈강제 협공〉 (0턴)'


def make_battle(tab=2, **mc):
    waves, limit, _, _, meta = _norm_encounter({'stage': 'clash/%s/%s Ⅰ' % (TABS[tab], TABS[tab])})
    # 오래 살아 있는 합성 상대. 보스 스탯·스킬·소환 데이터는 실제 로더 그대로.
    b = Battle([unit('합성 표적', hp=10**8, atk=100, sa=10000)], waves, random.Random(7),
               mc={'foe_forced_coop': 'on', **mc}, timeline=True, battle_mode=meta['battle_mode'], turn_limit=limit)
    b.spawn_wave()
    return b, b.foes[0]


class ClashLoaderTest(unittest.TestCase):
    def test_normal_level_and_browser_pack(self):
        self.assertEqual(rule_for_content('clash'), 'normal')
        from tools.build_simpack import files
        self.assertIn('data/foe_clash.json', files())

    def test_real_merge_offsets_and_databook_precedence(self):
        frag = F.load_extra()
        original = copy.deepcopy(frag)
        raw = dict(u=[dict(sk=[0])], s=[dict(n='base')], x=[{}], ak=[], g=[dict(k='base')])
        self.assertTrue(F.merge_extra(raw, frag))
        self.assertEqual(frag, original)
        self.assertEqual(raw['u'][1]['sk'], [i + 1 for i in frag['u'][0]['sk']])
        for tab, ft in zip(raw['g'][-1]['tabs'], frag['g'][0]['tabs']):
            for st, fs in zip(tab['s'], ft['s']):
                self.assertEqual(st['w'], [[[e[0]+1, e[1]+1] for e in w] for w in fs['w']])
                for sm, fm in zip(st.get('sm', []), fs.get('sm', [])):
                    self.assertEqual(sm[2], [[a+1, b+1, n] for a,b,n in fm[2]])
        merged = copy.deepcopy(raw)
        self.assertFalse(F.merge_extra(raw, frag))
        self.assertEqual(raw, merged)
        self.assertFalse(F.merge_extra(raw, None))

    def test_fragment_aux_on_off_and_missing(self):
        # 실제 파일 로더를 거친다. 일반 생성물은 비워 조각의 병합을 끄면 반드시 실패하게 함.
        (ROOT / 'local').mkdir(exist_ok=True)
        for mode in ('on', 'databook', 'missing'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory(dir=ROOT / 'local') as tmp:
                root = Path(tmp)
                (root / 'data').mkdir()
                (root / 'rawdata').mkdir()
                raw = dict(u=[], s=[], x=[], ak=[], g=[] if mode != 'databook' else [dict(k='clash')])
                (root / 'rawdata/foe.js').write_text('window.__SSD.foe='+json.dumps(raw), encoding='utf8')
                if mode != 'missing':
                    (root / 'data/foe_clash.json').write_text(json.dumps(F.load_extra()), encoding='utf8')
                with patch.object(F, '_FOE', None), patch.object(F, '_EXTRA_ON', {}):
                    got = F.load_foe(tmp)
                    self.assertEqual(len(got['g']), 0 if mode == 'missing' else 1)
                    self.assertEqual(len(F.battle_end(tmp)), 18 if mode == 'on' else 0)
                    self.assertEqual(len(F.spawn_flags(tmp)), 18 if mode == 'on' else 0)
                    self.assertEqual(len(F.foe_summon(tmp)['groups']), 6 if mode == 'on' else 0)
                    self.assertEqual(len(F.foe_summon(tmp)['stages']), 6 if mode == 'on' else 0)


class ClashCombatTest(unittest.TestCase):
    def test_legacy_does_not_resolve_forced_target(self):
        b, boss = make_battle(foe_forced_coop='off')
        line = next(l for l in boss.d.lines if l.raw == COOP)
        with patch.object(b, 'resolve', side_effect=AssertionError('legacy target selection')):
            b.apply_buff(boss, line.eff, Ctx(boss, boss, boss.d.skills['기본기']))

    def test_actual_standard_battles(self):
        """스킬 순서·장막·중첩을 실제 행동 루프에서 관찰. 기능 제거 시 실패해야 함."""
        cast = Battle.cast
        for tab, prefix, buff, minimum in [
                (0, ['재충전', '포착', '포착', '재충전', '침입자 청소'], '버전 업그레이드(해제불가)', 2),
                (1, ['서리 지진', '차가운 고통', '차가운 고통', '서리 지진', '눈보라를 가르는 포효'], '혹한의 기운', 2),
                (2, ['소집', '판별', '판별'], '방위', 2)]:
            with self.subTest(tab=tab):
                waves, limit, fx, _, meta = _norm_encounter({'stage': 'clash/%s/%s Ⅲ' % (TABS[tab], TABS[tab])})
                b = Battle([unit_def(k, build='standard') for k in ['gwen','fei','professor-m','amora']],
                           waves, random.Random(3), leader=0, turn_limit=limit, fx=fx,
                           timeline=True, battle_mode=meta['battle_mode'])
                observed = dict(stacks=0, shield=0, soldier_stacks=0)
                def observe(battle, *args, **kwargs):
                    result = cast(battle, *args, **kwargs)
                    for u in battle.foes:
                        if u.dead:
                            continue
                        if u.d.boss:
                            observed['stacks'] = max(observed['stacks'], u.eff[buff].stacks if buff in u.eff else 0)
                            observed['shield'] = max(observed['shield'], u.shield_total())
                        else:
                            observed['soldier_stacks'] = max(observed['soldier_stacks'],
                                u.eff['퇴적(해제불가)'].stacks if '퇴적(해제불가)' in u.eff else 0)
                    return result
                with patch.object(Battle, 'cast', observe):
                    b.run()
                boss_name = waves[0][0].name
                skills = [e['skill_name'] for e in b.timeline if e.get('actor') == boss_name and not e.get('via')]
                self.assertEqual(skills[:len(prefix)], prefix)
                self.assertGreater(b.progress(), 0)
                self.assertGreaterEqual(observed['stacks'], minimum)
                self.assertFalse(b.unsup)
                if tab == 0:
                    self.assertGreater(observed['shield'], 0)
                if tab == 2:
                    self.assertGreater(b.rule_hits['foe_forced_coop'], 0)
                    self.assertGreater(observed['soldier_stacks'], 1)

    def test_enemy_aoe_coop_target_is_opponent(self):
        b, boss = make_battle()
        ctx = Ctx(boss, boss, boss.d.skills['궁극기'])
        self.assertTrue(ctx.skill.all)
        self.assertIs(b._coop_target(ctx), b.allies[0])

    def test_summon_then_forced_coop_and_legacy(self):
        for mode in ('on', 'off'):
            with self.subTest(mode=mode):
                b, boss = make_battle()
                b.mc['foe_forced_coop'] = mode
                self.assertEqual(len(b.foes), 1)
                self.assertTrue(any(l.raw == COOP for l in boss.d.lines))
                self.assertFalse(boss.d.unmodeled)
                spec = boss.d.auto_lines[('기본기', COOP)]
                self.assertEqual(spec, dict(one=True, ally=True, exclude_self=True,
                                           f=['not_unable_to_coop', ['not_has', ['협공 불가']], 'high_atk']))
                b.cast(boss, boss.d.skills['특수기'])
                soldiers = [u for u in b.foes if u is not boss]
                self.assertEqual([u.pos for u in soldiers], [0, 4])
                self.assertTrue(all(u.summoned for u in soldiers))
                b.cast(boss, boss.d.skills['특수기'])
                self.assertEqual(len(b.foes), 3)
                # 공격력 동률을 풀고 최고 공격력 병졸을 고르는지 검사.
                give(soldiers[1], '합성 공격력', {'공격력%': 100})
                b.cast(boss, boss.d.skills['기본기'], target=b.allies[0])
                events = [e for e in b.timeline if e.get('via') == 'forced_coop']
                self.assertEqual(len(events), int(mode == 'on'))
                if mode == 'on':
                    self.assertEqual(events[0]['pos'], 4)
                    self.assertEqual(events[0]['tgt_side'], 0)
                    self.assertGreater(b.rule_hits['foe_forced_coop'], 0)
                self.assertGreater(b.allies[0].taken, 0)
                b.cast(b.allies[0], b.allies[0].d.skills['기본기'], target=boss)
                self.assertGreater(b.progress(), 0)
                self.assertFalse(any('협공' in k for k in b.unsup))
                # 부하가 살아 있어도 보스 처치로 종료.
                self.assertEqual(len(b.alive(1)), 3)
                b.kill(boss, b.allies[0])
                self.assertFalse(b.alive(1))

    def test_auto52_filters_and_no_candidates(self):
        for reason in ('broken', '기절', '수면', '협공 불가', 'dead', 'cooldown'):
            with self.subTest(reason=reason):
                b, boss = make_battle()
                b.cast(boss, boss.d.skills['특수기'])
                soldiers = [u for u in b.foes if u is not boss]
                high, low = soldiers
                give(high, '합성 공격력', {'공격력%': 100})
                if reason in ('broken', 'dead'):
                    setattr(high, reason, True)
                elif reason == 'cooldown':
                    high.cd['기본기'] = 2
                else:
                    give(high, reason)
                b.cast(boss, boss.d.skills['기본기'], target=b.allies[0])
                events = [e for e in b.timeline if e.get('via') == 'forced_coop']
                # 쿨은 Auto52 필터가 아닌 최종 사용 검사라 다른 병졸로 다시 뽑지 않음.
                self.assertEqual([e['pos'] for e in events], [] if reason == 'cooldown' else [low.pos])
        b, boss = make_battle()
        b.cast(boss, boss.d.skills['기본기'], target=b.allies[0])
        self.assertFalse(any(e.get('via') == 'forced_coop' for e in b.timeline))
        b.cast(boss, boss.d.skills['특수기'])
        for u in b.foes:
            if u is not boss:
                give(u, '협공 불가')
        b.cast(boss, boss.d.skills['기본기'], target=b.allies[0])
        self.assertFalse(any(e.get('via') == 'forced_coop' for e in b.timeline))


class ClashTurnLimitTest(unittest.TestCase):
    """실제 보스·구원자 스킬과 합성 능력치로 긴 판을 만든다(개인 계정 입력 없음)."""
    stage = 'clash/폐쇄된 심상/폐쇄된 심상 Ⅰ'

    def party(self, atk=1000, hp=10**9):
        return {'units': [{'key': 'gwen', 'stats_final': True,
                           'stats_override': {'hp': hp, 'atk': atk, 'def': 10000, 'spd': 100, 'cr': 0}}]}

    def run_case(self, atk=1000, hp=10**9, encounter=None, **options):
        seen = []
        run = Battle.run
        def observe(battle):
            seen.append(battle)
            return run(battle)
        with patch.object(Battle, 'run', observe):
            result = simulate(self.party(atk, hp), {'stage': self.stage, **(encounter or {})},
                              {'n_runs': 1, 'seed': 3, 'per_run': True, **options})
        self.assertEqual(len(seen), 1)
        self.assertGreater(result['outcome']['progress'], 0)
        return result, seen[0]

    def test_clear_after_50_without_defeat_limit(self):
        # 명시 제한 입력이 있어도 격전 의뢰 기본은 제한 없음. 실제 처치까지 진행.
        r, b = self.run_case(encounter={'turn_limit': 50})
        self.assertIsNone(r['encounter']['turn_limit'])
        self.assertEqual(b.max_turns, 200)
        self.assertGreater(b.clear_t / b.turn_ticks, 50)
        self.assertGreater(b.global_turns, 65)
        self.assertEqual(r['runs'][0][0], 'clear')
        self.assertEqual((r['outcome']['clear_p'], r['outcome']['wipe_p'], r['outcome']['timeout_p']), (1, 0, 0))
        self.assertFalse(b.alive(1))

    def test_safety_cap_is_undecided_and_override_is_honored(self):
        for cap in (None, 60):
            with self.subTest(cap=cap):
                r, b = self.run_case(atk=300, encounter={} if cap is None else {'max_turns': cap})
                expected = 200 if cap is None else cap
                self.assertEqual(b.max_turns, expected)
                self.assertGreater(b.t / b.turn_ticks, expected - 2)
                self.assertLessEqual(b.t / b.turn_ticks, expected)
                self.assertGreater(b.global_turns, 50)
                self.assertTrue(b.alive(0) and b.alive(1))
                self.assertEqual(r['runs'], [['timeout', None]])
                self.assertEqual((r['outcome']['clear_p'], r['outcome']['wipe_p'], r['outcome']['timeout_p']), (0, 0, 1))

    def test_wipe_still_ends_battle(self):
        r, b = self.run_case(hp=10000)
        self.assertFalse(b.alive(0))
        self.assertLess(b.t / b.turn_ticks, 50)
        self.assertEqual(r['runs'], [['wipe', None]])
        self.assertEqual((r['outcome']['wipe_p'], r['outcome']['timeout_p']), (1, 0))

    def test_legacy_keeps_50_model_turn_cap(self):
        r, b = self.run_case(rules_override={'clash_no_turn_limit': False})
        self.assertEqual(b.max_turns, 50)
        self.assertLessEqual(b.t / b.turn_ticks, 50)
        self.assertEqual(r['runs'], [['timeout', None]])

    def test_star_mission_is_separate_from_clear(self):
        for limit in (60, 65):
            for atk, star_p in ((1000, 0), (10000, 1)):
                with self.subTest(limit=limit, atk=atk):
                    r, b = self.run_case(atk=atk, star_turns=limit)
                    self.assertEqual(r['outcome']['clear_p'], 1)
                    self.assertEqual(r['star_turn'], {'limit': limit, 'p': star_p})
                    self.assertEqual(int(b.global_turns <= limit), star_p)
                    self.assertIsNone(r['encounter']['turn_limit'])

    def test_web_summary_keeps_timeout_separate_from_wipe(self):
        for atk, outcome in ((1000, (1, 0, 0)), (300, (0, 0, 1))):
            with self.subTest(atk=atk):
                r = json.loads(run_auto(self.stage, self.party(atk), 1, 3, {'star_turns': 65}))
                self.assertGreater(r['prog'], 0)
                self.assertEqual((r['clear'], r['wipe'], r['timeout']), outcome)
                self.assertEqual(r['t60'], 0)


if __name__ == '__main__':
    unittest.main()
