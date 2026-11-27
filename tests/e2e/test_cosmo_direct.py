"""Real page, synthetic account, controlled workers; wide/narrow three-team flow."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
from test_direct_party import ready
from test_page import test_server

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'_tmp/cosmo-direct'
FAKE="""(() => {
window.cdPosts=[];window.cdDelay=1600;
window.Worker=class {
 postMessage(m){cdPosts.push(m);const send=x=>{if(!this.dead)this.onmessage({data:{id:m.id,requestId:m.requestId,job:m.job,jobId:m.jobId,owner:m.owner,revision:m.revision,...x}})};
 send({type:'stage',msg:'준비 끝'});
 setTimeout(()=>send({type:'stage',msg:'계산 중',completed:50,total:m.n_runs}),40);
 setTimeout(async()=>{const ver=(await fetch('sim/manifest.json').then(r=>r.json())).ver;
 const index=['mogulus','baskerville','disparity'].indexOf(m.teams[0].key);
 send({type:'team',key:m.teams[0].key,result:{ver,n:m.n_runs,clear:.8,ta:35,cosmo:{mean:10000+index*1000,top:12000+index*1000,clear:.8,frac:1},progs:[1],via:{},u:{}}});send({type:'done'});
 },cdDelay);
 }
 terminate(){this.dead=true;}
};})();"""

def account():
    info=json.loads((ROOT/'tests/fixtures/myinfo_synthetic.json').read_text(encoding='utf8'))
    growth=json.loads((ROOT/'data/growth.json').read_text(encoding='utf8'))
    owned={u['id'] for u in info['units']}
    for unit in list(growth['assumed']['units'].values())[:16]:
        if unit['uid'] not in owned:
            info['units'].append({**info['units'][0],'id':unit['uid']})
    path=OUT/'synthetic.json'
    path.write_text(json.dumps(info,ensure_ascii=False),encoding='utf8')
    return path

def flow(browser,base,width):
    p=ready(browser,base,width,info=account(),query='?c=cosmo&pm=direct',setup=lambda p:p.add_init_script(FAKE))
    p.wait_for_function('MI.growth && CDIRECT.state')
    panel=p.locator('#cosmo-direct-panel')
    bosses=p.evaluate('D.cosmoRaid.bosses.map(b=>b.key)')
    ordinary=p.evaluate('JSON.stringify(DIRECT.draft)')
    for i,boss in enumerate(bosses):
        panel.locator(f'[data-cd-boss={boss}]').click()
        if i:
            used=panel.locator('[data-cd-act=jump]').first
            assert used.get_attribute('aria-disabled')=='true'
            before=p.evaluate('JSON.stringify(CDIRECT.state.teams)')
            used.focus();p.keyboard.press('Enter')
            assert p.evaluate('CDIRECT.state.active')==bosses[0]
            assert p.evaluate('JSON.stringify(CDIRECT.state.teams)')==before
            panel.locator(f'[data-cd-boss={boss}]').click()
        if width<760 and panel.locator('[data-cd-act=pick]').first.is_hidden():
            panel.locator('[data-cd-act=picker]').click()
        for _ in range(4):panel.locator('[data-cd-act=pick]').first.click()
        panel.locator('[data-cd-act=leader]').last.click()
        panel.locator('#cd-level').select_option(str(i+2))
        assert panel.locator('#cd-run-one').get_attribute('aria-disabled')=='false'
    assert p.evaluate('CosmoDirect.usedBy(CDIRECT.state).size')==12
    assert panel.locator('#cd-run-all').get_attribute('aria-disabled')=='false'
    if width<760 and panel.locator('[data-cd-act=pick]').first.is_visible():panel.locator('[data-cd-act=picker]').click()
    panel.locator('#cd-run-all').click()
    p.wait_for_function('Object.values(CDIRECT.rows).some(r=>r.progress===50)')
    panel.locator('[data-cd-lane-slot]').scroll_into_view_if_needed()
    assert panel.locator('[data-cd-lane-slot] .gwen-lane-actor').count()==1
    assert panel.locator('[data-cd-gwen-slot] .gwen-lane-actor').count()==0
    p.wait_for_function('!CDIRECT.active && CosmoDirect.summary(CDIRECT.state,cdResults()).done===3')
    assert panel.locator('[data-cd-total]').inner_text()=='33,000'
    panel.locator('[data-cd-gwen-slot]').scroll_into_view_if_needed()
    p.wait_for_function("document.querySelector('[data-cd-gwen-slot] [data-gwen-report] img')?.naturalWidth>0")
    assert panel.locator('[data-cd-lane-slot] .gwen-lane-actor').count()==0
    assert panel.locator('.gwen-lane-actor').count()==1
    img=panel.locator('[data-cd-gwen-slot] img')
    assert img.get_attribute('data-gwen-expression').startswith('st_')
    assert panel.locator('.cd-lane-banner').is_visible()
    bounds=panel.locator('[data-cd-gwen-slot]').evaluate("""el=>{const a=el.getBoundingClientRect(),b=el.querySelector('img').getBoundingClientRect();return {left:b.left-a.left,right:a.right-b.right,bottom:a.bottom-b.bottom,top:b.top-a.top};}""")
    assert min(bounds.values())>=-1,bounds
    assert abs(bounds['left']-bounds['right'])<2,bounds
    # 결과 그웬은 합계 칸(4번째 칸) 안, 말풍선이 합계를 말함 — 자동 찾기 결과 요약과 같은 모양
    assert panel.locator('.cg-top .cg-say [data-cd-gwen-slot] .gwen-lane-actor').count()==1
    say=panel.locator('.cg-say-bubble').text_content();assert say=='다 해볼 만해, 자신 있어!합계 33,000!',say
    # 말풍선은 그웬 머리 위(꼬리 아래) — 다른 결과 화면과 같은 규칙. 칸 밖으로 잘리지 않고 말풍선 글자도 안 잘림.
    geo=panel.locator('.cg-say').evaluate("""el=>{const r=e=>e.getBoundingClientRect(),c=r(el),b=r(el.querySelector('.cg-say-bubble')),g=r(el.querySelector('[data-cd-gwen-slot] img'));
      return {gap:g.top-b.bottom,mid:Math.abs((b.left+b.right)/2-(g.left+g.right)/2),inside:b.left>=c.left-.5&&b.right<=c.right+.5&&b.top>=c.top-.5&&g.bottom<=c.bottom+1,
        clipped:[...el.querySelectorAll('.cg-say-bubble,.cg-say-bubble *')].some(e=>e.scrollWidth>e.clientWidth+1),
        tail:getComputedStyle(el.querySelector('.cg-say-bubble'),'::after').rotate}}""")
    assert geo['gap']>=-8 and geo['mid']<=12 and geo['inside'] and not geo['clipped'] and geo['tail']=='45deg',geo
    # 결과가 있는 카드는 보강 줄(난이도 태그 등)을 가짐 — 좁은 직접 편성 탭(760px 이하)에서는 숨김
    more=panel.locator('#cd-tab-alpha .cg-more, .cg-tab .cg-more').first
    assert more.count()==1 and ('난이도' in more.text_content()),more.count()
    assert more.is_visible()==(width>760),(width,more.is_visible())
    announcements=panel.locator('[data-gwen-report]').get_attribute('data-announcements')
    p.evaluate('cdPaint();cdPaint();directRefresh()')
    assert panel.locator('[data-gwen-report]').get_attribute('data-announcements')==announcements
    posts=p.evaluate('cdPosts')
    assert len(posts)==3 and all(m['owner']=='cdirect' for m in posts)
    assert [m['teams'][0]['options']['cosmo_raid']['level'] for m in posts]==[2,3,4]
    assert p.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    p.screenshot(path=str(OUT/f'result-{width}.png'),full_page=True)
    # One edited team loses its result; the other two still contribute completed cards.
    panel.locator('#cd-level').select_option('5')
    assert '2/3' in panel.locator('[data-cd-total]').inner_text()
    panel.locator('[data-cd-act=undo]').click()
    assert panel.locator('[data-cd-total]').inner_text()=='33,000'
    # Finishing while the «내 구원자» tab hides the editor must not leave it blank on return.
    panel.locator('#cd-level').select_option('6')
    panel.locator('#cd-run-one').click()
    p.wait_for_function('!!CDIRECT.active')
    p.locator('#tab-info').click()
    assert panel.is_hidden()
    p.wait_for_function('!CDIRECT.active')
    p.locator('#tab-reco').click()
    assert panel.is_visible()
    assert panel.locator('[role=tab]').count()==3 and panel.locator('#cd-run-one').count()==1,panel.inner_html()[:200]
    assert panel.locator('[data-cd-total]').inner_text()=='33,000'
    # Actual automatic-result button, exact engine positions/breaks/levels on import.
    p.evaluate("""() => {
      const teams=Object.entries(CDIRECT.state.teams).map(([boss,t],i)=>({boss,order:t.draft.slots.map(s=>s.key).reverse(),level:i+7,
        brk:csBreaks()[0]?.name||null,brkLv:csBreaks()[0]?.level||null,st:{mean:10000+i*1000,top:12000+i*1000,clear:.8,frac:1}}));
      teams.forEach(t=>t.keys=t.order);window.cdSearchRow={sum:33000,teams};
      Object.assign(CSR,{phase:'done',rows:[cdSearchRow],level:6,reqLevel:6,mode:'mean',fast:false,sig:csSig()});
      directNavigate('reco');renderCosmoSearch();
    }""")
    assert p.locator('[data-k=cs-best] [data-k=cs-boss-summary] .cg-tab').count()==3
    assert p.locator('[data-k=cs-best] [data-k=cs-team]').count()==3
    actions=p.locator('[data-k=cs-best] .season-actions')
    assert actions.locator('[data-cs=start]').count()==1
    assert actions.locator('[data-fold=cs-result-basis]').count()==1
    assert actions.bounding_box()['y']<p.locator('[data-k=cs-best] [data-k=cs-team]').first.bounding_box()['y']
    # 위 카드에 있는 기준 점수·클리어율은 팀 머리에서 다시 쓰지 않고, 카드에 없는 값(난이도·다른 점수·보스 깎음)만 남김
    heads=p.locator('[data-k=cs-best] .cs-bh').all_inner_texts()
    assert len(heads)==3 and all('난이도' in h and '상위 점수' in h and '보스 깎음' in h and '클리어율' not in h and '평균 점수' not in h for h in heads),heads
    assert p.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    p.screenshot(path=str(OUT/f'auto-result-{width}.png'),full_page=True)
    p.locator('[data-k=cs-best] [data-cs=edit]').click()
    assert panel.is_visible()
    assert p.evaluate('JSON.stringify(CDIRECT.state)===JSON.stringify(CosmoDirect.fromSearch(cdSearchRow,cdSeason()))')
    assert p.evaluate('JSON.stringify(LS.get(CosmoDirect.STORAGE_KEY))===JSON.stringify(CosmoDirect.storage(CDIRECT.state))')
    assert p.evaluate('JSON.stringify(DIRECT.draft)')==ordinary
    assert p.evaluate("new URL(shareUrl()).searchParams.has('cd') && !new URL(shareUrl()).searchParams.has('dp')")
    shared=p.evaluate('shareUrl()')
    expected=p.evaluate('JSON.stringify(CosmoDirect.share(CDIRECT.state))')
    p.goto(shared);p.wait_for_function('window._ready && CDIRECT.state && MI.growth')
    assert p.locator('#cosmo-direct-panel').is_visible()
    assert p.evaluate('JSON.stringify(CosmoDirect.share(CDIRECT.state))')==expected
    assert p.evaluate('CDIRECT.shared')
    local=p.evaluate('JSON.stringify(LS.get(CosmoDirect.STORAGE_KEY))')
    p.locator('#cd-level').select_option('14')
    assert p.evaluate('JSON.stringify(LS.get(CosmoDirect.STORAGE_KEY))')==local
    draft=p.evaluate('JSON.stringify(CDIRECT.state)')
    p.select_option('#content',p.evaluate("String(contents.findIndex(c=>c.key==='op'))"))
    p.wait_for_function('DIRECT.slots && DIRECT.values')
    p.evaluate('cdPaint()')  # A late worker/load callback must not remount an inactive editor.
    assert p.locator('.direct-slot').count()==4
    assert p.locator('#cosmo-direct-panel').inner_html()==''
    p.select_option('#content',p.evaluate("String(contents.findIndex(c=>c.key==='cosmo'))"))
    assert p.evaluate('JSON.stringify(CDIRECT.state)')==draft
    assert panel.locator('[role=tab]').count()==3
    assert not p.errors,p.errors
    p.close()

def real_workers(browser,base):
    p=ready(browser,base,1280,info=None,query='?c=cosmo&pm=direct')
    p.evaluate("""() => {
      SIMQ.n=2;
      const keys=R.slice(0,12).map(s=>s.key);
      D.cosmoRaid.bosses.forEach((b,i)=>keys.slice(i*4,i*4+4).forEach((key,slot)=>cdChange({type:'draft',boss:b.key,action:{type:'put',key,slot}})));
      cdChange({type:'levelAll',level:0});cdRun();
    }""")
    p.wait_for_function('!CDIRECT.active',timeout=180000)
    results=p.evaluate('cdResults()')
    assert len(results)==3,p.evaluate('[CDIRECT.error,CDIRECT.validation,CDIRECT.rows]')
    for boss,r in results.items():
        assert r['cosmo']['n']==2 and r['cosmo']['mean']>0 and r['cosmo']['frac']>0,(boss,r['cosmo'])
    assert p.evaluate('CosmoDirect.summary(CDIRECT.state,cdResults()).total')==sum(r['cosmo']['mean'] for r in results.values())
    assert not p.errors,p.errors
    p.close()

if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    with test_server() as base,sync_playwright() as pw:
        browser=pw.chromium.launch()
        try:
            for width in (1440,390):
                flow(browser,base,width)
                print(f'PASS cosmo direct {width}: 3 teams, duplicate jump, jobs, total, single Gwen, undo, search import, share')
            real_workers(browser,base)
            print('PASS cosmo direct real workers: all 3 bosses, positive damage, per-run score summaries')
        finally:browser.close()
