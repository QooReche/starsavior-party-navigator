# -*- coding: utf-8 -*-
r"""실제 sim_worker.js 부팅 측정. 생성물 재생성 없이 기존 manifest의 파일을 읽음.

E:\AI_mk2\venv-pw\Scripts\python.exe -X utf8 -I tools/bench_cosmo_boot.py --output local/cosmo-boot.json
새 브라우저 컨텍스트 / 같은 컨텍스트의 새 워커 / 같은 워커 재사용을 3회 비교함.
"""
import argparse
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests' / 'e2e'))
from test_page import test_server
from playwright.sync_api import sync_playwright

MEASURE = """async () => {
 const boot = async worker => {
  const start = performance.now(), stages = [];
  return await new Promise((resolve, reject) => {
   const timeout = setTimeout(() => reject(new Error('worker boot timeout')), 120000);
   worker.onerror = event => {clearTimeout(timeout); reject(new Error(event.message));};
   worker.onmessage = ({data}) => {
    if (data.type === 'stage') stages.push({msg:data.msg, ms:performance.now()-start});
    if (data.type === 'error') {clearTimeout(timeout); reject(new Error(data.msg));}
    if (data.type === 'done') {clearTimeout(timeout); resolve({ms:performance.now()-start, stages});}
   };
   worker.postMessage({type:'run', id:'boot', base:location.origin+'/', teams:[]});
  });
 };
 const first = new Worker('/sim_worker.js');
 try {
  const cold = await boot(first);
  first.terminate();
  const next = new Worker('/sim_worker.js');
  try {return {cold, http_warm:await boot(next), reused:await boot(next)};}
  finally {next.terminate();}
 } finally {first.terminate();}
}"""


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', required=True)
    args = ap.parse_args()
    rows = []
    with test_server() as base, sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            for _ in range(3):
                context = browser.new_context()
                try:
                    page = context.new_page()
                    page.goto(base + '/sim_worker.js')  # 화면 앱 초기화 비용은 제외함
                    rows.append(page.evaluate(MEASURE))
                finally:
                    context.close()
            report = {'browser': browser.version, 'samples': rows,
                      'mean_ms': {key: statistics.fmean(r[key]['ms'] for r in rows)
                                  for key in ('cold', 'http_warm', 'reused')}}
        finally:
            browser.close()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
