"""그웬 SD 그림 작업 연출: 실제 렌더러·360px·취소 DOM·reduced-motion·캡처.

python -X utf8 tests/e2e/test_gwen_loading.py [--shots] [--video]
임시 파일은 작업 트리 _tmp, 캡처는 _shot_art_*.png, 영상은 _shot_load.webm.
"""
import argparse
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TMP = ROOT / '_tmp'
TMP.mkdir(exist_ok=True)
os.environ['TEMP'] = os.environ['TMP'] = str(TMP)

from test_page import test_server
from test_gwen_auto import lane_audit
from playwright.sync_api import sync_playwright, TimeoutError


ERROR_ART = {'calculation':'cry', 'few':'sulk', 'empty':'sulk', 'other':'surprised'}



def wait_decoded(page, image):
    # 정지 그림→애니메이션 전환이 decode 도중 일어나면 이전 요청은 EncodingError로 취소됨.
    # 실제 src 변경만 다시 기다리고, 손상된 그림 등 다른 디코드 오류는 그대로 실패시킴.
    page.wait_for_function("""async img => {
      const source=img.src;
      try { await img.decode(); }
      catch(error) {
        if(error.name==='EncodingError' && img.src!==source)return false;
        throw error;
      }
      return img.src===source && img.naturalWidth>0;
    }""", arg=image.element_handle())

def check_scene(page, mode, scope='#out', reduced=False, cause='other', art=None):
    scene = page.locator(f'{scope} [data-gwen]')
    assert scene.count() == 1, (scope, scene.count())
    assert scene.get_attribute('data-gwen') == mode
    scene.scroll_into_view_if_needed()
    page.wait_for_function('(e)=>!!e.getAttribute("src")', arg=scene.locator('img').element_handle())
    wait_decoded(page, scene.locator('img'))
    assert scene.locator('img').evaluate('(img)=>img.naturalWidth>0')
    if scene.get_attribute('data-gwen-reaction'):
        assert abs(scene.locator('img').bounding_box()['height']-(240 if page.viewport_size['width']>=1200 else 112))<1
    else:
        assert scene.locator('.gwen-scene').bounding_box()['height'] == (120 if page.viewport_size['width'] == 360 else 140)
    art = art or (ERROR_ART[cause] if mode == 'error' else
        {'inspect':'investigate','screen':'files','long':'walk','report':'report','welcome':'welcome'}[mode])
    assert scene.locator('img').get_attribute('data-gwen-art') == art, f'{mode}/{cause}: wrong art'
    assert scene.locator('img').get_attribute('data-gwen-motion').endswith(art+'.webp')
    animated = mode in ('inspect','screen','long') and not reduced
    expected = '/assets/ui_icons/gwen/' + art + ('.webp' if animated else '.png')
    if reduced or mode == 'long':
        page.wait_for_function('(a)=>a[0].currentSrc.endsWith(a[1])', arg=[scene.locator('img').element_handle(), expected])
    else:
        assert scene.locator('img').get_attribute('data-gwen-motion').endswith(art+'.webp')
    animation = scene.locator('img').evaluate('(img)=>getComputedStyle(img).animationName')
    if reduced or mode not in ('report', 'long'):
        assert animation == 'none', animation
    elif mode == 'long':
        assert animation == 'none', animation  # bounded traveler transform is audited in test_wide_gwen
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), '가로 넘침'


def error_wiring_audit(page):
    page.emulate_media(reduced_motion='reduce')
    for cause,art in ERROR_ART.items():
        page.evaluate('(c)=>{$("out").hidden=false;$("out").innerHTML=Ux.gwenError(c)}',cause)
        check_scene(page,'error',cause=cause,reduced=True)
        if art == 'surprised':
            continue
        original=page.evaluate('(a)=>Ux.GWEN_SCENES[a]',art)
        try:
            page.evaluate('''([a,c])=>{Ux.GWEN_SCENES[a]={file:null,fallback:'surprised'};
              $('out').innerHTML=Ux.gwenError(c);}''',[art,cause])
            try:
                check_scene(page,'error',cause=cause,reduced=True)
            except AssertionError as error:
                assert 'wrong art' in str(error),str(error)
                print(f'CAUGHT error wiring rollback: {cause}/{art}',flush=True)
            else:
                raise AssertionError(f'error wiring rollback survived: {cause}')
        finally:
            page.evaluate('([a,s,c])=>{Ux.GWEN_SCENES[a]=s;$("out").innerHTML=Ux.gwenError(c)}',[art,original,cause])
        check_scene(page,'error',cause=cause,reduced=True)
    page.emulate_media(reduced_motion='no-preference')


