"""Compare frozen simulation inputs while allowing guild search policy metadata."""
import json


def comparison_payload(value, package_version):
    """Validate the actual package tag before comparing all simulation fields."""
    out = {key: item for key, item in value.items() if key != 'pins'}
    replies = []
    for key, result in value['replies']:
        assert result['ver'] == package_version, 'worker package version mismatch'
        replies.append([key, {name: item for name, item in result.items() if name != 'ver'}])
    out['replies'] = replies
    return out


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
