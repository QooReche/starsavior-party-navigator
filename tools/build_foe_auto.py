# -*- coding: utf-8 -*-
"""적 스킬별 자동 대상 규칙(AutoSkillId)·효과 줄 자동 대상(AutoTargetId) -> data/foe_auto.json (공개 저장소에는 가공 어휘만).

게임 코드(NKM.decompiled.cs 6390~6450 효과 줄 자동 대상, 6454~6620 스킬 규칙 행, 6786~7130 필터).
- 데이터북 적(유닛 ui·변형 xi) ↔ 게임 유닛은 tools/build_foe_spawn 의 스테이지 연결을 쓰되, 조건에 맞는 배치가 하나뿐인 스테이지만,
  칸마다 역할·속성·보스 여부가 같을 때만 모은다. 한 (ui, xi) 에 게임 유닛이 여럿이면 가공 규칙이 모두 같을 때만 쓴다(다르면 제외·보고).
- 스킬 규칙: 게임 스킬(_ATTACK/_SPECIAL/_HYPER = 기본기/특수기/궁극기)의 AutoSkillId 행을 조건(c)·필터(f) 어휘로. 반응 스킬은 제외.
- 효과 줄: 그 스킬의 SE 행(COND_<스킬>_NN, 순서대로)과 데이터북 ef 줄을 줄 수가 같고, 줄마다 대상 종류(자신/적 전체/자동 지정 …)가
  맞을 때만 짝짓는다. AutoTargetId 가 있는 「적 자동 지정」 줄만 lines[si:k] = {"one": 단일 대상, "f": [...]}.
  EnforceAutoTargetId(강제 추가 행동 경로)는 쓰지 않는다.
모르는 어휘가 나온 스킬·줄은 건너뛰고 보고한다(조용히 다른 규칙으로 바꾸지 않음).

사용: python -X utf8 -I tools/build_foe_auto.py [--static <비공개 저장소>]
"""
import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.runtime import static_path, low_priority   # noqa: E402
from tools.build_auto_skill import jsonc   # noqa: E402
from tools import build_foe_spawn as SP   # noqa: E402
from battlesim.fileio import atomic_text   # noqa: E402
from battlesim.starsavior import foe as F   # noqa: E402

ROLE = {'NURT_STRIKER': '스트라이커', 'NURT_CASTER': '캐스터', 'NURT_ASSASSIN': '어쌔신', 'NURT_RANGER': '레인저',
        'NURT_DEFENDER': '디펜더', 'NURT_SUPPORTER': '서포터'}
ELEM = {'NUAT_SUN': '태양', 'NUAT_MOON': '달', 'NUAT_STAR': '별', 'NUAT_ORDER': '질서', 'NUAT_CHAOS': '혼돈'}
SLOT = {'ATTACK': '기본기', 'SPECIAL': '특수기', 'HYPER': '궁극기'}
SIMPLE = {'IsNotInvincible': 'not_invincible', 'IsBoss': 'boss', 'IsElite': 'elite', 'IsAdvantageAdjustType': 'advantage',
          'IsLowHpRate': 'low_hp_rate', 'IsLowMaxHp': 'low_max_hp', 'IsHighHpRate': 'high_hp_rate', 'IsHighMaxHp': 'high_max_hp',
          'IsHighAtk': 'high_atk', 'IsLowAtk': 'low_atk', 'IsHighSpeedGauge': 'high_gauge', 'IsLowSpeedGauge': 'low_gauge',
          'IsHighTurnSpeed': 'high_spd', 'IsLowTurnSpeed': 'low_spd', 'IsLastHitTarget': 'last_hit', 'IsLastDamageTarget': 'last_damager',
          'IsLeader': 'leader', 'IsAllyOneNotSelf': 'not_self', 'IsSuperArmorBreak': 'broken', 'IsNotSuperArmorBreak': 'not_broken',
          'FollowSkillTargetType': 'follow'}
RATE = {'FrontLineTargetRate': 'front', 'BackLineTargetRate': 'back', 'DefenderTargetRate': '디펜더', 'StrikerTargetRate': '스트라이커',
        'RangerTargetRate': '레인저', 'CasterTargetRate': '캐스터', 'AssassinTargetRate': '어쌔신', 'SupporterTargetRate': '서포터'}
COUNT = {'IsPositiveBuffCountOverThan': 'buff_ge', 'IsPositiveBuffCountLessThan': 'buff_le',
         'IsNegativeBuffCountOverThan': 'debuff_ge', 'IsNegativeBuffCountLessThan': 'debuff_le'}
