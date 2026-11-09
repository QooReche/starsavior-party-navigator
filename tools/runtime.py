"""도구 실행 규약: 계산은 IDLE, 비공개 입력은 인자 또는 환경변수로 지정."""
import os
from pathlib import Path


def low_priority():
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        k = ctypes.WinDLL('kernel32', use_last_error=True)
        k.GetCurrentProcess.restype = wintypes.HANDLE
        k.SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        k.GetPriorityClass.argtypes = [wintypes.HANDLE]
        if not k.SetPriorityClass(k.GetCurrentProcess(), 0x40) or k.GetPriorityClass(k.GetCurrentProcess()) != 0x40:
            raise RuntimeError('IDLE 우선순위를 설정하지 못했음')
    elif os.nice(0) < 19:
        os.nice(19 - os.nice(0))


SKIP_MARK = '[건너뜀]'


def skip_note(reason):
    """환경 때문에 못 돌린 검사를 알린다. tools/run_tests.py 가 이 표식을 모아 «건너뜀 N개» 로 보이고,
    --strict 이면 실패로 센다. 조용히 return 해서 통과로 보이게 하지 말 것."""
    print('  %s %s' % (SKIP_MARK, reason), flush=True)


def static_path_or_none(root=None):
    """시험용: 비공개 표 저장소를 찾는다. STARSAVIOR_STATIC -> <root>/../static-data 순. 없으면 None(시험은 SkipTest)."""
    root = Path(root) if root else Path(__file__).resolve().parents[1]
    for cand in (os.environ.get('STARSAVIOR_STATIC'), root.parent / 'static-data'):
        if cand and (Path(cand) / 'tables').is_dir():
            return Path(cand)
    return None


def static_path(value=None):
    value = value or os.environ.get('STARSAVIOR_STATIC')
    if not value:
        raise ValueError('비공개 입력 경로 필요: --static <경로> 또는 STARSAVIOR_STATIC 환경변수를 지정하기')
    path = Path(value)
    if not path.is_dir():
        raise ValueError('비공개 입력 경로가 없음: --static 또는 STARSAVIOR_STATIC 확인하기')
    return path
