"""허용 목록 D 남은 항목 재조사(PC 26752678) — 클라에서 확인되는 부분만 엔진과 대조. 계정 자료 없이 검증.

남긴 항목(서버 전용)의 클라 쪽 «경계»를 고정해, 엔진이 클라와 어긋나면 실패하게 한다.
- 코스모 HUD 점수: NKM:17371-17374 clamp(기본 + 최대 피해 점수 x ((최대HP-HP)x10000/최대HP)/10000, 0, 기본+최대 피해 점수),
  NKC:69007-69016 이 코스모 HUD 에서 이 식만 부름. 엔진 cosmo_score(클리어 전, Lv0)가 같은 정수값이어야 함.
- 달성 점수: STRING_COMMON SI_ACHIEVEMENT_SCORE_DESC_01 «달성 점수에는 추가 점수 배율이 적용되지 않습니다».
- 난이도 표시: NKC:683337-683345·85807-85814 가 ScaleFactor 를 NKM.Templets:33034-33042 (값 x 0.01)% 로 «+N%» 표시.
  엔진 배율 1 + ScaleFactor/10000 은 같은 의미(서버의 곱 순서·정수화는 미확인, 문서 참조).
- 코스모 배율 필드: data/cosmo_raid.json 의 StatScale/TacticsScale/StarLinkScale 가 클라 표와 같아야 함
  (클라는 Star.Templets:9377-9379 에서 읽기만 하고 RankingRaid 배율 묶음은 만들지 않음 → 엔진 미사용 차이를 문서에 기록).
실행: python -X utf8 -I tests/allowlist_remain_1121_test.py  (--mutate: 일부러 틀린 정의로 실패 확인용)
"""
import json
import math
import os
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT)]
from battlesim.starsavior import cosmo_raid as C   # noqa: E402

G = C.load()
REBUILD_T = Path(os.environ.get('REBUILD_26752678', 'E:/AI_mk2/rebuild_26752678')) / 'T'


def client_hud(base, max_damage, max_hp, hp):
    """NKM:17371-17374 그대로(정수 연산)."""
    v = base + max_damage * ((max_hp - hp) * 10000 // max_hp) // 10000
    return max(0, min(v, base + max_damage))


def cosmo_rows(name):
    """COSMO_TABLES(CLIENT_ 접두 추출본, cosmo_raid_test 와 같은 관례)의 표 행. 없으면 None."""
    tables = os.environ.get('COSMO_TABLES')
    if not tables:
        return None
    p = Path(tables) / ('CLIENT_%s.json' % name)
    if not p.exists():
        return None
    s = re.sub(r',(\s*[}\]])', r'\1', p.read_text(encoding='utf-8'))
    d = json.loads(s)
    return d['Data'] if isinstance(d, dict) else d


def string_value(key):
    p = REBUILD_T / 'hard' / 'STRING_COMMON.json'
    if not p.exists():
        return None
    s = re.sub(r',(\s*[}\]])', r'\1', p.read_text(encoding='utf-8'))
    for r in json.loads(s)['Data']:
        if r.get('Key') == key:
            return r.get('Value')
    return None


class RemainAllowlistTest(unittest.TestCase):
    def test_hud_part_matches_client_formula(self):
        max_hp = 1000000
        for b in G['bosses']:
            st = b['steps'][2]
            for hp in (max_hp, 999999, 750001, 500000, 499999, 123457, 1, 0):
                frac = (max_hp - hp) / max_hp
                got = C.cosmo_score(G, 0, frac, 0, 0, False, boss=b['key'], step=3)
                self.assertEqual(got, client_hud(st['base'], st['maxDamage'], max_hp, hp), (b['key'], hp))

    def test_achievement_not_multiplied(self):
        text = string_value('SI_ACHIEVEMENT_SCORE_DESC_01')
        if text is not None:
            self.assertIn('달성 점수에는 추가 점수 배율이 적용되지 않습니다', text)
        b = G['bosses'][0]
        row = C.level_row(b, len(b['levels']))
        self.assertGreater(row['scoreBonus'], 0)
        no_half = C.cosmo_score(G, len(b['levels']), 0.4999, 0, 0, False, boss=b['key'])
        half = C.cosmo_score(G, len(b['levels']), 0.5, 0, 0, False, boss=b['key'])
        st = b['steps'][2]
        raw_gain = st['maxDamage'] * 5000 // 10000 - st['maxDamage'] * 4999 // 10000
        scaled_gain = (st['base'] + st['maxDamage'] * 5000 // 10000) * (10000 + row['scoreBonus']) + 5000
        scaled_gain = scaled_gain // 10000 - ((st['base'] + st['maxDamage'] * 4999 // 10000) * (10000 + row['scoreBonus']) + 5000) // 10000
        self.assertGreater(raw_gain, 0)
        self.assertEqual(half - no_half, scaled_gain + row['half'], '반 달성 점수는 배율 없이 더해짐')

    def test_difficulty_scale_matches_client_display(self):
        b = G['bosses'][0]
        row = C.level_row(b, len(b['levels']))
        stats = dict(atk=10000, hp=1000000, def_=0)
        stats['def'] = stats.pop('def_') + 3000
        got = C._scale_stats(stats, row)
        for key, field in (('atk', 'atk'), ('hp', 'hp'), ('def', 'def')):
            shown_pct = row[field] * 0.01                       # NKM.Templets:33034-33037 → «+N%»
            self.assertEqual(got[key], math.floor(stats[key] * (1 + shown_pct / 100)), key)

    def test_cosmo_scale_fields_match_client_table(self):
        rows = cosmo_rows('BATTLE_TEMPLET_RANKING_RAID')
        if rows is None:
            self.skipTest('COSMO_TABLES 없음')
        by_id = {r['BattleID']: r for r in rows if 'BattleID' in r}
        n = 0
        for b in G['bosses']:
            for st in b['steps']:
                r = by_id[st['battleId']]
                self.assertEqual((st['statScale'], st['tacticsScale'], st['starLinkScale']),
                                 (r.get('StatScale'), r.get('TacticsScale'), r.get('StarLinkScale')), st['battleId'])
                self.assertEqual(st['survivor'], r.get('RemainingSaviorPoint', 0), st['battleId'])
                n += 1
        self.assertGreater(n, 0)


if __name__ == '__main__':
    if '--mutate' in sys.argv:
        sys.argv.remove('--mutate')
        orig_score, orig_scale = C.cosmo_score, C._scale_stats
        mode = os.environ.get('MUTATE', 'hud')

        if mode == 'hud':
            def wrong(G_, level, frac, *a, **k):          # 틀린 해석: 비율 내림 없이 반올림
                return orig_score(G_, level, min(1.0, frac + 0.00005), *a, **k)
            C.cosmo_score = wrong
        elif mode == 'half':
            def wrong(G_, level, frac, rt, sv, clear, boss=None, step=3):   # 틀린 해석: 달성 점수에도 배율
                t = orig_score(G_, level, frac, rt, sv, clear, boss=boss, step=step)
                b = C._boss_of(G_, boss) if boss else C._boss_of(G_, G_['season']['bossOrder'][0])
                row = C.level_row(b, level) if step == 3 else None
                if row and frac >= 0.5:
                    t += row['half'] * row['scoreBonus'] // 10000
                return t
            C.cosmo_score = wrong
        elif mode == 'scale':
            C._scale_stats = lambda s, row: {k: (v * (1 + row[k] / 1000) if row and k in ('atk', 'hp', 'def') else v)
                                             for k, v in s.items()}
    unittest.main()
