"""과거 시즌 화면·공유 이관·실제 Pyodide 작업자의 시즌 전환."""
from pathlib import Path
from unittest.mock import patch
import json
from urllib.parse import urlencode


def season_setup(h, season_id):
    """Render an archived season through the production builder, then route one page."""
    import build_party_html
    import guild_defense
    root = Path(h.ROOT)
    season = guild_defense.load(root/'data/guild_seasons'/('%s.json' % season_id))
    preview = root/'local/guild-rotation'/('preview-%s.html' % season_id)
    preview.parent.mkdir(parents=True, exist_ok=True)
    with patch.object(guild_defense, 'load', return_value=season):
        build_party_html.main(str(preview))
    html = preview.read_text(encoding='utf-8')
    return lambda page: page.route('**/index.html*', lambda route: route.fulfill(body=html, content_type='text/html'))


def register(h):
    def test_guild_sets_hidden(browser, ctx):
        draft={'v':1,'slots':[{'key':key,'grown':False} for key in ['gwen','fei','professor-m','amora']],
               'leader':'gwen','brk':'auto'}
        old={'level':3,'tiers':[3,2,1,3],'support':'40051'}
        query='?'+urlencode(dict(c='guild',gs=30112,pm='direct',auto=0,ag=0,ao=0,
                                dp=json.dumps(draft),go=json.dumps(old)))
        page=h.open_page(browser,ctx,query,wait=False,info=None)
        page.wait_for_function('DIRECT.mode==="direct" && !!QK.d && !!DIRECT.slots')
        for width in (1280,390):
            page.set_viewport_size({'width':width,'height':900})
            assert page.locator('#guild-extra select[data-g="set"]').count()==0
            text=page.locator('#guild-extra').text_content()+page.locator('#guild-panel').text_content()
            assert '선택 효과' not in text and '(가정)' not in text
            assert page.evaluate('GS.sel.tiers.every(t=>t===0) && gsTiers().every(t=>t===0)')
            assert page.evaluate('guildOptions().level===3 && guildOptions().support==="40051"')
        h.open_fold(page,'gd-effects')
        page.click('#guild-extra button[data-g="best"]')
        assert page.evaluate('guildOptions().sets.every(t=>t===0) && guildOptions().level===D.guild.challenge.levels.length')
        page.select_option('#guild-extra select[data-g="level"]','3')
        page.select_option('#guild-extra select[data-g="support"]','40051')
        shared=page.evaluate('shareUrl()')
        assert page.evaluate('JSON.parse(new URL(shareUrl()).searchParams.get("go")).tiers.every(t=>t===0)')
        page.goto(shared)
        page.wait_for_function('window._ready && !!QK.d && !!DIRECT.slots')
        assert page.evaluate('guildOptions().level===3 && guildOptions().support==="40051" && guildOptions().sets.every(t=>t===0)')
        page.evaluate('SIMQ.n=3;directRefresh()')
        page.click('#direct-run')
        page.wait_for_function('!DIRECT.active && DIRECT.rows.now?.status==="done"',timeout=240000)
        assert page.evaluate('DIRECT.rows.now.snapshot.options.guild.sets.every(t=>t===0)')
        assert page.evaluate('DIRECT.rows.now.result.prog>0 && DIRECT.rows.now.result.guild.base_scores.length===3')
        assert '선택 효과' not in page.locator('#direct-result-summary').text_content()
        # Same season flag restores editors; the client engine and data remain available.
        page.evaluate('D.guild.sets.ui=true;renderGuild()')
        assert page.locator('#guild-extra select[data-g="set"]').count()==4
        h.open_fold(page,'gd-effects')
        page.select_option('#guild-extra select[data-g="set"][data-i="0"]','1')
        assert page.evaluate('guildOptions().sets[0]===1')
        assert not ctx.errors,ctx.errors
        page.close()
        return True,'1280/390 hidden UI, old share normalized, best/level/support, share round trip, real direct result, flag on'

    def test_guild_rotation_client(browser, ctx):
        page=browser.new_page(viewport={'width':390,'height':844})
        h.attach(page,ctx)
        season_setup(h, 30109)(page)
        page.goto(ctx.base+'/index.html?pm=reco&c=guild&gs=30109&season=force')
        page.wait_for_function('window._ready && !!QK.d')
        assert page.evaluate('D.guild.season.id')==30109
        assert page.evaluate('D.guild.season.boss.name') in page.locator('#guild-panel').inner_text()
        assert page.evaluate('guildStoreKey().includes(D.guild.dataVersion)')
        assert page.evaluate('!seasonBlocked("guild")')
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        # 실제 작업자는 한 개만 만든다. 화면의 시즌/버전 입력 그대로 실행함.
        result=page.evaluate("""() => new Promise((resolve,reject)=>{
          const worker=new Worker('sim_worker.js');
          const timer=setTimeout(()=>{worker.terminate();reject(Error('worker timeout'))},180000);
          worker.onmessage=e=>{const m=e.data;if(m.type==='error'){clearTimeout(timer);worker.terminate();reject(Error(m.msg))}
            if(m.type==='team'){clearTimeout(timer);worker.terminate();resolve(m.result)}};
          worker.postMessage({type:'run',id:1,base:new URL('.',location.href).href,stage:'guild/S1/6단계',n_runs:1,seed:3,
            options:{guild:guildIdentity(),build:'standard'},teams:[{key:'test',party:{units:['gwen','fei','professor-m','amora']}}]});
        })""")
        assert result['prog']>0 and result['gate']
        assert len(result['guild']['base_scores'])==1 and result['guild']['base_scores'][0]>0
        page.screenshot(path=str(Path(ctx.shots)/'guild_rotation_30109.png'),full_page=True)
        page.goto(ctx.base+'/index.html?pm=reco&c=guild&season=force')
        page.wait_for_function('window._ready && !!QK.d')
        assert page.evaluate('SHARE.gs===30111 && SHARE.guildExpired && seasonBlocked("guild")')
        assert '30111' in page.locator('#season-note').inner_text()
        assert not ctx.errors,ctx.errors
        page.close()
        return True,'30109 mobile page, version storage, real single-worker score, old link explicitly 30111 and blocked'
    return [test_guild_rotation_client,test_guild_sets_hidden]
