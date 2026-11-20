"""Gwen interaction/lifetime/decoding regressions. Synthetic data; artifacts in _tmp/gwen-ux."""
import argparse
import json
from pathlib import Path
from test_gwen_art2 import ready, fixture, loaded, playing
from test_page import test_server
from playwright.sync_api import sync_playwright, TimeoutError, expect

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'_tmp/gwen-ux'
OUT.mkdir(parents=True,exist_ok=True)


def idle(page):
    fixture(page,page.evaluate('`<div class="party idle">${Ux.gwenIdle()}<div id="reco-actions"><button data-go="1">추천 편성 보기</button></div></div>`'))
    loaded(page,'#out .idle-gwen-art')
    return page.locator('#out [data-gwen-idle]')


def expression(scene):
    return scene.get_attribute('data-gwen-expression')


def dialogue_geometry_audit(page):
    page.emulate_media(reduced_motion='reduce');idle(page)
    changes=page.evaluate('''() => {
      const bubble=document.querySelector('#out .gwen-bubble');
      const selectors=['.gwen-poke','#reco-actions','#out'];
      const boxes=()=>selectors.map(s=>{const r=document.querySelector(s).getBoundingClientRect();return [r.x,r.y,r.width,r.height]});
      const before=JSON.stringify(boxes()),changes=[];
      for(const line of Object.values(Ux.GWEN_SAY).flat()){
        bubble.textContent=line;
        if(JSON.stringify(boxes())!==before||bubble.scrollHeight>bubble.clientHeight)changes.push(line);
      }
      return changes;
    }''')
    assert not changes,f'dialogue moved controls or overflowed: {changes}'


def idle_audit(page):
    page.clock.install()
    scene=idle(page)
    button=page.get_by_role('button',name='그웬 부르기')
    assert button.count()==1,'accessible button missing'
    assert button.get_attribute('type')=='button'
    a,b=button.bounding_box(),page.locator('#reco-actions').bounding_box()
    assert a['x']+a['width']<=b['x'] or a['y']+a['height']<=b['y'],'recommend button overlap'
    playing(page,scene.locator('img'))
    page.clock.run_for(1200)
    assert 'gwen-breathe' in scene.locator('img').evaluate('(e)=>getComputedStyle(e).animationName'),'breathing absent during rest'
    first=scene.locator('.gwen-bubble').inner_text()
    page.clock.run_for(12000)
    assert scene.locator('.gwen-bubble').inner_text()!=first,'dialogue did not rotate'
    assert scene.locator('[role=status]').inner_text()=='','automatic speech must not announce'
    page.clock.run_for(48000)
    assert expression(scene)=='doze','idle did not doze'
    page.keyboard.press('Shift')
    assert expression(scene)=='wake','input did not wake idle'
    page.clock.run_for(1600)
    button.focus()
    assert button.evaluate('(e)=>getComputedStyle(e).outlineStyle')!='none','focus ring missing'
    page.keyboard.press('Enter')
    assert expression(scene)=='shy','Enter click missing'
    assert scene.locator('[role=status]').inner_text(),'click feedback absent'
    # A held key counts once; three separate clicks reach cry, then ten seconds lock.
    page.keyboard.down('Enter');page.keyboard.down('Enter');page.keyboard.up('Enter')
    assert expression(scene)=='sulk','keyboard autorepeat counted'
    page.keyboard.press('Space')
    assert expression(scene)=='cry','third click must cry'
    button.click();assert expression(scene)=='cry','poke lock missing'
    page.clock.run_for(1600)
    assert expression(scene)=='ready','reaction did not restore'
    button.click();assert expression(scene)=='ready','ten-second lock missing'
    page.clock.run_for(8500)
    button.click();assert expression(scene)=='shy'
    page.clock.run_for(1600)
    # Visible time only: hidden time cannot consume idle or dialogue deadlines.
    page.evaluate('$("out").hidden=true')
    page.clock.run_for(90000)
    assert expression(scene)=='ready','hidden idle time was consumed'
    assert scene.get_attribute('data-gwen-paused')=='true','hidden CSS not paused'
    page.evaluate('$("out").hidden=false')
    loaded(page,'#out img')
    page.clock.run_for(1000)
    assert expression(scene)=='ready'
    # 호스트 부하/클릭 자동 대기 시간이 1.5초 반응 수명을 소비하지 않게 함.
    # 이후 가상 시간은 run_for로만 진행하고, 비동기 전환은 DOM 상태로 기다림.
    page.clock.pause_at(page.evaluate('Date.now() / 1000'))
    page.emulate_media(reduced_motion='reduce')
    expect(scene).to_have_attribute('data-gwen-paused','true')
    expect(scene).to_have_attribute('data-gwen-expression','ready')
    expect(scene.locator('img')).to_have_attribute('src',scene.locator('img').get_attribute('data-gwen-static'))
    expect(scene.locator('img')).to_have_attribute('data-gwen-playing','false')
    text=scene.locator('.gwen-bubble').inner_text()
    page.clock.run_for(90000)
    assert expression(scene)=='ready' and scene.locator('.gwen-bubble').inner_text()==text,'reduced motion rotated'
    button.click()
    expect(scene,'reduced motion blocks user feedback').to_have_attribute('data-gwen-expression','shy')
    page.clock.run_for(3100)
    expect(scene).to_have_attribute('data-gwen-expression','ready')
    page.emulate_media(reduced_motion='no-preference')


