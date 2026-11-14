# -*- coding: utf-8 -*-
"""전투 중 최종 능력치·연쇄 피해 공통 계산(stat_stage·stat_floor·buff_maxhp·chain_round·chain_stat_true =client).
몬테카를로 엔진(mc.Battle)과 기대값 엔진(engine.Sim)이 같은 식을 쓴다(gauge.py 와 같은 방식).

근거 = build 26610546 static-data decompiled/NKM/NKM.decompiled.cs
  18874-18891 OBF_16891: 1단 값 + 2단 고정 + 1단 값 x 2단 % 합(패시브 스킬 능력치·장비 %)
  18892-18897 최종 능력치 = (int)Math.Floor(앞 단 값 + 3단 고정 + 앞 단 값 x 3단 비율), 3단 비율 = 만분율 정수 합 x 0.0001
  18272-18358 최대 생명력 = 전투 전 최종값 x (1 + 버프 생명력% + 서든데스 생명력%) 를 정수로
  4730-4740·6212-6236 일반 연쇄(추가) 피해 값 = (int)((능력치 x 계수 + 그 x 증가합) x 1.85)
  6214-6217 ADT_STAT_TRUE 연쇄 = (int)(능력치 x 계수)
"""
import math


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


def stage3(b0, r3, floor):
    """공격력·방어력 최종값(stat_stage=client): floor 면 Floor(b0 + b0 x 3단 비율), 아니면 b0 x (1 + r3)."""
    if floor:
        return float(math.floor(b0 + b0 * rate3(r3)))
    return b0 * (1 + r3)


def spd_stage2(d, rate, flat):
    """속도 2단 값. 전투 전 속도가 기본 속도(spd_base)와 같을 때만 단 자료를 쓴다."""
    if d.stats.get('spd') == d.spd_base:
        return unit_stage2(d, 'spd', rate, flat)
    return d.spd_base * (1 + rate) + flat


def spd_stage3(s2, r3, f3, floor):
    """속도 최종값(stat_stage=client, 리더 +10 전): s2 + s2 x 3단 비율 + 3단 고정, floor 면 (int)Math.Floor(NKM:18897)."""
    s = s2 + s2 * rate3(r3) + f3
    return math.floor(s) if floor else s


def atk_client(d, r3, floor):
    """구원자 최종 공격력(stat_stage=client). 2단 = 패시브 공격력% + 장비 공격력%, r3 = 버프(+이번 시전 한정) 공격력%."""
    return stage3(unit_stage2(d, 'atk', d.passive['atkp'] + d.gear_atkp), r3, floor)


def def_from_base(b0, r3, floor):
    """방어력 최종값(stat_stage=client, 0 하한). b0 = 2단까지 값."""
    return max(0.0, stage3(b0, r3, floor) if floor else max(0.0, b0 * (1 + r3)))


def def_client(d, r3, floor):
    """구원자 최종 방어력(stat_stage=client, 0 하한)."""
    return def_from_base(unit_stage2(d, 'def', d.passive['defp']), r3, floor)


def spd_from_base(s2, r3, floor):
    """2단 고정·3단 고정이 없는 유닛(기대값 엔진의 적)의 최종 속도(stat_stage=client, 하한 전)."""
    return spd_stage3(s2, r3, 0.0, floor)


def spd_client(d, m_spdp, m_spdf, floor):
    """구원자 최종 속도(stat_stage=client, 리더 +10·하한 전)."""
    p = d.passive
    return spd_stage3(spd_stage2(d, p['spdp'], p['spdf']), m_spdp, m_spdf, floor)


def maxhp0(hp, rate):
    """전투 전 최종 최대 생명력 = floor(능력치 x (1 + 패시브·스테이지 생명력%))."""
    return float(math.floor(hp * (1 + rate)))


def maxhp(hp0, buff_rate, sd_rate=0.0):
    """현재 최대 생명력 = floor(전투 전 값 x (1 + 버프 생명력% + 서든데스 생명력%)), 묶음 −99% 하한(NKM:18272-18358)."""
    return float(math.floor(hp0 * max(0.01, 1 + buff_rate + sd_rate)))


def chain_value(val, coef, inc, base_mult):
    """일반 연쇄 피해 값(chain_round=client): (int)((능력치 x 계수 + 그 x 증가합) x 1.85)."""
    return float(int((val * coef + val * coef * inc) * base_mult))


def chain_true_value(val, coef):
    """ADT_STAT_TRUE 연쇄 피해 값(chain_stat_true=client): (int)(능력치 x 계수)."""
    return float(int(val * coef))
