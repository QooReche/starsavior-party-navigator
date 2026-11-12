# -*- coding: utf-8 -*-
"""격전 의뢰(SS_EVENT_CLASH, 11/12) 적 데이터 -> data/foe_clash.json.

데이터북(rawdata/foe.js)에 아직 없는 콘텐츠를 클라 표에서 직접 만든다. 출력은 foe.js 와 같은 모양의 «뒤에 덧붙이는 조각»:
  u(유닛) s(스킬) x(변형) ak(비어 있음: 필요한 NST 는 foe.js 의 ak 에 이미 있음) g(콘텐츠 그룹 1개)
  + 조각 밖 부가 항목: unmodeled(변환 못 한 SE 행과 원인), aux(소환 그룹·시작 쿨 표시), check(검증 기록)
조각 안 인덱스 규칙은 data/foe_clash.json 의 _note 에 있다(조각 내부 0 기준, 로더가 오프셋을 더함).

핵심 = 효과 줄 변환기 SeConverter: SE 행(SE_TEMPLET_SKILL_*) -> 데이터북 효과 줄 문법(battlesim/starsavior/parser.py 가 읽는 형식).
검증: 데이터북에 이미 있는 옛 판(모티베이터·웬디고·페르세스·고대 병졸)의 ef 줄을 옛 클라 SE 행으로 다시 만들어 비교한다(compare_old).
줄 모양(shape)이 데이터북 전체 ef 에 한 번도 나온 적 없는 줄은 «검증 못 한 문법» 으로 보고 ef 에 넣지 않고 unmodeled 에 남긴다
(--include-unverified 를 주면 넣는다).

사용: python -X utf8 -I tools/build_foe_clash.py [--static <비공개 저장소>] [--report <옛 판 비교 보고 파일>] [--include-unverified]
"""
import argparse
import json
import re
import sys
from collections import Counter, OrderedDict, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.tables import jsonc   # noqa: E402
from tools.runtime import static_path, low_priority   # noqa: E402

ROLE = {'NURT_STRIKER': '스트라이커', 'NURT_CASTER': '캐스터', 'NURT_ASSASSIN': '어쌔신', 'NURT_RANGER': '레인저',
        'NURT_DEFENDER': '디펜더', 'NURT_SUPPORTER': '서포터'}
ELEM = {'NUAT_SUN': '태양', 'NUAT_MOON': '달', 'NUAT_STAR': '별', 'NUAT_ORDER': '질서', 'NUAT_CHAOS': '혼돈'}
ATTACK_KIND = {'UAT_ELEMENT': '원소', 'UAT_IMPACT': '충격', 'UAT_SLASH': '참격'}
GRADE = {'NUG_BOSS': '보스', 'NUG_NORMAL': '일반'}
SLOT = {'ATTACK': '기본기', 'SPECIAL': '특수기', 'HYPER': '궁극기'}
TARGET_TG = {'NSTT_ENEMY_ONE': '적 단일', 'NSTT_ENEMY_ALL': '적 전체', 'NSTT_MYSELF': '자신', 'NSTT_INVALID': '-'}
SKILL_TY = {'NST_ACTIVE': '액티브', 'NST_PASSIVE': '패시브', 'NST_REACT': '트리거'}
PHASE = {'NSEAT_SKILL_START': '스킬 사용 시작 시', 'NSEAT_SKILL_END': '스킬 사용 후', 'NSEAT_DAMAGE_END': '피해 처리 후',
         'NSEAT_DAMAGE_START': '피해 처리 직전', 'NSEAT_DIE': '사망 시'}
TARGET_HEAD = {'NSETT_SELF': '자신', 'NSETT_TARGET': '스킬 대상', 'NSETT_ENEMY_ALL': '적 전체', 'NSETT_MYTEAM_ALL': '아군 전체',
               'NSETT_MYTEAM_ALL_NOT_SELF': '자신 제외 아군 전체'}
ALL_TARGETS = {'NSETT_ENEMY_ALL', 'NSETT_MYTEAM_ALL', 'NSETT_MYTEAM_ALL_NOT_SELF'}
# NST -> 데이터북 속성 이름(상태 효과 설명 괄호 안). 표에 없는 NST 는 변환 거절.
STAT_LABEL = {'NST_NV_RATE_ATK': '공격력%', 'NST_NV_RATE_DEF': '방어력%', 'NST_NV_RATE_HP': '생명력%', 'NST_NV_RATE_TURN_SPEED': '속도%',
              'NST_RATE_EFFECT_EVADE': '효과 저항', 'NST_RATE_EFFECT_HIT': '효과 적중', 'NST_RATE_DAMAGE_REDUCE': '피해 감소',
              'NST_RATE_HIT': '명중률', 'NST_RATE_CRITICAL': '치명타 확률', 'NST_RATE_DAMAGE_UP': '피해 증가',
              'NST_RATE_DAMAGE_REDUCE_SKILL_ENEMY_ONE': '단일 대상 피해 감소'}
# 이번 스킬 한정 «능력치 보정» 버프(BI_STAT_*) -> 라벨, 값 종류(RATE=만분율 %, VALUE=정수)
LOCAL_STAT = {'BI_STAT_NST_RATE_DAMAGE_UP': '피해 증가', 'BI_STAT_NST_RATE_DAMAGE_REDUCE': '피해 감소',
              'BI_STAT_NST_SUPER_ARMOR_DAMAGE': '강인도 피해',
              'BI_STAT_NST_RATE_DAMAGE_UP_ADJUST_MOON': 'vs 달 속성 피해 증가',
              'BI_STAT_NST_RATE_DAMAGE_UP_ADJUST_STAR': 'vs 별 속성 피해 증가',
              'BI_STAT_NST_RATE_DAMAGE_UP_ADJUST_SUN': 'vs 태양 속성 피해 증가'}
DOT_FIELDS = ('m_BleedingDTStrID', 'm_BurnDTStrID', 'm_PoisonDTStrID')


class Unconvertible(Exception):
    """이 SE 행은 데이터북 줄로 만들 수 없음(원인을 메시지에)."""


def fnum(v):
    v = round(v, 4)
    return str(int(v)) if v == int(v) else ('%g' % v)


def sgn(v):
    return ('+' if v >= 0 else '-') + fnum(abs(v))


# ---------------------------------------------------------------------------------------------- 표 읽기
class Tables:
    def __init__(self, static):
        t = Path(static) / 'tables'
        self.t = t
        self.strings = json.loads((t / 'Strings' / 'STRING_COMMON_ko_en.json').read_text(encoding='utf-8'))
        self.buff = {r['m_BuffStrID']: r for r in jsonc(t / 'BUFF_TEMPLET.json')['Data']}
        self.se = {}
        for n in (1, 2):
            for r in jsonc(t / ('SE_TEMPLET_SKILL_%d.json' % n))['Data']:
                self.se[r['m_SEStrID']] = r
        self.skill = {}
        for n in (1, 2):
            for r in jsonc(t / ('SKILL_TEMPLET_%d.json' % n))['Data']:
                self.skill[r['m_SkillStrID']] = r
        self.level = defaultdict(list)
        for n in (1, 2):
            for r in jsonc(t / ('SKILL_LEVEL_GROUP_TEMPLET_%d.json' % n))['Data']:
                self.level[r['SkillLevelGroupID']].append(r)
        self.cond = {r['Id']: r for r in jsonc(t / 'Plain' / 'SKILL_CONDITION_TEMPLET.json')['Data']}
        self.dt = {r['DTStrID']: r for r in jsonc(t / 'DAMAGE_TEMPLET.json')['Data']}
        self.auto_target = {r['Id']: r['TargetCondition'] for r in jsonc(t / 'Plain' / 'AUTO_SKILL_TARGET_TEMPLET.json')['Data']}
        self.summon = {r['SummonGroupId']: r for r in jsonc(t / 'Plain' / 'SUMMON_TEMPLET.json')['Data']}
        self.immune = defaultdict(list)
        for r in jsonc(t / 'BUFF_IMMUNE_TEMPLET.json')['Data']:
            self.immune[r['ImmuneGroupId']].append(r)
        self.units = {}
        for n in (1, 2, 3, 4):
            for r in jsonc(t / ('UNIT_TEMPLET_BASE%d.json' % n))['Data']:
                self.units[r['m_UnitStrID']] = r
        self.stat = {r['m_StatStrID']: r for r in jsonc(t / 'UNIT_STAT_TEMPLET2.json')['Data']}
        self.per_level = {r['StatAddPerLevelStrID']: r['StatAddPerLevelData'] for r in jsonc(t / 'STAT_ADD_PER_LEVEL2.json')['Data']}
        self.damage_scale = self._find_const('DamageScale') / 10000.0      # 18500 -> 1.85

    def _find_const(self, key):
        d = jsonc(self.t / 'Plain' / 'CLIENT_CONST_TEMPLET.json')

        def walk(x):
            if isinstance(x, dict):
                if key in x:
                    return x[key]
                for v in x.values():
                    r = walk(v)
                    if r is not None:
                        return r
            elif isinstance(x, list):
                for v in x:
                    r = walk(v)
                    if r is not None:
                        return r
            return None
        r = walk(d)
        if r is None:
            raise KeyError(key)
        return r

    def ko(self, key):
        """문자열 키 -> 한국어. '키@@인자' 형태면 {0} 자리에 인자를 넣는다."""
        if not key:
            return None
        arg = None
        if '@@' in key:
            key, arg = key.split('@@', 1)
        s = (self.strings.get(key) or {}).get('ko')
        if s is None:
            return None
        if arg is not None:
            s = s.replace('{0}', arg)
        return s

    def buff_name(self, bid):
        b = self.buff.get(bid)
        return self.ko(b.get('m_BuffName')) if b else None


