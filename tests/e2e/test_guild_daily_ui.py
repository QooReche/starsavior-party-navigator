"""P5: real daily planner + serial controlled worker, no Pyodide or account files."""
from pathlib import Path
from playwright.sync_api import sync_playwright
from test_page import test_server, FULL
from test_direct_party import ready

ROOT=Path(__file__).resolve().parents[2]
SETUP=r'''() => {
  const start=Date.parse('2026-11-26T12:00:00+09:00'),at=performance.now();Date.now=()=>start+performance.now()-at;
  const S=D.guild.search;if(S.preset!=='daily')throw Error('기본 daily 진입 누락');
  Object.assign(S,{poolSize:8,minPowerRatio:0,minRole:{},minFront:0,minDealer:0});
  S.excluded=[];S.daily.workers.max=1;S.daily.screen.runs=1;Object.assign(S.daily.rerank,{runs:2,keep:4});
  Object.assign(S.daily.probe,{runs:2,teams:4,levels:[0,1],steps:[6]});S.daily.final.runs=3;S.daily.combine.top=1;
  Object.assign(S.daily.place,{runs:[1,2,3],keep:1,recheckRuns:1});MI.brkLv={'스타피어서':7};
  const pool=GuildSearch.pool(S,MI.profiles.op.results,R);window.dailyBlocks=[pool.slice(0,4).map(x=>x.key),pool.slice(4,8).map(x=>x.key)];
  SIMQ.auto=false;simAutoKick=()=>{};window.dailyQueue=[];window.dailyAuto=false;window.dailyPosts=[];window.dailyStopStage=0;
  const search=GuildPlanner.search;
  GuildPlanner.search=cx=>{const phase=cx.onPhase;cx.onPhase=(name,total,meta)=>{phase(name,total,meta);if(meta.policyStage===dailyStopStage)dailyAuto=false;};return search(cx);};
  window.Worker=class {
    postMessage(m){dailyPosts.push(m);const send=data=>this.onmessage?.({data:{id:m.id,...data}});
      for(const t of m.teams)dailyQueue.push(()=>{if(this.dead)return;
        const prefix=JSON.stringify([D.guild.season.id,D.guild.dataVersion])+':';
        if(!t.key.startsWith(prefix))throw Error('길드 시즌 작업 키 누락');
        if(!t.key.endsWith('|step:'+t.options.guild.step))throw Error('길드 단계 작업 키 누락');
        if(t.options.guild.seasonId!==D.guild.season.id||t.options.guild.dataVersion!==D.guild.dataVersion)throw Error('길드 시즌 요청 불일치');
        const prior=t.options.merge_raw?JSON.parse(t.options.merge_raw):[];
        const block=dailyBlocks.some(xs=>t.party.units.every(u=>xs.includes(u.key)));
        const score=(block?(t.options.guild.step===7?100000:1000):1)+(t.options.break_skill?.name==='스타피어서'?100:0)
          +Math.round(t.party.units.reduce((sum,u)=>sum+u.stats_override.atk,0)/100);
        const raw=prior.concat(Array.from({length:m.n_runs},()=>['clear',10,20,1,score]));
        send({type:'team',key:t.key,result:{n:raw.length,clear:1,prog:1,progs:raw.map(x=>x[3]),via:{},u:{},guild:{base_scores:raw.map(x=>x[4])},raw:JSON.stringify(raw)}});
      });dailyQueue.push(()=>{if(!this.dead)send({type:'done'});});
    }terminate(){this.dead=true;}
  };
  window.dailyFlush=()=>{dailyAuto=true;const pump=()=>{if(!dailyAuto)return;for(let i=0;i<100&&dailyQueue.length&&dailyAuto;i++)dailyQueue.shift()();setTimeout(pump,10);};pump();};
  window.dailyStep=()=>dailyQueue.shift()?.();
  renderGuild();
}'''

def layout(p,width):
    assert p.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),'horizontal overflow'
    if width==1280:
        cards=p.locator('#guild-search .rowcards.gs-compact').first.bounding_box()
        head=p.locator('#guild-search .cs-bh').first.bounding_box()
        assert cards['x']<head['x'] and cards['width']>head['width'],'desktop cards must occupy the left column'
    if width==390:
        boxes=p.locator('#guild-search .rowcards.gs-compact').first.locator('.gc').evaluate_all('(xs)=>xs.map(x=>x.getBoundingClientRect().y)')
        assert len(boxes)==4 and max(boxes)-min(boxes)<2,boxes

