# -*- coding: utf-8 -*-
"""mc.dead_keep_dnp 기본 client(2026-11-14 전환): 사망·부활 뒤에도 DeadNotDispel 효과(쇠락 등)가 남는다.
클라 부활(OBF_25709.OBF_27662, build 26610546 NKM.decompiled.cs 5436-5455)은 DeadNotDispel 이 아닌 버프와
죽은 시전자의 도발만 지운다. 옛 기본(off)은 사망 때 전부 지워 부활 최대 HP 를 크게 봤다.
분기 자체는 followup_d_test.test_dnp_and_stage_fx_revive 가 두 값으로 검사함 — 여기서는 «기본값으로» 도는지만.
실행: python -X utf8 -I tests/dead_keep_default_test.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from simkit import battle, give, unit                            # noqa: E402
from battlesim.mc import Ctx                                     # noqa: E402
from battlesim.rules import MC_OPTS, MC_RULES                    # noqa: E402
from battlesim.starsavior.parser import Line                     # noqa: E402


def test_default_client():
    assert MC_OPTS['dead_keep_dnp'] == 'client' and MC_RULES['dead_keep_dnp']['legacy'] == 'off'


def test_default_battle_keeps_dnp_on_death():
    b = battle([unit('owner'), unit('target')], [unit('foe')])       # 규칙 덮어쓰기 없음 = 기본값
    owner, target = b.allies
    ctx = Ctx(owner, owner, owner.d.skills['기본기'])
    ctx.target, ctx.targets = target, [target]
    b.run_line(owner, Line('[스킬 사용 후] 스킬 대상에게 〈폭주 : 쇠락〉 (지속 무한 / 생명력% -5%)', '기본기', 'active'), ctx)
    give(target, '공격력 증가', {'공격력%': 20.0})
    b.kill(target, b.foes[0])
    assert '폭주 : 쇠락' in target.eff and '공격력 증가' not in target.eff
    assert b.rule_hits['dead_keep_dnp'] >= 1


if __name__ == '__main__':
    test_default_client()
    test_default_battle_keeps_dnp_on_death()
    print('ok 2')