def clean_markup(s):
    """<b><color=#..>X</color></b> -> [X]"""
    if s is None:
        return None
    s = re.sub(r'<b><color=#[0-9A-Fa-f]+>(.*?)</color></b>', r'[\1]', s)
    s = re.sub(r'<[^>]+>', '', s)
    return s


# ---------------------------------------------------------------------------------------------- SE 행 -> 효과 줄
class SeConverter:
    def __init__(self, tb):
        self.tb = tb

    # ---- 조건(SkillConditionId) -> «(조건: ...)» 안쪽 문구
    def cond_text(self, cid, phase_type):
        tb = self.tb
        row = tb.cond.get(cid)
        if row is None:
            raise Unconvertible('조건 %s 가 SKILL_CONDITION_TEMPLET 에 없음' % cid)
        keys = [k for k in row if k != 'Id']
        if len(keys) != 1:
            raise Unconvertible('조건 %s 형식(키 %s)' % (cid, keys))
        head, body = keys[0], dict(row[keys[0]])
        heads = {'OnMyAttack': '내 공격 시', 'AfterMyAttack': '내 공격 후', 'MyEffectiveHit': '내가 피격될 때',
                 'MyEffectiveDamageStart': '내가 피해를 받기 직전', 'MyEffectiveDie': '내가 사망할 때',
                 'OnEnemyNonAttack': '적 비공격 스킬 시'}
        if head not in heads:
            raise Unconvertible('조건 %s 머리 %s 미지원' % (cid, head))
        # 발동 시점과 머리가 어긋나는지(예: DAMAGE_END 인데 OnMyAttack)는 데이터북도 시점 단어로 구분하지 않으므로 그대로 둠
        title = heads[head]
        if head == 'OnEnemyNonAttack' and phase_type == 'NSEAT_SKILL_END':
            title = '적 비공격 스킬 후'
        parts = []
        self.cond_buffs = []
        if 'SkillIndex' in body:
            si = {'NSI_SKILL_1_ATTACK': '기본기', 'NSI_SKILL_2_SPECIAL': '특수기', 'NSI_SKILL_3_HYPER': '궁극기'}.get(body.pop('SkillIndex'))
            if si is None:
                raise Unconvertible('조건 %s SkillIndex 미지원' % cid)
            parts.append('사용 스킬: ' + si)
        if 'SelfBuffStrId' in body:
            names = []
            for b in body.pop('SelfBuffStrId'):
                n = tb.buff_name(b)
                if n is None:
                    continue          # 이름 문자열이 없는 버프 id 는 데이터북 줄에도 안 나옴
                if n not in names:
                    names.append(n)
                    self.cond_buffs.append(b)
            if not names:
                raise Unconvertible('조건 %s 버프 이름 없음' % cid)
            parts.append('자신이 보유: ' + ', '.join(names))
            if 'SelfBuffLevelCount' in body:
                parts.append('중첩수: %d' % body.pop('SelfBuffLevelCount'))
        if body.get('TargetPositiveBuff') is True and 'BuffCountLess' in body:
            # 클라: 대상의 강화 효과 수를 세어 «≤ N»(0개 포함)로 판정(NKM.Templets 42752 `TargetPositiveBuff && !CountOk(n)`, 43328 `N>0 && N<count → 거짓`).
            # «대상 강화효과 보유: 예»(≥1) 와 합치면 0개가 빠지므로 엔진 전용 키 «대상 강화효과 개수 이하»(mc.line_ok)를 쓴다.
            body.pop('TargetPositiveBuff')
            parts.append('대상 강화효과 개수 이하: %d' % body.pop('BuffCountLess'))
        for key, label in (('TargetNegativeBuff', '대상 약화효과 보유'), ('TargetPositiveBuff', '대상 강화효과 보유'),
                           ('EnemyPositiveBuff', '적 강화효과 보유'), ('EnemyNegativeBuff', '적 약화효과 보유')):
            if body.get(key) is True:
                body.pop(key)
                parts.append(label + ': 예')
        if 'TargetSuperArmorBreak' in body:
            if body.pop('TargetSuperArmorBreak') is not True:
                raise Unconvertible('조건 %s TargetSuperArmorBreak=false' % cid)
            parts.append('대상 브레이크: 예')
        if 'BuffCountLess' in body:
            parts.append('효과 개수 이하: %d' % body.pop('BuffCountLess'))
        for key, label in (('EnemyAdjustType', 'EnemyAdjustType'), ('NotEnemyAdjustType', 'NotEnemyAdjustType')):
            if key in body:
                v = ELEM.get(body.pop(key))
                if v is None:
                    raise Unconvertible('조건 %s 속성 값' % cid)
                parts.append('%s: %s' % (label, v))
        if body:
            raise Unconvertible('조건 %s 미해석 키 %s' % (cid, sorted(body)))
        return title + (' [%s]' % '; '.join(parts) if parts else '')

    # ---- 대상 머리말
    def target_head(self, row):
        tt = row.get('m_BuffTargetType')
        if tt in TARGET_HEAD:
            return TARGET_HEAD[tt]
        if tt in ('NSETT_AUTO_ALLY_ONE', 'NSETT_AUTO_ALLY_ONE_NOT_SELF', 'NSETT_AUTO_ENEMY_ONE', 'NSETT_AUTO_ENEMY', 'NSETT_AUTO_ALLY'):
            cond = self.tb.auto_target.get(row.get('AutoTargetId'))
            if cond is None:
                raise Unconvertible('자동 대상 %s 의 조건 행 없음(AutoTargetId=%s)' % (tt, row.get('AutoTargetId')))
            c = dict(cond)
            if (tt == 'NSETT_AUTO_ALLY_ONE_NOT_SELF' and c == {
                    'IsNotUnableToAct': True, 'IsNotSpecificBuff': ['BI_DISABLE_CROSS_ATTACK'], 'IsHighAtk': True}):
                # AutoTargetId 52: NKM:7149-7152,7535-7536,7572-7574,7754-7755,7901-7912.
                # 우선 필터의 실패/동률 처리는 foe_auto 규칙으로 보존한다.
                return '자신 제외 아군 1명(자동 지정)'
            if tt == 'NSETT_AUTO_ENEMY' and len(c) == 1:
                # 데이터북: «강화 효과가 2개 이상인 적 전체에게» / «강화 효과가 1개 이하인 적 전체에게» (옛 웬디고 궁극기 AutoTargetId 1005·1006)
                if 'IsPositiveBuffCountOverThan' in c:
                    return '강화 효과가 %d개 이상인 적 전체' % c['IsPositiveBuffCountOverThan']
                if 'IsPositiveBuffCountLessThan' in c:
                    return '강화 효과가 %d개 이하인 적 전체' % c['IsPositiveBuffCountLessThan']
            notself = c.pop('IsAllyOneNotSelf', False)
            atk = c.pop('IsHighAtk', False)
            if c or not atk or tt not in ('NSETT_AUTO_ALLY_ONE', 'NSETT_AUTO_ALLY_ONE_NOT_SELF'):
                raise Unconvertible('자동 대상 조건 %s 문구 미정(AutoTargetId=%s)' % (cond, row.get('AutoTargetId')))
            return ('공격력이 가장 높은 다른 아군 1명' if notself else '공격력이 가장 높은 아군 1명')
        raise Unconvertible('대상 종류 %s' % tt)

    # ---- 확률
    def chance(self, row):
        a = row.get('m_fBuffActiveRate')
        b = (row.get('m_Condition') or {}).get('m_fActiveRate')
        if a is not None and b is not None and a != b:
            raise Unconvertible('m_fBuffActiveRate(%s) 와 m_Condition.m_fActiveRate(%s) 가 다름' % (a, b))
        v = a if a is not None else b
        return 100.0 if v is None else v / 100.0

    def chance_prefix(self, row):
        c = self.chance(row)
        if c >= 100:
            return ''
        n = fnum(c)
        return '(대상마다 %s%% 판정) ' % n if row.get('m_BuffTargetType') in ALL_TARGETS else '%s%% 확률로 ' % n

    # ---- 속성/지속
    def stats_of(self, row):
        """SE 행 Stats(있으면) 우선, 없으면 BUFF_TEMPLET Stats -> [(NST, 종류 'RATE'|'VALUE', 값)]"""
        buff = self.tb.buff[row['m_BuffStrID']]
        se_stats = row.get('Stats')
        base = buff.get('Stats') or []
        out = []
        for i, bs in enumerate(base if base else (se_stats or [])):
            nst = bs.get('NKM_STAT_TYPE')
            ov = se_stats[i] if (se_stats and i < len(se_stats) and base) else None
            src = ov if ov is not None else bs
            if 'NKM_STAT_TYPE_RATE' in src:
                out.append((nst, 'RATE', src['NKM_STAT_TYPE_RATE']))
            elif 'NKM_STAT_TYPE_VALUE' in src:
                out.append((nst, 'VALUE', src['NKM_STAT_TYPE_VALUE']))
            else:
                raise Unconvertible('Stats 값 키 없음 %s' % src)
        if se_stats and base and len(se_stats) != len(base):
            raise Unconvertible('SE Stats 개수(%d) 와 버프 Stats 개수(%d) 가 다름' % (len(se_stats), len(base)))
        return out

    def props_text(self, stats):
        parts = []
        for nst, kind, v in stats:
            lab = STAT_LABEL.get(nst)
            if lab is None:
                raise Unconvertible('속성 %s 의 데이터북 이름을 모름' % nst)
            parts.append('%s %s%%' % (lab, sgn(v / 100.0)) if kind == 'RATE' else '%s %s' % (lab, sgn(v)))
        return ', '.join(parts)

    def dot_text(self, buff):
        for f in DOT_FIELDS:
            if buff.get(f):
                dt = self.tb.dt.get(buff[f])
                if dt is None:
                    raise Unconvertible('DT %s 없음' % buff[f])
                if f != 'm_BleedingDTStrID' and buff['m_BuffStrID'] != 'BI_FREEZING':
                    raise Unconvertible('지속 피해 종류 %s 문구 미확인' % f)
                if dt.get('AtkFactor') and not dt.get('HpFactor') and not dt.get('DefFactor'):
                    return '턴마다 공격력×%s%% ×%s 피해(방어력 적용)' % (fnum(dt['AtkFactor'] / 100.0), fnum(self.tb.damage_scale))
                raise Unconvertible('DT %s 형식 %s' % (buff[f], dt))
        return None

    def desc_pair(self, row, buff):
        """(설명문, {0} 템플릿 또는 None). BuffDesc 인자(@@) > SE Stats 값 순으로 {0} 을 채움."""
        tb = self.tb
        key = row.get('BuffDesc') or buff.get('m_BuffDesc')
        raw = tb.strings.get(key.split('@@')[0], {}).get('ko') if key else None
        if raw is None:
            return None, None
        if '{0}' not in raw:
            return clean_markup(raw), None
        arg = key.split('@@', 1)[1] if '@@' in key else None
        if arg is None:
            st = self.stats_of(row) if (buff.get('Stats') or row.get('Stats')) else []
            if st and st[0][1] == 'RATE':
                arg = fnum(abs(st[0][2]) / 100.0)
        if arg is None:
            return clean_markup(raw), raw
        return clean_markup(raw.replace('{0}', arg)), clean_markup(raw)

    # ---- 본체
    def convert(self, se_id):
        it = self._convert(se_id)
        it['cond_buffs'] = list(self.cond_buffs)
        return it

    def base_gl(self, bid):
        """조건에서만 언급된 버프의 상태 설명(데이터북 방식): 버프 정의의 속성만(지속·해제 불가·중첩 표기 없음)."""
        tb = self.tb
        buff = tb.buff[bid]
        stats = self.stats_of({'m_BuffStrID': bid})
        d, d0 = self.desc_pair({'m_BuffStrID': bid}, buff)
        gl = dict(n=tb.buff_name(bid), k='강화' if buff.get('IsPositive') else '약화', d=d, x=self.props_text(stats))
        if d0:
            gl['d0'] = d0
        return gl

    def _convert(self, se_id):
        """-> dict(line=..., gl=[버프 설명 항목 or None], kind=..., key=(중복 접기용 키))"""
        tb = self.tb
        row = tb.se.get(se_id)
        if row is None:
            raise Unconvertible('SE 행 %s 없음' % se_id)
        cond = row.get('m_Condition') or {}
        at = cond.get('m_ActiveType')
        if at not in PHASE:
            raise Unconvertible('발동 시점 %s 미지원' % at)
        head = '[%s]' % PHASE[at]
        self.cond_buffs = []
        if row.get('SkillConditionId'):
            head += ' (조건: %s)' % self.cond_text(row['SkillConditionId'], at)
        bid = row.get('m_BuffStrID')
        buff = tb.buff.get(bid)
        if buff is None:
            raise Unconvertible('BUFF_TEMPLET 에 %s 없음' % bid)
        gl = None
        flags = []
        # ----- 종류별 본문
        if bid == 'BI_SUMMON':
            grp = tb.summon.get(row.get('SummonGroupId'))
            if not grp:
                raise Unconvertible('SUMMON_TEMPLET 그룹 %s 없음' % row.get('SummonGroupId'))
            units = {sd['UnitStrId'] for sd in grp['SummonData']}
            if len(units) != 1:
                raise Unconvertible('소환 그룹 %s 에 유닛 종류가 여럿' % row['SummonGroupId'])
            u = tb.units[units.pop()]
            body = '자신에게 소환: %s ×%d' % (tb.ko(u['m_UnitNameString']), len(grp['SummonData']))
            return dict(line=head + ' ' + body, gl=None, collapse='mul', kind='summon', se=se_id)
        if bid in LOCAL_STAT:
            st = (row.get('Stats') or [None])[0]
            if not st or len(row['Stats']) != 1:
                raise Unconvertible('능력치 보정 Stats 형식')
            if row.get('m_BuffTargetType') != 'NSETT_SELF':
                raise Unconvertible('능력치 보정 대상 %s' % row.get('m_BuffTargetType'))
            if 'NKM_STAT_TYPE_RATE' in st:
                val = '%s%%' % sgn(st['NKM_STAT_TYPE_RATE'] / 100.0)
            else:
                val = sgn(st['NKM_STAT_TYPE_VALUE'])
            return dict(line='%s 자신에게 능력치 보정 %s %s {이번 스킬에만 적용}' % (head, LOCAL_STAT[bid], val), gl=None, collapse='none', kind='local', se=se_id)
        th = self.target_head(row)
        who = th + '에게'
        if buff.get('SuperArmorUp'):
            if row.get('m_BuffTargetType') != 'NSETT_SELF' or 'SuperArmorUpValue' not in row:
                raise Unconvertible('강인도 회복 형식')
            return dict(line='%s 자신에게 강인도 %d 회복' % (head, row['SuperArmorUpValue']), gl=None, collapse='none', kind='armor', se=se_id)
        if buff.get('SpeedGaugeUp') or buff.get('SpeedGaugeDown'):
            if 'SpeedGaugeRate' not in row:
                raise Unconvertible('행동 게이지 값(SpeedGaugeRate) 없음')
            up = bool(buff.get('SpeedGaugeUp'))
            ch = self.chance_prefix(row)
            fl = ' {효과 적중 판정}' if buff.get('EffectHitCheck') else ''
            return dict(line='%s %s %s행동 게이지 %s%%p %s%s' % (head, who, ch, fnum(row['SpeedGaugeRate'] / 100.0), '증가' if up else '감소', fl),
                        gl=None, collapse='none', kind='gauge', se=se_id)
        if buff.get('SkillCoolturnDown'):
            slot = {'NSI_SKILL_3_HYPER': '궁극기', 'NSI_SKILL_2_SPECIAL': '특수기', 'NSI_SKILL_1_ATTACK': '기본기'}.get(buff.get('SkillCoolturnType'))
            if slot is None or 'SkillCoolturnDownValue' not in row:
                raise Unconvertible('쿨타임 감소 형식')
            return dict(line='%s %s %s 쿨타임 %d턴 감소' % (head, who, slot, row['SkillCoolturnDownValue']), gl=None, collapse='none', kind='cdr', se=se_id)
        if buff.get('DeleteBuff') or buff.get('DeleteDebuff'):
            n = row.get('BuffDeleteCount', 1)
            what = '(강화효과 해제)' if buff.get('DeleteBuff') else '(약화효과 해제)'
            ch = self.chance_prefix(row)
            fl = ' {효과 적중 판정}' if buff.get('EffectHitCheck') else ''
            return dict(line='%s %s %s%s 효과 %d개 해제%s' % (head, who, ch, what, n, fl), gl=None, collapse='mul', kind='delete', se=se_id)
        if buff.get('DeleteSpecificBuff'):
            tgt = row.get('DeleteSpecificBuffStrId')
            nm = tb.buff_name(tgt) if tgt else None
            if not nm:
                raise Unconvertible('해제할 버프 이름을 못 읽음(DeleteSpecificBuffStrId=%s)' % tgt)
            return dict(line="%s %s '%s' 해제" % (head, who, nm), gl=None, collapse='none', kind='remove', se=se_id)
        if buff.get('AddDamage'):
            if row.get('AddDamageStatType') != 'NST_ATK' or row.get('AddDamageTargetType') != 'NSETT_SELF' or 'AddDamageRate' not in row:
                raise Unconvertible('추가 피해 형식')
            return dict(line='%s %s 연쇄 피해 = 자신 공격력×%s%% (×%s, 방어력 적용)' % (head, who, fnum(row['AddDamageRate'] / 100.0), fnum(tb.damage_scale)),
                        gl=None, collapse='none', kind='chain', se=se_id)
        if buff.get('ForceCrossAttack'):
            return dict(line='%s %s %s〈강제 협공〉 (0턴)' % (head, who, self.chance_prefix(row)),
                        gl=None, collapse='none', kind='forced_coop', se=se_id)
        # ----- 일반 상태 효과(버프/디버프)
        name = tb.buff_name(bid)
        if not name:
            raise Unconvertible('버프 %s 이름 문자열 없음' % bid)
        stats = self.stats_of(row)
        life = 'TurnInfinite' in buff and buff.get('TurnInfinite')
        dur = '지속 무한' if life else '%d턴' % row['m_BuffLifeTurn']
        if not life and row['m_BuffLifeTurn'] <= 0:
            raise Unconvertible('버프 %s 지속 턴 0' % bid)
        props = self.props_text(stats) if stats else ''
        dot = self.dot_text(buff)
        paren = ' / '.join(x for x in (dur, props) if x)
        barrier = ''
        if buff.get('Barrier'):
            if row.get('BarrierStatType') != 'NST_HP' or row.get('BarrierTargetType') != 'NSETT_SELF' or 'BarrierRate' not in row:
                raise Unconvertible('보호막 크기 형식')
            barrier = ' 보호막 = 자신 생명력×%s%%' % fnum(row['BarrierRate'] / 100.0)
        if buff.get('CanNotDispel'):
            flags.append('해제 불가')
        if buff.get('IsLevel'):
            if not buff.get('BuffLevelMax'):
                raise Unconvertible('버프 %s IsLevel 인데 BuffLevelMax 없음' % bid)
            flags.append('최대 %d중첩' % buff['BuffLevelMax'])
        if buff.get('EffectHitCheck'):
            flags.insert(0, '효과 적중 판정')
        line = '%s %s %s〈%s〉 (%s)%s%s%s' % (head, who, self.chance_prefix(row), name, paren, barrier,
                                              (' ‹%s›' % dot) if dot else '', (' {%s}' % ', '.join(flags)) if flags else '')
        d, d0 = self.desc_pair(row, buff)
        x_parts = []
        if life:
            x_parts.append('지속 무한')
        else:
            x_parts.append('%d턴' % row['m_BuffLifeTurn'])
        if props:
            x_parts.insert(0, props)
        if dot:
            x_parts.append(dot)
        if buff.get('IsLevel'):
            x_parts.append('최대 %d중첩' % buff['BuffLevelMax'])
        if buff.get('CanNotDispel'):
            x_parts.append('해제 불가')
        # 데이터북 x 는 «속성 / 지속 / 최대 중첩 / 해제 불가», 속성이 없으면 «지속 / 지속 피해»
        if props:
            xs = ' / '.join([props] + [p for p in x_parts if p != props])
        else:
            xs = ' / '.join(x_parts)
        # 데이터북 gl(상태 효과 설명)은 게임 UI 에 아이콘이 뜨는 효과(BUFF_TEMPLET.m_bShowBuffInfo)만 가진다(옛 판 비교로 확인)
        gl = None
        if buff.get('m_bShowBuffInfo'):
            gl = dict(n=name, k='강화' if buff.get('IsPositive') else '약화', d=d, x=xs)
            if d0:
                gl['d0'] = d0
        return dict(line=line.replace('〉  (', '〉 ('), gl=gl, collapse='buff', kind='buff', se=se_id)


