"""「클리어 추천 육성」을 모든 콘텐츠로(11/14) — 스테이지형 8개 콘텐츠마다 실제 작업자로 탐색이 돌고 결과 칸이 남는지.

test_page.py 가 등록한다(같은 브라우저, 공개 가상 픽스처만). 제보 재현: 장비 탐사 혹한의 습격 20 에서 «켜짐» 표시만 있고
아무 결과·안내가 없었음 → 어느 콘텐츠든 결과(더 나은 편성) 또는 한 줄 안내가 남아야 한다.
"""

# (콘텐츠 key, 콘텐츠 이름, 스테이지 검색어, 고른 뒤 확인할 스테이지 이름 일부)
CASES = [
    ('op', '작전 (일반)', 'SECTOR 15-3', 'SECTOR 15-3'),
    ('oph', '작전 (어려움)', 'SECTOR 3-3', 'SECTOR 3-3'),
    ('daily', '일일 재화 던전', '도시 순찰', '도시 순찰'),
    ('equip', '장비 탐사', '혹한의 습격 20', '혹한의 습격 XX'),
    ('cube', '큐브 팰리스', '커널', '커널'),
    ('rush', '플래시 포인트', '매니저 그레고리 1', '매니저 그레고리'),
    ('clo', '성간 회랑', 'FLOOR 10', 'FLOOR 10'),
    ('clash', '격전 의뢰', '폐쇄된 심상', '폐쇄된 심상'),
]
STAR = {'equip', 'clash'}

STATE_JS = '''() => {const el=document.getElementById('growth-result'),r=GROW.result,c=contents[$('content').value],st=cur[$('stage').value];
  return {kind:c.key,stage:st.name,tab:st.tab,phase:GROW.phase,errors:GROW.errors,resultKind:r&&r.kind,runs:r&&r.runs,reason:r&&r.reason||null,
    base:r&&r.baseline?{clear:r.baseline.clear,t60:r.baseline.t60??null}:null,best:r&&r.best?{clear:r.best.clear,t60:r.best.t60??null}:null,
    better:!!r&&growthBetter(r.kind,r.baseline,r.best),state:el?el.dataset.state:null,text:el?el.innerText.replace(/\\s+/g,' ').trim():'',
    tag:document.querySelectorAll('#out .growth-on').length,star:starOf(c.key),turns:growthGoalTurns(c.key),
    fields:r?[...new Set(Object.values(r.snapshot.changes).flatMap(a=>a.changedFields))].sort():[],
    rule:MyInfoStats.rule_for_content(c.key),final:r&&r.team?r.team.party.units.every(u=>u.stats_final&&u.build==='none'):null,
    opts:simOpt(c.key),tabs:document.querySelectorAll('#result-tabs [role=tab]').length,
    tabNow:document.querySelector('#result-tab-now [data-tab-metric]')?.textContent||''}}'''


