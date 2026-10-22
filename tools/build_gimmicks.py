"""적 기믹 유형 발견(스킬/패시브 원문 통독 -> 유형 체계) + 구원자 성향(다중 타수 등) 태깅 + 유형x성향 규칙.

실행: python -X utf8 -I build_gimmicks.py [--raw foe_raw.json] [--stages foe_stages.json] [--savior main.json]
                                           [--reco savior_reco.json] [--out 출력폴더]
읽기 전용 입력, 쓰기는 --out 만. 규칙은 상단 딕셔너리(TYPES / ENEMY_RULES / SAVIOR_TAGS / COUNTER_RULES)에 있다.

유형 체계는 키워드 목록에서 나온 것이 아니라 적 스킬 원문 513종(정규화 후)을 직접 읽고 묶은 것이다(gimmick_review.md 참고).
아래 정규식은 그 통독 결과를 기계적으로 옮긴 것이며, 매칭 안 된 문구는 residual 로 따로 남겨 재검토한다.
"""
import argparse, collections as C, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
import sys
sys.path.insert(0, str(HERE))
from battlesim.fileio import atomic_json, read_json
ROOT = os.path.normpath(os.path.join(HERE, '..'))  # 저장소 루트
D = dict(
    raw=os.path.join(ROOT, 'tools', 'raw', 'foe_raw.json'),            # build_foe.py 가 만든 데이터북 foe.js 원본 파싱
    stages=os.path.join(ROOT, 'data', 'foe_stages.json'),
    savior=os.path.join(ROOT, 'rawdata', 'databook_main.json'),                    # 데이터북 main.js 를 JSON 으로 푼 파일(저장소에 없음)
    reco=os.path.join(ROOT, 'data', 'savior_reco.json'),
    out=os.path.join(ROOT, 'tools', 'raw', 'gimmicks'),                 # 큰 중간 산출물(저장소 제외), tools/pack_gimmicks.py 가 압축 데이터를 data/ 로 만든다
    syn=os.path.join(ROOT, 'data', 'synergy_pairs.json'),
)

