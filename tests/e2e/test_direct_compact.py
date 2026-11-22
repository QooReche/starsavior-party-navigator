"""Compact direct results: real DOM geometry, keyboard disclosure and lossless details.

Synthetic account/worker results, shared production recommendation orchestration.
"""
import json
from pathlib import Path
from test_direct_party import ready, enter, pick_four, geometry
from test_direct_execution import fake
from test_direct_phase2 import choice, finished
from test_page import test_server
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'_tmp/compact'


def start(browser,base,width=1280,mutation=None):
    def setup(p):
        fake(p);p.clock.install()
        if mutation:
            file,old,new=mutation
            src=(ROOT/file).read_text(encoding='utf-8')
            assert old in src,file
            p.route('**/'+file,lambda route:route.fulfill(body=src.replace(old,new),content_type='application/javascript'))
    p=ready(browser,base,width,setup=setup,touch=width==360)
    enter(p);pick_four(p,width==360)
    p.locator('[data-direct-action=grown][data-slot="0"]').click()
    assert not p.locator('#direct-with').evaluate('e=>e.open'),'options open by default'
    p.locator('#direct-with-summary').focus();p.keyboard.press('Enter')
    p.wait_for_function("$('direct-with-summary').getAttribute('aria-expanded')==='true'")
    choice(p,2)
    p.locator('#direct-with-summary').focus();p.keyboard.press('Space')
    p.wait_for_function("$('direct-with-summary').getAttribute('aria-expanded')==='false'")
    assert '추천 같이 · 육성 포함' in p.locator('#direct-with-summary').inner_text()
    return p


def collapsed(p):
    assert p.locator('[data-direct-action=compare-toggle][aria-expanded=true]').count()==0,'comparison expanded by default'
    assert p.locator('.direct-row-detail:visible').count()==0,'comparison details visible by default'
    assert p.locator('#direct-steps li:visible').count()==0,'completed stages remained visible'
    assert p.locator('#direct-steps-toggle').get_attribute('aria-expanded')=='false'
    assert p.locator('#direct-steps-toggle').inner_text()=='3단계 완료'


def heights(p,width):
    geometry(p,width)
    result=p.evaluate('''()=>{const r=s=>document.querySelector(s).getBoundingClientRect();
      return {left:r('#direct-panel .result-summary').height,right:r('.direct-board-footer').bottom-r('#direct-board').top}}''')
    if width>=1200:
        assert result['left']<=result['right']*1.15,result
        actor=p.locator('#direct-result-lane .gwen-lane-poke').bounding_box()
        stats=p.locator('#direct-result-summary').bounding_box()
        assert 115<=actor['width']<=125 and actor['x']>=stats['x']+stats['width'],(actor,stats)
    return result


def speech_bounds(p):
    p.locator('.gwen-lane-poke').scroll_into_view_if_needed()
    p.clock.run_for(6500)
    p.locator('.gwen-lane-poke').click()
    p.clock.run_for(50)
    speech=p.locator('.gwen-lane-speech')
    assert speech.is_visible(),'reaction speech was not exercised'
    b=speech.bounding_box();lane=p.locator('#direct-result-lane').bounding_box()
    assert b['x']>=lane['x']-.5 and b['x']+b['width']<=lane['x']+lane['width']+.5,(b,lane)
    assert b['y']>=lane['y']-.5,(b,lane)
    # SAY.rift is never a bubble (gwen_lane.js skips kind 'rift'); it is the progress card's log line, checked below.
    clipped=p.evaluate("""()=>{const bubble=document.querySelector('.gwen-lane-speech'),lane=bubble.closest('.gwen-lane').getBoundingClientRect(),original=bubble.textContent;
      const failed=Object.entries(GwenLane.SAY).filter(([k])=>k!=='rift').flatMap(([,v])=>v).filter(text=>{bubble.textContent=text;const b=bubble.getBoundingClientRect();return b.top<lane.top-.5||b.left<lane.left-.5||b.right>lane.right+.5;});
      bubble.textContent=original;return failed;}""")
    assert not clipped,clipped
    p.clock.resume()
    log_bounds(p)


