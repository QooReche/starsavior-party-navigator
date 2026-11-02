"""e2e 서버의 포트 소유·동시 실행·종료 회귀 시험(Playwright 없이 실행)."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from pathlib import Path
import runpy
import socket
import urllib.request
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
page = runpy.run_path(str(ROOT / 'tests/e2e/test_page.py'))
serve, Server, Handler = (page[k] for k in ('test_server', 'TestHTTPServer', 'TestHandler'))


def fetch(base):
    with urllib.request.urlopen(base + '/README.md', timeout=10) as response:
        return response.read()


def main():
    expected = (ROOT / 'README.md').read_bytes()
    with ExitStack() as outer:
        second = outer.enter_context(serve())
        with serve() as first:
            port = urlsplit(first).port
            assert first != second and port != 8899
            # A second process must not steal an already bound Windows listener.
            try:
                duplicate = Server(('127.0.0.1', port), Handler)
            except OSError:
                pass
            else:
                duplicate.server_close()
                raise AssertionError('시험 서버 포트 중복 바인드')
            with ThreadPoolExecutor(max_workers=16) as pool:
                assert all(body == expected for body in pool.map(fetch, [first, second] * 16))
        with socket.socket() as client:
            client.settimeout(2)
            assert client.connect_ex(('127.0.0.1', port)) != 0, '종료 뒤 서버가 남았음'
        assert fetch(second) == expected, '한 서버 종료가 다른 서버에 영향을 줌'
    print('PASS 서버 중복 바인드 거부·동시 32요청·소유 포트 종료·다른 서버 유지')


if __name__ == '__main__':
    main()
