# -*- coding: utf-8 -*-
"""
sim_damage.py - 호환용 얇은 껍데기. 실제 코드는 저장소 루트의 battlesim/ 패키지(구성은 battlesim/README.md).

예전처럼 `python -X utf8 -I tools/sim_damage.py {index,stats,party,stage,unit,lines} ...` 로 실행하고,
`import sim_damage as sd` 로 쓰던 이름(sd.get_db, sd.build_index, sd.simulate_party, sd.Sim ...)도 그대로 쓸 수 있다.
한 파일이던 시절과 같게 동작하도록, `sd.X = 값` 은 같은 객체를 들고 있는 battlesim 모듈 전부에 전달하고(상수·함수·클래스 교체 실험),
실행 중 다시 할당되는 전역(_DB, _CACHE)은 읽을 때마다 실제 모듈 값을 돌려준다.
"""
import argparse  # noqa: F401
import json  # noqa: F401
import math  # noqa: F401
import os
import re  # noqa: F401
import statistics  # noqa: F401
import sys
from collections import defaultdict  # noqa: F401

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)   # -I 실행은 스크립트 폴더·현재 폴더를 import 경로에서 뺀다

from battlesim.rules import (  # noqa: E402,F401
    AOE_DIV, ASSUMPTIONS, BASE_MULT, COOP_CAP, DEF_K, DEFAULT_OPTS, ELEM_BEATS, ELEM_LOSES, FOE_ELEM, INF_HP, KNOWN_DOT,
    TICK_PER_TURN,
)
from battlesim.starsavior.data import DB, OUT_DIR, SRC, _DB, _find_key, get_db  # noqa: E402,F401  (_DB 는 아래 _LIVE 로 대체)
from battlesim.starsavior.stats import STAT_MODES, calc_stats  # noqa: E402,F401
from battlesim.starsavior.parser import (  # noqa: E402,F401
    NUM, Line, Skill, UnitDef, _map_prop, _perm_apply, parse_cond, parse_effect, parse_flags, parse_props, split_head, trig_kind,
)
from battlesim.engine import Actor, Buff, Ctx, DummyDef, Enemy, Sim, _patch_dummy, clamp, dummy_dmg_hook  # noqa: E402,F401
from battlesim.metrics import (  # noqa: E402,F401
    STAGES, _CACHE, ally_gain, build_index, describe, mechanics, ref_enemies, simulate_party, solo_run, stage_enemies,
    stage_report, unit_def, unit_metrics,
)
from battlesim.cli import dump_lines, main  # noqa: E402,F401
import types  # noqa: E402
import battlesim.cli  # noqa: E402,F401

_LIVE = {'_DB': 'battlesim.starsavior.data', '_CACHE': 'battlesim.metrics'}   # 실행 중 재할당되는 전역 -> 항상 실제 값
for _n in _LIVE:
    del globals()[_n]


def _bs_modules():
    return [m for k, m in list(sys.modules.items()) if m is not None and (k == 'battlesim' or k.startswith('battlesim.'))]


class _Shim(types.ModuleType):
    def __getattr__(self, name):
        if name in _LIVE:
            return getattr(sys.modules[_LIVE[name]], name)
        raise AttributeError(name)

    def __setattr__(self, name, value):
        if name in _LIVE:
            setattr(sys.modules[_LIVE[name]], name, value)
            return
        old = self.__dict__.get(name, _Shim)
        if old is not _Shim:
            for m in _bs_modules():
                if getattr(m, name, _Shim) is old:
                    setattr(m, name, value)
        super().__setattr__(name, value)


sys.modules[__name__].__class__ = _Shim

if __name__ == '__main__':
    main()