def log_bounds(p):
    # Every forced-scan system line, rendered by the production scrAlertHtml in a real progress card at this width.
    clipped=p.evaluate("""()=>{const host=document.createElement('div');host.innerHTML='<div class="party progress" data-alert="scan" data-state="running"><b class="case-title">x</b></div>';
      $('direct-panel').append(host);const card=host.firstElementChild,all=123456789,n=GwenLane.SAY.rift.length,failed=[],seen=new Set();
      for(let i=0;i<n;i++){const sc={got:Math.ceil(i*all/n),left:all};card.querySelectorAll('.scr-alert,.fx-log').forEach(x=>x.remove());
        card.querySelector('.case-title').insertAdjacentHTML('afterend',scrAlertHtml('scan',sc));
        const log=card.querySelector('.fx-log'),code=log.querySelector('code'),r=log.getBoundingClientRect(),c=card.getBoundingClientRect();seen.add(log.dataset.line);
        if(r.left<c.left-.5||r.right>c.right+.5||code.scrollWidth>code.clientWidth+1||code.scrollHeight>code.clientHeight+1)failed.push(code.textContent);}
      // Quick-scan lines shown for 0.8s before the alarm (data-alert=pre): step 1 [SCAN], step 2 adds [RESULT].
      card.dataset.alert='pre';const pre=[];for(const left of [SCR_ALERT.preMs,1]){card.querySelectorAll('.scr-alert,.fx-log').forEach(x=>x.remove());
        card.querySelector('.case-title').insertAdjacentHTML('afterend',scrAlertHtml('pre',{full:{length:all},alertAt:Date.now()+left}));
        const log=card.querySelector('.fx-log'),code=log.querySelector('code'),r=log.getBoundingClientRect(),c=card.getBoundingClientRect();pre.push(log.dataset.line+':'+code.textContent);
        if(r.left<c.left-.5||r.right>c.right+.5||code.scrollWidth>code.clientWidth+1||code.scrollHeight>code.clientHeight+1)failed.push(code.textContent);}
      host.remove();return {failed,seen:seen.size,n,pre};}""")
    assert clipped['seen']==clipped['n'],clipped
    assert clipped['pre']==['p1:[SCAN] 빠른 관측 — 후보 123,456,789개 판정 중…','p2:[SCAN] 빠른 관측 — 후보 123,456,789개 판정 중…[RESULT] 돌파 가능 0개'],clipped['pre']
    assert not clipped['failed'],clipped['failed']


def keyboard(p,selector):
    b=p.locator(selector);b.focus();p.keyboard.press('Enter')
    assert b.get_attribute('aria-expanded')=='true'
    target=b.get_attribute('aria-controls')
    assert p.locator('#'+target).is_visible()
    return b


def contract(browser,base,width):
    p=start(browser,base,width)
    p.evaluate('window.directDelay=100;void directRun()')
    p.wait_for_function("DIRECT.bundle.current==='reco'&&RECO.task&&!RECO.task.done")
    assert p.locator('#direct-steps li:visible').count()==3
    assert p.locator('#direct-steps-toggle').is_hidden()
    p.evaluate('window.directDelay=1');finished(p)
    collapsed(p);result=heights(p,width)
    speech_bounds(p)
    # Same rows, no extra computation; each old detail is reachable through a native button.
    posts=p.evaluate('directPosts.length')
    for kind in ['now','grown','reco','growth']:
        b=keyboard(p,f'[data-direct-action=compare-toggle][data-kind={kind}]')
        detail=p.locator('#'+b.get_attribute('aria-controls'))
        text=detail.inner_text()
        assert '클리어 82%' in text and '60턴' in text and '전투력 100,000' in text,text
        assert p.locator(f'[data-direct-row={kind}] .face').count()==4
        if kind!='now':assert '보수적 비교 범위' in text and '거의 같음' in text,text
        if kind=='reco':assert '추천 탭과 같은 결과' in text and '추천 탭에서 보기' in text
        if kind=='growth':assert '육성해도 더 나은 편성 없음' in text and '육성 계획 보기' in text
        p.evaluate('directResultsPaint()')
        assert b.evaluate('e=>e===document.activeElement') and b.get_attribute('aria-expanded')=='true'
        assert detail.inner_text()==text,'detail changed during paint'
        p.keyboard.press('Space');assert b.get_attribute('aria-expanded')=='false' and detail.is_hidden()
    assert p.evaluate('directPosts.length')==posts
    b=keyboard(p,'#direct-steps-toggle');assert p.locator('#direct-steps li:visible').count()==3
    p.keyboard.press('Space');collapsed(p)
    # Failed, skipped and cancelled rows stay visible while completed rows fold away.
    p.evaluate("DIRECT.bundle.steps[1].status='error';DIRECT.bundle.steps[1].message='실패 · 다시 시도';DIRECT.bundle.steps[2].status='skipped';DIRECT.bundle.steps[2].message='건너뜀';directResultsPaint()")
    assert p.locator('#direct-steps li:visible').count()==2
    assert p.locator('#direct-steps [data-step=direct]').is_hidden()
    assert '실패' in p.locator('#direct-steps').inner_text() and '건너뜀' in p.locator('#direct-steps').inner_text()
    keyboard(p,'#direct-steps-toggle');assert p.locator('#direct-steps li:visible').count()==3
    p.keyboard.press('Space');assert p.locator('#direct-steps li:visible').count()==2
    # A fresh run must expose all stages again and fold only on completion.
    p.evaluate("DIRECT.cache.clear();SIMQ.res={};window.directDelay=100;void directRun()")
    p.wait_for_function('DIRECT.bundle.running&&!!DIRECT.active')
    assert p.locator('#direct-steps li:visible').count()==3
    p.locator('#direct-run').click();finished(p)
    assert p.locator('#direct-steps li:visible').count()>=1
    geometry(p,width);assert not p.errors,p.errors;p.close()
    return {'width':width,**result}