# ------------------------------------------------------------------ 유형 카탈로그 (통독 후 제안)
# name/desc: 설명. good/bad: 구원자 태그(아래 SAVIOR_TAGS). 'w' 가중치. note: 판정 한계
TYPES = {
 'HIT_COUNT_TRIGGER': dict(name='피격 횟수 누적 발동', desc='N회 피격/한 턴 N번 피격 시 강한 스킬 발동(카운트다운형). 피격이 타수 단위인지 스킬 단위인지는 원문만으로 불명.',
     prefer=['SINGLE_BIG', 'BREAK'], avoid=['MULTIHIT'], w=2, impact_conf='추정'),
 'HIT_STACK_OFFENSE': dict(name='피격 시 공격 스택', desc='피격 후 공격력/속도/치명/피해량이 N%씩 최대 M회 중첩(많이 때릴수록 적이 강해짐).',
     prefer=['BURST', 'SINGLE_BIG', 'GAUGE_DOWN', 'CC_APPLY'], avoid=['MULTIHIT'], w=1, impact_conf='추정'),
 'HIT_STACK_DEFENSE': dict(name='피격 시 방어 스택', desc='피격 후 방어력/피해 감소율이 중첩(오래·많이 때릴수록 단단해짐).',
     prefer=['BURST', 'DEF_PEN', 'SINGLE_BIG'], avoid=['MULTIHIT'], w=1, impact_conf='추정'),
 'HIT_GAUGE_GAIN': dict(name='피격 시 행동게이지 증가', desc='피격(조건부 포함)마다 자신의 행동 게이지 증가 -> 연타일수록 적이 빨리 행동.',
     prefer=['GAUGE_DOWN', 'CC_APPLY', 'SINGLE_BIG'], avoid=['MULTIHIT'], w=1, impact_conf='추정'),
 'HIT_RETALIATION': dict(name='피격 반응 반격/연쇄피해/스킬 발동', desc='피격 후 타격자에게 연쇄 피해·디버프·스킬 발동, 반격 버프.',
     prefer=['SHIELD', 'HEAL', 'SINGLE_BIG'], avoid=['MULTIHIT'], w=1, impact_conf='추정'),
 'HIT_TOUGHNESS_RECOVER': dict(name='피격 시 강인도 회복', desc='피격마다 강인도 회복 -> 브레이크가 지연.',
     prefer=['BREAK', 'SINGLE_BIG'], avoid=['MULTIHIT'], w=1, impact_conf='추정'),
 'TURN_HIT_REDUCTION': dict(name='첫 피격 후 이번 턴 피해 감소', desc='피격 후 이번 턴 받는 피해 50% 감소 -> 한 턴 안 두 번째 이후 타격이 반감.',
     prefer=['SINGLE_BIG'], avoid=['MULTIHIT'], w=3, impact_conf='확인'),
 'SLOT_DAMAGE_REDUCTION': dict(name='기본기 피해 감소', desc='기본기로 받는 피해 50% 감소 등 스킬 슬롯별 피해 감소.',
     prefer=['BURST'], avoid=['BASIC_DEPENDENT'], w=1, impact_conf='확인'),
 'REACTIVE_TO_ATTACK_KIND': dict(name='공격 종류(단일/전체/스킬 슬롯)별 반응', desc='단일 공격/전체 공격/궁극기 피격 시 상태 전환·쿨 감소·게이지 변동. 공격 종류에 따라 이득/손해가 갈린다.',
     prefer=[], avoid=[], w=1, impact_conf='확인', param='attack_kind'),
 'SHIELD_GEN': dict(name='보호막 생성(깨야 함)', desc='스스로 보호막/방패를 만들고 유지. 보호막 상태에서 강화·반응·방어 스택이 붙는 경우가 많다.',
     prefer=['BREAK', 'DEF_PEN', 'DISPEL'], avoid=[], w=1, impact_conf='추정'),
 'SHIELD_GATED': dict(name='보호막 상태일 때만 강화/발동', desc='보호막 보유 시 피해 증가·반격·스킬 발동·공격력 스택. 깨뜨리면 약해진다.',
     prefer=['BREAK', 'DEF_PEN', 'BURST'], avoid=[], w=2, impact_conf='확인'),
 'BUFF_STATE_PUNISH': dict(name='강화/보호막 상태 아군 가중 피해', desc='대상이 강화 효과(또는 보호막) 상태일 때 피해 증가. 또는 강화 효과 없는 대상에게 피해 증가(양방향).',
     prefer=['SELF_SUSTAIN'], avoid=['BUFFER_DEP'], w=1, impact_conf='확인'),
 'TOUGHNESS_IMMUNE_WINDOW': dict(name='강인도 피해 무효 구간', desc='특정 스킬 후 강인도 피해 무효(아군 전체 포함). 이 구간에는 브레이크 불가.',
     prefer=['BURST'], avoid=['BREAK_ONLY'], w=2, impact_conf='확인'),
 'TOUGHNESS_BREAK_REACTIVE': dict(name='강인도 격파 연동', desc='자신/부하 격파 시 효과 해제·전이·스택(격파가 이득인 경우), 격파 상태에서 오히려 강해지는 경우, 아군 격파 후 적 스택.',
     prefer=['BREAK'], avoid=[], w=2, impact_conf='확인'),
 'TOUGHNESS_PRESSURE': dict(name='적의 강인도 피해 증가', desc='적 스킬이 강인도 피해 +1 -> 아군 브레이크 취약.',
     prefer=['SHIELD', 'TAUNT'], avoid=[], w=1, impact_conf='확인'),
 'ENRAGE_STACK': dict(name='시간 경과 폭주(턴/스킬 사용 스택)', desc='스킬 사용 후 피해량 5%씩 중첩, 턴 시작/종료 시 능력치 중첩. 장기전 불리 -> 빠른 처치.',
     prefer=['BURST', 'GAUGE_ALLY', 'EXTRA_TURN', 'CD_REDUCE'], avoid=[], w=1, impact_conf='확인'),
 'SUMMON': dict(name='소환/분신', desc='하수인/인형 소환. 하수인 격파와 본체 효과가 연동되는 경우 있음.',
     prefer=['AOE'], avoid=[], w=2, impact_conf='확인'),
 'LINKED_MINIONS': dict(name='부하 연동(보호 대상/처치 순서)', desc='부하 생존/격파가 보스 효과를 좌우([족장을 지켜라!], 영웅의 혼, 퇴적/침식).',
     prefer=['BREAK', 'AOE'], avoid=[], w=2, impact_conf='확인'),
 'BUFF_STRIP': dict(name='아군 강화 효과 해제/강화 불가', desc='아군 강화 효과를 해제하거나 강화 불가를 건다. 버프 의존 편성이 무너진다.',
     prefer=['SELF_SUSTAIN'], avoid=['BUFFER_DEP'], w=2, impact_conf='확인'),
 'DEBUFF_SCALING': dict(name='아군 약화 효과 개수 비례 피해', desc='아군이 가진 약화 효과 수/상태에 따라 피해 증가.',
     prefer=['CLEANSE', 'RES_IMMUNE'], avoid=[], w=2, impact_conf='확인'),
 'SELF_CLEANSE': dict(name='자신 약화 효과 정기 해제', desc='턴 시작/종료 시 약화 효과를 모두 해제하거나 스킬 사용 시 해제. 디버프 누적 전략 무력화.',
     prefer=['BURST'], avoid=['DEBUFFER'], w=1, impact_conf='확인'),
 'DEBUFF_GATED_POWER': dict(name='자신 약화 상태에 좌우', desc='자신의 약화 효과 개수가 적을수록 강해지거나(또는 많을수록 약해짐). 디버프를 얹어 두는 편이 유리.',
     prefer=['DEBUFFER'], avoid=[], w=2, impact_conf='확인'),
 'ELEMENT_RESIST': dict(name='속성 한정 피해 감소', desc='특정 속성이 아닌 대상에게 받는 피해 30~50% 감소. 맞는 속성만 유효.',
     prefer=[], avoid=[], w=3, impact_conf='확인', param='element'),
 'ELEMENT_BIAS_ATTACK': dict(name='특정 속성에 가중(적 공격/반응)', desc='특정 속성 아군에게 주는 피해 증가 등.',
     prefer=[], avoid=[], w=1, impact_conf='확인', param='element'),
 'CONDITIONAL_DAMAGE_REDUCTION': dict(name='상태 조건부 피해 감소', desc='낙인/약화 효과 N개 이상/고정 상태에서 받는 피해 감소.',
     prefer=['DEF_PEN', 'BURST'], avoid=[], w=1, impact_conf='확인'),
 'TARGET_PRIORITY': dict(name='우선 공격 대상 지정', desc='전열·후열 낙인·타격자·최고 공격력·최저 생명력·행동 게이지 최고·표적/맹약 대상을 우선 공격.',
     prefer=['SHIELD', 'HEAL', 'TAUNT'], avoid=[], w=1, impact_conf='확인', param='target'),
 'GAUGE_DENIAL': dict(name='아군 행동게이지/쿨타임 방해', desc='아군 행동 게이지 감소·초기화, 쿨타임 증가.',
     prefer=['RES_IMMUNE', 'CLEANSE', 'GAUGE_ALLY'], avoid=[], w=1, impact_conf='확인'),
 'CC_APPLY': dict(name='행동 제약 디버프(기절/수면/빙결/속박/침묵/도발)', desc='행동 불가·스킬 제한 디버프.',
     prefer=['RES_IMMUNE', 'CLEANSE'], avoid=[], w=1, impact_conf='확인'),
 'RESIST_IGNORE': dict(name='효과 저항/면역 무시 디버프', desc='효과 저항·면역·명중과 관계없이 걸리는 효과(낙인, 맹약, 표적, 불협화음 등). 효과 저항 스탯으론 못 막음.',
     prefer=['CLEANSE'], avoid=[], w=2, impact_conf='확인'),
 'HEAL_BLOCK': dict(name='회복 불가', desc='아군에게 회복 불가 부여.',
     prefer=['SHIELD'], avoid=['HEAL'], w=2, impact_conf='확인'),
 'UNDYING': dict(name='불사/부활성 회복', desc='치명 피해 시 일부 회복 후 불사 부여.',
     prefer=['BURST'], avoid=[], w=1, impact_conf='확인'),
 'SKILL_NULLIFY': dict(name='스킬 피해 무효 N회', desc='[스킬 피해 무효] 1회 부여. 첫 공격이 흡수될 가능성(무효가 타수 단위인지 스킬 단위인지 불명).',
     prefer=['AOE'], avoid=[], w=1, impact_conf='추정'),
 'INVULN_GUARD': dict(name='면역/수호 상태', desc='[면역]/[수호(해제불가)] 부여. 정확한 의미는 용어 해설 확인 필요.',
     prefer=['DISPEL'], avoid=[], w=1, impact_conf='추정'),
 'STEALTH': dict(name='은신', desc='[은신] 부여. 타겟 불가라면 단일기가 헛나갈 수 있음(원문엔 효과 정의 없음).',
     prefer=['AOE'], avoid=[], w=1, impact_conf='추정'),
 'ALLY_DEATH_TRIGGER': dict(name='아군 사망 연동', desc='아군(적 측 개체) 사망 시 스택/쿨 초기화/해제 등.',
     prefer=['AOE'], avoid=[], w=1, impact_conf='확인'),
 'HP_THRESHOLD_PHASE': dict(name='생명력 구간 전환(전투 중 1회 등)', desc='HP 50% 이하 등에서 쿨 초기화·보호막·반격·스킬 발동.',
     prefer=['BURST'], avoid=[], w=1, impact_conf='확인'),
 'SELF_DESTRUCT': dict(name='자폭/사망 폭발', desc='시한 폭탄형 사망 폭발, 격파 시 공격력 0 후 사망.',
     prefer=['AOE', 'BURST'], avoid=[], w=2, impact_conf='확인'),
 'PCT_HP_DAMAGE': dict(name='최대 생명력 비례 피해', desc='대상 최대 생명력 비례 연쇄 피해(방어력 무관). 연쇄 횟수가 늘어나는 단계 있음.',
     prefer=['SHIELD', 'HEAL'], avoid=[], w=2, impact_conf='확인'),
 'OPENER_BURST': dict(name='개전 즉시 강공(선공/쿨 최대 감소)', desc='전투 시작 시 행동 게이지 100% 증가/궁극기 쿨 최대 감소.',
     prefer=['SHIELD', 'HEAL', 'GAUGE_ALLY'], avoid=[], w=1, impact_conf='확인'),
 'EXTRA_ACTION': dict(name='추가 턴/연속 행동', desc='추가 턴, 타격 후 기본기 추가 발동.',
     prefer=['CC_APPLY', 'GAUGE_DOWN'], avoid=[], w=1, impact_conf='확인'),
 'NONATTACK_PUNISH': dict(name='비공격 스킬 사용 반응', desc='아군이 공격이 아닌 스킬을 쓰면 쿨 감소·게이지/버프 획득.',
     prefer=[], avoid=['SUPPORT_HEAVY'], w=1, impact_conf='확인'),
 'STANCE_CYCLE': dict(name='상태 교대 사이클', desc='낮/밤, 운룡/풍호처럼 스킬 사용 후 상태가 번갈아 바뀌어 특정 턴에만 취약/강력.',
     prefer=['BURST'], avoid=[], w=1, impact_conf='확인'),
 'SELF_BUFF_DEPENDENT': dict(name='자신의 강화 효과에 비례해 강해짐', desc='자신 강화 효과 개수/상태에 따라 피해량 증가. 강화 해제(디스펠)로 약화 가능.',
     prefer=['DISPEL'], avoid=[], w=2, impact_conf='확인'),
 'COOLDOWN_DISRUPT': dict(name='아군 쿨타임 증가', desc='아군 모든 스킬 쿨타임 증가.',
     prefer=['RES_IMMUNE', 'CD_REDUCE'], avoid=[], w=1, impact_conf='확인'),
}

# ------------------------------------------------------------------ 적 문구 -> 유형 규칙
# (code, regex, severity(int|callable(match)->int), subtype, only_slot('패시브'|None))

