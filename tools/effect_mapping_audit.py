# -*- coding: utf-8 -*-
"""엔진이 쓰는 공개 설명문 효과 줄 ↔ 클라 원형 SE 행 기계 대조(PC 26752678, 계정 자료 없음).

범위: 구원자 전 형태(기본·개화)의 전 스킬 레벨, 현행 콘텐츠 적 전원(일반·코스모·길드·격전 스테이지).
연결(추정 없음):
- 구원자: build_auto_skill.form_bindings(UNIT_TEMPLET_BASE1.m_listSkill / BLOSSOM_TEMPLET.BlossomListSkill),
  레벨 k 의 줄 = 데이터북 L.e[L.ei[k-1]](myinfo_combat.select_skills 와 같음) ↔ SKILL_LEVEL_GROUP_TEMPLET k 의 SkillLevelSE.
- 적: tools/foe_se_link(스테이지 배치로 게임 유닛 연결, 스킬 칸 대응, 단일 레벨 SkillLevelSE).
- 줄: build_foe_auto.pair_lines(줄 수·대상 머리말이 모두 맞을 때만). 안 맞는 스킬은 «대응 미증명»으로 센다.
대조 항목(짝지은 줄마다): 연쇄 계수·능력치·피해 유형, 이번 스킬 보정 수치, 행동 게이지, 쿨 감소, 버프 이름,
지속 턴, 반복 부여 횟수, 발동 확률, 효과 적중 판정, 추가 발동 칸, 이름 지정 해제 대상.
SE 기본값은 클라 로더 ST:29248-29330(m_fBuffActiveRate 10000, RepeatBuffCount 1, m_BuffLifeTurn 0)과
NT:41933(m_Condition.m_fActiveRate 10000)을 따른다.

사용: python -X utf8 -I tools/effect_mapping_audit.py --view <client_view 출력> [--json 출력.json]
"""
import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import build_foe_auto as FA   # noqa: E402
from tools.foe_se_link import Tables, links, skill_pairs   # noqa: E402
from tools.tables import buff_names   # noqa: E402
from battlesim.starsavior.parser import Line   # noqa: E402

GAUGE_KINDS = ('gauge',)
STAT_OF = {'atk': ('NSETT_SELF', 'NST_ATK'), 'hp': ('NSETT_SELF', 'NST_HP'), 'def': ('NSETT_SELF', 'NST_DEF'),
           'target_atk': ('NSETT_TARGET', 'NST_ATK'), 'target_def': ('NSETT_TARGET', 'NST_DEF'), 'target_hp': ('NSETT_TARGET', 'NST_HP')}
ENFORCE = {'NSI_SKILL_1_ATTACK': '기본기', 'NSI_SKILL_2_SPECIAL': '특수기', 'NSI_SKILL_3_HYPER': '궁극기'}


def strip_name(n):
    return re.sub(r'\(해제\s*불가\)$', '', (n or '').strip()).strip()


