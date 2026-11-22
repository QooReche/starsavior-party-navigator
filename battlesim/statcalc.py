# -*- coding: utf-8 -*-
"""전투 중 최종 능력치·연쇄 피해 공통 계산(클라 3단 구성·단마다 Floor·버프 최대 생명력·연쇄 선정수화·ADT_STAT_TRUE 연쇄).
몬테카를로 엔진(mc.Battle)과 기대값 엔진(engine.Sim)이 같은 식을 쓴다(gauge.py 와 같은 방식).

근거 = build 26610546 static-data decompiled/NKM/NKM.decompiled.cs
  18874-18891 OBF_16891: 1단 값 + 2단 고정 + 1단 값 x 2단 % 합(패시브 스킬 능력치·장비 %)
  18892-18897 최종 능력치 = (int)Math.Floor(앞 단 값 + 3단 고정 + 앞 단 값 x 3단 비율), 3단 비율 = 만분율 정수 합 x 0.0001
  18272-18358 최대 생명력 = 전투 전 최종값 x (1 + 버프 생명력% + 서든데스 생명력%) 를 정수로
  4730-4740·6212-6236 일반 연쇄(추가) 피해 값 = (int)((능력치 x 계수 + 그 x 증가합) x 1.85)
  6214-6217 ADT_STAT_TRUE 연쇄 = (int)(능력치 x 계수)
"""
import math

from . import rules as _rules
from .rules import ELEM_BEATS, ELEM_LOSES


# ------------------------------------------------------------------ 피해식 조각(설계 fable_unify B1·B2) — 연산 순서를 옮겨 온 그대로
def def_rate(de):
    """방어율 = 방어 / (방어 + DEF_K). DEF_K 는 부를 때 rules 에서 읽음(tools/boss_hit_diagnostic.py PvP 민감도가 rules.DEF_K 를 바꿈)."""
    return de / (de + _rules.DEF_K)


def def_rate_pen(dr, pen, cap=True):
    """관통 뒤 방어율 max(0, dr - dr x pen). cap=True 면 pen 을 1 로 자른다(min(1, pen)) — 일반 피해식(mc.final_dmg)만 cap=False
    (호출부가 이미 min(1, pen + 추가) 로 잘라 넘김)."""
    return max(0.0, dr - dr * (min(1.0, pen) if cap else pen))


def elem_adv(a_el, v_el, step=0.05):
    """속성 상성: a 가 v 를 이기면 +step, 지면 -step, 아니면 0. 원소 None 가드는 호출부 몫(None 끼리 비교하면 «이김»이 됨)."""
    if ELEM_BEATS.get(a_el) == v_el:
        return step
    if ELEM_LOSES.get(a_el) == v_el:
        return -step
    return 0.0


def rate3(r):
    """3단(버프) 비율: 만분율 정수 합 x 0.0001(NKM:18892-18897)."""
    return round(r * 10000) * 0.0001


def stage2(st, cur, rate, flat=0.0):
    """2단까지의 값(NKM:18874-18891). st = calc_stats 가 남긴 (1단 값, 2단 %, 2단 고정) 또는 None, cur = 전투 전 능력치.
    그 값으로 다시 계산한 전투 전 능력치가 cur 와 같으면 1단 값 기준 한 합으로, 아니면(내정보 덮어쓰기 등) cur x (1 + rate) 로 근사."""
    if st is not None:
        s1, r2, f2 = st
        if math.floor(s1 + s1 * r2 + f2) == cur:
            return s1 + f2 + s1 * (r2 + rate) + flat
    return cur * (1 + rate) + flat


def unit_stage2(d, key, rate, flat=0.0):
    """유닛 정의 d 의 2단까지 값(d.stat_stage 가 없으면 전투 전 능력치로 근사)."""
    return stage2((getattr(d, 'stat_stage', None) or {}).get(key), d.stats[key], rate, flat)


def stage3(b0, r3):
    """공격력·방어력 최종값: Floor(b0 + b0 x 3단 비율)."""
    return float(math.floor(b0 + b0 * rate3(r3)))


def spd_stage2(d, rate, flat):
    """속도 2단 값. 전투 전 속도가 기본 속도(spd_base)와 같을 때만 단 자료를 쓴다."""
    if d.stats.get('spd') == d.spd_base:
        return unit_stage2(d, 'spd', rate, flat)
    return d.spd_base * (1 + rate) + flat


def spd_stage3(s2, r3, f3):
    """속도 최종값(리더 +10 전): (int)Math.Floor(s2 + s2 x 3단 비율 + 3단 고정)(NKM:18897)."""
    return math.floor(s2 + s2 * rate3(r3) + f3)


def atk_client(d, r3):
    """구원자 최종 공격력. 2단 = 패시브 공격력% + 장비 공격력%, r3 = 버프(+이번 시전 한정) 공격력%."""
    return stage3(unit_stage2(d, 'atk', d.passive['atkp'] + d.gear_atkp), r3)


def def_from_base(b0, r3):
    """방어력 최종값(0 하한). b0 = 2단까지 값."""
    return max(0.0, stage3(b0, r3))


def def_client(d, r3):
    """구원자 최종 방어력(0 하한)."""
    return def_from_base(unit_stage2(d, 'def', d.passive['defp']), r3)


def spd_from_base(s2, r3):
    """2단 고정·3단 고정이 없는 유닛(기대값 엔진의 적)의 최종 속도(하한 전)."""
    return spd_stage3(s2, r3, 0.0)


def spd_client(d, m_spdp, m_spdf):
    """구원자 최종 속도(리더 +10·하한 전)."""
    p = d.passive
    return spd_stage3(spd_stage2(d, p['spdp'], p['spdf']), m_spdp, m_spdf)


def maxhp0(hp, rate):
    """전투 전 최종 최대 생명력 = floor(능력치 x (1 + 패시브·스테이지 생명력%))."""
    return float(math.floor(hp * (1 + rate)))


def maxhp(hp0, buff_rate, sd_rate=0.0):
    """현재 최대 생명력 = floor(전투 전 값 x (1 + 버프 생명력% + 서든데스 생명력%)), 묶음 −99% 하한(NKM:18272-18358)."""
    return float(math.floor(hp0 * max(0.01, 1 + buff_rate + sd_rate)))


def chain_value(val, coef, inc, base_mult):
    """일반 연쇄 피해 값: (int)((능력치 x 계수 + 그 x 증가합) x 1.85)."""
    return float(int((val * coef + val * coef * inc) * base_mult))


def chain_true_value(val, coef):
    """ADT_STAT_TRUE 연쇄 피해 값: (int)(능력치 x 계수)."""
    return float(int(val * coef))
