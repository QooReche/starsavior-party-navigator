"""길드 시즌 정본과 보스 실행기. 날짜는 실행기 선택에 관여하지 않는다."""
import hashlib
import json
import os

from .. import datafile
from .data import SRC
from .boss_registry import expand, guild_waves, dependency_digest


@datafile.cached
def load(season_id=None, src=SRC):
    if season_id is None:
        season_id = datafile.load('guild_current', src)['seasonId']
    if isinstance(season_id, bool) or not str(season_id).isdigit():
        raise ValueError('길드 시즌 id는 양의 정수: %r' % season_id)
    try:
        g = expand(datafile.load('guild_seasons/%d' % int(season_id), src), src)
        check_dependencies(src, tuple(g.get('dependencies', {}).items()))
        return g
    except FileNotFoundError:
        raise ValueError('보관되지 않은 길드 시즌: %s' % season_id) from None


@datafile.cached
def check_dependencies(src, entries):
    for name, expected in entries:
        if dependency_digest(os.path.join(src, name)) != expected:
            raise ValueError('길드 실행 자료가 바뀜: 시즌 재추출 필요 ('+name+')')


def identity(options, src=SRC):
    g = load(options.get('seasonId'), src)
    version = options.get('dataVersion')
    if version and version != g['dataVersion']:
        raise ValueError('길드 시즌 자료 버전이 다름: 화면을 새로 고쳐야 함')
    return '%s:%s' % (g['season']['id'], g['dataVersion'])


def build_waves(options, src=SRC):
    identity(options, src)
    g = load(options.get('seasonId'), src)
    step = int(options.get('step', g['defaultStep']))
    return guild_waves(g, options, step, src)


def bfb_waves(g, options, step, src):
    from .guild_bfb import build_waves
    return build_waves(int(options.get('level', 0)), options.get('sets'), src,
                       options.get('support'), season=g)


def client_waves(g, options, step, src):
    from .foe import FoeDef, load_foe
    from .guild_common import config, scale_stats
    st = next((s for s in g['steps'] if s['step'] == step), None)
    if st is None:
        raise ValueError('길드 시즌에 없는 단계: %s/%s' % (g['season']['id'], step))
    if st.get('unavailable'):
        raise ValueError(st['unavailable'])
    cfg = config(g, options, st)
    raw = load_foe(src)
    waves = []
    for w in st['waves']:
        row = []
        for member in w:
            custom = member.get('definition')
            ui = member['foe']
            if custom is None:
                signature = hashlib.sha256(json.dumps([raw['u'][ui]['n'], [raw['s'][si] for si in raw['u'][ui]['sk']]],
                    ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
                if signature != member['foeSignature']:
                    raise ValueError('길드 적 자료가 바뀜: 시즌을 재추출해야 함 (' + member['unit'] + ')')
            else:
                # 독립 조각은 기존 foe:0 자동 대상 자료를 차용하지 않는다.
                # FoeDef가 붙인 표를 아래에서 조각 자체 메타로 대체한다.
                ui = 0
            s = member['stats']
            stats = dict(zip(('hp','atk','def','spd','cr','cd','eh','er','der','sa'),
                             (s[k] for k in ('hp','atk','def','spd','crit','critdmg','hit','evade','abs_evade','tough'))))
            if member['boss']:
                stats = scale_stats(stats, cfg['row'])
            d = FoeDef(custom or raw, ui, st={'lv':member['level']}, stats_override=stats,
                       key_override='guild:' + member['unit'] if custom else None)
            if custom:
                d.auto = {s['sl']:s['auto'] for s in custom['s'] if s.get('auto')}
                d.auto_lines, d.force_lines, d.enforce_self, d.skill_order = {}, set(), {}, ()
                d.unmodeled.extend('길드 효과 미반영: %s — %s' % (u['se'],u['reason']) for u in custom['unmodeled'])
            if member.get('clientRules'):
                rules = member['clientRules']
                d.auto, d.skill_order = rules['skills'],rules['order']
                d.auto_lines = {(sl,text):spec for sl,text,spec in rules['lines']}
                d.enforce_self = {(sl,text):spec for sl,text,spec in rules['enforceSelf']}
                d.force_lines = {tuple(row) for row in rules['force']}
                d.se_meta = {(sl,text):target_type for sl,text,target_type in rules['se']}
            d.name, d.role, d.element = member['name'], member['role'], member['element']
            if 'hitStats' in member:
                d.stats.update(hit=member['hitStats']['NST_RATE_HIT'], evade=member['hitStats']['NST_RATE_EVADE'])
            d.boss = member['boss']
            d.grade = '보스' if d.boss else ('정예' if member.get('elite') else '일반')
            d.spawn, d.slot = member['spawn'], member['slot']
            d.game_slot, d.game_deck = member['slot'], st['deck']
            d.guild = cfg
            row.append(d)
        waves.append(row)
    mode = {'BM_BOSS_KILL':'boss_kill', 'BM_KILL_ALL':'all_kill'}.get(st['mode'])
    if not mode:
        raise ValueError('미지원 길드 승리 조건: ' + st['mode'])
    return waves, dict(content='guild', tab='길드 방어전', name='%s %d단계' % (g['season']['label'],step),
                       level=st['battleLevel'], recommended_power=st['power'], wave_count=len(waves),
                       battle_mode=mode, turn_limit=st['turnLimit'], guild=dict(options, seasonId=g['season']['id'], step=step),
                       guild_score={k:st[k] for k in ('base','bossKill','kill','eliteKill')})


def base_points(battle, points):
    """NKM:17376-17392. 보스마다 비율 정수화, 일반·엘리트는 실제 처치 수."""
    total = points['base']
    for u in battle.all_foes:
        if u.d.boss:
            maximum = int(u.maxhp)
            lost = maximum - max(0, int(u.hp))
            total += points['bossKill'] * (lost * 10000 // maximum) // 10000
        elif u.dead:
            total += points['eliteKill'] if u.d.grade == '정예' else points['kill']
    return total
