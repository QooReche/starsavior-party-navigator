// Pointer presentation only: every committed drop goes through directChange.
function directDragInit(){
  const labels=['전열1','전열2','후열1','후열2'];let suppressUntil=0;
  document.addEventListener('click',e=>{if(Date.now()<suppressUntil){suppressUntil=0;e.preventDefault();e.stopImmediatePropagation();}},true);
  function eligible(e){
    const b=e.target.closest('[data-direct-action="slot"],[data-direct-action="pick"]');
    if(!b||b.disabled||e.button!==0||!e.isPrimary)return null;
    if(b.dataset.directAction==='slot'&&!DIRECT.draft.slots[+b.dataset.slot])return null;
    if(b.closest('dialog'))return null;
    return b;
  }
  document.addEventListener('pointerdown',e=>{
    if(DIRECT.drag)return;const source=eligible(e);if(!source)return;
    const slot=source.dataset.directAction==='slot'?+source.dataset.slot:null;
    const d=DIRECT.drag={source,slot,key:slot==null?source.dataset.key:DIRECT.draft.slots[slot].key,
      id:e.pointerId,touch:e.pointerType!=='mouse',x:e.clientX,y:e.clientY,startX:e.clientX,startY:e.clientY,active:false};
    if(d.touch)d.timer=setTimeout(()=>{if(DIRECT.drag===d)start(d);},350);
  });
  function target(d){
    const el=document.elementFromPoint(d.x,d.y),cell=el?.closest('[data-direct-slot]');
    if(cell&&$('direct-board').contains(cell)){
      const slot=+cell.dataset.directSlot;if(slot===d.slot)return null;
      return {el:cell,slot,text:d.slot==null?'넣기':DIRECT.draft.slots[slot]?'맞바꾸기':'자리 옮기기'};
    }
    if(d.slot!=null&&(el?.closest('#direct-drop-remove')||innerWidth>760&&el?.closest('#direct-picker-inline')))
      return {el:$('direct-drop-remove'),remove:true,text:'빼기'};
    return null;
  }
  function mark(d){
    document.querySelectorAll('.direct-drop-over').forEach(el=>{el.classList.remove('direct-drop-over');delete el.dataset.dropLabel;});
    d.target=target(d);if(d.target){d.target.el.classList.add('direct-drop-over');d.target.el.dataset.dropLabel=d.target.text;}
    d.ghost.style.transform=`translate(${d.x-32}px,${d.y-(d.touch?104:32)}px)`;
  }
  function scroll(d){
    if(DIRECT.drag!==d||!d.active)return;
    const delta=d.y<48?-12:d.y>innerHeight-48?12:0;
    if(delta){window.scrollBy(0,delta);mark(d);}
    d.frame=requestAnimationFrame(()=>scroll(d));
  }
  function start(d){
    d.active=true;clearTimeout(d.timer);d.source.classList.add('direct-drag-source');
    const ghost=document.createElement('div');ghost.className='direct-drag-ghost';ghost.setAttribute('aria-hidden','true');
    ghost.innerHTML=face(BYKEY[d.key]);document.body.append(ghost);d.ghost=ghost;
    document.body.classList.add('direct-dragging');$('direct-board').classList.add('direct-drop-ready');
    $('direct-drop-remove').hidden=d.slot==null;$('direct-selection').hidden=true;
    try{$('direct-panel').setPointerCapture(d.id);}catch{}
    if(d.touch)navigator.vibrate?.(20);mark(d);scroll(d);
  }
  document.addEventListener('pointermove',e=>{
    const d=DIRECT.drag;if(!d||d.id!==e.pointerId)return;d.x=e.clientX;d.y=e.clientY;
    const distance=Math.hypot(d.x-d.startX,d.y-d.startY);
    if(!d.active){if(d.touch){if(distance>8)finish(false);return;}if(distance<6)return;start(d);}
    e.preventDefault();mark(d);
  },{passive:false});
  // Suppress native panning only after the long press; ordinary picker scrolling stays native.
  document.addEventListener('touchmove',e=>{if(DIRECT.drag?.active)e.preventDefault();},{passive:false});
  document.addEventListener('contextmenu',e=>{if(e.target.closest('.direct-member,.direct-candidate'))e.preventDefault();});
  document.addEventListener('dragstart',e=>{if(e.target.closest('.direct-member,.direct-candidate'))e.preventDefault();});
  document.addEventListener('pointerup',e=>{if(DIRECT.drag?.id===e.pointerId)finish(true);});
  document.addEventListener('pointercancel',e=>{if(DIRECT.drag?.id===e.pointerId)finish(false);});
  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&DIRECT.drag){e.preventDefault();finish(false);}});
  window.addEventListener('blur',()=>finish(false));
  function finish(commit){
    const d=DIRECT.drag;if(!d)return;clearTimeout(d.timer);cancelAnimationFrame(d.frame);
    DIRECT.drag=null;
    try{$('direct-panel').releasePointerCapture(d.id);}catch{}
    if(!d.active){if(DIRECT.paintDeferred){DIRECT.paintDeferred=false;directPaint();}return;}
    suppressUntil=Date.now()+700;const t=commit?d.target:null;
    d.source.classList.remove('direct-drag-source');document.body.classList.remove('direct-dragging');
    $('direct-board').classList.remove('direct-drop-ready');$('direct-drop-remove').hidden=true;
    document.querySelectorAll('.direct-drop-over').forEach(el=>{el.classList.remove('direct-drop-over');delete el.dataset.dropLabel;});
    if(!t&&!matchMedia('(prefers-reduced-motion: reduce)').matches&&document.documentElement.dataset.gwenQuiet!=='true'){
      const r=d.source.getBoundingClientRect();d.ghost.animate([{transform:d.ghost.style.transform},{transform:`translate(${r.x+r.width/2-32}px,${r.y+r.height/2-32}px)`,opacity:0}],{duration:150}).finished.finally(()=>d.ghost.remove());
    }else d.ghost.remove();
    DIRECT.paintDeferred=false;DIRECT.selected=null;
    if(t){
      const action=t.remove?{type:'remove',slot:d.slot}:d.slot==null?{type:'put',key:d.key,slot:t.slot}:{type:'swap',a:d.slot,b:t.slot};
      directChange(action);
      $('direct-state').textContent=t.remove?`${BYKEY[d.key].name} 뺌`:d.slot==null?`${labels[t.slot]}에 ${BYKEY[d.key].name} 넣음`:`${labels[d.slot]}과 ${labels[t.slot]} ${t.text==='맞바꾸기'?'맞바꿈':'자리 옮김'}`;
    }else directPaint();
  }
  DIRECT.cancelDrag=()=>finish(false);
}
