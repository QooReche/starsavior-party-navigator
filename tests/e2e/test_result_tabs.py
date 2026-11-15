"""결과 탭(지금 내 구원자로 | 클리어 추천 육성)이 넓은 화면 배치와 함께 생기고 전환되는지.

python -X utf8 tests/e2e/test_result_tabs.py [--shots]
가상 계정(SYNTH)을 덜 키운 상태로 덮어쓴 뒤 실제 작업자로 탐색한다. 서버는 임시 포트를 쓰고 finally 에서 닫는다.
--shots 면 저장소 루트에 _tabs_{now,growth,best}_{1280,360}.png 를 남긴다(.gitignore).
둘째 장면: 다 키운 가상 계정(FULL)으로 쉬운 스테이지 → 탐색이 «더 나은 편성 없음»으로 끝나도 탭이 남고 육성 탭은 「이미 최선」 안내.
"""
import argparse
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TMP = ROOT / '_tmp'
TMP.mkdir(exist_ok=True)
os.environ['TEMP'] = os.environ['TMP'] = str(TMP)
from test_page import test_server, Ctx, SYNTH, FULL, open_page, choose, overwrite_account, result_tabs_audit
from playwright.sync_api import sync_playwright

NOW, GROWTH = '#out > [data-party="1"]', '#growth-result'


def tabs_audit(page, width):
    """탭 두 개가 실제로 있고, 누를 때마다 두 칸이 번갈아 보인다. 「지금」 칸 안은 넓은 화면 배치 그대로."""
    assert page.locator('#result-tabs [role="tab"]').count() == 2, '결과 탭이 없음'
    assert page.evaluate("$('result-tabs').parentElement===$('out')&&$('result-tabs').nextElementSibling===document.querySelector('%s')"
                         "&&document.querySelector('%s').nextElementSibling===$('growth-result')" % (NOW, NOW)), '탭·지금 칸·육성 칸 순서'
    titles = page.locator('#result-tabs .result-tab-title').all_inner_texts()
    assert titles == ['지금 내 구원자로', '클리어 추천 육성'], titles
    for key, shown, hidden in [('growth', GROWTH, NOW), ('now', NOW, GROWTH), ('growth', GROWTH, NOW), ('now', NOW, GROWTH)]:
        page.click('#result-tab-' + key)
        result_tabs_audit(page, key)
        assert page.locator(shown).is_visible() and not page.locator(hidden).is_visible(), key
        assert page.locator(shown).bounding_box()['height'] > 200, key
    # 「지금」 칸: 조사 결과 칸·그웬 반응·말풍선이 탭과 함께 정상
    team, summary = (page.locator(NOW + ' ' + s).bounding_box() for s in ('.result-team', '.result-summary'))
    assert page.locator(NOW + ' .result-team .gc').count() == 4
    if width >= 1200:
        assert summary['x'] + summary['width'] <= team['x'] and abs(summary['y'] - team['y']) < 2, (summary, team)
    else:
        assert summary['y'] + summary['height'] <= team['y'], (summary, team)
    reaction = page.locator(NOW + ' .result-summary .gwen-reaction')
    assert reaction.count() == 1 and reaction.locator('img').is_visible()
    bubble = reaction.locator('.gwen-bubble')
    assert bubble.is_visible() and bubble.inner_text().strip(), '그웬 말풍선'
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), '가로 넘침'


def best_audit(page, width):
    """더 나은 편성이 없어도 탭 두 개가 남고, 육성 탭은 짧은 「이미 최선」 안내 + 결과 좋음 쪽 그웬(실패 그림·실패 대사 아님)."""
    assert page.locator('#result-tabs [role="tab"]').count() == 2, '더 나은 편성 없음에서 탭이 사라짐'
    assert page.locator('#result-tabs .result-tab-title').all_inner_texts() == ['지금 내 구원자로', '클리어 추천 육성']
    assert page.inner_text('#result-tab-growth [data-tab-metric]') == '추가 육성 불필요'
    assert page.inner_text('#result-tab-now [data-tab-metric]') == '클리어 100%'
    assert page.locator('.result-recommend').is_hidden(), '없음 안내에 「추천」 표시'
    for key, shown, hidden in [('growth', GROWTH, NOW), ('now', NOW, GROWTH), ('growth', GROWTH, NOW)]:
        page.click('#result-tab-' + key)
        result_tabs_audit(page, key)
        assert page.locator(shown).is_visible() and not page.locator(hidden).is_visible(), key
    panel = page.locator(GROWTH)
    assert panel.get_attribute('data-state') == 'none' and panel.get_attribute('data-tone') == 'best'
    assert page.inner_text(GROWTH + ' [data-k="growth-best"]') == '지금 편성이 이미 최선임'
    assert '클리어율 100%임' in page.inner_text(GROWTH + ' [data-k="growth-none"]')      # 없음 판정 근거 문구 유지
    # 그웬: 작은 그림 하나 + best 대사. 실패 연출(surprised·error 대사)이 아님
    assert panel.locator('[data-gwen="error"], [data-gwen-art="surprised"], [data-gwen-say="error"]').count() == 0, '실패용 그웬'
    bubble = panel.locator('.gwen-bubble')
    assert bubble.count() == 1 and bubble.is_visible() and bubble.get_attribute('data-gwen-say') == 'best'
    line = bubble.inner_text().strip()
    assert page.evaluate('line=>Ux.GWEN_SAY.best.includes(line)&&!Ux.GWEN_SAY.error.includes(line)', line), line
    art = panel.locator('img.gwen-best-art')
    assert art.count() == 1 and art.is_visible() and art.get_attribute('data-gwen-art') == 'confident'
    box = art.bounding_box()
    assert abs(box['width'] - 72) < 1 and abs(box['height'] - 72) < 1, box
    # 한 화면 그웬 하나: 육성 탭에서 보이는 그웬 그림은 이 작은 그림뿐
    assert page.evaluate("[...document.querySelectorAll('#out img[data-gwen-art]')].filter(i=>i.checkVisibility({visibilityProperty:true})).length") == 1
    height = panel.bounding_box()['height']
    assert height <= (200 if width >= 1200 else 260), '안내 칸이 큼: %s' % height
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), '가로 넘침'
    page.click('#result-tab-now')
    result_tabs_audit(page, 'now')


