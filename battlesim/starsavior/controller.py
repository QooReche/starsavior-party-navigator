# -*- coding: utf-8 -*-
"""시즌 보스 컨트롤러(mc.Battle.gb) 훅 계약 — 길드 BFB(guild_bfb.Controller)·코스모(cosmo_raid.Controller)의 공통 부모.

mc.Battle 이 부르는 훅 전부의 «아무것도 안 함» 기본 구현을 둔다. 세 번째 시즌 보스는 필요한 훅만 덮어쓰면 되고 mc.py 는 안 고친다.
_put·_drop 은 하위 클래스마다 기본값(cat·src·dirty 조건)이 달라 여기 두지 않는다.
"""


class BaseController:
    pending_damage = None   # 예약 고정 피해 목록(코스모만 인스턴스 목록). None 이면 통합 큐(mc.flush_add_damage)가 건너뜀

    def __init__(self, b):
        self.b = b
        self.boss = None
        self.cfg = None

    # ---------- 웨이브·시전
    def on_wave(self):
        return

    def before_cast(self, u, sk, ctx):
        return

    def skill_start(self, u, sk, ctx):
        """스킬 시작(NSEAT_SKILL_START): 대상 확정 직후·타격 전"""
        return

    def after_cast(self, u, sk, ctx, extra):
        return

    def pre_hit(self, a, v):
        return

    def post_hit(self, a, v):
        return

    def flush_damage(self):
        """chain_timing 즉시 경로의 반응 종료 뒤 예약 피해 처리"""
        return

    def execute_se(self, owner, ln, ctx):
        """시즌 전용 SE 줄(kind=cosmo) 실행기. 없으면 미지원으로 센다."""
        self.b.unsup['코스모 전용 SE 실행기 없음'] += 1

    # ---------- 보스·보호막
    def barrier(self):
        return False

    def is_boss(self, u):
        return False

    def pick_target(self, att, sk, pool):
        """is_boss(att) 가 참인 컨트롤러만 불린다."""
        raise NotImplementedError

    def after_break_skill(self, had_barrier):
        return

    def _cur_ctx(self):
        return getattr(self.b, '_cast_ctx', None)