def collapse_lines(items):
    """연속된 같은 줄 N개 -> 한 줄 + N회 표기(데이터북 문법: 버프는 «{..., N회 부여}», 해제·소환은 « ×N»)."""
    out = []
    for it in items:
        if out and out[-1]['line'] == it['line'] and it['collapse'] in ('buff', 'mul'):
            out[-1]['n'] += 1
            continue
        out.append(dict(it, n=1))
    res = []
    for it in out:
        line, n = it['line'], it['n']
        if n > 1:
            if it['collapse'] == 'buff':
                if line.endswith('}'):
                    line = line[:-1] + ', %d회 부여}' % n
                else:
                    line += ' {%d회 부여}' % n
            else:
                line += ' ×%d' % n
        res.append(dict(it, line=line))
    return res


# ---------------------------------------------------------------------------------------------- 줄 모양(shape) 검증
def _mask(s):
    if s is None:
        return None
    s = re.sub(r'〈[^〉]*〉', '〈*〉', s)
    s = re.sub(r"'[^']*'", "'*'", s)
    s = re.sub(r'(자신이 보유|적 강화효과 보유|자신 약화효과 보유): [^;\]]*', r'\1: *', s)
    s = re.sub(r'소환: .+? ×', '소환: * ×', s)
    s = re.sub(r'vs \S+ 속성', 'vs * 속성', s)
    s = re.sub(r'(EnemyAdjustType|NotEnemyAdjustType): [^;\]]*', r'\1: *', s)
    s = re.sub(r'\((\d+턴|지속 무한)( / [^)]*)?\)', lambda m: '(%s%s)' % ('T' if m.group(1) != '지속 무한' else '∞', ' / P' if m.group(2) else ''), s)
    return re.sub(r'\d+(?:\.\d+)?', '#', s)


