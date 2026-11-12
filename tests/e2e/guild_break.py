"""시즌4 가짜 결과로 4단계 표시·취소·레벨 서명을 확인한다."""
import os


def register(h):
    def test_guild_break_search(browser, ctx):
        page = h.open_page(browser, ctx)
        page.select_option('#content', value=page.evaluate("String(contents.findIndex(c=>c.key==='guild'))"))
        h.settle(page)
        page.evaluate("""() => {
          MI.brkLv={'스타피어서':7,'미지원 시험 스킬':9};
          const S=D.guild.search;
          Object.assign(S,{poolSize:5,minPowerRatio:0,minRole:{},minFront:0,minDealer:0,
            screen2:{keep:5,runs:3},finalists:5});
          S.screen.runs=2;S.final={runs:4,levels:[4],supports:['fire']};
          window.gbRequests=[];window.gbWorkers=[];window.gbIds=[];window.gbHold=false;
          window.Worker=class {
            constructor(){gbWorkers.push(this)}
            terminate(){this.dead=true}
            postMessage(req){
              gbRequests.push(req);
              if(gbHold&&req.n_runs===40)return;
              setTimeout(()=>{
                if(this.dead)return;
                for(const t of req.teams){
                  const id=t.key.split('|')[0];if(!gbIds.includes(id))gbIds.push(id);
                  const ix=gbIds.indexOf(id),b=t.options.break_skill;
                  const win=req.n_runs===40&&ix===4&&b?.name==='스타피어서'&&b.level===7&&t.options.guild.level===5;
                  const progs=win?[...Array(8).fill(1),...Array(32).fill(0)]:Array(req.n_runs).fill(.9-ix*.02);
                  this.onmessage({data:{id:req.id,type:'team',key:t.key,result:{n:req.n_runs,
                    prog:progs.reduce((a,b)=>a+b,0)/progs.length,progs,clear:win?.2:0,via:{trigger:1}}}});
                }
                this.onmessage({data:{id:req.id,type:'done'}});
              },0);
            }
          };
        }""")
        page.click('#guild-search [data-gs="start"]')
        page.wait_for_selector('#guild-search [data-k="gs-best"]')
        assert page.evaluate("GSR.rows[0].keys.join('+')===gbIds[4] && GSR.rows[0].brkLv===7 && GSR.rows[0].level===5")
        assert page.evaluate("gbRequests.filter(r=>r.n_runs===40).flatMap(r=>r.teams).length===5*3*2")
        assert page.locator('#guild-search [data-k="gs-best"] .bbar').inner_text() == '브레이크 스킬: 스타피어서 Lv.7'
        assert page.locator('#guild-search [data-gs]').count() == 2  # 기존 시작·협공뿐
        h.open_fold(page, 'gs-results')
        assert '브레이크 스킬: 스타피어서 Lv.7' in page.locator('#guild-search tbody tr').first.inner_text()
        page.set_viewport_size({'width':390, 'height':844})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        page.screenshot(path=os.path.join(ctx.shots, 'guild_break_mobile.png'), full_page=True)
        page.evaluate("MI.brkLv['스타피어서']=8;renderGuildSearch(true)")
        assert page.locator('#guild-search [data-k="gd-search-stale"]').count() == 1
        # 4단계에서 취소한 뒤 늦은 결과가 완료 상태를 되살리지 않는다.
        page.evaluate('gbHold=true;gbRequests=[]')
        page.click('#guild-search [data-gs="start"]')
        page.wait_for_function('gbRequests.some(r=>r.n_runs===40)')
        assert '4단계' in page.locator('#guild-search [data-k="gd-search-progress"]').inner_text()
        page.click('#guild-search [data-gs="cancel"]')
        assert page.evaluate("GSR.phase==='idle' && gbWorkers.every(w=>w.dead)")
        page.evaluate("gbWorkers.forEach(w=>w.onmessage({data:{type:'done'}}))")
        assert page.evaluate("GSR.phase==='idle'")
        # 미보유/미지원만 있으면 3단계 결과 그대로.
        for owned in ({}, {'미지원 시험 스킬': 9}):
            page.evaluate('(lv)=>{MI.brkLv=lv;gbRequests=[];gbHold=false}', owned)
            page.click('#guild-search [data-gs="start"]')
            page.wait_for_selector('#guild-search [data-k="gs-best"]')
            assert page.evaluate("gbRequests.every(r=>r.n_runs!==40)&&GSR.rows[0].keys.join('+')===gbIds[0]")
        assert not ctx.errors, ctx.errors
        page.close()
        return True, '브레이크 순위 역전·Lv 표시·기록 만료·4단계 취소·미보유/미지원 생략'

    return [test_guild_break_search]
