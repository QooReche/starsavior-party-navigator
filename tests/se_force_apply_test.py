# -*- coding: utf-8 -*-
"""SE 행 ForceApplyEffect 인 적 효과 줄이 면역·회피를 건너뛰는지 mc.se_force_apply.
클라: 부여 검사(build 26610546 NKM.decompiled.cs 4318-4327·4394-4416)의 면역·회피 거부는 강제 적용(OBF_8151)이면 생략,
OBF_8151 = SE 행 ForceApplyEffect || 버프 ForceApplyEffect(생성자 6112). 효과 적중 판정은 별개.
자료: tools/build_foe_auto.py 가 SE↔효과 줄을 짝지어 force 를 담음(data/foe_auto.json). 홍염 양각 보스 «솟구치는 환영»은
머리말 정규식이 «「환상(해제불가)」 상태인 적»의 괄호를 못 읽어 짝짓기가 실패했었음.
실행: python -X utf8 -I tests/se_force_apply_test.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from simkit import battle, give, unit                            # noqa: E402
from battlesim.mc import Ctx                                     # noqa: E402
from battlesim.rules import MC_OPTS                              # noqa: E402
from battlesim.starsavior import foe as F                        # noqa: E402
from battlesim.starsavior.parser import Line                     # noqa: E402

STUN = '[스킬 사용 후] 스킬 대상에게 〈기절〉 (1턴)'


def _run(mode, forced, guard=None, evaded=False, immune_list=False):
    b = battle([unit('a')], [unit('f')], mc={'se_force_apply': mode})
    a, f = b.allies[0], b.foes[0]
    ln = Line(STUN, '기본기', 'active')
    f.d.force_lines = {(ln.slot, ln.raw)} if forced else set()
    if guard:
        give(a, guard, dur=3)
    if immune_list:
        a.d.immune = {'기절'}
    ctx = Ctx(f, f, f.d.skills['기본기'])
    ctx.target, ctx.targets = a, [a]
    if evaded:
        ctx.evaded.add(a)
    b.run_line(f, ln, ctx)
    return b, a


def test_default_client():
    assert MC_OPTS['se_force_apply'] == 'client'


def test_forced_passes_client():
    for kw in (dict(guard='면역'), dict(evaded=True), dict(immune_list=True)):
        b, a = _run('client', True, **kw)
        assert '기절' in a.eff, kw
        assert b.rule_hits['se_force_apply'] >= 1, kw


def test_forced_blocked_legacy_and_unforced():
    for kw in (dict(guard='면역'), dict(evaded=True), dict(immune_list=True)):
        assert '기절' not in _run('off', True, **kw)[1].eff, kw
        assert '기절' not in _run('client', False, **kw)[1].eff, kw


def test_bellwether_force_data():
    units = json.loads((ROOT / 'data' / 'foe_auto.json').read_text(encoding='utf-8'))['units']
    forced = {k: v['force'] for k, v in units.items() if v.get('force')}
    assert len(forced) == 5 and all(v == ['502:2'] for v in forced.values()), forced
    raw = F.load_foe()
    assert '〈착란 체크용 버프〉' in raw['s'][502]['ef'][2]
    ui = int(next(iter(forced)).split(':')[1])
    d = F.FoeDef(raw, ui, int(next(iter(forced)).split(':')[2]))
    assert ('특수기', raw['s'][502]['ef'][2]) in d.force_lines


if __name__ == '__main__':
    n = 0
    for k, fn in list(globals().items()):
        if k.startswith('test_') and callable(fn):
            fn(); n += 1
    print('ok', n)