def cycle_audit(page):
    page.clock.install()
    for mode,names in [('inspect',['investigate','think','magnify']),('screen',['files','stamp','board']),('long',['walk','stakeout','zap','coffee'])]:
        fixture(page,page.evaluate('(m)=>Ux.gwenWork(m)',mode))
        loaded(page,'#out img');scene=page.locator('#out [data-gwen]')
        for name in names:
            assert expression(scene)==name,f'cycle stuck: {mode}/{name}'
            actual=scene.locator('img').get_attribute('data-gwen-art')
            assert actual==name,f'cycle art disconnected: {mode}/{name}: {actual}'
            assert scene.locator('img').get_attribute('data-gwen-motion').endswith('/'+name+'.webp')
            assert scene.get_attribute('data-gwen')==mode,'expression changed actual stage'
            assert ('gwen-roam' in scene.get_attribute('class'))==(name=='walk'),'only walk may roam'
            page.clock.run_for(9100)
        # Stop all scene time while hidden, then resume the pending deadline.
        before=expression(scene);page.evaluate('$("out").hidden=true');page.clock.run_for(30000)
        assert expression(scene)==before,'hidden cycle continued'
        page.evaluate('$("out").hidden=false');page.clock.run_for(9100)
        assert expression(scene)!=before,'cycle did not resume'


def result_audit(page):
    page.clock.install()
    # Execute the actual quickBox + simBar with only heavy recommendation helpers stubbed.
    page.evaluate('''() => {
      window.__rows=[{combo:{key:'a'},keys:['a'],q:{power:1},b:{},vd:'ok'}, {combo:{key:'b'},keys:['b'],q:{power:1},b:{},vd:'ok'}];
      window.__resultA={clear:.95,n:100};window.__resultB={clear:0,n:100};
      const sig=(st,t)=>t.combo.key;
      window.__reportBar=new Function('simSig','return ('+simBar.toString()+')')(sig);
      window.__reportBox=new Function('quickRows','ckey','quickWeak','simSig','miVerdict','scrNote','simBar','simCell','return ('+quickBox.toString()+')')(
        ()=>__rows,c=>c.key,()=>[],sig,()=>'',()=>'',__reportBar,()=>'');
      SIMQ.busy=null;SIMQ.err='';SIMQ.res.a=__resultA;SIMQ.res.b=__resultB;
      window.__paintReport=()=>{$('out').innerHTML=__reportBox(1,__rows,{}, {},'b','', '');$('out').scrollIntoView({block:'center'});};
      __paintReport();
    }''')
    loaded(page,'#out [data-gwen=report] img')
    assert expression(page.locator('#out [data-gwen=report]'))=='st_cry','shown result must drive report'
    assert page.locator('#out [data-gwen-reaction]').get_attribute('data-gwen-reaction') in ['notes','st_cry']
    page.clock.run_for(600)
    page.evaluate('__paintReport()');page.clock.run_for(1300)
    assert page.locator('#out [data-gwen=report]').count()==1,'result portrait disappeared after reaction'
    page.evaluate('__paintReport()')
    assert page.locator('#out [data-gwen=report]').count()==1,'completed result disappeared'
    assert page.locator('#out [data-gwen=report] img').get_attribute('data-gwen-playing')=='false','completed result replayed'
    # Horizontal clipping uses exactly the same visibility predicate as image playback.
    page.evaluate('''() => {window.__clipResult={};$('out').innerHTML='<div id="reportclip" style="position:fixed;left:110vw;top:0;width:200px">'+Ux.gwenReport(__clipResult)+'</div>';}''')
    page.clock.run_for(10000)
    assert page.locator('#reportclip [data-gwen]').count()==1,'offscreen report was consumed'
    page.evaluate('$("reportclip").style.left="0"');loaded(page,'#reportclip img');page.clock.run_for(1900)
    assert page.locator('#reportclip [data-gwen]').count()==1
    assert page.locator('#reportclip img').get_attribute('data-gwen-playing')=='false'


