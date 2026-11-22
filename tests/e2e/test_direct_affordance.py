"""Always visible editing controls, using a synthetic account and real power adapters."""
import json
from pathlib import Path
from test_direct_party import ready, enter, pick_four, geometry
from test_page import test_server
from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parents[2] / '_tmp/afford'


def visible_controls(p):
    # Neither pointer hover, selection nor retained keyboard focus may reveal controls.
    p.mouse.move(0, 0)
    p.evaluate('document.activeElement.blur()')
    assert p.locator('.direct-slot.selected').count() == 0
    metrics = p.locator('#direct-board [data-direct-action=leader], .direct-grow').evaluate_all('''xs => xs.map(e => {
      const r=e.getBoundingClientRect();let visible=true;
      for(let n=e;n;n=n.parentElement){const s=getComputedStyle(n);
        if(s.display==='none'||s.visibility!=='visible'||Number(s.opacity)===0)visible=false;}
      return {visible,w:r.width,h:r.height,label:e.getAttribute('aria-label'),action:e.dataset.directAction};
    })''')
    assert len(metrics) == 8, metrics
    for m in metrics:
        assert m['visible'] and m['w'] >= 40 and m['h'] >= 40, ('hidden or undersized control', m)
        if m['action'] == 'leader': assert '리더 지정' in m['label']
    assert p.locator('.direct-grow').evaluate_all('''xs=>xs.every(e=>{
      const r=e.getBoundingClientRect(),slot=e.closest('.direct-slot').getBoundingClientRect();
      return Math.abs(r.width-slot.width)<1;
    })'''), 'growth hit area lost full slot width'
    assert p.locator('.direct-grow>span').all_text_contents() == ['☐ 육성했다면'] * 4
    assert p.locator('.direct-drag-help').inner_text() == '끌어서 넣고 바꿈 · ☆로 리더 · ☐ 육성했다면 체크'
    # Both the crown and position label must fit without covering each other.
    assert p.locator('.direct-card-wrap').evaluate_all('''xs=>xs.every(e=>{
      const b=e.querySelector('[data-direct-action=leader]').getBoundingClientRect(),
      pos=e.querySelector('.direct-position').getBoundingClientRect(),r=e.getBoundingClientRect();
      return b.left>=r.left&&b.right<=r.right&&b.top>=r.top&&b.bottom<=r.bottom&&
        (pos.right<=b.left||pos.left>=b.right||pos.bottom<=b.top||pos.top>=b.bottom);
    })'''), 'leader/position overlap or outside card'
    return metrics


def capture(p, name, width):
    p.locator('#direct-board').scroll_into_view_if_needed()
    p.mouse.move(0, 0)
    p.screenshot(path=str(OUT / f'{name}-{width}.png'))