def exercise(page, base, width, shots):
    page.goto(base + '/index.html?season=force&pm=reco', wait_until='networkidle')
    page.wait_for_function('typeof Ux!=="undefined" && typeof SIMQ!=="undefined"')
    page.wait_for_timeout(1000)  # quick.json 완료 뒤 예약된 첫 화면 갱신까지 기다림.
    welcome = page.locator('[data-k="miguide"] .gwen-guide-art')
    welcome.scroll_into_view_if_needed()
    page.wait_for_function('(e)=>!!e.getAttribute("src")', arg=welcome.element_handle())
    assert welcome.get_attribute('data-gwen-static') == 'assets/ui_icons/gwen/welcome.png'
    wait_decoded(page, welcome)
    if shots:
        welcome.scroll_into_view_if_needed()
        page.screenshot(path=str(ROOT / f'_shot_art_welcome_{width}.png'))
    page.locator('#mi-open-import').click()
    page.locator('#drawer .gwen-welcome').wait_for(state='visible')
    assert page.locator('#drawer .gwen-welcome').get_attribute('data-gwen-static') == 'assets/ui_icons/gwen/welcome.png'
    assert page.locator('#drawer').evaluate('(e)=>e.scrollWidth<=e.clientWidth')
    if shots:
        page.screenshot(path=str(ROOT / f'_shot_art_import_{width}.png'))
    page.locator('#dclose').click()
    page.evaluate('''() => {
      RECO.timer=1;idleView();
      // 결과는 합성 상태로 강제하며 작업자를 실행하지 않음.
      window.__loadSt=cur[$('stage').value];
    }''')
    check_scene(page, 'inspect')

    def shot(name, scope='#out'):
        page.locator(scope).scroll_into_view_if_needed()
        if shots:
            page.screenshot(path=str(ROOT / f'_shot_art_{name}_{width}.png'))

    shot('wait')
    page.evaluate('growthControlPlace(true);RECO.timer=null;idleView()')
    assert page.locator('#out [data-gwen]').count() == 0
    page.evaluate('''() => {
      LASTQ[1]={rows:[{}, {}, {}]};SIMQ.busy=1;SIMQ.loaded=true;SIMQ.screening=true;
      SIMQ.scr[scrKey(__loadSt,1)]={got:2,left:80};
      growthControlPlace(true);$('out').innerHTML=simProgress(__loadSt);
      window.__cancel=document.querySelector('[data-simcancel]');
      window.__face=document.querySelector('#reco-board-lane .gwen-lane-actor');
    }''')
    lane_audit(page)
    shot('screen', '#reco-board-lane')
    page.evaluate('''() => {
      SIMQ.scr[scrKey(__loadSt,1)].got=3;
      simProgressSync(document.querySelector('[data-k="progress"]'),__loadSt);
    }''')
    assert page.evaluate('__cancel===document.querySelector("[data-simcancel]") && __face===document.querySelector("#reco-board-lane .gwen-lane-actor")')
    assert page.locator('[role=progressbar]').get_attribute('aria-valuenow') == '3'
    # 본선으로 전환해도 공용 진행 레인과 취소 단추를 유지함.
    page.evaluate('''() => {
      LASTQ[1].rows=[];SIMQ.screening=false;SIMQ.loaded=false;
      simProgressSync(document.querySelector('[data-k="progress"]'),__loadSt);
      window.__cancel=document.querySelector('[data-simcancel]');
    }''')
    lane_audit(page)
    page.evaluate('SIMQ.loaded=true;simProgressSync(document.querySelector("[data-k=progress]"),__loadSt)')
    lane_audit(page)
    assert page.evaluate('__cancel===document.querySelector("[data-simcancel]")')
    shot('final')
    for mode in ['inspect', 'screen', 'long', 'error', 'welcome']:
        page.evaluate('(mode)=>$("out").innerHTML=Ux.gwenWork(mode)', mode)
        check_scene(page, mode)
        page.emulate_media(reduced_motion='reduce')
        check_scene(page, mode, reduced=True)
        if mode == 'long':
            shot('reduced')
            # reduced-motion 규칙을 실제로 무효화하면 같은 검사가 실패해야 함.
            style = page.add_style_tag(content='#out .gwen-work .gwen-worker{animation:gwen-report 1s infinite!important}')
            try:
                check_scene(page, mode, reduced=True)
            except AssertionError:
                pass
            else:
                raise AssertionError('reduced-motion 변이를 검출하지 못함')
            style.evaluate('(e)=>e.remove()')
            check_scene(page, mode, reduced=True)
        page.emulate_media(reduced_motion='no-preference')
    page.evaluate('''() => {
      SIMQ.busy=1;SIMQ.err='';$('out').innerHTML=simBar(1,[],__loadSt,false);
    }''')
    check_scene(page, 'inspect')
    shot('simulation')
    page.evaluate('SIMQ.busy=null;SIMQ.err="시험 오류";SIMQ.errP=1;$("out").innerHTML=simBar(1,[],__loadSt,false)')
    check_scene(page, 'error', cause='calculation')
    shot('error')
    page.evaluate('SIMQ.err="";$("out").innerHTML=simBar(1,[],__loadSt,false)')
    assert page.locator('#out [data-gwen]').count() == 0
    # 결과 초상은 유지하고 1.8초 발표 반응만 종료함. 실제 quickBox 연결은 auto/ux 시험이 검사함.
    for reduced in (False, True):
        page.emulate_media(reduced_motion='reduce' if reduced else 'no-preference')
        page.evaluate('''() => {
          SIMQ.res.__art_report={n:100,clear:1};
          $('out').innerHTML=Ux.gwenReaction(1,SIMQ.res.__art_report);
        }''')
        check_scene(page, 'report', reduced=reduced, art=page.locator('#out img').get_attribute('data-gwen-art'))
        page.wait_for_timeout(500)
        shot('report_reduced' if reduced else 'report')
        page.evaluate('$("out").innerHTML=Ux.gwenReaction(1,SIMQ.res.__art_report)')
        check_scene(page, 'report', reduced=reduced, art=page.locator('#out img').get_attribute('data-gwen-art'))
        page.wait_for_timeout(1900)
        assert page.locator('#out [data-gwen]').count() == 1
        assert page.locator('#out img').get_attribute('data-gwen-playing') == 'false'
        page.evaluate('''() => {
          $('out').innerHTML=Ux.gwenReaction(1,SIMQ.res.__art_report);
        }''')
        assert page.locator('#out [data-gwen]').count() == 1
        assert page.locator('#out img').get_attribute('data-gwen-playing') == 'false'
    page.emulate_media(reduced_motion='no-preference')
    # HTML만 만들다 버렸거나 숨긴 탭에 넣었어도 처음 보일 때 발표함.
    page.evaluate('''() => {
      window.__hiddenResult={};Ux.gwenReport(__hiddenResult);
      $('out').innerHTML='<div id="art-hidden" hidden>'+Ux.gwenReport(__hiddenResult)+'</div>';
    }''')
    page.wait_for_timeout(1900)
    assert page.locator('#art-hidden [data-gwen="report"]').count() == 1
    page.evaluate('$("art-hidden").hidden=false')
    check_scene(page, 'report', art='st_point')
    page.wait_for_timeout(1900)
    assert page.locator('#art-hidden [data-gwen="report"]').count() == 1
    assert page.locator('#art-hidden img').get_attribute('data-gwen-playing') == 'false'
    # 旧SD 이미지로 되돌리면 실제 currentSrc 검사가 실패해야 함.
    page.emulate_media(reduced_motion='reduce')
    page.evaluate('$("out").innerHTML=Ux.gwenWork("screen")')
    check_scene(page, 'screen', reduced=True)
    page.locator('#out [data-gwen-art]').evaluate('(e)=>e.src="assets/ui_icons/gwen_sd.png"')
    page.wait_for_timeout(100)
    page.set_default_timeout(500)
    try:
        check_scene(page, 'screen', reduced=True)
    except (AssertionError, TimeoutError):
        pass
    else:
        raise AssertionError('그림 연결 되돌림을 검출하지 못함')
    finally:
        page.set_default_timeout(10000)
    page.evaluate('$("out").innerHTML=Ux.gwenWork("screen")')
    check_scene(page, 'screen', reduced=True)
    page.emulate_media(reduced_motion='no-preference')
    # 시즌별 실제 연결 및 코스모의 글자만 바꾸는 경로.
    for kind, state, renderer in [('guild', 'GSR', 'renderGuildSearch(true)'), ('cosmo', 'CSR', 'renderCosmoSearch()')]:
        page.evaluate(f'''() => {{
          MI.info={{units:[]}};$('content').value=contents.findIndex(c=>c.key==='{kind}');
          Object.assign({state},{{phase:'run',msg:'1단계: 후보 훑는 중',done:2,total:80,sig:{'gsSig()' if kind=='guild' else 'csSig()'}}});
          {renderer};
        }}''')
        scope = '#' + kind + '-search'
        check_scene(page, 'screen', scope)
        page.evaluate(f'''window.__cancel=document.querySelector('{scope} button[data-{'gs' if kind=='guild' else 'cs'}="cancel"]');
            window.__face=document.querySelector('{scope} .gwen-worker');{state}.done=3;{renderer}''')
        assert page.evaluate(f"__face===document.querySelector('{scope} .gwen-worker')")
        page.evaluate(f'{state}.msg="3단계: 상위 팀 확인 중";{renderer}')
        check_scene(page, 'long', scope)
        assert page.evaluate(f'''__cancel===document.querySelector('{scope} button[data-{'gs' if kind=='guild' else 'cs'}="cancel"]')''')
        shot(kind, scope)
        page.evaluate(f'{state}.phase="err";{state}.msg="시험 오류";{renderer}')
        check_scene(page, 'error', scope, cause='other')
        page.evaluate(f'{state}.phase="done";{state}.rows=[];{renderer}')
        check_scene(page, 'error', scope, cause='empty')
        page.evaluate(f'{state}.phase="idle";{renderer}')
        assert page.locator(scope + ' [data-gwen]').count() == 0
        page.evaluate(f'$("{kind}-search").hidden=true')
    page.evaluate('''() => {
      $('content').value=contents.findIndex(c=>c.key==='op');
      $('out').innerHTML='';$('assume-growth').checked=true;
      GROW.phase='running';GROW.msg='육성 계획 탐색 · 후보 2/80';GROW.result=null;growthPaint();
      window.__cancel=document.querySelector('[data-growth-cancel]');
      window.__face=document.querySelector('#growth-result .gwen-worker');
    }''')
    check_scene(page, 'long', '#growth-result')
    shot('growth')
    page.evaluate('GROW.msg="육성 계획 탐색 · 후보 3/80";growthPaint()')
    assert page.evaluate('__cancel===document.querySelector("[data-growth-cancel]") && __face===document.querySelector("#growth-result .gwen-worker")')
    page.locator('[data-growth-cancel]').click()
    assert page.locator('#growth-result [data-gwen]').count()==0, 'cancel is not an error'
    page.evaluate('growthNonePaint({key:"op"},{reason:"few"})')
    check_scene(page, 'error', '#growth-result', cause='few')
    shot('empty')
    page.evaluate('$("assume-growth").checked=false;growthPaint()')
    assert page.locator('#growth-result [data-gwen]').count() == 0
    page.evaluate('''() => {
      REQ=true;$('grow').add(new Option('내 정보','myinfo'));$('grow').value='myinfo';
      MI.info={units:[],star_link:{unlocked:true,slots:[],source:[],level:1}};
      SLOT.phase='running';SLOT.msg='슬롯 후보 확인 2/8';SLOT.result=null;
      slotPaint();$('star-link-result').open=true;
    }''')
    check_scene(page, 'long', '#star-link-result')
    shot('slots')
    page.evaluate('SLOT.phase="error";SLOT.msg="시험 오류";slotPaint()')
    check_scene(page, 'error', '#star-link-result', cause='calculation')
    page.evaluate('SLOT.phase="idle";slotPaint()')
    assert page.locator('#star-link-result [data-gwen]').count() == 0
    error_wiring_audit(page)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--shots', action='store_true')
    parser.add_argument('--video', action='store_true')
    args = parser.parse_args()
    with test_server() as base, sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            for width in [1280, 360]:
                context = browser.new_context(viewport={'width': width, 'height': 850},
                    **({'record_video_dir': str(TMP / 'video'), 'record_video_size': {'width': 720, 'height': 850}} if args.video and width == 360 else {}))
                context.add_init_script('Math.random=()=>.5')
                page = context.new_page()
                page.set_default_timeout(10000)
                try:
                    exercise(page, base, width, args.shots)
                    if page.video:
                        page.evaluate('$("out").innerHTML=simProgress(__loadSt);$("out").scrollIntoView()')
                        page.wait_for_timeout(3000)
                finally:
                    context.close()
                if page.video:
                    page.video.save_as(str(ROOT / '_shot_load.webm'))
                print(f'PASS Gwen {width}px: stages, errors, persistent results, stable buttons, reduced-motion mutation')
        finally:
            browser.close()


if __name__ == '__main__':
    main()
