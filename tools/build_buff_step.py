# -*- coding: utf-8 -*-
"""단계 그룹 버프(BUFF_STEP_TEMPLET) -> data/buff_step.json.

같은 BuffStepGroupId 의 버프끼리는 단계(BuffStep1..3 순서)가 높은 쪽이 이긴다(NKM:4283-4305).
엔진은 이름으로 효과를 저장하므로 «이름 -> [그룹, 단계]» 로 담는다. 같은 이름이 둘 이상의 (그룹, 단계)에
걸리면 이름만으로 단계를 못 가르므로 뺀다(10001 그룹 «잔재된 괴리» 3단계 등).

  python -X utf8 -I tools/build_buff_step.py --static <비공개 저장소>
원문 표는 출력에 넣지 않는다.
"""
import argparse
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.runtime import static_path                      # noqa: E402
from tools.tables import buff_names, rows                  # noqa: E402
from battlesim.fileio import atomic_json                   # noqa: E402


def extract(step_rows, bname, warn=print):
    found = defaultdict(set)
    for r in step_rows:
        g = r['BuffStepGroupId']
        step = 1
        while r.get('BuffStep%d' % step):
            sid = r['BuffStep%d' % step]
            name = bname.get(sid)
            if name:
                found[name].add((g, step))
            else:
                warn('이름 없는 단계 버프: %s (그룹 %s)' % (sid, g))
            step += 1
    out = {}
    for name, pairs in sorted(found.items()):
        if len(pairs) > 1:
            warn('단계 모호, 제외: %s %s' % (name, sorted(pairs)))
            continue
        out[name] = list(next(iter(pairs)))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--static', type=Path)
    ap.add_argument('--out', default=str(ROOT / 'data' / 'buff_step.json'))
    a = ap.parse_args()
    tables = static_path(a.static) / 'tables'
    names = extract(rows(tables / 'BUFF_STEP_TEMPLET.json'), buff_names(tables),
                    lambda m: print(m, file=sys.stderr))
    atomic_json(a.out, dict(
        _note='BUFF_STEP_TEMPLET: 이름 -> [단계 그룹 id, 단계]. 같은 그룹은 높은 단계가 이김(tools/build_buff_step.py).',
        names=names), indent=1)
    print('단계 그룹 버프 이름', len(names), '저장:', a.out)


if __name__ == '__main__':
    main()