def line_parts(line):
    """효과 줄 -> (시점, 조건, 대상 머리, 본문, 플래그 목록). 각각 숫자·이름을 가린 «문법 모양»."""
    m = re.match(r'^\[([^\]]+)\]\s*(.*)$', line, re.S)
    phase, rest = m.group(1), m.group(2)
    cond = None
    if rest.startswith('(조건:'):
        depth = 0
        for i, ch in enumerate(rest):
            depth += (ch == '(') - (ch == ')')
            if depth == 0:
                cond, rest = rest[len('(조건:'):i].strip(), rest[i + 1:].strip()
                break
    flags = []
    fm = re.search(r'\s*\{([^{}]*)\}((?: ×\d+)?)$', rest)
    if fm:
        flags = [f.strip() for f in fm.group(1).split(',')]
        rest = rest[:fm.start()] + fm.group(2)
    rest = re.sub(r' ×\d+$', ' ×#', rest)
    head, body = (rest.split('에게 ', 1) + [''])[:2] if '에게 ' in rest else (None, rest)
    head = re.sub(r'^(?:\(대상마다 \d+% 판정\)\s*)', '', head) if head else head
    return _mask(phase), _mask(cond), _mask(head), _mask(body), [_mask(f) for f in flags]


def db_shapes(raw):
    """데이터북 ef 전체에서 모은 문법 요소 집합(시점·조건·머리·본문·플래그 항목)."""
    sets = [set() for _ in range(5)]
    for s in raw['s']:
        for l in s.get('ef') or []:
            p = line_parts(l)
            for i in range(4):
                sets[i].add(p[i])
            sets[4].update(p[4])
    return sets