AUTO_ENEMY = {'NSETT_AUTO_ENEMY': False, 'NSETT_AUTO_ENEMY_ONE': True}
# 데이터북 ef 줄의 대상 머리말 -> SE m_BuffTargetType 묶음(짝짓기 검증용)
HEAD = [(r'적 1명\(자동 지정\)', {'NSETT_AUTO_ENEMY_ONE'}), (r'적\(자동 지정\)', {'NSETT_AUTO_ENEMY', 'NSETT_AUTO_ENEMY_ONE'}),
        (r'아군[^에]*\(자동 지정\)|자신[^에]*제외[^에]*\(자동 지정\)', {'NSETT_AUTO_ALLY', 'NSETT_AUTO_ALLY_ONE', 'NSETT_AUTO_ALLY_ONE_NOT_SELF'}),
        (r'적 전체', {'NSETT_ENEMY_ALL'}), (r'아군 전체|자신 제외 아군 전체|자신을 제외한 아군 전체', {'NSETT_MYTEAM_ALL', 'NSETT_MYTEAM_ALL_NOT_SELF'}),
        (r'자신에게|자신의', {'NSETT_SELF'}), (r'스킬 대상|대상에게|적에게|적 1명에게', {'NSETT_TARGET'})]
REPORT = Counter()
REPORT_HEAD = Counter()      # 대상 머리말을 못 읽은 줄(짝짓기 거절)


class Unknown(Exception):
    pass


def names_of(ids, bname):
    out = []
    for i in ids:
        n = bname.get(i)
        if not n:
            raise Unknown('효과 이름 없음 ' + i)
        if n not in out:
            out.append(n)
    return out


def filters(t, bname):
    out = []
    for k, v in (t or {}).items():
        if k in SIMPLE and v is True:
            out.append(SIMPLE[k])
        elif k in RATE and isinstance(v, int):
            out.append([RATE[k], v / 10000])
        elif k in COUNT and isinstance(v, int):
            out.append([COUNT[k], v])
        elif k in ('IsSpecificBuff', 'IsNotSpecificBuff'):
            out.append(['has' if k == 'IsSpecificBuff' else 'not_has', names_of(v, bname)])
        elif k in ('IsAdjustType', 'IsNotAdjustType') and v in ELEM:
            out.append(['elem' if k == 'IsAdjustType' else 'not_elem', ELEM[v]])
        elif k in ('IsRoleType', 'IsNotRoleType') and v in ROLE:
            out.append(['role' if k == 'IsRoleType' else 'not_role', ROLE[v]])
        else:
            raise Unknown('필터 %s=%s' % (k, v))
    return out


def conds(c, bname):
    out = []
    c = dict(c)
    if 'SelfSpecificBuff' in c:
        ids = c.pop('SelfSpecificBuff')
        if 'SelfBuffLevelCount' in c:
            ns = names_of(ids, bname)
            if len(ns) != 1:
                raise Unknown('스택 조건 여러 효과')
            out.append(['self_stack_eq', ns[0], int(c.pop('SelfBuffLevelCount'))])
        else:
            out.append(['self_has', names_of(ids, bname)])
    for k, tag in (('NotSelfSpecificBuff', 'self_not_has'), ('ExistEnemySpecificBuff', 'enemy_has'), ('ExistAllySpecificBuff', 'ally_has')):
        if k in c:
            out.append([tag, names_of(c.pop(k), bname)])
    if 'AllyHpRateLessThan' in c:
        out.append(['ally_hp_le_bp', int(c.pop('AllyHpRateLessThan'))])
    if c.pop('AllyDie', False):
        out.append(['ally_dead'])
    if c:
        raise Unknown('조건 %s' % sorted(c))
    return out


def se_rows(tables):
    by = defaultdict(list)
    for n in (1, 2):
        for r in json.loads((tables / ('SE_TEMPLET_SKILL_%d.json' % n)).read_text(encoding='utf-8'))['Data']:
            m = re.match(r'^COND_(.+)_(\d+)$', r.get('m_SEStrID') or '')
            if m:
                by[m.group(1)].append((int(m.group(2)), r))
    return {k: [r for _, r in sorted(v, key=lambda x: x[0])] for k, v in by.items()}


def se_of(sid, se):
    for key in (sid.replace('NKM_UNIT_MON_', '', 1), sid.replace('NKM_UNIT_', '', 1)):
        if key in se:
            return se[key]
    return None


