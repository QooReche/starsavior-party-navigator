"""B-stage UI and real Pyodide parity. Only synthetic accounts are used."""
import argparse
import json
from pathlib import Path
from test_direct_party import ready, enter, pick_four, geometry
from test_page import test_server, wait_sim_done
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'_tmp/direct-b'
OUT.mkdir(parents=True,exist_ok=True)

FAKE="""(() => {Object.defineProperty(navigator,'hardwareConcurrency',{get:()=>3});
 window.directPosts=[];window.directWorkers=[];
 window.Worker=class {constructor(){directWorkers.push(this)}
 postMessage(m){this.req=m;directPosts.push(m);if(window.holdDirect)return;
 const emit=x=>{if(!this.dead)this.onmessage({data:{id:m.id,requestId:m.requestId,job:m.job,jobId:m.jobId,owner:m.owner,revision:m.revision,...x}})};
 emit({type:'stage',msg:'준비 끝'});
 setTimeout(()=>emit({type:'stage',msg:'계산 중',completed:62,total:100}),50);
 setTimeout(async()=>{const ver=(await fetch('sim/manifest.json').then(r=>r.json())).ver;
  if(window.failGrown&&m.teams[0].key==='grown'){emit({type:'error',msg:'controlled failure'});return;}
  // A batched request (SearchExecutor chunk>1) carries several teams; the real worker answers each team, then one done.
  for(const t of m.teams)emit({type:'team',key:t.key,result:{ver,n:m.n_runs,clear:window.clearDirect??.82,t60:.55,ttk:42,ta:60,ci:[.7,.9],power:100000,progs:[.8],via:{},u:{},bs:{name:t.options.break_skill?.name||null}}});emit({type:'done'});
 },window.directDelay||500);
 }terminate(){this.dead=true}};})();"""

def fake(page):page.add_init_script(FAKE)

def start(browser,base,width=1280,setup=fake,info=True):
    kwargs={'setup':setup,'touch':width==360}
    if not info:kwargs['info']=None
    p=ready(browser,base,width,**kwargs);enter(p);pick_four(p,width==360)
    p.evaluate("$('direct-comparison').open=true")
    return p

def expand_row(p,kind):
    b=p.locator(f'[data-direct-action=compare-toggle][data-kind={kind}]')
    if b.get_attribute('aria-expanded')!='true':b.click()


def done(p):p.wait_for_function("!DIRECT.active && DIRECT.rows.now?.status==='done'",timeout=120000)

