# -*- coding: utf-8 -*-
"""적 반응(트리거) 스킬 발동 조건 -> data/foe_react.json (공개 저장소에는 가공 어휘만).

게임 코드(NKM.decompiled.cs 8097~8160 ReactSkillBooking): 시전자 사망·쿨·행동 불가면 취소.
SKILL_TEMPLET(NST_REACT) + ReactConditionID -> SKILL_CONDITION_TEMPLET(tables/Plain):
- AfterMyAttack: 적의 공격 뒤 발동
- MyEffectiveHit: 적의 유효 타격 시 발동
조건 어휘: 자기 버프 보유/미보유·스택 수·대상 버프 보유·대상 미제거·기본기 여부·단일 대상 여부.
데이터북 적 <-> 게임 유닛 연결은 tools/build_foe_auto.py 와 같은 방식(tools/build_foe_spawn 의 스테이지 배치).
모르는 어휘는 건너뛰고 보고(조용히 근사 금지).

사용: python -X utf8 -I tools/build_foe_react.py [--static <비공개 저장소>]
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
from tools.build_foe_auto import ROLE, ELEM   # noqa: E402
from battlesim.fileio import atomic_text   # noqa: E402
from battlesim.starsavior import foe as F   # noqa: E402

SLOT = {'ATTACK': '기본기', 'SPECIAL': '특수기', 'HYPER': '궁극기'}
TARGET_TYPE = {'NSTT_REACT_ENEMY_TARGET': 'react_target', 'NSTT_ENEMY_ALL': 'all', 'NSTT_MYSELF': 'self',
               'NSTT_REACT_ALLY_TARGET': 'react_ally_target', 'NSTT_ALLY_ALL': 'ally_all'}
TIMING = {'AfterMyAttack': 'after_attack', 'MyEffectiveHit': 'hit',
          'AfterAllyAttack': 'after_ally_attack', 'OnMyAttack': 'on_my_attack',
          'AllyEffectiveHit': 'ally_hit'}
SKILL_IDX = {'NSI_SKILL_1_ATTACK': 'basic', 'NSI_SKILL_2_SPECIAL': 'special', 'NSI_SKILL_3_HYPER': 'hyper'}
REPORT = Counter()


class Unknown(Exception):
    pass


def buff_names(tables):
    strings = json.loads((tables / 'Strings' / 'STRING_COMMON_ko_en.json').read_text(encoding='utf-8'))
    out = {}
    for r in json.loads((tables / 'BUFF_TEMPLET.json').read_text(encoding='utf-8'))['Data']:
        ko = (strings.get(r.get('m_BuffName') or '') or {}).get('ko')
        if ko:
            out[r['m_BuffStrID']] = ko
    return out


def names_of(ids, bname):
    out = []
    for i in ids:
        n = bname.get(i)
        if not n:
            raise Unknown('buff name missing: ' + i)
        if n not in out:
            out.append(n)
    return out


def translate_conds(timing_data, bname):
    out = []
    d = dict(timing_data)
    si = d.pop('SkillIndex', None)
    if si:
        tag = SKILL_IDX.get(si)
        if tag:
            out.append(['skill_' + tag])
        else:
            return None
    # IncludeSelf (AfterAllyAttack / AllyEffectiveHit): false = 자기 행동에는 발동 안 함
    inc_self = d.pop('IncludeSelf', None)
    if inc_self is not None:
        out.append(['include_self', bool(inc_self)])
    if d.pop('IsSingleEnemyTargetType', False):
        out.append(['single_target'])
    if d.pop('IsSingleAllyTargetType', False):
        out.append(['single_ally_target'])
    # DamageResultType: ['NormalHit', 'CriticalHit', 'Evade'] 중 일치하는 것
    drt = d.pop('DamageResultType', None)
    if drt:
        out.append(['damage_result', list(drt)])
    self_buffs = d.pop('SelfBuffStrId', None)
    stack_eq = d.pop('SelfBuffLevelCount', None)
    stack_ge = d.pop('SelfBuffLevelCountOver', None)
    if self_buffs:
        try:
            ns = names_of(self_buffs, bname)
        except Unknown:
            return None
        if stack_eq is not None:
            if len(ns) != 1:
                return None
            out.append(['self_stack_eq', ns[0], int(stack_eq)])
        elif stack_ge is not None:
            if len(ns) != 1:
                return None
            out.append(['self_stack_ge', ns[0], int(stack_ge)])
        else:
            out.append(['self_has', ns])
    not_self = d.pop('NotSelfBuffStrId', None)
    if not_self:
        try:
            ns = names_of(not_self, bname)
        except Unknown:
            return None
        out.append(['self_not_has', ns])
    tgt_buffs = d.pop('TargetBuffStrId', None)
    if tgt_buffs:
        try:
            ns = names_of(tgt_buffs, bname)
        except Unknown:
            return None
        out.append(['target_has', ns])
    if d.pop('NotEliminateEnemy', False):
        out.append(['not_eliminate'])
    if d.pop('EliminateEnemy', False):
        out.append(['eliminate'])
    # 대상 강화/약화 효과 보유 여부
    if d.pop('TargetNegativeBuff', False):
        out.append(['target_neg_buff'])
    if d.pop('TargetPositiveBuff', False):
        out.append(['target_pos_buff'])
    if d.pop('SelfPositiveBuff', False):
        out.append(['self_pos_buff'])
    if d.pop('SelfNegativeBuff', False):
        out.append(['self_neg_buff'])
    if d:
        return None
    return out


def build(static):
    tables = Path(static) / 'tables'
    bname = buff_names(tables)
    cond_table = {}
    for r in jsonc(tables / 'Plain' / 'SKILL_CONDITION_TEMPLET.json')['Data']:
        cond_table[r['Id']] = r
    react_by_sid = {}
    for n in (1, 2):
        for r in json.loads((tables / ('SKILL_TEMPLET_%d.json' % n)).read_text(encoding='utf-8'))['Data']:
            if r.get('m_NKM_SKILL_TYPE') != 'NST_REACT':
                continue
            sid = r.get('m_SkillStrID', '')
            m = re.search(r'_(ATTACK|SPECIAL|HYPER)\d*$', sid)
            if not m:
                continue
            if re.search(r'_(ATTACK|SPECIAL|HYPER)\d+$', sid):
                continue
            tt = TARGET_TYPE.get(r.get('m_TARGET_TYPE', ''))
            if tt is None:
                REPORT['target type unknown: ' + r.get('m_TARGET_TYPE', '')] += 1
                continue
            react_by_sid[sid] = dict(slot=SLOT[m.group(1)], cond_id=r.get('ReactConditionID'), target=tt)
    gunits = {}
    for n in (1, 2, 3, 4):
        for u in json.loads((tables / ('UNIT_TEMPLET_BASE%d.json' % n)).read_text(encoding='utf-8'))['Data']:
            gunits[u['m_UnitStrID']] = u
    raw = F.load_foe(str(ROOT))
    rows = SP.battle_rows(static)
    link = defaultdict(set)
    for c in raw['g']:
        for ti, t in enumerate(c['tabs']):
            for si, s in enumerate(t['s']):
                hits = []
                cands = SP.candidates(c['k'], t['t'], s['n'], ti, si, rows)
                for cid in cands:
                    row = rows.get(cid)
                    if not row or not row[0].exists() or not SP.same_battle(c['k'], s, row, raw, static):
                        continue
                    waves = (SP.jsonc(row[0]).get('Data') or {}).get('Waves') or []
                    lists = [[[sp['UnitStrId'], sp.get('ChangeAdjustType')] for sp in (w.get('TeamBSpawnList') or [])] for w in waves]
                    if [len(x) for x in lists] != [len(w) for w in s['w']]:
                        continue
                    hits.append(lists)
                if len({json.dumps(h) for h in hits}) != 1:
                    continue
                for w, lw in zip(s['w'], hits[0]):
                    for e, (gid, cadj) in zip(w, lw):
                        ui, xi = e[0], (e[1] if len(e) > 1 else None)
                        u_raw, gu = raw['u'][ui], gunits.get(gid)
                        x = raw['x'][xi] if xi is not None else None
                        if gu is None:
                            continue
                        el = (x and x.get('el')) or u_raw['el']
                        g_el = ELEM.get(cadj if cadj and cadj != 'NUAT_INVALID' else gu.get('NKM_UNIT_ADJUST_TYPE'))
                        if ROLE.get(gu.get('m_NKM_UNIT_ROLE_TYPE')) != u_raw['r'] or g_el != el:
                            continue
                        link[(ui, xi)].add(gid)
    out = {}
    for (ui, xi), gids in sorted(link.items(), key=lambda kv: (kv[0][0], -1 if kv[0][1] is None else kv[0][1])):
        u = raw['u'][ui]
        db_trigger = {}
        for si_idx in u['sk']:
            sd = raw['s'][si_idx]
            if sd['ty'] == '트리거':
                db_trigger[sd['sl']] = sd['n']
        if not db_trigger:
            continue
        variants = []
        for gid in sorted(gids):
            gu = gunits[gid]
            rules = {}
            for sk_sid in gu.get('m_listSkill') or []:
                rsk = react_by_sid.get(sk_sid)
                if rsk is None:
                    continue
                slot = rsk['slot']
                if slot not in db_trigger:
                    REPORT['slot mismatch'] += 1
                    continue
                cond_id = rsk['cond_id']
                cr = cond_table.get(cond_id) if cond_id else None
                if cr is None:
                    if cond_id:
                        REPORT['cond ID missing: %d' % cond_id] += 1
                    continue
                timing, timing_data = None, None
                for tk, tv in TIMING.items():
                    if tk in cr and cr[tk]:
                        timing, timing_data = tv, cr[tk]
                        break
                if timing is None:
                    REPORT['timing unknown'] += 1
                    continue
                conds = translate_conds(timing_data, bname)
                if conds is None:
                    REPORT['cond vocab unknown'] += 1
                    continue
                rules[slot] = dict(timing=timing, conds=conds, target=rsk['target'])
            variants.append(json.dumps(rules, ensure_ascii=False, sort_keys=True))
        if not variants or len(set(variants)) != 1:
            if len(set(variants)) > 1:
                REPORT['same unit different rules'] += 1
            continue
        rules = json.loads(variants[0])
        if rules:
            key = 'foe:%d' % ui + (':%d' % xi if xi is not None else '')
            out[key] = rules
    return out


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
    note = ('react rules for foe trigger skills (tools/build_foe_react.py). '
            'units[foe:N[:M]][slot] = {timing, conds, target}. '
            'timing: after_attack / hit / after_ally_attack / on_my_attack / ally_hit. '
            'target: react_target / all / self / react_ally_target / ally_all. '
            'conds: self_has/self_not_has/self_stack_ge/self_stack_eq/target_has/not_eliminate/eliminate'
            '/skill_basic/skill_special/skill_hyper/single_target/single_ally_target'
            '/include_self/damage_result/target_neg_buff/target_pos_buff/self_pos_buff/self_neg_buff.')
    doc = dict(_note=note, units=units)
    atomic_text(ROOT / 'data' / 'foe_react.json', json.dumps(doc, ensure_ascii=False, separators=(',', ':')) + '\n')
    n_rules = sum(len(v) for v in units.values())
    print('foe_react.json:', len(units), 'units,', n_rules, 'rules')
    for k, v in REPORT.most_common():
        print(' ', v, k)


if __name__ == '__main__':
    main()