# -*- coding: utf-8 -*-
"""표준 육성 여정(스텔라 아카이브) 환산이 클라와 같은지.

클라 build 26610546:
- 환산 NKM.decompiled.cs:19121-19137(StatFactorBundle): 여정 스탯마다 0~1500 으로 자르고 × 1차→2차 계수
  (Plain/CLIENT_CONST_TEMPLET JourneyStat: 힘→공격력 1, 체력→생명력 6, 인내→방어력 0.5, 집중→효과 적중 0.04%p, 보호→효과 저항 0.04%p,
  읽기 NKM.Templets.decompiled.cs:29837-29866) × 직업 배율(JOURNEY_STAT_ROLE_TYPE_TEMPLET Multiply*, 1/10000), (int) 버림.
- 기록 값(어느 스탯에 얼마)은 플레이어가 여정에서 고른 훈련 결과다 — 자동 여정도 훈련 비율 슬라이더 5개를 사람이 정하고
  (NKC.decompiled.cs:303218~ NKCPopupJourneyAutoParam journeyStatSliders·trainingFrequency, 모두 0 이면 시작 불가) 진행 결과는
  서버가 준다. 그래서 엔진 표준 기록(rules/builds.json journey, assumed)의 배분은 클라 근거가 없고, 이 시험은 환산·배율만 지킨다.
실행: python -X utf8 -I tests/journey_client_test.py (비공개 표 대조는 STARSAVIOR_STATIC 이 있을 때만)"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT)]
from battlesim.starsavior.build import setting_spec   # noqa: E402
from battlesim.starsavior.data import DB              # noqa: E402
from battlesim.starsavior.parser import UnitDef       # noqa: E402
from tools.runtime import static_path_or_none          # noqa: E402

FACTOR = (('atk', 1.0), ('hp', 6.0), ('def', 0.5), ('eh', 4.0), ('er', 4.0))   # CLIENT_CONST JourneyStat (집중·보호 4 = 0.04%p = 엔진 4/10000)


def client_journey(js, mul5):
    return {k: int(min(max(v, 0), 1500) * f * m / 10000) for (k, f), v, m in zip(FACTOR, js, mul5)}


def test_standard_journey_matches_client_formula():
    db = DB(str(ROOT))
    growth = json.loads((ROOT / 'data/growth.json').read_text(encoding='utf-8'))
    n = 0
    for key, a in growth['assumed']['units'].items():
        mul3 = growth['units'][str(a['uid'])]['journey_mul']      # tools/build_growth.py: JOURNEY_STAT_ROLE_TYPE_TEMPLET 그대로
        d = UnitDef(db, key, level=200, res_stage=10, star=0, build='none')
        sp = setting_spec(db, key, db.units[key], base_stats=d.stats, passive_cr=d.passive['cr'])
        assert sp['journey'] == client_journey(sp['journey_raw'], list(mul3) + [10000, 10000]), key
        n += 1
    assert n >= 50, n


def test_client_tables_match_constants():
    st = static_path_or_none(ROOT)
    if st is None:
        print('건너뜀: 비공개 표 없음')
        return
    tables = Path(st) / 'tables'
    text = (tables / 'Plain' / 'CLIENT_CONST_TEMPLET.json').read_text(encoding='utf-8')
    block = text[text.index('"JourneyStat"'):]
    got = [int(re.search(r'"%s":\s*(\d+)' % s, block).group(1)) for s in
           ('NST_ATK', 'NST_HP', 'NST_DEF', 'NST_RATE_EFFECT_HIT', 'NST_RATE_EFFECT_EVADE')]
    # 공격력·생명력·방어력은 1/10000 계수, 효과 적중·저항은 비율 스탯이라 계수 × 배율 원값(10000) — 엔진 단위로 4
    assert got == [10000, 60000, 5000, 4, 4], got
    rows = json.loads((tables / 'JOURNEY_STAT_ROLE_TYPE_TEMPLET.json').read_text(encoding='utf-8'))['Data']
    for r in rows:
        assert r['MultiplyFocus'] == 10000 and r['MultiplyProtect'] == 10000, r['JourneyStatRoleType']
    db = DB(str(ROOT))
    role = {'NURT_' + r['JourneyStatRoleType'][5:]: r for r in rows}
    ko = {'NURT_DEFENDER': '디펜더', 'NURT_STRIKER': '스트라이커', 'NURT_RANGER': '레인저', 'NURT_CASTER': '캐스터',
          'NURT_ASSASSIN': '어쌔신', 'NURT_SUPPORTER': '서포터'}
    for k, name in ko.items():
        r = role[k]
        mul = next(x['mul'] for x in db.main['topics']['roles'] if x['n'] == name)     # build.py 가 쓰는 데이터북 배율
        want = [r['Multiply' + s] / 10000 for s in ('Power', 'Health', 'Endurance', 'Focus', 'Protect')]
        assert [round(x, 4) for x in mul] == want, (name, mul, want)


if __name__ == '__main__':
    n = 0
    for k, fn in list(globals().items()):
        if k.startswith('test_') and callable(fn):
            fn(); n += 1
    print('ok', n)
