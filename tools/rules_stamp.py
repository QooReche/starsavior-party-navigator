# -*- coding: utf-8 -*-
"""생성물(data/guild_sim.json·data/quick.json)이 어느 엔진 규칙으로 만들어졌는지 기록·대조한다.

규칙 기본값(battlesim/rules/default.json 의 formula·opts·mc 값)을 바꾸면 지문이 달라지고,
tests/gen_rules_stamp_test.py 가 «생성물이 옛 규칙 기준»이라고 실패한다. 처리 방법은 둘 중 하나:
  1) 생성물을 다시 만든다 — 빌더(build_guild_sim.py, calibrate_quick.py --write)가 끝에 도장을 새로 찍음.
  2) 다시 만들 필요가 없음을 확인했으면(새 키를 쓰는 데이터가 없음, 결과 해시가 같음 등) 이유를 적어 인정:
       python -X utf8 -I tools/rules_stamp.py --ack guild_sim --reason "이유"
     인정 이유는 tools/gen_rules_stamp.json 의 history 에 남는다(이유 없는 인정은 거부).

  python -X utf8 -I tools/rules_stamp.py            # 현재 지문과 도장 비교
"""
import argparse
import hashlib
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
STAMP = os.path.join(ROOT, 'tools', 'gen_rules_stamp.json')
NAMES = ('guild_sim', 'quick')


def fingerprint():
    sys.path.insert(0, ROOT)
    from battlesim import rules
    payload = {'formula': rules._F, 'opts': rules._O, 'mc': rules.MC_OPTS}
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(blob.encode('utf-8')).hexdigest()[:16]


def load():
    if not os.path.exists(STAMP):
        return {}
    with open(STAMP, encoding='utf-8') as f:
        return json.load(f)


def stamp(name, reason):
    """도장을 현재 지문으로 갱신하고 이유를 기록한다."""
    if name not in NAMES:
        raise ValueError('모르는 생성물: %s' % name)
    if not reason or not reason.strip():
        raise ValueError('이유가 필요함')
    data = load()
    entry = data.setdefault(name, {'hash': '', 'history': []})
    fp = fingerprint()
    entry['hash'] = fp
    entry['history'].append({'hash': fp, 'reason': reason.strip()})
    entry['history'] = entry['history'][-10:]
    with open(STAMP, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write('\n')
    return fp


def stale():
    """지문이 도장과 다른 생성물 이름 목록(도장이 없으면 그 이름도 포함)."""
    data, fp = load(), fingerprint()
    return [n for n in NAMES if data.get(n, {}).get('hash') != fp]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ack', choices=NAMES, help='다시 만들지 않고 현재 규칙을 인정(--reason 필수)')
    ap.add_argument('--reason')
    a = ap.parse_args()
    if a.ack:
        try:
            print('도장', a.ack, stamp(a.ack, a.reason))
        except ValueError as e:
            print('오류:', e)
            return 2
        return 0
    bad = stale()
    print('현재 지문', fingerprint())
    for n in NAMES:
        print(' ', n, '일치' if n not in bad else '옛 규칙 기준')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
