"""Conservative prelink fallback: real page, synthetic exports, no claimed unlock state."""
import json
from pathlib import Path
from test_direct_party import ready, enter, pick_four
from test_page import test_server
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / '_tmp/unlock'
NOTE = '레벨 확인 불가 · 다시 불러오기 필요 · 레벨 가정 없음'


def setup(mode):
    def apply(page):
        page.add_init_script('''(() => {
          const i=JSON.parse(localStorage.getItem('pn.myinfo'));
          const mode=%s;
          for(const u of i.units){u.level=40;u.star=0;u.skills.passive=0;}
          if(mode==='zero'||mode==='locked'){i.star_link_level=0;i.star_link={level:0,source:[],slots:[]};}
          if(mode==='locked')i.star_link.unlocked=false;
          if(mode==='unknown')delete i.star_link.unlocked;
          if(mode==='legacy')delete i.star_link;
          localStorage.setItem('pn.myinfo',JSON.stringify(i));
        })()''' % json.dumps(mode))
    return apply


def scenario(browser, base, width, mode):
    page = ready(browser, base, width, touch=width == 360, setup=setup(mode))
    enter(page)
    pick_four(page, mobile=width == 360)
    frozen = page.evaluate('JSON.stringify(MI.info)')
    before = page.evaluate('DIRECT.values.values[0].power')
    assert page.locator('[data-direct-level-note]').count() == 0
    if width == 1280:
        page.screenshot(path=str(OUT / f'{mode}-{width}-before.png'), full_page=True)
    page.locator('[data-direct-action=grown][data-slot="0"]').click()
    expected = mode in ('zero', 'legacy', 'unknown', 'locked')
    assert page.locator('[data-direct-level-note]').count() == int(expected)
    if mode == 'locked':
        assert '스타링크 미개방 · 현재 돌파 기준 최대 레벨(Lv.' in page.locator('[data-direct-level-note]').inner_text()
        assert '실제로는 Lv.' in page.locator('[data-direct-level-note]').inner_text()
        assert page.evaluate('DIRECT.values.values[0].power') > before
        assert not page.evaluate('DIRECT.values.linked.length')
        assert page.evaluate('DIRECT.values.prelink[DIRECT.draft.slots[0].key].target') in (80, 160)
    elif expected:
        assert page.locator('[data-direct-level-note]').inner_text() == NOTE
        assert not page.evaluate('DIRECT.values.linked.length')
        assert page.evaluate("DIRECT.values.changes[DIRECT.draft.slots[0].key]?.levelTarget == null")
    if mode == 'legacy':
        assert page.evaluate('DIRECT.values.values[0].power') > before, 'other growth remains effective'
    assert page.evaluate('JSON.stringify(MI.info)') == frozen
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    assert page.locator('[data-direct-level-note]').evaluate_all('''xs => xs.every(x => {
      const r=x.getBoundingClientRect();return r.width>0 && r.left>=0 && r.right<=innerWidth && x.scrollWidth<=x.clientWidth+1;
    })''')
    assert not page.errors, page.errors
    page.screenshot(path=str(OUT / f'{mode}-{width}-after.png'), full_page=True)
    result = {'mode': mode, 'width': width, 'before': before,
              'after': page.evaluate('DIRECT.values.values[0].power'),
              'notes': page.locator('[data-direct-level-note]').all_text_contents()}
    page.locator('[data-direct-action=grown][data-slot="0"]').click()
    assert page.locator('[data-direct-level-note]').count() == 0
    if expected:
        fixed = page.evaluate("contents.findIndex(c=>c.key==='rush')")
        assert fixed >= 0
        page.locator('#content').select_option(str(fixed))
        page.wait_for_function("DIRECT.values?.profile?.rule==='fixed200'")
        page.locator('[data-direct-action=grown][data-slot="0"]').click()
        assert page.locator('[data-direct-level-note]').count() == 0
    page.close()
    return result


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with test_server() as base, sync_playwright() as pw:
        browser = pw.chromium.launch()
        rows = [scenario(browser, base, width, mode)
                for width in (1280, 360) for mode in ('locked', 'unknown', 'zero', 'legacy', 'opened')]
        page = ready(browser, base, 360, info=None)
        enter(page)
        assert page.locator('[data-direct-level-note]').count() == 0
        page.close()
        browser.close()
    (OUT / 'screen-results.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
    print('PASS locked/unknown/fallback/legacy/opened 1280+360, real powers, wrapping, toggle, no-info')


if __name__ == '__main__':
    main()
