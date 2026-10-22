"""산출물 쓰기: UTF-8·LF, 같은 디렉터리의 임시 파일을 완성한 뒤 교체."""
import json
import os
from pathlib import Path
import tempfile
from contextlib import contextmanager


@contextmanager
def atomic_open(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as f:
            yield f
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def atomic_text(path, text):
    with atomic_open(path) as f:
        f.write(text.replace('\r\n', '\n').replace('\r', '\n'))


def atomic_json(path, value, **kwargs):
    atomic_text(path, json.dumps(value, ensure_ascii=False, **kwargs))


def read_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)
