// Small DOM/clock used by the presentation regressions. No network or engine mocks.
const vm=require('node:vm');
function harness(){
  let now=0,serial=0;const timers=new Map(),decodes=[],observers=[];let holdDecode=false;
  const dataKey=s=>s.replace(/-([a-z])/g,(_,c)=>c.toUpperCase());
  class Element{
    constructor(tag='div'){this.tagName=tag;this.children=[];this.dataset={};this.style={};this.attrs={};this.hidden=false;this.clientWidth=600;this.offsetWidth=80;this.listeners={};
      this.classList={toggle:(s,on)=>{const a=new Set(this.className?.split(' ')||[]);if(on)a.add(s);else a.delete(s);this.className=[...a].join(' ')},contains:s=>(this.className||'').split(' ').includes(s)};}
    get nodeType(){return 1;}
    get isConnected(){return this===doc.body||this.parentElement?.isConnected||false;}
    get firstElementChild(){return this.children[0]||null;}
    append(...els){for(const el of els){el.remove();el.parentElement=this;this.children.push(el);}}
    remove(){if(this.parentElement)this.parentElement.children=this.parentElement.children.filter(c=>c!==this);this.parentElement=null;}
    replaceWith(el){const parent=this.parentElement;if(!parent)return;const at=parent.children.indexOf(this);el.remove();parent.children[at]=el;el.parentElement=parent;this.parentElement=null;}
    replaceChildren(...els){for(const c of [...this.children])c.remove();this.append(...els);}
    setAttribute(k,v){v=String(v);this.attrs[k]=v;if(k.startsWith('data-'))this.dataset[dataKey(k.slice(5))]=v;else if(k==='class')this.className=v;else if(k==='hidden')this.hidden=true;else this[k]=v;}
    getAttribute(k){return k.startsWith('data-')?this.dataset[dataKey(k.slice(5))]??null:this.attrs[k]??this[k]??null;}
    hasAttribute(k){return this.getAttribute(k)!=null;}
    removeAttribute(k){delete this.attrs[k];if(k.startsWith('data-'))delete this.dataset[dataKey(k.slice(5))];else delete this[k];}
    matches(selector){return selector.split(',').some(raw=>{const s=raw.trim();if(s==='[hidden]')return this.hidden;
      const tag=s.match(/^[\w-]+/);if(tag&&tag[0]!==this.tagName)return false;
      for(const [,name] of s.matchAll(/\.([\w-]+)/g))if(!this.classList.contains(name))return false;
      for(const [,key,val] of s.matchAll(/\[([\w-]+)(?:=["']?([^\]"']+)["']?)?\]/g)){if(!this.hasAttribute(key)||val!=null&&this.getAttribute(key)!==val)return false;}
      return !s.includes(':empty')||!this.textContent;
    });}
    querySelectorAll(s){return this.children.flatMap(c=>[...(c.matches(s)?[c]:[]),...c.querySelectorAll(s)]);}
    querySelector(s){return this.querySelectorAll(s)[0]||null;}
    closest(s){return this.matches(s)?this:this.parentElement?.closest(s)||null;}
    contains(el){return el===this||this.children.some(c=>c.contains(el));}
    addEventListener(type,fn){(this.listeners[type]??=[]).push(fn);}
    getBoundingClientRect(){return {x:0,y:0,left:0,top:0,right:this.clientWidth,bottom:160,width:this.clientWidth,height:160};}
    getClientRects(){return this.isConnected&&!this.closest('[hidden]')?[this.getBoundingClientRect()]:[];}
    animate(frames,opts){const a={currentTime:0,playState:'running',cancel(){this.playState='idle'},pause(){this.playState='paused'},play(){this.playState='running'}};return a;}
    decode(){return holdDecode?new Promise(resolve=>decodes.push({el:this,resolve})):Promise.resolve();}
    set innerHTML(html){this._html=html;this.replaceChildren();const stack=[this];
      for(const token of html.matchAll(/<\/?[a-z][^>]*>/gi)){const s=token[0];if(s.startsWith('</')){if(stack.length>1)stack.pop();continue;}
        const tag=s.match(/^<([\w-]+)/)[1],el=new Element(tag);
        for(const [,key,,quoted,bare] of s.slice(tag.length+1,-1).matchAll(/([\w-]+)(?:=(?:(["'])(.*?)\2|([^\s>]+)))?/g))el.setAttribute(key,quoted??bare??'');
        stack.at(-1).append(el);if(!['img','input','br','progress'].includes(tag))stack.push(el);
      }}
    get innerHTML(){return this._html||'';}
  }
  const doc={hidden:false,baseURI:'http://test/',documentElement:new Element('html'),body:new Element('body'),listeners:{},
    createElement:tag=>new Element(tag),getElementById:id=>doc.body.querySelectorAll('*').find(e=>e.id===id)||null,
    querySelector:s=>doc.body.querySelector(s),querySelectorAll:s=>doc.body.querySelectorAll(s),
    addEventListener(type,fn){(this.listeners[type]??=[]).push(fn);},dispatchEvent(){}};
  const addTimer=(fn,ms,repeat)=>{const id=++serial;timers.set(id,{fn,at:now+ms,ms,repeat});return id;};
  const c=vm.createContext({console,URL,WeakRef,Event,document:doc,innerWidth:1280,innerHeight:900,localStorage:{getItem:()=>null,setItem(){}},
    Math:Object.assign(Object.create(Math),{random:()=>0}),performance:{now:()=>now},Date:{now:()=>now},
    matchMedia:()=>({matches:false,addEventListener(){}}),addEventListener(){},
    setInterval:(fn,ms)=>addTimer(fn,ms,true),setTimeout:(fn,ms)=>addTimer(fn,ms,false),clearTimeout:id=>timers.delete(id),
    getComputedStyle:e=>({visibility:'visible',display:e.hidden?'none':'block',opacity:'1',overflowX:'visible',overflowY:'visible'}),
    IntersectionObserver:class{observe(){}unobserve(){}},MutationObserver:class{constructor(fn){observers.push(fn)}observe(){}},Image:class extends Element{constructor(){super('img')}},
    fetch:async()=>({ok:true,blob:async()=>new Blob()}),Blob});
  c.window=c;c.UiShared=require('../../ui_shared');c.URL=class extends URL{static createObjectURL(){return 'blob:test'}static revokeObjectURL(){}};
  const flush=async()=>{for(let i=0;i<12;i++)await Promise.resolve();};
  return {c,doc,Element,decodes,holdDecode:v=>holdDecode=v,flush,// refresh(records): MutationObserver 콜백에 넘길 기록. 생략하면 «body 안이 바뀜»(그웬 그림을 품은 노드 추가)
    refresh:records=>observers.forEach(fn=>fn(records||[{type:'childList',target:doc.body,addedNodes:[doc.body],removedNodes:[]}])),
    load:src=>vm.runInContext(src,c),add(id,parent=doc.body,tag='div'){const e=new Element(tag);e.id=id;parent.append(e);return e;},
    async tick(ms){const end=now+ms;for(let guard=0;guard<10000;guard++){const pair=[...timers].sort((a,b)=>a[1].at-b[1].at)[0];if(!pair||pair[1].at>end)break;
      const [id,t]=pair;now=t.at;if(t.repeat)t.at+=t.ms;else timers.delete(id);t.fn();await flush();}now=end;await flush();}};
}
module.exports=harness;
