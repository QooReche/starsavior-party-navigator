"""Public synthetic interval fixtures. No account or private table contents."""
import inspect
import json
from pathlib import Path
import sys
import tempfile
import subprocess

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import build_cosmo_raid as builder


def audit(read=builder.season_period):
    (ROOT / 'local').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=ROOT / 'local') as tmp:
        path = Path(tmp) / 'CLIENT_INTERVAL_TEMPLET.json'
        key = 'DATE_TEST_PLAYABLE'
        unknown = dict(start=None, end=None)
        assert read(tmp, key) == unknown
        def write(rows):
            path.write_text(json.dumps(dict(Data=rows)), encoding='utf-8')
        row = dict(StrID=key, StartDate='2026-11-01 04:00:00', EndDate='2026-11-05 04:00:00')
        write([dict(row, StrID='DATE_TEST_REWARD', EndDate='2026-11-12 04:00:00'), row])
        expected = dict(start='2026-11-01T04:00:00+09:00', end='2026-11-05T04:00:00+09:00')
        assert read(tmp, key) == expected
        assert read(tmp, None) == unknown
        write([dict(row, StartDate='2026-10-31T19:00:00Z', EndDate='2026-11-04T19:00:00Z')])
        assert read(tmp, key) == expected
        for changed in [dict(row, EndDate=None), dict(row, StartDate='invalid'), dict(row, EndDate=row['StartDate']), dict(row, EndDate='2026-10-01')]:
            write([changed])
            assert read(tmp, key) == unknown
        write([row, dict(row, EndDate='2026-11-06 04:00:00')])
        assert read(tmp, key) == unknown, 'ambiguous interval must remain open/unknown'
        write([row, row])
        assert read(tmp, key) == expected


def dates_only_cli():
    with tempfile.TemporaryDirectory(dir=ROOT / 'local') as tmp:
        output = Path(tmp) / 'public.json'
        original = dict(season=dict(id=123, playableInterval='DATE_TEST', start='old', end='old'),
                        bosses=[dict(stats=dict(atk=123, hp=456))], search=dict(runs=7))
        output.write_text(json.dumps(original), encoding='utf-8')
        result = subprocess.run([sys.executable, '-X', 'utf8', '-I', str(ROOT / 'tools/build_cosmo_raid.py'),
                                 '--tables', tmp, '--season', '123', '--out', str(output), '--season-dates-only'],
                                capture_output=True, text=True, encoding='utf-8')
        assert result.returncode == 0, result.stdout + result.stderr
        original['season'].update(start=None, end=None)
        assert json.loads(output.read_text(encoding='utf-8')) == original


if __name__ == '__main__':
    audit()
    dates_only_cli()
    source = inspect.getsource(builder.season_period)
    for name, old, new in [('KST', 'hours=9', 'hours=0'), ('end boundary', 'start < end', 'start <= end'),
                           ('interval match', 'interval_id not in row.values()', 'False')]:
        assert old in source
        namespace = dict(vars(builder))
        exec(source.replace(old, new), namespace)
        try:
            audit(namespace['season_period'])
        except AssertionError:
            print('MUTATION caught:', name)
        else:
            raise AssertionError('mutation survived: ' + name)
    print('ALL OK season period; 3 mutations')
