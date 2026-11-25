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
import datetime
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


def lf_digest(path):
    """파일 해시 — 저장소는 eol=lf 라 CRLF 작업 폴더에서 만든 값도 같아지게 줄바꿈을 LF 로 맞춰 잰다."""
    return hashlib.sha256(Path(path).read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')


class Extractor:
    def __init__(self, static, build, as_of=None):
        self.static, self.build = Path(static), build
        self.as_of = as_of or datetime.date.today().isoformat()
        self.tb = Tables(static)
        self.raw = load_foe(str(ROOT))
        self.be = {r['BattleEffectId']: r for r in self.rows('BATTLE_EFFECT_TEMPLET')}
        self.be_name = {r['BattleEffectStrId']: r for r in self.be.values()}
        self.se = {r['m_SEStrID']: r for r in self.rows('SE_TEMPLET_BATTLE_EFFECT')}
        from tools.build_simpack import FIXED
        self.dependencies = {}
        for name in FIXED:
            if name.startswith(('data/guild_', 'battlesim/')): continue
            self.dependencies[name] = lf_digest(ROOT/name)

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

    def support_effects(self, row):
        from tools.build_guild_support import compile_effect
        self.tb.load_effects(self.static)
        return [dict(e, execution=compile_effect(self.se[e['id']], self.tb)) for e in self.effects(row)]

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
                    boss=bool(sp.get('IsBoss')), elite=u['NKM_UNIT_GRADE']=='NUG_ELITE', slot=sp['SpawnPosIndex'], spawn=spawn_flag(sp),
                    hitStats={k:st['m_StatData'].get(k,0) for k in ('NST_RATE_HIT','NST_RATE_EVADE')},
                    source=self.source('UNIT_TEMPLET_BASE2', 'm_UnitStrID', sp['UnitStrId']))
        if ui is None:
            out['definition'] = self.definition(u, base)
        else:
            out['foeSignature'] = digest([raw['u'][ui]['n'], [raw['s'][si] for si in raw['u'][ui]['sk']]])
        # 시즌의 실제 UnitStrId로 자동 대상·강제 적용·추가 행동을 연결함.
        tb.load_effects(self.static)
        from tools.build_foe_auto import unit_rules
        definition = out.get('definition') or raw
        unit = definition['u'][0 if ui is None else ui]
        se = {}
        for sid in u['m_listSkill']:
            values = {tuple(r.get('SkillLevelSE',[])) for r in tb.level[tb.skill[sid]['SkillLevelGroup']]}
            if len(values) != 1: raise ValueError('길드 적 스킬 레벨별 효과가 다름: '+sid)
            se[sid] = [tb.se[n] for n in values.pop()]
        rules = unit_rules(unit,definition,u,tb.skill,tb.auto_skill,tb.auto_target,se,
                           {bid:tb.buff_name(bid) for bid in tb.buff})
        def line(k):
            si,li=map(int,k.split(':'));sk=definition['s'][si]
            return [sk['sl'],sk['ef'][li]]
        out['clientRules'] = dict(skills=rules['skills'],order=rules.get('order',[]),
            lines=[line(k)+[v] for k,v in rules['lines'].items()],
            enforceSelf=[line(k)+[v] for k,v in rules.get('enforce_self',{}).items()],
            force=[line(k) for k in rules.get('force',[])],
            se=[line(k)+[v] for k,v in rules.get('se',{}).items()])
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
                                 role=ROLE.get(be.get('TargetRoleType')), effects=self.support_effects(be),
                                 source=self.source('BATTLE_EFFECT_TEMPLET', 'BattleEffectStrId', key)))
        result = dict(schema=1, asOf=self.as_of, gameBuild=self.build, dependencies=self.dependencies,
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
                                   bossCount=sum(u['boss'] for w in steps[-1]['waves'] for u in w),
                                   eliteCount=sum(u['elite'] and not u['boss'] for w in steps[-1]['waves'] for u in w),
                                   bossWave=next(i for i,w in enumerate(steps[-1]['waves']) if any(u['boss'] for u in w))))
        # 표시·탐색 기본값은 계산 설정이며 게임 규칙의 근거로 사용하지 않는다.
        template_path = ROOT/'data/guild_seasons/30111.json'
        template = json.loads(template_path.read_text(encoding='utf-8'))
        result['sources'] = {'client': {'name': self.build+' PC 클라 추출', 'url':''}}
        result['sets'] = copy.deepcopy(template['sets'])
        result['sets'].update(src=['client'],scope='가정 계산용')
        result['search'] = copy.deepcopy(template['search'])
        search = result['search']; n = len(result['challenge']['levels'])
        search.update(excludeText=[],excludeKeys=[],notes=[],excludeWhy='',banCoop=False)
        search['screen'].update(level=min(6,n),supporter='none',other='none',support='none')
        search['final'].update(levels=list(range(n+1)),supports=['none']+[str(s['id']) for s in supports])
        search['supportRole'] = {str(s['id']):s['role'] for s in supports if s['role']}
        result['challenge'].update(effectText=template['challenge']['effectText'],note='클라 난이도 그룹 연결에서 추출함.',statNote='')
        result['rules'] = dict(turnLimit=steps[-1]['turnLimit'],partyCount=1,partySize=int(steps[-1]['deck'].rsplit('_',1)[1]),conf='확인',src=['client'])
        result['score'] = dict(conf='추정',src=['client'],note='클라 기본 점수는 실제 처치·보스별 체력 비율로 계산. 추가 점수 배율의 서버 반올림은 미확인.',
                               hypotheses=[dict(id='A',name='클리어 점수',desc='기본 점수 합계 × 추가 점수 배율',bossExcluded=False)])
        result['gimmicks'] = dict(conf='확인',src=['client'],items=[])
        result['community'] = dict(conf='낮음',src=[],items=[],note='이 시즌의 추가 공략 자료 없음')
        result['exBoss'] = dict(hp=boss['stats']['hp'],atk=boss['stats']['atk'],**{'def':boss['stats']['def']},speed=boss['stats']['spd'],superArmor=boss['stats']['tough'],conf='확인',src=['client'])
        result['stepsMeta'].update(conf='확인',src=['client'],minionsNote='현재 클라의 원래 웨이브·배치 기준')
        result['season'].update(conf='확인',src=['client'])
        return result


