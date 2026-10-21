"""36-36 영상 편성 + 실측 5판, 같은 seed로 강인도 규칙 전후 대조.

python -X utf8 -I tools/toughness_check.py --modes db video --runs 60
gen_quick_calib는 party_spec 변환만 사용하며 계수 생성은 실행하지 않는다.
"""
import argparse
import json
import os
import statistics
import sys
from unittest.mock import patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, 'tools')]
from battlesim import api, quick
from battlesim.mc import Battle
import gen_quick_calib as G
import ingame_check


def video_run(mode, runs):
    q, pen = quick.load(ROOT)
    order = ['wedding-epindel', 'waltz-asherah', 'haydee', 'bunny-charlotte']
    st = q['st']['op']['아가논 시가지|SECTOR 36-36']
    spec = G.party_spec(q, pen, order, None, order, 382000 / st['bp'], st)
    records = []

    class MeasuredBattle(Battle):
        def log(self, **kw):
            if kw.get('brk') == '공허순례자':
                self.boss_break_actions.append(sum(u.actions for u in self.allies + self.all_foes))
            super().log(**kw)

        def run(self):
            self.boss_break_actions = []
            super().run()
            records.append(dict(result=self.result, ally_actions=sum(u.actions for u in self.allies),
                                actions=sum(u.actions for u in self.allies + self.all_foes),
                                boss_break_actions=self.boss_break_actions))
            return self

    # 리더 없음·재점화0·순수 오토·브레이크 스킬 미장착. 영상의 수동 순서는 미입력.
    with patch.object(api, 'Battle', MeasuredBattle):
        r = api.simulate(spec, {'stage': 'op/아가논 시가지/SECTOR 36-36'},
                         dict(G.SIMOPT, n_runs=runs, seed=7,
                              rules_override=dict(G.SIMOPT['rules_override'], toughness_elem=mode)))
    mean = lambda xs: round(statistics.fmean(xs), 3) if xs else None
    first = [x['boss_break_actions'][0] for x in records if x['boss_break_actions']]
    return dict(clear=r['outcome']['clear_p'], actions=mean([x['actions'] for x in records]),
                ally_actions=mean([x['ally_actions'] for x in records]),
                boss_breaks=mean([len(x['boss_break_actions']) for x in records]),
                first_break_action=mean(first), runs_with_break=len(first), records=records)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runs', type=int, default=60)
    p.add_argument('--modes', nargs='+', default=['db', 'video'])
    p.add_argument('--output')
    args = p.parse_args()
    result = dict(runs=args.runs, seed=7, modes={})
    for mode in args.modes:
        samples = [ingame_check.run(name, args.runs, {'toughness_elem': mode}, bs=True)
                   for name in ingame_check.SAMPLES]
        video = video_run(mode, args.runs)
        result['modes'][mode] = dict(samples=samples, video=video)
        print(json.dumps(dict(mode=mode, samples=[{k: s[k] for k in
              ('stage', 'real_ratio', 'sim_ratio', 'sim_clear', 'sim_ally_actions', 'foe_breaks')} for s in samples],
              video={k: v for k, v in video.items() if k != 'records'}), ensure_ascii=False), flush=True)
    if args.output:
        with open(args.output, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
            f.write('\n')


if __name__ == '__main__':
    main()
