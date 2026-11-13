"""자신이 얻는 상태와 그 상태인 아군 대상 지원의 연결 후보. 원문 줄을 함께 반환함."""
import re


def links(units, parse_line):
    grants, supports = [], []
    for i, unit in enumerate(units):
        for skill in unit['sk']:
            for raw in skill.get('ef', []):
                line = parse_line(raw)
                if not line:
                    continue
                grant = re.match(r'^〈([^〉]+)〉', line['eff']) if line['tgt'] == '자신' else None
                if grant:
                    grants.append((i, grant[1], skill['n'] + ': ' + raw))
                support = re.match(r'^「([^」]+)」 상태인 아군 전체에게 (.+)$', line['eff'])
                if support:
                    supports.append((i, support[1], skill['n'] + ': ' + raw, support[2]))
    for a, status, grant in grants:
        for b, required, support, effect in supports:
            if a != b and status == required:
                yield a, b, status, grant, support, effect
