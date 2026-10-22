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


def static_path(value=None):
    value = value or os.environ.get('STARSAVIOR_STATIC')
    if not value:
        raise ValueError('비공개 입력 경로 필요: --static <경로> 또는 STARSAVIOR_STATIC 환경변수를 지정하기')
    path = Path(value)
    if not path.is_dir():
        raise ValueError('비공개 입력 경로가 없음: --static 또는 STARSAVIOR_STATIC 확인하기')
    return path
