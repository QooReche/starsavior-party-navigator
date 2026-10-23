"""Export validated stage victory modes; no private IDs or original rows."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import build_foe_spawn as spawn
from tools.runtime import static_path, low_priority
from battlesim.fileio import atomic_text


def build(static):
    modes = {}
    for path in (Path(static) / 'tables').glob('BATTLE_TEMPLET_*.json'):
        for row in json.loads(path.read_text(encoding='utf-8'))['Data']:
            modes[row['BattleStrID']] = row.get('BattleMode')
    matched = {}
    spawn.build(static, matched)
    rows = spawn.battle_rows(static)
    raw = spawn.F.load_foe(str(ROOT))
    out = []
    for content in raw['g']:
        for tab in content['tabs']:
            for stage in tab['s']:
                key = '%s|%s|%s' % (content['k'], tab['t'], stage['n'])
                bid = matched.get(key)
                if modes.get(bid) != 'BM_BOSS_KILL':
                    continue
                # Victory depends on IsBoss, not on the enemy's display grade.
                # Only export stages whose runtime boss flags match every slot.
                _, waves = spawn.F.stage_waves(content['k'], tab['t'], stage['n'])
                native = spawn.jsonc(rows[bid][0])['Data']['Waves']
                if [[d.boss for d in w] for w in waves] != [
                        [bool(u.get('IsBoss')) for u in w['TeamBSpawnList']] for w in native]:
                    continue
                out.append(key)
    return sorted(out)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--static', type=Path)
    args = ap.parse_args()
    low_priority()
    stages = build(static_path(args.static))
    out = dict(_note='BM_BOSS_KILL stages matched by build_foe_spawn; other stages retain all-kill behavior.',
               boss_kill=stages)
    atomic_text(ROOT / 'data/battle_end.json', json.dumps(out, ensure_ascii=False, separators=(',', ':')) + '\n')
    print('boss_kill stages:', len(stages))