def decode_gate(page):
    page.evaluate('''() => {
      window.__created=[];window.__revoked=[];window.__gate=[];
      const create=URL.createObjectURL.bind(URL),revoke=URL.revokeObjectURL.bind(URL),decode=HTMLImageElement.prototype.decode;
      URL.createObjectURL=b=>{const u=create(b);__created.push(u);return u;};
      URL.revokeObjectURL=u=>{__revoked.push(u);revoke(u);};
      HTMLImageElement.prototype.decode=function(){const p=decode.call(this);return this.src.startsWith('blob:')?p.then(()=>new Promise(resolve=>__gate.push(resolve))):p;};
    }''')


def decode_audit(page,remove=False):
    decode_gate(page)
    fixture(page,page.evaluate('Ux.gwenWork("welcome")'))
    pic=loaded(page,'#out img')
    page.wait_for_function('__gate.length>0')
    assert pic.get_attribute('src').endswith('welcome.png'),'source changed before decode'
    if remove:
        page.evaluate('window.__old=document.querySelector("#out img");$("out").innerHTML="";__gate.splice(0).forEach(f=>f())')
        page.wait_for_timeout(150)
        assert page.evaluate('__created.every(u=>__revoked.includes(u))'),'removed decode retained URL'
        assert page.evaluate('__old.src.endsWith("welcome.png")'),'removed decode wrote stale source'
    else:
        page.evaluate('document.querySelector("#out img").dataset.gwenExpression="ready"')
        page.wait_for_function('document.querySelector("#out img").src.endsWith("ready.png")')
        page.wait_for_function('__gate.length>=2')
        page.evaluate('__gate.shift()()')
        page.wait_for_timeout(100)
        assert pic.get_attribute('src').endswith('ready.png'),'stale decode overwrote replacement'
        page.evaluate('__gate.splice(0).forEach(f=>f())')
        page.wait_for_function('(e)=>e.dataset.gwenPlaying==="true"',arg=pic.element_handle())
        page.evaluate('$("out").innerHTML=""');page.wait_for_timeout(50)
        assert page.evaluate('__created.every(u=>__revoked.includes(u))'),'replacement retained URL'


def fetch_audit(page):
    held=[];page._gwen_held=held
    def hold(route):
        held.append(route)
        page.evaluate('window.__cryHeld=true')
    page.route('**/cry.webp',hold)
    page.evaluate('''() => {window.__fetchCreated=[];window.__cryHeld=false;window.__cryRead=false;
      const create=URL.createObjectURL.bind(URL),fetch=window.fetch.bind(window);
      URL.createObjectURL=b=>{const u=create(b);__fetchCreated.push(u);return u;};
      window.fetch=async (...args)=>{const response=await fetch(...args);
        if(response.url.endsWith('/cry.webp')){const blob=response.blob.bind(response);
          response.blob=()=>blob().then(b=>{window.__cryRead=true;return b;});}
        return response;};}''')
    fixture(page,page.evaluate('Ux.gwenError("calculation")'))
    pic=loaded(page,'#out img')
    assert pic.get_attribute('data-gwen-art')=='cry','calculation art disconnected'
    assert pic.get_attribute('src').endswith('/cry.png'),'calculation still disconnected'
    page.wait_for_function('__cryHeld')
    assert held,'pending fetch path not exercised'
    page.evaluate('window.__fetchOld=document.querySelector("#out img");$("out").innerHTML=""')
    created=page.evaluate('__fetchCreated.length')
    for route in held:route.continue_()
    held.clear()
    page.wait_for_function('__cryRead')
    assert page.evaluate('__fetchOld.src.endsWith("/cry.png")'),'removed fetch wrote stale source'
    assert page.evaluate('__fetchCreated.length')==created,'removed fetch created a blob URL'


