"""Run the real selector CLIs in an isolated repository, then execute both raids."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class SeasonSelectorTest(unittest.TestCase):
    def test_dependency_content_and_cache_invalidation(self):
        from battlesim import api
        from battlesim.starsavior.boss_registry import dependency_digest
        from battlesim.starsavior.guild import check_dependencies
        scratch = ROOT/'local'
        scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='dependency-', dir=scratch) as tmp:
            path = Path(tmp)/'input.json'
            path.write_text('{"a":1,"b":2}', encoding='utf-8')
            entries = (('input.json', dependency_digest(path)),)
            check_dependencies(tmp, entries)
            path.write_text('{\n  "b": 2, "a": 1\n}', encoding='utf-8')
            api.clear_engine_caches()
            check_dependencies(tmp, entries)
            path.write_text('{"a":3,"b":2}', encoding='utf-8')
            api.clear_engine_caches()
            with self.assertRaisesRegex(ValueError, 'input.json'):
                check_dependencies(tmp, entries)
        api.clear_engine_caches()

    def test_select_and_reselect(self):
        scratch = ROOT / 'local'
        scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='season-select-', dir=scratch) as tmp:
            root = Path(tmp)
            for name in ('data', 'rawdata', 'battlesim', 'tools'):
                shutil.copytree(ROOT/name, root/name, ignore=shutil.ignore_patterns('__pycache__', 'raw'))
            for path in ROOT.glob('*.py'):
                shutil.copy2(path, root/path.name)
            shutil.copy2(ROOT/'party_contents.json', root/'party_contents.json')

            def run(*args):
                p = subprocess.run([sys.executable, '-X', 'utf8', '-B', *args], cwd=root,
                                   env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'),
                                   capture_output=True, text=True, encoding='utf-8')
                self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
                return p.stdout

            probe = (
                "from battlesim import api; from battlesim.starsavior import guild; "
                "guild.build_waves({'seasonId':30112}); "
                "r=api.simulate(['gwen','fei','professor-m','amora'],"
                "{'guild':{'seasonId':30112,'step':1}},"
                "{'build':'standard','seed':7,'n_runs':1}); "
                "assert r['outcome']['progress'] > 0; "
                "import json; print(json.dumps([r['outcome'],r['prog_runs']],sort_keys=True))"
            )
            before = run('-c', probe)
            for sid in (1022, 1023, 1023):
                run('tools/build_cosmo_raid.py', '--season', str(sid), '--select-only')
                self.assertEqual(run('-c', probe), before)
                projection = (root/'data/cosmo_raid.json').read_bytes()
                run('-c', "import json; from tools.build_cosmo_raid import save_season; "
                    "from pathlib import Path; p=Path('data/cosmo_raid.json'); "
                    "save_season(json.loads(p.read_text(encoding='utf-8')),p)")
                self.assertEqual((root/'data/cosmo_raid.json').read_bytes(), projection)
            cosmo = (root/'data/cosmo_raid.json').read_bytes()
            versions = []
            for sid in (30109, 30112, 30112):
                run('tools/build_guild_seasons.py', '--current', str(sid), '--select-only')
                self.assertEqual(run('-c', probe), before)
                self.assertEqual((root/'data/cosmo_raid.json').read_bytes(), cosmo)
                versions.append(json.loads((root/'data/guild_defense.json').read_text(encoding='utf-8'))['dataVersion'])
                run('-c', "from battlesim import api; "
                    "r=api.simulate(['gwen','fei','professor-m','amora'],{'guild':{'step':1}},"
                    "{'build':'standard','seed':7,'n_runs':1}); assert r['outcome']['progress'] > 0; "
                    "r=api.simulate(['gwen','fei','professor-m','amora'],{'cosmo_raid':{'step':1}},"
                    "{'build':'standard','seed':7,'n_runs':1}); assert r['outcome']['progress'] > 0")
            self.assertEqual(versions[-2], versions[-1])


if __name__ == '__main__':
    unittest.main()