NOT_HIT = r'(?<!아군이 )(?<!자신을 제외한 아군이 )'
ENEMY_RULES = [
 ('HIT_COUNT_TRIGGER', r'(?:(단일|전체) 공격에 )?(\d+)회 피격', lambda m: 3 if int(m.group(2)) <= 3 else 2 if int(m.group(2)) <= 5 else 1, lambda m: m.group(1) or '미지정'),
 ('HIT_COUNT_TRIGGER', r'한 턴에 (\d+)번 (?:이상 )?피격', lambda m: 3, lambda m: '턴당'),
 ('HIT_STACK_OFFENSE', r'피격 (?:시|후)[^.]*?(?:공격력|속도|치명타 확률|(?<!받는 )(?<!감소)피해량)[^.]*?\d+%씩[^.]*?(?:최대 \d+회|$)?', lambda m: 2, None),
 ('HIT_STACK_DEFENSE', r'피격 (?:시|후)[^.]*?(?:(?:방어력|효과 저항)[^.]*?\d+%씩|피해량 감소율이 \d+%씩)', lambda m: 1, None),
 ('HIT_GAUGE_GAIN', r'(?:피격 (?:시|후))[^.]*?자신의 행동 게이지를 \d+% 증가', lambda m: 1 if re.search('이면|상태|경우', m.group(0)) else 2, None),
 ('HIT_RETALIATION', r'피격 (?:시|후)[^.]*?(?:타격자에게|연쇄 피해|\[[^\]]+\]을 발동|\[[^\]]+\]를 발동)', lambda m: 2, None),
 ('HIT_RETALIATION', r'\[(?:강화 )?반격(?: 증가)?\]', lambda m: 2, lambda m: '반격 버프'),
 ('HIT_TOUGHNESS_RECOVER', r'피격 (?:시|후)[^.]*?강인도를 \d+ 회복', lambda m: 2, None),
 ('TURN_HIT_REDUCTION', r'피격 후 이번 턴에 받는 피해량이 \d+% 감소', lambda m: 3, None),
 ('SLOT_DAMAGE_REDUCTION', r'기본기로 받는 피해량이 \d+% 감소', lambda m: 2, None),
 ('REACTIVE_TO_ATTACK_KIND', r'(단일 공격|전체 공격|기본기|특수기|궁극기)(?: 혹은 (?:기본기|특수기|궁극기))?(?:에)? ?피격', lambda m: 2, lambda m: m.group(1)),
 ('SHIELD_GEN', r'(?:자신|아군 전체|자신을 제외한 아군 전체)에게 [^.]*?\[(?:보호막|공허 방패|저항 장막)[^\]]*\]|보호막은 자신의 최대 생명력', lambda m: 2, None),
 ('SHIELD_GATED', r'(?:자신이|대상이|적이)\s*\[?(?:보호막|공허 방패|저항 장막)[^\]]*\]?\s*(?:\(해제불가\)\])?\s*상태(?:이면|라면)|피격 후 자신이 \[보호막\] 상태|피격 시 자신이 보호막 상태', lambda m: 2, None),
 ('BUFF_STATE_PUNISH', r'(?:대상이|적이) 강화 효과 상태이면[^.]*?피해량이 \d+% 증가|대상이 \[보호막\] 상태이면 피해량이 추가로|강화 효과(?:가| 상태가) 아니라면[^.]*?피해량이 \d+% 증가|강화 효과가 없|적이 강화 효과 상태가 아니라면|보유한 강화 효과가 1개 이하인 적', lambda m: 2, None),
 ('TOUGHNESS_IMMUNE_WINDOW', r'강인도 피해 무효', lambda m: 3 if '아군 전체' in m.string else 2, None),
 ('TOUGHNESS_BREAK_REACTIVE', r'(?:자신의|적의) 강인도 격파|강인도 격파 (?:상태|시|후)|강인도 격파 후', lambda m: 2, None),
 ('TOUGHNESS_PRESSURE', r'강인도 피해(?:가| ?)\s*\d+ 증가', lambda m: 1, None),
 ('ENRAGE_STACK', r'스킬 사용 후 (?:자신의 )?(?:스킬 )?피해량이 \d+%씩 증가', lambda m: 2, '피해량 5%/스킬'),
 ('ENRAGE_STACK', r'(?:턴 (?:시작|종료)(?: 시| 후)?|타격 (?:시|후)|스킬 사용 후|사용 후)(?![^.]*피격)[^.]*?(?:공격력|속도|치명타 확률|효과 적중|방어력)[^.]*?\d+%씩[^.]*?(?:\.\s*)?(?:최대 \d+회|중첩)', lambda m: 1, '능력치 중첩'),
 ('SUMMON', r'소환(?:합니다|됩니다)|마리 소환', lambda m: 2, None),
 ('LINKED_MINIONS', r'\[족장을 지켜라!|\[영웅의 혼|\[퇴적\(해제불가\)\]|\[침식\(해제불가\)\]', lambda m: 2, None),
 ('BUFF_STRIP', r'강화 효과를 (?:모두 |\d+개)\s*해제|강화 효과를 1개씩 2번 해제|\[강화 불가\]를|강화 효과를 해제', lambda m: 2 if re.search('모두|강화 불가', m.group(0)) else 1, None),
 ('DEBUFF_SCALING', r'약화 효과(?: 개수)?(?:가)?[^.]*?(?:당|하나 당)[^.]*?(?:피해량|연쇄)|약화 효과 상태이면[^.]*?(?:피해량|연쇄 피해)[^.]*?증가|적 전체가 보유(?:한|하고 있는) 약화 효과', lambda m: 2, None),
 ('SELF_CLEANSE', r'(?:턴 (?:시작|종료)(?: 시| 후)?)[^.]*?약화 효과를 모두 해제', lambda m: 2, '턴 정기'),
 ('SELF_CLEANSE', r'(?:자신의|자신이 보유한) 약화 효과를 (?:모두 |\d+개)\s*해제', lambda m: 1, '스킬 부수'),
 ('DEBUFF_SCALING', r'(?:적이|대상이) (?:약화 효과|\[(?:출혈|공허 포자)\]) 상태(?:이면|인)|\[공허 포자\] 상태인 적', lambda m: 1, '상태의존'),
 ('STANCE_CYCLE', r'해당 효과를 해제하고 자신에게 \[[^\]]+\](?:를|을) 발생', lambda m: 1, None),
 ('BUFF_STATE_PUNISH', r'타격자가 강화 효과(?: 상태)?(?:이면|가 아닌)', lambda m: 1, '타격자 상태'),
 ('SELF_BUFF_DEPENDENT', r'자신이 (?:보유한 )?강화 효과(?: 상태| 개수)|자신이 보유한 강화 효과|아군 전체가 보유한 \[?[^.]*?개수 당|\[끝없는 장막\]의 개수|\[오버히트\(해제불가\)\]가 \d+중첩', lambda m: 2, None),
 ('DEBUFF_GATED_POWER', r'자신(?:의|이 보유한)? ?약화 효과(?:가| 개수)[^.]*?(?:이하|미만|개수당|아니)|자신이 약화 효과 상태(?:가 아니|이)', lambda m: 2, None),
 ('ELEMENT_RESIST', r'(태양|달|별|질서|혼돈) 속성이 아닌 대상에게 받는 피해량이 (\d+)% 감소', lambda m: 3 if int(m.group(2)) >= 50 else 2, lambda m: m.group(1)),
 ('ELEMENT_BIAS_ATTACK', r'(태양|달|별|질서|혼돈) 속성 대상(?:에게|에게 피격)', lambda m: 1, lambda m: m.group(1)),
 ('CONDITIONAL_DAMAGE_REDUCTION', r'(?:받는 피해량이 \d+% 감소합니다|받는 피해량을 \d+% 감소)', lambda m: 1, None),
 ('TARGET_PRIORITY', r'전열을 우선 공격|전열의 디펜더를 우선|낙인은 후열을 우선|타격자(?:를|에게)? ?(?:우선적으로|우선)|타격자를 우선적으로|공격력이 가장 높은 적(?:을| 대상)?(?:을)? ?우선|현재 생명력 비율이 가장 낮은 적을 우선|행동 게이지가 가장 높은 적을 우선|\[표적\(해제불가\)\] 상태인 적을 우선|\[피의 맹약\(해제불가\)\]인 대상을 우선', lambda m: 1, lambda m: m.group(0)[:10]),
 ('GAUGE_DENIAL', r'(?:적(?: 전체)?의 )?행동 게이지(?:를|가)? ?(?:\d+% 감소|초기화)|모든 스킬 쿨타임을 1턴 증가', lambda m: 2 if re.search('초기화|100%', m.group(0)) else 1, None),
 ('CC_APPLY', r'\[(기절|수면|빙결|속박|침묵|도발)\]', lambda m: 2 if m.group(1) in ('기절', '수면', '빙결', '속박') else 1, lambda m: m.group(1)),
 ('RESIST_IGNORE', r'효과 저항(?: 및 면역 효과)?[^.]*?(?:무시|관계없이)|효과 저항 및 면역 효과, 명중과 관계없이|명중, 효과 저항, 면역 효과와 관계없이', lambda m: 2, None),
 ('HEAL_BLOCK', r'\[회복 불가\]', lambda m: 2, None),
 ('UNDYING', r'사망에 이르는 피해|\[불사\]', lambda m: 2, None),
 ('SKILL_NULLIFY', r'\[스킬 피해 무효\]', lambda m: 2, None),
 ('INVULN_GUARD', r'\[면역\]을 발생|\[수호\(해제불가\)\]', lambda m: 2, None),
 ('STEALTH', r'\[은신\]', lambda m: 2, None),
 ('ALLY_DEATH_TRIGGER', r'아군 사망 시|자신이 사망 시', lambda m: 2, None),
 ('HP_THRESHOLD_PHASE', r'자신의 생명력이 (\d+)% 이하이면[^.]*', lambda m: 2 if '전투 중 1회만' in m.string else 1, None),
 ('SELF_DESTRUCT', r'큰 피해를 발생시킨 후 사망|스킬 사용 후 사망', lambda m: 3, None),
 ('PCT_HP_DAMAGE', r'최대 생명력에 비례한 연쇄 피해', lambda m: 2, None),
 ('OPENER_BURST', r'전투 시작 시[^.]*?(?:쿨타임이 최대로 감소|행동 게이지(?:가|를) 100% 증가)', lambda m: 1, None),
 ('EXTRA_ACTION', r'추가 턴이 발생|무작위 적에게 기본기를 발동', lambda m: 2, None),
 ('NONATTACK_PUNISH', r'적이 공격이 아닌 스킬 사용 시', lambda m: 2, None),
 ('COOLDOWN_DISRUPT', r'모든 스킬 쿨타임을 1턴 증가', lambda m: 2, None),
]

