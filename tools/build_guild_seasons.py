"""PC 클라의 길드 시즌·전투·배치를 가공한다. 현재 시즌은 --current로만 바꾼다.

과거 시즌도 지정 클라 빌드에서 추출한 정의이며 당시 빌드 재현본이 아니다.
원문 표는 저장하지 않는다. 새로운 스킬/효과 연결을 해석하지 못하면 중단한다.
"""
import argparse
import copy
import hashlib
import json
import sys
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.runtime import static_path
from tools.tables import jsonc, table, strings
from tools.build_foe_clash import (Tables as BaseTables, ROLE, ELEM, ATTACK_KIND, spawn_flag,
                                 SkillBuilder, SeConverter, db_shapes, SKILL_TY, TARGET_TG, clean_markup)
from battlesim.starsavior.foe import load_foe, foe_stats, SK_NST

ELEMENT = dict(zip(('태양', '달', '별', '질서', '혼돈'), ('sun', 'moon', 'star', 'order', 'chaos')))
ROLE_KEY = dict(zip(('스트라이커', '캐스터', '어쌔신', '레인저', '디펜더', '서포터'),
                    ('striker', 'caster', 'assassin', 'ranger', 'defender', 'supporter')))


class Tables(BaseTables):
    """길드 연결에 필요한 표만 순차 로드. 대형 SE/조건 표를 중복 보관하지 않는다."""
    def __init__(self, static):
        self.strings = strings(Path(static) / 'tables')
        self.buff = {r['m_BuffStrID']: r for r in table(static, 'BUFF_TEMPLET')}
        self.units = {}
        for n in (1, 2, 3, 4):
            self.units.update((r['m_UnitStrID'], r) for r in table(static, 'UNIT_TEMPLET_BASE%d' % n)
                              if 'GUILDRAID' in r['m_UnitStrID'])
        self.skill = {}
        for n in (1, 2):
            self.skill.update((r['m_SkillStrID'], r) for r in table(static, 'SKILL_TEMPLET_%d' % n))
        self.stat = {r['m_StatStrID']: r for r in table(static, 'UNIT_STAT_TEMPLET2')}
        self.per_level = {r['StatAddPerLevelStrID']: r['StatAddPerLevelData'] for r in table(static, 'STAT_ADD_PER_LEVEL2')}

    def load_effects(self, static):
        if hasattr(self, 'se'):
            return
        self.t = Path(static) / 'tables'
        self.se, self.level = {}, defaultdict(list)
        for n in (1, 2):
            self.se.update((r['m_SEStrID'], r) for r in table(static, 'SE_TEMPLET_SKILL_%d' % n))
            for r in table(static, 'SKILL_LEVEL_GROUP_TEMPLET_%d' % n):
                self.level[r['SkillLevelGroupID']].append(r)
        self.dt = {r['DTStrID']: r for r in table(static, 'DAMAGE_TEMPLET')}
        self.cond = {r['Id']: r for r in jsonc(self.t / 'Plain/SKILL_CONDITION_TEMPLET.json')['Data']}
        self.auto_target = {r['Id']: r['TargetCondition'] for r in jsonc(self.t / 'Plain/AUTO_SKILL_TARGET_TEMPLET.json')['Data']}
        self.auto_skill = {r['Id']: r for r in jsonc(self.t / 'Plain/AUTO_SKILL_TEMPLET.json')['Data']}
        self.immune = defaultdict(list)
        for r in table(static, 'BUFF_IMMUNE_TEMPLET'):
            self.immune[r['ImmuneGroupId']].append(r)
        self.damage_scale = self._find_const('DamageScale') / 10000


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')


