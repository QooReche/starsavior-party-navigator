# -*- coding: utf-8 -*-
"""격전 의뢰 적 데이터 빌더(tools/build_foe_clash.py) 시험. 비공개 표(static-data)가 없는 PC 에서는 건너뜀.

  python -X utf8 -I tests/foe_clash_test.py

1) 출력 스키마가 foe.js 와 같은 키 집합이고 인덱스가 조각 안에서 닫혀 있는지
2) 데이터북 옛 판(모티베이터·웬디고·페르세스·고대 병졸)의 ef·gl 을 옛 클라 SE 행으로 다시 만든 일치율이 기록값 이상인지
3) 6단계 × 3보스(+소환 병졸) 스탯이 클라 표에서 «이 파일이 직접 계산한 값» 과 같은지(foe_stats 공식 b + gw×(L-1), AddStatData % 보정)
4) 스테이지 18개의 이름·레벨·전투력, 검증 못 한 줄이 ef 에 들어가지 않았는지, data/foe_clash.json 이 지금 빌더 출력과 같은지"""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.runtime import static_path_or_none   # noqa: E402
from tools.tables import jsonc                  # noqa: E402

STATIC = static_path_or_none(ROOT)
# 기록값(2026-11-12 빌드 26610546, 옛 판 비교): 이 값 아래로 내려가면 변환기가 퇴행한 것
RECORDED = dict(skills_exact=63, lines_exact=134, gl_exact=78, gl_lists_exact=63)
LV = [400, 665, 1047, 1611, 2181, 2751]
BP = [64450, 105525, 164735, 252155, 340505, 428855]
NUM = ['Ⅰ', 'Ⅱ', 'Ⅲ', 'Ⅳ', 'Ⅴ', 'Ⅵ']


def merge(raw, frag):
    """로더가 하는 일(data/foe_clash.json _note 의 규칙): 조각 인덱스에 오프셋을 더해 foe.js 뒤에 붙인다."""
    r = copy.deepcopy(raw)
    so, uo, xo = len(r['s']), len(r['u']), len(r['x'])
    if frag.get('ak'):
        raise AssertionError('조각 ak 가 비어 있지 않으면 이 병합 규칙으로는 부족함')
    r['s'] += copy.deepcopy(frag['s'])
    r['x'] += copy.deepcopy(frag['x'])
    for u in frag['u']:
        u2 = copy.deepcopy(u)
        u2['sk'] = [i + so for i in u['sk']]
        r['u'].append(u2)
    for g in copy.deepcopy(frag['g']):
        for t in g['tabs']:
            for st in t['s']:
                st['w'] = [[[e[0] + uo] + ([e[1] + xo] if len(e) > 1 else []) for e in w] for w in st['w']]
                for sm in st.get('sm', []):
                    sm[2] = [[a + uo, b + xo, c] for a, b, c in sm[2]]
        r['g'].append(g)
    return r


