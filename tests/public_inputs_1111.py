"""P1/P2 regression and old private-build checks use their original PUBLIC inputs.

Captured from 2e455c5; expected hashes/results are never rewritten. This does
not cover 11/12 accuracy: patch_1112_test exercises the current public data.
Remove the old private-build use after re-extracting the 11/12 client tables.
"""
from contextlib import contextmanager, ExitStack
import gzip
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


@contextmanager
def public_inputs():
    from battlesim.starsavior import data, build
    from battlesim import metrics
    from tools import build_growth, build_myinfo_combat
    files = json.loads(gzip.decompress((ROOT / 'tests/fixtures/public_inputs_1111.json.gz').read_bytes()))
    work = ROOT / 'local'
    work.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='public-1111-', dir=work) as tmp, ExitStack() as stack:
        root = Path(tmp)
        for name, text in files.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding='utf8')
        db = data.DB(tmp)
        for obj, name, value in [(data, '_DB', db), (build_growth, 'ROOT', root),
                                  (build_myinfo_combat, 'ROOT', root), (build, '_GUIDE', None),
                                  (build, '_RULES', None),
                                  (build, 'RULES_PATH', str(root / 'battlesim/rules/builds.json'))]:
            stack.enter_context(patch.object(obj, name, value))
        metrics._CACHE.clear()
        try:
            yield db
        finally:
            metrics._CACHE.clear()


@contextmanager
def recommendation_inputs():
    import party_reco as pr
    with public_inputs() as db, ExitStack() as stack:
        original = pr._json
        def read(path):
            relative = Path(path).relative_to(ROOT)
            frozen = Path(db.src) / relative
            return original(frozen if frozen.is_file() else path)
        stack.enter_context(patch.object(pr, '_json', read))
        for name in ('_DI', '_GCACHE', '_SYN_IDX'):
            stack.enter_context(patch.object(pr, name, {}))
        yield