# 유형 체계에서 의도적으로 제외(거의 모든 적이 가지는 노이즈)
NOISE_NOTE = '출혈/연소/방어력·공격력·속도·명중률 감소 등 일반 약화 부여, 단순 공격력 증가 자가 버프는 유형에서 제외'

# ------------------------------------------------------------------ 구원자 태그 규칙
# 각 태그: 대상 텍스트(skill 단위 d1+dx+ef) 정규식. act=='공격' 인 스킬만 보는 것은 ATTACK_ONLY
SAVIOR_TAGS = {
 'CC_APPLY':   r'적[^.]*?\[(?:기절|수면|빙결|속박|침묵|도발)\]|\[(?:기절|수면|빙결|속박)\]',
 'GAUGE_DOWN': r'적(?: 전체)?의 행동 게이지를? [^.]*?감소|적의 행동 게이지',
 'GAUGE_ALLY': r'(?:자신|아군)[^.]*?행동 게이지(?:를|가)? ?\[?\d+%?\]?\s*(?:p )?증가|행동 게이지 \d+%p 증가',
 'EXTRA_TURN': r'추가 턴',
 'CD_REDUCE':  r'쿨타임(?:을| )[^.]*?감소|쿨타임이 1턴 감소|쿨타임 초기화',
 'DISPEL':     r'강화 효과(?:를)? ?(?:모두|\d+개)? ?해제|적[^.]*?강화 효과[^.]*?해제',
 'DEBUFFER':   r'적(?: 전체)?에게[^.]*?(?:방어력 감소|공격력 감소|속도 감소|효과 저항 감소|강화 불가|출혈|연소|감전|중독)',
 'CLEANSE':    r'(?:자신|아군)[^.]*?약화 효과[^.]*?해제',
 'RES_IMMUNE': r'효과 저항 증가|\[면역\]|면역',
 'SHIELD':     r'\[보호막\]|보호막(?:을|이)? ?(?:발생|부여)|보호막은',
 'HEAL':       r'(?:생명력을|피해량의)[^.]*?회복|회복시|지속 회복|부활',
 'TAUNT':      r'\[도발\]|도발(?:을|이)? ?발생|공격 대상을 .*?유도',
 'DEF_PEN':    r'방어력(?:을)? ?\d+%.*?관통|방어 관통|관통합니다',
 'BREAK':      r'강인도 피해가 \d+ 증가|강인도 피해',
 'BUFFER_DEP': r'강화 효과 개수 당|보유한 강화 효과|강화 효과 상태|강화 효과가 \d+개',
 'SELF_SUSTAIN': r'자신[^.]*?(?:보호막|회복|피해 감소)',
}

