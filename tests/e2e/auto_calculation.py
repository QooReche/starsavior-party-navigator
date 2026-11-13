"""Manual recommendation and URL/shared auto-start with hostile late workers.

Registered by test_page.py; uses its one browser and synthetic public fixtures.
"""
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
  // 작업자는 팀을 하나씩 받고, done 을 보내면 다음 팀을 받는다(대기열) → 남은 일이 없을 때까지 되풀이. 단계가 바뀌는 곳(비동기)에서 멈춘다
  window.finishAutoAll=clear=>{
    for(let guard=0;guard<2000;guard++){
      const job=autoJobs.find(j=>!j.finished&&!j.worker.stopped);
      if(!job)return;
      finishAutoJob(job,typeof clear==='function'?clear():clear);
    }
    throw Error('finishAutoAll did not settle');
  };
}"""


def fake_setup(page):
    page.add_init_script('(' + FAKE_WORKER + ')()')


def drain(page):
    for _ in range(20):
        page.evaluate("finishAutoAll()")
        page.wait_for_timeout(80)
        if page.evaluate("SIMQ.busy===null&&!simWaiting(cur[$('stage').value])&&!!document.querySelector('.party[data-team]')"):
            return
    raise AssertionError('latest calculation did not finish')


def test_auto_calculation_controls(browser, ctx):
    def setup(page):
        fake_setup(page)
        page.add_init_script("localStorage.setItem('pn.reco.auto','true')")
    page = open_page(browser, ctx, query='?auto=0', info=SYNTH, simauto=None, wait=False,
                     setup=setup)
    wait_myinfo(page)

    def idle():
        page.wait_for_timeout(450)  # Beyond the retained 300ms URL/shared debounce.
        assert page.locator('#reco-auto').count() == 0
        assert page.locator('[data-recoretry], [data-recocancel], .party[data-team]').count() == 0
        assert page.locator('[data-go]').inner_text() == '추천 편성 보기'
        assert page.evaluate('!REQ&&RECO.timer===null&&SIMQ.busy===null')

    idle()
    page.select_option('#stage', index=2)
    idle()
    assert page.evaluate('autoJobs.length') == 0, 'legacy preference must not start work'
    assert page.evaluate("LS.get('reco.auto')") is True, 'old preference need not be deleted'
    page.reload()
    wait_myinfo(page)
    idle()
    assert page.evaluate('autoJobs.length') == 0
    page.click('[data-go]')
    page.wait_for_function('autoJobs.length>0')
    page.click('[data-simcancel]')
    assert page.evaluate('autoJobs.every(j=>j.worker.stopped)&&SIMQ.busy===null')
    page.wait_for_timeout(450)
    assert page.evaluate('SIMQ.busy===null'), 'stop must not immediately restart'
    page.locator('[data-sim]').first.click()
    page.wait_for_function('autoJobs.some(j=>!j.worker.stopped)')
    drain(page)
    assert page.locator('[data-recoretry]').count() == 0
    old_jobs = page.evaluate('autoJobs.length')
    page.select_option('#stage', index=3)
    idle()
    assert page.evaluate('autoJobs.length') == old_jobs, 'changing a completed selection must wait for a click'
    # ?auto=1 still starts recommendation, respecting the separate simulation preference.
    page.evaluate('simAuto(false)')
    page.goto(ctx.base + '/index.html?auto=1&dev=1')
    wait_myinfo(page)
    page.wait_for_selector('.party[data-team]')
    assert page.locator('#reco-auto, [data-recoretry]').count() == 0
    assert page.evaluate("LS.get('reco.auto')===true&&localStorage.getItem('pn.simauto')==='0'")
    page.select_option('#stage', index=3)
    page.wait_for_selector('.party[data-team]')
    assert page.evaluate('autoJobs.length') == 0
    # Seasonal searches also keep their explicit start buttons.
    page.goto(ctx.base + '/index.html?auto=0&dev=1')
    wait_myinfo(page)
    for key in ['guild', 'cosmo']:
        page.evaluate("k=>{$('q').value='';$('content').value=contents.findIndex(c=>c.key===k);$('content').dispatchEvent(new Event('change'));}", key)
        page.wait_for_timeout(500)
        assert page.evaluate('SIMQ.busy===null&&GSR.phase!=="run"&&CSR.phase!=="run"')
        assert page.locator('[data-go]').count() or page.locator('[data-cs="start"]').count()
    # No stage, no automatic work; closed clash season is blocked even with ?auto=1.
    page.goto(ctx.base + '/index.html?auto=1&dev=1')
    wait_myinfo(page)
    page.evaluate("$('content').value=contents.findIndex(c=>c.key==='op');refreshTabs();$('q').value='no-such-stage';refreshStages()")
    page.wait_for_timeout(450)
    assert page.evaluate('SIMQ.busy===null&&!REQ')
    page.evaluate("history.replaceState(null,'','?auto=0');const c=contents.find(c=>c.key==='clash');c.seasonPeriod={start:'2000-01-01T00:00:00Z',end:'2000-01-02T00:00:00Z'};$('q').value='';$('content').value=contents.indexOf(c);refreshTabs()")
    page.wait_for_timeout(450)
    assert page.evaluate("seasonBlocked('clash')&&SIMQ.busy===null&&!REQ")
    assert not ctx.errors, ctx.errors
    page.close()
    return True, 'no toggle/retry; legacy true ignored on startup/reload/selection; manual start/stop; URL/simauto independence; seasonal gate'


def race_case(browser, ctx, mutation=None, main=False):
    def setup(page):
        fake_setup(page)
        if mutation:
            with open(os.path.join(ROOT, 'index.html'), encoding='utf-8') as f:
                html = f.read()
            if mutation == 'cancel':
                old, new = 'simInvalidate(); // cancel old selection immediately', '// cancellation removed'
            else:
                old, new = 'if(!o.live()||(m.id!=null&&m.id!==o.id))return;', '/* stale request guard removed */'
            assert old in html, mutation
            page.route('**/index.html?*', lambda r: r.fulfill(body=html.replace(old, new), content_type='text/html'))
    page = open_page(browser, ctx, query='?auto=1', info=SYNTH, simauto=None, wait=False, setup=setup)
    wait_myinfo(page)
    page.wait_for_function('autoJobs.length>0')
    if main:
        for _ in range(10):
            if page.evaluate('autoJobs.some(j=>j.req.n_runs===100)'):
                break
            page.evaluate('finishAutoAll()')
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
    page = open_page(browser, ctx, query='?auto=0', info=SYNTH, simauto='0', wait=False, setup=fake_setup)
    wait_myinfo(page)
    # The shared account arrives asynchronously, after normal page startup.
    url = page.evaluate("async()=>{const u=new URL(await shareUrlMi());u.searchParams.set('ag','1');return u.href}")
    saved = page.evaluate("JSON.stringify([LS.get('myinfo'),LS.get('growth.options'),LS.get('growth.history')])")
    page.goto(url)
    page.wait_for_function('MI.shared&&!!MI.growth&&!MI.pending')
    page.wait_for_function('autoJobs.length>0')
    assert page.locator('#assume-growth').is_checked()
    assert page.locator('#reco-auto').count() == 0

    def finish_growth():
        for _ in range(100):
            page.evaluate("finishAutoAll(()=>SIMQ.busy==='growth'?.95:.6)")
            page.wait_for_timeout(80)
            if page.evaluate("GROW.phase==='done'"):
                break
        assert page.evaluate("GROW.phase==='done'&&GROW.result.runs>0&&GROW.result.best.prog>0"), page.evaluate('GROW.errors')
        assert page.locator('#result-tab-growth').count() == 1
        assert page.evaluate("GROW.result.best.clear>GROW.result.baseline.clear")

    finish_growth()
    assert page.evaluate("JSON.stringify([LS.get('myinfo'),LS.get('growth.options'),LS.get('growth.history')])") == saved
    # After the shared link's initial run, a new selection needs an explicit click.
    old_jobs = page.evaluate('autoJobs.length')
    page.select_option('#stage', index=2)
    page.wait_for_timeout(450)
    assert page.locator('[data-go]').count() == 1
    assert page.locator('[data-recoretry], [data-recocancel], .party[data-team]').count() == 0
    assert page.evaluate('autoJobs.length') == old_jobs
    page.click('[data-go]')
    page.wait_for_function('autoJobs.some(j=>!j.finished&&!j.worker.stopped)')
    finish_growth()
    assert page.evaluate("GROW.sig===growthSig(contents[$('content').value],cur[$('stage').value])")
    assert page.evaluate("JSON.stringify([LS.get('myinfo'),LS.get('growth.options'),LS.get('growth.history')])") == saved
    # Keep the shared-link preparation window open so the actual stop button is testable.
    page.add_init_script("""const nativeTimeout=window.setTimeout;
      window.setTimeout=(fn,ms,...args)=>nativeTimeout(fn,ms===300?3000:ms,...args);""")
    page.goto('about:blank')  # Reopening the same hash URL alone may not reload the document.
    page.goto(url)
    page.wait_for_function('MI.shared&&!!MI.growth&&!MI.pending')
    page.click('[data-recocancel]')
    page.wait_for_timeout(3200)
    assert page.locator('[data-go]').count() == 1
    assert page.locator('[data-recocancel]').count() == 0
    assert page.evaluate('autoJobs.length===0&&!REQ&&RECO.timer===null&&!RECO.sharedPending')
    assert not ctx.errors, ctx.errors
    page.close()
    return True, 'shared link auto-start/growth/stop; subsequent selection requires click; local account/options/history preserved'


def test_auto_calculation_stop_buttons(browser, ctx):
    """멈춤 단추는 진행 표시가 갱신되는 사이에 눌러도 먹는다(실제 마우스: 내림 → 팀 결과 도착 → 올림).
    예선 진행 칸의 「취소」(전체 취소)와 클리어 추천 육성의 「중단」."""
    page = open_page(browser, ctx, query='?auto=0', info=SYNTH, simauto='0', wait=False, setup=fake_setup)
    wait_myinfo(page)
    url = page.evaluate("async()=>{const u=new URL(await shareUrlMi());u.searchParams.set('ag','1');return u.href}")
    page.goto(url)
    page.wait_for_function('MI.shared&&!!MI.growth&&!MI.pending')
    page.wait_for_function('autoJobs.length>0&&SIMQ.screening')
    # 1) 예선 중: 「지금까지 결과로 보기」 옆에 「취소」가 있고, 누르는 사이 한 작업자의 팀 결과가 와도 전부 멈춘다
    page.wait_for_selector('#out [data-k="progress"] button[data-simcancel]')
    buttons = page.locator('#out [data-k="progress"] button').all_inner_texts()
    press(page, '#out [data-k="progress"] button[data-simcancel]', "() => finishAutoJob(autoJobs.find(j=>!j.finished&&!j.worker.stopped))")
    stopped = page.evaluate("({all:autoJobs.every(j=>j.worker.stopped),busy:SIMQ.busy,err:SIMQ.err,screening:SIMQ.screening})")
    page.wait_for_timeout(450)
    assert page.evaluate('SIMQ.busy===null'), 'cancel must not immediately restart'
    assert buttons[-2:] == ['지금까지 결과로 보기', '취소'], buttons
    assert stopped == {'all': True, 'busy': None, 'err': '중단함', 'screening': False}, stopped
    # 2) 다시 시작해 추천을 끝내면 육성 탐색이 돈다. 「중단」을 누르는 사이 팀 결과(진행 글자 갱신)가 와도 중단된다
    page.locator('[data-sim]').first.click()
    for _ in range(100):
        if page.evaluate("SIMQ.busy==='growth'&&GROW.phase==='running'&&autoJobs.some(j=>!j.finished&&!j.worker.stopped)&&!!document.querySelector('[data-growth-cancel]')"):
            break
        page.evaluate("if(SIMQ.busy!=='growth')finishAutoAll(.6)")
        page.wait_for_timeout(80)
    assert page.evaluate("SIMQ.busy==='growth'&&GROW.phase==='running'"), page.evaluate('[SIMQ.busy,GROW.phase,GROW.errors]')
    page.click('#result-tab-growth')
    page.wait_for_selector('#growth-result [data-growth-cancel]')
    before = page.inner_text('#growth-result [data-k="growth-msg"]')
    press(page, '#growth-result [data-growth-cancel]', """() => {
      for(let i=0;i<3;i++)finishAutoJob(autoJobs.find(j=>!j.finished&&!j.worker.stopped),.9);   // 팀 셋이 끝남(작업자는 다음 팀을 받음)
      window.__growthMsg=document.querySelector('#growth-result [data-k="growth-msg"]').textContent}""")
    after = page.evaluate('window.__growthMsg')
    assert after != before and '3/' in after, (before, after)                # 누르는 사이 진행 글자는 실제로 바뀌었다
    assert page.evaluate("GROW.phase==='error'&&SIMQ.busy===null"), page.evaluate('[GROW.phase,SIMQ.busy]')
    assert '계산을 끝내지 못했어요' in page.inner_text('#growth-result')
    assert not ctx.errors, ctx.errors
    page.close()
    return True, '예선 「취소」·육성 「중단」: 누르는 사이 진행이 갱신돼도 클릭이 먹음 (%s → %s)' % (before.strip(), after.strip())


def register(api):
    for name in ['ROOT', 'SYNTH', 'open_page', 'wait_myinfo', 'press']:
        globals()[name] = getattr(api, name)
    return [test_auto_calculation_controls, test_auto_calculation_races,
            test_auto_calculation_shared_growth, test_auto_calculation_stop_buttons]
