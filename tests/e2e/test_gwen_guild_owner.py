"""Guild EX shares recommendation/search: the last user action owns Gwen."""
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright
from test_page import test_server, FULL
from test_direct_party import ready
from test_gwen_search_stage import FAKE


def owner(p, mode):
    assert p.evaluate('GwenLane.mount().state.mode') == mode, 'last action lost Gwen ownership'
    assert p.locator('.gwen-lane-actor:visible').count() == 1, 'one visible Gwen required'
    assert p.locator('#out [data-gwen-idle]:visible, #out .gwen-work:visible').count()==0, 'inactive inline Gwen still visible'
    other = 'guildSearch' if mode == 'reco' else 'reco'
    for part in ('board', 'result'):
        slot = p.locator(f'[data-gwen-slot="{other}-{part}"]')
        if slot.count():
            assert not slot.is_visible(), 'inactive lane leaves empty space: '+other+'-'+part
    if other == 'reco':
        assert not p.locator('#reco-gwen-stage').is_visible(), 'inactive reco wrapper leaves space'


def recommendation(p):
    # Exercise the real button entry and result updater; only worker delivery is controlled.
    p.evaluate('showReco()')
    p.evaluate('''() => {
      SIMQ.busy=null;SIMQ.screening=false;SIMQ.kick=false;
      const st=cur[$('stage').value];
      for(const box of Object.values(LASTQ))for(const t of box.rows)
        SIMQ.res[simSig(st,t)]={n:100,clear:.8,ci:[.7,.9],ta:35,frac:1,u:{}};
      run(true);
    }''')
    owner(p, 'reco')


def flow(browser, base, width, variant=None):
    def setup(page):
        if variant:
            file,old,new=variant
            source=(Path(__file__).resolve().parents[2]/file).read_text(encoding='utf-8')
            assert old in source,(file,old)
            page.route('**/'+file+'*',lambda r:r.fulfill(body=source.replace(old,new),content_type='text/html' if file.endswith('html') else 'application/javascript'))
    p=ready(browser,base,width,info=FULL,query='?pm=reco&season=force',setup=setup)
    try:
        p.select_option('#content',p.evaluate('String(contents.findIndex(c=>c.key==="guild"))'))
        assert 'EX' in p.locator('#stage option:checked').inner_text()
        p.evaluate(FAKE)
        p.evaluate('''() => {
          const S=D.guild.search;
          Object.assign(S,{poolSize:5,minPowerRatio:0,minRole:{},minFront:0,minDealer:0,screen2:{keep:5,runs:2},finalists:5});
          S.screen.runs=2;S.final.runs=2;S.final.levels=[4];S.final.supports=['fire'];
          SIMQ.auto=false;simAutoKick=()=>{};renderGuildSearch(true);
        }''')
        p.locator('#guild-search [data-gs=start]').click()
        p.wait_for_function('stageQueue.length>0')
        p.evaluate('stageFlush()')
        p.wait_for_function('GSR.phase==="done"')
        owner(p,'guildSearch')
        p.evaluate('showReco()')
        owner(p,'reco')
        p.evaluate('''() => {
          // Also exercise the simulation result slot with a synthetic encounter.
          const st=cur[$('stage').value];QK.d.st.guild||={};
          QK.d.st.guild[st.tab+'|'+st.name]=Object.values(QK.d.st.op)[0];
        }''')
        recommendation(p)
        p.evaluate("directNavigate('direct');directNavigate('reco')")
        owner(p,'reco')
        # Opposite order: recommendation -> a new search, then recommendation mid-search.
        p.evaluate('stageAuto=false')
        p.locator('#guild-search [data-gs=start]').click()
        p.wait_for_function('stageQueue.length>0')
        owner(p,'guildSearch')
        p.evaluate("directNavigate('direct');directNavigate('reco')")
        owner(p,'guildSearch')
        recommendation(p)
        p.evaluate('stageStep();stageRepeatPhase()')
        owner(p,'reco')
        p.evaluate('stageFlush()')
        p.wait_for_function('GSR.phase==="done"')
        owner(p,'reco')
        # Hidden shared-screen slots must not leak into another content's stage.
        p.evaluate('stageAuto=false')
        p.locator('#guild-search [data-gs=start]').click()
        p.wait_for_function('stageQueue.length>0')
        owner(p,'guildSearch')
        p.select_option('#content',p.evaluate('String(contents.findIndex(c=>c.key==="op"))'))
        p.evaluate('recoGwenShow(true,.5)')
        assert p.locator('#reco-board-lane').is_visible(), 'guild hiding leaked into another content'
        assert p.locator('#reco-board-lane .gwen-lane-actor').is_visible()
        assert not p.errors,p.errors
    finally:
        p.evaluate('stageAuto=false')
        p.close()


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--mutations',action='store_true');args=ap.parse_args()
    with test_server() as base,sync_playwright() as pw:
        browser=pw.chromium.launch()
        try:
            for width in (1280,390):
                flow(browser,base,width)
                print('PASS guild EX ownership',width,flush=True)
            if args.mutations:
                for name,variant,message in [
                    ('progress steals',('index.html',"GwenStage.activate(mode==='guildSearch'?guildGwenMode():mode)","GwenStage.activate(mode)"),'last action lost Gwen ownership'),
                    ('empty slot',('index.html','slot.hidden=guild&&owner!==mode||','slot.hidden='),'inactive lane leaves empty space'),
                    ('navigation steals',('direct_ui.js','(cosmo?searchMode:guildGwenMode())','searchMode'),'last action lost Gwen ownership'),
                    ('hidden content leak',('index.html',"for(const mode of ['reco','guildSearch'])", "if(guild)for(const mode of ['reco','guildSearch'])"),'guild hiding leaked'),
                    ('inline duplicate',('direct.css','body[data-guild-gwen-owner=guildSearch] #out :is([data-gwen-idle],.gwen-work){display:none}',''),'inactive inline Gwen still visible'),
                ]:
                    try:flow(browser,base,1280,variant)
                    except AssertionError as e:
                        assert message in str(e),(name,str(e))
                        print('CAUGHT',name,flush=True)
                    else:raise AssertionError('mutation survived: '+name)
                flow(browser,base,1280)
                print('PASS restored ownership',flush=True)
        finally:browser.close()
