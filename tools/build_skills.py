"""Build the skill viewer payload using only the checked-in public databook.

python -X utf8 tools/build_skills.py [--check]
Keys are game unit IDs (roster uid). Effect internals and duplicate text are omitted.
"""
import json
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from battlesim.fileio import atomic_text
SOURCE = ROOT / "rawdata/databook_main.json"
OUTPUT = ROOT / "data/savior_skills.json"


def compact(units):
    result = {}
    for unit in units:
        # Bloomed SR entries reuse the same ID. The roster represents the base form;
        # never let the later SSR variant silently overwrite its descriptions.
        if unit.get("v", "기본") != "기본":
            continue
        skills = []
        for skill in unit["sk"]:
            row = {k: skill[k] for k in ("sl", "n", "ty", "tg", "cd", "cdm", "mx", "d1") if k in skill}
            if skill.get("dx") and skill["dx"] != skill.get("d1"):
                row["dx"] = skill["dx"]
            row["lv"] = [level[:2] for level in skill.get("lv", [])]
            row["gl"] = [[g.get(k, "") for k in ("n", "k", "d")] for g in skill.get("gl", [])]
            skills.append(row)
        result[str(unit["id"])] = skills
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source', type=Path, default=SOURCE)
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    source = json.loads(args.source.read_text(encoding="utf-8"))
    rows = compact(source["units"])
    payload = json.dumps(rows, ensure_ascii=False, separators=(",", ":")) + "\n"
    if args.check:
        if OUTPUT.read_text(encoding="utf-8") != payload:
            raise SystemExit("savior_skills.json is stale; run tools/build_skills.py")
    else:
        atomic_text(OUTPUT, payload)
    print(f"{OUTPUT.name}: {len(rows)} units, {len(payload.encode('utf-8')):,} bytes")


if __name__ == "__main__":
    main()
