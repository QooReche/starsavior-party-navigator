"""지원 진단의 양방향 허용 목록 래칫. 단일 프로세스, 공개 standard 입력만 사용함.

python -X utf8 -I tools/unsupported_allowlist.py --diff
python -X utf8 -I tools/unsupported_allowlist.py --write
새 항목은 사유/클라 확정 단서/담당을 비워 쓰며, 사람이 채우기 전 관문은 실패함.
"""
import argparse
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from battlesim import api
from battlesim.mc import support_report
from battlesim.rules import MC_OPTS
from battlesim.starsavior.data import get_db
from battlesim.starsavior.foe import stage_waves
from tools.runtime import low_priority

ALLOWLIST = ROOT / 'tests/fixtures/unsupported_allowlist.json'
SCENARIOS = ROOT / 'tests/fixtures/unsupported_scenarios.json'
AREAS = ('A', 'B', 'C', 'D', 'E')
RUNS = 3
SEED = 1


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def key(*parts):
    """구분자/줄바꿈이 들어간 원문도 충돌 없이 보존하는 키 문자열."""
    return json.dumps(parts, ensure_ascii=False, separators=(',', ':'))


def static_key(row):
    return key(*(row[field] for field in ('unit', 'slot', 'reason', 'raw', 'critical')))


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def collect(db=None, scenarios=None):
    started = time.perf_counter()
    db = get_db() if db is None else db
    cfg = read_json(SCENARIOS) if scenarios is None else scenarios
    require(bool(db.units), '구원자 0명: 자료 로딩 실패')
    # 시즌 교체 때 옛 보스만 검사하는 조용한 통과를 막음.
    current = read_json(ROOT / 'data/cosmo_raid.json')['season']['bossOrder']
    require(set(cfg['bosses']) == set(current) and len(cfg['bosses']) == 3,
            '현 시즌 3보스와 고정 시나리오가 다름: unsupported_scenarios.json 갱신 필요')
    encs = {boss: {'cosmo_raid': {'boss': boss, 'step': 3, 'level': 0}} for boss in cfg['bosses']}
    encs['guild'] = {'guild': {'level': 0}}
    season_encs = dict(encs)
    encs['stage'] = {'stage': cfg['stage']}
    found = {area: set() for area in AREAS}
    stats = dict(saviors=len(db.units), static_builds=0, stages=0, scenarios=0, runs=0)
    runtime_started = time.perf_counter()

    def run(party, encounter, area, scope, options=None):
        opts = dict(n_runs=RUNS, seed=SEED, build='standard', **(options or {}))
        try:
            result = api.simulate(party, encounter, opts)
            progress = result['prog_runs']
            require(len(progress) == RUNS, '요청한 3판이 모두 반환되지 않음')
            require(any(p > 0 for p in progress), '진행도 0: 진단 경로를 검사할 수 없는 시나리오')
            runtime = result['unsupported']['runtime']
            require(isinstance(runtime, dict), 'runtime 키 사전 누락')
            found[area].update(key(*scope, item) for item in runtime)
            found['D'].update(key('rule', row['rule']) for row in result['assumptions_used'])
            if 'cosmo_raid' in encounter:
                raid = result['cosmo_raid']
                found['D'].add(key('score_conf', raid['score_conf']))
                found['D'].update(key('cosmo_approx', text) for text in raid['approx'])
        except Exception as exc:
            raise AssertionError('시나리오 실행 실패 %s: %s' % (scope, exc)) from exc
        stats['scenarios'] += 1
        stats['runs'] += RUNS

    for unit in sorted(db.units):
        for build in ('standard', 'none'):
            defs, _ = api._norm_party_raw({'units': [{'key': unit, 'build': build}]},
                                          db, 'fixed', build, MC_OPTS)
            require(len(defs) == 1, '구원자 정적 정의 누락: ' + unit)
            found['A'].update(key(unit, build, static_key(row)) for row in support_report(defs))
            stats['static_builds'] += 1
        fill = cfg['fill_alternate'] if unit in cfg['fill'] else cfg['fill']
        party = [unit] + fill
        require(len(party) == len(set(party)) == 4 and all(u in db.units for u in party),
                '채움 파티는 존재하는 서로 다른 4형태여야 함: ' + unit)
        for name, encounter in encs.items():
            run(party, encounter, 'B', (unit, name))

    covered = set()
    for sample in cfg['season_samples']:
        name = sample['encounter']
        require(name in season_encs, '상위 편성 표본의 알 수 없는 보스: ' + name)
        require(len(sample['party']) == len(set(sample['party'])) == 4 and
                all(u in db.units for u in sample['party']), '상위 편성 표본 구원자 누락')
        run({'units': sample['party'], 'leader': sample['leader']},
            sample['spec'], 'C', ('runtime', name), sample.get('options'))
        require(('guild' in sample['spec']) if name == 'guild' else
                sample['spec'].get('cosmo_raid', {}).get('boss') == name,
                '표본 encounter와 spec 불일치')
        covered.add(name)
    require(covered == set(season_encs), '현 시즌 적 runtime 표본 누락')
    stats['runtime_seconds'] = round(time.perf_counter() - runtime_started, 3)

    for name, encounter in season_encs.items():
        waves = api._norm_encounter_raw(encounter)[0]
        require(bool(waves) and all(waves), '현 시즌 적 waves 누락: ' + name)
        found['C'].update(key('static', name, static_key(row))
                          for row in support_report([d for wave in waves for d in wave]))
    # Stage별 보고를 먼저 만들고 고유 줄로 합침. 유닛만 합치면 표지 상호참조가 달라짐.
    for content in db.foe['contents']:
        for tab in content['tabs']:
            for stage in tab['stages']:
                _, waves = stage_waves(content['key'], tab['tab'], stage['name'])
                require(bool(waves) and all(waves), '일반 콘텐츠 적 waves 누락: ' + stage['name'])
                found['E'].update(static_key(row) for row in support_report([d for wave in waves for d in wave]))
                stats['stages'] += 1
    require(stats['stages'] > 0, '일반 콘텐츠 스테이지 0개: 자료 로딩 실패')
    stats['seconds'] = round(time.perf_counter() - started, 3)
    return found, stats


