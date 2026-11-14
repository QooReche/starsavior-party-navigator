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



def _buff_banned(mode, forced):
    """〈강화 불가〉(CantGetMoreBuff) 거부도 강제 적용이면 생략(NKM:4389 IsPositive && !OBF_8151)."""
    b = battle([unit('a')], [unit('f')], mc={'se_force_apply': mode})
    f = b.foes[0]
    ln = Line('[스킬 사용 후] 자신에게 〈공격력 증가〉 (2턴 / 공격력% +10%)', '기본기', 'active')
    f.d.force_lines = {(ln.slot, ln.raw)} if forced else set()
    give(f, '강화 불가', harmful=True, dur=3)
    ctx = Ctx(f, f, f.d.skills['기본기'])
    ctx.target, ctx.targets = f, [f]
    b.run_line(f, ln, ctx)
    return f


def test_forced_buff_passes_buff_ban_client():
    assert '공격력 증가' in _buff_banned('client', True).eff
    assert '공격력 증가' not in _buff_banned('client', False).eff
    assert '공격력 증가' not in _buff_banned('off', True).eff


def _buff_forced(mode, name, **kw):
    """버프 자체 ForceApplyEffect(BUFF_TEMPLET, 예: 불협화음(해제불가) 300413)도 SE 강제와 같다(OBF_8151 = SE || 버프, NKM:6112)."""
    b = battle([unit('a')], [unit('f')], mc={'se_force_apply': mode})
    a, f = b.allies[0], b.foes[0]
    ln = Line('[스킬 사용 후] 스킬 대상에게 〈%s〉 (2턴)' % name, '기본기', 'active')
    f.d.force_lines = set()
    if kw.get('guard'):
        give(a, kw['guard'], dur=3)
    ctx = Ctx(f, f, f.d.skills['기본기'])
    ctx.target, ctx.targets = a, [a]
    if kw.get('evaded'):
        ctx.evaded.add(a)
    b.run_line(f, ln, ctx)
    return a


def test_buff_force_flag_passes_evade_and_immune_client():
    from battlesim.mc import buff_flags
    assert '불협화음(해제불가)' in buff_flags()['force_apply'] and '기절' not in buff_flags()['force_apply']
    for kw in (dict(evaded=True), dict(guard='면역')):
        assert '불협화음(해제불가)' in _buff_forced('client', '불협화음(해제불가)', **kw).eff, kw
        if kw.get('evaded'):    # 면역(CantGetMoreDebuff)은 옛 immune_force_apply 이름 통과가 이미 있어 off 에서도 통과
            assert '불협화음(해제불가)' not in _buff_forced('off', '불협화음(해제불가)', **kw).eff, kw
        assert '공격력 감소' not in _buff_forced('client', '공격력 감소', **kw).eff, kw     # 강제 아닌 효과는 그대로 막힘

if __name__ == '__main__':
    n = 0
    for k, fn in list(globals().items()):
        if k.startswith('test_') and callable(fn):
            fn(); n += 1
    print('ok', n)
