# -*- coding: utf-8 -*-
"""Python 구현과 JS 구현을 대조하는 시험이 함께 쓰는 node 도우미."""
import json
import os
import subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))


def node_available():
    try:
        subprocess.run(['node', '-v'], capture_output=True, check=True)
        return True
    except (OSError, subprocess.CalledProcessError):
        return False


def node_json(code):
    """저장소 루트에서 node -e 로 code 를 돌리고 stdout 의 JSON 을 돌려줌."""
    p = subprocess.run(['node', '-e', code], capture_output=True, text=True, encoding='utf-8', cwd=ROOT)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout)
