"""일반 스테이지 벨그라스의 SE 복원. 코스모 전용 모델과 다른 적은 제외."""
import copy
import re

from .parser import split_head

ERO = '침식된 의지(해제불가)'
ROT = '썩은 의지(해제불가)'
CHECK = '썩은 의지 발생 방지 버프'


def is_stage(d):
    return (getattr(d, 'is_foe', False) and d.key.startswith('foe:')
            and d.name == '벨그라스')


def normalize(d, lines):
    if not is_stage(d):
        return lines
    out = []
    for original in lines:
        ln = copy.copy(original)
        ln.eff = dict(original.eff)
        e, p = ln.eff, dict(ln.params)
        rest = split_head(ln.raw)[2]
        fixed = re.fullmatch(r'자신에게 고정 피해 (\d+)', rest)
        # 26752678 SE930082301..350 / 조건51074..51123:
        # SKILL_START, SELF, 썩은 의지 정확히 1..50개, AddTrueDamageValue=5000*n.
        if (fixed and ln.slot == '궁극기' and ln.kind == 'own_pre'
                and p.get('사용 스킬') == '궁극기' and p.get('자신이 보유') == ROT
                and p.get('중첩수', '').isdigit()
                and 1 <= int(p['중첩수']) <= 50 and int(fixed[1]) == 5000 * int(p['중첩수'])):
            ln.eff = dict(kind='belgras_fixed', value=int(fixed[1]))
        # SE930082510 / 조건58601: 적의 공격·비공격 시전 시작에 판정.
        elif (ln.trig == '적 행동 시' and p == {'자신이 보유': ERO}
              and e.get('name') == CHECK and e['kind'] == 'buff'):
            ln.kind = 'foe_pre_any'
            e.update(cast_marker=True, belgras_marker=True)
        # 데이터북이 SE503/504/505를 ×3 한 줄로 합침. SE506의 2회와 합쳐 17회.
        elif (e['kind'] == 'buff' and e.get('consume') and e.get('name') == ERO
              and e.get('times') == 5 and rest.endswith('5중첩 감소 ×3')):
            e.update(times=15, belgras_repeat=True)
        out.append(ln)
    return out


def expire_marker(b, ctx):
    # NKM:15825-15828 -> 16017-16027 -> 4047-4053:
    # SKILL_END 뒤 수명 0 표지를 지움. 이어지는 협공은 새로운 시전임.
    for x, name in ctx.markers:
        if name == CHECK:
            x.eff.pop(name, None)
            b.dirty(x)