def shots_and_reuse(browser,base,width):
    p=start(browser,base,width);before=p.evaluate('JSON.stringify(MI.info)')
    p.screenshot(path=str(OUT/f'before-{width}.png'),full_page=True)
    p.evaluate('window.directDelay=1800')
    if width==360:p.locator('#direct-run').tap()
    else:p.locator('#direct-run').focus();p.keyboard.press('Enter')
    p.wait_for_function("DIRECT.rows.now?.progress===62")
    expand_row(p,'now')
    assert '62/100판' in p.locator('[data-direct-row=now]').inner_text()
    assert p.locator('#direct-run').inner_text()=='취소'
    p.screenshot(path=str(OUT/f'running-{width}.png'),full_page=True)
    done(p);assert '82%' in p.locator('#direct-result-summary').inner_text()
    assert p.locator('#direct-gwen [data-gwen-report]').count()==1
    p.screenshot(path=str(OUT/f'result-{width}.png'),full_page=True)
    count=p.evaluate('directPosts.length');sig=p.evaluate('DIRECT.rows.now.sig')
    p.locator('[data-direct-action=grown][data-slot="0"]').click()
    assert p.evaluate('DIRECT.rows.now.sig===DIRECT.expected.now.sig'),'growth invalidated current row'
    p.locator('#direct-run').click();done(p)
    assert p.evaluate('directPosts.length')<=count+1
    assert p.locator('[data-direct-row=grown]').count()==1
    expand_row(p,'grown')
    assert '보수적 비교 범위' in p.locator('[data-direct-row=grown]').inner_text()
    p.screenshot(path=str(OUT/f'growth-comparison-{width}.png'),full_page=True)
    count=p.evaluate('directPosts.length')
    p.locator('[data-direct-action=leader][data-slot]').count() # leader buttons use key
    p.evaluate("directChange({type:'leader',key:DIRECT.draft.slots[1].key})")
    assert p.locator('[data-direct-row=now]').evaluate("e=>e.classList.contains('direct-past')")
    assert '82%' in p.locator('[data-direct-row=now]').inner_text()
    p.screenshot(path=str(OUT/f'past-{width}.png'),full_page=True)
    p.locator('#direct-undo').click()
    assert not p.locator('[data-direct-row=now]').evaluate("e=>e.classList.contains('direct-past')")
    assert p.evaluate('DIRECT.rows.now.sig')==sig
    p.locator('#direct-run').click();done(p);assert p.evaluate('directPosts.length')==count
    assert p.evaluate('JSON.stringify(MI.info)')==before
    # Only the failed row retries; successful sibling stays cached.
    p.evaluate("DIRECT.cache.delete(DIRECT.rows.grown.sig);window.failGrown=true;window.directDelay=100")
    p.locator('[data-direct-action=run-row]').count()
    p.evaluate("directRun('grown')")
    p.wait_for_function("!DIRECT.active && DIRECT.rows.grown.status==='error'")
    assert p.evaluate("DIRECT.rows.now.status==='done'")
    p.screenshot(path=str(OUT/f'error-{width}.png'),full_page=True)
    p.evaluate('window.failGrown=false')
    p.locator('[data-direct-action=run-row][data-kind=grown]').click();done(p)
    p.evaluate("DIRECT.cache.delete(DIRECT.rows.grown.sig);window.failGrown=true;directRun('grown')")
    p.wait_for_function("!DIRECT.active && DIRECT.rows.grown.status==='error'")
    p.locator('[data-direct-action=grown][data-slot="0"]').click()
    assert '계산 실패' not in p.locator('[data-direct-row=grown]').inner_text(),'obsolete failure leaked into current inputs'
    assert p.evaluate("DIRECT.rows.now.status==='done'")
    geometry(p,width);assert not p.errors,p.errors;p.close()

def conditions_and_cancel(browser,base):
    p=start(browser,base);p.evaluate('window.holdDirect=true');p.locator('#direct-run').click()
    p.wait_for_function('DIRECT.rows.now?.status==="running"');old=p.evaluate('DIRECT.requestId')
    p.locator('#direct-run').click();assert p.evaluate('!DIRECT.active && directWorkers.every(w=>w.dead)')
    p.evaluate('window.holdDirect=false');p.locator('#direct-run').click();done(p)
    assert p.evaluate('DIRECT.requestId')>old
    # Edits and account changes cancel only the direct snapshot already in flight.
    p.evaluate("DIRECT.cache.clear();window.holdDirect=true;directRun()")
    p.wait_for_function('DIRECT.rows.now?.status==="running"')
    p.evaluate("directChange({type:'leader',key:DIRECT.draft.slots[1].key})")
    assert p.evaluate('!DIRECT.active && directWorkers.every(w=>w.dead)')
    p.locator('#direct-undo').click()
    p.evaluate('directRun()');p.wait_for_function('DIRECT.rows.now?.status==="running"')
    p.evaluate("MI.hash+='running-change';directPaint()")
    assert p.evaluate('!DIRECT.active && directWorkers.every(w=>w.dead)')
    p.evaluate("MI.hash=MI.hash.replace('running-change','');window.holdDirect=false;directPaint();directRun()")
    done(p)
    p.evaluate("DIRECT.draft.slots[0].grown=true;DIRECT.draft.starLink=true;directPaint()")
    p.locator('#direct-run').click();done(p)
    p.evaluate("MI.hash+='changed';directPaint()")
    assert p.locator('[data-direct-row=now].direct-past').count()==1
    p.evaluate("MI.hash=MI.hash.replace('changed','');directPaint()")
    assert p.locator('[data-direct-row=now].direct-past').count()==0
    p.evaluate("$('stage').selectedIndex=1;condChanged()")
    assert p.locator('[data-direct-row=now].direct-past').count()==1
    p.evaluate("$('stage').selectedIndex=0;condChanged()")
    assert p.locator('[data-direct-row=now].direct-past').count()==0
    p.evaluate("MI.error='성장표 오류';directPaint()")
    assert p.locator('#direct-run').is_disabled()
    assert '내 정보 계산 자료를 불러오지 못했음' in p.locator('#direct-run-state').inner_text()
    assert not p.errors,p.errors;p.close()

