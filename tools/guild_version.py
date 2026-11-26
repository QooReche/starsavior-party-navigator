"""길드 자료 버전의 유일한 계산 경로. 펼친 시즌 정의를 입력받는다.

표시·근거로 확인한 필드만 제외한다. 이름/설명도 엔진이 읽을 수 있으므로
일반 name/text/desc는 유지하며, 특히 sets.items[].tiers[].text는 계산 입력임.
"""
import hashlib
import json

# 시즌/효과/배치에 붙이는 표시·추출 근거 메타. 실행 값과 의존 자료 해시는 유지함.
DISPLAY_KEYS = frozenset({
    'effectText', 'note', 'statNote', 'provenance', 'asOf', 'gameBuild',
    'source', 'sources', 'src', 'conf', '_note', 'minionsNote',
})
# 범위를 제한해야 안전한 표시 필드. client는 BFB의 일반 단계 실행 정의임.
DISPLAY_PATHS = frozenset({
    ('season', 'label'), ('season', 'name'), ('season', 'start'),
    ('season', 'end'), ('season', 'settleEnd'), ('season', 'intervals'),
    ('sets', 'scope'), ('sets', 'items', '*', 'name'),
    ('supports', '*', 'name'),
    ('score', 'hypotheses', '*', 'name'), ('score', 'hypotheses', '*', 'desc'),
    ('search', 'excludeWhy'),
})


def calculation_payload(value, path=()):
    if isinstance(value, list):
        return [calculation_payload(v, path + ('*',)) for v in value]
    if not isinstance(value, dict):
        return value
    return {
        k: calculation_payload(v, () if not path and k == 'client' else path + (k,))
        for k, v in value.items()
        if k not in DISPLAY_KEYS and path + (k,) not in DISPLAY_PATHS
        and not (not path and k == 'dataVersion')
    }


def season_version(season):
    payload = calculation_payload(season)
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode()).hexdigest()
