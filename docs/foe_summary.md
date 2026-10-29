# 팬 데이터북 적 정보 요약

원본: https://starsavior-databook.pages.dev/#foe (data/foe.js). 생성: build_foe.py

## 콘텐츠별 규모

| 콘텐츠 | 탭 | 스테이지 | 적 인스턴스(웨이브 합) | 보스 스테이지 | 평균 aoe_ratio | 평균 defender_ratio |
|---|---|---|---|---|---|---|
| 작전 (일반) (op) | 45 | 1448 | 5771 | 1311 | 0.29 | 0.14 |
| 작전 (어려움) (oph) | 40 | 400 | 1200 | 400 | 0.33 | 0.14 |
| 일일 재화 던전 (daily) | 3 | 27 | 162 | 27 | 0.27 | 0.15 |
| 장비 탐사 (equip) | 3 | 60 | 60 | 60 | 1.00 | 0.33 |
| 큐브 팰리스 (cube) | 8 | 8 | 128 | 8 | 0.56 | 0.02 |
| 플래시 포인트 (rush) | 11 | 44 | 132 | 44 | 0.33 | 0.03 |
| 성간 회랑 (clo) | 4 | 2100 | 12929 | 1967 | 0.26 | 0.18 |
| 코스모 게이트 (cosmo) | 11 | 33 | 45 | 33 | 0.93 | 0.20 |

합계: 콘텐츠 8, 스테이지 4120, 적 인스턴스 20427, 고유 적 유닛(원본 u) 1591

## 적 속성 분포 (콘텐츠별 적 인스턴스 수)

| 콘텐츠 | sun | moon | star | order | chaos |
|---|---|---|---|---|---|
| 작전 (일반) | 1730 | 1756 | 1649 | 252 | 384 |
| 작전 (어려움) | 316 | 316 | 306 | 98 | 164 |
| 일일 재화 던전 | 54 | 54 | 54 | 0 | 0 |
| 장비 탐사 | 20 | 20 | 20 | 0 | 0 |
| 큐브 팰리스 | 0 | 0 | 0 | 64 | 64 |
| 플래시 포인트 | 48 | 48 | 36 | 0 | 0 |
| 성간 회랑 | 4006 | 3986 | 4007 | 464 | 466 |
| 코스모 게이트 | 6 | 3 | 3 | 6 | 27 |

## 스테이지 지배 속성 분포 (스테이지 수)

| 콘텐츠 | sun | moon | star | order | chaos |
|---|---|---|---|---|---|
| 작전 (일반) | 453 | 457 | 430 | 36 | 72 |
| 작전 (어려움) | 110 | 110 | 110 | 20 | 50 |
| 일일 재화 던전 | 9 | 9 | 9 | 0 | 0 |
| 장비 탐사 | 20 | 20 | 20 | 0 | 0 |
| 큐브 팰리스 | 0 | 0 | 0 | 4 | 4 |
| 플래시 포인트 | 16 | 16 | 12 | 0 | 0 |
| 성간 회랑 | 650 | 650 | 650 | 75 | 75 |
| 코스모 게이트 | 3 | 0 | 0 | 6 | 24 |

## 보스 목록 (이름·속성·역할 고유 조합 225개)