@unittest.skipIf(STATIC is None, '비공개 표 저장소(static-data) 없음')
class ClashBuildTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tools import build_foe_clash as B
        cls.B = B
        cls.out = B.build(STATIC)
        B.fix_sm(cls.out)
        cls.cmp = B.compare_old(cls.out['tb'], cls.out['raw'], cls.out['conv'], cls.out['shapes'])
        cls.raw = cls.out['raw']
        cls.frag = dict(u=cls.out['u'], s=cls.out['s'], x=cls.out['x'], ak=[], g=[cls.out['g']])
        cls.merged = merge(cls.raw, cls.frag)
        p = ROOT / 'data' / 'foe_clash.json'
        cls.doc = json.loads(p.read_text(encoding='utf-8')) if p.exists() else None

    # ---------------------------------------------------------------- 1) 스키마
    def test_schema_same_keys_as_foe_js(self):
        raw, f = self.raw, self.frag
        union = lambda rows: set(k for r in rows for k in r)   # noqa: E731
        self.assertLessEqual(union(f['u']), union(raw['u']))
        self.assertLessEqual(union(f['s']), union(raw['s']))
        self.assertLessEqual(union(f['x']), union(raw['x']))
        gk = union(raw['g'])
        self.assertEqual(set(f['g'][0]), {'k', 't', 'tabs'})
        self.assertLessEqual(set(f['g'][0]), gk)
        tab_keys = set(k for g in raw['g'] for t in g['tabs'] for k in t)
        stage_keys = set(k for g in raw['g'] for t in g['tabs'] for s in t['s'] for k in s)
        for t in f['g'][0]['tabs']:
            self.assertLessEqual(set(t), tab_keys)
            for s in t['s']:
                self.assertLessEqual(set(s), stage_keys)
                self.assertTrue({'n', 'lv', 'bp', 'w'} <= set(s))
        for u in f['u']:
            self.assertTrue({'n', 'g', 'el', 'r', 'k', 'b', 'gw', 'ti', 'im', 'sk'} <= set(u))
            self.assertEqual(len(u['b']), 10)
            self.assertEqual(len(u['gw']), 3)
        for s in f['s']:
            self.assertTrue({'sl', 'n', 'ty', 'tg', 'd1', 'ef'} <= set(s))
            self.assertIn(s['sl'], ('기본기', '특수기', '궁극기', '패시브'))
        # 같은 키 집합: 필드 값 종류(어휘)도 데이터북이 쓰는 것만
        self.assertLessEqual({s['ty'] for s in f['s']}, {s['ty'] for s in raw['s']})
        self.assertLessEqual({s['tg'] for s in f['s']}, {s['tg'] for s in raw['s']})
        self.assertLessEqual({u['el'] for u in f['u']}, {u['el'] for u in raw['u']})
        self.assertLessEqual({u['k'] for u in f['u']}, {u['k'] for u in raw['u']})

    def test_indexes_closed_inside_fragment(self):
        f, raw = self.frag, self.raw
        for u in f['u']:
            for i in u['sk']:
                self.assertTrue(0 <= i < len(f['s']))
        for x in f['x']:
            for a in x.get('a', []):
                self.assertTrue(0 <= a[0] < len(raw['ak']))          # x.a 는 기존 foe.js ak 인덱스
        for t in f['g'][0]['tabs']:
            for s in t['s']:
                for w in s['w']:
                    for e in w:
                        self.assertTrue(0 <= e[0] < len(f['u']))
                        if len(e) > 1:
                            self.assertTrue(0 <= e[1] < len(f['x']))
                for _gid, _who, lst in s.get('sm', []):
                    for ui, xi, n in lst:
                        self.assertTrue(0 <= ui < len(f['u']) and 0 <= xi < len(f['x']) and n >= 1)

    def test_merged_loads_in_engine(self):
        """병합한 raw 로 FoeDef 가 18 스테이지 전부에서 만들어지고, 효과 줄이 파서(Line)에서 «미해석» 으로 떨어지지 않음"""
        from battlesim.starsavior.foe import FoeDef
        raw = self.merged
        g = raw['g'][-1]
        self.assertEqual(g['k'], 'clash')
        n = lines = 0
        bad = []
        for t in g['tabs']:
            for st in t['s']:
                defs = [FoeDef(raw, e[0], e[1] if len(e) > 1 else None, st) for w in st['w'] for e in w]
                for _gid, _who, lst in st.get('sm', []):
                    defs += [FoeDef(raw, a, b, st) for a, b, _c in lst]
                for d in defs:
                    n += 1
                    lines += len(d.lines)
                    bad += [ln.raw for ln in d.lines if ln.eff['kind'] == 'ignored' and ln.eff.get('why') == '미해석']
        self.assertGreaterEqual(n, 18)
        self.assertGreater(lines, 100)
        # «자신에게 강인도 N 회복» 은 옛 데이터북 줄도 파서가 «미해석» 으로 읽는 기존 엔진 공백(rawdata/foe.js 에 같은 문법 88줄). 그 밖의 새 «미해석» 은 없어야 함
        self.assertTrue(bad)
        for raw_line in bad:
            self.assertRegex(raw_line, r'자신에게 강인도 \d+ 회복$')

    # ---------------------------------------------------------------- 2) 옛 판 재현
    def test_old_edition_reproduction_rate(self):
        c = self.cmp
        for k, v in RECORDED.items():
            self.assertGreaterEqual(c[k], v, '%s: %s < 기록값 %s' % (k, c[k], v))
        self.assertGreaterEqual(c['lines_exact'] / c['lines'], 0.99)
        self.assertGreaterEqual(c['skills_exact'] / c['skills'], 0.99)
        self.assertGreater(c['lines'], 100)           # 비교 대상이 실제로 있었는지(빈 비교로 통과 금지)
        self.assertGreater(c['cand_hit'] / c['cand_total'], 0.9)

    def test_new_lines_pinned(self):
        """새 판 대표 줄을 문자열로 못 박는다(변환기 문법이 바뀌면 여기서 걸림)"""
        efs = {(s['n'], i): l for s in self.frag['s'] for i, l in enumerate(s['ef'])}
        self.assertEqual(efs[('재충전', 0)], '[스킬 사용 후] 자신에게 〈저항 장막(해제불가)〉 (2턴 / 효과 저항 +100%) 보호막 = 자신 생명력×20% {해제 불가}')
        self.assertEqual(efs[('포착', 0)], '[스킬 사용 시작 시] (조건: 내 공격 시 [대상 약화효과 보유: 예]) 자신에게 능력치 보정 피해 증가 +30% {이번 스킬에만 적용}')
        self.assertIn('스킬 대상에게 〈속도 감소〉 (2턴 / 속도% -20%) {효과 적중 판정}', efs[('포착', 1)])
        self.assertEqual(efs[('재충전', 2)], '[스킬 사용 후] 자신에게 강인도 7 회복')
        self.assertEqual(efs[('한 맺힌 격앙', 0)], '[피해 처리 직전] (조건: 내가 피해를 받기 직전 [NotEnemyAdjustType: 별]) 자신에게 능력치 보정 피해 감소 +50% {이번 스킬에만 적용}')
        self.assertEqual(efs[('강압', 0)], '[스킬 사용 시작 시] (조건: 적 비공격 스킬 시) 자신에게 행동 게이지 50%p 증가')
        self.assertIn('{효과 적중 판정, 2회 부여}', efs[('침입자 청소', 1)])
        version = next(l for l in efs.values() if '〈버전 업그레이드(해제불가)〉' in l)
        self.assertIn('피해 감소 +5%', version)  # SE Stats=500, BuffDesc @@3 is display only.
        self.assertIn('최대 5중첩', version)

    def test_force_coop_converted_without_unmodeled(self):
        """퍼세스 강제 협공까지 변환됨. 빙결 조건(TargetPositiveBuff+BuffCountLess)은
        엔진 키 «대상 강화효과 개수 이하»로 변환돼 ef 에 있다(클라 NKM.Templets 42752·43328)"""
        all_ef = {l for s in self.frag['s'] for l in s['ef']}
        um = self.out['unmodeled']
        self.assertEqual(um, [])
        self.assertIn('[스킬 사용 후] (조건: 내 공격 후 [사용 스킬: 기본기]) 자신 제외 아군 1명(자동 지정)에게 〈강제 협공〉 (0턴)', all_ef)
        self.assertTrue(any('빙결' in l and '대상 강화효과 개수 이하: 1' in l for l in all_ef))
        self.assertFalse(any('빙결' in l and '대상 강화효과 보유' in l for l in all_ef))

    # ---------------------------------------------------------------- 3) 스탯: 표에서 독립 계산
    def indep_stats(self, unit_str, level, add):
        t = Path(STATIC) / 'tables'
        units = {r['m_UnitStrID']: r for n in (1, 2, 3, 4) for r in jsonc(t / ('UNIT_TEMPLET_BASE%d.json' % n))['Data']}
        stat = {r['m_StatStrID']: r for r in jsonc(t / 'UNIT_STAT_TEMPLET2.json')['Data']}
        per = {r['StatAddPerLevelStrID']: r['StatAddPerLevelData'] for r in jsonc(t / 'STAT_ADD_PER_LEVEL2.json')['Data']}
        sr = stat[units[unit_str]['m_StatStrID']]
        s, p = sr['m_StatData'], per[sr['m_StatAddPerLevelStrID']]
        rate = lambda k: 1 + add.get(k, 0) / 10000.0   # noqa: E731
        return dict(
            hp=int((s['NST_HP'] + p['NST_HP'] * (level - 1)) * rate('NST_NV_RATE_HP') + 1e-9),
            atk=int((s['NST_ATK'] + p['NST_ATK'] * (level - 1)) * rate('NST_NV_RATE_ATK') + 1e-9),
            **{'def': int((s['NST_DEF'] + p['NST_DEF'] * (level - 1)) * rate('NST_NV_RATE_DEF') + 1e-9)},
            spd=int(s['NST_TURN_SPEED'] * rate('NST_NV_RATE_TURN_SPEED') + 1e-9),
            cr=s['NST_RATE_CRITICAL'], cd=s['NST_RATE_CRITICAL_DAMAGE'], eh=s['NST_RATE_EFFECT_HIT'],
            er=s['NST_RATE_EFFECT_EVADE'], der=s['NST_RATE_DEFINITE_EFFECT_EVADE'], sa=s['NST_SUPER_ARMOR'])

    def test_stats_match_client_tables(self):
        from battlesim.starsavior.foe import FoeDef
        t = Path(STATIC) / 'tables'
        battle = {r['BattleID']: r for r in jsonc(t / 'BATTLE_TEMPLET_NORMAL.json')['Data'] if r.get('ContentsTag') == 'SS_EVENT_CLASH'}
        summon = {r['SummonGroupId']: r for r in jsonc(t / 'Plain' / 'SUMMON_TEMPLET.json')['Data']}
        g = self.merged['g'][-1]
        checked = summons = 0
        for ti, tab in enumerate(g['tabs']):
            for si, st in enumerate(tab['s']):
                brow = battle[22002001 + ti * 1000 + si]
                self.assertEqual(st['lv'], brow['BattleLevel'])
                script = jsonc(t / 'BattleScript' / brow['BattleTempletFileName'].replace('.txt', '.json'))['Data']
                spawn = script['Waves'][0]['TeamBSpawnList'][0]
                e = st['w'][0][0]
                d = FoeDef(self.merged, e[0], e[1] if len(e) > 1 else None, st)
                want = self.indep_stats(spawn['UnitStrId'], brow['BattleLevel'], spawn.get('AddStatData') or {})
                self.assertEqual(d.level, brow['BattleLevel'])
                self.assertEqual(d.stats, want, '%s %s' % (tab['t'], st['n']))
                checked += 1
                for gid, _who, lst in st.get('sm', []):
                    slots = summon[gid]['SummonData']
                    expanded = [(a, b) for a, b, c in lst for _ in range(c)]
                    self.assertEqual(len(expanded), len(slots))
                    for (a, b), sd in zip(expanded, slots):
                        sdef = FoeDef(self.merged, a, b, st)
                        self.assertEqual(sdef.stats, self.indep_stats(sd['UnitStrId'], brow['BattleLevel'], sd.get('AddStatData') or {}))
                        summons += 1
        self.assertEqual(checked, 18)
        self.assertEqual(summons, 12)

    def test_first_and_last_stage_hp_spot_values(self):
        """공식 b + gw×(L-1) 이 실제로 쓰이는지 손계산 하나: 모티베이터 1단계 HP = (64800+140×399)×(1-0.65)"""
        from battlesim.starsavior.foe import FoeDef
        st = self.merged['g'][-1]['tabs'][0]['s'][0]
        e = st['w'][0][0]
        d = FoeDef(self.merged, e[0], e[1], st)
        self.assertEqual(d.stats['hp'], int((64800 + 140 * 399) * 0.35 + 1e-9))
        self.assertEqual(d.stats['atk'], int((385 + 11 * 399) * 0.75 + 1e-9))
        self.assertEqual(d.stats['spd'], 143)

    # ---------------------------------------------------------------- 4) 스테이지 18개
    def test_stage_rows(self):
        g = self.frag['g'][0]
        self.assertEqual((g['k'], g['t']), ('clash', '격전 의뢰'))
        self.assertEqual([t['t'] for t in g['tabs']], ['폐쇄된 심상', '이형의 공세', '거짓된 계약'])
        total = 0
        for t in g['tabs']:
            self.assertEqual(len(t['s']), 6)
            for i, s in enumerate(t['s']):
                total += 1
                self.assertEqual(s['n'], '%s %s' % (t['t'], NUM[i]))
                self.assertEqual((s['lv'], s['bp']), (LV[i], BP[i]))
                self.assertEqual(len(s['w']), 1)
                self.assertEqual(len(s['w'][0]), 1)
        self.assertEqual(total, 18)
        for s in g['tabs'][2]['s']:
            self.assertEqual(len(s['sm']), 1)
        self.assertTrue(all('sm' not in s for t in g['tabs'][:2] for s in t['s']))

    def test_summon_group_ids(self):
        sm = [s['sm'][0][0] for s in self.frag['g'][0]['tabs'][2]['s']]
        self.assertEqual(sm, [1301, 1302, 1303, 1304, 1305, 1306])
        # 1303 은 슬롯 0·4 의 AddStatData 가 달라 항목이 둘로 갈려야 함
        self.assertEqual(len(self.frag['g'][0]['tabs'][2]['s'][2]['sm'][0][2]), 2)

    def test_committed_file_is_current(self):
        self.assertIsNotNone(self.doc, 'data/foe_clash.json 이 없음: python -X utf8 -I tools/build_foe_clash.py --static <표>')
        for k in ('u', 's', 'x', 'ak', 'g'):
            self.assertEqual(self.doc[k], json.loads(json.dumps(self.frag[k], ensure_ascii=False)), k)
        # 파일의 unmodeled 에는 빌더 main() 이 엔진 보고용 skill_name·units 를 덧붙이므로 그 둘은 빼고 비교
        strip = lambda rows: [{k: v for k, v in r.items() if k not in ('skill_name', 'units')} for r in rows]
        self.assertEqual(strip(self.doc['unmodeled']), json.loads(json.dumps(strip(self.out['unmodeled']), ensure_ascii=False)))
        self.assertTrue(all(r.get('skill_name') and r.get('units') for r in self.doc['unmodeled']))
        self.assertIn('조각 내부 0 기준', self.doc['_note'])


if __name__ == '__main__':
    unittest.main()
