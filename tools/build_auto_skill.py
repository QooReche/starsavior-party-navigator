# -*- coding: utf-8 -*-
"""구원자 스킬별 자동 전투 규칙(AutoSkillId) -> data/auto_skill.json (공개 저장소에는 가공 어휘만).

게임 코드(NKM.decompiled.cs 6360~6620 AutoSkillController): 자동 전투는 궁극기 -> 특수기 -> 기본기 순으로 액티브 스킬마다
쿨 -> 규칙 행(SkillConditions)을 위에서부터 보고 조건이 모두 참인 첫 행의 대상 필터로 대상을 고른다. 참인 행이 없거나 대상이 0명이면
그 스킬을 건너뛴다. 스킬에 AutoSkillId 가 없으면 구원자 = 규칙 1, 적 = 규칙 1001(엔진 상수, 아래 DEFAULTS 와 표가 같은지 확인함).
대상 필터(6786~7130): 차례로 거르고, 거른 결과가 0명이면 목록 유지, 1명이 되면 멈춤, 끝에 여럿이면 무작위.

출력 units[구원자 key][칸] = {"t": 대상 종류, "rows": [{"c": [조건...], "f": [필터...]}, ...]} 또는 {"react": true}(반응 스킬 — 엔진은 반응 문구로 처리).
  조건: ["ally_hp_le_bp", 7500] = 생명력 int(비율x10000) <= 값인 아군이 있음, ["ally_dead"] = 쓰러진 아군이 있음,
        ["self_stack_eq", 이름, n] = 자신의 그 스택이 정확히 n.
  필터: not_invincible, boss, elite, advantage, low_hp_rate, low_max_hp, not_self, dead_ally(쓰러진 아군 중 마지막으로 쓰러진 1명).
모르는 조건·필터·대상 종류가 나오면 실패한다(조용히 빠뜨리지 않음).

사용: python -X utf8 -I tools/build_auto_skill.py [--static <비공개 저장소>]
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.runtime import static_path, low_priority   # noqa: E402
from battlesim.fileio import atomic_text   # noqa: E402

SLOTS = ('기본기', '특수기', '궁극기', '패시브')
TT = {'NSTT_ENEMY_ONE': 'enemy_one', 'NSTT_ENEMY_ALL': 'enemy_all', 'NSTT_ALLY_ONE': 'ally_one',
      'NSTT_ALLY_ALL': 'ally_all', 'NSTT_MYSELF': 'self'}
FILTER = {'IsNotInvincible': 'not_invincible', 'IsBoss': 'boss', 'IsElite': 'elite', 'IsAdvantageAdjustType': 'advantage',
          'IsLowHpRate': 'low_hp_rate', 'IsLowMaxHp': 'low_max_hp', 'IsAllyOneNotSelf': 'not_self', 'IsRandomDeadAllyOne': 'dead_ally'}
ELEM = {'SUN': '태양', 'MOON': '달', 'STAR': '별', 'ORDER': '질서', 'CHAOS': '혼돈'}
# 엔진(battlesim/mc.py RULE1·RULE1001)이 상수로 쓰는 기본 규칙. 표가 바뀌면 빌드가 실패해 엔진을 같이 고치게 한다.
DEFAULTS = {1: {'IsNotInvincible': True, 'IsBoss': True, 'IsElite': True, 'IsAdvantageAdjustType': True, 'IsLowHpRate': True, 'IsLowMaxHp': True},
            1001: {'FrontLineTargetRate': 8000, 'DefenderTargetRate': 8000}}


def jsonc(path):
    """주석(//) 달린 표. 문자열 안의 // 는 건드리지 않는다."""
    s = Path(path).read_text(encoding='utf-8')
    out, i, n, ins = [], 0, len(s), False
    while i < n:
        c = s[i]
        if ins:
            out.append(c)
            if c == '\\':
                out.append(s[i + 1])
                i += 2
                continue
            ins = c != '"'
            i += 1
            continue
        if c == '"':
            ins = True
        elif s.startswith('//', i):
            j = s.find('\n', i)
            i = n if j < 0 else j
            continue
        out.append(c)
        i += 1
    return json.loads(re.sub(r',(\s*[\]}])', r'\1', ''.join(out)))


def elem_stack_names(ui):
    """구원자 설명 사전(gl)의 「속성 스택 · <속성>」 이름"""
    out = {}
    for s in ui or []:
        for g in s.get('gl') or []:
            if len(g) >= 2 and g[1].startswith('속성 스택 · '):
                out.setdefault(g[1].split('·')[1].strip(), g[0])
    return out


def conds(c, stacks, where):
    out = []
    c = dict(c)
    if 'AllyHpRateLessThan' in c:
        out.append(['ally_hp_le_bp', int(c.pop('AllyHpRateLessThan'))])
    if c.pop('AllyDie', False):
        out.append(['ally_dead'])
    if 'SelfSpecificBuff' in c and 'SelfBuffLevelCount' in c:
        ids = c.pop('SelfSpecificBuff')
        n = int(c.pop('SelfBuffLevelCount'))
        if len(ids) != 1 or not ids[0].startswith('BI_ADJUSTTYPE_RESOURCE_'):
            raise SystemExit('모르는 스택 조건 %s: %s' % (where, ids))
        el = ELEM[ids[0].rsplit('_', 1)[1]]
        if el not in stacks:
            raise SystemExit('속성 스택 이름 없음 %s: %s' % (where, el))
        out.append(['self_stack_eq', stacks[el], n])
    if c:
        raise SystemExit('모르는 조건 %s: %s' % (where, sorted(c)))
    return out


def filters(t, where):
    out = []
    for k, v in (t or {}).items():
        if k not in FILTER or v is not True:
            raise SystemExit('모르는 필터 %s: %s=%s' % (where, k, v))
        out.append(FILTER[k])
    return out


def build(static):
    tables = Path(static) / 'tables'
    auto = {r['Id']: r for r in jsonc(tables / 'Plain' / 'AUTO_SKILL_TEMPLET.json')['Data']}
    target = {r['Id']: r['TargetCondition'] for r in jsonc(tables / 'Plain' / 'AUTO_SKILL_TARGET_TEMPLET.json')['Data']}
    for i, want in DEFAULTS.items():
        rows = auto[i]['SkillConditions']
        if len(rows) != 1 or rows[0]['Condition'] or target[rows[0]['TargetConditionId']] != want:
            raise SystemExit('기본 규칙 %d 이 엔진 상수와 다름 — battlesim/mc.py 를 같이 고칠 것' % i)
    skills = {}
    for n in (1, 2):
        for r in json.loads((tables / ('SKILL_TEMPLET_%d.json' % n)).read_text(encoding='utf-8'))['Data']:
            skills[r['m_SkillStrID']] = r
    index = json.loads((ROOT / 'data' / 'saviors_index.json').read_text(encoding='utf-8'))
    keys = {int(k): v['key'] for k, v in index.items() if not k.startswith('_') and v.get('key')}
    desc = json.loads((ROOT / 'data' / 'savior_skills.json').read_text(encoding='utf-8'))
    units = {}
    for u in json.loads((tables / 'UNIT_TEMPLET_BASE1.json').read_text(encoding='utf-8'))['Data']:
        key = keys.get(u['m_UnitID'])
        if key is None:
            continue
        stacks = elem_stack_names(desc.get(str(u['m_UnitID'])))
        for slot, sid in zip(SLOTS, u['m_listSkill']):
            sk = skills.get(sid) or {}
            aid = sk.get('AutoSkillId')
            if not aid:
                continue
            where = '%s %s(%d)' % (key, slot, aid)
            if sk.get('m_NKM_SKILL_TYPE') == 'NST_REACT':
                units.setdefault(key, {})[slot] = {'react': True}
                continue
            if sk.get('m_TARGET_TYPE') not in TT:
                raise SystemExit('모르는 대상 종류 %s: %s' % (where, sk.get('m_TARGET_TYPE')))
            rows = [{'c': conds(r['Condition'], stacks, where), 'f': filters(target.get(r['TargetConditionId']), where)}
                    for r in auto[aid]['SkillConditions']]
            units.setdefault(key, {})[slot] = {'t': TT[sk['m_TARGET_TYPE']], 'rows': rows}
    return units


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
    out = dict(_note='구원자 스킬별 자동 전투 규칙(tools/build_auto_skill.py). 규칙 행 = 조건(c, 모두 참) + 대상 필터(f, 차례로 거름). '
                     '참인 행이 없으면 그 스킬을 건너뜀. 여기 없는 스킬은 엔진 기본 규칙(구원자 1).',
               units=dict(sorted(units.items())))
    atomic_text(ROOT / 'data' / 'auto_skill.json', json.dumps(out, ensure_ascii=False, separators=(',', ':')) + '\n')
    print('auto_skill.json: 구원자', len(units), '스킬', sum(len(v) for v in units.values()))


if __name__ == '__main__':
    main()