# ------------------------------------------------------------------ 기믹 유형 -> 역할 슬롯/스킬 구조/조합 규칙
# slots: (슬롯명, 충족 태그(any)) 목록. 서로 다른 구원자가 슬롯을 채워야 보너스. good/bad: 선호/부적합 스킬 구조(서술).
# syn: 슬롯 충족 구원자 사이 연계(synergy_pairs.json 유형 번호 접두 '1'~'5')가 있으면 가산. 가중치는 TYPES[w] x 심각도/2.
SLOT_BONUS = 2.0      # 슬롯 1개 충족 보너스(유형 가중 전)
SYN_BONUS = 0.5       # 조합 내 방향 연계 강도 1당 가산(추정 연계는 x0.5)
SYN_SLOT_BONUS = 1.0  # 같은 유형의 서로 다른 두 슬롯 충족자 사이 syn 유형 연계가 있으면 추가 가산
SLOT_RULES = {
 'HIT_COUNT_TRIGGER': dict(slots=[('발동 차단/지연', ['BREAK', 'CC_APPLY', 'GAUGE_DOWN']), ('단일 대형 폭딜', ['SINGLE_BIG', 'BURST'])], syn=['4'],
     good='턴당 공격 횟수가 적고 1타 비중이 큰 궁극기 중심 구성. 브레이크로 발동 차단(공허초월자 영면의 눈동자는 격파 상태에서 불발)',
     bad='추가 발동/연쇄 피해/연타·트리거 추가 공격(MULTIHIT>=2). 전체 공격 카운트형은 광역 연타도 부적합, 단일 카운트형(오르트로스)은 광역이 우회책'),
 'TURN_HIT_REDUCTION': dict(slots=[('1턴 1타 폭딜', ['SINGLE_BIG', 'BURST'])], syn=[],
     good='한 턴에 한 번의 큰 타격(궁극기), 쿨감으로 궁극기 빈도 확보', bad='한 턴에 여러 번 피격시키는 구성(추가 발동·트리거·연타)'),
 'HIT_STACK_OFFENSE': dict(slots=[('속공 폭딜', ['BURST', 'DEALER']), ('행동 억제', ['CC_APPLY', 'GAUGE_DOWN'])], syn=['4'],
     good='짧은 턴 안에 끝내는 버스트, 행동 게이지 감소/CC로 적 턴 감소', bad='많이 때리면서 오래 끄는 소모전(피격 스택이 쌓임)'),
 'HIT_STACK_DEFENSE': dict(slots=[('초반 폭딜', ['BURST']), ('방어 관통', ['DEF_PEN'])], syn=[],
     good='초반 몰아치기, 방어 관통', bad='저계수 연타 장기전'),
 'HIT_GAUGE_GAIN': dict(slots=[('행동 억제', ['CC_APPLY', 'GAUGE_DOWN'])], syn=[],
     good='적 게이지 감소/CC', bad='연타로 적 게이지를 계속 채우는 구성'),
 'HIT_RETALIATION': dict(slots=[('피격 반응 완충', ['SHIELD', 'HEAL', 'TAUNT'])], syn=['3'],
     good='반격을 흡수하는 보호막/힐/도발', bad='취약한 후열 딜러 위주의 연타'),
 'SHIELD_GEN': dict(slots=[('보호막 파괴/방관', ['BREAK', 'DEF_PEN']), ('후속 폭딜', ['BURST', 'SINGLE_BIG', 'DEALER'])], syn=['1', '2'],
     good='보호막 파괴(강인도 피해/방어 관통) 담당 1 + 파괴 직후 폭딜 담당 1', bad='보호막이 남은 상태의 저피해 연타(보호막 유지 시 반격/가중 피해)'),
 'SHIELD_GATED': dict(slots=[('보호막 파괴/방관', ['BREAK', 'DEF_PEN']), ('후속 폭딜', ['BURST', 'SINGLE_BIG', 'DEALER'])], syn=['1', '2'],
     good='보호막 파괴 담당 1 + 폭딜 1, 파괴 전 피격 반응(마르실/타냐/벨 리스) 흡수용 보호막/힐',
     bad='MULTIHIT(피격마다 보호막 반응 발동), 보호막 아군에게 가중 피해(공허망명자)면 보호막 부여형 서포터'),
 'BUFF_STATE_PUNISH': dict(slots=[('자립형 폭딜', ['SELF_RELIANT'])], syn=[],
     good='버프 없이도 피해가 나오는 딜러', bad='강화 효과/보호막 의존 딜러'),
 'BUFF_STRIP': dict(slots=[('자립형 폭딜', ['SELF_RELIANT']), ('클렌즈/재부여', ['CLEANSE', 'CD_REDUCE'])], syn=['2'],
     good='강화 의존이 낮은 딜러 + 재부여 가능한 구성', bad='BUFFER_DEP(강화 효과 개수 비례) 스킬 중심'),
 'DEBUFF_SCALING': dict(slots=[('클렌즈/면역', ['CLEANSE', 'RES_IMMUNE']), ('폭딜', ['BURST', 'DEALER'])], syn=['3'],
     good='아군 약화를 해제하거나 면역으로 막는 담당 + 딜러', bad='피격 시 약화를 많이 받는 저방어 구성'),
 'DEBUFF_GATED_POWER': dict(slots=[('디버프 부여', ['DEBUFFER']), ('디버프 소비 폭딜', ['DEALER'])], syn=['1'],
     good='보스에 약화를 상시 유지(디버프 담당) + 약화 조건 소비 딜러(부여->소비 연계쌍)', bad='클렌즈 위주, 디버프 없이 단독 딜'),
 'SELF_CLEANSE': dict(slots=[('자체 완결 폭딜', ['SELF_RELIANT'])], syn=[],
     good='턴 정기 해제를 감안해 디버프 의존이 낮은 딜', bad='디버프를 누적해 소비하는 느린 구성'),
 'SELF_BUFF_DEPENDENT': dict(slots=[('강화 해제', ['DISPEL']), ('폭딜', ['DEALER'])], syn=['1'],
     good='적 강화 효과 해제 스킬 + 폭딜', bad='해제 수단 없는 장기전'),
 'ENRAGE_STACK': dict(slots=[('가속(게이지/쿨감/추가턴)', ['GAUGE_ALLY', 'CD_REDUCE', 'EXTRA_TURN']), ('폭딜', ['BURST', 'DEALER'])], syn=['4'],
     good='가속 담당이 폭딜 담당의 궁극기/특수기를 빨리 돌리는 쌍(쿨감·게이지->궁극/특수 연계)', bad='지속 피해/누적형 느린 딜, 순수 서포트 3명 이상'),
 'SUMMON': dict(slots=[('광역', ['AOE']), ('브레이커', ['BREAK'])], syn=[], good='소환체를 한 번에 정리하는 광역', bad='단일 집중(소환체 방치)'),
 'LINKED_MINIONS': dict(slots=[('광역', ['AOE']), ('브레이커', ['BREAK'])], syn=[], good='부하 우선 격파(광역/브레이크) 후 보스', bad='보스만 단일 연타(부하 생존 효과 유지)'),
 'TARGET_PRIORITY': dict(slots=[('보호/도발', ['TAUNT', 'SHIELD', 'HEAL'])], syn=['3'], good='우선 공격 대상을 받아내는 보호·도발·힐(생존연계쌍)', bad='전열/표적에 서는 저내구 딜러'),
 'CC_APPLY': dict(slots=[('클렌즈/면역', ['CLEANSE', 'RES_IMMUNE'])], syn=[], good='저항·클렌즈', bad='행동 불가 시 붕괴되는 단일 코어 구성'),
 'GAUGE_DENIAL': dict(slots=[('클렌즈/게이지 복구', ['CLEANSE', 'RES_IMMUNE', 'GAUGE_ALLY'])], syn=['4'], good='게이지 보충/면역', bad='첫 턴에 모든 것을 거는 구성'),
 'RESIST_IGNORE': dict(slots=[('클렌즈', ['CLEANSE'])], syn=[], good='해제 수단(효과 저항 스탯은 무의미)', bad='효과 저항 스탯에만 의존'),
 'HEAL_BLOCK': dict(slots=[('보호막/피감', ['SHIELD', 'SELF_SUSTAIN'])], syn=[], good='회복 외 생존(보호막)', bad='힐 의존 생존'),
 'TOUGHNESS_IMMUNE_WINDOW': dict(slots=[('구간 전후 폭딜', ['BURST']), ('브레이커', ['BREAK'])], syn=[], good='무효 구간 전 버스트, 종료 후 브레이크', bad='브레이크 전용 딜러를 구간 중에 사용'),
 'TOUGHNESS_BREAK_REACTIVE': dict(slots=[('브레이커', ['BREAK']), ('폭딜', ['BURST', 'DEALER'])], syn=[], good='격파가 이득인 기믹은 브레이커 1 + 폭딜 1(공허몰살자는 격파 금지)', bad='격파 시 오히려 강해지는 보스에 브레이커'),
 'PCT_HP_DAMAGE': dict(slots=[('보호막/힐', ['SHIELD', 'HEAL'])], syn=['3'], good='방어력 무관 피해를 흡수/회복', bad='방어력 스탯에만 의존한 탱킹'),
 'OPENER_BURST': dict(slots=[('초반 방어', ['SHIELD', 'HEAL', 'TAUNT'])], syn=['3'], good='개전 직후 방어 수단', bad='첫 턴 궁극기 준비만 하는 느린 시작'),
 'HP_THRESHOLD_PHASE': dict(slots=[('구간 전 폭딜', ['BURST'])], syn=[], good='구간 직전 한 번에 넘기는 버스트', bad='구간 근처에서 쪼개는 연타(반응 반복)'),
 'STEALTH': dict(slots=[('광역', ['AOE'])], syn=[], good='은신 대상 무관 광역', bad='단일 집중(추정)'),
 'SKILL_NULLIFY': dict(slots=[('광역/소모용 선타', ['AOE'])], syn=[], good='무효를 소모시킬 광역/저가치 선타(추정)', bad='첫 턴 궁극기(추정)'),
 'ELEMENT_RESIST': dict(slots=[], syn=[], good='해당 속성 구원자(param)', bad='다른 속성'),
}

# 다중 타수 신호 가중치(문구에서 읽히는 것만). 임계값은 상단에서 조정
MH = dict(
    explicit=r'(\d+)\s*(?:회|번|타)\s*(?:연속\s*)?(?:공격|타격|발사|베)',        # 'N회 공격' 류(데이터에 거의 없음)
    seq=r'연속|연타|난타|난사|여러 번',                                           # d1 키워드(가중 1)
    extra_cast=r'추가 발동|한 ?번 더 발동|두 번 더 발동|추가로 발동',             # 추가 발동(가중 2)
    chain=r'연쇄 피해',                                                           # 연쇄 피해(가중 1)
    extra_turn=r'추가 턴',                                                        # 추가 턴(가중 0.5)
    w_seq=1.0, w_extra=2.0, w_chain=1.0, w_turn=0.0, w_trigger_attack=1.0, cap_skill=3.0,
    # 총점 -> 0~3
    thr=(0.5, 2.0, 4.0),     # score>=thr[0]->1, >=thr[1]->2, >=thr[2]->3
    # 단일 대형 타격: 단일 대상 공격 중 최대 계수(%)와 점수 조건
    big_amp_pct=30, big_max_mh=1, big_max_aoe=0.34,   # 계수는 슬롯 표준값이라 판별 불가 -> 조건부 피해 증가 N% 이상을 단일 집중 신호로 사용
)

def cfg_args():
    ap = argparse.ArgumentParser()
    for k, v in D.items(): ap.add_argument('--' + k, default=v)
    return ap.parse_args()

def load(p): return read_json(p)

def norm(t): return re.sub(r'\d+(?:\.\d+)?', 'N', t)

