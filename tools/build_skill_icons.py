# -*- coding: utf-8 -*-
"""구원자 스킬 칸(기본기·특수기·궁극기·고유 패시브)별 게임 아이콘 -> data/skill_icons.json + assets/skill_icons/*.png.

공개 저장소에는 가공 맵만 둔다: units[구원자 uid] = [기본기, 특수기, 궁극기, 패시브] 아이콘 파일명(확장자 없음, 없으면 null).
스킬 표(SKILL_TEMPLET_1/2)의 m_SkillIcon 에서 얻되 원본 행·이름 문자열은 맵에 넣지 않는다.
아이콘 PNG 는 --icons 폴더(추출한 128px 축소본)에서 필요한 것만 assets/skill_icons/ 로 복사한다.

사용: python -X utf8 -I tools/build_skill_icons.py --static <비공개 저장소> --icons <축소본 폴더>
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.runtime import static_path   # noqa: E402
from battlesim.fileio import atomic_text   # noqa: E402


def build(static, icons):
    tables = Path(static) / 'tables'
    skills = {}
    for n in (1, 2):
        for r in json.loads((tables / ('SKILL_TEMPLET_%d.json' % n)).read_text(encoding='utf-8'))['Data']:
            skills[r['m_SkillStrID']] = (r.get('m_SkillIcon') or '').rsplit('.', 1)[0]
    pub = json.loads((ROOT / 'data' / 'savior_skills.json').read_text(encoding='utf-8'))
    base = {}
    for t in sorted(tables.glob('UNIT_TEMPLET_BASE*.json')):
        for u in json.loads(t.read_text(encoding='utf-8'))['Data']:
            base.setdefault(str(u['m_UnitID']), u.get('m_listSkill') or [])
    units, miss, copied = {}, [], set()
    for uid in pub:
        row = []
        for i, sid in enumerate((base.get(uid) or [])[:4]):
            name = skills.get(sid, '')
            if name and (icons / (name + '.png')).is_file():
                row.append(name)
                copied.add(name)
            else:
                row.append(None)
                miss.append((uid, i))
        row += [None] * (4 - len(row))
        units[uid] = row
    return units, miss, copied


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--static', help='비공개 저장소(기본: STARSAVIOR_STATIC)')
    ap.add_argument('--icons', type=Path, required=True, help='스킬 아이콘 PNG 폴더(128px 축소본)')
    ap.add_argument('--out', type=Path, default=ROOT / 'data/skill_icons.json')
    ap.add_argument('--assets', type=Path, default=ROOT / 'assets/skill_icons')
    args = ap.parse_args()
    units, miss, copied = build(static_path(args.static), args.icons)
    args.assets.mkdir(parents=True, exist_ok=True)
    for old in args.assets.glob('*.png'):
        if old.stem not in copied:
            old.unlink()
    for name in sorted(copied):
        shutil.copyfile(args.icons / (name + '.png'), args.assets / (name + '.png'))
    out = {'_note': 'units[구원자 uid] = [기본기, 특수기, 궁극기, 고유 패시브] 아이콘 파일명(assets/skill_icons/<이름>.png). 재생성: tools/build_skill_icons.py',
           'units': units}
    atomic_text(args.out, json.dumps(out, ensure_ascii=False, separators=(',', ':')) + '\n')
    total = sum(len(v) for v in units.values())
    print('연결 %d / %d 칸, 못 찾음 %d, 고유 아이콘 %d개' % (total - len(miss), total, len(miss), len(copied)))
    for m in miss:
        print('  없음', m)


if __name__ == '__main__':
    main()