def report_loading_audit(page):
    page.clock.install();held=[]
    page.route('**/st_point.png',lambda route:held.append(route))
    fixture(page,page.evaluate('window.__slowReport={};Ux.gwenReport(__slowReport)'))
    page.wait_for_timeout(100)
    assert held,'report PNG delay was not exercised'
    page.clock.run_for(2100)
    assert page.locator('#out [data-gwen-report]').count()==1,'report expired before decoding'
    for route in held:route.continue_()
    try:
        page.wait_for_function('document.querySelector("#out [data-gwen-report] img").dataset.gwenLoaded==="true"')
        page.wait_for_function('document.querySelector("#out [data-gwen-report] img").dataset.gwenPlaying==="true"')
    except TimeoutError as error:
        raise AssertionError('report expired before decoding: reaction never started') from error
    page.clock.run_for(1700)
    assert page.locator('#out [data-gwen-report]').count()==1,'report did not get 1.8 visible seconds'
    page.clock.run_for(200)
    assert page.locator('#out [data-gwen-report]').count()==1
    assert page.locator('#out [data-gwen-report] img').get_attribute('data-gwen-playing')=='false','report expired before decoding'
    assert page.evaluate('Ux.gwenReport(__slowReport)')!=''


def seasonal_errors_audit(page):
    # Candidate-shortage fixture needs supported bosses to reach that validation.
    page.evaluate('D.cosmoRaid.bosses.forEach(b=>b.sim=true)')
    for kind,state,start in [('guild','GSR','guildSearchStart'),('cosmo','CSR','cosmoSearchStart')]:
        page.evaluate(f'''async () => {{
          MI.info={{units:[]}};MI.profiles.op={{results:{{}}}};MI.profiles.cosmo={{results:{{}}}};
          SIMQ.busy=null;GSR.phase='idle';CSR.phase='idle';$('assume-growth').checked=false;
          $('content').value=contents.findIndex(c=>c.key==='{kind}');
          await {start}();
        }}''')
        assert page.evaluate(f'{state}.errorCause')=='few','seasonal candidate shortage lost its cause'
        assert expression(page.locator(f'#{kind}-search [data-gwen]'))=='sulk','seasonal shortage must sulk'


def loading_audit(page,width,shots=False):
    page.emulate_media(reduced_motion='reduce')
    held=[];page._gwen_held=held
    page.route('**/ready.png',lambda route:held.append(route))
    page.route('**/savior/*_face.webp',lambda route:held.append(route))
    fixture(page,page.evaluate('`<div class="party idle">${Ux.gwenIdle()}<div id="reco-actions"><button>추천 편성 보기</button></div></div><div id="face-test">${face(R[0])}</div>`'))
    page.wait_for_timeout(200)
    page.evaluate('window.__shifts=[];window.__observer=new PerformanceObserver(l=>__shifts.push(...l.getEntries().map(e=>e.value)));__observer.observe({type:"layout-shift"})')
    selectors=['.gwen-poke','.idle-gwen-art','.idle-gwen .gwen-bubble','#reco-actions','#face-test img','#face-test','#out']
    before={s:page.locator(s).bounding_box() for s in selectors}
    assert all(before['.idle-gwen-art'][k]==before['.gwen-poke'][k] for k in ['width','height']),'fixed image space missing'
    for selector in ['.idle-gwen-art','#face-test img']:
        img=page.locator(selector)
        assert img.evaluate('(e)=>e.naturalWidth')==0,'delay was not exercised'
        assert img.evaluate('(e)=>getComputedStyle(e).opacity')=='0','unloaded image visible'
    if shots:page.screenshot(path=str(OUT/f'delayed-before-{width}.png'))
    page.wait_for_timeout(1500)
    for route in held:route.continue_()
    held.clear()
    page.wait_for_function('document.querySelector(".idle-gwen-art").dataset.gwenLoaded==="true"&&document.querySelector("#face-test img").dataset.imageLoaded==="true"')
    page.wait_for_timeout(200)
    after={s:page.locator(s).bounding_box() for s in selectors}
    assert before==after,f'loading geometry moved: {before} -> {after}'
    shifts=page.evaluate('__shifts')
    assert sum(shifts)==0,f'loading layout shifts: {shifts}'
    if shots:page.screenshot(path=str(OUT/f'delayed-after-{width}.png'))
    (OUT/f'layout-{width}.json').write_text(json.dumps({'before':before,'after':after,'layoutShift':sum(shifts)},indent=2),encoding='utf-8')


