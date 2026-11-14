# -*- coding: utf-8 -*-
"""구원자 스킬별 자동 전투 규칙(AutoSkillId) -> data/auto_skill.json (공개 저장소에는 가공 어휘만).

게임 코드(NKM.decompiled.cs 6360~6620 AutoSkillController): 자동 전투는 궁극기 -> 특수기 -> 기본기 순으로 액티브 스킬마다
쿨 -> 규칙 행(SkillConditions)을 위에서부터 보고 조건이 모두 참인 첫 행의 대상 필터로 대상을 고른다. 참인 행이 없거나 대상이 0명이면
그 스킬을 건너뛴다. 스킬에 AutoSkillId 가 없으면 구원자 = 규칙 1, 적 = 규칙 1001(엔진 상수, 아래 DEFAULTS 와 표가 같은지 확인함).
대상 필터(6786~7130): 차례로 거르고, 거른 결과가 0명이면 목록 유지, 1명이 되면 멈춤, 끝에 여럿이면 무작위.

출력 units[구원자 key][칸] = {"t": 대상 종류, "rows": [{"c": [조건...], "f": [필터...]}, ...]} 또는 {"react": true}(반응 스킬 — 엔진은 반응 문구로 처리).
기본/개화는 (id, variant)로 구분하고 개화 스킬은 BLOSSOM_TEMPLET에서 읽는다.
효과 줄은 variant_lines가 현행이며 lines는 옛 매핑 재현용이다.
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
from battlesim.starsavior.savior_ids import keys_by_id   # noqa: E402
from tools.tables import jsonc, buff_names   # noqa: E402,F401  (jsonc: 다른 빌더가 여기서 가져다 씀)
from battlesim.starsavior.parser import explicit_target, split_head


def described_auto(raw):
    """공개 데이터북 2.70에서 풀어 쓴 자동 대상도 SE와 연결한다."""
    return explicit_target(split_head(raw)[2].split('에게 ', 1)[0])


def is_auto_line(raw):
    return '(자동 지정)' in raw or described_auto(raw) is not None

SLOTS = ('기본기', '특수기', '궁극기', '패시브')
NSI = {'NSI_SKILL_1_ATTACK': '기본기', 'NSI_SKILL_2_SPECIAL': '특수기', 'NSI_SKILL_3_HYPER': '궁극기'}
TT = {'NSTT_ENEMY_ONE': 'enemy_one', 'NSTT_ENEMY_ALL': 'enemy_all', 'NSTT_ALLY_ONE': 'ally_one',
      'NSTT_ALLY_ALL': 'ally_all', 'NSTT_MYSELF': 'self'}
FILTER = {'IsNotInvincible': 'not_invincible', 'IsBoss': 'boss', 'IsElite': 'elite', 'IsAdvantageAdjustType': 'advantage',
          'IsLowHpRate': 'low_hp_rate', 'IsLowMaxHp': 'low_max_hp', 'IsHighDef': 'high_def', 'IsLowDef': 'low_def',
          'IsAllyOneNotSelf': 'not_self', 'IsRandomDeadAllyOne': 'dead_ally', 'IsNotUnableToAct': 'not_unable_to_act'}
ELEM = {'SUN': '태양', 'MOON': '달', 'STAR': '별', 'ORDER': '질서', 'CHAOS': '혼돈'}
# 엔진(battlesim/mc.py RULE1·RULE1001)이 상수로 쓰는 기본 규칙. 표가 바뀌면 빌드가 실패해 엔진을 같이 고치게 한다.
DEFAULTS = {1: {'IsNotInvincible': True, 'IsBoss': True, 'IsElite': True, 'IsAdvantageAdjustType': True, 'IsLowHpRate': True, 'IsLowMaxHp': True},
            1001: {'FrontLineTargetRate': 8000, 'DefenderTargetRate': 8000}}


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


def form_bindings(tables, keys, book):
    """공개 (id, variant)를 기본/개화 스킬 목록과 명시적으로 연결한다.

    BLOSSOM_TEMPLET.BlossomListSkill이 정본이며 _SSR 이름을 추측하지 않는다.
    같은 id의 마지막 설명을 기본 스킬에 붙이면 베라의 두 자동 대상이 뒤섞인다.
    """
    variants = {}
    for row in book:
        pair = (row['id'], row['v'])
        if pair in variants:
            raise ValueError('중복 구원자 형태: %r' % (pair,))
        variants[pair] = row
    blossom = {r['UnitId']: r for r in json.loads((tables / 'BLOSSOM_TEMPLET.json').read_text(encoding='utf-8'))['Data']}
    for u in json.loads((tables / 'UNIT_TEMPLET_BASE1.json').read_text(encoding='utf-8'))['Data']:
        uid = u['m_UnitID']
        if uid not in keys:
            continue
        for variant, field in (('기본', 'm_listSkill'), ('개화(SSR)', 'BlossomListSkill')):
            bu = variants.get((uid, variant))
            if bu is None:
                continue
            source = u if variant == '기본' else blossom.get(uid)
            if source is None:
                raise ValueError('개화 스킬 연결 없음: %s' % uid)
            key = keys[uid] + ('' if variant == '기본' else '@' + variant)
            yield key, bu, u, source[field]


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
    keys = keys_by_id(index)
    desc = json.loads((ROOT / 'data' / 'savior_skills.json').read_text(encoding='utf-8'))
    units, order = {}, {}
    book = json.loads((ROOT / 'rawdata/databook_main.json').read_text(encoding='utf-8'))['units']
    for key, _bu, u, skill_ids in form_bindings(tables, keys, book):
        if u.get('SkillOrderList'):
            # 오토 스킬 시도 순서(NKM.decompiled.cs 6378 루프, 없으면 기본 [궁극기, 특수기, 기본기] — NKM.Templets 25744~25751)
            try:
                order[key] = [NSI[x] for x in u['SkillOrderList']]
            except KeyError as ex:
                raise SystemExit('모르는 SkillOrderList 칸 %s: %s' % (key, ex))
        stacks = elem_stack_names(desc.get(str(u['m_UnitID'])))
        for slot, sid in zip(SLOTS, skill_ids):
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
    return units, order


def _dedup_se(rows):
    """묶음 번호·행 ID 만 다른 SE 행을 하나로(순서 유지)."""
    out, seen = [], set()
    for r in rows:
        k = json.dumps({k: v for k, v in r.items() if k not in ('m_SEStrID', 'm_SEID', 'SEGroupID')}, sort_keys=True, ensure_ascii=False)
        if k not in seen:
            seen.add(k)
            out.append(r)
    return out


def _skip_paren(head):
    """앞머리 「(조건: …)」 한 덩어리를 짝 맞는 닫는 괄호까지 건너뛴다(조건 안 「보호막(해제불가)」 같은 괄호 포함)."""
    if not head.startswith('('):
        return head
    depth = 0
    for i, ch in enumerate(head):
        depth += (ch == '(') - (ch == ')')
        if depth == 0:
            return head[i + 1:].lstrip()
    return head


def build_lines(static, report, *, legacy=False, client=False):
    """구원자 효과 줄 자동 대상(SE AutoTargetId) -> {구원자 key: [[칸, 데이터북 원문, {one, ally?, f}], ...]}.
    데이터북 효과 줄에는 게임 SE 행이 아닌 줄(이번 스킬 보정 등)이 섞여 있어 줄 수 대신 「(자동 지정)」 줄 ↔ 게임 자동 지정 행을
    순서대로 짝짓는다(개수·아군/적·1명/전체가 맞을 때만). SE 이름 COND_<스킬>_<묶음>_<줄> 의 묶음 01 = 기본 효과, 그 뒤는 레벨업 추가 행.
    client=True는 build 26314877 NKM:7013-7019의 대상형 자신 제외를 필터 체인 앞에 적용한다.
    client=False는 3월판 근거의 기존 자료(개화 제외·기본형 not_self 우선 필터)를 재현한다."""
    from tools import build_foe_auto as FA
    tables = Path(static) / 'tables'
    target = {r['Id']: r['TargetCondition'] for r in jsonc(tables / 'Plain' / 'AUTO_SKILL_TARGET_TEMPLET.json')['Data']}
    bname = buff_names(tables)
    se = {}
    for n in (1, 2):
        for r in json.loads((tables / ('SE_TEMPLET_SKILL_%d.json' % n)).read_text(encoding='utf-8'))['Data']:
            m = re.match(r'^COND_(.+)_(\d+)_(\d+)$', r.get('m_SEStrID') or '')
            if m:
                se.setdefault(m.group(1), {}).setdefault(int(m.group(2)), []).append((int(m.group(3)), r))
    index = json.loads((ROOT / 'data' / 'saviors_index.json').read_text(encoding='utf-8'))
    keys = keys_by_id(index)
    book = json.loads((ROOT / 'rawdata' / 'databook_main.json').read_text(encoding='utf-8'))['units']
    slot_of = {'기본기': 0, '특수기': 1, '궁극기': 2, '고유 패시브': 3}
    auto_types = set(FA.AUTO_ENEMY) | set(FA.AUTO_ALLY) | {'NSETT_AUTO_ALLY_ONE_NOT_SELF'}
    out = {}
    bindings = form_bindings(tables, keys, book)
    if legacy:
        # 규칙의 옛 값·고정 해시 재현용. 새 자료는 반드시 위 형태별 연결을 쓴다.
        last = {u['id']: u for u in book}
        bindings = ((keys[u['m_UnitID']], last[u['m_UnitID']], u, u['m_listSkill'])
                    for u in json.loads((tables / 'UNIT_TEMPLET_BASE1.json').read_text(encoding='utf-8'))['Data']
                    if u['m_UnitID'] in keys and u['m_UnitID'] in last)
    for key, bu, _u, skill_ids in bindings:
        for s in bu['sk']:
            i = slot_of.get(s['sl'])
            if i is None or i >= len(skill_ids):
                continue
            sid = skill_ids[i].replace('NKM_UNIT_', '', 1)
            levels = se.get(sid) or se.get(sid.replace('S_', '', 1))
            if not levels:
                continue
            # 가운데 번호 01 = 기본 효과 묶음, 02 이상 = 레벨업 때 더해지는 행(SKILL_LEVEL_GROUP_TEMPLET).
            # 기본 묶음의 자동 지정 SE 로 spec(필터)을 정하고, 추가 묶음에도 자동 지정이 있으면
            # 데이터북 L.e 의 전 레벨 그룹에서 「(자동 지정)」 줄을 열거해 같은 spec 을 등록한다.
            seqs = {lv: [r for _n, r in sorted(rows, key=lambda x: x[0]) if r.get('m_BuffTargetType') in auto_types]
                    for lv, rows in levels.items()}
            base = min(seqs)
            rows = seqs[base]
            where = '%s %s' % (key, s['sl'])
            has_levelup_auto = any(v for lv, v in seqs.items() if lv != base)
            if not any(r.get('AutoTargetId') for r in rows):
                continue
            lines = [ln for ln in s.get('ef') or [] if is_auto_line(ln)]
            if len(lines) != len(rows):
                # 데이터북은 묶음 번호(SEGroupID)만 다른 같은 행을 한 줄(「×5」·「N회 부여」)로 합쳐 적는다 — 첫 행만 남겨 다시 짝짓는다
                rows = _dedup_se(rows)
            if len(lines) != len(rows):
                report['자동 지정 줄 수 불일치(제외): ' + where] += 1
                continue
            got = []
            for ln, r in zip(lines, rows):
                tt = r['m_BuffTargetType']
                if not client and not legacy and bu['v'] != '기본' and tt == 'NSETT_AUTO_ALLY_ONE_NOT_SELF':
                    # 3월판 근거의 옛 동작 재현: 개화 연결에서 설명문 선택을 유지한다.
                    # not_self 우선 필터로 대체하면 아군이 혼자일 때 자신을 다시 선택하게 된다.
                    report['옛 data 모드 개화 대상형 제외(설명문 유지): ' + where] += 1
                    continue
                head = _skip_paren(ln.split(']', 1)[-1].lstrip())
                described = described_auto(ln)
                ally = described['ally'] if described else not head.startswith('적')
                one = described['one'] if described else '1명' in head.split('(자동 지정)')[0]
                if ally != tt.startswith('NSETT_AUTO_ALLY') or one != tt.endswith(('_ONE', '_ONE_NOT_SELF')):
                    got = None
                    break
                if r.get('AutoTargetId') and (tt in FA.AUTO_ENEMY or tt in FA.AUTO_ALLY or tt == 'NSETT_AUTO_ALLY_ONE_NOT_SELF'):
                    try:
                        spec = {'one': FA.AUTO_ENEMY.get(tt, FA.AUTO_ALLY.get(tt, True)), 'f': FA.filters(target.get(r['AutoTargetId']), bname)}
                    except FA.Unknown as ex:
                        report['모르는 필터(그 줄 제외): %s %s' % (where, ex)] += 1
                        continue
                    if tt.startswith('NSETT_AUTO_ALLY'):
                        spec['ally'] = True
                    if tt == 'NSETT_AUTO_ALLY_ONE_NOT_SELF':
                        if client:
                            spec['exclude_self'] = True
                        elif 'not_self' not in spec['f']:
                            spec['f'] = ['not_self'] + spec['f']
                    got.append([s['sl'], ln, spec])
            if got is None:
                report['아군/적·1명/전체 불일치(제외): ' + where] += 1
                continue
            if got:
                out.setdefault(key, []).extend(got)
            # 레벨업 추가 행에도 자동 지정이 있는 스킬: 데이터북 L.e 전 레벨 그룹에서 「(자동 지정)」 줄을
            # 같은 spec(기본 묶음 필터)으로 등록한다. 줄 수가 다른 그룹은 건너뛴다(보고만).
            if has_levelup_auto and got:
                specs = [g[2] for g in got]
                L = s.get('L')
                if L and 'e' in L and 'ln' in L:
                    seen = {g[1] for g in out.get(key, [])}   # 이미 등록된 원문
                    for gi, grp in enumerate(L['e']):
                        grp_lns = [L['ln'][j] for j in grp if j < len(L['ln'])]
                        grp_auto = [ln for ln in grp_lns if is_auto_line(ln)]
                        if len(grp_auto) != len(specs):
                            report['레벨 그룹 %d 자동 지정 줄 수 불일치(생략): %s' % (gi, where)] += 1
                            continue
                        for ln, spec in zip(grp_auto, specs):
                            if ln not in seen:
                                out[key].append([s['sl'], ln, spec])
                                seen.add(ln)
    return out


def build_self_enforce(static, report):
    """구원자 자신 추가 발동(BI_ENFORCE, NSETT_SELF)의 적 대상 규칙 -> {구원자 key: [[칸, 데이터북 원문, {slot, eat, f, cool, cond}]]}.
    EnforceAutoTargetId 0 = 규칙 1(구원자, NKM.decompiled.cs:5014-5030). 기본/개화는 form_bindings 연결.
    한 스킬의 자신 enforce 행 규칙이 하나뿐이면 그 스킬의 «자신에게 … 추가 발동» 줄 전부(레벨 그룹 원문 포함)에, 여럿이면 줄 수가 같을 때만 순서대로."""
    from tools import build_foe_auto as FA
    tables = Path(static) / 'tables'
    target = {r['Id']: r['TargetCondition'] for r in jsonc(tables / 'Plain' / 'AUTO_SKILL_TARGET_TEMPLET.json')['Data']}
    bname = buff_names(tables)
    se = {}
    for n in (1, 2):
        for r in json.loads((tables / ('SE_TEMPLET_SKILL_%d.json' % n)).read_text(encoding='utf-8'))['Data']:
            m = re.match(r'^COND_(.+)_(\d+)_(\d+)$', r.get('m_SEStrID') or '')
            if m:
                se.setdefault(m.group(1), []).append(((int(m.group(2)), int(m.group(3))), r))
    index = json.loads((ROOT / 'data' / 'saviors_index.json').read_text(encoding='utf-8'))
    keys = keys_by_id(index)
    book = json.loads((ROOT / 'rawdata' / 'databook_main.json').read_text(encoding='utf-8'))['units']
    slot_of = {'기본기': 0, '특수기': 1, '궁극기': 2, '고유 패시브': 3}
    out = {}
    for key, bu, _u, skill_ids in form_bindings(tables, keys, book):
        for s in bu['sk']:
            i = slot_of.get(s['sl'])
            if i is None or i >= len(skill_ids):
                continue
            sid = skill_ids[i].replace('NKM_UNIT_', '', 1)
            rows = se.get(sid) or se.get(sid.replace('S_', '', 1)) or []
            rows = [r for _n, r in sorted(rows, key=lambda x: x[0]) if FA.is_self_enforce(r)]
            if not rows:
                continue
            where = '%s %s' % (key, s['sl'])
            try:
                specs = [FA.self_enforce_spec(r, target, bname, 1) for r in rows]
            except FA.Unknown as ex:
                report['자신 추가 발동 모르는 어휘(제외): %s %s' % (where, ex)] += 1
                continue
            cands = list(s.get('ef') or [])
            L = s.get('L') or {}
            cands += [ln for ln in L.get('ln') or [] if ln not in cands]
            lines = [(ln, FA.RX_SELF_EXTRA.match(FA.effect_part(ln))) for ln in cands]
            lines = [(ln, m.group(1)) for ln, m in lines if m]
            # 같은 대상 규칙인데 행마다 재발동 제한·조건 번호만 다른 경우(오메가 파워업 스타 1~3중첩 5행 ↔ 데이터북 3줄)는 대상 규칙 하나로 보고
            # cool·cond 는 None(여러 값)으로 둔다 — 엔진은 대상 규칙만 쓰고, cool·cond 는 표 대조용
            core = {json.dumps({k: sp[k] for k in ('slot', 'eat', 'f')}, sort_keys=True, ensure_ascii=False) for sp in specs}
            uniq = [json.loads(x) for x in sorted({json.dumps(sp, sort_keys=True, ensure_ascii=False) for sp in specs})]
            if len(uniq) > 1 and len(core) == 1:
                uniq = [dict(json.loads(core.pop()), cool=None, cond=None)]
            if not lines:
                report['자신 추가 발동 줄 없음(데이터북 미해석): ' + where] += 1
                continue
            # 문구의 시전 칸과 표의 EnforceSkillIndex 칸이 같아야 연결(오연결 방지)
            if len(uniq) == 1 and all(sl == uniq[0]['slot'] for _ln, sl in lines):
                pairs = [(ln, uniq[0]) for ln, _sl in lines]
            elif len(uniq) > 1 and len(lines) == len(specs) and all(sl == sp['slot'] for (_ln, sl), sp in zip(lines, specs)):
                pairs = [(ln, sp) for (ln, _sl), sp in zip(lines, specs)]
            else:
                report['자신 추가 발동 규칙 여럿·줄 수·칸 불일치(제외): ' + where] += 1
                continue
            out.setdefault(key, []).extend([s['sl'], ln, sp] for ln, sp in pairs)
    return out


def build_no_preemptive(static):
    """build 26314877의 버프/스킬 NoPreemptiveDefend를 공개 이름·칸으로 연결."""
    tables = Path(static) / 'tables'
    strings = json.loads((tables / 'Strings/STRING_COMMON_ko_en.json').read_text(encoding='utf8'))
    buffs = sorted({strings[r['m_BuffName']]['ko']
                    for r in json.loads((tables / 'BUFF_TEMPLET.json').read_text(encoding='utf8'))['Data']
                    if r.get('NoPreemptiveDefend')})
    skills = {r['m_SkillStrID']: r for n in (1, 2) for r in json.loads(
        (tables / ('SKILL_TEMPLET_%d.json' % n)).read_text(encoding='utf8'))['Data']}
    index = json.loads((ROOT / 'data/saviors_index.json').read_text(encoding='utf8'))
    keys = keys_by_id(index)
    book = json.loads((ROOT / 'rawdata/databook_main.json').read_text(encoding='utf8'))['units']
    out = {}
    for key, _bu, _u, ids in form_bindings(tables, keys, book):
        slots = [slot for slot, sid in zip(SLOTS, ids) if skills[sid].get('NoPreemptiveDefend')]
        if slots:
            out[key] = slots
    # 현 표의 적 스킬에는 플래그가 없음. 생기면 적 스킬 매핑도 구현해야 함.
    flagged = {sid for sid, sk in skills.items() if sk.get('NoPreemptiveDefend')}
    mapped = {sid for _k, _b, _u, ids in form_bindings(tables, keys, book) for sid in ids}
    if flagged - mapped:
        raise ValueError('NoPreemptiveDefend 스킬 매핑 확대 필요')
    return {'buffs': buffs, 'skills': dict(sorted(out.items()))}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--static', type=Path)
    args = ap.parse_args()
    try:
        static = static_path(args.static)
    except ValueError as ex:
        ap.error(str(ex))
    low_priority()
    units, order = build(static)
    from collections import Counter
    report = Counter()
    lines = build_lines(static, Counter(), legacy=True)
    variant_lines = build_lines(static, report)
    client_lines = build_lines(static, Counter(), legacy=True, client=True)
    client_variant_lines = build_lines(static, report, client=True)
    out = dict(_note='구원자 스킬별 자동 전투 규칙(tools/build_auto_skill.py). 규칙 행 = 조건(c, 모두 참) + 대상 필터(f, 차례로 거름). '
                     '참인 행이 없으면 그 스킬을 건너뜀. 여기 없는 스킬은 엔진 기본 규칙(구원자 1).',
               units=dict(sorted(units.items())),
               order_note='오토 스킬 시도 순서(UNIT_TEMPLET_BASE1.SkillOrderList). 여기 없는 구원자는 기본 순서 궁극기->특수기->기본기',
               order=dict(sorted(order.items())),
               lines_note='옛 구원자 효과 줄 자동 대상(SE AutoTargetId): lines[구원자 key] = [[칸, 데이터북 원문, {one 1명, ally 내 편, f 필터}]]. '
                          'mc.ally_variant_mapping=legacy 재현용. 없는 줄은 엔진 설명문 근사(mc.ally_auto_lines=data 일 때만 씀)',
               lines=dict(sorted(lines.items())),
               variant_lines_note='형태별 자동 대상: 기본은 UNIT_TEMPLET_BASE1, 개화는 BLOSSOM_TEMPLET의 스킬에 연결. '
                                  'mc.ally_variant_mapping=data에서 사용. lines는 legacy 재현용.',
               variant_lines=dict(sorted(variant_lines.items())),
               client_lines_note='build 26314877 자동 대상. exclude_self는 필터 전에 시전자 제거. '
                                 'mc.ally_auto_lines=client에서 사용하며 client_lines는 옛 형태 연결, client_variant_lines는 기본/개화 연결.',
               client_lines=dict(sorted(client_lines.items())),
               client_variant_lines=dict(sorted(client_variant_lines.items())),
               no_preemptive=build_no_preemptive(static),
               self_enforce_note='자신이 시전하는 추가 발동(BI_ENFORCE, NSETT_SELF)의 적 대상: self_enforce[구원자 key] = [[칸, 데이터북 원문, '
                                 '{slot, eat = EnforceAutoTargetId(0 이면 1), f 필터, cool = SeCoolTurn, cond = SkillConditionId}]]. mc.self_enforce_target=client 에서 사용',
               self_enforce=dict(sorted(build_self_enforce(static, report).items())))
    atomic_text(ROOT / 'data' / 'auto_skill.json', json.dumps(out, ensure_ascii=False, separators=(',', ':')) + '\n')
    print('auto_skill.json: 구원자', len(units), '스킬', sum(len(v) for v in units.values()), '스킬 순서', len(order),
          '효과 줄 자동 대상', sum(len(v) for v in variant_lines.values()), '(구원자 %d)' % len(variant_lines))
    for k, v in sorted(report.items()):
        print('  ', v, k)


if __name__ == '__main__':
    main()