def compare(eff, r, tb, bname):
    """짝지은 (효과 줄, SE 행)의 불일치 목록 [(항목, 엔진 값, 클라 값)]."""
    out = []
    kind = eff['kind']
    cond_rate = (r.get('m_Condition') or {}).get('m_fActiveRate', 10000)
    buff_rate = r.get('m_fBuffActiveRate', 10000)
    if kind == 'chain':
        if (r.get('AddDamageTargetType'), r.get('AddDamageStatType')) != STAT_OF.get(eff['stat']):
            out.append(('연쇄 능력치', eff['stat'], (r.get('AddDamageTargetType'), r.get('AddDamageStatType'))))
        if r.get('AddDamageRate') != round(eff['coef'] * 10000):
            out.append(('연쇄 계수', round(eff['coef'] * 10000), r.get('AddDamageRate')))
        if bool(r.get('AddTrueDamageByStat')) != (eff.get('damage_type') == 'ADT_STAT_TRUE'):
            out.append(('연쇄 피해 유형', eff.get('damage_type'), 'ADT_STAT_TRUE' if r.get('AddTrueDamageByStat') else 'ADT_NORMAL'))
    elif kind == 'local':
        # Stats 한 칸: NKM_STAT_TYPE_RATE 는 만분율(%×100), NKM_STAT_TYPE_VALUE 는 그대로(강인도 피해 등).
        st = [(k, v) for x in r.get('Stats') or [] for k, v in x.items()]
        chance = eff.get('chance', 1)
        full = eff['val'] / chance
        if len(st) == 1:
            k, v = st[0]
            mine = round(full * 100) if k == 'NKM_STAT_TYPE_RATE' else round(full)
            if mine != v:
                out.append(('이번 스킬 보정 수치', mine, v))
        if round(chance * 10000) != cond_rate * buff_rate // 10000:
            out.append(('이번 스킬 보정 발동 확률', round(chance * 10000), (cond_rate, buff_rate)))
    elif kind in GAUGE_KINDS:
        rate = r.get('SpeedGaugeRate')
        if rate is not None and round(abs(eff['val']) * 100) != abs(rate):
            out.append(('행동 게이지', round(eff['val'] * 100), rate))
    elif kind == 'cdr':
        v = r.get('SkillCoolturnDownValue')
        if v is not None and v != eff['val']:
            out.append(('쿨 감소', eff['val'], v))
    elif kind == 'extra_cast':
        slot = ENFORCE.get(r.get('EnforceSkillIndex'))
        if r.get('m_BuffStrID') == 'BI_ENFORCE' and slot and slot != eff['slot']:
            out.append(('추가 발동 칸', eff['slot'], slot))
    elif kind == 'remove':
        sid = r.get('DeleteSpecificBuffStrId')
        if sid and strip_name(bname.get(sid)) and strip_name(bname.get(sid)) != strip_name(eff.get('name')):
            out.append(('해제 대상', eff.get('name'), bname.get(sid)))
    if kind == 'buff' and not eff.get('consume'):
        name = bname.get(r.get('m_BuffStrID'))
        if name and eff.get('name') and strip_name(name) != strip_name(eff['name']):
            out.append(('버프 이름', eff['name'], name))
        life = r.get('m_BuffLifeTurn', 0)
        dur = eff.get('dur')
        if isinstance(dur, (int, float)) and not math.isinf(dur) and dur > 0 and life > 0 and int(dur) != life:
            out.append(('지속 턴', dur, life))
        rep = r.get('RepeatBuffCount', 1)
        if eff.get('times', 1) not in (1, rep) and rep > 1:
            out.append(('반복 부여', eff.get('times', 1), rep))
        chance = round(eff.get('chance', 1) * 10000)
        if chance not in (buff_rate, cond_rate, buff_rate * cond_rate // 10000):
            out.append(('발동 확률', chance, (cond_rate, buff_rate)))
        # NKM:20238-20256: SE 가 EffectHitCheck=false 를 명시하면 생략, 아니면 버프 표의 EffectHitCheck,
        # 같은 편 대상은 판정 없이 적용. 그래서 적 쪽 대상 줄만 비교한다.
        info = tb.buff.get(r.get('m_BuffStrID')) or {}
        hit = bool(info.get('EffectHitCheck')) and r.get('EffectHitCheck', True) is not False
        enemy_side = (r.get('m_BuffTargetType') or '').startswith(('NSETT_TARGET', 'NSETT_ENEMY', 'NSETT_AUTO_ENEMY'))
        if enemy_side and bool(eff.get('judge')) != hit:
            out.append(('효과 적중 판정', bool(eff.get('judge')), hit))
    return out


def pair(lines, rows):
    """pair_lines, 안 되면 «N회 부여» 를 한 행(RepeatBuffCount=N)으로 보고 다시. 반복 수는 compare 가 대조."""
    got = FA.pair_lines(lines, rows)
    if got is None and any(FA.RX_TIMES.search(x) for x in lines):
        got = FA.pair_lines([FA.RX_TIMES.sub('', x) for x in lines], rows)
    return got


def audit_stats(where, lines, slot, src, stats, res):
    """[상시] 능력치 줄 ↔ SKILL_LEVEL_GROUP_TEMPLET.SkillLevelStat(SE 아님). 수치 집합만 대조(능력치 이름 어휘는 쓰지 않음)."""
    from battlesim.starsavior.parser import parse_props
    perm = []
    for x in lines:
        if Line(x, slot, src).kind != 'perm':
            continue
        if ',' in x:     # 쉼표 복합 줄: MC 는 mc_semantics.normalized_definition 처럼 parse_props 로 전부 적용
            perm += [round(v * 100) for v in parse_props(x.split('능력치:', 1)[1])[1].values()]
        else:
            perm.append(round(Line(x, slot, src).eff['val'] * 100))
    perm.sort()
    table = sorted(x.get('SkillLevelStatRate', x.get('SkillLevelStatValue', 0) * 100) for x in stats or [])
    if not perm and not table:
        return
    res['stat_lines'] += len(perm)
    if perm != table:
        res['mismatch'].append(dict(where=where, item='상시 능력치(SkillLevelStat)', line=' / '.join(lines), se='SkillLevelStat',
                                    engine=perm, client=table))


def audit_lines(where, lines, slot, src, rows, tb, bname, res, seen, damage_type='ADT_NORMAL'):
    # [상시] 능력치 줄은 SE 가 아니라 SkillLevelStat 이라 SE 짝짓기에서 뺀다(audit_stats 가 따로 대조).
    lines = [x for x in lines if Line(x, slot, src).kind != 'perm']
    key = (tuple(lines), tuple(r.get('m_SEStrID') for r in rows))
    if key in seen:
        return
    seen.add(key)
    res['skills'] += 1
    pairs = pair(lines, rows)
    if pairs is None:
        res['unpaired'][where.split(' ', 1)[0]] += 1
        res['unpaired_lines'] += len(lines)
        n = sum(int(m.group(1)) if (m := FA.RX_TIMES.search(x)) else 1 for x in lines)
        why = ('SE 행이 더 많음(설명문 생략·합침)' if n < len(rows) else
               '설명문 줄이 더 많음(SE 없는 설명·다른 레벨 합침)' if n > len(rows) else '대상 머리말 불일치')
        res['unpaired_why'][why] += 1
        return
    res['paired_lines'] += len({i for i, _ in pairs})
    for i, r in pairs:
        eff = Line(lines[i], slot, src, damage_type=damage_type).eff
        for item, mine, client in compare(eff, r, tb, bname):
            res['mismatch'].append(dict(where=where, item=item, line=lines[i], se=r.get('m_SEStrID'),
                                        engine=mine, client=client))


def savior_forms(tb):
    from tools.build_auto_skill import form_bindings
    from battlesim.starsavior.savior_ids import keys_by_id
    index = json.loads((ROOT / 'data' / 'saviors_index.json').read_text(encoding='utf-8'))
    book = json.loads((ROOT / 'rawdata/databook_main.json').read_text(encoding='utf-8'))['units']
    return list(form_bindings(Path(tb.static) / 'tables', keys_by_id(index), book))


def level_se(tb):
    t = Path(tb.static) / 'tables'
    by_name = {}
    for n in (1, 2):
        for r in json.loads((t / ('SE_TEMPLET_SKILL_%d.json' % n)).read_text(encoding='utf-8'))['Data']:
            by_name[r['m_SEStrID']] = r
    levels, stats = defaultdict(dict), defaultdict(dict)
    for n in (1, 2):
        for r in json.loads((t / ('SKILL_LEVEL_GROUP_TEMPLET_%d.json' % n)).read_text(encoding='utf-8'))['Data']:
            levels[r['SkillLevelGroupID']][r['SkillLevelValue']] = [by_name[x] for x in r.get('SkillLevelSE') or [] if x in by_name]
            stats[r['SkillLevelGroupID']][r['SkillLevelValue']] = r.get('SkillLevelStat') or []
    return levels, stats


def audit(view):
    tb = Tables(view)
    bname = buff_names(Path(view) / 'tables')
    res = dict(skills=0, stat_lines=0, paired_lines=0, unpaired_lines=0, unpaired=Counter(), unpaired_why=Counter(), mismatch=[], forms=0, foes=0)
    seen = set()
    levels, lstats = level_se(tb)
    slot_ix = {'기본기': 0, '특수기': 1, '궁극기': 2, '고유 패시브': 3}
    # 엔진은 연쇄 피해 유형을 data/chain_damage.json(AddTrueDamageByStat 빌더)으로 Line 에 넘김(parser.py UnitDef).
    from battlesim.starsavior.data import get_db
    engine_units = get_db().units
    for key, bu, _u, skill_ids in savior_forms(tb):
        res['forms'] += 1
        for s in bu['sk']:
            i = slot_ix.get(s['sl'])
            if i is None or i >= len(skill_ids):
                continue
            sk = tb.skills.get(skill_ids[i]) or {}
            lv = levels.get(sk.get('SkillLevelGroup')) or {}
            ls = lstats.get(sk.get('SkillLevelGroup')) or {}
            src = 'passive' if s['sl'] == '고유 패시브' else 'active'
            dtype = next((x.get('chain_damage_type', 'ADT_NORMAL') for x in engine_units.get(key.split('@')[0], {}).get('sk', [])
                          if x['sl'] == s['sl']), 'ADT_NORMAL')
            L = s.get('L') or {}
            if L.get('ei'):
                # Lv1 = SkillLevelSE(1) 전체. Lv k(≥2) = 그 레벨 행(SkillLevelSE(k))만 대조하고, 데이터북 쪽도
                # Lv k 줄 중 Lv k-1 에 없던 줄만 쓴다(레벨 합성 규칙을 가정하지 않음). 행이 없는 레벨은 건너뜀.
                prev = []
                for k, ei in enumerate(L['ei'], 1):
                    rows = lv.get(k) or []
                    full = [L['ln'][j] for j in L['e'][ei]]
                    lines = full if k == 1 else [x for x in full if x not in prev]
                    prev = full
                    audit_stats('savior:%s %s Lv%d' % (key, s['sl'], k), full, s['sl'], src, ls.get(k), res)
                    if not rows:
                        continue
                    audit_lines('savior:%s %s Lv%d' % (key, s['sl'], k), lines, s['sl'], src, rows, tb, bname, res, seen, dtype)
            elif len(lv) == 1:
                audit_lines('savior:%s %s' % (key, s['sl']), s.get('ef') or [], s['sl'], src,
                            next(iter(lv.values())), tb, bname, res, seen, dtype)
            else:
                res['unpaired']['savior'] += 1
    raw, linked = links(tb)
    for fkey, (u, gids) in sorted(linked.items()):
        res['foes'] += 1
        for g in gids:
            for si, sid in skill_pairs(u, raw, tb.units[g], tb.skills):
                sd = raw['s'][si]
                src = 'passive' if sd['sl'] == '패시브' else ('trigger' if sd.get('ty') == '트리거' else 'active')
                audit_lines('foe:%s(%s) %s %s' % (fkey, u.get('n'), sd['sl'], sid), sd.get('ef') or [], sd['sl'], src,
                            tb.se.get(sid) or [], tb, bname, res, seen)
    res['unpaired'] = dict(res['unpaired'])
    res['unpaired_why'] = dict(res['unpaired_why'])
    res['savior_unpaired_skills'] = sum(v for k, v in res['unpaired'].items() if k.startswith('savior:'))
    res['foe_unpaired_skills'] = sum(v for k, v in res['unpaired'].items() if k.startswith('foe:'))
    res['by_item'] = dict(Counter(m['item'] for m in res['mismatch']))
    return res


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--view', required=True, type=Path)
    ap.add_argument('--json', type=Path)
    a = ap.parse_args()
    res = audit(a.view)
    if a.json:
        a.json.write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding='utf-8')
    print({k: v for k, v in res.items() if k != 'mismatch'})