def blink_audit(page):
    assert page.evaluate('Ux.GWEN_SCENES.ready.blink')=='ready_blink.png','blink disconnected'
    page.clock.install();scene=idle(page);playing(page,scene.locator('img'))
    page.clock.run_for(1200)
    page.evaluate('''() => {window.__frames=[];new MutationObserver(()=>__frames.push({time:Date.now(),src:document.querySelector('#out img').src})).observe(document.querySelector('#out img'),{attributes:true,attributeFilter:['src']});}''')
    page.clock.run_for(3400)
    # The real blink PNG must decode before its 120–160 ms visible interval starts.
    page.wait_for_function('document.querySelector("#out img").currentSrc.endsWith("/ready_blink.png")')
    page.clock.run_for(160)
    frames=page.evaluate('__frames')
    assert len(frames)>=2,'blink did not close and reopen during PNG rest'
    assert frames[0]['src'].endswith('/ready_blink.png'),'blink frame disconnected'
    assert frames[1]['src'].endswith('/ready.png'),'blink did not reopen'
    assert 120<=frames[1]['time']-frames[0]['time']<=160,frames
    assert scene.locator('img').get_attribute('data-gwen-playing')=='false','blink ran during action'


def run_case(browser,base,audit,width=1280,source=None,template=None,touch=False):
    context=browser.new_context(viewport={'width':width,'height':950},has_touch=touch)
    context.add_init_script('Math.random=()=>.5')
    if source:context.route('**/ux_ui.js*',lambda r:r.fulfill(status=200,content_type='application/javascript',body=source))
    if template:context.route('**/index.html*',lambda r:r.fulfill(status=200,content_type='text/html',body=template))
    page=context.new_page();page.set_default_timeout(6000)
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    try:
        ready(page,base);audit(page);assert not errors,errors
    finally:
        for route in getattr(page,'_gwen_held',[]):route.abort()
        context.close()


