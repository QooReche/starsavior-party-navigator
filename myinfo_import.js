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
    if (typeof DecompressionStream !== "function") throw new Error("이 브라우저는 압축 해제를 지원하지 않습니다. 파일 선택으로 올려 주세요.");
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
    if (o.format !== FORMAT) return "지원하지 않는 형식입니다(" + String(o.format) + ").";
    if (!Array.isArray(o.units) || !o.units.length) return "구원자 정보가 비어 있습니다.";
    for (const u of o.units) if (!u || !Number.isInteger(u.id)) return "구원자 항목이 올바르지 않습니다.";
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

  // 구원자별 내실 요약(후속: 시뮬 반영용). 지금은 별·공명·스킬·호감도만 정리한다.
  function perUnit(info, roster) {
    const byUid = new Map();
    for (const s of roster) if (Number.isInteger(s.uid)) byUid.set(s.uid, s.key);
    const out = {};
    for (const u of info.units) {
      const k = byUid.get(u.id);
      if (!k) continue;
      out[k] = { star: u.star, sigil: u.sigil, resonance: u.resonance, skills: u.skills, favor: u.favor, equip: (u.equip || []).length };
    }
    return out;
  }

  const api = { FORMAT, fromHash, validate, mapOwned, perUnit, b64urlToBytes };
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.MyInfoImport = api;
})(typeof window !== "undefined" ? window : globalThis);