def share_flow(browser,base):
    from urllib.parse import urlencode
    p=ready(browser,base,1280,info=FULL,query='?pm=reco&season=force')
    p.select_option('#content',p.evaluate('String(contents.findIndex(c=>c.key==="guild"))'))
    args=p.evaluate("""() => {const s=contents[$('content').value].stages.find(s=>parseInt(s.name,10)===7);return {c:'guild',gs:String(D.guild.season.id),s:s.tab+'|'+s.name,go:JSON.stringify({level:2,tiers:[],support:GuildView.supportChoices(D.guild)[1].id}),auto:'1',pm:'reco',season:'force'};}""")
    p.close()
    p=ready(browser,base,1280,info=FULL,query='?'+urlencode(args))
    try:
        assert p.evaluate('RECO.timer===null && REQ===false && !RECO.sharedPending && $("out").innerHTML===""')
        expected=p.evaluate('guildOptions()')
        assert expected['step']==7 and expected['level']==2
        assert expected['support']==__import__('json').loads(args['go'])['support']
        p.evaluate("directNavigate('direct')")
        assert p.locator('#direct-guild-controls #stage').is_visible()
        assert p.locator('#direct-guild-controls [data-g=level]').input_value()=='2'
        p.evaluate("directNavigate('home')")
        assert p.evaluate('document.querySelector(".stage-filter").parentElement===$("dcount").parentElement')
        p.evaluate("directNavigate('direct')")
        p.go_back();p.wait_for_function('DIRECT.mode==="home"')
        assert p.evaluate('document.querySelector(".stage-filter").parentElement===$("dcount").parentElement')
        assert not p.errors,p.errors
    finally:p.close()