def unverified_parts(line, shapes):
    """줄의 문법 요소 중 데이터북에 한 번도 나오지 않은 것의 목록(비면 검증됨)."""
    p = line_parts(line)
    bad = []
    engine_cond = p[1] is not None and re.fullmatch(r'내 공격 후 \[대상 강화효과 개수 이하: #\]', p[1]) is not None
    # 기존 구원자 파서·forced_coop 경로가 읽는 즉시 플래그. 신규 적 줄은 전용 시험으로 검사.
    engine_coop = line == ('[스킬 사용 후] (조건: 내 공격 후 [사용 스킬: 기본기]) '
                           '자신 제외 아군 1명(자동 지정)에게 〈강제 협공〉 (0턴)')
    # 위 조건은 엔진 전용 키(mc.line_ok)라 데이터북에 없어도 클라 코드(NKM.Templets 42752·43328)로 의미가 확인된 문법으로 본다
    for i, label in enumerate(('시점', '조건', '대상 머리', '본문')):
        if i == 1 and engine_cond:
            continue
        if engine_coop and i in (2, 3):
            continue
        if p[i] is not None and p[i] not in shapes[i]:
            bad.append('%s: %s' % (label, p[i]))
    for f in p[4]:
        if f not in shapes[4]:
            bad.append('플래그: %s' % f)
    return bad


# ---------------------------------------------------------------------------------------------- 스킬 변환
class SkillBuilder:
    def __init__(self, tb, conv, shapes, include_unverified=False):
        self.tb, self.conv, self.shapes, self.inc = tb, conv, shapes, include_unverified
        self.unmodeled = []

    def level_row(self, skill):
        lv = self.tb.level.get(skill['SkillLevelGroup'])
        if not lv:
            raise KeyError('SKILL_LEVEL_GROUP 없음 ' + skill['m_SkillStrID'])
        return sorted(lv, key=lambda r: r['SkillLevelValue'])

    def ef_for(self, skill_id, owner=None, record=True, level_index=0):
        """스킬 id -> (ef 줄 목록, gl 목록, SE 개수). 변환 못 한 행·검증 못 한 줄은 unmodeled 에 기록."""
        tb = self.tb
        sk = tb.skill[skill_id]
        lv = self.level_row(sk)[level_index]
        items = []
        for sid in lv.get('SkillLevelSE') or []:
            try:
                it = self.conv.convert(sid)
            except Unconvertible as ex:
                if record:
                    self.unmodeled.append(dict(skill=owner or skill_id, se=sid, reason=str(ex), kind='변환 불가'))
                continue
            items.append(it)
        items = collapse_lines(items)
        ef = []
        for it in items:
            bad = unverified_parts(it['line'], self.shapes)
            if bad and not self.inc:
                if record:
                    self.unmodeled.append(dict(skill=owner or skill_id, se=it['se'], kind='문법 미검증', candidate=it['line'],
                                               reason='데이터북 ef 에 한 번도 나온 적 없는 문법 요소 → ' + ' | '.join(bad)))
                continue
            ef.append(it['line'])
        # 상태 설명(gl): 데이터북은 스킬 설명 d1 에 [대괄호]로 나온 상태 효과마다 한 항목을 둔다(옛 판 비교로 확인, d1 등장 순서).
        # 이 스킬이 직접 거는 효과는 이 스킬 SE 값, 조건에서만 언급된 효과는 같은 유닛의 다른 스킬이 거는 설명, 그것도 없으면 버프 정의의 속성만.
        applied = OrderedDict()
        cond_ref = OrderedDict()
        for it in items:
            if it['gl']:
                applied.setdefault(it['gl']['n'], it['gl'])
            for bid in it.get('cond_buffs') or []:
                nm = self.tb.buff_name(bid)
                if nm:
                    cond_ref.setdefault(nm, bid)
        d1 = clean_markup(self.tb.ko(lv['SkillLevelDesc'])) or ''
        gl, sib = [], None
        for nm in OrderedDict.fromkeys(re.findall(r'\[([^\]]+)\]', d1)):
            if nm in applied:
                gl.append(applied[nm])
            elif nm in cond_ref:
                b = self.tb.buff.get(cond_ref[nm])
                if not (b and b.get('m_bShowBuffInfo')):
                    continue
                if sib is None:
                    sib = self.sibling_gl(skill_id)
                try:
                    gl.append(sib.get(nm) or self.conv.base_gl(cond_ref[nm]))
                except Unconvertible:
                    continue
        return ef, gl, len(lv.get('SkillLevelSE') or []), lv

    def sibling_gl(self, skill_id):
        """같은 유닛(이 스킬을 가진 첫 유닛)의 다른 스킬이 직접 거는 상태 설명 {이름: gl}"""
        if not hasattr(self, '_owner'):
            self._owner = {}
            for u in sorted(self.tb.units.values(), key=lambda r: r['m_UnitID']):
                for sid in u.get('m_listSkill') or []:
                    self._owner.setdefault(sid, u)
        u = self._owner.get(skill_id)
        out = {}
        for sid in (u.get('m_listSkill') if u else []) or []:
            if sid == skill_id or sid not in self.tb.skill:
                continue
            for lvr in self.level_row(self.tb.skill[sid])[:1]:
                for se_id in lvr.get('SkillLevelSE') or []:
                    try:
                        it = self.conv.convert(se_id)
                    except Unconvertible:
                        continue
                    if it['gl'] and it['gl']['n'] not in out:
                        out[it['gl']['n']] = it['gl']
        return out


# ---------------------------------------------------------------------------------------------- 옛 판 재현 비교
FAMILY_KEYS = {'모티베이터': 'MOTIVATOR_HANDS', '웬디고': 'WENDIGO', '페르세스': 'PERSES_SWORD', '고대 병졸': 'ARCHON_SPEAR'}
NEW_MARK = ('GOLD_BOSS', 'ARMOR_BLACK', 'VIOLET')


