"""전투력 차이 보정(power_penalty=model) 클라 대조. 계정 자료 없이 검증.

- 비율 정의: 클라 경고 구간 조회 Star.Templets:6514-6544(OBF_22329.OBF_5481)는
  (long)전투력*10000/권장 (정수 내림), 부족분 = 10000 - 비율. 엔진 power_pen 이 같은 비율·같은 행을 써야 함.
- 표: 엔진이 읽는 databook topics.pen·data/power_penalty.json 이 클라 데이터 BATTLE_POWER_RANGE_TEMPLET(500행)과,
  경고 표 tribe 가 BATTLE_POWER_TRIBE_TEMPLET(21행)과 같아야 함(STARSAVIOR_STATIC 없으면 표 대조만 건너뜀).
- 구조: RANGE 의 배율 꺾임(2%p 간격)이 클라가 보여 주는 TRIBE 단계 경계(부족분 1000~5000, 200 간격)와 같은 격자.
실행: python -X utf8 -I tests/power_penalty_client_test.py  (--mutate: 일부러 틀린 정의로 실패 확인용)
"""
import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT)]
from battlesim.api import power_pen                    # noqa: E402
from battlesim.starsavior.data import get_db           # noqa: E402

PEN = json.loads((ROOT / 'data' / 'power_penalty.json').read_text(encoding='utf-8'))


def client_ratio(power, rec):
    """Star.Templets:6521 의 비율(정수 내림)."""
    return power * 10000 // rec


def static_rows(name):
    static = os.environ.get('STARSAVIOR_STATIC')
    if not static:
        return None
    p = Path(static) / 'tables' / ('%s.json' % name)
    if not p.exists():
        return None
    d = json.loads(p.read_text(encoding='utf-8'))
    return d['Data'] if isinstance(d, dict) else d


class PowerPenaltyClientTest(unittest.TestCase):
    def test_ratio_and_row_follow_client_lookup(self):
        db = get_db()
        # (전투력, 권장) → 비율이 행 경계 바로 양쪽에 오도록 고른 합성 값
        cases = [(7608, 10000), (8999, 10000), (9000, 10000), (9990, 10000), (4999, 10000), (5000, 10000),
                 (12345, 16000), (10001, 10000), (333333, 1000000), (8000, 10000), (7999, 10000)]
        for power, rec in cases:
            r = client_ratio(power, rec)
            pp = power_pen(power, rec, db)
            self.assertEqual(round(pp[0] * 100), r, (power, rec))
            row = next((x for x in PEN['pen'] if x[0] <= r < x[1]), None)
            if row is None:   # 표 위(비율 >= 9990) = 보정 없음
                self.assertGreaterEqual(r, max(x[1] for x in PEN['pen']))
                self.assertEqual(pp[1:], (1.0, 1.0), (power, rec))
            else:
                self.assertEqual(pp[1:], (row[2] / 10000, row[3] / 10000), (power, rec))
        self.assertEqual(power_pen(7608, 10000, db), (76.08, .755, 1.245))
        self.assertEqual(power_pen(8999, 10000, db)[1:], (.999, 1.001))
        self.assertEqual(power_pen(9000, 10000, db)[1:], (1.0, 1.0))
        self.assertEqual(power_pen(4999, 10000, db)[1:], (.1, 1.9))

    def test_engine_table_is_client_range_table(self):
        self.assertEqual(get_db().main['topics']['pen'], PEN['pen'])
        rows = static_rows('BATTLE_POWER_RANGE_TEMPLET')
        if rows is None:
            self.skipTest('STARSAVIOR_STATIC 없음')
        self.assertEqual(len(rows), 500)
        client = sorted([r['UnderBattlePowerMin'], r['UnderBattlePowerMax'], r['TeamADamageRate'], r['TeamBDamageRate']]
                        for r in rows)
        self.assertEqual(client, sorted(PEN['pen']))

    def test_warning_table_is_client_tribe_table(self):
        rows = static_rows('BATTLE_POWER_TRIBE_TEMPLET')
        if rows is None:
            self.skipTest('STARSAVIOR_STATIC 없음')
        client = sorted([r['UnderBattlePowerMin'], r['UnderBattlePowerMax'], bool(r.get('IsBattlePowerPopup'))] for r in rows)
        self.assertEqual(client, sorted([t[0], t[1], t[3]] for t in PEN['tribe']))

    def test_range_steps_sit_on_tribe_grid(self):
        rows = sorted(PEN['pen'])
        steps = {b[0] for a, b in zip(rows, rows[1:]) if abs(b[2] - a[2]) > 20}
        grid = {10000 - t[0] for t in PEN['tribe'] if 1200 <= t[0] <= 4800} | {5000, 5200}
        self.assertEqual(steps, {s for s in grid if s < 9000} | {5000})
        self.assertTrue(all(a + b == 20000 for _, _, a, b in rows))
        onset = max(r[1] for r in rows if r[2] != 10000)
        self.assertEqual(onset, 9000)    # 보정 시작 = TRIBE «경계»(부족분 10%) 시작과 같은 비율


if __name__ == '__main__':
    if '--mutate' in sys.argv:
        sys.argv.remove('--mutate')
        import battlesim.api as api
        orig = api.power_pen

        def shortfall_lookup(power, rec, db):   # 틀린 해석: RANGE 를 부족분으로 조회
            r = orig(power, rec, db)
            if r is None:
                return r
            s = 10000 - int(round(r[0] * 100))
            row = next((x for x in db.main['topics']['pen'] if x[0] <= s < x[1]), None)
            return (r[0], row[2] / 10000, row[3] / 10000) if row else (r[0], 1.0, 1.0)
        globals()['power_pen'] = shortfall_lookup
    unittest.main()
