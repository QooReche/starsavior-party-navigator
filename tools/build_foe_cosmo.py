# -*- coding: utf-8 -*-
"""26752678 PC 표의 바스커빌 COSMO_01~03을 SE 순서 그대로 적 조각으로 만든다."""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.tables import rows
from tools.build_foe_clash import (Tables, SeConverter, Unconvertible, db_shapes, unverified_parts,
                                  ROLE, ELEM, ATTACK_KIND, SKILL_TY, TARGET_TG, clean_markup, spawn_flag)
from tools.build_foe_auto import filters, conds


class ClientTables(Tables):
    """추출 폴더를 직접 읽음. 비공개 원문을 작업 트리에 복사하지 않는다."""
    def __init__(self, path):
        self.t = Path(path)
        self.strings = {}
        for r in rows(self.t / 'hard/STRING_COMMON.json'):
            for k in ([r['Key']] if 'Key' in r else r.get('Keys', [])):
                self.strings[k] = {'ko': r.get('Value', '')}
        def keyed(file, key):
            return {r[key]: r for r in rows(self.t / file)}
        self.buff = keyed('CLIENT_BUFF_TEMPLET.json', 'm_BuffStrID')
        self.dt = keyed('CLIENT_DAMAGE_TEMPLET.json', 'DTStrID')
        self.cond = keyed('plain/SKILL_CONDITION_TEMPLET.json', 'Id')
        self.auto_target = {r['Id']: r['TargetCondition'] for r in rows(self.t / 'plain/AUTO_SKILL_TARGET_TEMPLET.json')}
        self.auto_skill = keyed('plain/AUTO_SKILL_TEMPLET.json', 'Id')
        self.skill, self.se, self.units, self.stat, self.per_level = {}, {}, {}, {}, {}
        self.level = defaultdict(list)
        for n in (1, 2):
            self.skill.update(keyed('CLIENT_SKILL_TEMPLET_%d.json' % n, 'm_SkillStrID'))
            self.se.update(keyed('CLIENT_SE_TEMPLET_SKILL_%d.json' % n, 'm_SEStrID'))
            for r in rows(self.t / ('CLIENT_SKILL_LEVEL_GROUP_TEMPLET_%d.json' % n)):
                self.level[r['SkillLevelGroupID']].append(r)
        for p in self.t.glob('CLIENT_UNIT_TEMPLET_BASE*.json'):
            self.units.update({r['m_UnitStrID']: r for r in rows(p)})
        for p in self.t.glob('CLIENT_UNIT_STAT_TEMPLET*.json'):
            self.stat.update({r['m_StatStrID']: r for r in rows(p)})
        for p in self.t.glob('CLIENT_STAT_ADD_PER_LEVEL*.json'):
            self.per_level.update({r['StatAddPerLevelStrID']: r['StatAddPerLevelData'] for r in rows(p)})
        self.immune = defaultdict(list)
        for r in rows(self.t / 'CLIENT_BUFF_IMMUNE_TEMPLET.json'):
            self.immune[r['ImmuneGroupId']].append(r)
        self.damage_scale = 1.85

    def buff_name(self, bid):
        # hard/STRING_COMMON.json:114693-114695의 Keys 배열에 현재 이름(끝나지 않는 사냥)이 있음.
        # 문자열이 빠진 추출본만 가명 사용. 최대 중첩 0은 무제한(NKM:4445).
        return super().buff_name(bid) or ({'BI_DOOMSDAY_BEAST_BOSS_7': '폭주하는 피 피해 증가(가명)'}.get(bid))


