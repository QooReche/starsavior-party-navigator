"""2026-11-21 남은 가정 등급 재기입: 등급 어휘·보고 계약·기본 경로가 옛 폴백을 안 타는지(docs/rule_grades_1121.md)."""
from collections import Counter
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from simkit import battle, unit  # noqa: E402
from battlesim import api, mc as mcmod  # noqa: E402
from battlesim.mc import Battle  # noqa: E402
from battlesim.rules import DEFAULT_OPTS, MC_OPTS, MC_RULES, RULES  # noqa: E402

TOOL_MC = ('turn_ticks', 'max_events', 'max_depth', 'unknown_cond')
APPROX_OPTS = ('debuff_success', 'inf_hp_frac', 'break_p', 'kill_p_inf', 'no_debuff_p', 'init_cd_frac',
               'enemy_def', 'enemy_spd', 'ref_enemy_count', 'enemy_resist', 'debuff_state')


def all_rules():
    for section in ('formula', 'opts', 'mc'):
        for key, rule in RULES[section].items():
            if isinstance(rule, dict) and 'grade' in rule:
                yield section, key, rule
    for key, rule in RULES['mc']['break_skills'].items():
        yield 'mc.break_skills', key, rule


def count_targets(override=None):
    counts = Counter()
    weighted, filt = Battle.weighted_pick, Battle.filter_pick

    def w(self, pool):
        counts['weighted'] += 1
        return weighted(self, pool)

    def f(self, att, pool, steps, ctx=None):
        counts['rule1001'] += steps is mcmod.RULE1001
        return filt(self, att, pool, steps, ctx)

    opts = dict(build='standard', n_runs=2, seed=20261121)
    if override:
        opts['rules_override'] = override
    with patch.object(Battle, 'weighted_pick', w), patch.object(Battle, 'filter_pick', f):
        r = api.simulate(['gwen', 'amora', 'frey', 'claire'], {'stage': 'clo/태양 회랑/FLOOR 250'}, opts)
    return r['outcome']['progress'], counts


class RuleGradesTest(unittest.TestCase):
    def test_grade_vocabulary(self):
        bad = [(s, k, r['grade']) for s, k, r in all_rules() if r['grade'] not in api.RULE_GRADES]
        self.assertEqual(bad, [])
        self.assertTrue(api.ASSUMPTION_GRADES < api.RULE_GRADES)
        self.assertFalse(api.ASSUMPTION_GRADES & {'code', 'data', 'approx', 'tool'})

    def test_reclassified_grades(self):
        for k in TOOL_MC:
            self.assertEqual(MC_RULES[k]['grade'], 'tool', k)
        for k in APPROX_OPTS:
            self.assertEqual(RULES['opts'][k]['grade'], 'approx', k)
        for k in ('unknown_cond_p', 'nova', 'coop'):
            self.assertEqual(RULES['opts'][k]['grade'], 'tool', k)
        self.assertEqual(RULES['formula']['TICK_PER_TURN']['grade'], 'tool')
        self.assertEqual(MC_RULES['clash_no_turn_limit']['grade'], 'user')
        self.assertEqual(MC_RULES['ally_init_cd']['grade'], 'user')
        self.assertIn('10-21', MC_RULES['ally_init_cd']['note'])
        self.assertEqual(MC_RULES['enemy_init_cd']['grade'], 'code')
        self.assertIn('26752678', MC_RULES['enemy_init_cd']['source'])
        # 옛 근거(영상)는 지우지 않고 보존
        self.assertIn('ChgzulK7VI4', MC_RULES['enemy_init_cd']['source'])

    def test_report_excludes_tool_keeps_user_and_legacy_alternatives(self):
        current = {x['rule'] for x in api.assumptions_used(MC_OPTS, DEFAULT_OPTS)}
        self.assertFalse(current & {'mc.' + k for k in TOOL_MC})
        self.assertTrue({'mc.clash_no_turn_limit', 'mc.ally_init_cd', 'mc.heal_target'} <= current)
        legacy = {x['rule'] for x in api.assumptions_used(
            dict(MC_OPTS, enemy_spawn='legacy', enemy_auto_target='weighted'), dict(DEFAULT_OPTS, nova_policy='manual'))}
        self.assertTrue({'mc.enemy_init_cd_special', 'mc.target_row_weight', 'mc.target_defender_mult',
                         'mc.target_mode', 'mc.manual_burst'} <= legacy)
        # code 로 승격한 옛 경로 값은 그 경로를 골라도 가정으로 싣지 않음
        self.assertNotIn('mc.enemy_init_cd', legacy)

    def test_tool_cap_still_diagnosed_at_runtime(self):
        b = battle([unit('a', hp=10 ** 9)], [unit('e', hp=10 ** 9)], mc=dict(max_depth=0))
        a = b.allies[0]
        self.assertIsNone(b.cast(a, a.d.skills['기본기']))
        self.assertEqual(sum(v for k, v in b.unsup.items() if k.startswith('depth:')), 1)

    def test_legacy_enemy_init_cd_equals_client_unflagged_full(self):
        """클라 OBF_7817: 플래그 없는 칸은 표 쿨 가득. legacy enemy_init_cd(1.0)의 궁극기 칸과 같아야 함."""
        sk = [dict(slot='기본기', dm=1), dict(slot='특수기', dm=1, cd=3), dict(slot='궁극기', dm=1, cd=4)]

        def cds(code, mc):
            d = unit('e', hp=10 ** 9, atk=0, skills=sk)
            d.spawn = code
            f = battle([unit('a', hp=10 ** 9, atk=0)], [d], mc=dict(enemy_cd_native=True, **mc)).foes[0]
            return f.cd['특수기'], f.cd['궁극기']
        client_n, client_s = cds('N', {}), cds('S', {})
        legacy = cds('N', dict(enemy_spawn='legacy'))
        self.assertEqual(client_n, (3, 4))
        self.assertEqual(legacy[1], client_n[1])
        # 특수기 상수 0은 S 플래그와만 같음(모든 적 공통 규칙이 아님 -> video 유지)
        self.assertEqual(legacy, client_s)
        self.assertNotEqual(legacy, client_n)

    def test_default_enemy_target_uses_client_1001_not_weighted(self):
        progress, counts = count_targets()
        self.assertGreater(progress, 0)
        self.assertGreater(counts['rule1001'], 0)
        self.assertEqual(counts['weighted'], 0)
        # 계측이 실제로 잡는지: legacy 를 고르면 옛 가중 추첨이 돈다
        progress, counts = count_targets(dict(enemy_auto_target='weighted'))
        self.assertGreater(progress, 0)
        self.assertGreater(counts['weighted'], 0)


if __name__ == '__main__':
    unittest.main()
