"""chain_timing 통합 큐가 빠른 계산 보정 표본(clear>=0.5 판정)에 주는 영향.

보정 표본 파일(tools/raw/quick_calib.json 형식, 계정 자료 아님)을 읽어 통합 큐 대상 줄이 있는 표본만
before(chain_timing=client_mapped)·after(기본)로 같은 시드·판 수로 다시 계산한다. 단일 프로세스.
대상 = 스테이지 적에 원형 연결된 연쇄 줄이 있거나(data/chain_se.json foes), 벨그라스 스테이지이거나,
시즌 컨트롤러 전투에서 원형 연결된 구원자 연쇄(크리스텔·아세라)가 있는 표본.

사용: python -X utf8 -I tools/measure_conn_quick.py <quick_calib.json> <출력.json> [--runs 40]
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import gen_quick_calib as G   # noqa: E402
from tools.runtime import low_priority   # noqa: E402


def affected(ck, sk, keys):
    from battlesim.starsavior import chain_se, belgras_se
    from battlesim.starsavior.foe import stage_waves
    from battlesim.starsavior.mc_semantics import normalized_lines
    tab, name = sk.split('|', 1)
    _, waves = stage_waves(ck, tab, name)
    defs = [d for w in waves for d in w]
    if any(belgras_se.is_stage(d) for d in defs):
        return 'belgras'
    for d in defs:
        for ln in normalized_lines(d):
            if ln.eff['kind'] == 'chain' and chain_se.foes().get(d.key, {}).get((ln.slot, ln.raw)):
                return 'foe_chain'
    if any(getattr(d, 'bfb', None) or getattr(d, 'cosmo', None) for d in defs) and set(keys) & set(chain_se.data()):
        return 'savior_chain_season'
    return None


def run(ck, sk, team_key, g, runs, override):
    from battlesim import simulate
    q, _ = G.quick_data(G.ROOT)
    st = q['st'][ck][sk]
    order = next(o for c, s, t, o, L in G.teams() if (c, s, t) == (ck, sk, team_key))
    lead = next(L for c, s, t, o, L in G.teams() if (c, s, t) == (ck, sk, team_key))
    spec = G.party_spec(q, order, lead, team_key.split(','), g, st)
    tab, name = sk.split('|', 1)
    r = simulate(spec, {'stage': '%s/%s/%s' % (ck, tab, name)},
                 dict(G.SIMOPT, n_runs=runs, seed=7, rules_override=dict(G.SIMOPT['rules_override'], **override)))
    return r['outcome']['clear_p']


def main():
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    runs = int(sys.argv[sys.argv.index('--runs') + 1]) if '--runs' in sys.argv else 40
    low_priority()
    rows = json.loads(src.read_text(encoding='utf-8'))['rows']
    teams = {(c, s, t) for c, s, t, o, L in G.teams()}
    todo = []
    for ck, sk, tk, g, c in (r[:5] for r in rows):
        if (ck, sk, tk) not in teams:
            continue
        why = affected(ck, sk, tk.split(','))
        if why:
            todo.append((ck, sk, tk, g, why))
    print('전체', len(rows), '대상', len(todo), flush=True)
    res = []
    for i, (ck, sk, tk, g, why) in enumerate(todo):
        before = run(ck, sk, tk, g, runs, {'chain_timing': 'client_mapped'})
        after = run(ck, sk, tk, g, runs, {})
        res.append(dict(ck=ck, sk=sk, team=tk, growth=g, why=why, before=before, after=after))
        if (i + 1) % 20 == 0:
            print(i + 1, flush=True)
            out.write_text(json.dumps(res, ensure_ascii=False), encoding='utf-8')
    out.write_text(json.dumps(res, ensure_ascii=False), encoding='utf-8')
    changed = [r for r in res if r['before'] != r['after']]
    flips = [r for r in res if (r['before'] >= 0.5) != (r['after'] >= 0.5)]
    print('대상', len(res), '확률 변경', len(changed), 'clear>=0.5 판정 변경', len(flips))
    for r in flips:
        print(' ', r)


if __name__ == '__main__':
    main()
