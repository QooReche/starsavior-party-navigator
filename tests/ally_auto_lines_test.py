# -*- coding: utf-8 -*-
"""효과 줄 자동 대상(게임 SE AutoTargetId) 회귀: python -X utf8 -I tests/ally_auto_lines_test.py

구원자 = data/auto_skill.json lines(mc.ally_auto_lines), 적 = data/foe_auto.json(mc.foe_auto) — 적의 아군 대상 줄 포함."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from p3_test import battle, unit   # noqa: E402
from battlesim.mc import Ctx, ally_auto_lines   # noqa: E402
from battlesim.metrics import unit_def   # noqa: E402
from tools.build_auto_skill import _skip_paren, is_auto_line, described_auto   # noqa: E402


def line_of(u, slot, head):
    return next(ln for ln in u.d.lines if ln.slot == slot and head in ln.raw)


class AllyAutoLinesTest(unittest.TestCase):
    def test_client_not_self_type_does_not_fall_back_to_caster(self):
        # 실제 공개 스킬의 전투 시작 효과로 검증: 혼자 남은 리디아에게 책임 전가 금지.
        for mode, expected in [('client', False), ('data', True)]:
            b = battle([unit_def('lydia-moon-caster')], [unit('boss', hp=10**9)],
                       mc={'ally_auto_lines': mode})
            a = b.allies[0]
            ln = line_of(a, '고유 패시브', '책임 전가(해제불가)')
            spec = b.line_spec(a, ln)
            self.assertEqual(bool(spec.get('exclude_self')), mode == 'client')
            b.run_line(a, ln, Ctx(a, a, None))
            b.cast(a, a.d.skills['기본기'])
            self.assertGreater(b.progress(), 0)
            self.assertEqual(a.has('책임 전가(해제불가)'), expected)
            self.assertEqual(a.cast_count['기본기'], 1)

    def test_client_not_self_excludes_before_priorities_and_keeps_legacy(self):
        for variants in (False, True):
            old = ally_auto_lines(variants=variants)
            current = ally_auto_lines(variants=variants, client=True)
            key = 'wedding-epindel'
            slot, raw = next(k for k, s in current[key].items() if s.get('exclude_self'))
            b = battle([unit_def(key), unit('other', atk=1)], [unit('foe', hp=10**9)])
            a, other = b.allies
            a.d.stats['atk'] = 10**7
            ctx = Ctx(a, a, a.d.skills['특수기'])
            self.assertEqual(b.line_auto_targets(a, current[key][slot, raw], ctx), [other])
            other.hp = 0
            other.dead = True
            self.assertEqual(b.line_auto_targets(a, current[key][slot, raw], ctx), [])
            self.assertEqual(b.line_auto_targets(a, old[key][slot, raw], ctx), [a])

    def test_client_mapping_registers_bloom_annah_all_levels(self):
        d = json.loads((ROOT / 'data/auto_skill.json').read_text(encoding='utf8'))
        rows = d['client_variant_lines']['annah@개화(SSR)']
        self.assertEqual(len(rows), 3)
        for slot, raw, spec in rows:
            self.assertEqual(spec, {'one': True, 'f': [], 'ally': True, 'exclude_self': True})
        self.assertNotIn('annah@개화(SSR)', d['variant_lines'])

    def setup(self, mc=None):
        b = battle([unit_def('dana'), unit('low_atk', atk=100), unit('high_atk', atk=5000), unit('mid', atk=3000)],
                   [unit('boss', hp=10 ** 9)], mc=mc)
        dana = b.allies[0]
        dana.d.stats['atk'] = 10 ** 6            # 자신이 공격력 최고여도 「자신 제외」 필터로 빠져야 함
        ln = line_of(dana, '특수기', '공격력이 가장 높은 다른 아군 1명')
        b._cur_line = ln
        return b, dana, ln

    def test_data_rule_not_self_high_atk(self):
        b, dana, ln = self.setup()
        spec = b.line_spec(dana, ln)
        self.assertEqual(spec, {'one': True, 'f': ['not_self', 'high_atk'], 'ally': True})
        got = b.resolve(dana, '아군 1명(자동 지정)', Ctx(dana, dana, dana.d.skills['특수기']))
        self.assertEqual([u.name for u in got], ['high_atk'])

    def test_off_switch_uses_description(self):
        b, dana, ln = self.setup(mc=dict(ally_auto_lines='off'))
        self.assertIsNone(b.line_spec(dana, ln))

    def test_data_shape(self):
        d = json.loads((ROOT / 'data' / 'auto_skill.json').read_text(encoding='utf-8'))
        rows = [r for field in ('lines', 'variant_lines') for v in d[field].values() for r in v]
        self.assertGreater(len(rows), 10)
        for slot, raw, spec in rows:
            self.assertTrue(is_auto_line(raw), raw)
            self.assertEqual(set(spec) - {'one', 'f', 'ally'}, set())
            head = _skip_paren(raw.split(']', 1)[-1].lstrip())   # (조건: …) 를 건너뛴 대상 머리말 — 조건 안 괄호 포함
            described = described_auto(raw)
            self.assertEqual(spec.get('ally', False), described['ally'] if described else not head.startswith('적'))

    def test_every_level_line_registered(self):
        """내 정보 스킬 레벨이 바꿔 끼우는 줄(데이터북 L 그룹)도 같은 규칙으로 등록 — 힐데·웨딩 에핀델 궁극기 등 레벨업 추가 행."""
        d = json.loads((ROOT / 'data' / 'auto_skill.json').read_text(encoding='utf-8'))
        index = json.loads((ROOT / 'data' / 'saviors_index.json').read_text(encoding='utf-8'))
        key_of = {int(k): v['key'] for k, v in index.items() if not k.startswith('_') and v.get('key')}
        book = json.loads((ROOT / 'rawdata' / 'databook_main.json').read_text(encoding='utf-8'))['units']
        missing = []
        for u in book:
            key = key_of.get(u['id'], '') + ('' if u['v'] == '기본' else '@' + u['v'])
            got = {(sl, raw) for sl, raw, _ in d['variant_lines'].get(key, [])}
            for s in u['sk']:
                L = s.get('L')
                if not L or not any(sl == s['sl'] for sl, _ in got):
                    continue
                for grp in L['e']:
                    missing += [(key, s['sl'], L['ln'][j][:40]) for j in grp
                                if is_auto_line(L['ln'][j]) and (s['sl'], L['ln'][j]) not in got]
        self.assertEqual(missing, [])
        hilde = [raw for sl, raw, _ in d['variant_lines']['hilde'] if sl == '궁극기']
        self.assertEqual(len(hilde), 3)                  # 도발 기본·75%·85% 판정

    def test_foe_ally_lines_exist(self):
        d = json.loads((ROOT / 'data' / 'foe_auto.json').read_text(encoding='utf-8'))
        ally = [s for v in d['units'].values() for s in v['lines'].values() if s.get('ally')]
        self.assertGreater(len(ally), 0)


if __name__ == '__main__':
    unittest.main()
