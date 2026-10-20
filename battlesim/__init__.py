# -*- coding: utf-8 -*-
"""전투 시뮬레이터 패키지. 구성은 battlesim/README.md."""


def simulate(party_spec, encounter_spec, options=None):
    """P3 확률 엔진 진입점(재사용 계약, docs/battlesim_design.md 2절). 상세는 battlesim.api.simulate."""
    from .api import simulate as _simulate   # 패키지 import 만으로 엔진·데이터를 읽지 않도록 지연 import
    return _simulate(party_spec, encounter_spec, options)
