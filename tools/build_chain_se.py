"""Connect verified chain lines to native BuffId groups (PC 26752678).

units: 크리스텔·아세라 연쇄 줄(전 레벨). foes: 적 정의의 연쇄 줄 — tools/foe_se_link 의 유닛·스킬·줄 짝짓기로
찾은 SE 행이 계수·능력치 기준·피해 유형·발동 확률까지 같을 때만. fixed: 엔진의 고정 피해·응징 예약의 원형 BuffId.
NKM:6085-6109(SE→추가 피해 버프, AutoTarget 조건 0개면 재선택), 6244-6284(BuffId 묶음 처리).
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from battlesim.starsavior.data import get_db
from battlesim.starsavior.parser import Line
from collections import Counter
from tools.tables import jsonc


def build(tables):
    tables = Path(tables)
    rows = [r for n in (1, 2) for r in jsonc(tables / f'CLIENT_SE_TEMPLET_SKILL_{n}.json')['Data']]
    buffs = {r['m_BuffStrID']: r['m_BuffID'] for r in jsonc(tables / 'CLIENT_BUFF_TEMPLET.json')['Data']}
    targets = {r['Id']: r['TargetCondition'] for r in jsonc(tables / 'plain/AUTO_SKILL_TARGET_TEMPLET.json')['Data']}
    out = {}
    for key in ('cristelle', 'asherah-order-striker'):
        result = []
        for sk in get_db().units[key]['sk']:
            for raw in dict.fromkeys(sk.get('ef', []) + sk.get('L', {}).get('ln', [])):
                ln = Line(raw, sk['sl'], 'passive' if sk['sl'] == '고유 패시브' else 'active')
                if ln.eff['kind'] != 'chain':
                    continue
                params = dict(ln.params)
                if key == 'cristelle':
                    cond = 32157 + int(params['효과 개수 이상']) if sk['sl'] == '궁극기' else 31066
                    prefix = 'COND_INCOGNITA_LANDGRAVE_'
                    auto = None
                else:
                    prefix = 'COND_DARK_UNKNOWN_'
                    single = params.get('단일 대상 공격') == '예'
                    boss = ln.eff['coef'] >= 1
                    cond = (52200 if boss else 2171) if single else 2172
                    auto = None if single else (10611 if boss else 55)
                candidates = [r for r in rows if r.get('m_SEStrID', '').startswith(prefix)
                              and r.get('SkillConditionId') == cond and r.get('AutoTargetId') == auto
                              and r.get('AddDamageRate') == round(ln.eff['coef'] * 10000)]
                specs = set()
                for r in candidates:
                    assert r['AddDamageTargetType'] == 'NSETT_SELF' and r['AddDamageStatType'] == 'NST_ATK'
                    assert r['m_Condition']['m_fActiveRate'] == 10000
                    retarget = auto is not None and not targets[auto]
                    assert not retarget, 'Retargeting requires a separate verified mapping'
                    specs.add((buffs[r['m_BuffStrID']], retarget))
                if len(specs) != 1:
                    raise ValueError((key, raw, specs))
                bid, retarget = specs.pop()
                result.append([sk['sl'], raw, {'buff': bid, 'retarget': retarget}])
        assert len(result) == (6 if key == 'cristelle' else 12), (key, len(result))
        out[key] = result
    return out


STAT = {'atk': ('NSETT_SELF', 'NST_ATK'), 'hp': ('NSETT_SELF', 'NST_HP'), 'def': ('NSETT_SELF', 'NST_DEF'),
        'target_atk': ('NSETT_TARGET', 'NST_ATK'), 'target_def': ('NSETT_TARGET', 'NST_DEF'), 'target_hp': ('NSETT_TARGET', 'NST_HP')}


def chain_row_spec(eff, r, tb):
    """연쇄 효과 줄과 SE 행이 같은지 검사해 (spec, None) 또는 (None, 거절 사유)."""
    if not r.get('AddDamageRate') or r.get('AddTrueDamageValue'):
        return None, '원형 SE가 능력치 추가 피해 아님'
    if (r.get('AddDamageTargetType'), r.get('AddDamageStatType')) != STAT.get(eff['stat']):
        return None, '능력치 기준 다름'
    if r['AddDamageRate'] != round(eff['coef'] * 10000):
        return None, '계수 다름'
    if bool(r.get('AddTrueDamageByStat')) != (eff.get('damage_type') == 'ADT_STAT_TRUE'):
        return None, '피해 유형(ADT_STAT_TRUE) 다름'
    # NT:41933 m_fActiveRate 기본 10000(표에 칸이 없으면 항상 발동).
    rate = (r.get('m_Condition') or {}).get('m_fActiveRate', 10000)
    if rate != round(eff.get('chance', 1) * 10000):
        return None, '발동 확률 다름'
    info = tb.buff.get(r.get('m_BuffStrID'))
    if info is None:
        return None, '버프 행 없음'
    auto = r.get('AutoTargetId')
    retarget = bool(auto) and not tb.target.get(auto)
    return {'buff': info['m_BuffID'], 'retarget': retarget}, None


def _head_ok(line, r):
    """효과 부분(조건 괄호 뒤)의 대상 머리말이 SE m_BuffTargetType 과 같은 종류인지(build_foe_auto.HEAD)."""
    from tools import build_foe_auto as FA
    import re
    part = FA.effect_part(line)
    for pat, kinds in FA.HEAD:
        if re.search(pat, part):
            return r.get('m_BuffTargetType') in kinds and ('자동 지정' in part) == (r.get('m_BuffTargetType') or '').startswith('NSETT_AUTO')
    return False


def unit_chain(u, raw, gu, tb, report):
    from tools import build_foe_auto as FA
    from tools.foe_se_link import skill_pairs
    out = {}
    for si, sid in skill_pairs(u, raw, gu, tb.skills):
        sd = raw['s'][si]
        slot = sd['sl']
        src = 'passive' if slot == '패시브' else ('trigger' if sd.get('ty') == '트리거' else 'active')
        ef = sd.get('ef') or []
        chain = {i for i, x in enumerate(ef) if Line(x, slot, src).eff['kind'] == 'chain'}
        if not chain:
            continue
        rows_se = tb.se.get(sid) or []
        pairs = FA.pair_lines(ef, rows_se)
        if pairs is None:
            # 전체 줄 짝짓기가 안 되면(«×2» 해제 줄·조건 속 대상 낱말 등) 연쇄 줄과 추가 피해 SE 행만 순서대로 대응.
            # 수가 같고 줄마다 대상 머리말·계수·능력치·유형·확률이 모두 같을 때만 쓴다.
            add_rows = [r for r in rows_se if r.get('AddDamageRate') or r.get('AddTrueDamageValue')]
            idx = sorted(chain)
            if len(add_rows) != len(idx) or not all(_head_ok(ef[i], r) for i, r in zip(idx, add_rows)):
                report['줄 짝짓기 실패(즉시 실행 유지)'] += len(chain)
                continue
            pairs = list(zip(idx, add_rows))
            report['연쇄 줄만 순서 대응'] += len(idx)
        for i, r in pairs:
            if i not in chain:
                continue
            spec, why = chain_row_spec(Line(ef[i], slot, src).eff, r, tb)
            k = (slot, ef[i])
            if spec is None:
                report['원형 불일치: ' + why] += 1
                out[k] = None
            elif out.get(k, spec) != spec:
                out[k] = None
                report['같은 줄에 다른 BuffId(제외)'] += 1
            elif k not in out:
                out[k] = spec
    return out


def build_foes(static):
    from tools.foe_se_link import Tables, links
    tb = Tables(static)
    raw, linked = links(tb)
    report = Counter()
    out = {}
    for key, (u, gids) in sorted(linked.items()):
        variants = {json.dumps(sorted([list(k), v] for k, v in unit_chain(u, raw, tb.units[g], tb, report).items()),
                               ensure_ascii=False) for g in gids}
        if len(variants) != 1:
            report['게임 유닛별 결과 다름(제외)'] += 1
            continue
        rows = [[k[0], k[1], v] for k, v in json.loads(variants.pop()) if v is not None]
        if rows:
            out[key] = rows
    return out, dict(report)


def build_fixed(tables):
    """엔진 고정 피해·응징 예약의 원형 BuffId. 행 내용이 기대와 다르면 실패."""
    tables = Path(tables)
    rows = {r['m_SEID']: r for n in (1, 2) for r in jsonc(tables / f'CLIENT_SE_TEMPLET_SKILL_{n}.json')['Data']}
    rows.update({r['m_SEID']: r for r in jsonc(tables / 'CLIENT_SE_TEMPLET_BATTLE_EFFECT.json')['Data']})
    buffs = {r['m_BuffStrID']: r['m_BuffID'] for r in jsonc(tables / 'CLIENT_BUFF_TEMPLET.json')['Data']}
    # 벨그라스(일반 스테이지·코스모) 궁극기 시작 자기 고정 피해: SE930082301..350, 중첩 n당 5000.
    hyper = {rows[930082300 + n]['m_BuffStrID'] for n in range(1, 51)}
    for n in range(1, 51):
        r = rows[930082300 + n]
        assert (r['AddTrueDamageValue'], r['m_BuffTargetType'], r['m_Condition']['m_ActiveType']) == (5000 * n, 'NSETT_SELF', 'NSEAT_SKILL_START'), n
    assert len(hyper) == 1
    # 코스모 EX 응징(SET_31): SE9403101, 공격력 30%, AutoTargetId 10(조건 있음 → 재선택 없음).
    p = rows[9403101]
    assert (p['AddDamageRate'], p['AddDamageStatType'], p['AutoTargetId']) == (3000, 'NST_ATK', 10)
    return {'belgras_hyper': buffs[hyper.pop()], 'cosmo_punish': buffs[p['m_BuffStrID']]}


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--tables', required=True, type=Path, help='rebuild_26752678/T (CLIENT_ 접두)')
    ap.add_argument('--view', required=True, type=Path, help='tools/client_view.py 출력 폴더(같은 T에서 만든 것)')
    args = ap.parse_args()
    foes, report = build_foes(args.view)
    data = {'_note': 'PC 26752678. units/foes: (칸, 원문, {buff: 원형 BuffId, retarget: 처리 도중 사망 시 재선택}). '
                     'fixed: 엔진 고정 피해·응징 예약의 원형 BuffId. tools/build_chain_se.py',
            'units': build(args.tables), 'foes': foes, 'fixed': build_fixed(args.tables), 'report': report}
    (ROOT / 'data/chain_se.json').write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n', encoding='utf8')
    print({k: len(v) for k, v in data['units'].items()}, '적', len(foes), '줄', sum(len(v) for v in foes.values()), report)