def build(tables):
    from battlesim.starsavior.foe import SK_NST
    tb = ClientTables(tables)
    conv = SeConverter(tb)
    # 생성한 조각을 문법 선례로 다시 읽으면 허용 목록 검사가 무력화됨. 데이터북 원문만 읽는다.
    raw = (ROOT / 'rawdata/foe.js').read_text(encoding='utf-8')
    shapes = db_shapes(json.JSONDecoder().raw_decode(raw[raw.index('__SSD.foe=') + len('__SSD.foe='):])[0])
    names = {bid: tb.buff_name(bid) for bid in tb.buff}
    out = dict(_note='PC 빌드 26752678 바스커빌 조각. se는 원본 순서·ID·대상·조건과 실행 담당을 보존함. 데이터북 스테이지 우선.',
               u=[], s=[], x=[], ak=[], g=[], aux={'spawn': {}, 'slots': {}}, boss_kill=[], unmodeled=[], check={})
    idx, report = {}, []
    def skill(sid, replacement=False):
        if sid in idx:
            return idx[sid]
        sk = tb.skill[sid]
        level = sorted(tb.level[sk['SkillLevelGroup']], key=lambda r: r['SkillLevelValue'])[0]
        slot = next((v for k, v in [('SPECIAL', '특수기'), ('ATTACK', '기본기'), ('HYPER', '궁극기')] if k in sid), '패시브')
        d = dict(id=sid, sl=slot, n=tb.ko(sk['m_SkillName']) or '폭주하는 피', ty=SKILL_TY[sk['m_NKM_SKILL_TYPE']],
                 tg=TARGET_TG[sk['m_TARGET_TYPE']], cd=sk.get('m_CoolTurn', 0), ab=sk.get('SuperArmorBreakValue', 0),
                 d1=clean_markup(tb.ko(level.get('SkillLevelDesc'))), ef=[], se=[], gl=[], replacement=replacement)
        dt = tb.dt.get(sk.get('DTStrID'), {})
        if dt.get('AtkFactor'):
            d['dm'] = '공격력×%g%%' % (dt['AtkFactor'] / 100)
        if sk['m_TARGET_TYPE'] == 'NSTT_ENEMY_ALL':
            d['all'] = 1
        aid = sk.get('AutoSkillId')
        if aid:
            auto = tb.auto_skill[aid]
            d['auto'] = dict(t='enemy_one', rows=[dict(c=conds(r.get('Condition', {}), names), f=filters(tb.auto_target[r['TargetConditionId']], names))
                                                   for r in auto['SkillConditions']])
        for order, se in enumerate(level.get('SkillLevelSE', [])):
            row = tb.se[se]
            try:
                it = conv.convert(se)
                bad = unverified_parts(it['line'], shapes)
                if bad:
                    raise Unconvertible('문법 미검증: ' + ' | '.join(bad))
            except Unconvertible as ex:
                out['unmodeled'].append(dict(skill=sid, se=se, reason=str(ex)))
                continue
            meta = dict(it.get('meta', {}))
            b = tb.buff[row['m_BuffStrID']]
            if row.get('AutoTargetId'):
                meta['auto'] = dict(one=row['m_BuffTargetType'].endswith('_ONE'), f=filters(tb.auto_target[row['AutoTargetId']], names))
            meta['force'] = bool(row.get('ForceApplyEffect') or b.get('ForceApplyEffect'))
            # NKM:4505-4524: IsUniqueID는 같은 이름이어도 독립 객체, IsBuff와 양성은 별개.
            meta['buff'] = dict(name=tb.buff_name(row['m_BuffStrID']), unique=bool(b.get('IsUniqueID')),
                                category=('buff' if b.get('IsPositive') else 'debuff') if b.get('IsBuff') else 'marker',
                                unlimited=bool(b.get('IsLevel') and not b.get('BuffLevelMax')),
                                speed_zero=any(x.get('StatTypeFix') == 'NST_TURN_SPEED' and x.get('StatTypeFixValue') == 0 for x in b.get('FixStats', [])),
                                armor_ban=bool(b.get('SuperArmorDamageBan')))
            d['ef'].append(it['line'])
            d['se'].append(dict(order=order, id=se, ef=it['line'], target=row.get('m_BuffTargetType'),
                                condition=row.get('SkillConditionId'), executor='cosmo' if meta.get('op') else 'engine', meta=meta))
            if it['gl']:
                d['gl'].append(it['gl'])
            report.append(se)
        idx[sid] = len(out['s'])
        out['s'].append(d)
        return idx[sid]

    stages = []
    for step in (1, 2, 3):
        uid = 'NKM_UNIT_MON_DOOMSDAY_BEAST_BLACK_BOSS_COSMO_%02d' % step
        r = tb.units[uid]
        st = tb.stat[r['m_StatStrID']]
        growth = tb.per_level[st['m_StatAddPerLevelStrID']]
        u = dict(n=tb.ko(r['m_UnitNameString']), g='보스', el=ELEM[r['NKM_UNIT_ADJUST_TYPE']],
                 r=ROLE[r['m_NKM_UNIT_ROLE_TYPE']], k=ATTACK_KIND[r['UnitAttackTagType']],
                 b=[st['m_StatData'].get(k, 0) for k in SK_NST], gw=[growth[k] for k in SK_NST[:3]],
                 sk=[skill(sid) for sid in r['m_listSkill']], im=[], client_model='baskerville')
        replacement = r['m_listSkill'][1] + '2'
        u['sk'].append(skill(replacement, True))
        for ir in tb.immune[r['ImmuneGroupId']]:
            for bid in ir['ImmuneBuffIdList']:
                nm = tb.ko(ir.get('ImmuneBuffName')) or tb.buff_name(bid)
                if nm and not any(x['n'] == nm for x in u['im']):
                    u['im'].append(dict(n=nm))
        out['u'].append(u)
        # plain/JSON_RANKING_RAID_DOOMSDAY_BEAST_01_BATTLE_01.json:10-16 (02·03도 같은 배치).
        script_name = 'JSON_RANKING_RAID_DOOMSDAY_BEAST_01_BATTLE_%02d' % step
        script = rows(tb.t / ('plain/' + script_name + '.json'))
        spawns = script['Waves'][0]['TeamBSpawnList']
        if len(script['Waves']) != 1 or len(spawns) != 1 or spawns[0]['UnitStrId'] != uid:
            raise ValueError('바스커빌 배치 구조 변경')
        br = next(r for r in rows(tb.t / 'CLIENT_BATTLE_TEMPLET_RANKING_RAID.json')
                  if r['BattleTempletFileName'] == script_name + '.txt')
        stages.append(dict(n='%s %d단계' % (u['n'], step), lv=br['BattleLevel'], bp=br['BattlePower'], w=[[[step - 1]]]))
        key = 'cosmo|%s|%s' % (u['n'], stages[-1]['n'])
        out['aux']['spawn'][key] = [spawn_flag(spawns[0])]
        out['aux']['slots'][key] = [[spawns[0]['SpawnPosIndex']]]
        if br['BattleMode'] == 'BM_BOSS_KILL':
            out['boss_kill'].append(key)
    out['g'] = [dict(k='cosmo', t='코스모 게이트', tabs=[dict(t=out['u'][0]['n'], s=stages)])]
    out['check'] = dict(converted=len(report), failed=len(out['unmodeled']), rows=report)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--tables', type=Path, required=True)
    ap.add_argument('--out', type=Path, default=ROOT / 'data/foe_cosmo_extra.json')
    args = ap.parse_args()
    doc = build(args.tables)
    print('변환', doc['check']['converted'], '불가', doc['check']['failed'])
    for r in doc['unmodeled']:
        print(r['se'], r['reason'])
    if doc['unmodeled']:
        raise SystemExit(1)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
