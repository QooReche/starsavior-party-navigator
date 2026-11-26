"""Reusable boss/monster definitions. Seasons contain layouts and module references.

Module names are content hashes: registering another build never silently changes an
archived season. Expanded projections keep the existing engine/UI contracts.
"""
import copy
import hashlib
import json
from .. import datafile
from .data import SRC


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()


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