# ================================================================== 적 쪽
def build_enemy(a):
    raw = load(a.raw); U, S, X = raw['u'], raw['s'], raw['x']
    # 스킬 idx -> 소유 유닛 idx
    own = C.defaultdict(list)
    for ui, u in enumerate(U):
        for si in u['sk']: own[si].append(ui)
    # 유닛 idx -> 등장 스테이지(원본 g 를 직접 순회; foe_stages 와 동일 구조)
    app = C.defaultdict(list)   # ui -> [(ckey,cname,tab,stage,boss,elite)]
    stage_units = {}            # 'content|tab|stage' -> {ui: [boss, elite]}
    stage_meta = []
    for g in raw['g']:
        for t in g['tabs']:
            for st in t['s']:
                seen = {}
                for w in st['w']:
                    for e in w:
                        ui, xi = e[0], (e[1] if len(e) > 1 else None)
                        x = X[xi] if xi is not None else None
                        b = bool((x and x.get('b')) or U[ui]['g'] == '보스')
                        el = bool((x and x.get('e')) or U[ui]['g'] == '정예')
                        k = ui
                        if k not in seen: seen[k] = [b, el]
                        else: seen[k] = [seen[k][0] or b, seen[k][1] or el]
                for sm in st.get('sm', []) or []:
                    for ui, xi, n in sm[2]:
                        seen.setdefault(ui, [False, False])
                stage_units[f"{g['k']}|{t['t']}|{st['n']}"] = dict(seen)
                for ui, (b, el) in seen.items():
                    app[ui].append((g['k'], g['t'], t['t'], st['n'], b, el))
                stage_meta.append((g['k'], t['t'], st['n'], st.get('fx'), st.get('lt'), bool(st.get('sm'))))

    found = {}      # (code, unit_name, slot, skill_name, normtext, subtype) -> record
    residual = C.Counter()
    covered_ct = C.Counter(); total_texts = set()
    for si, s in enumerate(S):
        if si not in own: continue
        text = s.get('d1', '') or ''
        if not text.strip(): continue
        slot = s['sl']
        hit_any = False
        for code, rx, sev, sub in ENEMY_RULES:
            for m in re.finditer(rx, text):
                hit_any = True
                sv = sev(m) if callable(sev) else sev
                st_ = sub(m) if callable(sub) else sub
                for ui in own[si]:
                    u = U[ui]
                    key = (code, u['n'], slot, s['n'], norm(text), st_ or '')
                    r = found.get(key)
                    if r is None:
                        r = found[key] = dict(code=code, unit=u['n'], unit_title=u.get('ti'), unit_grade=u['g'], slot=slot, skill=s['n'], text=text,
                                              severity=sv, subtype=st_, uidx=set(), element=u['el'], role=u['r'])
                    r['uidx'].add(ui); r['severity'] = max(r['severity'], sv)
                break   # 같은 규칙이 한 문구에서 여러 번 걸려도 1건
        total_texts.add(norm(s['n'] + '|' + text))
        if not hit_any:
            residual[(slot, s['n'], norm(text)[:150])] += 1
    # 등장 범위 집계
    gims = []
    ui_codes = C.defaultdict(list)   # ui -> [(gid, code, sev)]
    for gi, (key, r) in enumerate(found.items()):
        r['gid'] = f'G{gi:04d}'
        for ui in r['uidx']: ui_codes[ui].append((r['gid'], r['code'], r['severity']))
        ap = C.defaultdict(lambda: C.defaultdict(list))
        boss_stages = 0; elite_stages = 0; nst = 0
        for ui in r['uidx']:
            for ck, cn, tab, stn, b, el in app.get(ui, []):
                ap[(ck, cn)][tab].append(stn); nst += 1
                boss_stages += b; elite_stages += el
        appearances = []
        for (ck, cn), tabs in ap.items():
            appearances.append(dict(content=ck, content_name=cn, n_stage=sum(len(v) for v in tabs.values()),
                                    tabs={t: dict(n=len(v), first=v[0], last=v[-1]) for t, v in tabs.items()}))
        gims.append(dict(gid=r['gid'], code=r['code'], unit=r['unit'], unit_title=r['unit_title'], unit_grade=r['unit_grade'], slot=r['slot'],
                         skill=r['skill'], text=r['text'], subtype=r['subtype'], severity=r['severity'],
                         confidence='확인', impact_confidence=TYPES[r['code']]['impact_conf'],
                         is_boss_unit=r['unit_grade'] == '보스', is_elite_unit=r['unit_grade'] == '정예',
                         n_stage_appearances=nst, boss_flag_stages=boss_stages, elite_flag_stages=elite_stages,
                         unit_variants=len(r['uidx']), appearances=sorted(appearances, key=lambda x: -x['n_stage'])))
    gims.sort(key=lambda g: (g['code'], -g['severity'], -g['n_stage_appearances']))
    # 스테이지 고정효과(fx)/턴 제한
    fx = C.Counter(); lt = C.Counter()
    for ck, tab, stn, f, l, sm in stage_meta:
        for x in f or []: fx[(ck, re.sub(r'\d+', 'N', x))] += 1
        if l: lt[(ck, l)] += 1
    # 스테이지 키 -> 기믹(엔진이 스테이지별로 읽는 인덱스). 키 형식 'content|tab|stage'
    sidx = {}
    for sk_, units in stage_units.items():
        codes = {}; bosses = []
        for ui, (b, el) in units.items():
            cs = ui_codes.get(ui, [])
            if b or el: bosses.append(dict(unit=U[ui]['n'], boss=bool(b), elite=bool(el)))
            for gid, code, sev in cs:
                e = codes.setdefault(code, dict(sev=0, units=[], gids=[]))
                e['sev'] = max(e['sev'], sev)
                if U[ui]['n'] not in e['units']: e['units'].append(U[ui]['n'])
                e['gids'].append(gid)
        if codes: sidx[sk_] = dict(boss_units=bosses, types=codes)
    by_gid = {g['gid']: g for g in gims}
    for g in gims: g['stage_keys'] = []
    for sk_, v in sidx.items():
        for code, e in v['types'].items():
            for gid in e['gids']:
                lst = by_gid[gid]['stage_keys']
                if len(lst) < 60 and sk_ not in lst: lst.append(sk_)
    for g in gims: g['stage_keys_truncated'] = g['n_stage_appearances'] > len(g['stage_keys'])
    return gims, residual, fx, lt, total_texts, stage_meta, sidx

# ================================================================== 구원자 쪽
def build_savior(a):
    d = load(a.savior); U = d['units']
    reco = load(a.reco)['saviors']
    key_of = {(s['name'], s['subtitle']): s['key'] for s in reco}
    byk = C.defaultdict(list)
    for u in U: byk[(u['n'], u['ti'])].append(u)
    out = {}; tags_out = {}; unmatched = []
    for (n, ti), us in byk.items():
        key = key_of.get((n, ti))
        if key is None: unmatched.append((n, ti))
        skills = [s for u in us for s in u['sk']]
        base = us[0]
        # 중복 스킬(같은 이름) 제거: 개화 변형 등
        seen = set(); sk = []
        for s in skills:
            k2 = (s['sl'], s['n'])
            if k2 in seen: continue
            seen.add(k2); sk.append(s)
        # ---- 다중 타수
        ev = []; score = 0.0
        atk = [s for s in sk if s.get('act') == '공격']
        single_coefs = []; aoe_n = 0
        for s in sk:
            txt = ' '.join([s.get('d1', ''), s.get('dx') or '', ' '.join(s.get('ef', []))])
            w = 0.0; why = []
            m = re.search(MH['explicit'], txt)
            if m: w += int(m.group(1)) - 1; why.append(m.group(0))
            if s.get('act') == '공격' and re.search(MH['seq'], s.get('d1', '')): w += MH['w_seq']; why.append('연속/연타 문구')
            if re.search(MH['extra_cast'], txt): w += MH['w_extra']; why.append('추가 발동')
            if re.search(MH['chain'], txt) and (s.get('act') == '공격' or s['ty'] == '고유 패시브'): w += MH['w_chain']; why.append('연쇄 피해')
            if re.search(MH['extra_turn'], txt): w += MH['w_turn']; why.append('추가 턴')
            if s['ty'] == '트리거' and s.get('act') == '공격': w += MH['w_trigger_attack']; why.append('트리거 추가 공격')
            w = min(w, MH['cap_skill'])
            if w > 0: ev.append(dict(skill=s['n'], slot=s['sl'], weight=w, why=why)); score += w
        for s in atk:
            if s.get('tg') == '적 전체' or s.get('all'): aoe_n += 1
            elif s.get('tg') == '적 단일' and s.get('cf'): single_coefs.append((s['cf'][0] / 100.0, s['n'], s['sl']))
        thr = MH['thr']
        lvl = 3 if score >= thr[2] else 2 if score >= thr[1] else 1 if score >= thr[0] else 0
        big = None
        aoer = (aoe_n / len(atk)) if atk else 0
        if single_coefs and lvl <= MH['big_max_mh'] and aoer <= MH['big_max_aoe']:
            amps = []
            for s in atk:
                if s.get('tg') != '적 단일' or s['sl'] not in ('특수기', '궁극기', '변형 궁극기', '변형 특수기'): continue
                txt = ' '.join([s.get('d1', ''), ' '.join(s.get('ef', []))])
                for m in re.finditer(r'(?:피해량이 |피해 증가 \+|피해량이 추가로 )(\d+)%', txt):
                    if int(m.group(1)) != 15: amps.append((int(m.group(1)), s['n'], s['sl']))   # +15%는 전 스킬 공통 표준 보정
            if amps:
                a_, nm, sl = max(amps)
                if a_ >= MH['big_amp_pct']: big = dict(skill=nm, slot=sl, conditional_amp_pct=a_)
        out[key or f'{n}|{ti}'] = dict(name=n, subtitle=ti, element=base['a'], role=base['r'], grade=base['g'], matched_reco=key is not None,
            multihit_score=lvl, multihit_raw=round(score, 2), evidence=ev,
            single_big=big, max_single_coef_pct=max([c for c, _, _ in single_coefs], default=None), coef_note='슬롯 표준값이라 변별력 없음',
            attack_skills=len(atk), aoe_attack_skills=aoe_n, aoe_ratio=round(aoe_n / len(atk), 2) if atk else None,
            note='타수는 스킬 문구에서 직접 읽히지 않는 경우가 대부분: 추가 발동/연쇄 피해/연속 문구 기반 추정')
        # ---- 일반 태그(유형 체계용)
        tg = {}
        for tag, rx in SAVIOR_TAGS.items():
            hits = []
            for s in sk:
                txt = ' '.join([s.get('d1', ''), s.get('dx') or '', ' '.join(s.get('ef', []))])
                if tag == 'BREAK':
                    ok = re.search(r'강인도 피해가 \d+ 증가', txt) or (s.get('ab') or 0) >= 3   # ab=1/2 는 슬롯 표준값(특수 1, 궁극 2)
                else: ok = re.search(rx, txt)
                if ok: hits.append(s['n'])
            if hits: tg[tag] = sorted(set(hits))[:4]
        if lvl >= 2: tg['MULTIHIT'] = [e['skill'] for e in ev][:4]
        if big: tg['SINGLE_BIG'] = [big['skill']]
        if out[key or f'{n}|{ti}']['aoe_ratio'] and out[key or f'{n}|{ti}']['aoe_ratio'] >= 0.5: tg['AOE'] = ['적 전체 공격 비중 높음']
        # 버스트: 궁극기 계수가 큰 경우(단일/광역 무관)
        uc = [s['cf'][0] / 100.0 for s in atk if s['sl'] in ('궁극기', '변형 궁극기') and s.get('cf')]
        if uc and max(uc) >= 250: tg['BURST'] = [f'궁극기 계수 {max(uc):.0f}%']
        # 서포트 중심: 공격 스킬 비중 낮음
        if len(atk) <= 2: tg['SUPPORT_HEAVY'] = ['공격 스킬 2개 이하']
        else: tg['DEALER'] = ['공격 스킬 3개 이상']
        if 'DEALER' in tg and 'BUFFER_DEP' not in tg: tg['SELF_RELIANT'] = ['강화 의존 문구 없음']
        # 기본기 의존: 기본기 이외 공격 스킬 없음(드묾)
        tags_out[key or f'{n}|{ti}'] = tg
    return out, tags_out, unmatched

