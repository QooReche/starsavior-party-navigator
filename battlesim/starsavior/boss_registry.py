"""Reusable boss/monster definitions. Seasons contain layouts and module references.

Module names are content hashes: registering another build never silently changes an
archived season. Expanded projections keep the existing engine/UI contracts.
"""
import copy
import hashlib
import json
from pathlib import Path
from .. import datafile
from .data import SRC


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()


# Shared execution inputs, independent of the browser's distribution manifest.
# Current raid projections are not inputs to archived guild battles.
GUILD_DEPENDENCIES = (
    'rawdata/databook_main.json', 'rawdata/foe.js', 'data/foe_spawn.json',
    'rawdata/guide_app-core.js', 'data/synergy_tags.json', 'data/myinfo_combat.json',
    'data/auto_skill.json', 'data/foe_auto.json', 'data/sudden_death.json',
    'data/stage_fx.json', 'data/battle_end.json', 'data/chain_damage.json',
    'data/hit_stats.json', 'data/chain_se.json', 'data/break_skill_levels.json',
    'data/buff_count.json', 'data/buff_step.json', 'data/buff_force.json',
    'data/buff_immune_pass.json', 'data/buff_global_turn.json', 'data/foe_react.json',
    'data/foe_client.json', 'data/foe_summon.json', 'data/foe_clash.json',
    'data/buff_dead_keep.json', 'data/buff_flags.json', 'data/foe_cosmo_extra.json',
    'data/foe_equip.json',
)


def dependency_digest(path):
    """JSON identity is content, not indentation/key order; JS remains LF bytes."""
    path = Path(path)
    if path.suffix == '.json':
        return 'json:' + fingerprint(json.loads(path.read_text(encoding='utf-8')))
    return hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def cosmo_adapter(key, src=SRC):
    return datafile.load('boss_catalog', src)['cosmo'][key]['adapter']


def cosmo_key(script, src=SRC):
    matches = [key for key, row in datafile.load('boss_catalog', src)['cosmo'].items()
               if row['script'] in script]
    if len(matches) != 1:
        raise ValueError('미등록/중복 보스 배치: ' + script)
    return matches[0]


@datafile.cached
def module(key, src=SRC):
    value = datafile.load('boss_modules/' + key, src)
    if fingerprint(value) != key.rsplit('-', 1)[-1]:
        raise ValueError('보스 모듈 내용 해시 불일치: ' + key)
    return value


def expand(value, src=SRC):
    if isinstance(value, list):
        return [expand(v, src) for v in value]
    if not isinstance(value, dict):
        return value
    base = copy.deepcopy(module(value['$module'], src)) if '$module' in value else {}
    base.update({k: v for k, v in value.items() if k != '$module'})
    return {k: expand(v, src) for k, v in base.items()}


def guild_waves(g, options, step, src=SRC):
    from .guild import client_waves, bfb_waves
    engine = g['season']['boss']['engine']
    adapters = {'client': client_waves, 'bfb': bfb_waves}
    if engine not in adapters:
        raise ValueError('미지원 길드 보스 실행기: ' + engine)
    if engine == 'bfb' and step != g['defaultStep']:
        return client_waves(g['client'], options, step, src)
    return adapters[engine](g, options, step, src)


def controller(battle, waves):
    """One registration point, including the retained BFB custom adapter."""
    registrations = (
        ('guild_boss', 'bfb', 'guild_bfb'),
        ('guild_boss', 'guild', 'guild_common'),
        ('cosmo_raid_boss', 'cosmo', 'cosmo_raid'),
    )
    for switch in ('guild_boss', 'cosmo_raid_boss'):
        if battle.mc[switch] not in ('on', 'off'):
            raise ValueError(switch + ' 는 on|off')
    from importlib import import_module
    for switch, marker, adapter in registrations:
        if battle.mc[switch] == 'on' and any(getattr(d, marker, None) for w in waves for d in w):
            return import_module('.' + adapter, __package__).Controller(battle)
    return None
