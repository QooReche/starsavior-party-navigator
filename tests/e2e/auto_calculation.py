"""Automatic recommendation: real UI, hostile late workers, and CDP CPU slowdown.

Registered by test_page.py; uses its one browser and synthetic public fixtures.
"""
import json
import os


FAKE_WORKER = """() => {
  window.autoJobs=[];
  window.Worker=class {
    postMessage(req){this.req=req;autoJobs.push({worker:this,req,callback:this.onmessage});}
    terminate(){this.stopped=true;}
  };
  window.finishAutoJob=(job,clear=1)=>{
    const {req,callback}=job;
    callback({data:{type:'stage',id:req.id,msg:'준비 끝'}});
    for(const team of req.teams)callback({data:{type:'team',id:req.id,key:team.key,
      result:{ver:GROW.versions?.engine,n:req.n_runs,clear,prog:clear,progs:Array(req.n_runs).fill(clear),
        via:{coop:0},ci:[clear,clear],ttk:2,ta:2}}});
    callback({data:{type:'done',id:req.id}});
    job.finished=true;
  };
}"""


def option(page, enabled):
    page.locator('#optbox').evaluate('(e)=>e.open=true')
    page.locator('#reco-auto').set_checked(enabled)


def fake_setup(page):
    page.add_init_script('(' + FAKE_WORKER + ')()')


def drain(page):
    for _ in range(20):
        page.evaluate("autoJobs.filter(j=>!j.finished&&!j.worker.stopped).forEach(j=>finishAutoJob(j))")
        page.wait_for_timeout(80)
        if page.evaluate("SIMQ.busy===null&&!simWaiting(cur[$('stage').value])&&!!document.querySelector('.party[data-team]')"):
            return
    raise AssertionError('latest calculation did not finish')


def test_auto_calculation_controls(browser, ctx):
    page = open_page(browser, ctx, query='?auto=0', info=SYNTH, simauto='0', wait=False,
                     setup=fake_setup)
    wait_myinfo(page)
    # The checked default is tested independently of the explicit opt-in cases.
    assert page.locator('#reco-auto').is_checked() == page.evaluate('RECO_AUTO_DEFAULT')
    option(page, True)
    page.wait_for_selector('.party[data-team]')
    assert page.evaluate('autoJobs.length') == 0, 'recommendation must respect simauto=0'
    assert page.evaluate("localStorage.getItem('pn.simauto')") == '0'
    page.select_option('#stage', index=2)
    page.wait_for_selector('.party[data-team]')
    assert page.evaluate('autoJobs.length') == 0
    option(page, False)
    page.wait_for_selector('[data-go]')
    assert page.evaluate("LS.get('reco.auto')") is False
    page.reload()
    wait_myinfo(page)
    page.wait_for_selector('[data-go]')
    assert not page.locator('#reco-auto').is_checked()
    page.click('[data-go]')
    page.wait_for_function('autoJobs.length>0')
    page.click('[data-simcancel]')
    assert page.evaluate('autoJobs.every(j=>j.worker.stopped)&&SIMQ.busy===null')
    page.wait_for_timeout(450)
    assert page.evaluate('SIMQ.busy===null'), 'stop must not immediately restart'
    page.locator('[data-sim]').first.click()
    page.wait_for_function('autoJobs.some(j=>!j.worker.stopped)')
    drain(page)
    old_jobs = page.evaluate('autoJobs.length')
    page.click('[data-recoretry]')
    page.wait_for_function(f'autoJobs.length>{old_jobs}')
    drain(page)
    # ?auto=1 remains an independent URL override; it must not save the device switch.
    page.evaluate('simAuto(false)')  # The explicit retry above enables simulation, as before.
    page.goto(ctx.base + '/index.html?auto=1&dev=1')
    wait_myinfo(page)
    page.wait_for_selector('.party[data-team]')
    assert not page.locator('#reco-auto').is_checked()
    assert page.evaluate("LS.get('reco.auto')===false&&localStorage.getItem('pn.simauto')==='0'")
    page.select_option('#stage', index=3)
    page.wait_for_selector('.party[data-team]')
    assert page.evaluate('autoJobs.length') == 0
    # Only the new preference excludes both seasonal searches; legacy auto URLs stay intact.
    page.goto(ctx.base + '/index.html?auto=0&dev=1')
    wait_myinfo(page)
    option(page, True)
    for key in ['guild', 'cosmo']:
        page.evaluate("k=>{$('q').value='';$('content').value=contents.findIndex(c=>c.key===k);$('content').dispatchEvent(new Event('change'));}", key)
        page.wait_for_timeout(500)
        assert page.evaluate('SIMQ.busy===null&&GSR.phase!=="run"&&CSR.phase!=="run"')
        assert page.locator('[data-go]').count() or page.locator('[data-cs="start"]').count()
    # No stage, no automatic work; closed clash season is blocked even with opt-in.
    page.evaluate("$('content').value=contents.findIndex(c=>c.key==='op');refreshTabs();$('q').value='no-such-stage';refreshStages()")
    page.wait_for_timeout(450)
    assert page.evaluate('SIMQ.busy===null&&!REQ')
    page.evaluate("history.replaceState(null,'','?auto=0');const c=contents.find(c=>c.key==='clash');c.seasonPeriod={start:'2000-01-01T00:00:00Z',end:'2000-01-02T00:00:00Z'};$('q').value='';$('content').value=contents.indexOf(c);refreshTabs()")
    page.wait_for_timeout(450)
    assert page.evaluate("seasonBlocked('clash')&&SIMQ.busy===null&&!REQ")
    assert not ctx.errors, ctx.errors
    page.close()
    return True, 'preference persistence, simauto/URL independence, stop/retry, seasonal buttons and closed-season gate'