def entries(document):
    require(document.get('version') == 1, '허용 목록 version 오류')
    require(set(document.get('areas', {})) == set(AREAS), '허용 목록 영역 A~E 누락/추가')
    mapped = {}
    for area in AREAS:
        rows = document['areas'][area]
        require(isinstance(rows, list), '허용 목록 영역은 배열이어야 함: ' + area)
        mapped[area] = {}
        for row in rows:
            require(isinstance(row.get('key'), str) and bool(row['key'].strip()), '빈 진단 키: ' + area)
            require(row['key'] not in mapped[area], '중복 진단 키: ' + row['key'])
            mapped[area][row['key']] = row
    return mapped


def differences(found, document):
    allowed = entries(document)
    require(set(found) == set(AREAS), '수집 영역 A~E 누락/추가')
    return {area: {'added': sorted(found[area] - allowed[area].keys()),
                   'removed': sorted(allowed[area].keys() - found[area])} for area in AREAS}


def assert_gate(found, document):
    delta = differences(found, document)
    errors = []
    for area, changes in delta.items():
        errors.extend('%s 새 항목: 클라로 확정하거나 사유와 함께 등록: %s' % (area, k) for k in changes['added'])
        errors.extend('%s 해소됨, 목록에서 지우기: %s' % (area, k) for k in changes['removed'])
    for area, rows in entries(document).items():
        for k, row in rows.items():
            for field in ('reason', 'client_clue', 'owner'):
                if not isinstance(row.get(field), str) or not row[field].strip():
                    errors.append('%s %s 빈칸: %s' % (area, field, k))
    require(not errors, '\n'.join(errors))


def refreshed(found, document):
    previous = entries(document)
    return dict(version=1, areas={area: [previous[area].get(k, dict(key=k, reason='', client_clue='', owner=''))
                                       for k in sorted(found[area])] for area in AREAS})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--diff', action='store_true')
    mode.add_argument('--write', action='store_true')
    args = parser.parse_args()
    low_priority()
    document = read_json(ALLOWLIST) if ALLOWLIST.exists() else dict(version=1, areas={a: [] for a in AREAS})
    found, stats = collect()
    print(json.dumps({'measurement': stats, 'counts': {a: len(found[a]) for a in AREAS}}, ensure_ascii=False))
    for area, changes in differences(found, document).items():
        for status, keys in changes.items():
            for item in keys:
                print('%s %s %s' % (area, status, item))
    if args.write:
        document = refreshed(found, document)
        ALLOWLIST.write_text(json.dumps(document, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print('허용 목록 저장함. 새 항목의 reason/client_clue/owner를 채운 뒤 --diff로 확인하기.')
    try:
        assert_gate(found, document)
    except AssertionError as exc:
        print(exc)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
