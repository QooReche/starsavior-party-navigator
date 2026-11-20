"""Actual page transport and persisted rear-row leader, using synthetic worker scores."""
import argparse
from playwright.sync_api import sync_playwright
from test_direct_party import ROOT, ready, enter, pick_four
from test_page import test_server

FAKE = """(() => {
window.layoutPosts=[];window.layoutDelay=10;
window.Worker=class {
 postMessage(m){layoutPosts.push(m);const send=x=>{if(!this.dead)this.onmessage({data:{id:m.id,requestId:m.requestId,job:m.job,jobId:m.jobId,owner:m.owner,revision:m.revision,...x}})};
 send({type:'stage',msg:'준비 끝'});
 setTimeout(async()=>{const ver=(await fetch('sim/manifest.json').then(r=>r.json())).ver;
 for(const t of m.teams){const keys=t.party.units.map(u=>u.key),best=keys.slice().sort().at(-1),score=keys[t.party.leader]===best?1:.2;
 send({type:'team',key:t.key,result:{ver,n:m.n_runs,clear:score,t60:score,prog:.8,progs:[.8],via:{},cosmo:{mean:score*100,top:score*100,clear:score,frac:.8}}});}
 send({type:'done'});},layoutDelay);
 }
 terminate(){this.dead=true;}
};})();"""

# Capture each message handler and request before cancellation. Even terminated
# workers can deliver queued replies here, so merely killing the worker is insufficient.
DELAYED = """(() => {
window.layoutPending=[];window.layoutPosts=[];
window.Worker=class {
 postMessage(m){layoutPosts.push(m);const handler=this.onmessage;
  const send=x=>handler({data:{id:m.id,requestId:m.requestId,job:m.job,jobId:m.jobId,owner:m.owner,revision:m.revision,...x}});
  send({type:'stage',msg:'준비 끝'});
  layoutPending.push(()=>{for(const t of m.teams){const keys=t.party.units.map(u=>u.key),score=keys[t.party.leader]===keys.slice().sort().at(-1)?1:.2;
   send({type:'team',key:t.key,result:{n:m.n_runs,clear:score,t60:score,prog:.8,progs:Array(m.n_runs).fill(.8),via:{}}});}
   send({type:'done'});});
 }
 terminate(){this.dead=true;}
};
window.layoutDrain=()=>{let count=0;while(layoutPending.length){if(++count>24)throw Error('duplicate placement jobs');layoutPending.shift()();}return count;};
})();"""


def delayed(browser,base,mutation=None):
    def setup(p):
        p.add_init_script(DELAYED)
        # This fixture always exercises one physical worker, including mutation runs.
        p.add_init_script("Object.defineProperty(navigator,'hardwareConcurrency',{get:()=>2});Object.defineProperty(navigator,'deviceMemory',{get:()=>1});")
        if mutation:
            path,old,new=mutation
            src=(ROOT/path).read_text(encoding='utf-8')
            assert old in src,old
            p.route('**/'+path,lambda route:route.fulfill(body=src.replace(old,new),content_type='text/javascript'))
    p=ready(browser,base,setup=setup)
    try:
        enter(p);pick_four(p)
        snapshot="JSON.stringify([DIRECT.draft,DIRECT.undo])"
        for action in ('undo','edit','content','reclick'):
            p.evaluate("directChange({type:'leader',key:DIRECT.draft.slots[1].key})")
            before=p.evaluate('JSON.stringify(DIRECT.draft)')
            old_undo=p.evaluate('JSON.stringify(DIRECT.undo)')
            p.locator('#direct-arrange').click()
            assert p.evaluate('!!DIRECT.placement && layoutPending.length===1 && SIMPOOL.workers.length===1')
            if action=='undo':
                p.locator('#direct-undo').click()
                assert p.evaluate('JSON.stringify(DIRECT.draft)')==old_undo
            elif action=='edit':
                # Return to the exact start input before the old result arrives (ABA).
                p.locator('[data-direct-action=grown][data-slot="0"]').click()
                p.locator('[data-direct-action=grown][data-slot="0"]').click()
                assert p.evaluate('JSON.stringify(DIRECT.draft)')==before
            elif action=='content':
                value=p.locator('#content').input_value()
                p.select_option('#content',p.evaluate("String(contents.findIndex(c=>c.key==='cosmo'))"))
                p.select_option('#content',value)
                assert p.evaluate('JSON.stringify(DIRECT.draft)')==before
            else:
                p.locator('#direct-arrange').click()
            assert p.evaluate('!DIRECT.placement'),f'{action}: placement not cancelled immediately'
            expected=p.evaluate(snapshot)
            assert p.evaluate('layoutDrain()')==1,'cancelled request dispatched more work'
            assert p.evaluate(snapshot)==expected,f'{action}: late reply changed draft/undo'
            assert p.locator('#direct-arrange').inner_text()=='자리 자동 배치'
            assert p.evaluate('!DIRECT.runError'),f'{action}: stale cancellation replaced current UI'

        # All 24 replies arrive, then cancel/restart before the await continuation.
        # Input equality alone cannot distinguish the old and new requests.
        # `void`: evaluate would otherwise await the pending comparison until its watchdog fires.
        p.evaluate("directChange({type:'leader',key:DIRECT.draft.slots[0].key});void directArrangeSim()")
        expected=p.evaluate(snapshot)
        p.evaluate("""() => {window.oldPlacement=DIRECT.placement;window.completed=layoutDrain();
          directArrangeSim();directArrangeSim();window.newPlacement=DIRECT.placement;}""")
        assert p.evaluate('completed===24 && newPlacement!==oldPlacement && DIRECT.placement===newPlacement'), 'settled old result replaced new request'
        assert p.evaluate(snapshot)==expected,'settled cancelled result changed draft/undo'
        assert p.locator('#direct-arrange').inner_text()=='배치 비교 0/24 · 취소'
        before=p.evaluate('JSON.stringify(DIRECT.draft)')
        assert p.evaluate('layoutDrain()')==24
        p.wait_for_function('!DIRECT.placement')
        assert p.evaluate('JSON.stringify(DIRECT.undo)')==before,'arrangement must record exactly its starting draft'
        assert p.evaluate("DIRECT.draft.leader===DIRECT.draft.slots.map(s=>s.key).sort().at(-1)")
        p.locator('#direct-undo').click()
        assert p.evaluate('JSON.stringify(DIRECT.draft)')==before
        assert p.locator('#direct-undo').is_disabled()

        # A changed input between resolution and continuation must also be rejected.
        p.evaluate('void directArrangeSim()')
        p.evaluate("() => {layoutDrain();DIRECT.draft={...DIRECT.draft,brk:null};}")
        assert p.evaluate('DIRECT.draft.brk===null && !DIRECT.undo'),'changed input accepted settled result'

        # A winning arrangement equal to the current draft still owns one undo entry.
        for _ in range(2):
            before=p.evaluate('JSON.stringify(DIRECT.draft)')
            p.locator('#direct-arrange').click()
            assert p.evaluate('layoutDrain()')==24
            p.wait_for_function('!DIRECT.placement')
            assert p.evaluate('JSON.stringify(DIRECT.undo)')==before,'unchanged winner reused an older undo entry'
        p.locator('#direct-undo').click()
        assert p.evaluate('JSON.stringify(DIRECT.draft)')==before
        assert p.locator('#direct-undo').is_disabled()
        assert not p.errors,p.errors
    finally:
        p.close()


