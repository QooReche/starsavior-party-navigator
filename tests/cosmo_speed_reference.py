"""93d300f의 이전 경로. 최적화 동일성 시험용이며 운영 엔진에서는 사용하지 않음."""
from battlesim.mc import REACT_TRIG
from contextlib import ExitStack, contextmanager
from unittest.mock import patch
from battlesim import mc


@contextmanager
def mode(name):
    """baseline / dirty / line / all 경로를 각각 비교한다."""
    with ExitStack() as stack:
        if name in ('baseline', 'line'):
            stack.enter_context(patch.object(mc.Battle, 'dirty', old_dirty))
        if name in ('baseline', 'dirty'):
            stack.enter_context(patch.object(mc, 'line_kind', old_line_kind))
        yield


def old_line_kind(ln):
    """확률 엔진에서 쓰는 줄 시점. 기대값 엔진의 kind 에 반응 시점을 더한다."""
    if ln.kind != 'unmodeled':
        if ln.phase == '웨이브 시작 시' and ln.kind == 'battle_start':
            return 'wave_start'
        return ln.kind
    if ln.trig:
        for k, v in REACT_TRIG:
            if ln.trig.startswith(k):
                return v
        return 'unmodeled'
    if ln.phase == '피해 처리 직전':
        return 'prehit_self'
    if ln.phase == '피해 처리 후':
        return 'hit_self'      # 조건 없는 「피해 처리 후」 = 내가 피격된 뒤(적 설명문 「피격 후 …」와 일치, 가정)
    if ln.phase == '피격 시':
        return 'hit_self'
    return 'unmodeled'


def old_dirty(self, u):
    u._m = None
    if self.mc['buff_maxhp'] == 'on' and u.hp > u.maxhp:
        # 효과가 바뀌어 최대 생명력이 줄면 현재 생명력을 바로 자른다(늘어도 전투 중엔 채우지 않음 — NKM 2828~2839).
        # 조회(maxhp)에는 부수효과를 두지 않는다 — hp/maxhp 를 읽는 순서에 따라 값이 달라지지 않게(codex 리뷰)
        u.hp = u.maxhp