def combinations(browser,base):
    p=start(browser,base)
    for grown,link in [(False,False),(True,False),(False,True),(True,True)]:
        p.evaluate('''([grown,link])=>{DIRECT.draft.slots.forEach(m=>m.grown=grown);DIRECT.draft.starLink=link;directPaint()}''',[grown,link])
        p.locator('#direct-run').click();done(p)
        assert p.evaluate("!!DIRECT.expected.grown")==bool(grown),'retired starLink field changed execution'
        assert p.evaluate("DIRECT.rows.now.sig===DIRECT.expected.now.sig")
    # Same final request is calculated once, irrespective of assumption flags.
    p.close();p=start(browser,base,info=False)
    p.evaluate("DIRECT.draft.slots[0].grown=true;directPaint()")
    p.locator('#direct-run').click();done(p)
    assert p.evaluate('directPosts.length')==1
    assert p.evaluate('DIRECT.rows.now.result.clear===DIRECT.rows.grown.result.clear')
    p.evaluate("DIRECT.draft.slots[0].grown=false;directPaint()")
    assert p.locator('[data-direct-row=grown].direct-past').count()==1,'deduplicated assumption result did not become past'
    assert p.locator('[data-direct-row=now].direct-past').count()==0
    p.evaluate("DIRECT.draft.slots[0].grown=true;directPaint()")
    assert p.locator('[data-direct-row=grown].direct-past').count()==0
    assert '표준 육성 기준' in p.locator('#direct-standard').inner_text()
    p.close()

def real_execution(browser,base):
    def observe(p):p.add_init_script("window.actualProgress=[];const OriginalWorker=window.Worker;window.Worker=class extends OriginalWorker{constructor(...a){super(...a);this.addEventListener('message',e=>{if(e.data.completed)actualProgress.push(e.data.completed)})}}")
    p=start(browser,base,setup=observe,info=False)
    p.locator('#direct-run').click();done(p)
    assert p.evaluate('DIRECT.rows.now.result.prog>0')
    assert p.evaluate('actualProgress.includes(62)&&actualProgress.includes(100)')
    # Run identical payload without observation; verify all engine result fields.
    parity=p.evaluate('''async()=>{const snap=DIRECT.rows.now.snapshot,expected=DIRECT.rows.now.result;
      return await new Promise((resolve,reject)=>{const w=new Worker('sim_worker.js');w.onmessage=e=>{if(e.data.type==='team'){const a=e.data.result;w.terminate();resolve(JSON.stringify(a)===JSON.stringify(expected));}if(e.data.type==='error'){w.terminate();reject(e.data.msg)}};
      w.postMessage({type:'run',id:901,base:new URL('.',location.href).href,stage:snap.stage,n_runs:snap.runs,seed:snap.seed,options:snap.options,teams:[{key:'parity',party:snap.party,options:{break_skill:snap.brk}}]});});}''')
    assert parity,'progress observer changed an engine result'
    p.locator('#direct-detail summary').first.click()
    assert p.locator('#direct-detail .gc .crown').count()==1
    assert p.locator('#direct-detail .gc:has(.crown)').get_attribute('data-key')==p.evaluate('DIRECT.rows.now.snapshot.draft.leader')
    p.screenshot(path=str(OUT/'real-result-1280.png'),full_page=True)
    p.set_viewport_size({'width':360,'height':1000});geometry(p,360)
    p.screenshot(path=str(OUT/'real-result-360.png'),full_page=True)
    p.set_viewport_size({'width':1280,'height':1000})
    expand_row(p,'reco')
    p.locator('[data-direct-action=view-reco]').click();p.evaluate('showReco()');wait_sim_done(p,timeout=240000)
    p.locator('#mode-strip [data-pn-mode=direct]').click()
    assert p.evaluate('DIRECT.compare.result===SIMQ.res[simSig(cur[$("stage").value],LASTQ[1].rows[0])]')
    assert p.locator('#direct-recommend').count()==0
    assert '추천 탭과 같은 결과' in p.locator('[data-direct-row=reco]').inner_text()
    assert not p.errors,p.errors;p.close()

