# -*- coding: utf-8 -*-
"""코드로 만드는 적 정의(코스모 시즌 보스·길드 BFB·api 의 직접 적은 적)의 공통 뼈대와 가상 스킬 생성.

FoeDef(foe.py, 데이터북 적)와 같은 속성 계약을 한 곳에서 채운다. 새 공통 속성은 여기에만 더한다.
하위 클래스는 고유 필드(cosmo·bfb·spawn·slot)만 덧붙인다.
"""
from collections import defaultdict

from .parser import Skill

_UNSET = object()


class FoeBase:
    is_foe = True

    def __init__(self, key, name, *, role, element, boss, attack_kind, stats, skills, lines=None, immune=()):
        self.key, self.name = key, name
        self.id, self.variant = -1, '적'
        self.role, self.element = role, element
        self.boss = boss
        self.grade = '보스' if boss else '일반'
        self.attack_kind = attack_kind
        self.stats = stats
        self.immune = set(immune)
        self.skills = skills
        self.trigger_skills, self.unmodeled = {}, []
        self.lines = [] if lines is None else lines
        self.desc = {}
        self.passive = defaultdict(float)
        self.nb, self.manual, self.gear_atkp = {}, None, 0.0
        self.effect_info = {}
        self.spd_base = stats['spd']
        self.react, self.auto, self.auto_lines = {}, {}, {}


def make_skill(slot, name, cf, cd, *, tg, all_=False, attack=True, tough=_UNSET, lines=_UNSET):
    """가상 액티브 스킬. cf 는 정수 계수(공격력 × cf/100 %) — 단위 변환(코스모 round(coef*100)·길드 int(coef))은 호출부에서.
    tough·lines 를 안 주면 sk.ab·sk.semantic_lines 를 만들지 않는다(엔진이 getattr/hasattr 로 «없음»을 구분)."""
    sk = Skill(dict(sl=slot, n=name, ty='액티브', tg=tg, act='공격' if attack else '비공격', cf=[cf, 0, 0, 0],
                    all=all_, cd=cd, nv=0))
    if tough is not _UNSET:
        sk.ab = tough
    if lines is not _UNSET:
        sk.semantic_lines = lines
    return sk
