"""공개 데이터북에서 내 정보 화면의 이름·효과 설명을 생성함."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from battlesim.fileio import atomic_text, read_json


def build(public):
    return {"potentials": {str(p["id"]): {"name": p["n"], "levels": {str(v[0]): v[4] for v in p.get("lv", [])}} for p in public["dict"]["pot"]},
            "slots": [p[0] for p in public["equip"]["adv"]["parts"]],
            "sets": {str(s["id"]): s["n"] for s in public["equip"]["sets"]}}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source', type=Path, default=ROOT / 'rawdata/databook_main.json')
    ap.add_argument('--out', type=Path, default=ROOT / 'data/myinfo_view.json')
    args = ap.parse_args()
    atomic_text(args.out, json.dumps(build(read_json(args.source)), ensure_ascii=False, separators=(',', ':')) + '\n')


if __name__ == '__main__':
    main()