| 이름 | 속성 | 역할 | 콘텐츠 |
|---|---|---|---|
| 공허감응자 | sun | caster | 성간 회랑, 작전 (어려움) |
| 공허감응자 | moon | caster | 성간 회랑 |
| 공허감응자 | star | caster | 성간 회랑 |
| 공허개척자 | moon | caster | 성간 회랑, 작전 (일반) |
| 공허개척자 | order | caster | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 공허개척자 | sun | caster | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 공허개척자 | star | caster | 성간 회랑, 작전 (어려움) |
| 공허결집자 | chaos | ranger | 성간 회랑 |
| 공허결집자 | sun | ranger | 성간 회랑 |
| 공허결집자 | moon | ranger | 성간 회랑 |
| 공허결집자 | star | ranger | 성간 회랑 |
| 공허말살자 | moon | striker | 성간 회랑, 작전 (일반) |
| 공허말살자 | sun | striker | 성간 회랑, 작전 (어려움), 플래시 포인트 |
| 공허말살자 | star | striker | 성간 회랑, 작전 (어려움) |
| 공허망명자 | star | striker | 성간 회랑, 작전 (어려움), 플래시 포인트 |
| 공허망명자 | order | striker | 성간 회랑, 작전 (어려움) |
| 공허망명자 | sun | striker | 성간 회랑 |
| 공허망명자 | moon | striker | 성간 회랑 |
| 공허매장자 | star | assassin | 성간 회랑, 작전 (어려움) |
| 공허매장자 | chaos | assassin | 성간 회랑, 작전 (어려움) |
| 공허매장자 | moon | assassin | 성간 회랑, 플래시 포인트 |
| 공허매장자 | sun | assassin | 성간 회랑 |
| 공허맹약자 | sun | ranger | 성간 회랑, 작전 (어려움) |
| 공허맹약자 | order | ranger | 성간 회랑 |
| 공허맹약자 | moon | ranger | 성간 회랑 |
| 공허맹약자 | star | ranger | 성간 회랑 |
| 공허멸시자 | moon | ranger | 성간 회랑, 작전 (어려움), 플래시 포인트 |
| 공허멸시자 | star | ranger | 성간 회랑, 작전 (어려움) |
| 공허멸시자 | sun | ranger | 성간 회랑 |
| 공허목도자 | star | ranger | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 공허목도자 | sun | ranger | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 공허목도자 | chaos | ranger | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 공허목도자 | moon | ranger | 성간 회랑, 작전 (어려움) |
| 공허몰락자 | moon | striker | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 공허몰락자 | sun | striker | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 공허몰락자 | star | striker | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 공허몰락자 | order | striker | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 공허몰살자 | star | striker | 성간 회랑 |
| 공허몰살자 | sun | striker | 성간 회랑 |
| 공허몰살자 | moon | striker | 성간 회랑 |
| 공허변주자 | moon | ranger | 성간 회랑 |
| 공허변주자 | sun | ranger | 성간 회랑 |
| 공허변주자 | star | ranger | 성간 회랑 |
| 공허선도자 | star | caster | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 공허선도자 | moon | caster | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 공허선도자 | sun | caster | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 공허수확자 | sun | striker | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 공허수확자 | moon | striker | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 공허수확자 | star | striker | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 공허수확자 | order | striker | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 공허순례자 | chaos | caster | 성간 회랑, 작전 (일반) |
| 공허순례자 | moon | caster | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 공허순례자 | star | caster | 성간 회랑, 작전 (일반) |
| 공허순례자 | sun | caster | 성간 회랑, 작전 (어려움) |
| 공허순례자 | order | caster | 성간 회랑, 작전 (어려움) |
| 공허습격자 | sun | assassin | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 공허습격자 | star | assassin | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 공허습격자 | moon | assassin | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 공허습격자 | chaos | assassin | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 공허알현자 | chaos | ranger | 성간 회랑 |
| 공허알현자 | sun | ranger | 성간 회랑 |
| 공허알현자 | moon | ranger | 성간 회랑 |
| 공허알현자 | star | ranger | 성간 회랑 |
| 공허열반자 | star | defender | 성간 회랑, 플래시 포인트 |
| 공허열반자 | sun | defender | 성간 회랑 |
| 공허열반자 | moon | defender | 성간 회랑 |
| 공허융합자 | star | ranger | 성간 회랑, 작전 (일반) |
| 공허융합자 | sun | ranger | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 공허융합자 | order | ranger | 성간 회랑, 작전 (어려움) |
| 공허융합자 | moon | ranger | 성간 회랑, 작전 (어려움) |
| 공허융합자 | chaos | ranger | 성간 회랑, 작전 (어려움) |
| 공허응집자 | sun | ranger | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 공허응집자 | star | ranger | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 공허응집자 | moon | ranger | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 공허절멸자 | moon | defender | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 공허절멸자 | sun | defender | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 공허절멸자 | star | defender | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 공허절멸자 | chaos | defender | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 공허조율자 | chaos | ranger | 성간 회랑, 작전 (일반) |
| 공허조율자 | sun | ranger | 성간 회랑, 작전 (어려움) |
| 공허조율자 | order | ranger | 성간 회랑, 작전 (어려움) |
| 공허조율자 | moon | ranger | 성간 회랑 |
| 공허조율자 | star | ranger | 성간 회랑 |
| 공허징벌자 | sun | striker | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 공허징벌자 | moon | striker | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 공허징벌자 | order | striker | 성간 회랑, 작전 (일반) |
| 공허징벌자 | star | striker | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 공허찬탈자 | chaos | ranger | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 공허찬탈자 | moon | ranger | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 공허찬탈자 | star | ranger | 성간 회랑, 작전 (어려움) |
| 공허찬탈자 | sun | ranger | 성간 회랑, 작전 (어려움) |
| 공허초월자 | sun | defender | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 공허초월자 | moon | defender | 성간 회랑, 작전 (어려움) |
| 공허초월자 | star | defender | 성간 회랑, 작전 (어려움) |
| 공허투영자 | order | caster | 성간 회랑 |
| 공허투영자 | sun | caster | 성간 회랑 |
| 공허투영자 | moon | caster | 성간 회랑 |
| 공허투영자 | star | caster | 성간 회랑 |
| 공허학살자 | moon | striker | 성간 회랑, 작전 (어려움) |
| 공허학살자 | chaos | striker | 성간 회랑, 작전 (어려움) |
| 공허학살자 | sun | striker | 성간 회랑, 플래시 포인트 |
| 공허학살자 | star | striker | 성간 회랑 |
| 망각의 예언자 | moon | ranger | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 망각의 예언자 | star | ranger | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 망각의 예언자 | chaos | ranger | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 망각의 예언자 | sun | ranger | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 망각의 예언자 | order | ranger | 성간 회랑, 작전 (어려움) |
| 망자의 처단자 | star | assassin | 성간 회랑, 작전 (일반) |
| 망자의 처단자 | sun | assassin | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 망자의 처단자 | moon | assassin | 성간 회랑, 작전 (일반) |
| 망자의 처단자 | order | assassin | 성간 회랑, 작전 (어려움) |
| 망자의 처단자 | chaos | assassin | 성간 회랑 |
| 맹목의 전파자 | star | caster | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 맹목의 전파자 | sun | caster | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 맹목의 전파자 | order | caster | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 맹목의 전파자 | chaos | caster | 성간 회랑, 작전 (일반) |
| 맹목의 전파자 | moon | caster | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 번뇌의 숙고자 | sun | assassin | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 번뇌의 숙고자 | moon | assassin | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 번뇌의 숙고자 | star | assassin | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 번뇌의 숙고자 | chaos | assassin | 성간 회랑, 작전 (어려움) |
| 번뇌의 숙고자 | order | assassin | 성간 회랑 |
| 살육의 포식자 | sun | defender | 성간 회랑, 작전 (일반) |
| 살육의 포식자 | star | defender | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 살육의 포식자 | moon | defender | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 살육의 포식자 | order | defender | 성간 회랑, 작전 (일반) |
| 살육의 포식자 | chaos | defender | 성간 회랑, 작전 (일반) |
| 심연의 주시자 | sun | striker | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 심연의 주시자 | moon | striker | 성간 회랑, 작전 (일반) |
| 심연의 주시자 | star | striker | 성간 회랑, 작전 (일반) |
| 심연의 주시자 | chaos | striker | 성간 회랑, 작전 (어려움) |
| 심연의 주시자 | order | striker | 성간 회랑 |
| 업화의 추적자 | sun | striker | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 업화의 추적자 | moon | striker | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 업화의 추적자 | star | striker | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 업화의 추적자 | order | striker | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 업화의 추적자 | chaos | striker | 성간 회랑 |
| 왜곡의 배회자 | moon | assassin | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 왜곡의 배회자 | order | assassin | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 왜곡의 배회자 | sun | assassin | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 왜곡의 배회자 | star | assassin | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 왜곡의 배회자 | chaos | assassin | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 잔상의 감시자 | star | supporter | 성간 회랑, 작전 (일반) |
| 잔상의 감시자 | sun | supporter | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 잔상의 감시자 | moon | supporter | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 잔상의 감시자 | chaos | supporter | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 잔상의 감시자 | order | supporter | 성간 회랑, 작전 (어려움) |
| 재앙의 숭배자 | sun | caster | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 재앙의 숭배자 | moon | caster | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 재앙의 숭배자 | star | caster | 성간 회랑, 작전 (일반) |
| 재앙의 숭배자 | order | caster | 성간 회랑, 작전 (어려움) |
| 재앙의 숭배자 | chaos | caster | 성간 회랑, 작전 (어려움) |
| 저주의 경멸자 | sun | defender | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 저주의 경멸자 | moon | defender | 성간 회랑, 작전 (일반) |
| 저주의 경멸자 | star | defender | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 저주의 경멸자 | chaos | defender | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 저주의 경멸자 | order | defender | 성간 회랑 |
| 침묵의 은둔자 | moon | caster | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 침묵의 은둔자 | star | caster | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 침묵의 은둔자 | sun | caster | 성간 회랑, 작전 (어려움), 작전 (일반) |
| 침묵의 은둔자 | chaos | caster | 성간 회랑, 작전 (어려움) |
| 침묵의 은둔자 | order | caster | 성간 회랑 |
| 붐킨해머 | star | striker | 일일 재화 던전 |
| 약탈자 족장 크룬나둔 | moon | striker | 일일 재화 던전, 플래시 포인트 |
| 황금기사 아르투르 | sun | defender | 일일 재화 던전 |
| 공허감응자 | order | caster | 작전 (어려움) |
| 공허감응자 | chaos | caster | 작전 (어려움) |
| 공허결집자 | order | ranger | 작전 (어려움) |
| 공허말살자 | order | striker | 작전 (어려움), 작전 (일반) |
| 공허말살자 | chaos | striker | 작전 (어려움), 작전 (일반) |
| 공허멸시자 | chaos | ranger | 작전 (어려움) |
| 공허목도자 | order | ranger | 작전 (어려움), 작전 (일반) |
| 공허몰락자 | chaos | striker | 작전 (어려움), 작전 (일반) |
| 공허몰살자 | order | striker | 작전 (어려움) |
| 공허선도자 | order | caster | 작전 (어려움), 작전 (일반) |
| 공허선도자 | chaos | caster | 작전 (어려움), 작전 (일반) |
| 공허수확자 | chaos | striker | 작전 (어려움), 작전 (일반) |
| 공허습격자 | order | assassin | 작전 (어려움), 작전 (일반) |
| 공허알현자 | order | ranger | 작전 (어려움) |
| 공허열반자 | chaos | defender | 작전 (어려움) |
| 공허응집자 | order | ranger | 작전 (어려움), 작전 (일반) |
| 공허응집자 | chaos | ranger | 작전 (어려움), 작전 (일반) |
| 공허절멸자 | order | defender | 작전 (어려움), 작전 (일반) |
| 공허징벌자 | chaos | striker | 작전 (어려움), 작전 (일반) |
| 공허초월자 | chaos | defender | 작전 (어려움) |
| 공허투영자 | chaos | caster | 작전 (어려움) |
| 공허변주자 | order | ranger | 작전 (일반) |
| 공허찬탈자 | order | ranger | 작전 (일반) |
| 공허초월자 | order | defender | 작전 (일반) |
| 모티베이터 | sun | defender | 장비 탐사 |
| 웬디고 | moon | striker | 장비 탐사 |
| 페르세스 | star | striker | 장비 탐사 |
| 괴리의 표상 | order | striker | 코스모 게이트 |
| 데모라이기스 : 베타 | chaos | ranger | 코스모 게이트 |
| 데모라이기스 : 알파 | chaos | defender | 코스모 게이트 |
| 로자리아 르 프리데 | chaos | ranger | 코스모 게이트 |
| 불사왕 모굴루스 | chaos | striker | 코스모 게이트 |
| 오르트로스 | chaos | striker | 코스모 게이트 |
| 올베로스 | moon | defender | 코스모 게이트 |
| 집행자 길레 | chaos | caster | 코스모 게이트 |
| 카넬리아 | chaos | caster | 코스모 게이트 |
| 티리아 | sun | striker | 코스모 게이트 |
| 힐데 (타입 : 지크프리트) | chaos | defender | 코스모 게이트 |
| 라이온 | order | ranger | 큐브 팰리스 |
| 라이온 | chaos | ranger | 큐브 팰리스 |
| 복제체 나루 | order | ranger | 큐브 팰리스 |
| 복제체 다나 | order | caster | 큐브 팰리스 |
| 복제체 루그 | chaos | ranger | 큐브 팰리스 |
| 복제체 루나 | order | caster | 큐브 팰리스 |
| 복제체 리디아 | order | ranger | 큐브 팰리스 |
| 복제체 린 | order | striker | 큐브 팰리스 |
| 복제체 마르실 | chaos | assassin | 큐브 팰리스 |
| 복제체 벨 리스 | order | ranger | 큐브 팰리스 |
| 복제체 샤를 | order | striker | 큐브 팰리스 |
| 복제체 세레스 | chaos | striker | 큐브 팰리스 |
| 복제체 아세라 | chaos | striker | 큐브 팰리스 |
| 복제체 에밀리 | chaos | defender | 큐브 팰리스 |
| 복제체 카르멘 | chaos | defender | 큐브 팰리스 |
| 복제체 클라리사 | chaos | ranger | 큐브 팰리스 |
| 복제체 타냐 | order | striker | 큐브 팰리스 |
| 복제체 페이 | chaos | assassin | 큐브 팰리스 |
| 레디메이드 해피 68호 | star | striker | 플래시 포인트 |
| 레타르기아의 마술사 | sun | caster | 플래시 포인트 |
| 매니저 그레고리 | sun | striker | 플래시 포인트 |
| 카본펑크 칸 | moon | striker | 플래시 포인트 |