# ================================================================== 규칙(유형x성향) / 보스 매칭
import math
IDF = {}   # 태그 희소성 가중치(main 에서 채움): 흔한 태그(GAUGE_ALLY 등)는 변별력이 낮아 가중을 줄인다

def score_savior(tg, mh, rule, elem, sav_el):
    sc = 0.0; why = []
    for t in rule['prefer']:
        if t in tg: sc += IDF.get(t, 1.0); why.append('+' + t)
    for t in rule['avoid']:
        if t == 'MULTIHIT':
            if mh >= 2: sc -= 1 + (mh - 2) * 0.5; why.append('-MULTIHIT')
        elif t in tg: sc -= IDF.get(t, 1.0); why.append('-' + t)
    return sc, why

import itertools

def load_pairs(path):
    """synergy_pairs.json -> {(a,b): [(type_no, strength, conf_w, reason)]} (키의 '@변형' 접미 제거)"""
    out = C.defaultdict(list)
    if not os.path.exists(path): return out
    for p in load(path):
        a_, b_ = p['a'].split('@')[0], p['b'].split('@')[0]
        out[(a_, b_)].append((p['type'].split(':')[0], p['strength'], 1.0 if p.get('conf') == '확인' else 0.5, p['reason'][:80]))
    return out

def fill_slots(members, tagmap, slot_list):
    """한 유형의 슬롯들을 서로 다른 구성원으로 채운다(그리디). -> [(slot_name, member|None)]"""
    used = set(); res = []
    for name, tags in slot_list:
        pick = None
        for m in members:
            if m in used: continue
            if any(t in tagmap[m] for t in tags): pick = m; break
        if pick: used.add(pick)
        res.append((name, pick))
    return res

def combo_score(members, tagmap, indiv, tmap, pairs):
    """members(2~4명)의 기믹 조합 점수. tmap: {유형코드: 최대 심각도}. 개인점수 합 x0.5 + 슬롯 충족 + 연계."""
    sc = 0.5 * sum(indiv[m] for m in members); detail = []
    for code, sev in tmap.items():
        rule = SLOT_RULES.get(code)
        if not rule or not rule['slots']: continue
        wgt = TYPES[code]['w'] * sev / 2
        filled = fill_slots(members, tagmap, rule['slots'])
        for name, m in filled:
            if m: sc += SLOT_BONUS * wgt; detail.append(f'{code}:{name}={m}')
        fm = [m for _, m in filled if m]
        if len(set(fm)) >= 2 and rule['syn']:
            for x, y in itertools.permutations(set(fm), 2):
                if any(t[0] in rule['syn'] and t[1] >= 2 for t in pairs.get((x, y), [])):
                    sc += SYN_SLOT_BONUS * wgt; detail.append(f'{code}:연계 {x}->{y}'); break
    for x, y in itertools.permutations(members, 2):
        for t in pairs.get((x, y), []): sc += SYN_BONUS * t[1] * t[2] * 0.5
    return round(sc, 2), detail

def best_combos(tmap, sav, tagmap, indiv, pairs, sizes=(2, 3, 4), pool=20):
    slot_tags = set(t for c in tmap for n, ts in SLOT_RULES.get(c, {}).get('slots', []) for t in ts)
    cand = sorted(indiv, key=lambda k: -indiv[k])[:pool]
    extra = [k for k in tagmap if k not in cand and any(t in tagmap[k] for t in slot_tags)]
    cand = cand + sorted(extra, key=lambda k: -indiv[k])[:6]
    out = {}
    for n in sizes:
        best = []
        for mem in itertools.combinations(cand, n):
            s_, d_ = combo_score(mem, tagmap, indiv, tmap, pairs)
            best.append((s_, mem, d_))
        best.sort(key=lambda x: -x[0])
        out[str(n)] = [dict(score=s_, members=[dict(key=m, name=sav[m]['name'], subtitle=sav[m]['subtitle']) for m in mem], filled=d_[:8]) for s_, mem, d_ in best[:2 if n == 4 else 1]]
    return out

def slot_pair_examples(sav, tagmap, pairs, top=6):
    res = {}
    for code, rule in SLOT_RULES.items():
        if len(rule['slots']) < 2 or not rule['syn']: continue
        (n1, t1), (n2, t2) = rule['slots'][0], rule['slots'][1]
        lst = []
        for (x, y), ps in pairs.items():
            if x not in tagmap or y not in tagmap or x == y: continue
            for p in ps:
                if p[0] in rule['syn'] and p[1] >= 2 and any(t in tagmap[x] for t in t1) and any(t in tagmap[y] for t in t2):
                    lst.append((p[1] * p[2], x, y, p[0], p[3]))
        lst.sort(reverse=True)
        seen = set(); out = []
        for w_, x, y, ty, why in lst:
            if (x, y) in seen: continue
            seen.add((x, y)); out.append(dict(slot1=n1, a=x, a_name=sav[x]['name'] + '(' + sav[x]['subtitle'] + ')', slot2=n2, b=y,
                                              b_name=sav[y]['name'] + '(' + sav[y]['subtitle'] + ')', pair_type=ty, weight=w_, reason=why))
            if len(out) >= top: break
        res[code] = out
    return res

