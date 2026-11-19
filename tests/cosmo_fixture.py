"""코스모 지난 시즌 fixture — 시즌 1022(벨그라스·티리아·카넬리아) 모델 회귀 시험용.

data/cosmo_raid.json 은 «현재 시즌»만 담는다(11/19 부터 시즌 1023: 모굴루스·바스커빌의 괴수·괴리의 표상). 벨그라스 상태 기계와
티리아·카넬리아 EX 경로를 계속 시험하려고 1022 자료를 tests/fixtures/cosmo_raid_1022.json 으로 동결했다(커밋 2a6dd62 의
data/cosmo_raid.json 그대로, 표 빌드 26429597·26610546). 시험 파일은 import 직후 use_1022() 를 한 번 부른다(프로세스 단위).
"""
import os

FIXTURE_1022 = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures', 'cosmo_raid_1022.json')


def use_1022():
    from battlesim.starsavior import cosmo_raid
    cosmo_raid.use_data(FIXTURE_1022)
    return FIXTURE_1022