def compare_old(tb, raw, conv, shapes):
    """데이터북(foe.js)의 옛 판 ef <-> 옛 클라 SE 행 변환 결과. 반환: 보고용 dict."""
    sb = SkillBuilder(tb, conv, shapes, include_unverified=True)    # 비교에서는 모든 줄 포함
    # 데이터북 쪽: (유닛 이름, 스킬 이름) -> {ef 튜플: 등장 횟수}
    dbv = defaultdict(Counter)
    db_gl = defaultdict(dict)
    for u in raw['u']:
        if u['n'] not in FAMILY_KEYS:
            continue
        for si in u['sk']:
            s = raw['s'][si]
            if s['sl'] == '패시브' or s['sl'] in ('기본기', '특수기', '궁극기'):
                dbv[(u['n'], s['n'])][tuple(s.get('ef') or [])] += 1
                db_gl[(u['n'], s['n'], tuple(s.get('ef') or []))] = {g['n']: g for g in (s.get('gl') or []) if g.get('k') != '스킬'}
    # 클라 쪽 후보: 가족 키를 가진 옛 스킬(새 11/12 판 제외)
    cands = defaultdict(list)       # (유닛 이름, 스킬 한국어 이름) -> [(skill_id, ef, gl)]
    for sid, sk in tb.skill.items():
        if any(m in sid for m in NEW_MARK):
            continue
        fam = next((n for n, k in FAMILY_KEYS.items() if k in sid), None)
        if fam is None:
            continue
        nm = tb.ko(sk.get('m_SkillName'))
        if not nm or not tb.level.get(sk.get('SkillLevelGroup')):
            continue
        ef, gl, _n, _lv = sb.ef_for(sid, record=False)
        cands[(fam, nm)].append((sid, ef, gl))
    rows = []
    tot_lines = tot_exact = tot_skill = tot_skill_exact = 0
    mismatch = []
    gl_bad = []
    gl_tot = gl_exact = gl_lists = gl_lists_exact = 0
    for key, variants in sorted(dbv.items()):
        for ef_db, cnt in variants.items():
            best = None
            for sid, ef_cl, gl_cl in cands.get(key, []):
                m = sum(1 for a, b in zip(ef_db, ef_cl) if a == b)
                score = (m == len(ef_db) == len(ef_cl), m, -abs(len(ef_cl) - len(ef_db)))
                if best is None or score > best[0]:
                    best = (score, sid, ef_cl, gl_cl, m)
            n = len(ef_db)
            tot_lines += n
            tot_skill += 1
            if best is None:
                mismatch.append(dict(unit=key[0], skill=key[1], db=list(ef_db), client=None, reason='클라 후보 스킬 없음'))
                continue
            _score, sid, ef_cl, gl_cl, m = best
            tot_exact += m
            if m == n == len(ef_cl):
                tot_skill_exact += 1
            else:
                mismatch.append(dict(unit=key[0], skill=key[1], client_skill=sid, db=list(ef_db), client=ef_cl))
            # gl 비교: 항목 값(k·d·x)과 항목 순서·과잉 항목까지
            dg = db_gl[(key[0], key[1], ef_db)]
            cg = {g['n']: g for g in gl_cl}
            for gname, g in dg.items():
                gl_tot += 1
                c = cg.get(gname)
                if c and all(c.get(f) == g.get(f) for f in ('k', 'd', 'x')):
                    gl_exact += 1
                else:
                    gl_bad.append(dict(unit=key[0], skill=key[1], client_skill=sid, name=gname,
                                       db={f: g.get(f) for f in ('k', 'd', 'x')}, client=({f: c.get(f) for f in ('k', 'd', 'x')} if c else None)))
            extra = [n for n in cg if n not in dg]
            if extra:
                gl_bad.append(dict(unit=key[0], skill=key[1], client_skill=sid, name=extra, db='(없음)', client='과잉 항목'))
            if list(dg) == [g['n'] for g in gl_cl]:
                gl_lists_exact += 1
            gl_lists += 1
    # 역방향: 옛 클라 스킬 후보 중 데이터북에 같은 줄 묶음이 있는 비율(후보 고르기에 기대지 않은 지표)
    cand_total = cand_hit = 0
    for key, lst in cands.items():
        have = set(dbv.get(key, {}))
        for sid, ef_cl, gl_cl in lst:
            cand_total += 1
            cand_hit += tuple(ef_cl) in have
    return dict(skills=tot_skill, skills_exact=tot_skill_exact, lines=tot_lines, lines_exact=tot_exact,
                gl=gl_tot, gl_exact=gl_exact, gl_lists=gl_lists, gl_lists_exact=gl_lists_exact,
                cand_total=cand_total, cand_hit=cand_hit, mismatch=mismatch, gl_mismatch=gl_bad)


# ---------------------------------------------------------------------------------------------- 유닛·스테이지
CLASH_UNITS = OrderedDict([('모티베이터', [140001 + i for i in range(6)]), ('웬디고', [140011 + i for i in range(6)]),
                           ('퍼세스', [140021 + i for i in range(6)]), ('고대 병졸', [140031 + i for i in range(6)])])
TAB_ORDER = [('SI_EVENT_CLASH_MOTIVATOR_STAGE', 22002, '모티베이터'), ('SI_EVENT_CLASH_WENDIGO_STAGE', 22003, '웬디고'),
             ('SI_EVENT_CLASH_PERSES_STAGE', 22004, '퍼세스')]
ICON_BY_FAMILY = {'모티베이터': '모티베이터', '웬디고': '웬디고', '퍼세스': '페르세스', '고대 병졸': '고대 병졸'}   # 데이터북 쪽 이름(f·아이콘 차용용)


def spawn_flag(sd):
    """배치/소환 행 -> 시작 쿨 표시 A/S/H/B/N (tools/build_foe_spawn.py flag 와 같은 규칙)"""
    if sd.get('AllSkillAvailable'):
        return 'A'
    sp, hy = bool(sd.get('SpecialSkillAvailable')), bool(sd.get('HyperSkillAvailable'))
    return {(True, True): 'B', (True, False): 'S', (False, True): 'H'}.get((sp, hy), 'N')


def unit_by_id(tb):
    return {r['m_UnitID']: r for r in tb.units.values()}


def db_icons(raw):
    """데이터북의 아이콘 번호 차용표(클라 표에는 없는 데이터북 자체 번호): 상태 효과 이름 -> i, 스킬 이름 -> mic, 유닛 이름 -> f"""
    gi, mic, fid = {}, defaultdict(set), defaultdict(set)
    for u in raw['u']:
        for e in u.get('im', []):
            gi.setdefault(e['n'], e.get('i'))
        fid[u['n']].add(u.get('f'))
    for s in raw['s']:
        for e in s.get('gl') or []:
            if e.get('i') is not None:
                gi.setdefault(e['n'], e['i'])
        mic[(s['sl'] in ('기본기', '특수기', '궁극기') or s['sl'], s['n'])].add(s.get('mic'))
    return gi, mic, fid


def load_db(root):
    from battlesim.starsavior import foe as F
    return F.load_foe(str(root))