def race_case(browser, ctx, mutation=None, main=False):
    def setup(page):
        fake_setup(page)
        page.add_init_script("localStorage.setItem('pn.reco.auto','true')")
        if mutation:
            with open(os.path.join(ROOT, 'index.html'), encoding='utf-8') as f:
                html = f.read()
            if mutation == 'cancel':
                old, new = 'simInvalidate(); // cancel old selection immediately', '// cancellation removed'
            else:
                old, new = 'if(SIMQ.requestId!==id||(m.id!=null&&m.id!==id))return;', '/* stale request guard removed */'
            assert old in html, mutation
            page.route('**/index.html?*', lambda r: r.fulfill(body=html.replace(old, new), content_type='text/html'))
    page = open_page(browser, ctx, query='?auto=0', info=SYNTH, simauto=None, wait=False, setup=setup)
    wait_myinfo(page)
    page.wait_for_function('autoJobs.length>0')
    if main:
        for _ in range(10):
            if page.evaluate('autoJobs.some(j=>j.req.n_runs===100)'):
                break
            page.evaluate('autoJobs.filter(j=>!j.finished&&!j.worker.stopped).forEach(j=>finishAutoJob(j))')
            page.wait_for_timeout(80)
        assert page.evaluate('autoJobs.some(j=>j.req.n_runs===100)'), 'must exercise final simulation'
    page.evaluate("window.oldJob=autoJobs.filter(j=>!j.finished).at(-1);window.oldCount=autoJobs.length")
    page.select_option('#stage', index=1)
    if mutation == 'cancel':
        assert page.evaluate('oldJob.worker.stopped===true'), 'old worker was not terminated'
    else:
        assert page.evaluate('oldJob.worker.stopped===true')
        # A callback already queued before terminate() can still arrive during debounce.
        page.evaluate("window.beforeLate=JSON.stringify([SIMQ.res,SIMQ.scr,SIMQ.busy,SIMQ.msg]);oldJob.callback({data:{type:'team',id:oldJob.req.id,key:oldJob.req.teams[0].key,result:{clear:.13,prog:.13,progs:[.13],via:{},n:8,ttk:99}}});oldJob.callback({data:{type:'stage',id:oldJob.req.id,msg:'OLD'}})")
        assert page.evaluate('beforeLate===JSON.stringify([SIMQ.res,SIMQ.scr,SIMQ.busy,SIMQ.msg])'), 'late result changed current state'
    # Five changes inside the debounce window: only the final selection starts work.
    page.evaluate("async()=>{for(let i=2;i<=6;i++){$('stage').value=String(i);$('stage').dispatchEvent(new Event('change'));await new Promise(r=>setTimeout(r,40));}}")
    page.wait_for_function('autoJobs.length>oldCount')
    assert page.evaluate("autoJobs.slice(oldCount).every(j=>j.req.stage.endsWith('/'+cur[$('stage').value].name))")
    drain(page)
    snapshot = page.inner_text('#out')
    page.evaluate('finishAutoJob(oldJob,.13)')
    page.wait_for_timeout(100)
    assert page.inner_text('#out') == snapshot, 'old completion overwrote the latest result'
    assert page.evaluate("LASTQ[1].rows.every(t=>SIMQ.res[simSig(cur[$('stage').value],t)]?.clear===1)")
    page.close()