def mutation(page, change, restore, width, audit=tabs_audit):
    page.evaluate(change)
    try:
        try:
            audit(page, width)
        except AssertionError:
            pass
        else:
            raise AssertionError('mutation survived: ' + change)
    finally:
        page.evaluate(restore)
    audit(page, width)


def shot(page, name, width):
    page.click('#result-tab-' + ('growth' if name == 'best' else name))
    page.evaluate("scrollTo(0,0);document.querySelectorAll('img[loading=lazy]').forEach(i=>i.loading='eager')")
    page.wait_for_timeout(1200)
    page.screenshot(path=str(ROOT / f'_tabs_{name}_{width}.png'), full_page=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--shots', action='store_true')
    args = ap.parse_args()
    with test_server() as base, sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            ctx = Ctx(base, str(TMP))
            # simauto 기본값(자동 모의 전투) = 운영 화면과 같은 흐름: 진행 화면 → 결과 → 육성 탐색
            page = open_page(browser, ctx, info=SYNTH, simauto=None)
            choose(page, '작전 (일반)', 'SECTOR 15-3')
            overwrite_account(page)
            page.wait_for_function("SIMQ.busy==null&&(GROW.phase==='done'||GROW.phase==='error')", timeout=600000)
            assert page.evaluate("GROW.phase==='done'&&growthBetter(GROW.result.kind,GROW.result.baseline,GROW.result.best)"), page.evaluate('GROW.errors')
            for width in (1280, 360):
                page.set_viewport_size({'width': width, 'height': 900})
                page.evaluate('run(true)')          # 그 너비에서 결과를 새로 그린다(탭은 다시 붙어야 함)
                page.wait_for_timeout(1500)
                tabs_audit(page, width)
                if width == 1280:
                    # 육성 칸이 숨겨지지 않거나(탭이 풀림) 탭이 지금 칸을 못 찾으면 잡혀야 한다
                    mutation(page, "document.head.insertAdjacentHTML('beforeend','<style id=tabs-mut>.ux-tab-hidden{display:block!important}</style>')",
                             "$('tabs-mut').remove()", width)
                    mutation(page, "document.querySelector('%s').dataset.party='x';growthPaint()" % NOW,
                             "document.querySelector('#out > [data-party=x]').dataset.party='1';growthPaint()", width)
                if args.shots:
                    shot(page, 'growth', width)
                    shot(page, 'now', width)
                print(f'PASS {width}px: 탭 2개·전환 4회·넓은 화면 배치·그웬 반응·말풍선', flush=True)
            assert not ctx.errors, ctx.errors
            page.close()
            # 둘째 장면: 다 키운 계정 + 쉬운 스테이지 → 실제 탐색이 «더 나은 편성 없음»(클리어율 100%)으로 끝난다
            page = open_page(browser, ctx, info=FULL, simauto=None)
            choose(page, '작전 (일반)', 'SECTOR 1-3')
            page.evaluate("$('assume-growth').checked=true;condChanged();showReco()")
            page.wait_for_function("SIMQ.busy==null&&(GROW.phase==='done'||GROW.phase==='error')", timeout=600000)
            assert page.evaluate("GROW.phase==='done'&&GROW.result.runs>0&&!GROW.result.reason&&!growthBetter(GROW.result.kind,GROW.result.baseline,GROW.result.best)"
                                 "&&GROW.result.baseline.clear>=1"), page.evaluate('({e:GROW.errors,r:GROW.result&&{b:GROW.result.baseline,best:GROW.result.best,reason:GROW.result.reason}})')
            for width in (1280, 360):
                page.set_viewport_size({'width': width, 'height': 900})
                page.evaluate('run(true)')
                page.wait_for_timeout(1500)
                best_audit(page, width)
                if width == 1280:
                    # 옛 동작(탭을 없앰·실패 그웬)으로 되돌리면 잡혀야 한다
                    mutation(page, "window.keepNone=growthNonePaint;growthNonePaint=(c,r)=>{keepNone(c,r);growthTabs.reset();};growthPaint()",
                             "growthNonePaint=keepNone;growthPaint()", width, best_audit)
                    mutation(page, "window.keepBest=Ux.gwenBest;Ux.gwenBest=()=>Ux.gwenWork('error');growthPaint()",
                             "Ux.gwenBest=keepBest;growthPaint()", width, best_audit)
                if args.shots:
                    shot(page, 'best', width)
                    page.click('#result-tab-now')
                print(f'PASS {width}px: 더 나은 편성 없음에서도 탭 2개·「이미 최선」 안내·best 대사(실패 대사 아님)·그림 72px', flush=True)
            assert not ctx.errors, ctx.errors
        finally:
            browser.close()


if __name__ == '__main__':
    main()