def main():
    a = cfg_args()
    os.makedirs(a.out, exist_ok=True)
    gims, residual, fx, lt, total_texts, stage_meta, sidx = build_enemy(a)
    sav, sav_tags, unmatched = build_savior(a)

    # ---- 유형 요약
    by = C.defaultdict(list)
    for g in gims: by[g['code']].append(g)
    cat = {}
    for code, t in TYPES.items():
        gs = by.get(code, [])
        units = sorted({g['unit'] for g in gs})
        boss_units = sorted({g['unit'] for g in gs if g['is_boss_unit']})
        cat[code] = dict(name=t['name'], desc=t['desc'], prefer_savior_tags=t['prefer'], avoid_savior_tags=t['avoid'], weight=t['w'],
                         impact_confidence=t['impact_conf'], param=t.get('param'), n_gimmick_records=len(gs), n_units=len(units),
                         n_boss_units=len(boss_units), boss_units=boss_units[:40], severity_hist=dict(C.Counter(g['severity'] for g in gs)),
                         slots=[dict(name=n_, tags_any=ts_) for n_, ts_ in SLOT_RULES.get(code, {}).get('slots', [])],
                         good_structure=SLOT_RULES.get(code, {}).get('good'), bad_structure=SLOT_RULES.get(code, {}).get('bad'),
                         synergy_pair_types=SLOT_RULES.get(code, {}).get('syn'))
    # ---- 스테이지 고정효과
    stage_fx = [dict(content=ck, effect=e, n_stages=n) for (ck, e), n in sorted(fx.items())]
    # fx 중 '단일/전체 공격으로 주는 피해량 증가'는 단일/광역 적 유형으로 해석
    out1 = dict(_meta=dict(
        source='foe_raw.json(스킬 d1 원문) + 스테이지 구성; foe_stages.json 은 교차 검증용',
        note_confidence='confidence=확인: 원문에 해당 메커니즘이 명시. impact_confidence=추정: 그 메커니즘이 다중 타수에 불리한지는 엔진 규칙(피격=타수 단위인지 스킬 단위인지) 불명.',
        noise_excluded=NOISE_NOTE, n_unique_skill_texts=len(total_texts), n_gimmick_records=len(gims),
        residual_unmatched=len(residual), turn_limits=[dict(content=k, turns=v, n=n) for (k, v), n in lt.items()]),
        stage_index_file='stage_gimmicks.json (키 content|tab|stage -> boss_units, types{코드:{sev,units,gids}})', type_catalog=cat, gimmicks=gims, stage_effects=stage_fx)
    atomic_json(os.path.join(a.out, 'enemy_gimmicks.json'), out1 ,indent=1)

    # ---- 구원자 성향
    dist = C.Counter(v['multihit_score'] for v in sav.values())
    atomic_json(os.path.join(a.out, 'multihit_traits.json'), dict(_meta=dict(score_def='0=신호 없음, 1~3=추가 발동/연쇄 피해/연속 문구 신호 누적(MH 가중치, 상단 참고). 확인 불가: 스킬당 실제 히트 수.',
                              thresholds=MH['thr'], single_big_def=f"단일 대상 특수기/궁극기에 조건부 피해 증가 >= {MH['big_amp_pct']}%(표준 +15% 제외), multihit<= {MH['big_max_mh']}, 광역 공격 비중<= {MH['big_max_aoe']}. 계수 자체는 슬롯 표준값(기본 65/특수 90/궁극 115, 광역 궁극 225)이라 구분 불가",
                              distribution=dict(sorted(dist.items())), unmatched_with_reco=[list(x) for x in unmatched]),
                   saviors=sav) ,indent=1)

    nS = len(sav_tags)
    for t in set(x for v in sav_tags.values() for x in v):
        n_t = sum(1 for v in sav_tags.values() if t in v)
        IDF[t] = round(math.log((nS + 1) / (n_t + 1)) / math.log(nS + 1) * 2, 2)
    # ---- 보스/정예 단위 규칙: 유닛별 유형 집합 -> 선호/기피 구원자
    unit_types = C.defaultdict(lambda: C.defaultdict(list))
    for g in gims:
        if g['unit_grade'] in ('보스', '정예'): unit_types[g['unit']][g['code']].append(g)
    boss_rules = []; scores_by_unit = {}
    for unit, tmap in unit_types.items():
        total_sev = sum(max(x['severity'] for x in gs) * TYPES[c]['w'] for c, gs in tmap.items())
        # 이 유닛의 등장 범위
        apps = C.defaultdict(int)
        for gs in tmap.values():
            for g in gs:
                for ap_ in g['appearances']: apps[ap_['content']] = max(apps[ap_['content']], ap_['n_stage'])
        scores = {}
        for key, tg in sav_tags.items():
            s = sav[key]; sc = 0.0; why = []
            for c, gs in tmap.items():
                rule = TYPES[c]; sevm = max(x['severity'] for x in gs)
                prefer = list(rule['prefer']); avoid = list(rule['avoid'])
                p = rule.get('param')
                if c == 'HIT_COUNT_TRIGGER' and any(x['subtype'] == '단일' for x in gs) and not any(x['subtype'] in ('전체', '미지정', '턴당') for x in gs):
                    avoid = list(avoid); prefer = prefer + ['AOE']
                x_sc, x_why = score_savior(tg, s['multihit_score'], dict(prefer=prefer, avoid=avoid), None, s['element'])
                if p == 'element':
                    for x in gs:
                        if c == 'ELEMENT_RESIST' and x['subtype']:
                            el = {'태양': 'sun', '달': 'moon', '별': 'star', '질서': 'order', '혼돈': 'chaos'}.get(x['subtype'], x['subtype'])
                            x_sc += 1.5 if s['element'] in (x['subtype'], el) else -1.5; x_why.append(f"원소:{x['subtype']}")
                        if c == 'ELEMENT_BIAS_ATTACK' and x['subtype'] and s['element'] == x['subtype']: x_sc -= 0.5; x_why.append(f"-{x['subtype']}가중")
                sc += x_sc * rule['w'] * (sevm / 2); why += [f'{c}:{w}' for w in x_why]
            scores[key] = (round(sc, 2), why)
        ranked = sorted(scores.items(), key=lambda kv: -kv[1][0])
        scores_by_unit[unit] = scores
        boss_rules.append(dict(unit=unit, n_types=len(tmap), type_codes=sorted(tmap), priority=total_sev,
                               stage_counts_by_content=dict(apps),
                               prefer=[dict(key=k, name=sav[k]['name'], subtitle=sav[k]['subtitle'], score=v[0], why=v[1][:4]) for k, v in ranked[:5] if v[0] > 0],
                               avoid=[dict(key=k, name=sav[k]['name'], subtitle=sav[k]['subtitle'], score=v[0], why=v[1][:4]) for k, v in ranked[::-1][:5] if v[0] < 0]))
    boss_rules.sort(key=lambda r: -r['priority'])
    # ---- 조합(2~4명) 점수: 슬롯 충족 + 구원자 간 연계(synergy_pairs.json)
    pairs = load_pairs(a.syn)
    for r in boss_rules:
        tmap = {c: max(x['severity'] for x in unit_types[r['unit']][c]) for c in r['type_codes']}
        indiv = {k: sc for k, (sc, _) in scores_by_unit[r['unit']].items()}
        r['combos'] = best_combos(tmap, sav, sav_tags, indiv, pairs)
        r['unfit_structures'] = {c: SLOT_RULES[c]['bad'] for c in r['type_codes'] if c in SLOT_RULES and tmap[c] >= 2 and TYPES[c]['w'] >= 2}
    slot_pairs = slot_pair_examples(sav, sav_tags, pairs)
    atomic_json(os.path.join(a.out, 'stage_gimmicks.json'), sidx ,separators=(',', ':'))
    atomic_json(os.path.join(a.out, 'gimmick_counters.json'), dict(_meta=dict(desc='유형 코드 -> 구원자 태그 선호/기피 규칙, 구원자별 태그, 보스/정예 단위 규칙 점수(규칙 합산, 가중치=유형 w * 심각도/2).',
                              tag_defs=SAVIOR_TAGS, tag_notes='MULTIHIT=다중 타수 점수>=2, SINGLE_BIG=단일 대형, AOE=적 전체 공격 비중>=0.5, BURST=궁극기 계수>=250%, SUPPORT_HEAVY=공격 스킬<=2'),
                   type_rules={c: dict(prefer=t['prefer'], avoid=t['avoid'], weight=t['w'], param=t.get('param')) for c, t in TYPES.items()},
                   slot_rules={c: dict(slots=[dict(name=n_, tags_any=ts_) for n_, ts_ in r_['slots']], good=r_['good'], bad=r_['bad'], synergy_pair_types=r_['syn']) for c, r_ in SLOT_RULES.items()},
                   combo_scoring=dict(slot_bonus=SLOT_BONUS, syn_bonus=SYN_BONUS, syn_slot_bonus=SYN_SLOT_BONUS, formula='0.5*sum(개인점수) + sum(슬롯 충족 * 2.0 * w*sev/2) + 슬롯 충족자 간 연계 + 0.5*sum(연계 강도*신뢰)*0.5'),
                   slot_pair_examples=slot_pairs, savior_tags=sav_tags, boss_rules=boss_rules) ,indent=1)

    # ---- 검토 요약용 residual 덤프(작게)
    res = [dict(slot=k[0], skill=k[1], text=k[2], n=v) for k, v in residual.most_common()]
    atomic_json(os.path.join(a.out, 'gimmick_residual.json'), res ,indent=1)
    print('gimmick records', len(gims), 'types used', len(by), 'residual', len(residual), 'texts', len(total_texts))
    print('savior mh dist', dict(sorted(dist.items())), 'unmatched', unmatched, 'saviors', len(sav))
    print('type counts', {c: len(v) for c, v in sorted(by.items(), key=lambda kv: -len(kv[1]))})

if __name__ == '__main__':
    main()
