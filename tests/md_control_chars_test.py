"""문서 md 에 제어문자가 없는지 확인.

2026-11-08 정리 때 HANDOFF.md·docs/ingame_samples.md 의 경로가 `AI\\temp` → `AI<탭>emp`,
`work\\video` → `work<VT>ideo`, `C:\\build\\new-extract` → 줄바꿈으로 깨져 있었음
(파이썬 문자열에 넣은 백슬래시가 이스케이프로 풀린 것). 탭(\\x09)·개행(\\x0a)·CR(\\x0d)은 허용하고
그 밖의 C0 제어문자(\\x00-\\x08, \\x0b, \\x0c, \\x0e-\\x1f)를 막음. BOM 도 막음(다른 md 와 맞춤)."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
BAD = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')


def md_files():
    files = [ROOT / 'HANDOFF.md', ROOT / 'README.md', ROOT / 'AGENTS.md']
    files += sorted((ROOT / 'docs').glob('*.md'))
    return [f for f in files if f.exists()]


def find_bad(text):
    out = []
    for i, line in enumerate(text.split('\n'), 1):
        for m in BAD.finditer(line):
            out.append((i, repr(line[max(0, m.start() - 20):m.start() + 20])))
    return out


class MdControlCharsTest(unittest.TestCase):
    def test_files_exist(self):
        names = {f.name for f in md_files()}
        self.assertTrue({'HANDOFF.md', 'README.md', 'AGENTS.md', 'HISTORY.md'} <= names)

    def test_no_control_chars(self):
        problems = []
        for f in md_files():
            text = f.read_bytes().decode('utf-8')
            for line, ctx in find_bad(text):
                problems.append('%s:%d: %s' % (f.relative_to(ROOT), line, ctx))
        self.assertEqual(problems, [], '\n'.join(problems[:20]))

    def test_no_bom(self):
        boms = [str(f.relative_to(ROOT)) for f in md_files() if f.read_bytes().startswith(b'\xef\xbb\xbf')]
        self.assertEqual(boms, [])

    def test_detector_catches_broken_paths(self):
        # 실제로 깨졌던 모양을 잡는지(검사 자체가 비어 있지 않은지)
        self.assertTrue(find_bad('`AI\\temp\\partynavigator\\work\x0bideo_1108\\`'))
        self.assertTrue(find_bad('C:\x08uild'))
        self.assertTrue(find_bad('leader_1108\x07fter'))
        self.assertFalse(find_bad('표\t탭은 허용\r\n'))


if __name__ == '__main__':
    unittest.main()