def build(static, include_unverified=False, root=ROOT):
    tb = Tables(static)
    raw = load_db(root)
    conv = SeConverter(tb)
    shapes = db_shapes(raw)
    sb = SkillBuilder(tb, conv, shapes, include_unverified)
    gi, mic_map, fid_map = db_icons(raw)
    by_id = unit_by_id(tb)
    ak_names = {a[1]: i for i, a in enumerate(raw['ak'])}
    need_nst = ('NST_NV_RATE_ATK', 'NST_NV_RATE_HP', 'NST_NV_RATE_DEF')
    for n in need_nst:
        if n not in ak_names:
            raise SystemExit('foe.js ak 에 %s 가 없음(조각 ak 를 늘려야 함)' % n)

    s_list, s_index = [], {}          # 스킬 id -> 조각 내 인덱스
    u_list, x_list, x_index = [], [], {}
    unmodeled_units = []
    undone = []                        # 차용 불가 항목 보고

    def add_skill(skill_id, unit_name):
        if skill_id in s_index:
            return s_index[skill_id]
        sk = tb.skill[skill_id]
        ef, gl, nse, lv = sb.ef_for(skill_id, owner=skill_id)
        lvs = sb.level_row(sk)
        slot_m = re.search(r'_(ATTACK|SPECIAL|HYPER)$', skill_id)
        sl = SLOT[slot_m.group(1)] if slot_m else '패시브'
        if sk['m_NKM_SKILL_TYPE'] not in SKILL_TY or sk['m_TARGET_TYPE'] not in TARGET_TG:
            raise SystemExit('스킬 종류/대상 미지원 %s %s' % (skill_id, sk['m_NKM_SKILL_TYPE']))
        d = OrderedDict(sl=sl, n=tb.ko(sk['m_SkillName']), ty=SKILL_TY[sk['m_NKM_SKILL_TYPE']], tg=TARGET_TG[sk['m_TARGET_TYPE']])
        d['mic'] = None
        if sk.get('m_CoolTurn'):
            d['cd'] = sk['m_CoolTurn']
        if sk.get('SuperArmorBreakValue'):
            d['ab'] = sk['SuperArmorBreakValue']
        dt = tb.dt.get(sk.get('DTStrID'))
        if dt and dt.get('AtkFactor'):
            d['dm'] = '공격력×%s%%' % fnum(dt['AtkFactor'] / 100.0)
        if sk['m_TARGET_TYPE'] == 'NSTT_ENEMY_ALL':
            d['all'] = 1
        d['mx'] = len(lvs)
        d['d1'] = clean_markup(tb.ko(lv['SkillLevelDesc']))
        d['ef'] = ef
        if gl:
            d['gl'] = [dict(g, i=gi.get(g['n'])) for g in gl]
            for g in d['gl']:
                if g['i'] is None:
                    del g['i']
                    undone.append('상태 효과 아이콘 번호(i) 차용 불가: %s' % g['n'])
        # mic: 데이터북에서 같은 칸·이름 스킬의 번호 차용(여럿이면 첫 값이 유일할 때만)
        cand = {m for m in mic_map.get((True if sl != '패시브' else '패시브', d['n']), set()) if m is not None}
        if len(cand) == 1:
            d['mic'] = cand.pop()
        else:
            del d['mic']
            undone.append('스킬 아이콘 번호(mic) 차용 불가: %s (%s 후보 %s)' % (d['n'], sl, sorted(cand)))
        s_index[skill_id] = len(s_list)
        s_list.append(d)
        return s_index[skill_id]

    def link_skills(idxs):
        """스킬 설명 d1 에 같은 유닛의 궁극기 이름이 [대괄호]로 나오면 gl 에 «스킬» 항목을 둔다(데이터북 방식: sm = 그 스킬의 mic)."""
        names = {s_list[i]['n']: i for i in idxs}
        for i in idxs:
            s = s_list[i]
            order = list(OrderedDict.fromkeys(re.findall(r'\[([^\]]+)\]', s['d1'] or '')))
            for nm in order:
                j = names.get(nm)
                if j is None or j == i or any(g['n'] == nm for g in s.get('gl', [])):
                    continue
                tgt = s_list[j]
                if tgt['sl'] != '궁극기':
                    undone.append('스킬 링크 gl 은 궁극기만 데이터북 선례가 있음: %s -> %s(%s)' % (s['n'], nm, tgt['sl']))
                    continue
                e = OrderedDict(n=nm, k='스킬', d='이 적의 궁극기 이름입니다. 아래 스킬 카드를 참고하세요.')
                if tgt.get('mic') is not None:
                    e['sm'] = tgt['mic']
                s.setdefault('gl', []).append(e)
            if s.get('gl'):
                s['gl'].sort(key=lambda g: order.index(g['n']) if g['n'] in order else len(order))

    def ak_pairs(add):
        pairs = []
        for nst, v in (add or {}).items():
            if nst not in ak_names:
                raise SystemExit('AddStatData %s 가 foe.js ak 에 없음' % nst)
            pairs.append([ak_names[nst], v])
        return pairs

    def xi_of(add):
        pairs = ak_pairs(add)
        if not pairs:
            return None
        key = json.dumps(pairs)
        if key not in x_index:
            x_index[key] = len(x_list)
            x_list.append({'a': pairs})
        return x_index[key]

    unit_idx = {}                      # UnitID -> 조각 내 u 인덱스
    for fam, ids in CLASH_UNITS.items():
        for uid in ids:
            r = by_id[uid]
            st = tb.stat[r['m_StatStrID']]['m_StatData']
            gw = tb.per_level[tb.stat[r['m_StatStrID']]['m_StatAddPerLevelStrID']]
            b = [st['NST_HP'], st['NST_ATK'], st['NST_DEF'], st['NST_TURN_SPEED'], st['NST_RATE_CRITICAL'],
                 st['NST_RATE_CRITICAL_DAMAGE'], st['NST_RATE_EFFECT_HIT'], st['NST_RATE_EFFECT_EVADE'],
                 st['NST_RATE_DEFINITE_EFFECT_EVADE'], st['NST_SUPER_ARMOR']]
            im = []
            for ir in tb.immune.get(r.get('ImmuneGroupId'), []):
                for bid in ir['ImmuneBuffIdList']:
                    nm = tb.ko(ir.get('ImmuneBuffName')) or tb.buff_name(bid)
                    desc = clean_markup(tb.ko(ir.get('ImmuneBuffDesc')) or tb.ko(tb.buff[bid].get('m_BuffDesc')))
                    if any(e['n'] == nm for e in im):
                        continue
                    e = OrderedDict(n=nm, k='약화', d=desc)
                    if gi.get(nm) is not None:
                        e['i'] = gi[nm]
                    else:
                        undone.append('면역 효과 아이콘 번호(i) 차용 불가: %s' % nm)
                    im.append(e)
            f_cand = fid_map.get(ICON_BY_FAMILY[fam], set()) - {None}
            u = OrderedDict(n=tb.ko(r['m_UnitNameString']), g=GRADE[r['NKM_UNIT_GRADE']], el=ELEM[r['NKM_UNIT_ADJUST_TYPE']],
                            r=ROLE[r['m_NKM_UNIT_ROLE_TYPE']], k=ATTACK_KIND[r['UnitAttackTagType']], b=b,
                            gw=[gw['NST_HP'], gw['NST_ATK'], gw['NST_DEF']], ti=tb.ko(r['m_UnitTitleString']))
            if len(f_cand) == 1:
                u['f'] = next(iter(f_cand))
            else:
                undone.append('유닛 아이콘 번호(f) 차용 불가: %s 후보 %s' % (u['n'], sorted(f_cand)))
            u['im'] = im
            u['sk'] = [add_skill(sid, u['n']) for sid in r['m_listSkill']]
            link_skills(u['sk'])
            unit_idx[uid] = len(u_list)
            u_list.append(u)

    # ---- 스테이지
    aux_spawn, aux_sg, aux_ss = {}, {}, {}
    boss_kill = []   # BattleMode == BM_BOSS_KILL 인 스테이지 키(엔진 battle_end 가 보스 처치를 승리 조건으로 씀)
    battle = [r for r in jsonc(Path(static) / 'tables' / 'BATTLE_TEMPLET_NORMAL.json')['Data'] if r.get('ContentsTag') == 'SS_EVENT_CLASH' and r['BattleTabId'] in (22002, 22003, 22004)]
    unit_str_to_id = {r['m_UnitStrID']: r['m_UnitID'] for r in tb.units.values()}
    tabs = []
    content = tb.ko('SI_EVENT_CLASH_TITLE')
    for _stage_key, tab_id, fam in TAB_ORDER:
        rows = sorted((r for r in battle if r['BattleTabId'] == tab_id), key=lambda r: r['OrderList'])
        stages = []
        for r in rows:
            bs = jsonc(Path(static) / 'tables' / 'BattleScript' / r['BattleTempletFileName'].replace('.txt', '.json'))['Data']
            waves, wflags = [], []
            sm = []
            for w in bs['Waves']:
                wl, fl = [], []
                for sp in w['TeamBSpawnList']:
                    uid = unit_str_to_id[sp['UnitStrId']]
                    xi = xi_of(sp.get('AddStatData'))
                    wl.append([unit_idx[uid]] + ([xi] if xi is not None else []))
                    fl.append(spawn_flag(sp))
                    # 소환: 보스 특수기 SE 의 SummonGroupId
                    for sid in tb.units[sp['UnitStrId']]['m_listSkill']:
                        for lvl in sb.level_row(tb.skill[sid]):
                            for se_id in lvl.get('SkillLevelSE') or []:
                                gid = tb.se[se_id].get('SummonGroupId')
                                if not gid:
                                    continue
                                grp = tb.summon[gid]
                                # 슬롯 순서대로 (유닛, 변형) 을 만들고 이웃한 같은 항목만 마릿수로 접는다(foe.py 가 슬롯 순서로 펼침)
                                lst = []
                                for sd in grp['SummonData']:
                                    ent = [unit_idx[unit_str_to_id[sd['UnitStrId']]], xi_of(sd.get('AddStatData'))]
                                    if lst and lst[-1][:2] == ent:
                                        lst[-1][2] += 1
                                    else:
                                        lst.append(ent + [1])
                                sm.append([gid, u_list[unit_idx[uid]]['n'], lst])
                                aux_sg[str(gid)] = {'slots': [dict(pos=sd['SpawnPosIndex'], flag=spawn_flag(sd),
                                                                   **({'stats': sd['AddStatData']} if sd.get('AddStatData') else {}))
                                                              for sd in grp['SummonData']]}
                waves.append(wl)
                wflags.append(''.join(fl))
            name = tb.ko(r['BattleName'])
            st = OrderedDict(n=name, lv=r['BattleLevel'], bp=r['BattlePower'], w=waves)
            if sm:
                st['sm'] = sm
            stages.append(st)
            key = '%s|%s|%s' % ('clash', tb.ko(r['BattleTitleName']), name)
            aux_spawn[key] = wflags
            if r.get('BattleMode') == 'BM_BOSS_KILL':
                boss_kill.append(key)
            if sm:
                aux_ss[key] = {'wave_slots': [[sp.get('SpawnPosIndex', i) for i, sp in enumerate(w['TeamBSpawnList'])] for w in bs['Waves']]}
        tabs.append(OrderedDict(t=tb.ko(rows[0]['BattleTitleName']), s=stages))
    g = OrderedDict(k='clash', t=content, tabs=tabs)
    return dict(tb=tb, raw=raw, u=u_list, s=s_list, x=x_list, g=g, unmodeled=sb.unmodeled, undone=sorted(set(undone)),
                aux=dict(spawn=aux_spawn, summon_groups=aux_sg, summon_stages=aux_ss), boss_kill=boss_kill, conv=conv, shapes=shapes)