class Extractor:
    def __init__(self, static, build):
        self.static, self.build = Path(static), build
        self.tb = Tables(static)
        self.raw = load_foe(str(ROOT))
        self.be = {r['BattleEffectId']: r for r in self.rows('BATTLE_EFFECT_TEMPLET')}
        self.be_name = {r['BattleEffectStrId']: r for r in self.be.values()}
        self.se = {r['m_SEStrID']: r for r in self.rows('SE_TEMPLET_BATTLE_EFFECT')}

    def rows(self, name):
        path = self.static / 'tables' / (name + '.json')
        try:
            with path.open(encoding='utf-8-sig') as f:
                return json.load(f)['Data']
        except json.JSONDecodeError:
            return jsonc(path)['Data']

    def source(self, name, key, value):
        path = self.static / 'tables' / (name + '.json')
        needle = json.dumps(value, ensure_ascii=False)
        with path.open(encoding='utf-8-sig') as f:
            hits = [i + 1 for i, line in enumerate(f) if '"' + key + '"' in line and line.split(':', 1)[1].strip().rstrip(',') == needle]
        if len(hits) != 1:
            raise ValueError((name, key, value, hits))
        return 'tables/%s.json:%d' % (name, hits[0])

    def effects(self, row):
        # 필요한 실행 값·연결만 보관. 클라 원문 행/설명/아이콘은 복사하지 않는다.
        out = []
        for sid in row.get('BattleEffectSeStrId', []):
            s = self.se[sid]
            b = self.tb.buff[s['m_BuffStrID']]
            out.append(dict(id=sid, buff=s['m_BuffStrID'], phase=s['m_Condition']['m_ActiveType'],
                            chance=s['m_Condition'].get('m_fActiveRate', 10000),
                            target=s.get('m_BuffTargetType'), condition=s.get('SkillConditionId'),
                            duration=s.get('m_BuffLifeTurn', 0), stats=s.get('Stats', b.get('Stats', [])),
                            maxStacks=b.get('BuffLevelMax', 1),
                            source=self.source('SE_TEMPLET_BATTLE_EFFECT', 'm_SEStrID', sid)))
        return out

    def challenge(self, group):
        levels = []
        for r in sorted((r for r in self.rows('DIFFICULTY_LEVEL_GROUP') if r['DifficultyGroupId'] == group), key=lambda x: x['Level']):
            v = dict(level=r['Level'], atk=r.get('ScaleFactorAttack', 0) / 100,
                     hp=r.get('ScaleFactorHp', 0) / 100, **{'def': r.get('ScaleFactorDefence', 0) / 100},
                     score=r.get('DifficultyValue', 0) / 100, skillStack=0, hpDrain=0, speed=0, immune=0, effects=[])
            for link in r.get('ChallengeEffect', []):
                be = self.be[int(link['BattleEffectId'])]
                if be.get('BteamEffectTarget') != 'MONSTER_BOSS':
                    raise ValueError('도전 대상 변경: ' + str(be['BattleEffectId']))
                for e in self.effects(be):
                    bid = e['buff']
                    rate = (e['stats'] or [{}])[0].get('NKM_STAT_TYPE_RATE', 0) / 100
                    if bid == 'BI_STAR_CHALLENGE_EX_1': v['skillStack'] = rate
                    elif bid == 'BI_STAR_CHALLENGE_EX_2': v['hpDrain'] = -rate
                    elif bid == 'BI_STAT_NST_NV_RATE_TURN_SPEED_INFINITE': v['speed'] = rate
                    elif bid == 'BI_DEBUFFBAN_CAN_NOT_DISPEL': v['immune'] = e['duration']
                    else: raise ValueError('미해석 도전 효과: ' + bid)
                    v['effects'].append(e)
            levels.append(v)
        return dict(group=group, levels=levels, cumulative=True, conf='확인', src=['client'])

    def member(self, sp, level):
        tb, raw = self.tb, self.raw
        u = tb.units[sp['UnitStrId']]
        st = tb.stat[u['m_StatStrID']]
        growth = tb.per_level[st['m_StatAddPerLevelStrID']]
        names = [tb.ko(tb.skill[sid]['m_SkillName']) for sid in u['m_listSkill']]
        candidates = [i for i, d in enumerate(raw['u']) if d['n'] == tb.ko(u['m_UnitNameString'])
                      and d['r'] == ROLE[u['m_NKM_UNIT_ROLE_TYPE']]
                      and [raw['s'][si]['n'] for si in d['sk'][:len(names)]] == names]
        # 데이터북은 교체 스킬을 기본 6개 뒤에 붙인다. 추가 이름도 클라 교체 SE의 연결에서 확인한다.
        if any(len(raw['u'][i]['sk']) > len(names) for i in candidates):
            tb.load_effects(self.static)
            reachable = set(u['m_listSkill'])
            pending = list(reachable)
            while pending:
                sid = pending.pop()
                for lv in tb.level[tb.skill[sid]['SkillLevelGroup']]:
                    for seid in lv.get('SkillLevelSE', []):
                        target = tb.se[seid].get('AfterChangeSkillStrId')
                        if target and target not in reachable:
                            reachable.add(target)
                            pending.append(target)
            allowed_names = {tb.ko(tb.skill[sid]['m_SkillName']) for sid in reachable}
            candidates = [i for i in candidates if all(raw['s'][si]['n'] in allowed_names for si in raw['u'][i]['sk'])]
        # 같은 스킬 이름의 다른 변형을 조용히 선택하지 않는다.
        variants = {digest([raw['s'][si] for si in raw['u'][i]['sk']]) for i in candidates}
        if candidates and len(variants) != 1:
            raise ValueError('스킬 변형 구별 필요: ' + sp['UnitStrId'])
        ui = candidates[0] if candidates else None
        base = dict(b=[st['m_StatData'].get(k, 0) for k in SK_NST], gw=[growth.get(k, 0) for k in SK_NST[:3]])
        ak = {v[1]: i for i, v in enumerate(raw['ak'])}
        stats, lev = foe_stats(raw, base, {'a': [[ak[k], v] for k, v in sp.get('AddStatData', {}).items()]}, {'lv': level})
        # 기존 FoeDef 효과 해석을 재사용하되 수치·속성·칸·쿨은 클라 배치에서 직접 받는다.
        out = dict(unit=sp['UnitStrId'], foe=ui, skills=u['m_listSkill'],
                    stats=stats, level=lev, element=ELEM.get(sp.get('ChangeAdjustType'), ELEM[u['NKM_UNIT_ADJUST_TYPE']]),
                    role=ROLE[u['m_NKM_UNIT_ROLE_TYPE']], name=tb.ko(u['m_UnitNameString']),
                    boss=bool(sp.get('IsBoss')), slot=sp['SpawnPosIndex'], spawn=spawn_flag(sp),
                    source=self.source('UNIT_TEMPLET_BASE2', 'm_UnitStrID', sp['UnitStrId']))
        if ui is None:
            out['definition'] = self.definition(u, base)
        else:
            out['foeSignature'] = digest([raw['u'][ui]['n'], [raw['s'][si] for si in raw['u'][ui]['sk']]])
        return out

    def definition(self, u, base):
        tb = self.tb
        tb.load_effects(self.static)
        sb = SkillBuilder(tb, SeConverter(tb), db_shapes(self.raw))
        skills = []
        for sid in u['m_listSkill']:
            sk = tb.skill[sid]
            ef, gl, _, lv = sb.ef_for(sid)
            slot = next((v for k,v in [('ATTACK','기본기'), ('SPECIAL','특수기'), ('HYPER','궁극기')] if sid.endswith('_'+k)), '패시브')
            d = dict(id=sid, sl=slot, n=tb.ko(sk['m_SkillName']), ty=SKILL_TY[sk['m_NKM_SKILL_TYPE']],
                     tg={**TARGET_TG, 'NSTT_REACT_ENEMY_TARGET': '적 단일'}[sk['m_TARGET_TYPE']], cd=sk.get('m_CoolTurn'), ab=sk.get('SuperArmorBreakValue',0),
                     d1=clean_markup(tb.ko(lv.get('SkillLevelDesc'))), ef=ef, gl=gl)
            dt = tb.dt.get(sk.get('DTStrID'), {})
            if dt.get('AtkFactor'):
                d['dm'] = '공격력×%g%%' % (dt['AtkFactor']/100)
            if sk['m_TARGET_TYPE'] == 'NSTT_ENEMY_ALL':
                d['all'] = 1
            if sk.get('AutoSkillId'):
                from tools.build_foe_auto import filters, conds
                names = {bid: tb.buff_name(bid) for bid in tb.buff}
                d['auto'] = dict(t='enemy_one', rows=[dict(c=conds(r.get('Condition',{}), names),
                                  f=filters(tb.auto_target[r['TargetConditionId']],names))
                                  for r in tb.auto_skill[sk['AutoSkillId']]['SkillConditions']])
            skills.append(d)
        immune = []
        for r in tb.immune.get(u.get('ImmuneGroupId'), []):
            for bid in r['ImmuneBuffIdList']:
                name = tb.ko(r.get('ImmuneBuffName')) or tb.buff_name(bid)
                if name and name not in [v['n'] for v in immune]:
                    immune.append(dict(n=name))
        unit = dict(base, n=tb.ko(u['m_UnitNameString']), r=ROLE[u['m_NKM_UNIT_ROLE_TYPE']],
                    el=ELEM[u['NKM_UNIT_ADJUST_TYPE']], g='보스' if u['NKM_UNIT_GRADE']=='NUG_BOSS' else '일반',
                    k=ATTACK_KIND[u['UnitAttackTagType']], sk=list(range(len(skills))), im=immune)
        return dict(u=[unit], s=skills, x=[], ak=self.raw['ak'], unmodeled=sb.unmodeled)

    def season(self, row):
        sid = row['GuildDungeonSeasonId']
        steps = []
        for r in sorted((r for r in self.rows('BATTLE_TEMPLET_GUILD_DUNGEON') if r['BattleTabId'] == row['BattleTabId']), key=lambda x: x['OrderList']):
            script = r['BattleTempletFileName'].replace('.txt', '')
            script_path = self.static / 'tables/BattleScript' / (script + '.json')
            bs = self.rows('BattleScript/' + script) if script_path.exists() else None
            waves = [[self.member(sp, r['BattleLevel']) for sp in w['TeamBSpawnList']] for w in bs['Waves']] if bs else []
            steps.append(dict(step=r['OrderList'], ex=bool(r.get('DifficultyGroupId')), battleId=r['BattleID'],
                              battle=r['BattleStrID'], script=script, mode=r['BattleMode'], turnLimit=r['LimitTurn'],
                              battleLevel=r['BattleLevel'], power=r['BattlePower'], base=r['BasePoint'],
                              bossKill=r['BossKillPoint'], kill=r['KillPoint'], eliteKill=r['EliteKillPoint'],
                              difficultyGroupId=r.get('DifficultyGroupId'), waves=waves,
                              unavailable=None if bs else '배치 스크립트 추출본 없음: ' + script,
                              deck=r.get('DeckSlotMax', 'BATTLE_SLOT_4'),
                              source=self.source('BATTLE_TEMPLET_GUILD_DUNGEON', 'BattleID', r['BattleID'])))
        boss = next(u for w in steps[-1]['waves'] for u in w if u['boss'])
        supports = []
        items = [(row['SpecialBuffStrId'], row['SpecialBuffName'], True)]
        items += [(s['NormalBuffStrId'], s['NormalBuffName'], False) for s in row.get('GuildDungeonSeasonBuff', [])]
        for key, name, special in items:
            be = self.be_name[key]
            supports.append(dict(id=be['BattleEffectId'], name=self.tb.ko(name), special=special,
                                 role=ROLE.get(be.get('TargetRoleType')), effects=self.effects(be),
                                 source=self.source('BATTLE_EFFECT_TEMPLET', 'BattleEffectStrId', key)))
        return dict(schema=1, asOf='2026-11-25', gameBuild=self.build,
                    provenance=dict(kind='current-client-extraction', build=self.build,
                                    note='%s 클라에서 추출. 당시 빌드 재현본이 아님.' % self.build,
                                    source=self.source('GUILD_DUNGEON_SEASON_TEMPLET', 'GuildDungeonSeasonId', sid)),
                    season=dict(id=sid, label=str(sid), name=str(sid),
                                intervals=dict(play=row['PlayableIntervalId'], settlement=row['IntervalId']),
                                boss=dict(name=boss['name'], element=ELEMENT[boss['element']], role=boss['role'],
                                          roleKey=ROLE_KEY[boss['role']], engine='client')),
                    steps=steps, challenge=self.challenge(steps[-1]['difficultyGroupId']), supports=supports,
                    defaultStep=steps[-1]['step'],
                    stepsMeta=dict(minions=sum(not u['boss'] for w in steps[-1]['waves'] for u in w),
                                   waveCount=len(steps[-1]['waves']),
                                   bossWave=next(i for i,w in enumerate(steps[-1]['waves']) if any(u['boss'] for u in w))))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--static', type=Path)
    ap.add_argument('--build', default='26752678')
    ap.add_argument('--season', type=int, action='append')
    ap.add_argument('--current', type=int, help='명시적으로 현재 시즌 선택')
    ap.add_argument('--extract-only', action='store_true', help='시즌 파일만 추출하고 현재 시즌 사본은 갱신하지 않음')
    a = ap.parse_args()
    ex = Extractor(static_path(a.static), a.build)
    dest = ROOT / 'data/guild_seasons'
    for row in ex.rows('GUILD_DUNGEON_SEASON_TEMPLET'):
        sid = row['GuildDungeonSeasonId']
        if a.season and sid not in a.season: continue
        generated = ex.season(row)
        if sid == 30111:
            # 최초 보관 이후에는 정본의 사용자 설정/기존 BFB 수치·시뮬을 덮어쓰지 않는다.
            source = dest / '30111.json'
            g = json.loads((source if source.exists() else ROOT / 'data/guild_defense.json').read_text(encoding='utf-8'))
            g['season']['boss'].update(engine='bfb', roleKey='ranger')
            g['provenance'] = generated['provenance']
            g['client'] = generated
            g['defaultStep'] = 7
            g['stepsMeta'].update(waveCount=2, bossWave=1)
            g['assets'] = {}
            for name in ('guild_bfb', 'guild_sim'):
                target = dest / '30111' / (name + '.json')
                if not target.exists():
                    write(target, json.loads((ROOT / 'data' / (name + '.json')).read_text(encoding='utf-8')))
                g['assets'][name] = dict(path='guild_seasons/30111/' + name,
                                        sha256=hashlib.sha256(target.read_bytes()).hexdigest())
        else:
            g = generated
        g.pop('dataVersion', None)
        g['dataVersion'] = digest(g)
        write(dest / ('%d.json' % sid), g)
        print(sid, g['season']['boss']['name'], len(g['steps']), g['dataVersion'][:12])
    if a.extract_only:
        return
    index_path = ROOT / 'data/guild_current.json'
    current = a.current or (json.loads(index_path.read_text(encoding='utf-8'))['seasonId'] if index_path.exists() else 30111)
    selected = json.loads((dest / ('%d.json' % current)).read_text(encoding='utf-8'))
    write(index_path, dict(seasonId=current))
    write(ROOT / 'data/guild_defense.json', selected)


if __name__ == '__main__':
    main()
