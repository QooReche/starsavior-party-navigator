"""Persist reusable definitions, without changing expanded runtime values."""
import copy
import json
from pathlib import Path
from battlesim.starsavior.boss_registry import fingerprint, expand
from battlesim.fileio import atomic_text
from battlesim import datafile

ROOT = Path(__file__).resolve().parents[1]
MONSTER_FIELDS = ('foe', 'foeSignature', 'definition', 'clientRules', 'hitStats',
                  'name', 'role', 'element')


def write(path, value):
    """One serialization for module archives and their expanded projections."""
    atomic_text(path, json.dumps(value, ensure_ascii=False, indent=1) + '\n')


def register(kind, definition, root=ROOT):
    key = kind + '-' + fingerprint(definition)
    path = root / 'data/boss_modules' / (key + '.json')
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        write(path, definition)
    elif json.loads(path.read_text(encoding='utf-8')) != definition:
        raise ValueError('보스 모듈 충돌: ' + key)
    return {'$module': key}


def pack_guild(value, root=ROOT):
    g = copy.deepcopy(value)
    if '$module' in g['season']['boss']:
        return g
    # Boss behavior and presentation live together; stage stats stay in the season.
    g['season']['boss'] = register('guild', g['season']['boss'], root)
    for step in g['steps']:
        for wave in step.get('waves', []):
            for member in wave:
                definition = {k: member.pop(k) for k in MONSTER_FIELDS if k in member}
                member.update(register('monster', definition, root))
    for field in ('gimmicks',):
        if field in g:
            g[field] = register(field, g[field], root)
    if 'client' in g:
        g['client'] = pack_guild(g['client'], root)
    return g


def pack_cosmo(value, root=ROOT):
    g = copy.deepcopy(value)
    fields = ('key', 'name', 'element', 'role', 'title', 'attackKind', 'unitId', 'immuneGroup')
    for boss in g['bosses']:
        if '$module' in boss:
            continue
        definition = {k: boss.pop(k) for k in fields if k in boss}
        boss.update(register('cosmo', definition, root))
    fields = {row['modelData'] for row in datafile.load('boss_catalog', str(root))['cosmo'].values()
              if row.get('modelData')}
    for field in fields:
        if g.get(field) and '$module' not in g[field]:
            g[field] = register('model', g[field], root)
    return g


def migrate(root=ROOT):
    paths = list((root/'data/guild_seasons').glob('*.json'))
    for path in paths:
        original = json.loads(path.read_text(encoding='utf-8'))
        packed = pack_guild(original, root)
        assert expand(packed, str(root)) == expand(original, str(root))
        write(path, packed)
    # Current cosmo projection stays compatible; the season archive is the source.
    paths = [root/'data/cosmo_raid.json', *sorted((root/'tests/fixtures').glob('cosmo_raid_*.json'))]
    for path in paths:
        original = json.loads(path.read_text(encoding='utf-8'))
        packed = pack_cosmo(original, root)
        assert expand(packed, str(root)) == original
        target = root/'data/cosmo_seasons'/('%s.json' % original['season']['id'])
        target.parent.mkdir(parents=True, exist_ok=True)
        write(target, packed)
    print('Module migration: expanded values unchanged, guild', len(paths))
