"""Compare frozen simulation inputs while allowing guild search policy metadata."""
import json


def assert_engine_inputs(old_files, new_files, old_read, new_read):
    assert old_files == new_files, 'simulation file list changed'
    for name in old_files:
        before, after = old_read(name), new_read(name)
        if before == after:
            continue
        if name == 'data/guild_defense.json':
            before, after = json.loads(before), json.loads(after)
            for value in (before, after):
                # Search budgets/dispatch and explanatory text are not read by
                # the battle engine. Boss, challenge and score data stay pinned.
                value.pop('search', None)
                value.pop('_note', None)
        assert before == after, 'frozen simulation input changed: ' + name