def goal_and_reaction(browser,base):
    p=start(browser,base)
    p.select_option('#content',p.evaluate("String(contents.findIndex(c=>c.key==='equip'))"))
    p.locator('#direct-run').click();done(p)
    assert p.evaluate('DIRECT.expected.now.options.star_turns')==60
    expand_row(p,'now')
    assert '60턴 내 55%' in p.locator('[data-direct-row=now]').inner_text()
    assert '−50' in p.evaluate("directDifference({n:100,clear:.9,t60:.2},{n:100,clear:.1,t60:.7},'t60')")
    p.evaluate("$('goal').value='0';condChanged()")
    expand_row(p,'now')
    assert '60턴 내 55%' in p.locator('[data-direct-row=now].direct-past').inner_text(),'past metric changed with goal'
    p.close();p=start(browser,base,info=False)
    p.evaluate('window.clearDirect=.01');p.locator('#direct-run').click();done(p)
    assert p.locator('#direct-gwen .gwen-lane-actor[data-event=low]').count()==1
    assert p.locator('#out [data-gwen-report]').count()==0,'direct completion reached recommendation report'
    assert not p.errors,p.errors;p.close()

def waiting_priority(browser,base):
    p=start(browser,base)
    p.evaluate('''()=>{window.holdDirect=true;window.recoFinished=[];
      simDispatch(scrPool(2),['a','b','c'],{id:500,live:()=>true,msg:key=>({type:'run',n_runs:100,teams:[{key,options:{}}]}),team:j=>recoFinished.push(j),done(){},error(){}});}''')
    p.locator('#direct-run').click();p.wait_for_function("DIRECT.rows.now?.status==='waiting'")
    assert '대기 중' in p.locator('#direct-run-state').inner_text()
    p.locator('#mode-strip [data-pn-mode=reco]').click()
    p.locator('#mode-strip [data-pn-mode=direct]').click()
    assert p.evaluate('directPosts.length')==2
    p.evaluate('''()=>{const w=directWorkers[0],m=w.req;w.onmessage({data:{...m,type:'team',key:m.teams[0].key,result:{clear:.8}}});w.onmessage({data:{...m,type:'done'}});}''')
    assert p.evaluate('directPosts[2].owner')=='direct'
    assert p.evaluate('directWorkers.filter(w=>!w.dead).length')==2
    p.locator('#direct-run').click()
    assert p.evaluate('directWorkers.some(w=>!w.dead&&w.req.owner==="reco")')
    p.evaluate("simPoolDrop('reco')")
    assert not p.errors,p.errors;p.close()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--real',action='store_true');ap.add_argument('--mutations',action='store_true');a=ap.parse_args()
    with test_server() as base,sync_playwright() as pw:
        browser=pw.chromium.launch()
        try:
            cases=[('captures/keyboard/reuse 1280',lambda:shots_and_reuse(browser,base,1280)),('captures/touch/reuse 360',lambda:shots_and_reuse(browser,base,360)),('conditions/cancel/errors',lambda:conditions_and_cancel(browser,base)),('four combinations/deduplication',lambda:combinations(browser,base)),('t60/past metric/direct Gwen',lambda:goal_and_reaction(browser,base)),('waiting/priority/mode/cancel',lambda:waiting_priority(browser,base))]
            if a.real:cases.append(('real engine progress parity/recommendation reuse',lambda:real_execution(browser,base)))
            for name,fn in cases:fn();print('PASS',name,flush=True)
            if a.mutations:
                def stale_check(mutate=False):
                    def setup(p):
                        fake(p)
                        if mutate:
                            src=(ROOT/'direct_run.js').read_text(encoding='utf-8')
                            old="const past=(row,kind='now')=>!!row?.result&&row.sig!==expected[kind]?.sig;"
                            assert old in src
                            p.route('**/direct_run.js',lambda route:route.fulfill(body=src.replace(old,'const past=row=>false;'),content_type='text/javascript'))
                    p=start(browser,base,setup=setup)
                    try:
                        p.locator('#direct-run').click();done(p)
                        p.evaluate("directChange({type:'leader',key:DIRECT.draft.slots[1].key})")
                        assert p.locator('[data-direct-row=now].direct-past').count()==1,'past result label missing'
                    finally:p.close()
                stale_check()
                try:stale_check(True)
                except AssertionError as e:
                    assert str(e)=='past result label missing',str(e)
                    print('MUTATION caught + restored: past result label removed',flush=True)
                else:raise AssertionError('past result mutation survived')
        finally:browser.close()
    print(f'{len(cases)} B-stage E2E groups passed',flush=True)

if __name__=='__main__':main()