def touch_audit(page):
    scene=idle(page);page.get_by_role('button',name='그웬 부르기').tap()
    assert expression(scene)=='shy'
    page.get_by_role('button',name='그웬 부르기').tap()
    assert expression(scene)=='sulk','pointer+click double counted'
    page.get_by_role('button',name='그웬 부르기').tap()
    assert expression(scene)=='cry'


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--mutations',action='store_true');ap.add_argument('--shots',action='store_true');ap.add_argument('--video',action='store_true');args=ap.parse_args()
    with test_server() as base,sync_playwright() as pw:
        browser=pw.chromium.launch()
        try:
            for width in [360,1280,1600]:
                for audit in [idle_audit,cycle_audit,result_audit,dialogue_geometry_audit]:
                    run_case(browser,base,audit,width);print(f'PASS {audit.__name__} {width}',flush=True)
                run_case(browser,base,lambda p:loading_audit(p,width,args.shots),width)
                print(f'PASS loading geometry/opacity/CLS {width}',flush=True)
            for audit in [decode_audit,lambda p:decode_audit(p,True),fetch_audit,report_loading_audit,seasonal_errors_audit,blink_audit,touch_audit]:
                run_case(browser,base,audit,touch=True);print(f'PASS {audit.__name__}',flush=True)
            if args.mutations:
                source=(ROOT/'ux_ui.js').read_text(encoding='utf-8')
                variants=[
                    ('cry-wire',"cry:{file:'cry'}","cry:{file:null,fallback:'surprised'}",fetch_audit,'calculation art disconnected'),
                    ('fetch-token','const data=await bytes(path);if(!valid(token))return;',
                     'const data=await bytes(path);',fetch_audit,'removed fetch created a blob URL'),
                    ('cycle-wire',"think:{file:'think'","think:{file:null,fallback:'report'",cycle_audit,'cycle art disconnected'),
                    ('blink-wire',"blink:'ready_blink.png'","blink:'ready.png'",blink_audit,'blink disconnected'),
                    ('cycle',"if(due('cycle')){","if(false){",cycle_audit,'cycle stuck'),
                    ('wake',"if(s.expression==='doze'){","if(false){",idle_audit,'input did not wake'),
                    ('token','s.token++;root.clearTimeout(s.timer);','root.clearTimeout(s.timer);',decode_audit,'stale decode'),
                    ('hidden','if(doc.hidden||!img.isConnected', 'if(!img.isConnected',None,''),
                    ('accessible','data-gwen-idle>','data-gwen-idle aria-hidden="true">',idle_audit,'accessible button'),
                    ('decode','await probe.decode();','probe.decode();',decode_audit,'source changed before decode'),
                    ('report-ready','report&&!report.done&&s.still','report&&!report.done',report_loading_audit,'report expired before decoding'),
                ]
                def hidden_audit(page):
                    page.clock.install();scene=idle(page)
                    page.evaluate('Object.defineProperty(document,"hidden",{configurable:true,value:true});document.dispatchEvent(new Event("visibilitychange"))')
                    page.clock.run_for(61000)
                    assert expression(scene)=='ready','document hidden time consumed'
                hidden_index=next(i for i,v in enumerate(variants) if v[0]=='hidden')
                variants[hidden_index]=(*variants[hidden_index][:3],hidden_audit,'document hidden time consumed')
                for name,old,new,audit,message in variants:
                    assert old in source,name
                    try:run_case(browser,base,audit,source=source.replace(old,new))
                    except AssertionError as e:
                        assert message in str(e),(name,str(e));print('CAUGHT intended assertion: '+name,flush=True)
                    else:raise AssertionError('mutation survived: '+name)
                html=(ROOT/'index.html').read_text(encoding='utf-8')
                old='Ux.gwenReaction(SIMQ.res[simSig(st,shown)]?.clear,SIMQ.res[simSig(st,shown)])';assert old in html
                try:run_case(browser,base,result_audit,template=html.replace(old,'Ux.gwenReaction(SIMQ.res[simSig(st,rows[0])]?.clear,SIMQ.res[simSig(st,rows[0])])'))
                except AssertionError as e:
                    assert 'shown result must drive report' in str(e);print('CAUGHT intended assertion: shown',flush=True)
                else:raise AssertionError('shown mutation survived')
                # Geometry rollback removes both attribute and CSS reservation, checked by the same browser assertion.
                def geometry_mutation(page):
                    page.add_style_tag(content='.idle-gwen-art{width:auto!important;height:auto!important;aspect-ratio:auto!important}')
                    loading_audit(page,1280)
                changed=source.replace('width="${size}" height="${size}"','')
                try:run_case(browser,base,geometry_mutation,source=changed)
                except AssertionError as e:
                    assert 'fixed image space missing' in str(e);print('CAUGHT intended assertion: geometry',flush=True)
                else:raise AssertionError('geometry mutation survived')
                def dialogue_mutation(page):
                    page.add_style_tag(content='@media(max-width:600px){.idle:has(>.idle-gwen){grid-template-columns:auto minmax(0,auto)}}')
                    dialogue_geometry_audit(page)
                try:run_case(browser,base,dialogue_mutation,width=360)
                except AssertionError as e:
                    assert 'dialogue moved controls' in str(e);print('CAUGHT intended assertion: dialogue-space',flush=True)
                else:raise AssertionError('dialogue-space mutation survived')
            if args.shots or args.video:
                context=browser.new_context(viewport={'width':1280,'height':950},record_video_dir=str(OUT/'video') if args.video else None)
                page=context.new_page();ready(page,base);idle(page)
                if args.video:page.wait_for_timeout(12000)
                if args.shots:page.screenshot(path=str(OUT/'idle-1280.png'))
                context.close()
                if args.video:page.video.save_as(str(OUT/'idle-12s.webm'))
        finally:browser.close()


if __name__=='__main__':main()