# sm 의 선택적 xi: foe.py 는 [ui, xi, count] 를 그대로 펼침 -> xi 가 없으면 None 대신 변형 없는 항목이 필요하므로 아래에서 정리한다.
def fix_sm(out):
    """sm 항목의 xi 가 None 이면 foe.py 가 raw['x'][None] 을 읽지 못하므로 빈 변형을 하나 두고 가리킨다."""
    need = any(e[1] is None for st in (s for t in out['g']['tabs'] for s in t['s']) for sm in st.get('sm', []) for e in sm[2])
    if not need:
        return
    out['x'].append({})
    idx = len(out['x']) - 1
    for t in out['g']['tabs']:
        for st in t['s']:
            for sm in st.get('sm', []):
                for e in sm[2]:
                    if e[1] is None:
                        e[1] = idx


NOTE = ('격전 의뢰(SS_EVENT_CLASH) 적 데이터 조각 — tools/build_foe_clash.py 가 클라 표에서 만듦(데이터북 rawdata/foe.js 와 같은 스키마, 값은 전부 표 기준). '
        '로더 규칙: u·s·x·g 는 foe.js 뒤에 덧붙이고, 조각 안 인덱스는 «조각 내부 0 기준»이라 로더가 오프셋을 더한다. '
        '유닛 u[i].sk[] 의 값은 이 조각 s 의 인덱스(+len(foe.s)), 스테이지 w[][][0] 은 이 조각 u 인덱스(+len(foe.u)), w[][][1] 과 sm[][2][][1] 은 이 조각 x 인덱스(+len(foe.x)), '
        'sm[][2][][0] 은 이 조각 u 인덱스. x[].a[][0] 은 조각 ak 가 아니라 «기존 foe.js ak 인덱스 그대로»(필요한 NST_NV_RATE_ATK/HP/DEF 가 foe.js ak 에 이미 있어 ak 는 비어 있음). '
        'g 는 foe.g 뒤에 1개 덧붙임. 소환 sm 항목 = [소환 그룹 ID, 소환자 이름(u.n), [[소환 유닛 u 인덱스, x 인덱스, 마릿수]]]. '
        'unmodeled = 효과 줄로 못 만든 SE 행(원인 포함), aux = foe_spawn.json·foe_summon.json 에 해당하는 값(시작 쿨 표시·소환 그룹·칸 번호), check = 검증 기록. '
        'f·mic·i(아이콘 번호)는 클라 표에 없는 데이터북 자체 번호라 데이터북에서 같은 이름의 값을 빌렸고, 빌릴 수 없으면 필드를 뺐다(check.undone).')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--static', type=Path)
    ap.add_argument('--report', type=Path, help='옛 판 비교 상세(불일치 목록)를 쓸 파일')
    ap.add_argument('--include-unverified', action='store_true', help='문법 미검증 줄도 ef 에 넣음')
    ap.add_argument('--out', type=Path, default=ROOT / 'data' / 'foe_clash.json')
    args = ap.parse_args()
    try:
        static = static_path(args.static)
    except ValueError as ex:
        ap.error(str(ex))
    low_priority()
    out = build(static, args.include_unverified)
    fix_sm(out)
    cmp_ = compare_old(out['tb'], out['raw'], out['conv'], out['shapes'])
    doc = OrderedDict(_note=NOTE, u=out['u'], s=out['s'], x=out['x'], ak=[], g=[out['g']])
    tb = out['tb']
    # 엔진(FoeDef)이 «미반영 효과»를 지원 보고에 올릴 수 있도록 한글 스킬 이름과 그 스킬을 쓰는 유닛 이름을 덧붙인다
    unm = []
    for x in out['unmodeled']:
        x = dict(x)
        sk = tb.skill.get(x.get('skill'))
        if sk:
            x['skill_name'] = tb.ko(sk['m_SkillName'])
            x['units'] = sorted({tb.ko(u['m_UnitNameString']) for u in tb.units.values() if x['skill'] in (u.get('m_listSkill') or [])})
        unm.append(x)
    doc['unmodeled'] = unm
    doc['aux'] = out['aux']
    doc['boss_kill'] = out['boss_kill']
    # 기간은 클라 표에 없다(서버 INTERVAL). 공식 공지(11/12 업데이트 안내 «진행 기간: 11/12(목) 점검 종료 후 ~ 12/03(목) 04:00») + 게임 이벤트 화면(2026-11-12 04:00 ~ 2026-12-03 04:00 UTC+9)
    doc['period'] = dict(start='2026-11-12T04:00:00+09:00', end='2026-12-03T04:00:00+09:00', src=['notice1112', 'ui'])
    doc['check'] = dict(old_edition=dict(skills=cmp_['skills'], skills_exact=cmp_['skills_exact'], lines=cmp_['lines'],
                                         lines_exact=cmp_['lines_exact'], gl=cmp_['gl'], gl_exact=cmp_['gl_exact'],
                                         gl_lists=cmp_['gl_lists'], gl_lists_exact=cmp_['gl_lists_exact'],
                                         cand_total=cmp_['cand_total'], cand_hit=cmp_['cand_hit']),
                        undone=out['undone'], include_unverified=bool(args.include_unverified))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8', newline='\n')
    print('저장', args.out, 'u', len(out['u']), 's', len(out['s']), 'x', len(out['x']), '스테이지', sum(len(t['s']) for t in out['g']['tabs']))
    print('옛 판 재현: 스킬 %d 중 완전 일치 %d, 줄 %d 중 일치 %d, 상태설명 %d 중 일치 %d' % (
        cmp_['skills'], cmp_['skills_exact'], cmp_['lines'], cmp_['lines_exact'], cmp_['gl'], cmp_['gl_exact']))
    print('  상태설명 목록(순서·과잉 포함) 일치 %d/%d, 역방향(옛 클라 스킬 %d개 중 데이터북에 같은 줄 묶음이 있는 것) %d' % (
        cmp_['gl_lists_exact'], cmp_['gl_lists'], cmp_['cand_total'], cmp_['cand_hit']))
    print('unmodeled', len(out['unmodeled']), Counter(u['kind'] for u in out['unmodeled']))
    if args.report:
        args.report.write_text(json.dumps(dict(ef=cmp_['mismatch'], gl=cmp_['gl_mismatch']), ensure_ascii=False, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
