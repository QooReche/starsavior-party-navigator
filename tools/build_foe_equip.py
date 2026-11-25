"""PC 클라 장비 던전 → 데이터북에 없는 단계만 foe_equip 조각으로 생성.

스테이지 이름/탭은 번역 표, 전투/배치/유닛/스킬/소환은 클라 표에서 읽는다.
알 수 없는 전투 입력이나 변환 못 한 효과는 실패하며 기존 출력은 보존한다.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from battlesim.fileio import atomic_json
from battlesim.starsavior.foe import SK_NST, RATE
from tools.tables import jsonc
from tools.runtime import static_path, low_priority
from tools.build_foe_clash import (Tables, SkillBuilder, SeConverter, db_shapes,
    ROLE, ELEM, ATTACK_KIND, GRADE, SLOT, SKILL_TY, TARGET_TG, clean_markup, fnum, spawn_flag)
from tools.build_foe_auto import filters, conds


def databook(root=ROOT):
    text = (Path(root) / 'rawdata/foe.js').read_text(encoding='utf-8')
    return json.JSONDecoder().raw_decode(text.split('__SSD.foe=', 1)[1])[0]


def build(static, raw=None, *, all_stages=False):
    raw = databook() if raw is None else raw
    tb = Tables(static)
    battles = jsonc(tb.t / 'BATTLE_TEMPLET_NORMAL.json')['Data']
    tabs = jsonc(tb.t / 'BATTLE_TAB_TEMPLET.json')['Data']
    auto = {r['Id']: r for r in jsonc(tb.t / 'Plain/AUTO_SKILL_TEMPLET.json')['Data']}
    return generate(tb, battles, tabs, lambda name: jsonc(tb.t / 'BattleScript' / name.replace('.txt', '.json'))['Data'],
                    auto, raw, all_stages=all_stages)


def generate(tb, battles, tabs, script, auto, raw, *, all_stages=False):
    """표를 주입할 수 있는 변환 핵심. 시험은 비공개 표 대신 합성 고정 입력을 쓴다."""
    out = dict(_note='PC 클라 장비 던전 추가 조각. 데이터북의 같은 탭·단계를 우선함. tools/build_foe_equip.py로 재생성.',
               u=[], s=[], x=[], ak=[], g=[], aux={k: {} for k in ('spawn', 'slots', 'deck', 'summon_groups', 'summon_stages')},
               boss_kill=[])
    existing = {(t['t'], s['n']) for g in raw['g'] if g['k'] == 'equip' for t in g['tabs'] for s in t['s']}
    conv = SeConverter(tb)
    sb = SkillBuilder(tb, conv, db_shapes(raw), False)
    bnames = {k: tb.buff_name(k) for k in tb.buff}
    aks = {a[1]: i for i, a in enumerate(raw['ak'])}
    ui, si, xi = {}, {}, {}

    def ko(key):
        value = tb.ko(key)
        if not value:
            raise ValueError('한국어 문자열 없음: ' + str(key))
        return value

    def skill(sid):
        if sid in si:
            return si[sid]
        sk = tb.skill[sid]
        if sk['m_NKM_SKILL_TYPE'] not in ('NST_ACTIVE', 'NST_PASSIVE'):
            raise ValueError('장비 적 스킬 종류 미지원: ' + sid)
        m = re.search(r'_(ATTACK|SPECIAL|HYPER)$', sid)
        if not m and sk['m_NKM_SKILL_TYPE'] != 'NST_PASSIVE':
            raise ValueError('장비 적 스킬 칸 미지원: ' + sid)
        ef, gl, _, lv = sb.ef_for(sid)
        if sb.unmodeled:
            raise ValueError('장비 적 효과 변환 실패: ' + json.dumps(sb.unmodeled, ensure_ascii=False))
        d = dict(sl=SLOT[m[1]] if m else '패시브', n=ko(sk['m_SkillName']),
                 ty=SKILL_TY[sk['m_NKM_SKILL_TYPE']], tg=TARGET_TG[sk['m_TARGET_TYPE']],
                 cd=sk.get('m_CoolTurn', 0), ab=sk.get('SuperArmorBreakValue', 0),
                 d1=clean_markup(tb.ko(lv.get('SkillLevelDesc'))), ef=ef, gl=gl)
        dt = tb.dt[sk['DTStrID']] if sk.get('DTStrID') else {}
        if any(dt.get(k) for k in ('HpFactor', 'DefFactor')):
            raise ValueError('공격력 외 피해 계수: ' + sid)
        if dt.get('AtkFactor'):
            d['dm'] = '공격력×%s%%' % fnum(dt['AtkFactor'] / 100)
        if sk['m_TARGET_TYPE'] == 'NSTT_ENEMY_ALL':
            d['all'] = 1
        # 인덱스 기반 foe_auto를 갱신하지 않아도 신규 유닛에서 동일 규칙을 실행한다.
        if sk.get('AutoSkillId'):
            d['id'] = sid
            d['auto'] = dict(rows=[dict(c=conds(r.get('Condition', {}), bnames),
                                       f=filters(tb.auto_target[r['TargetConditionId']], bnames))
                                   for r in auto[sk['AutoSkillId']]['SkillConditions']])
        for se_id in lv.get('SkillLevelSE', []):
            row = tb.se[se_id]
            item = conv.convert(se_id)
            if item.get('meta'):
                raise ValueError('전용 실행기가 필요한 장비 효과: ' + se_id)
            meta = {}
            if row.get('AutoTargetId'):
                meta['auto'] = dict(one=row['m_BuffTargetType'].endswith('_ONE'),
                                    f=filters(tb.auto_target[row['AutoTargetId']], bnames))
            if row.get('ForceApplyEffect') or tb.buff[row['m_BuffStrID']].get('ForceApplyEffect'):
                meta['force'] = True
            if meta:
                if item['line'] not in ef:
                    raise ValueError('합쳐진 효과 줄에 대상/강제 규칙 연결 불가: ' + se_id)
                d.setdefault('se', []).append(dict(ef=item['line'], meta=meta))
        si[sid] = len(out['s'])
        out['s'].append(d)
        return si[sid]

    def unit(uid):
        if uid in ui:
            return ui[uid]
        r = tb.units[uid]
        if r.get('SkillOrderList'):
            raise ValueError('장비 적 SkillOrderList 미지원: ' + uid)
        stats = tb.stat[r['m_StatStrID']]
        growth = tb.per_level[stats['m_StatAddPerLevelStrID']]
        u = dict(n=ko(r['m_UnitNameString']), ti=tb.ko(r.get('m_UnitTitleString')),
                 g=GRADE[r['NKM_UNIT_GRADE']], el=ELEM[r['NKM_UNIT_ADJUST_TYPE']],
                 r=ROLE[r['m_NKM_UNIT_ROLE_TYPE']], k=ATTACK_KIND[r['UnitAttackTagType']],
                 b=[stats['m_StatData'][k] for k in SK_NST], gw=[growth[k] for k in SK_NST[:3]],
                 sk=[skill(sid) for sid in r['m_listSkill']], im=[])
        for row in tb.immune.get(r.get('ImmuneGroupId'), []):
            for bid in row['ImmuneBuffIdList']:
                name = tb.ko(row.get('ImmuneBuffName')) or tb.buff_name(bid)
                if not name:
                    raise ValueError('면역 이름 없음: ' + bid)
                if not any(i['n'] == name for i in u['im']):
                    u['im'].append(dict(n=name))
        ui[uid] = len(out['u'])
        out['u'].append(u)
        return ui[uid]

    def entry(sp):
        allowed = {'UnitStrId', 'SpawnPosIndex', 'IsBoss', 'IsElite', 'AddStatData', 'ChangeAdjustType',
                   'UnitLevel', 'AllSkillAvailable', 'SpecialSkillAvailable', 'HyperSkillAvailable'}
        if set(sp) - allowed:
            raise ValueError('배치 필드 미지원: ' + str(sorted(set(sp) - allowed)))
        u = unit(sp['UnitStrId'])
        x = {}
        if sp.get('IsBoss'):
            x['b'] = 1
        if sp.get('IsElite'):
            x['e'] = 1
        if sp.get('UnitLevel'):
            x['lv'] = sp['UnitLevel']
        if sp.get('ChangeAdjustType') and sp['ChangeAdjustType'] != 'NUAT_INVALID':
            x['el'] = ELEM[sp['ChangeAdjustType']]
        for k, v in sp.get('AddStatData', {}).items():
            if k not in aks or k not in set(SK_NST) | set(RATE):
                raise ValueError('배치 능력치 미지원: ' + k)
            x.setdefault('a', []).append([aks[k], v])
        key = json.dumps(x, sort_keys=True)
        if key not in xi:
            xi[key] = len(out['x'])
            out['x'].append(x)
        return [u, xi[key]]

    tab_rows = {r['BattleTabID']: r for r in tabs}
    selected = [r for r in battles if re.fullmatch(r'NORMAL_BATTLE_EXPLORE_EQUIP[123]_\d+', r['BattleStrID'])]
    groups = {}
    for r in sorted(selected, key=lambda r: (tab_rows[r['BattleTabId']]['OrderList'], r['OrderList'])):
        tab = ko(tab_rows[r['BattleTabId']]['BattleTabName'])
        name = ko(r['BattleName'])
        if not all_stages and (tab, name) in existing:
            continue
        if r['BattleMode'] not in ('BM_BOSS_KILL', 'BM_ALL_KILL'):
            raise ValueError('승리 조건 미지원: ' + r['BattleMode'])
        for field in ('BattleEffectData', 'DifficultyGroupId', 'SuddenDeathGroupId', 'FixUnitLevel', 'FixUnitResonance', 'RaiseUnitLevel', 'BattleDeckId'):
            if r.get(field):
                raise ValueError('장비 전투 필드 미지원: ' + field)
        bs = script(r['BattleTempletFileName'])
        if set(bs) != {'Waves'} or any(set(w) - {'MapPosType', 'TeamBSpawnList'} for w in bs['Waves']):
            raise ValueError('장비 전투 스크립트 구조 변경: ' + name)
        spawns = [w['TeamBSpawnList'] for w in bs['Waves']]
        if not spawns or any(not w for w in spawns):
            raise ValueError('빈 장비 웨이브: ' + name)
        st = dict(n=name, lv=r['BattleLevel'], bp=r['BattlePower'], w=[[entry(sp) for sp in w] for w in spawns])
        if r.get('LimitTurn'):
            st['lt'] = r['LimitTurn']
        key = 'equip|%s|%s' % (tab, name)
        if any(s['n'] == name for s in groups.get(tab, [])):
            raise ValueError('중복 장비 단계: ' + key)
        groups.setdefault(tab, []).append(st)
        out['aux']['spawn'][key] = [''.join(spawn_flag(sp) for sp in w) for w in spawns]
        out['aux']['slots'][key] = [[sp['SpawnPosIndex'] for sp in w] for w in spawns]
        if r.get('DeckSlotMax', 'BATTLE_SLOT_4') != 'BATTLE_SLOT_4':
            out['aux']['deck'][key] = r['DeckSlotMax']
        if r['BattleMode'] == 'BM_BOSS_KILL':
            out['boss_kill'].append(key)
        seen = set()
        for w in spawns:
            for sp in w:
                for sid in tb.units[sp['UnitStrId']]['m_listSkill']:
                    for se_id in sb.level_row(tb.skill[sid])[0].get('SkillLevelSE', []):
                        gid = tb.se[se_id].get('SummonGroupId')
                        if not gid or (sp['UnitStrId'], gid) in seen:
                            continue
                        seen.add((sp['UnitStrId'], gid))
                        summons = tb.summon[gid]['SummonData']
                        st.setdefault('sm', []).append([gid, out['u'][unit(sp['UnitStrId'])]['n'],
                                                       [entry(sd) + [1] for sd in summons]])
                        out['aux']['summon_groups'][str(gid)] = dict(slots=[dict(pos=sd['SpawnPosIndex'], flag=spawn_flag(sd)) for sd in summons])
                        out['aux']['summon_stages'][key] = dict(wave_slots=out['aux']['slots'][key])
    if groups:
        out['g'] = [dict(k='equip', t='장비 탐사', tabs=[dict(t=t, s=s) for t, s in groups.items()])]
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--static', type=Path)
    ap.add_argument('--out', type=Path, default=ROOT / 'data/foe_equip.json')
    ap.add_argument('--all-stages', action='store_true', help='1~20 대조용: 기존 단계도 생성')
    args = ap.parse_args()
    low_priority()
    doc = build(static_path(args.static), all_stages=args.all_stages)
    atomic_json(args.out, doc)
    print('장비 단계', sum(len(t['s']) for g in doc['g'] for t in g['tabs']), '유닛', len(doc['u']), '스킬', len(doc['s']))


if __name__ == '__main__':
    main()
