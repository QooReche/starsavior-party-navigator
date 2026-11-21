"""벨그라스 회귀 시험에 실제 경로 결함을 주입함. 파일은 고치지 않음."""
import io
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))
import belgras_stage_se_test as test
from battlesim.mc import Battle
from battlesim.starsavior import belgras_se as S


def check(name, method, target, replacement):
    suite = unittest.defaultTestLoader.loadTestsFromName('StageSE.' + method, test)
    stream = io.StringIO()
    with patch.object(target[0], target[1], replacement):
        result = unittest.TextTestRunner(stream=stream).run(suite)
    if not result.failures or result.errors:
        print(stream.getvalue())
        raise AssertionError(name + ': assertion 실패로 검출하지 못함')
    print(f'{name}: assertion 실패 {len(result.failures)}건 확인', flush=True)


def main():
    normalize, execute, fire = S.normalize, Battle._exec_line, Battle.fire_foes

    def no_queue(self, owner, ln, ctx):
        if ln.eff['kind'] != 'belgras_fixed':
            return execute(self, owner, ln, ctx)

    def immediate(self, owner, ln, ctx):
        result = execute(self, owner, ln, ctx)
        if ln.eff['kind'] == 'belgras_fixed':
            self.flush_belgras_damage()
        return result

    def no_action(self, actor, ctx, kind):
        if kind != 'foe_pre_any':
            return fire(self, actor, ctx, kind)

    def lost_repeat(d, lines, rules):
        out = normalize(d, lines, rules)
        for ln in out:
            if ln.eff.get('belgras_repeat'):
                ln.eff['times'] = 5
        return out

    cases = [
        ('옛 해석 복원', 'test_all_fifty_rows_and_scope_and_legacy_cache', (S, 'normalize'),
         lambda d, lines, rules: lines),
        ('예약 생략', 'test_exactly_one_queued_self_hit_and_cast_snapshot', (Battle, '_exec_line'), no_queue),
        ('예약 대신 즉시 피해', 'test_exactly_one_queued_self_hit_and_cast_snapshot', (Battle, '_exec_line'), immediate),
        ('예약 피해 실행 생략', 'test_reactions_before_damage_before_turn_end', (Battle, 'flush_belgras_damage'), lambda self: None),
        ('적 행동 시작 통지 생략', 'test_erosion_boundary_marker_for_attack_and_nonattack', (Battle, 'fire_foes'), no_action),
        ('협공 전 표지 정리 생략', 'test_marker_clears_before_coop_and_nested_casts_do_not_inherit', (S, 'expire_marker'), lambda b, ctx: None),
        ('광역 5회 감소 반복 유실', 'test_erosion_boundary_marker_for_attack_and_nonattack', (S, 'normalize'), lost_repeat),
        ('다른 적으로 범위 확대', 'test_all_fifty_rows_and_scope_and_legacy_cache', (S, 'is_stage'), lambda d: True),
    ]
    for name, method, target, replacement in cases:
        check(name, method, target, replacement)
    print(f'변이 {len(cases)}개 검출, 패치 자동 원복')


if __name__ == '__main__':
    main()
