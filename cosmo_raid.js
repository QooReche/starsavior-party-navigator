// 코스모 게이트(RANKING_RAID) 점수 함수(순수 함수: 저장소·네트워크 접근 없음). 규칙은 battlesim/starsavior/cosmo_raid.py cosmo_score 와 같다
// (tests/cosmo_raid_test.py 가 경계값까지 일치 확인). 합산식은 서버 계산이라 «추정» — 데이터 score.note 참고.
(function (root) {
  "use strict";
  const RATIO_UNIT = 10000;
  function bossOf(G, boss) {
    if (boss && typeof boss === "object") return boss;
    const b = G.bosses.find(x => x.key === boss || x.name === boss);
    if (!b) throw new Error("모르는 코스모 보스: " + boss);
    return b;
  }
  function levelRow(b, level) {
    if (!level) return null;
    if (level < 1 || level > b.levels.length) throw new Error("난이도 레벨은 0~" + b.levels.length + ": " + level);
    return b.levels[level - 1];
  }
  // HUD = 기본 + 최대 피해 점수 × (깎은 HP 비율; 1/10000 내림, 정수 나눗셈 내림). 클리어면 + 남은 턴 점수 × 남은 턴 + 생존 구원자 점수 × 생존 수(추정).
  // 최종 = (합) × (1 + 난이도 점수/10000) 사사오입(정수 연산) + 달성 점수(깎은 비율 ≥ 0.5: half, 클리어: kill; 배율 미적용). step 1·2 는 난이도 없음.
  function cosmoScore(G, level, damageFrac, remainTurns, survivors, clear, boss, step) {
    const b = bossOf(G, boss || "belgras"), st = b.steps[(step || 3) - 1];
    const f = Math.max(0, Math.min(1, clear ? 1 : damageFrac));
    const q = Math.floor(f * RATIO_UNIT + 1e-9);
    let raw = st.base + Math.floor(st.maxDamage * q / RATIO_UNIT);
    if (clear) raw += st.remainTurn * Math.max(0, Math.trunc(remainTurns)) + st.survivor * Math.max(0, Math.trunc(survivors));
    const row = (step || 3) === 3 ? levelRow(b, level) : null;
    const bonus = row ? row.scoreBonus : 0;
    let total = Math.floor((raw * (RATIO_UNIT + bonus) + RATIO_UNIT / 2) / RATIO_UNIT);
    if (row) {
      if (f >= 0.5 - 1e-12) total += row.half;
      if (clear) total += row.kill;
    }
    return total;
  }
  // 챌린지 효과가 해금되는 레벨 목록(IsEffectUi) 등 화면용 도우미: 레벨 L 에서 유효한 효과 객체 목록
  function levelEffects(G, boss, level) {
    const b = bossOf(G, boss), row = levelRow(b, level);
    const byId = {};
    G.effects.forEach(e => { byId[e.id] = e; });
    return row ? row.effects.map(i => byId[i]) : [];
  }
  const api = {cosmoScore, levelEffects, levelRow, bossOf};
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.CosmoRaid = api;
})(typeof window !== "undefined" ? window : globalThis);