def contract(browser, base, width):
    p = ready(browser, base, width, touch=width == 360)
    enter(p); pick_four(p, width == 360)
    geometry(p, width)
    metrics = visible_controls(p)
    member = p.locator('.direct-member').first
    for selected in [True, False]:
        (member.tap if width == 360 else member.click)()
        assert (p.evaluate('DIRECT.selected') is not None) == selected
    visible_controls(p)
    capture(p, 'leader-before', width)
    slot = p.evaluate('DIRECT.draft.slots.findIndex(m=>m.key!==DIRECT.draft.leader)')
    leader = p.locator(f'.direct-slot[data-direct-slot="{slot}"] [data-direct-action=leader]')
    key = p.evaluate('(i)=>DIRECT.draft.slots[i].key', slot)
    (leader.tap if width == 360 else leader.click)()
    assert p.evaluate('DIRECT.draft.leader') == key
    assert leader.get_attribute('aria-pressed') == 'true' and '★' in leader.inner_text()
    if width == 360:
        # 20280da: at <=760px the 40px hit area shows only a circle + star; the leader is the gold ring, not the crown.
        ring = leader.evaluate('''e=>{const s=getComputedStyle(e,'::before'),g=document.createElement('i');
          g.style.color='var(--gold)';e.append(g);const gold=getComputedStyle(g).color;g.remove();return {border:s.borderTopColor,gold}}''')
        assert ring['border'] == ring['gold'], ring
        assert not leader.locator('.crown').is_visible() and '리더' in leader.get_attribute('aria-label')
    else:
        assert leader.locator('.crown').is_visible() and '리더' in leader.inner_text()
    assert p.locator('#direct-board .crown').count() == 1
    capture(p, 'leader-after', width)
    grow = p.locator(f'.direct-grow[data-slot="{slot}"]')
    original = p.locator(f'[data-direct-power="{slot}"]').inner_text()
    capture(p, 'growth-before', width)
    (grow.tap if width == 360 else grow.click)()
    assert grow.get_attribute('aria-pressed') == 'true'
    assert grow.locator('span').inner_text() == '☑ 육성했다면'
    power = grow.locator('.direct-power')
    assert power.inner_text().startswith(original + '→'), power.inner_text()
    assert power.evaluate('e=>getComputedStyle(e).color') != p.locator('.direct-grow[aria-pressed=false] .direct-power').first.evaluate('e=>getComputedStyle(e).color')
    capture(p, 'growth-after', width)
    # Tab order and both native keyboard activation keys survive repaint.
    leader.focus(); p.keyboard.press('Tab')
    if width == 1280:
        assert p.locator(f'.direct-slot[data-direct-slot="{slot}"] [data-direct-action=remove]').evaluate('e=>e===document.activeElement')
        p.keyboard.press('Tab')
    assert grow.evaluate('e=>e===document.activeElement')
    for keypress, pressed in [('Space', 'false'), ('Enter', 'true')]:
        p.keyboard.press(keypress)
        assert grow.get_attribute('aria-pressed') == pressed
        assert grow.evaluate('e=>e===document.activeElement')
    other = p.locator('.direct-leader-toggle[aria-pressed=false]').first
    for keypress in ['Enter', 'Space']:
        other.focus(); p.keyboard.press(keypress)
        assert p.locator('.direct-leader-toggle[aria-pressed=true]').evaluate('e=>e===document.activeElement')
    assert not p.errors, p.errors
    p.close()
    p = ready(browser, base, width, info=None, touch=width == 360)
    enter(p); pick_four(p, width == 360)
    visible_controls(p)
    for grow in p.locator('.direct-grow').all():
        assert grow.is_disabled() and grow.get_attribute('title') == '내 정보 필요'
        assert float(grow.evaluate('e=>getComputedStyle(e).opacity')) < 1
    assert not p.errors, p.errors
    p.close()
    return {'width': width, 'controls': metrics}


def mutation(browser, base, width):
    p = ready(browser, base, width, touch=width == 360)
    enter(p); pick_four(p, width == 360)
    visible_controls(p)
    # Restore the original desktop-hover/mobile-hidden CSS behavior, then remove it.
    style = p.add_style_tag(content='''
      .direct-leader-toggle{display:none!important}
      @media(hover:hover){.direct-leader-toggle{display:flex!important;opacity:0!important}
      .direct-card-wrap:hover .direct-leader-toggle,.direct-card-wrap:focus-within .direct-leader-toggle{opacity:1!important}}
    ''')
    try:
        visible_controls(p)
    except AssertionError as error:
        assert 'hidden or undersized control' in str(error), str(error)
        print(f'CAUGHT hidden CSS {width}', flush=True)
    else:
        raise AssertionError('hidden CSS mutation survived')
    finally:
        style.evaluate('e=>e.remove()')
    visible_controls(p)
    print(f'PASS restored CSS {width}', flush=True)
    p.close()


def narrow_mouse(browser, base):
    p = ready(browser, base)
    enter(p); pick_four(p)
    p.set_viewport_size({'width': 360, 'height': 1000})
    card = p.locator('.direct-slot:not(.direct-leader) .direct-card-wrap').first
    card.hover()
    leader = card.locator('[data-direct-action=leader]')
    remove = card.locator('[data-direct-action=remove]')
    a, b = leader.bounding_box(), remove.bounding_box()
    assert (a['x'] + a['width'] <= b['x'] or b['x'] + b['width'] <= a['x'] or
            a['y'] + a['height'] <= b['y'] or b['y'] + b['height'] <= a['y']), 'leader/remove overlap'
    key = leader.get_attribute('data-key')
    leader.click()
    assert p.evaluate('DIRECT.draft.leader') == key
    assert p.evaluate('DIRECT.draft.slots.filter(Boolean).length') == 4
    # Use the now-leading card: the previous locator deliberately excluded it.
    remove = p.locator('.direct-leader [data-direct-action=remove]')
    remove.click()
    assert p.evaluate('DIRECT.draft.slots.filter(Boolean).length') == 3
    assert not p.errors, p.errors
    p.close()
    print('PASS narrow mouse leader/remove', flush=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with test_server() as base, sync_playwright() as pw:
        browser = pw.chromium.launch()
        results = []
        for width in [1280, 360]:
            results.append(contract(browser, base, width))
            mutation(browser, base, width)
            print(f'PASS affordance {width}', flush=True)
        narrow_mouse(browser, base)
        browser.close()
    (OUT / 'metrics.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