def test_auto_calculation_races(browser, ctx):
    race_case(browser, ctx)
    race_case(browser, ctx, main=True)
    caught = []
    for mutation, main in [('cancel', False), ('request', False), ('request', True)]:
        try:
            race_case(browser, ctx, mutation, main)
        except AssertionError as e:
            expected = 'not terminated' if mutation == 'cancel' else 'late result changed'
            assert expected in str(e), str(e)
            caught.append((mutation, main))
        else:
            raise AssertionError('mutation escaped: ' + mutation)
        finally:
            for context in browser.contexts:
                context.close()
    assert not ctx.errors, ctx.errors
    return True, 'five-change debounce; screening/final stale callbacks; mutations detected: ' + str(caught)


def test_auto_calculation_shared_growth(browser, ctx):
    def setup(page):
        fake_setup(page)
        page.add_init_script("localStorage.setItem('pn.reco.auto','false')")
    page = open_page(browser, ctx, query='?auto=0', info=SYNTH, simauto='0', wait=False, setup=setup)
    wait_myinfo(page)
    # The shared account arrives asynchronously, after normal page startup.
    url = page.evaluate("async()=>{const u=new URL(await shareUrlMi());u.searchParams.set('ag','1');return u.href}")
    saved = page.evaluate("JSON.stringify([LS.get('myinfo'),LS.get('growth.options'),LS.get('growth.history')])")
    page.goto(url)
    page.wait_for_function('MI.shared&&!!MI.growth&&!MI.pending')
    page.wait_for_function('autoJobs.length>0')
    assert page.locator('#assume-growth').is_checked()
    assert not page.locator('#reco-auto').is_checked()

    def finish_growth():
        for _ in range(100):
            page.evaluate("autoJobs.filter(j=>!j.finished&&!j.worker.stopped).forEach(j=>finishAutoJob(j,SIMQ.busy==='growth'?.95:.6))")
            page.wait_for_timeout(80)
            if page.evaluate("GROW.phase==='done'"):
                break
        assert page.evaluate("GROW.phase==='done'&&GROW.result.runs>0&&GROW.result.best.prog>0"), page.evaluate('GROW.errors')
        assert page.locator('#result-tab-growth').count() == 1
        assert page.evaluate("GROW.result.best.clear>GROW.result.baseline.clear")

    finish_growth()
    assert page.evaluate("JSON.stringify([LS.get('myinfo'),LS.get('growth.options'),LS.get('growth.history')])") == saved
    # Local automatic opt-in also runs the growth pass on the next selection.
    page.evaluate('simAuto(true)')
    option(page, True)
    page.select_option('#stage', index=2)
    page.wait_for_function('autoJobs.some(j=>!j.finished&&!j.worker.stopped)')
    finish_growth()
    assert page.evaluate("GROW.sig===growthSig(contents[$('content').value],cur[$('stage').value])")
    assert page.evaluate("JSON.stringify([LS.get('myinfo'),LS.get('growth.options'),LS.get('growth.history')])") == saved
    assert not ctx.errors, ctx.errors
    page.close()
    return True, 'asynchronous shared link auto-start, growth option/pass/result, subsequent selection, local account/options/history preserved'