def flow(browser,base,width,partial=False):
    p=ready(browser,base,width,info=FULL,query='?pm=reco&season=force')
    try:
        p.select_option('#content',p.evaluate('String(contents.findIndex(c=>c.key==="guild"))'))
        p.evaluate(SETUP)
        # Any selected stage must show daily, without exposing sets/sim tables.
        p.evaluate('$("stage").value="0";showInfo()')
        assert p.locator('.stage-filter').is_hidden()
        assert p.locator('#guild-extra').is_hidden()
        assert p.locator('#guild-search').is_visible()
        assert p.locator('#guild-extra [data-g=set]').count()==0
        assert p.locator('#guild-panel [data-k=gd-sim]').count()==0
        assert p.locator('.seal-stepper').count()==0
        assert '3장째는 구매 1회 성광석 30' in p.locator('#guild-search').inner_text()
        before=p.evaluate('Object.keys(localStorage).sort()')
        p.locator('[data-gs=start]').click()
        p.wait_for_function('dailyQueue.length>0||GSR.phase==="err"')
        assert p.evaluate('GSR.phase==="run"'),p.evaluate('GSR.msg')
        p.evaluate('delete guildDailyDateTick.day;guildDailyDateTick()')
        assert '날짜 바뀜' not in p.locator('[data-k=gs-day]').inner_text(),'first tick is not a reset'
        p.evaluate('window.stopNode=document.querySelector("[data-gs=partial]");dailyStep()')
        p.wait_for_timeout(250)
        assert p.evaluate('stopNode===document.querySelector("[data-gs=partial]")'),'progress replaced controls'
        assert p.locator('#guild-search [role=progressbar]').count()==1
        p.evaluate('dailyFlush()')
        p.wait_for_function('GSR.phase==="done"',timeout=20000)
        assert p.evaluate('GSR.teams.length===1 && GSR.teams[0].kind==="ex"')
        assert p.evaluate("GSR.teams[0].prog>0 && GSR.teams[0].brk==='스타피어서' && GSR.teams[0].brkLv===7")
        assert p.evaluate("dailyPosts.some(m=>m.teams.some(t=>t.options.break_skill?.name==='스타피어서'&&t.options.break_skill.level===7))")
        first=p.evaluate('JSON.stringify(GSR.teams[0])')
        if partial:p.evaluate('dailyStopStage=7')
        p.locator('[data-gs=follow]').click()
        if partial:
            p.wait_for_function('GSR.plan?.stages[GSR.stageIndex]?.policyStage===7 && !dailyAuto',timeout=20000)
            p.locator('[data-gs=partial]').click()
        p.wait_for_function('GSR.phase==="done"',timeout=20000)
        assert p.evaluate('JSON.stringify(GSR.teams[0])')==first
        assert p.locator('[data-gs=follow]').count()==0
        assert p.evaluate('GSR.sum>0 && GSR.teams.length===2'),p.evaluate('({sum:GSR.sum,teams:GSR.teams.length,plan:GSR.plan,warnings:GSR.warnings,rows:GSR.rows.map(t=>({keys:t.keys,score:t.score}))})')
        assert p.locator('#guild-search .cs-boss').count()==2
        assert p.evaluate('Object.keys(localStorage).sort()')==before,'daily added persistence'
        layout(p,width)
        if partial:assert '자리·리더 미평가' in p.locator('#guild-search').inner_text()
        saved=p.evaluate('JSON.stringify(GSR.teams)')
        p.locator('[data-gs=edit]').nth(1).click()
        p.wait_for_function('DIRECT.mode==="direct" && !!DIRECT.values')
        assert p.evaluate('JSON.stringify(DIRECT.draft.slots.map(s=>s.key))===JSON.stringify(GSR.teams[1].order)')
        assert p.evaluate('DIRECT.draft.leader===GSR.teams[1].leaderKey')
        assert p.locator('#direct-guild-controls #stage').is_visible()
        assert p.locator('#direct-guild-controls [data-g=support]').is_visible()
        assert p.evaluate('guildOptions().step===GSR.teams[1].step && guildOptions().support===GSR.teams[1].sup')
        assert p.evaluate('guildOptions().level===GSR.teams[1].level')
        assert p.evaluate('DIRECT.draft.brk===null || DIRECT.draft.brk.name===GSR.teams[1].brk')
        if partial:assert '자리·리더 미평가' in p.locator('#direct-guild-source').inner_text()
        assert p.evaluate('new URL(shareUrl()).searchParams.get("go")!==null'),'share go lost'
        p.evaluate("directNavigate('reco')")
        assert p.evaluate('JSON.stringify(GSR.teams)')==saved
        p.evaluate('$("q").value="6단계";refreshStages()')
        assert p.evaluate('!cur.some(s=>parseInt(s.name,10)===7)')
        p.locator('[data-gs=edit]').first.click()
        assert p.evaluate('DIRECT.mode==="direct" && guildOptions().step===GSR.teams[0].step && $("q").value===""')
        p.evaluate("directNavigate('reco')")
        assert p.evaluate('JSON.stringify(GSR.teams)')==saved
        layout(p,width)
        out=ROOT/'_tmp/p5';out.mkdir(parents=True,exist_ok=True)
        p.locator('#guild-search').screenshot(path=str(out/f'daily-{width}-{partial}.png'))
        # Date warning, closed-day input, and one-team/shortfall preview.
        p.evaluate("Date.now=()=>Date.parse('2026-11-27T04:00:01+09:00');guildDailyDateTick()")
        assert '날짜 바뀜' in p.locator('#guild-search').inner_text()
        assert '금요일 · EX 닫힘' in p.locator('[data-k=gs-day]').inner_text()
        assert '다음 EX는 토요일' in p.locator('[data-k=gs-day]').inner_text()
        p.evaluate('dailyAuto=false;dailyQueue=[];D.guild.search.poolSize=4;GSR.phase="idle";renderGuildSearch(true)')
        assert '오늘 편성 찾기 (1팀)' in p.locator('#guild-search').inner_text()
        # Early stop has no fake partial result.
        p.locator('[data-gs=start]').click();p.wait_for_function('dailyQueue.length>0')
        p.locator('[data-gs=partial]').click();p.wait_for_function('GSR.phase==="idle"')
        assert p.locator('[data-k=gs-daily-result]').count()==0
        if width==1280:
            # Compare the same four saviors so the block bonus cannot outweigh growth stats.
            p.evaluate('EXCL=new Set(R.filter(s=>!dailyBlocks[0].includes(s.key)).map(s=>s.key));window.dailyOriginal=JSON.stringify(MI.info);dailyPosts=[];dailyQueue=[];$("assume-growth").checked=true;renderGuildSearch(true)')
            p.locator('[data-gs=start]').click();p.wait_for_function('dailyQueue.length>0')
            p.evaluate('dailyFlush()');p.wait_for_function('GSR.phase==="done"',timeout=20000)
            assert p.evaluate('GSR.growth?.sum>0 && GROW.phase!=="running"'),'growth must use the daily shared run'
            assert p.evaluate('GSR.growth.teams.every(t=>t.prog>0) && GSR.growth.snapshot.errors.length===0')
            assert p.evaluate('JSON.stringify(MI.info)===dailyOriginal'),'growth changed the original account'
            assert p.locator('#growth-result').count()==0,'daily must not leave an obsolete growth tab'
            assert p.evaluate('GSR.growth.sum>GSR.sum'),'grown input stats must improve the synthetic score'
            p.locator('[data-fold=gs-grown] > summary').click()
            assert p.locator('[data-fold=gs-grown] .gc').count()==4
            assert p.locator('[data-fold=gs-grown] .growth-tasks').is_visible()
            p.locator('[data-gs=edit][data-grown=true]').click()
            assert p.evaluate('DIRECT.draft.slots.every(s=>s.grown)')
        assert not p.errors,p.errors
    finally:
        p.evaluate('dailyAuto=false;GSR.id++;GSR.handle?.cancel()');p.close()

if __name__=='__main__':
    with test_server() as base,sync_playwright() as pw:
        browser=pw.chromium.launch()
        try:
            share_flow(browser,base);print('PASS daily share/auto/navigation',flush=True)
            for width,partial in [(1280,False),(390,True)]:
                flow(browser,base,width,partial);print('PASS daily flow',width,'partial',partial,flush=True)
        finally:browser.close()