## 스키마 (foe_stages.json)

- 최상위: `_source`, `_notes`(필드 의미/추정 명시), `contents[]`
- contents[]: `key`(op/oph/daily/equip/cube/rush/clo/cosmo), `name`, `tabs[]`(`tab`, `section`, `stages[]`)
- stage: `name, level, recommended_power, wave_count, enemy_total, dominant_element, element_counts, role_counts, aoe_ratio, defender_ratio, has_boss, enemies[]`, 선택: `fx, fixed_player, turn_limit, season_bonus_latest, star_challenge_ref, star_pick, summons[]`
- enemy: `name, title, element, role, role_kr, attackType, boss, elite, level, stats{hp,atk,def,spd,crit,critdmg,hit,evade,abs_evade,tough}, aoe, passives[], adjust[], immune[], count_by_wave[], count` (비율 스탯은 1/10000 단위)

## 한계

- 코스모 게이트·성간 회랑 일부는 level 이 없을 수 있음. 별의 도전 EX 보정, 시즌 보너스 전체 이력, 스킬 상세(효과 문구·쿨타임)는 JSON에 넣지 않음(raw foe.js 의 s 테이블 참고).
- aoe_ratio 는 광역 스킬 보유 여부만 본 추정치. 동률 시 먼저 나온 속성이 선택됨.
- 소환되는 적(summons)은 분포·비율 계산에서 제외.
- 일부 콘텐츠(성간 회랑 등)는 스테이지 수가 많아 JSON 크기가 큼.