def pair_lines(ef, rows):
    """데이터북 ef 줄 ↔ SE 행. 줄 수가 같고 줄마다 대상 머리말이 SE 대상 종류와 맞을 때만 {줄 번호: SE 행}"""
    if len(ef) != len(rows):
        return None
    for line, r in zip(ef, rows):
        tt = r.get('m_BuffTargetType')
        for pat, kinds in HEAD:
            if re.search(pat, line):
                if tt not in kinds:
                    return None       # 한 줄이라도 대상 종류가 다르면 그 스킬 전체를 짝짓지 않음
                break
        else:
            REPORT_HEAD[line.split(']')[-1][:30]] += 1
            return None               # 대상 머리말을 못 읽은 줄이 있으면 짝짓지 않음
        if ('자동 지정' in line) != (tt or '').startswith('NSETT_AUTO'):
            return None
    return dict(enumerate(rows))


def build(static):
    tables = Path(static) / 'tables'
    units = {}
    for n in (1, 2, 3, 4):
        for u in json.loads((tables / ('UNIT_TEMPLET_BASE%d.json' % n)).read_text(encoding='utf-8'))['Data']:
            units[u['m_UnitStrID']] = u
    skills = {}
    for n in (1, 2):
        for r in json.loads((tables / ('SKILL_TEMPLET_%d.json' % n)).read_text(encoding='utf-8'))['Data']:
            skills[r['m_SkillStrID']] = r
    auto = {r['Id']: r for r in jsonc(tables / 'Plain' / 'AUTO_SKILL_TEMPLET.json')['Data']}
    target = {r['Id']: r['TargetCondition'] for r in jsonc(tables / 'Plain' / 'AUTO_SKILL_TARGET_TEMPLET.json')['Data']}
    strings = json.loads((tables / 'Strings' / 'STRING_COMMON_ko_en.json').read_text(encoding='utf-8'))
    bname = {}
    for r in json.loads((tables / 'BUFF_TEMPLET.json').read_text(encoding='utf-8'))['Data']:
        ko = (strings.get(r.get('m_BuffName') or '') or {}).get('ko')
        if ko:
            bname[r['m_BuffStrID']] = ko
    se = se_rows(tables)
    raw = F.load_foe(str(ROOT))
    rows = SP.battle_rows(static)
    link = defaultdict(set)      # (ui, xi) -> 게임 UnitStrId 집합
    for c in raw['g']:
        for ti, t in enumerate(c['tabs']):
            for si, s in enumerate(t['s']):
                hits = []
                cands = SP.candidates(c['k'], t['t'], s['n'], ti, si, rows)
                if c['k'] == 'equip':
                    # 장비 탐색(혹한의 습격 등): NORMAL_BATTLE_EXPLORE_EQUIP<탭 순서>_<단계> — 권장 전투력·레벨로 거른다
                    head = 'NORMAL_BATTLE_EXPLORE_EQUIP%d_' % (ti + 1)
                    cands = sorted(k for k in rows if k.startswith(head))
                for sid in cands:
                    row = rows.get(sid)
                    if not row or not row[0].exists() or row[1] != str(s.get('bp')) or row[2] != str(s.get('lv')):
                        continue
                    waves = (SP.jsonc(row[0]).get('Data') or {}).get('Waves') or []
                    lists = [[[sp['UnitStrId'], sp.get('ChangeAdjustType')] for sp in (w.get('TeamBSpawnList') or [])] for w in waves]
                    if [len(x) for x in lists] != [len(w) for w in s['w']]:
                        continue
                    hits.append(lists)
                if len({json.dumps(h) for h in hits}) != 1:
                    REPORT['스테이지 연결 없음/여럿'] += 1
                    continue
                for w, lw in zip(s['w'], hits[0]):
                    for e, (gid, cadj) in zip(w, lw):
                        ui, xi = e[0], (e[1] if len(e) > 1 else None)
                        u, gu = raw['u'][ui], units.get(gid)
                        x = raw['x'][xi] if xi is not None else None
                        if gu is None:
                            REPORT['게임 유닛 없음'] += 1
                            continue
                        el = (x and x.get('el')) or u['el']
                        # 칸 속성 = 배치의 ChangeAdjustType(있으면) 아니면 유닛 속성. 보스 표시는 데이터북이 정예를 일반으로 적기도 해 보지 않음
                        g_el = ELEM.get(cadj if cadj and cadj != 'NUAT_INVALID' else gu.get('NKM_UNIT_ADJUST_TYPE'))
                        if ROLE.get(gu.get('m_NKM_UNIT_ROLE_TYPE')) != u['r'] or g_el != el:
                            REPORT['칸 역할·속성 불일치'] += 1
                            continue
                        link[(ui, xi)].add(gid)
    out = {}
    for (ui, xi), gids in sorted(link.items(), key=lambda kv: (kv[0][0], -1 if kv[0][1] is None else kv[0][1])):
        u = raw['u'][ui]
        variants = []
        for gid in sorted(gids):
            try:
                variants.append(json.dumps(unit_rules(u, raw, units[gid], skills, auto, target, se, bname), ensure_ascii=False, sort_keys=True))
            except Unknown as ex:
                REPORT['모르는 어휘: ' + str(ex)[:60]] += 1
                variants.append(None)
        if None in variants or len(set(variants)) != 1:
            REPORT['한 유닛에 다른 규칙(제외)' if None not in variants else '모르는 어휘로 유닛 제외'] += 1
            continue
        rules = json.loads(variants[0])
        if rules['skills'] or rules['lines']:
            out['foe:%d' % ui + (':%d' % xi if xi is not None else '')] = rules
    return out