def test_auto_calculation_slow(browser, ctx):
    """Real Pyodide, full public fixture, one worker, 6x CDP CPU slowdown."""
    def setup(page):
        page.add_init_script("""if(!Object.getOwnPropertyDescriptor(navigator,'hardwareConcurrency'))Object.defineProperty(navigator,'hardwareConcurrency',{get:()=>2});
          if(!Object.getOwnPropertyDescriptor(navigator,'deviceMemory'))Object.defineProperty(navigator,'deviceMemory',{get:()=>1});
          localStorage.setItem('pn.reco.auto','false');
          window.slow={jobs:[],canceled:[],done:[],gaps:[]};
          const Native=Worker;
          window.Worker=class extends Native {
            constructor(...args){super(...args);this.addEventListener('message',e=>{
              if(e.data.type==='done'){this.finished=true;slow.done.push({stage:this.req?.stage,n:this.req?.n_runs});}
            });}
            postMessage(req){this.req=req;this.finished=false;slow.jobs.push({stage:req.stage,n:req.n_runs});super.postMessage(req);}
            terminate(){if(this.req&&!this.finished)slow.canceled.push(this.req.stage);super.terminate();}
          };""")
    page = open_page(browser, ctx, query='?auto=0', info=FULL, simauto=None, wait=False, setup=setup)
    wait_myinfo(page)
    page.wait_for_function('!!QK.d')
    cdp = page.context.new_cdp_session(page)
    cdp.send('Emulation.setCPUThrottlingRate', {'rate': 6})
    page.evaluate("window.slowStart=cur.findIndex(s=>s.name==='SECTOR 15-1');if(slowStart<0)throw Error('measurement stage missing');$('stage').value=String(slowStart);$('stage').dispatchEvent(new Event('change'))")
    option(page, True)
    page.wait_for_function('slow.jobs.length>0', timeout=60000)
    # Enter a new selection while the old real worker is still preparing/running.
    page.evaluate("""async()=>{
      slow.jobs=[];slow.done=[];slow.canceled=[];slow.gaps=[];
      let last=performance.now();window.slowTick=setInterval(()=>{const now=performance.now();slow.gaps.push(now-last);last=now;},50);
      for(let i=1;i<=5;i++){$('stage').value=String(slowStart+i);$('stage').dispatchEvent(new Event('change'));
        if(i<5)await new Promise(r=>setTimeout(r,50));}
      slow.last=performance.now();slow.stage=contents[$('content').value].key+'/'+cur[$('stage').value].tab+'/'+cur[$('stage').value].name;
    }""")
    wait_sim_done(page, timeout=600000)
    result = page.evaluate("""()=>{clearInterval(slowTick);return {cpu:6,workers:1,changes:5,
      elapsed_ms:Math.round(performance.now()-slow.last),max_gap_ms:Math.round(Math.max(...slow.gaps)),
      cancellations:slow.canceled.length,completed:new Set(slow.done.filter(x=>x.n===100).map(x=>x.stage)).size,
      main_batches:slow.done.filter(x=>x.n===100).length,
      starts:slow.jobs.filter(x=>x.n===8).length,requested_stages:[...new Set(slow.jobs.map(x=>x.stage))],
      stages:[...new Set(slow.done.map(x=>x.stage))],stage:slow.stage,
      progress:LASTQ[1].rows.map(t=>SIMQ.res[simSig(cur[$('stage').value],t)]?.prog),
      defaultOn:RECO_AUTO_DEFAULT};}""")
    cdp.send('Emulation.setCPUThrottlingRate', {'rate': 1})
    assert result['cancellations'] >= 1, result
    assert result['starts'] == 1 and result['requested_stages'] == [result['stage']], result
    assert result['completed'] == 1 and result['stages'] == [result['stage']], result
    assert any((p or 0) > 0 for p in result['progress']), result
    if result['elapsed_ms'] > 15000 or result['max_gap_ms'] > 1000:
        assert result['defaultOn'] is False, 'slow-device gate requires default OFF: ' + json.dumps(result)
    with open(os.path.join(ctx.shots, 'auto-calculation-slow.json'), 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    page.screenshot(path=os.path.join(ctx.shots, 'auto-calculation-slow.png'))
    assert not ctx.errors, ctx.errors
    page.close()
    return True, json.dumps(result, ensure_ascii=False)


def register(api):
    for name in ['ROOT', 'SYNTH', 'FULL', 'open_page', 'wait_myinfo', 'wait_sim_done']:
        globals()[name] = getattr(api, name)
    return [test_auto_calculation_controls, test_auto_calculation_races,
            test_auto_calculation_shared_growth, test_auto_calculation_slow]
