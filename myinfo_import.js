// 내 정보 불러오기(ss-myinfo-v1) — 브라우저·Node 공용. 서버로 아무것도 보내지 않는다.
// 사용: 주소 해시 '#myinfo=<base64url(gzip(JSON))>' 또는 파일 선택(JSON). 형식은 docs/myinfo_format.md.
(function (root) {
  "use strict";
  const FORMAT = "ss-myinfo-v1";

  function b64urlToBytes(s) {
    s = String(s).replace(/-/g, "+").replace(/_/g, "/");
    while (s.length % 4) s += "=";
    const bin = (typeof atob === "function") ? atob(s) : Buffer.from(s, "base64").toString("binary");
    const out = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
    return out;
  }

  async function gunzipText(bytes) {
    if (typeof DecompressionStream !== "function") throw new Error("자동 반영이 안 됩니다. 바탕화면 내정보.json을 [파일 선택]으로 불러오세요.");
    const ds = new DecompressionStream("gzip");
    const w = ds.writable.getWriter();
    w.write(bytes); w.close();
    const buf = await new Response(ds.readable).arrayBuffer();
    return new TextDecoder("utf-8").decode(buf);
  }

  // '#myinfo=...' 가 있으면 객체를, 없으면 null 을 돌려준다(형식이 틀리면 예외).
  async function fromHash(hash) {
    const m = /(?:^#|&)myinfo=([A-Za-z0-9_\-]+)/.exec(String(hash || ""));
    if (!m) return null;
    return JSON.parse(await gunzipText(b64urlToBytes(m[1])));
  }

  function validate(o) {
    if (!o || typeof o !== "object") return "파일 내용이 올바르지 않습니다.";
    if (o.format !== FORMAT) return "내정보.json을 선택해 주세요.";
    if (!Array.isArray(o.units) || !o.units.length) return "구원자 정보가 비어 있습니다.";
    const obj=v=>v!==null&&typeof v==="object"&&!Array.isArray(v);
    const num=v=>Number.isFinite(v)&&v>=0;
    const ints=(v,keys)=>keys.every(k=>!(k in v)||(Number.isInteger(v[k])&&v[k]>=0));
    const option=v=>obj(v)&&(!("stat" in v)||typeof v.stat==="string")&&(!("value" in v)||Number.isFinite(v.value));
    if (!ints(o,["star_link_level"])) return "스타링크 값이 올바르지 않습니다.";
    if ("tactics" in o && (!obj(o.tactics)||!ints(o.tactics,["facility_level","common_level"])||
        ("groups" in o.tactics&&(!obj(o.tactics.groups)||!Object.values(o.tactics.groups).every(v=>obj(v)&&ints(v,["level","attack","defense","hp"])))))) return "전술 정보가 올바르지 않습니다.";
    if ("break_skills" in o&&(!Array.isArray(o.break_skills)||!o.break_skills.every(b=>obj(b)&&Number.isInteger(b.id)&&b.id>0&&Number.isInteger(b.level)&&b.level>=1&&b.level<=10))) return "브레이크 스킬 정보가 올바르지 않습니다.";
    const ids=new Set();
    for (const u of o.units) {
      if (!obj(u)||!Number.isInteger(u.id)||u.id<=0||ids.has(u.id)||!ints(u,["star","sigil","resonance","favor"])) return "구원자 항목이 올바르지 않습니다.";
      ids.add(u.id);
      if ("skills" in u&&(!obj(u.skills)||!ints(u.skills,["basic","special","ultimate","passive"]))) return "스킬 정보가 올바르지 않습니다.";
      if ("equip" in u&&(!Array.isArray(u.equip)||!u.equip.every(e=>obj(e)&&ints(e,["item_id","level","enhance"])&&
          (!("main" in e)||option(e.main))&&(!("subs" in e)||(Array.isArray(e.subs)&&e.subs.every(option)))))) return "장비 정보가 올바르지 않습니다.";
      if ("gauntlet" in u) {
        const g=u.gauntlet;
        if (!obj(g)||!ints(g,["level"])||("journey" in g&&(!Array.isArray(g.journey)||g.journey.length!==5||!g.journey.every(num)))||
            ("potentials" in g&&(!Array.isArray(g.potentials)||!g.potentials.every(p=>Array.isArray(p)&&p.length===4&&p.every(v=>Number.isInteger(v)&&v>=0))))||
            ("blessings" in g&&(!Array.isArray(g.blessings)||!g.blessings.every(v=>Number.isInteger(v)&&v>=0)))) return "건틀렛 정보가 올바르지 않습니다.";
      }
    }
    return "";
  }

  // 로스터(uid = 게임 구원자 ID)에서 보유한 구원자의 key 목록과, 페이지가 모르는 ID 목록을 돌려준다.
  function mapOwned(info, roster) {
    const byUid = new Map();
    for (const s of roster) if (Number.isInteger(s.uid)) byUid.set(s.uid, s.key);
    const keys = [], unknown = [];
    for (const u of info.units) {
      const k = byUid.get(u.id);
      if (k) keys.push(k); else unknown.push(u.id);
    }
    return { keys, unknown };
  }

  // 보유 브레이크 스킬: 정적 표 ORBITAL_ARRAY_TEMPLET 의 m_SkillID → 화면 이름. 파일에 break_skills 가 없으면 null(직접 고르기)
  const BREAK_IDS = { 101: "특이점 관측", 102: "스타피어서", 103: "큐브 과부하", 104: "행성 정화", 105: "차원 강습" };
  function mapBreak(info) {
    if (!info || !Array.isArray(info.break_skills)) return null;
    const levels = {};
    for (const b of info.break_skills) if (BREAK_IDS[b.id]) levels[BREAK_IDS[b.id]] = b.level;
    return levels;
  }

  // 공유 링크용: JSON → gzip → base64url (fromHash 의 반대). 브라우저 CompressionStream 필요
  async function toHash(info) {
    if (typeof CompressionStream !== "function") throw new Error("링크를 만들 수 없습니다. 다른 브라우저에서 시도해 주세요.");
    const cs = new CompressionStream("gzip");
    const w = cs.writable.getWriter();
    w.write(new TextEncoder().encode(JSON.stringify(info))); w.close();
    const bytes = new Uint8Array(await new Response(cs.readable).arrayBuffer());
    let bin = "";
    for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
    const b64 = (typeof btoa === "function") ? btoa(bin) : Buffer.from(bin, "binary").toString("base64");
    return b64.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  }

  const api = { FORMAT, fromHash, toHash, validate, mapOwned, mapBreak, b64urlToBytes };
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.MyInfoImport = api;
})(typeof window !== "undefined" ? window : globalThis);