def unit_rules(u, raw, gu, skills, auto, target, se, bname):
    res = {'skills': {}, 'lines': {}}
    db = {raw['s'][si]['sl']: si for si in u['sk'] if raw['s'][si]['sl'] in SLOT.values()}
    for sid in gu.get('m_listSkill') or []:
        m = re.search(r'_(ATTACK|SPECIAL|HYPER)\d*$', sid)
        sk = skills.get(sid) or {}
        if not m or sk.get('m_NKM_SKILL_TYPE') == 'NST_REACT':
            continue
        slot = SLOT[m.group(1)]
        if slot not in db or re.search(r'_(ATTACK|SPECIAL|HYPER)\d+$', sid):
            continue          # 같은 칸 두 번째 스킬(SPECIAL2 등)은 데이터북 칸과 1:1 이 아니라 건너뜀
        aid = sk.get('AutoSkillId')
        if aid:
            res['skills'][slot] = {'rows': [{'c': conds(r['Condition'], bname), 'f': filters(target.get(r['TargetConditionId']), bname)}
                                            for r in auto[aid]['SkillConditions']]}
        add_lines(res, db[slot], sid, raw, se, target, bname)
    # 패시브: 게임 _PASSIVE 스킬 순서 = 데이터북 패시브 순서(수가 같을 때만)
    g_pass = [sid for sid in gu.get('m_listSkill') or [] if re.search(r'_PASSIVE\d*$', sid)]
    d_pass = [si for si in u['sk'] if raw['s'][si]['sl'] == '패시브']
    if len(g_pass) == len(d_pass):
        for sid, si in zip(g_pass, d_pass):
            add_lines(res, si, sid, raw, se, target, bname)
    elif any(any(r.get('AutoTargetId') for r in (se_of(sid, se) or [])) for sid in g_pass):
        REPORT['패시브 수 불일치(자동 지정 줄 제외)'] += 1
    return res


def add_lines(res, si, sid, raw, se, target, bname):
    rows_se = se_of(sid, se)
    if not rows_se or not any(r.get('AutoTargetId') for r in rows_se):
        return
    pairs = pair_lines(raw['s'][si].get('ef') or [], rows_se)
    if pairs is None:
        REPORT['효과 줄 짝짓기 실패'] += 1
        return
    for k, r in pairs.items():
        tt = r.get('m_BuffTargetType')
        if r.get('AutoTargetId') and tt in AUTO_ENEMY:
            res['lines']['%d:%d' % (si, k)] = {'one': AUTO_ENEMY[tt], 'f': filters(target.get(r['AutoTargetId']), bname)}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--static', type=Path)
    args = ap.parse_args()
    try:
        static = static_path(args.static)
    except ValueError as ex:
        ap.error(str(ex))
    low_priority()
    units = build(static)
    out = dict(_note='적 자동 대상 규칙(tools/build_foe_auto.py). units[foe:유닛[:변형]] = {skills[칸] = 규칙 행(c 조건, f 필터), '
                     'lines["스킬번호:줄번호"] = 효과 줄 자동 대상(one = 1명, f 필터)}. 없는 적·줄은 엔진 기본(설명문 근사 -> 규칙 1001).',
               units=units)
    atomic_text(ROOT / 'data' / 'foe_auto.json', json.dumps(out, ensure_ascii=False, separators=(',', ':')) + '\n')
    n_sk = sum(len(v['skills']) for v in units.values())
    n_ln = sum(len(v['lines']) for v in units.values())
    print('foe_auto.json: 적', len(units), '스킬 규칙', n_sk, '효과 줄', n_ln)
    for k, v in REPORT.most_common():
        print('  ', v, k)
    for k, v in REPORT_HEAD.most_common(8):
        print('   머리말 미인식', v, k)


if __name__ == '__main__':
    main()
