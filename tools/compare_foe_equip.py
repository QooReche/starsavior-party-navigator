"""장비 클라 직행 1~20단계와 데이터북의 엔진 입력을 필드별 대조한다."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from battlesim import datafile
from battlesim.fileio import atomic_json
from battlesim.starsavior.foe import FoeDef
from tools.build_foe_equip import build, databook
from tools.runtime import static_path


def stages(raw):
    return {(t['t'], s['n']): s for g in raw['g'] if g['k'] == 'equip'
            for t in g['tabs'] for s in t['s']}


def plain(value):
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, set):
        return sorted(plain(v) for v in value)
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    return value


def unit_input(raw, entry, st, *, client=False):
    d = FoeDef(raw, entry[0], entry[1] if len(entry) > 1 else None, st,
               key_override='equip-client:%d' % entry[0] if client else None)
    fields = ('name', 'role', 'element', 'grade', 'boss', 'attack_kind', 'level', 'stats', 'immune',
              'passive', 'nb', 'react', 'auto', 'auto_lines', 'force_lines', 'enforce_self', 'skill_order', 'unmodeled')
    out = {k: plain(getattr(d, k)) for k in fields}
    out['skills'] = {slot: {k: plain(getattr(sk, k)) for k in
                           ('name', 'ty', 'tg', 'is_attack', 'cf', 'all', 'nv', 'ab')}
                     | {'cd': sk.cd or 0} for slot, sk in d.skills.items()}
    out['lines'] = [{k: plain(getattr(ln, k)) for k in ln.__slots__} for ln in d.lines]
    # 스킬 카드 링크(kind=스킬)는 실행 중 상태 효과가 아님.
    out['effect_info'] = {k: v for k, v in d.effect_info.items() if v['kind'] != '스킬'}
    return out


def compare(raw, frag):
    old, new = stages(raw), stages(frag)
    client = dict(frag, ak=raw['ak'])
    counts, examples = Counter(), {}
    units = summons = skill_count = line_count = 0
    checks = Counter()

    def check(field, a, b, where):
        checks[field] += 1
        if a != b:
            counts[field] += 1
            if len(examples.setdefault(field, [])) < 3:
                examples[field].append(dict(stage=where, databook=a, client=b))

    def enemy(a, b, os, ns, where):
        nonlocal units, skill_count, line_count
        x, y = unit_input(raw, a, os), unit_input(client, b, ns, client=True)
        units += 1
        skill_count += len(y['skills'])
        line_count += len(y['lines'])
        for k in x:
            check('unit.' + k, x[k], y[k], where)

    spawn = datafile.load('foe_spawn')
    summon = datafile.load('foe_summon')
    boss = set(datafile.load('battle_end')['boss_kill'])
    check('stage.missing', [], sorted(old.keys() - new.keys()), 'all')
    for key in sorted(old.keys() & new.keys()):
        os, ns = old[key], new[key]
        where = '|'.join(('equip', *key))
        for field in ('lv', 'bp', 'lt', 'fx', 'fix'):
            check('stage.' + field, os.get(field), ns.get(field), where)
        check('stage.waves', list(map(len, os['w'])), list(map(len, ns['w'])), where)
        for ow, nw in zip(os['w'], ns['w']):
            for a, b in zip(ow, nw):
                enemy(a, b, os, ns, where)
        for field, default in (('spawn', None), ('slots', None), ('deck', 'BATTLE_SLOT_4')):
            vals = spawn['stages' if field == 'spawn' else field]
            check('stage.' + field, vals.get(where, default), frag['aux'][field].get(where, default), where)
        check('stage.boss_kill', where in boss, where in frag['boss_kill'], where)
        check('stage.summons', [(x[0], x[1], sum(e[2] for e in x[2])) for x in os.get('sm', [])],
              [(x[0], x[1], sum(e[2] for e in x[2])) for x in ns.get('sm', [])], where)
        for a, b in zip(os.get('sm', []), ns.get('sm', [])):
            aa = [e[:2] for e in a[2] for _ in range(e[2])]
            bb = [e[:2] for e in b[2] for _ in range(e[2])]
            for x, y in zip(aa, bb):
                enemy(x, y, os, ns, where + '|summon')
                summons += 1
            check('stage.summon_slots', summon['groups'][str(a[0])], frag['aux']['summon_groups'][str(b[0])], where)
    return dict(stages=len(old.keys() & new.keys()), added=sorted(new.keys() - old.keys()), units=units, summons=summons,
                active_skills=skill_count, lines=line_count, checks=dict(checks),
                differences=dict(counts), examples=examples)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--static', type=Path)
    ap.add_argument('--fragment', type=Path, help='이미 만든 --all-stages 조각을 재사용')
    ap.add_argument('--out', type=Path, required=True, help='local/ 아래 대조 결과')
    args = ap.parse_args()
    raw = databook()
    frag = json.loads(args.fragment.read_text(encoding='utf-8')) if args.fragment else build(static_path(args.static), raw, all_stages=True)
    result = compare(raw, frag)
    atomic_json(args.out, result)
    print(json.dumps({k: v for k, v in result.items() if k != 'examples'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
