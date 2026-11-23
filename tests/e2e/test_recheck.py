"""현장 재조사(자동 추천 끝의 자리·리더 비교 연출, 11/23) — 실제 화면 흐름(simAutoKick → recoArrangeKick → recoArrange → 표준 본선 재측정 → 끝)을
가짜 작업자(작업 배분만 바꿈, 결과는 판별 progs 포함)로 돌려 상태 전이·화면을 확인함.

  진입(결과 판 유지·진행 칸 없음·사무실 장면·카드는 규칙 자리) → 단계(훑기 → 1단계 → 2단계 → 판정, 막대 증가)
  → 끝: 바뀜(카드 이동·칩·이전→지금 줄·금빛) / 그대로 / 되돌림 / 취소(«지금 자리로 확정») / 오류 / 보이는 팀 모두 100%(연출 없음)
  공통: 그웬은 화면에 한 곳, 위쪽 완료 배너 없음·결과 뒤 길이 접힘, 보드 사진 4장(전열 위·후열 아래·리더 표시).
  일부러 깨뜨리기(--mutations): 카드 고정(hold)·배우 숨김 규칙·사진 자리·길 접기·연출 없음 조건을 지우면 실패해야 함.

  <venv-pw python> -X utf8 tests/e2e/test_recheck.py [--mutations]
"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright
from test_page import test_server

ROOT = Path(__file__).resolve().parents[2]

SETUP = r"""(mode) => {
  recoClearTimer();clearTimeout(_rt);SIMQ.auto=false;localStorage.setItem('pn.simauto','0');
  REQ=true;RECO.standard=true;document.querySelectorAll('#own input').forEach((x,i)=>x.checked=i<8);updCount();
  const st=cur[$('stage').value];window.RT={st,mode,Q:[],log:[]};
  directManifest=async()=>({ver:'fake'});simWatch=()=>()=>{};scrPool=()=>[];
  simDispatch=(ws,jobs,h)=>{RT.Q.push({jobs,h});};
  run(true);   // 후보·서명 재료(SCROWN) 확정 — 자동 확인은 아직 끔
  // 예선은 끝난 것으로(강제 탐색을 거친 경우는 full·fullDone), 본선 결과는 규칙 자리로 채움
  const forced=mode.includes('forced');
  SIMQ.scr[scrKey(st,1)]={done:true,order:[],pool:forced?['x']:[],res:{},res2:{},...(forced?{full:['x'],fullDone:true}:{})};
  SIMQ.kick=true;run(true);
  const rows=LASTQ[1].rows;RT.ruleKeys=new Set(rows.map(t=>{const r=arrangeOf(t.combo,true);return PartyPlacement.executionKey(t.keys.slice(),{order:DirectParty.toEngine(r.order),leaderKey:r.lead});}));
  const W=(n,w,base=.6)=>{const progs=Array.from({length:n},(_,i)=>i<w?1:base);return {n,clear:w/n,prog:progs.reduce((a,b)=>a+b,0)/n,progs,ver:'fake',ci:[0,1],ta:20,ttk:20};};
  RT.W=W;
  const all100=mode.includes('all100');
  rows.forEach((t,i)=>{SIMQ.res[simSig(st,t)]=all100?W(100,100):W(100,[62,55,50][i]??50);});
  // 1팀(1안)만 이길 자리를 정함: 전열 둘과 리더가 모두 규칙 자리와 다른 첫 후보
  const t0=rows[0],rule=arrangeOf(t0.combo,true),front=new Set([rule.order[1],rule.order[2]]);
  RT.win=PartyPlacement.all(t0.keys.slice()).map(p=>PartyPlacement.executionKey(t0.keys.slice(),p)).find(k=>{const [,,o,l]=JSON.parse(k);return !(front.has(o[0])&&front.has(o[1]))&&l!==rule.lead;});
  RT.team0=JSON.parse(RT.win)[1];
  RT.fake=j=>{const runs=j.runs||100,o=j.options||{};
    if(!o.rng_streams){RT.log.push('measure');return W(100,mode.includes('revert')?50:86);}   // 표준 본선 재측정(바뀐 자리)
    const stage=runs===20?'screen':o.run_offset?'final200':'check100',n=stage==='final200'?200:runs;RT.log.push(stage);
    const changed=mode.includes('changed')||mode.includes('revert')||mode==='measurecancel',win=changed&&j.key===RT.win;
    return W(n,Math.round(n*(win?(stage==='screen'?.9:.85):.6)));};
  RT.step=(k=1)=>{for(let i=0;i<k&&RT.Q.length;i++){const {jobs,h}=RT.Q.shift();for(const j of jobs)h.team(j,{result:RT.fake(j)},{});h.done();}};
  run();   // 자동 확인 → recoArrangeKick
}"""

COUNT_GWEN = r"""() => {
  const vis=e=>e.isConnected&&e.checkVisibility({checkVisibilityCSS:true})&&e.getBoundingClientRect().height>1&&getComputedStyle(e).clipPath==='none';
  const lanesOk=e=>{const l=e.closest('.gwen-lane');return !l||l.getBoundingClientRect().height>1;};
  const out=[];
  for(const a of document.querySelectorAll('[data-gwen=lane]'))if(vis(a)&&lanesOk(a))out.push('배우');
  for(const g of document.querySelectorAll('.rc-gwen,.fx-gwen'))if(vis(g)&&lanesOk(g))out.push(g.className);
  return out;
}"""


def ready(page, base, mode, width):
    page.goto(base+'/index.html?season=force&pm=reco', wait_until='networkidle')
    page.wait_for_function('window._ready && QK.d')
    page.evaluate(SETUP, mode)
    if 'all100' in mode:
        return
    page.wait_for_function('RECHECK.state==="work"&&document.querySelector("#out .rc-strip[data-state=work]")')


def gwen_one(page, where):
    f = page.evaluate(COUNT_GWEN)
    assert len(f) <= 1, '%s: 그웬이 %d곳 %s' % (where, len(f), f)
    return f


def photos(page):
    return page.evaluate("""() => [...document.querySelectorAll('#reco-board-lane .rc-photo')].map(p=>({slot:+p.dataset.slot,lead:p.hasAttribute('data-lead'),src:p.querySelector('img')?.getAttribute('src')||''}))""")


def board_audit(page, arr_js):
    """사진 4장 = 화면 자리 순서([후열,전열,전열,후열]). 전열 = 위 2칸(0·1), 후열 = 아래 2칸(2·3), 리더 1장 표시."""
    ph = photos(page)
    assert len(ph) == 4, ('사진 4장', ph)
    arr = page.evaluate(arr_js)
    imgs = page.evaluate('k=>k.map(x=>BYKEY[x]?.img||"")', arr['order'])
    for i, p in enumerate(ph):
        assert p['src'] == imgs[i], ('사진 순서', i)
        assert (p['slot'] in (0, 1)) == (i in (1, 2)), ('전열 위·후열 아래', i, p['slot'])
        assert p['lead'] == (arr['order'][i] == arr['lead']), ('리더 표시', i)
    assert sorted(p['slot'] for p in ph) == [0, 1, 2, 3]


def work_audit(page):
    assert page.locator('#out [data-k=progress]').count() == 0, '재조사 중에 진행 칸으로 바뀜'
    assert page.locator('#out .rowcards').count() >= 1, '결과 판 유지'
    lane = page.locator('#reco-board-lane')
    assert lane.get_attribute('data-recheck') == 'work'
    page.wait_for_function('document.body.dataset.recheckArt==="ready"')
    page.wait_for_function("document.querySelector('#reco-board-lane').getBoundingClientRect().height>=180")
    # 카드는 끝날 때까지 규칙 자리(hold)
    keys = page.evaluate("[...document.querySelectorAll('#out .party[data-party=\"1\"] .rowcards .gc')].map(e=>e.dataset.key)")
    rule = page.evaluate("arrangeOf(LASTQ[1].rows[0].combo,true).order")
    shown = page.evaluate("document.querySelector('#out .party[data-party=\"1\"]').dataset.team")
    if shown == page.evaluate("UiShared.teamKey(LASTQ[1].rows[0].keys)"):
        assert keys == rule, ('재조사 중 카드는 규칙 자리', keys, rule)
    assert page.locator('#reco-result-lane').is_hidden(), '재조사 중 결과 자리 그웬 비움'
    assert page.locator('#out .rowcards[data-rc=work]').count() == 1
    assert page.locator('#reco-lane-banner').is_hidden()
    assert gwen_one(page, '재조사 중') == ['rc-gwen'], '장면 속 SD 그웬이 그 한 명'
    board_audit(page, 'RECHECK.state==="work"?arrangeOf(LASTQ[1].rows.find(t=>RECHECK.rows.includes(UiShared.teamKey(t.keys))).combo,true):null')


def hold_audit(page):
    # 판정 단계(바뀐 자리는 이미 기록, 표준 본선 재측정 중): 다시 그려도 카드·수치는 규칙 자리 그대로(카드 이동은 되돌림 판정 뒤에만)
    page.evaluate('run(true)')
    keys = page.evaluate("[...document.querySelectorAll('#out .party[data-party=\"1\"] .rowcards .gc')].map(e=>e.dataset.key)")
    assert keys == page.evaluate('arrangeOf(LASTQ[1].rows[0].combo,true).order'), ('판정 중 카드는 규칙 자리', keys)
    assert page.locator('#out [data-k=progress]').count() == 0 and page.locator('#out .rc-strip[data-state=work]').count() == 1


def stages(page):
    seen, vals = [], []
    for _ in range(12):
        st = page.evaluate('RECHECK.stage')
        seen.append(st)
        page.wait_for_timeout(260)   # 갱신 간격(PAINT_MS) 뒤 칸 값
        vals.append(page.evaluate("+(document.querySelector('#out .rc-pbar')?.getAttribute('aria-valuenow')||-1)"))
        if not page.evaluate('RT.Q.length'):
            page.wait_for_function('RT.Q.length||RECHECK.state!=="work"', timeout=10000)
        if page.evaluate('RECHECK.state') != 'work':
            break
        if st == 'fix':
            hold_audit(page)
        page.evaluate('RT.step()')
    return seen, vals


def end_audit(page, mode, width):
    state = page.evaluate('RECHECK.state')
    strip = page.locator('#out .rc-strip')
    assert strip.count() == 1, '끝 기록 줄'
    end = strip.get_attribute('data-end')
    text = strip.inner_text()
    chips = page.locator('#out .gc[data-rc-move]').count()
    if 'changed' in mode:
        assert state == 'done' and end == 'changed', (state, end)
        assert '진형 재정렬' in text and '62% → 86%' in text, text
        assert chips >= 2, '바뀐 카드 칩'
        assert page.locator('#out .rc-swap').count() == 1, '이전→지금 줄'
        assert page.evaluate("document.querySelector('#reco-board-lane').dataset.rcEnd") == 'changed'
        board_audit(page, 'arrangeOf(LASTQ[1].rows[0].combo)')
        assert page.evaluate("[...document.querySelectorAll('#out .party[data-party=\"1\"] .rowcards .gc')].map(e=>e.dataset.key)") == page.evaluate('arrangeOf(LASTQ[1].rows[0].combo).order')
        # 이전 자리로 보기 → 규칙 자리, 다시 누르면 지금 자리
        page.locator('#out [data-recheck-view]').click()
        assert page.evaluate("[...document.querySelectorAll('#out .party[data-party=\"1\"] .rowcards .gc')].map(e=>e.dataset.key)") == page.evaluate('arrangeOf(LASTQ[1].rows[0].combo,true).order')
        page.locator('#out [data-recheck-view]').click()
    elif 'revert' in mode:
        assert state == 'done' and end == 'same' and '되돌림' in text, (state, end, text)
        assert chips == 0
        assert page.evaluate('arrangeOf(LASTQ[1].rows[0].combo).order') == page.evaluate('arrangeOf(LASTQ[1].rows[0].combo,true).order')
    elif 'cancel' in mode:
        if mode == 'measurecancel':
            assert page.evaluate('arrangeOf(LASTQ[1].rows[0].combo).order') == page.evaluate('arrangeOf(LASTQ[1].rows[0].combo,true).order'), '판정 전 중단인데 바뀐 자리가 남음'
            assert page.locator('#out .gc[data-rc-move]').count() == 0
        assert state == 'cancel' and end == 'cancel' and '재조사 중단' in text, (state, end, text)
        assert page.evaluate('LASTQ[1].rows.every(t=>arrGet(recoIdentity(),UiShared.teamKey(t.keys))?.changed===false)')
    elif 'error' in mode:
        assert state == 'error' and end == 'error' and '끝내지 못함' in text, (state, end, text)
    else:
        assert state == 'done' and end == 'same' and '현 진형 유지' in text and '가장 좋음' in text, (state, end, text)
        assert chips == 0
    # 끝 장면 뒤: 길 접힘(완료 배너 없음) · 그웬은 결과 자리 한 곳
    page.wait_for_function("!document.querySelector('#reco-board-lane .rc-scene')&&document.querySelector('#reco-board-lane').getBoundingClientRect().height<1", timeout=5000)
    assert page.locator('#reco-lane-banner').is_hidden()
    page.locator('#reco-result-lane').scroll_into_view_if_needed()
    page.wait_for_timeout(200)
    assert gwen_one(page, '끝') == ['배우'] and page.locator('#reco-result-lane [data-gwen=lane]').count() == 1
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), '가로 넘침'


def scenario(browser, base, mode, width=1280, variant=None):
    ctx = browser.new_context(viewport={'width': width, 'height': 1000})
    if variant:
        file, old, new = variant
        source = (ROOT/file).read_text(encoding='utf-8')
        assert old in source, (file, old)
        ctx.route('**/'+file+'*', lambda r: r.fulfill(body=source.replace(old, new), content_type='text/html' if file.endswith('html') else 'text/css' if file.endswith('css') else 'application/javascript'))
    page = ctx.new_page()
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    try:
        ready(page, base, mode, width)
        if 'all100' in mode:
            page.wait_for_timeout(300)
            assert page.evaluate('RECHECK.state') == '' and page.locator('#out .rc-strip').count() == 0, '모두 100%면 연출 없음'
            assert page.evaluate('LASTQ[1].rows.every(t=>arrGet(recoIdentity(),UiShared.teamKey(t.keys))?.skip)')
            assert page.locator('#reco-board-lane .rc-scene').count() == 0
            return
        work_audit(page)
        if mode == 'measurecancel':
            # 바뀐 팀의 표준 본선을 잰(결과 저장) 뒤 판정 전에 «지금 자리로 확정» → 규칙 자리로 끝나야 함
            for _ in range(8):
                page.wait_for_function('RT.Q.length', timeout=10000)
                if page.evaluate('RT.Q[0].jobs.every(j=>!j.options?.rng_streams)'):
                    break
                page.evaluate('RT.step()')
            page.evaluate("()=>{const {jobs,h}=RT.Q.shift();for(const j of jobs)h.team(j,{result:RT.fake(j)},{});}")
            assert page.evaluate('RT.log.includes("measure")')
            page.locator('#out [data-recheck-stop]').click()
        elif 'cancel' in mode:
            page.evaluate('RT.step()')
            page.locator('#out [data-recheck-stop]').click()
        elif 'error' in mode:
            page.evaluate("RT.Q.shift().h.error('boom')")
        else:
            seen, vals = stages(page)
            want = ['screen', 'check100'] + (['final200'] if 'same' not in mode else []) + ['fix']
            got = [s for i, s in enumerate(seen) if s != (seen[i-1] if i else None)]
            assert [s for s in got if s in want] == want, ('단계 순서', seen)
            vals = [v for v in vals if v >= 0]
            assert vals == sorted(vals) and vals[-1] > vals[0], ('막대 증가', vals)
            assert page.evaluate('RT.log.includes("measure")') == (mode in ('changed', 'revert')), '바뀐 팀만 표준 본선 재측정'
        page.wait_for_function('RECHECK.state!=="work"', timeout=10000)
        end_audit(page, mode, width)
        assert not errors, errors
    finally:
        ctx.close()


MUTATIONS = [
    ('카드 고정(hold) 없음', ('index.html', 'if(v&&!recheckHold(id))return', 'if(v)return'), 'changed', '규칙 자리'),
    ('배우 숨김 규칙 없음', ('recheck.css', '[data-recheck-art] .gwen-lane[data-recheck] :is(.gwen-lane-actor){clip-path:inset(50%)}', ''), 'same', '그웬이 2곳'),
    ('사진 자리 뒤바뀜', ('gwen_lane.js', 'let f=0,b=2;return faces.map(x=>x.front?f++:b++);', 'let f=2,b=0;return faces.map(x=>x.front?f++:b++);'), 'same', '전열 위·후열 아래'),
    ('길 안 접힘', ('direct.css', '.reco-gwen-stage #reco-board-lane[data-fold],', '.reco-gwen-stage #reco-board-lane[data-nofold],'), 'same', 'Timeout'),
    ('판정 전 중단에 바뀐 자리 남음', ('recommend_runtime.js', 'if(!v||v.changed){', 'if(!v||v.changed&&!SIMQ.res[snapshot.sigAt(t,v)]){'), 'measurecancel', '바뀐 자리가 남음'),
    ('100%에도 연출', ('recommend_runtime.js', 'return !arrGet(snapshot.key,UiShared.teamKey(t.keys))&&!(now&&goalVal(now)>=1&&now.clear>=1);', 'return true;'), 'all100', '연출 없음'),
]


if __name__ == '__main__':
    with test_server() as base, sync_playwright() as pw:
        browser = pw.chromium.launch()
        for mode, width in [('changed', 1280), ('changed', 390), ('same', 1280), ('revert', 1280), ('cancel', 390), ('measurecancel', 1280), ('error', 1280), ('all100', 1280), ('same,forced', 390)]:
            scenario(browser, base, mode, width)
            print('PASS', mode, width, flush=True)
        if '--mutations' in sys.argv:
            for name, variant, mode, message in MUTATIONS:
                try:
                    scenario(browser, base, mode, 1280, variant)
                except Exception as e:
                    assert message in str(e), (name, str(e)[:300])
                    print('CAUGHT', name, flush=True)
                else:
                    raise AssertionError('mutation survived: '+name)
        browser.close()
    print('PASS recheck: 진입·단계·끝(바뀜/그대로/되돌림/취소/오류)·100% 연출 없음·그웬 한 곳·길 접힘·사진 4장' + (' + 변이 %d' % len(MUTATIONS) if '--mutations' in sys.argv else ''))