def no_account(browser,base,width):
    p=ready(browser,base,width,info=None,setup=fake);enter(p);pick_four(p)
    p.locator('#direct-with-summary').click();choice(p,1);p.locator('#direct-with-summary').click()
    p.evaluate('window.directDelay=1;void directRun()');finished(p)
    assert p.locator('#direct-standard').is_visible()
    assert p.locator('.direct-row-detail:visible').count()==0
    heights(p,width);assert not p.errors,p.errors;p.close()


def mutations(browser,base):
    cases=[('rows default open',('direct_run.js','const open=openRows.has(kind);','const open=true;'),'comparison expanded by default'),
           ('completed stages always shown',('direct_bundle.js','const expanded=b.running||DIRECT.stepsExpanded;','const expanded=true;'),'completed stages remained visible')]
    for name,mutation,message in cases:
        p=start(browser,base,mutation=mutation)
        try:
            p.evaluate('window.directDelay=1;void directRun()');finished(p)
            try:collapsed(p)
            except AssertionError as e:
                assert str(e)==message,str(e)
                print('CAUGHT + restored:',name,flush=True)
            else:raise AssertionError('mutation survived: '+name)
        finally:p.close()

    mutation=('gwen_lane.js',
              "Math.max(half-x,Math.min(actor.offsetWidth/2,lane.clientWidth-half-x))",
              "Math.max(95-x,Math.min(actor.offsetWidth/2,lane.clientWidth-95-x))")
    p=start(browser,base,mutation=mutation)
    try:
        p.evaluate('window.directDelay=1;void directRun()');finished(p)
        try:speech_bounds(p)
        except AssertionError as e:
            assert str(e)!='reaction speech was not exercised',str(e)
            print('CAUGHT + restored: fixed-width speech clamp',flush=True)
        else:raise AssertionError('speech clamp mutation survived')
    finally:p.close()

    # A one-line, clipped log (no wrap) on a phone must be caught by the log check.
    p=start(browser,base,360)
    try:
        log_bounds(p)
        style=p.add_style_tag(content='.fx-log code{white-space:nowrap;overflow:hidden}')
        try:log_bounds(p)
        except AssertionError:print('CAUGHT + restored: unwrapped log line',flush=True)
        else:raise AssertionError('unwrapped log mutation survived')
        style.evaluate('e=>e.remove()');log_bounds(p)
    finally:p.close()


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    with test_server() as base,sync_playwright() as pw:
        b=pw.chromium.launch()
        results=[]
        for width in [1280,1600,360]:
            results.append(contract(b,base,width));print('PASS compact',results[-1],flush=True)
        for width in [1280,1600]:no_account(b,base,width)
        mutations(b,base);b.close()
    (OUT/'test-heights.json').write_text(json.dumps(results,indent=2),encoding='utf-8')


if __name__=='__main__':main()