def flow(browser, base):
    p=ready(browser,base,setup=lambda p:p.add_init_script(FAKE))
    enter(p);pick_four(p)
    original=p.evaluate('JSON.stringify(DIRECT.draft)')
    p.locator('#direct-arrange').click()
    p.wait_for_function('layoutPosts.length===24 && !DIRECT.placement')
    assert p.evaluate("DIRECT.draft.leader===DIRECT.draft.slots.map(m=>m.key).sort().at(-1)")
    assert p.evaluate("DIRECT.draft.slots.findIndex(m=>m.key===DIRECT.draft.leader)>=2")
    assert p.evaluate('layoutPosts.every(m=>m.teams[0].party.units.every(u=>u.stats_final))')
    saved=p.evaluate('JSON.stringify(DIRECT.draft)')
    p.evaluate('layoutDelay=2000;layoutPosts=[]')
    p.locator('#direct-arrange').click();p.wait_for_function('!!DIRECT.placement')
    p.locator('#direct-arrange').click();p.wait_for_function('!DIRECT.placement')
    assert p.evaluate('JSON.stringify(DIRECT.draft)')==saved
    p.reload();p.wait_for_function('window._ready && DIRECT.slots')
    assert p.evaluate('JSON.stringify(DIRECT.draft)')==saved
    p.select_option('#content',p.evaluate("String(contents.findIndex(c=>c.key==='cosmo'))"))
    p.wait_for_function('CDIRECT.state && MI.growth')
    p.evaluate("""() => {layoutPosts=[];layoutDelay=10;const b=CDIRECT.state.active;
      const keys=R.filter(r=>MI.info.units.some(u=>u.id===r.uid)).slice(0,4).map(r=>r.key);
      keys.forEach((key,slot)=>cdChange({type:'draft',boss:b,action:{type:'put',key,slot}}));
    }""")
    p.locator('[data-cd-act=arrange]').click()
    p.wait_for_function('layoutPosts.length===24 && !CDIRECT.placement')
    assert p.evaluate("(()=>{const d=CDIRECT.state.teams[CDIRECT.state.active].draft;return d.leader===d.slots.map(m=>m.key).sort().at(-1)&&d.slots.findIndex(m=>m.key===d.leader)>=2})()")
    expected=p.evaluate('JSON.stringify(CosmoDirect.share(CDIRECT.state))')
    p.goto(p.evaluate('shareUrl()'));p.wait_for_function('window._ready && CDIRECT.state')
    assert p.evaluate('JSON.stringify(CosmoDirect.share(CDIRECT.state))')==expected
    assert not p.errors,p.errors
    p.close()


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--mutations',action='store_true');args=ap.parse_args()
    with test_server() as base,sync_playwright() as pw:
        browser=pw.chromium.launch()
        try:
            delayed(browser,base);print('PASS delayed placement: undo, edit, content, cancel/restart, settled replies, exact undo')
            flow(browser,base);print('PASS placement page: 24 actual jobs, final stats, rear leader, cancel, storage, cosmo share')
            if args.mutations:
                mutations=[
                    ('placement_page.js','if(live()){DIRECT.placement=null;directChange','if(directInputKey()===input){DIRECT.placement=null;directChange','settled old result replaced new request'),
                    ('placement_page.js','DIRECT.placement===state&&directInputKey()===input','DIRECT.placement===state','changed input accepted settled result'),
                    ('direct_ui.js',"if(a==='undo'&&DIRECT.undo){DIRECT.placement?.cancel?.();", "if(a==='undo'&&DIRECT.undo){",'undo: placement not cancelled immediately'),
                ]
                for path,old,new,message in mutations:
                    try:delayed(browser,base,(path,old,new))
                    except AssertionError as e:
                        assert message in str(e),(message,str(e))
                        print('PASS mutation detected:',message)
                    else:raise AssertionError('placement mutation survived: '+message)
        finally:browser.close()
