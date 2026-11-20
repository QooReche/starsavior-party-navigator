"""실제 Pyodide 축소판을 이전→현재→현재→이전 순서로 측정함(동시 실행 없음)."""
import argparse
import json
from pathlib import Path
import statistics
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('output',type=Path)
    a=ap.parse_args()
    folder=ROOT/'_tmp/guild-executor-measure'
    folder.mkdir(parents=True,exist_ok=True)
    samples=[]
    for i,legacy in enumerate([True,False,False,True]):
        path=folder/f'{i}.json'
        cmd=[sys.executable,'-X','utf8','tests/e2e/test_search_executor.py','--all-phases','--bench',str(path)]
        if legacy:cmd.append('--legacy')
        subprocess.run(cmd,cwd=ROOT,check=True,timeout=300)
        sample=json.loads(path.read_text(encoding='utf8'))
        sample['implementation']='before' if legacy else 'after'
        samples.append(sample)
    for sample in samples:
        for key in ['engine','settings','keys','workers','allPhases','breakRuns','out']:
            assert sample[key]==samples[0][key],f'comparison condition/result changed: {key}'
        assert len(sample['timings'])==4,'must exercise all four guild stages'
    groups={k:[s for s in samples if s['implementation']==k] for k in ['before','after']}
    means={k:statistics.mean(s['totalMs'] for s in rows) for k,rows in groups.items()}
    phases={k:[{'phase':rows[0]['timings'][i]['phase'],**{field:statistics.mean(s['timings'][i][field] for s in rows) for field in ['elapsedMs','busyMs','idleMs']}} for i in range(4)] for k,rows in groups.items()}
    report={'order':['before','after','after','before'],'meanMs':means,'ratio':means['after']/means['before'],'limit':1.3,
            'idleDefinition':'2 * phase elapsed - sum(postMessage to done); engine load is busy, not CPU utilization',
            'phaseMeans':phases,'samples':samples}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('Guild before/after mean ms:',means,'ratio:',round(report['ratio'],4),flush=True)
    assert report['ratio']<=1.3,'reduced guild wall time exceeds 1.3x'

if __name__=='__main__':main()