def register(api):
    for name in ['ROOT', 'SYNTH', 'open_page', 'choose', 'settle', 'overwrite_account']:
        globals()[name] = getattr(api, name)

    def run_case(browser, ctx, key, content, query, want):
        page = open_page(browser, ctx, info=SYNTH)
        choose(page, content, query)
        picked = page.evaluate("() => ({key:contents[$('content').value].key,name:cur[$('stage').value].name,tab:cur[$('stage').value].tab})")
        assert picked['key'] == key and want in picked['name'], picked
        overwrite_account(page)
        page.wait_for_function("GROW.phase==='done'||GROW.phase==='error'", timeout=600000)
        s = page.evaluate(STATE_JS)
        assert s['phase'] == 'done', s
        assert s['kind'] == key and s['resultKind'] == key and s['runs'] > 0 and s['reason'] is None, s
        assert s['final'], '육성 계정의 최종 능력치로 모의 전투해야 함'
        # 켰으면 결과 칸이 반드시 남는다: 더 나은 편성(done) 또는 한 줄 안내(none)
        assert s['tag'] >= 1 and s['state'] == ('done' if s['better'] else 'none') and len(s['text']) > 10, s
        assert '클리어 추천 육성' in s['text'], s
        if s['better']:
            assert s['tabs'] == 2 and '키워야 함' in page.inner_text('#growth-result'), s
        else:
            assert s['tabs'] == 0 and any(w in s['text'] for w in ['찾지 못했어요', '깨지 못했어요', '100%예요', '올릴 항목이 없어요']), s
        # 그 콘텐츠의 규칙: 3별 목표(장비 탐사·격전 의뢰)는 60턴 내 확률로, 플래시 포인트는 레벨·공명 고정, 재점화는 작전만
        if key in STAR:
            assert s['star'] == 60 and s['turns'] == 60 and s['opts'].get('star_turns') == 60 and s['best']['t60'] is not None and s['base']['t60'] is not None, s
            assert '60턴' in s['text'], s
            if s['better']:
                assert s['tabNow'].startswith('60턴 내 '), s
        else:
            assert s['star'] == 0 and s['best']['t60'] is None and '60턴' not in s['text'], s
        if key == 'rush':
            assert s['rule'] == 'fixed200' and 'level' not in s['fields'] and 'resonance' not in s['fields'] and 'equip' in s['fields'], s
        else:
            assert s['rule'] == 'normal' and 'level' in s['fields'], s
        assert 'rekindle' not in s['opts'], s
        assert not ctx.errors, ctx.errors
        return page, s

    def make(key, content, query, want):
        def test(browser, ctx):
            page, s = run_case(browser, ctx, key, content, query, want)
            extra = ''
            if key == 'equip':
                # 목표 전환: «클리어만»으로 바꾸면 다시 계산하고 문구·숫자가 클리어율 기준이 된다(60턴 표현 없음)
                page.evaluate("() => {document.getElementById('optbox').open=true}")
                page.select_option('#goal', '0')
                settle(page)
                # 조건이 바뀌면 지난 결과는 지워지고, 모의 전투를 다시 실행하기 전까지는 대기 안내가 남는다(조용히 사라지지 않음)
                wait = page.evaluate("() => {const e=document.getElementById('growth-result');return e?[e.dataset.state,e.innerText]:null}")
                assert wait and wait[0] == 'idle' and '모의 전투를 실행하면 이어서 계산해요' in wait[1], wait
                page.click('.party[data-party="1"] button[data-sim="1"]')
                page.wait_for_function("(GROW.phase==='done'||GROW.phase==='error')&&GROW.result&&GROW.result.best&&GROW.result.best.t60==null", timeout=600000)
                c = page.evaluate(STATE_JS)
                assert c['phase'] == 'done' and c['star'] == 0 and 'star_turns' not in c['opts'] and c['best']['t60'] is None, c
                assert c['state'] == ('done' if c['better'] else 'none') and '60턴' not in c['text'] and len(c['text']) > 10, c
                extra = ' / 클리어만: %s %s→%s' % (c['state'], c['base'], c['best'])
            if key == 'oph':
                # 재점화는 작전·작전 어려움의 모의 전투 옵션에만 붙는다(육성 탐색도 같은 옵션을 쓴다)
                page.evaluate("() => {document.getElementById('optbox').open=true}")
                page.select_option('#rk', '2')
                settle(page)
                assert page.evaluate("simOpt('oph').rekindle===2&&simOpt('op').rekindle===2&&!('rekindle' in simOpt('equip'))&&growthConditions(contents[$('content').value]).rules.rekindle===2")
                page.select_option('#rk', '0')
                settle(page)
                extra = ' / 재점화 옵션 연결'
            page.screenshot(path=__import__('os').path.join(ctx.shots, 'growth_all_%s.png' % key), full_page=True)
            page.close()
            return True, '%s %s: %s 지금 %s → 맞추면 %s · %d판 · 올린 항목 %s%s' % (key, s['stage'], s['state'], s['base'], s['best'], s['runs'], ','.join(s['fields']), extra)
        test.__name__ = 'test_growth_all_' + key
        test.__doc__ = '%s: 실제 작업자로 클리어 추천 육성 탐색 → 결과 칸(더 나은 편성 또는 안내)이 남는다' % content
        return test

    def test_growth_all_notice(browser, ctx):
        """탐색을 시작하지 못한 경우에도 이유가 남는다: 모의 전투 중단·자동 모의 전투 꺼짐·길방 EX 밖 단계. 끄면 사라진다."""
        page = open_page(browser, ctx, info=SYNTH)
        choose(page, '장비 탐사', '혹한의 습격 20')
        overwrite_account(page)
        page.wait_for_function("GROW.phase==='done'||GROW.phase==='error'", timeout=600000)
        text = lambda: page.evaluate("() => {const e=document.getElementById('growth-result');return e?[e.dataset.state,e.innerText.replace(/\\s+/g,' ').trim()]:null}")
        page.evaluate("() => {growthCancel();SIMQ.err='중단함';SIMQ.errStage=cur[$('stage').value].tab+'|'+cur[$('stage').value].name;run(true)}")
        stopped = text()
        page.evaluate("() => {SIMQ.err='';SIMQ.kick=false;simAuto(false);growthCancel();run(true)}")
        manual = text()
        tag = page.locator('#out .growth-on').count()
        page.evaluate("() => {$('assume-growth').checked=false;growthCancel();run(true)}")
        off = text()
        page.evaluate("() => {$('assume-growth').checked=true}")
        choose(page, '길드방어전', '3단계')
        if page.locator('button[data-go]').count():
            page.click('button[data-go]')
        page.wait_for_selector('#out > [data-party="1"]', timeout=60000)
        page.wait_for_function("document.getElementById('growth-result')", timeout=20000)
        guild = text()
        errs = list(ctx.errors)
        page.close()
        ok = (stopped and stopped[0] == 'idle' and '모의 전투가 끝나지 않아' in stopped[1]
              and manual and manual[0] == 'idle' and '모의 전투를 실행하면' in manual[1] and tag >= 1
              and off is None and guild and guild[0] == 'idle' and 'EX 단계에서만' in guild[1] and not errs)
        return ok, '중단 %s / 수동 실행 대기 %s(켜짐 표시 %d) / 끔 %s / 길방 3단계 %s / 오류 %s' % (stopped, manual, tag, off, guild, errs[:2])

    return [make(*c) for c in CASES] + [test_growth_all_notice]
