# -*- coding: utf-8 -*-
"""적 정의(데이터북 유닛·변형) ↔ 클라 스킬 SE 행 연결. 연쇄 빌더·효과 대응 감사가 같이 쓴다.

연결은 build_foe_auto 와 같은 규칙만 쓴다(추정 없음):
- 유닛: 조건에 맞는 배치가 하나뿐인 스테이지에서 칸 역할·속성이 같을 때(build_foe_auto.unit_links).
  길드 방어전은 GUILD_DUNGEON_* 중 권장 전투력·레벨과 칸별 적 이름이 모두 같은 배치만(guild=True).
- 스킬: 게임 스킬 _ATTACK/_SPECIAL/_HYPER = 기본기/특수기/궁극기(반응·두 번째 스킬 제외),
  _PASSIVE 는 수가 같을 때만 순서대로(build_foe_auto.unit_rules 와 같음).
- 줄: SkillLevelSE 순서의 SE 행과 데이터북 ef 줄을 줄 수·대상 머리말로 짝지음(build_foe_auto.pair_lines).
"""
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import build_foe_auto as FA   # noqa: E402
from tools.tables import jsonc   # noqa: E402
from battlesim.starsavior import foe as F   # noqa: E402


class Tables:
    """static 형태 폴더(tools/client_view.py 출력)의 표."""

    def __init__(self, static):
        self.static = Path(static)
        t = self.static / 'tables'
        self.units = {}
        for n in (1, 2, 3, 4):
            for u in json.loads((t / ('UNIT_TEMPLET_BASE%d.json' % n)).read_text(encoding='utf-8'))['Data']:
                self.units[u['m_UnitStrID']] = u
        self.skills = {}
        for n in (1, 2):
            for r in json.loads((t / ('SKILL_TEMPLET_%d.json' % n)).read_text(encoding='utf-8'))['Data']:
                self.skills[r['m_SkillStrID']] = r
        self.target = {r['Id']: r['TargetCondition'] for r in jsonc(t / 'Plain' / 'AUTO_SKILL_TARGET_TEMPLET.json')['Data']}
        self.buff = {r['m_BuffStrID']: r for r in json.loads((t / 'BUFF_TEMPLET.json').read_text(encoding='utf-8'))['Data']}
        self.se = FA.se_rows(t, self.skills)


def skill_pairs(u, raw, gu, skills):
    """[(데이터북 스킬 번호 si, 게임 SkillStrID)] — unit_rules 와 같은 칸 대응."""
    out = []
    db = {raw['s'][si]['sl']: si for si in u['sk'] if raw['s'][si]['sl'] in FA.SLOT.values()}
    for sid in gu.get('m_listSkill') or []:
        m = re.search(r'_(ATTACK|SPECIAL|HYPER)\d*$', sid)
        sk = skills.get(sid) or {}
        if not m or sk.get('m_NKM_SKILL_TYPE') == 'NST_REACT':
            continue
        slot = FA.SLOT[m.group(1)]
        if slot not in db or re.search(r'_(ATTACK|SPECIAL|HYPER)\d+$', sid):
            continue
        out.append((db[slot], sid))
    g_pass = [sid for sid in gu.get('m_listSkill') or [] if re.search(r'_PASSIVE\d*$', sid)]
    d_pass = [si for si in u['sk'] if raw['s'][si]['sl'] == '패시브']
    if len(g_pass) == len(d_pass):
        out += list(zip(d_pass, g_pass))
    return out


def links(tb):
    """foe 키 -> (데이터북 유닛, 게임 유닛 ID 정렬 목록). 키는 엔진 UnitDef.key 와 같음."""
    raw = F.load_foe(str(ROOT))
    out = {}
    for (ui, xi), gids in FA.unit_links(tb.static, raw, tb.units, guild=True).items():
        out['foe:%d' % ui + (':%d' % xi if xi is not None else '')] = (raw['u'][ui], sorted(gids))
    return raw, out
