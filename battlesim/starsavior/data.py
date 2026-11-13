# -*- coding: utf-8 -*-
"""스타세이비어 데이터 로딩: 저장소 루트(SRC) 결정, databook_main.json·synergy_tags.json·foe_stages.json 읽기."""
import json
import os

SRC = os.environ.get('PN_SRC', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')))  # 저장소 루트
OUT_DIR = os.path.join(SRC, 'tools', 'raw')  # 큰 중간 산출물(저장소 제외)

# ------------------------------------------------------------------ 데이터 로딩
class DB:
    def __init__(self, src=SRC):
        self.src = src
        with open(os.path.join(src, 'rawdata', 'databook_main.json'), encoding='utf-8') as f:
            self.main = json.load(f)
        with open(os.path.join(src, 'data', 'synergy_tags.json'), encoding='utf-8') as f:
            tg = json.load(f)
        self.tags = {(s['id'], s['variant']): s for s in tg['saviors']}
        self.units = {}
        chain_path = os.path.join(src, 'data', 'chain_damage.json')
        chain_types = {}
        if os.path.exists(chain_path):  # 이전 빌드의 고정 입력에는 유형 자료가 없음.
            with open(chain_path, encoding='utf-8') as f:
                chain_types = json.load(f)['units']
        for u in self.main['units']:
            t = self.tags.get((u['id'], u['v']))
            key = t['key'] if t else ('%s@%s' % (u['id'], u['v']))
            self.units[key] = u
            for sk in u['sk']:
                damage_type = chain_types.get(key, {}).get(sk['sl'])
                if damage_type:
                    sk['chain_damage_type'] = damage_type
        self._foe = None

    @property
    def foe(self):
        if self._foe is None:
            with open(os.path.join(self.src, 'data', 'foe_stages.json'), encoding='utf-8') as f:
                self._foe = json.load(f)
        return self._foe

    def find_stage(self, content, tab, name):
        for c in self.foe['contents']:
            if c['key'] != content:
                continue
            for t in c['tabs']:
                if t['tab'] != tab:
                    continue
                for s in t['stages']:
                    if s['name'] == name:
                        return s
        raise KeyError((content, tab, name))


_DB = None
def get_db():
    global _DB
    if _DB is None:
        _DB = DB()
    return _DB


def _find_key(db, q):
    if q in db.units:
        return q
    cands = [k for k, u in db.units.items() if u['n'] == q and u['v'] == '기본']
    if len(cands) == 1:
        return cands[0]
    if q.isdigit():
        c = [k for k, u in db.units.items() if str(u['id']) == q]
        if c:
            return c[0]
    cands = [k for k in db.units if q in k]
    if cands:
        return cands[0]
    raise ValueError('구원자를 찾을 수 없음: %s (이름 중복은 key 로: %s ...)' % (q, ', '.join(list(db.units)[:6])))
