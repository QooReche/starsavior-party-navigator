import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine_input_guard import assert_engine_inputs, comparison_payload

FILES = ['battlesim/mc.py', 'data/guild_defense.json']
old = {FILES[0]: b'original engine', FILES[1]: json.dumps({'boss': {'hp': 100}, 'search': {'execution': {'chunk': 8}}, '_note': 'old'}).encode()}
new = dict(old)
new[FILES[1]] = json.dumps({'boss': {'hp': 100}, 'search': {'execution': {'chunk': 1}}, '_note': 'new'}).encode()
assert_engine_inputs(FILES, FILES, old.__getitem__, new.__getitem__)


def rejected(files, data):
    try:
        assert_engine_inputs(FILES, files, old.__getitem__, data.__getitem__)
    except AssertionError:
        return
    raise AssertionError('changed engine input was accepted')


rejected(FILES, {**new, FILES[0]: b'mutated engine'})
rejected(FILES, {**new, FILES[1]: json.dumps({'boss': {'hp': 101}, 'search': {}}).encode()})
rejected(FILES + ['extra.py'], new)
a = {'requests': [{'seed': 1}], 'replies': [['x', {'ver': 'old', 'prog': .5, 'raw': '[1]'}]], 'result': {'x': {'prog': .5}}}
b = {**a, 'replies': [['x', {'ver': 'new', 'prog': .5, 'raw': '[1]'}]]}
assert comparison_payload(a, 'old') == comparison_payload(b, 'new')
try:
    comparison_payload(b, 'wrong-package')
except AssertionError:
    pass
else:
    raise AssertionError('wrong worker package accepted')
assert comparison_payload(a, 'old') != comparison_payload({**b, 'requests': [{'seed': 2}]}, 'new')
assert comparison_payload(a, 'old') != comparison_payload({**b, 'replies': [['x', {'ver': 'new', 'prog': .6, 'raw': '[1]'}]]}, 'new')
assert comparison_payload(a, 'old') != comparison_payload({**b, 'replies': [['x', {'ver': 'new', 'prog': .5, 'raw': '[2]'}]]}, 'new')
print('PASS metadata allowed; engine/boss/file-list/package/request/progress/raw mutations rejected')