def select_current(current=None):
    dest = ROOT/'data/guild_seasons'
    index_path = ROOT / 'data/guild_current.json'
    current = current or (json.loads(index_path.read_text(encoding='utf-8'))['seasonId'] if index_path.exists() else 30111)
    selected = json.loads((dest / ('%d.json' % current)).read_text(encoding='utf-8'))
    # 날짜·표시 메타를 채운 뒤에도 정본 전체의 자료 버전을 다시 계산함.
    selected.pop('dataVersion',None)
    selected['dataVersion'] = digest(selected)
    write(dest/('%d.json'%current),selected)
    write(index_path, dict(seasonId=current))
    write(ROOT / 'data/guild_defense.json', selected)
    path = ROOT/'party_contents.json'
    contents = json.loads(path.read_text(encoding='utf-8'))
    boss = selected['season']['boss']
    contents['contents']['길드방어전']['bosses'] = {boss['name']:dict(enemies=[boss['element']],role=boss['role'],atk='미확인',note='시즌 '+str(current)+' · data/guild_seasons/'+str(current)+'.json')}
    write(path,contents)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--static', type=Path)
    ap.add_argument('--build', help='BUILD.md 마지막 절과 같아야 함(기본: 해당 기록)')
    ap.add_argument('--season', type=int, action='append')
    ap.add_argument('--as-of', help='표시용 자료 확인일(기본: 오늘, 재현 추출 시 원래 날짜)')
    ap.add_argument('--current', type=int, help='명시적으로 현재 시즌 선택')
    ap.add_argument('--extract-only', action='store_true', help='시즌 파일만 추출하고 현재 시즌 사본은 갱신하지 않음')
    ap.add_argument('--select-only', action='store_true', help='표 재추출 없이 정본의 현재 시즌 사본만 생성')
    a = ap.parse_args()
    if a.select_only:
        if a.extract_only or a.season: ap.error('--select-only와 추출 옵션을 함께 쓰지 않음')
        select_current(a.current)
        return
    static = static_path(a.static)
    recorded = (static/'decompiled/BUILD.md').read_text(encoding='utf-8')
    recorded = re.search(r'buildid\s*\**\s*(\d{6,})',recorded[recorded.rfind('\n## '):]).group(1)
    if a.build and a.build != recorded: ap.error('--build와 BUILD.md 마지막 기록 불일치')
    ex = Extractor(static, recorded,a.as_of)
    dest = ROOT / 'data/guild_seasons'
    rows = ex.rows('GUILD_DUNGEON_SEASON_TEMPLET')
    missing = set(a.season or ()) - {r['GuildDungeonSeasonId'] for r in rows}
    if missing: raise ValueError('현재 클라에 없는 시즌: '+str(sorted(missing)))
    for row in rows:
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
            g['dependencies'] = ex.dependencies
            g['defaultStep'] = 7
            g['stepsMeta'].update(waveCount=2, bossWave=1)
            g['assets'] = {}
            for name in ('guild_bfb', 'guild_sim'):
                target = dest / '30111' / (name + '.json')
                if not target.exists():
                    write(target, json.loads((ROOT / 'data' / (name + '.json')).read_text(encoding='utf-8')))
                g['assets'][name] = dict(path='guild_seasons/30111/' + name,
                                        sha256=lf_digest(target))
        else:
            g = generated
        g.pop('dataVersion', None)
        g['dataVersion'] = digest(g)
        write(dest / ('%d.json' % sid), g)
        print(sid, g['season']['boss']['name'], len(g['steps']), g['dataVersion'][:12])
    if a.extract_only:
        return
    select_current(a.current)


if __name__ == '__main__':
    main()
