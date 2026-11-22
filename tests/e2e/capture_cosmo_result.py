"""코스모 3보스 찾기 결과 화면 캡처(가짜 결과, 실제 탐색 안 함).

사용: python -X utf8 tests/e2e/capture_cosmo_result.py [출력 폴더]
1280·360 폭으로 «수사 완료!»·보스 카드 3장·4번째 칸(그웬 위 말풍선 합계)을 찍고,
배치(4칸 한 줄 / 세로 쌓기·가로 넘침 없음·낮은 클리어 경고·말풍선이 그웬 위·잘림 없음·보강 줄)를 확인해 출력함.
"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright
from test_page import test_server
from test_direct_party import ready
from test_cosmo_direct import account, OUT as ACCOUNT_OUT

OUT=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[2]/'local/cosmo-result'
FAKE_RESULT='''() => {
  const keys=R.filter(s=>MI.profiles.cosmo.results[s.key]?.power>0).slice(0,12).map(s=>s.key);
  const clears=[.88,.2,.7],scores=[12300813,12732600,12856319];
  const teams=D.cosmoRaid.bosses.map((b,i)=>({boss:b.key,keys:keys.slice(i*4,i*4+4),order:keys.slice(i*4,i*4+4),leaderKey:keys[i*4],
    level:i+3,brk:['특이점 관측',null,'스타피어서'][i],brkLv:[7,null,3][i],st:{mean:scores[i]-1e5,top:scores[i],clear:clears[i],frac:.9,n:20}}));
  Object.assign(CSR,{phase:'done',rows:[{sum:scores.reduce((a,b)=>a+b),teams}],level:3,reqLevel:3,mode:'top',fast:false,learned:false,sig:csSig(),pool:12,combos:1,keep:1,triples:1,runs:20});
  CSR.optLevel=3;CSR.optMode='top';CSR.optLearned=false;renderCosmoSearch();
}'''
AUDIT='''() => {
  const best=document.querySelector('[data-k=cs-best]'),top=best.querySelector('.cg-summary'),tabs=[...top.querySelectorAll('.cg-tab')],say=top.querySelector('.cg-say');
  const box=e=>e.getBoundingClientRect(),banner=document.querySelector('[data-gwen-slot="cosmoSearch-board"]');
  const gwen=say.querySelector('[data-gwen-slot="cosmoSearch-result"]'),img=gwen?.querySelector('img');
  return {tabs:tabs.map(t=>{const b=box(t);return [Math.round(b.x),Math.round(b.y),Math.round(b.width),Math.round(b.height)]}),
    say:(b=>[Math.round(b.x),Math.round(b.y),Math.round(b.width),Math.round(b.height)])(box(say)),
    bannerBottom:Math.round(box(banner).bottom),topY:Math.round(box(top).y),bottom:Math.round(box(top).bottom),bannerTop:Math.round(box(banner).top),
    gwenIn:!!img&&say.contains(img),img:img?(b=>[Math.round(b.x),Math.round(b.y),Math.round(b.width),Math.round(b.height)])(box(img)):null,
    bubble:say.querySelector('.cg-say-bubble').textContent,low:[...top.querySelectorAll('.cg-clear-low')].map(e=>e.textContent),
    overflow:document.documentElement.scrollWidth-innerWidth,
    bub:(b=>[Math.round(b.x),Math.round(b.y),Math.round(b.width),Math.round(b.height)])(box(say.querySelector('.cg-say-bubble'))),
    clipped:[...say.querySelectorAll('.cg-say-bubble,.cg-say-bubble *')].some(e=>e.scrollWidth>e.clientWidth+1),
    more:tabs.map(t=>[...t.querySelectorAll('[data-cg-more]')].map(e=>e.dataset.cgMore+':'+e.textContent+(e.scrollWidth>e.clientWidth+1?'(잘림)':''))),
    moreIn:tabs.every(t=>[...t.querySelectorAll('.cg-more-line')].every(e=>{const a=box(e),c=box(t);return a.bottom<=c.bottom+.5&&a.right<=c.right+.5;}))};
}'''

def main():
    OUT.mkdir(parents=True,exist_ok=True);ACCOUNT_OUT.mkdir(parents=True,exist_ok=True)
    with test_server() as base,sync_playwright() as pw:
        browser=pw.chromium.launch()
        try:
            for width in (1280,360):
                p=ready(browser,base,width,info=account(),query='?pm=reco&season=force')
                p.select_option('#content',p.evaluate('String(contents.findIndex(c=>c.key==="cosmo"))'))
                p.evaluate(FAKE_RESULT)
                p.wait_for_function('document.querySelector(\'[data-gwen-slot="cosmoSearch-result"] img\')?.naturalWidth>0')
                p.locator('[data-gwen-slot="cosmoSearch-result"]').scroll_into_view_if_needed()  # 좁은 화면은 그웬이 첫 화면 아래 — 보여야 반응이 끝남
                p.wait_for_function('document.querySelector(\'[data-gwen-slot="cosmoSearch-result"] img\')?.dataset.gwenPlaying==="false"',timeout=45000)
                p.locator('[data-gwen-slot="cosmoSearch-board"]').scroll_into_view_if_needed()
                p.evaluate('scrollBy(0,-60)')
                a=p.evaluate(AUDIT)
                print(width,a,flush=True)
                bx,by,bw,bh=a['bub'];sx,sy,sw,sh=a['say'];ix,iy,iw,ih=a['img']
                assert by+bh<=iy+8 and abs((bx+bw/2)-(ix+iw/2))<=12,('말풍선이 그웬 머리 위 가운데가 아님',a)
                assert sx<=bx and bx+bw<=sx+sw and sy<=by and iy+ih<=sy+sh+1,('말풍선·그웬이 칸 밖으로 잘림',a)
                assert not a['clipped'] and a['overflow']==0 and a['moreIn'],a
                assert a['bannerBottom']<=a['topY'],('배너와 겹침',a)
                assert all(any(x.startswith('level:난이도') for x in m) and any(x.startswith('frac:보스 깎음') for x in m) for m in a['more']),a
                assert a['more'][0][-1].startswith('brk:브레이크 특이점 관측 Lv.7') and not any(x.startswith('brk:') for x in a['more'][1]),a
                if width>=1200:assert len({t[1] for t in a['tabs']}|{a['say'][1]})==1 and all(t[3]==a['say'][3] for t in a['tabs']),('4칸 한 줄·같은 높이 아님',a)
                y0,y1=p.evaluate('''() => [document.querySelector('[data-gwen-slot="cosmoSearch-board"]').getBoundingClientRect().top+scrollY,
                  document.querySelector('[data-k=cs-best] .cg-summary').getBoundingClientRect().bottom+scrollY]''')
                p.screenshot(path=str(OUT/f'cosmo_result_after_{width}.png'),clip={'x':0,'y':max(0,y0-60),'width':width,'height':y1-y0+130},full_page=True)
                assert not p.errors,p.errors
                p.close()
        finally:browser.close()

if __name__=='__main__':main()
