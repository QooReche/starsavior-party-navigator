"""Connect verified Cristelle/Asherah chain lines to native BuffId groups."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from battlesim.starsavior.data import get_db
from battlesim.starsavior.parser import Line
from tools.tables import jsonc


def build(tables):
    tables = Path(tables)
    rows = [r for n in (1, 2) for r in jsonc(tables / f'CLIENT_SE_TEMPLET_SKILL_{n}.json')['Data']]
    buffs = {r['m_BuffStrID']: r['m_BuffID'] for r in jsonc(tables / 'CLIENT_BUFF_TEMPLET.json')['Data']}
    targets = {r['Id']: r['TargetCondition'] for r in jsonc(tables / 'plain/AUTO_SKILL_TARGET_TEMPLET.json')['Data']}
    out = {}
    for key in ('cristelle', 'asherah-order-striker'):
        result = []
        for sk in get_db().units[key]['sk']:
            for raw in dict.fromkeys(sk.get('ef', []) + sk.get('L', {}).get('ln', [])):
                ln = Line(raw, sk['sl'], 'passive' if sk['sl'] == '고유 패시브' else 'active')
                if ln.eff['kind'] != 'chain':
                    continue
                params = dict(ln.params)
                if key == 'cristelle':
                    cond = 32157 + int(params['효과 개수 이상']) if sk['sl'] == '궁극기' else 31066
                    prefix = 'COND_INCOGNITA_LANDGRAVE_'
                    auto = None
                else:
                    prefix = 'COND_DARK_UNKNOWN_'
                    single = params.get('단일 대상 공격') == '예'
                    boss = ln.eff['coef'] >= 1
                    cond = (52200 if boss else 2171) if single else 2172
                    auto = None if single else (10611 if boss else 55)
                candidates = [r for r in rows if r.get('m_SEStrID', '').startswith(prefix)
                              and r.get('SkillConditionId') == cond and r.get('AutoTargetId') == auto
                              and r.get('AddDamageRate') == round(ln.eff['coef'] * 10000)]
                specs = set()
                for r in candidates:
                    assert r['AddDamageTargetType'] == 'NSETT_SELF' and r['AddDamageStatType'] == 'NST_ATK'
                    assert r['m_Condition']['m_fActiveRate'] == 10000
                    retarget = auto is not None and not targets[auto]
                    assert not retarget, 'Retargeting requires a separate verified mapping'
                    specs.add((buffs[r['m_BuffStrID']], retarget))
                if len(specs) != 1:
                    raise ValueError((key, raw, specs))
                bid, retarget = specs.pop()
                result.append([sk['sl'], raw, {'buff': bid, 'retarget': retarget}])
        assert len(result) == (6 if key == 'cristelle' else 12), (key, len(result))
        out[key] = result
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--tables', required=True, type=Path)
    args = ap.parse_args()
    data = {'_note': 'PC 26752678. Verified native chain groups; no automatic retargeting in these rows.',
            'units': build(args.tables)}
    (ROOT / 'data/chain_se.json').write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n', encoding='utf8')
    print({k: len(v) for k, v in data['units'].items()})
