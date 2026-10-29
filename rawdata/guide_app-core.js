const SITE_BUILD_VERSION = window.__SITE_CACHE_KEY__ || "v107-amora-portrait-fix";
const LANGUAGE_STORAGE_KEY = "starsavior-guide-language";
const SUPPORTED_LANGUAGES = ["ko", "en", "ja"];
const LANGUAGE_HTML_CODES = {
  ko: "ko-KR",
  en: "en",
  ja: "ja"
};
const I18N_DATA = {"saviorNames":{"en":{"아세라":"Asherah","스마일":"Smile","루나":"Luna","카넬리아":"Carnelia","벨 리스":"Bell","에밀리":"Emily","샤를":"Charlotte","카르멘":"Carmen","프레이":"Frey","세이라":"Seira","트리쉬":"Trish","린":"Lyn","크리스텔":"Cristelle","에데":"Haydee","세르팡":"Serpang","다나":"Dana","뮤리엘":"Muriel","엘리사":"Elisa","티리아":"Tyria","로베르타":"Roberta","루그":"Lugh","페이":"Fei","에핀델":"Epindel","오메가":"Omega","세레스":"Ceres","리디아":"Lydia","할리":"Harley","페트라":"Petra","스칼렛":"Scarlet","클레어":"Claire","레이시":"Lacy","타냐":"Tanya","릴리":"Lily","키라":"Kyra","베스타":"Besta","안나":"Annah","마르실":"Marcille","베라":"Vera","나루":"Naru","클라리사":"Clarissa","힐데":"Hilde","유미나":"Yoo Mina","로자리아":"Rosaria","프로페서M":"Professor M"},"ja":{"아세라":"アセラ","스마일":"スマイル","루나":"ルナ","카넬리아":"カネリア","벨 리스":"ベル・リース","에밀리":"エミリー","샤를":"シャルル","카르멘":"カルメン","프레이":"フレイ","세이라":"セイラ","트리쉬":"トリッシュ","린":"リン","크리스텔":"クリステル","에데":"エデ","세르팡":"セルパン","다나":"ダーナ","뮤리엘":"ミュリエル","엘리사":"エリサ","티리아":"ティリア","로베르타":"ロベルタ","루그":"ルー","페이":"フェイ","에핀델":"エピンデル","오메가":"オメガ","세레스":"セレス","리디아":"リディア","할리":"ハーレー","페트라":"ペトラ","스칼렛":"スカーレット","클레어":"クレア","레이시":"レイシー","타냐":"ターニャ","릴리":"リリー","키라":"キラ","베스타":"ベスタ","안나":"アンナ","마르실":"マルシル","베라":"ベラ","나루":"ナル","클라리사":"クラリッサ","힐데":"ヒルデ","유미나":"ヤナギ・ミナ","로자리아":"ロザリア","프로페서M":"プロフェッサーM"}},"subtitles":{"en":{"보이저 구원단":"Voyager Savior Party","방랑자":"Wanderer","캔들 스퀘어":"Candle Square","모나스티르 기사단":"Monastir Knights","나이트메어":"Nightmare","아셀루스 협회":"Aselus Association","풍월당":"Wind Moon Sect","모렐 해운상회":"Morrel Ocean Traders","카노푸스 경비대":"Canopus Rangers","모노리스 교단":"Monolith Order","집행자":"Executor","궤도 수색대":"Orbital Search Team","오를랑 가문":"House Orlan","하트 오브 모나스티르":"Heart of Monastir","서부 탈환대":"Western Liberators","헬 세이비어":"Hell Saviors","페트라 조합":"Petra Construction","리틀 타이런트":"Little Tyrant","플로리스 블루 로즈":"Flawless Blue Rose","화이트 펄 트랩":"White Pearl Trap","선샤인 캣":"Sunshine Cat","람파디스":"Lampadis","키라는 친구같은 거 없어":"Kyra Doesn't Have Friends","왈츠 오브 스타라이트":"Waltz of Starlight","이터널 프로미스":"Eternal Promise","블레싱 인 블룸":"Blessing in Bloom","노블 프린세스":"Noble Princess","NOA 타운가드":"NOA Town Guard","배달부 협회":"Courier Guild","펜릴 소대":"Fenrir Squad","폴른 호크":"Fallen Hawk"},"ja":{"보이저 구원단":"ボイジャー救援団","방랑자":"放浪者","캔들 스퀘어":"キャンドル・スクエア","모나스티르 기사단":"モナスティル騎士団","나이트메어":"ナイトメア","아셀루스 협회":"アセルス協会","풍월당":"風月堂","모렐 해운상회":"モレル海運商会","카노푸스 경비대":"カノプス警備隊","모노리스 교단":"モノリス教団","집행자":"執行者","궤도 수색대":"軌道捜索隊","오를랑 가문":"オルラン家","하트 오브 모나스티르":"ハート・オブ・モナスティル","서부 탈환대":"西部奪還隊","헬 세이비어":"ヘルセイヴァー","페트라 조합":"ペトラ組合","리틀 타이런트":"リトル・タイラント","플로리스 블루 로즈":"フローレス・ブルーローズ","화이트 펄 트랩":"ホワイトパール・トラップ","선샤인 캣":"サンシャイン・キャット","람파디스":"ランパディス","키라는 친구같은 거 없어":"キラには友達なんていないの","왈츠 오브 스타라이트":"ワルツ・オブ・スターライト","이터널 프로미스":"エターナル・プロミス","블레싱 인 블룸":"ブレッシング in ブルーム","노블 프린세스":"ノーブル・プリンセス","NOA 타운가드":"NOAのタウンガード","배달부 협회":"配達屋協会","펜릴 소대":"フェンリル小隊","폴른 호크":"フォーレン・ホーク"}},"arcana":{"en":{"단점 보완 맞춤 훈련":"Customized Training to Cover Weaknesses","꽃들에게 죽음을":"Death for the Flowers","하늘의 심판":"Divine Judgement","죽음이 둘을 갈라놓을 때까지":"Till Death Do Us Part","불굴의 역작":"The Indomitable Masterpiece","하얀 달의 온기는 햇빛처럼":"A White Moon Shines With the Sun's Warmth","누각 위, 유리달 맞이":"Under the Glass Moon, Over the Pavilion","조용한 휴식 시간":"A Quiet Moment of Rest","스트라니스의 영애":"Young Lady of Stranis","완벽한 바니걸":"The Perfect Bunny Girl","키라만큼 귀여워!":"As Cute as Kyra!","오늘의 한 걸음":"Today's Step Forward","나른한 오후의 틈새":"A Drowsy Afternoon Interlude","공녀, 왕좌에 오르다":"The Princess Ascends the Throne","본 투 비 와일드":"Born to Be Wild","허수의 개척자":"The Imaginary Pioneer","종말은 소녀의 얼굴을 하고 있다.":"The End Wears the Face of a Girl","깊은 애도":"Deep Mourning","노스텔지어의 역습":"Nostalgia Strikes Back","하늘의 시련":"Divine Trial","금단의 기록물 Vol. 1":"Forbidden Archive Vol. 1","금단의 기록물":"Forbidden Archive Vol. 1","만족스러운 식사":"A Satisfying Meal","어느 한 기사의 맹세":"A Knight's Oath","서투른 욕망 해소법":"A Clumsy Way to Relieve Desire","노 페인, 노 게인":"No Pain, No Gain","메이드 바이 페트라♡":"Made by Petra♡","별을 보며 꿈을":"Dreams Under the Stars","음독의 각오":"Even If It's Poison","누구보다 프로페셔널":"More Than Professional","서류 더미 위의 책임감":"Responsibility Atop a Pile of Paperwork","언더커버 캅":"Undercover Cop","빛을 쫓아라!":"Follow the Light!","빛을 쫓아라":"Follow the Light!","휴가 준비는 쇼핑에서부터!":"Vacation Prep Starts with Shopping!","탐닉자의 유흥거리":"A Hedonist\'s Diversion"},"ja":{"단점 보완 맞춤 훈련":"弱点補完カスタムトレーニング","꽃들에게 죽음을":"花々に死を","하늘의 심판":"天の審判","죽음이 둘을 갈라놓을 때까지":"死が二人を分かつまで","불굴의 역작":"不屈の傑作","하얀 달의 온기는 햇빛처럼":"白い月のぬくもりは陽光のように","누각 위, 유리달 맞이":"楼閣の上、硝子の月を迎えて","조용한 휴식 시간":"静かな休息のひととき","스트라니스의 영애":"ストラニスの令嬢","완벽한 바니걸":"完璧なバニーガール","키라만큼 귀여워!":"キラくらいかわいい！","오늘의 한 걸음":"今日の一歩","나른한 오후의 틈새":"けだるい午後のひととき","공녀, 왕좌에 오르다":"公女、王座に就く","본 투 비 와일드":"ボーン・トゥ・ビー・ワイルド","허수의 개척자":"虚数の開拓者","종말은 소녀의 얼굴을 하고 있다.":"終末は少女の顔をしている","깊은 애도":"深い哀悼","노스텔지어의 역습":"ノスタルジアの逆襲","하늘의 시련":"天の試練","금단의 기록물 Vol. 1":"禁断の記録物 Vol. 1","금단의 기록물":"禁断の記録物 Vol. 1","만족스러운 식사":"満足な食事","어느 한 기사의 맹세":"ある騎士の誓い","서투른 욕망 해소법":"不器用な欲望解消法","노 페인, 노 게인":"ノーペイン・ノーゲイン","메이드 바이 페트라♡":"メイド・バイ・ペトラ♡","별을 보며 꿈을":"星を見ながら夢を","음독의 각오":"毒でも覚悟のうえ","누구보다 프로페셔널":"誰よりもプロフェッショナル","서류 더미 위의 책임감":"書類の山の上の責任感","언더커버 캅":"アンダーカバー・コップ","빛을 쫓아라!":"光を追え！","빛을 쫓아라":"光を追え！","휴가 준비는 쇼핑에서부터!":"休暇の準備はショッピングから！"}},"ui":{"en":{"본문으로 바로가기":"Skip to content","구원자 목록으로 이동":"Go to Savior list","주요 메뉴":"Main navigation","구원자":"Saviors","장비":"Equipment","코스모 게이트":"Cosmo Gate","밝은 테마로 변경":"Switch to light theme","어두운 테마로 변경":"Switch to dark theme","등록된 구원자":"Registered Saviors","구원자 검색 및 필터":"Savior search and filters","구원자 검색":"Search Saviors","이름, 소속, 역할 검색":"Search name, affiliation, or role","속성":"Element","전체":"All","클래스":"Class","명의 구원자":" Saviors","필터 초기화":"Reset filters","조건에 맞는 구원자가 없습니다.":"No Saviors match the current filters.","검색어나 필터를 변경해 주세요.":"Try changing the search term or filters.","구원자 목록":"Savior List","스킬설명 및 상세정보":"Skills & Details","육성 우선순위":"Growth Priority","PVE 기준":"PVE Standard","주 사용 콘텐츠":"Main Content","장비 세팅":"Equipment Setup","아르카나 세팅":"Arcana Setup","PVE 추천 아르카나":"Recommended PVE Arcana","대체 아르카나":"Alternative Arcana","주요 PVE 콘텐츠":"Main PVE Content","보유 상황에 따라 교체":"Swap based on availability","목걸이":"Necklace","반지":"Ring","추천 세트":"Recommended Sets","잠재력":"Potential","미정":"TBD","미등록":"Not Registered","대체 아르카나가 등록되지 않았습니다.":"No alternative Arcana registered.","원본 시트 표기":"Source sheet notation","선택":"Choose","주옵션 (Tier 2)":"Main Stats (Tier 2)","부옵션 (Tier 2)":"Substats (Tier 2)","장비 개요":"Equipment Overview","구원자 장비 주옵션 및 부옵션 정보입니다.":"Main-stat and substat information for Savior equipment.","부위":"Slot","주 능력치":"Main Stat","기본 주능력치 (+0)":"Base Main Stat (+0)","기본 주능력치 (+15)":"Base Main Stat (+15)","옵션":"Option","세트별 권장 능력치":"Recommended stats by set","장비 티어 판정 기준":"Equipment tier criteria","작전":"Operations","회랑":"Cloister","플래시 포인트":"Flash Point","인자작":"Trait Farming","없음":"None","기본기":"Basic Skill","특수기":"Special Skill","궁극기":"Ultimate","한정":"Limited","개화 필수":"Bloom required","1돌파 이상 필수":"Resonance 1+ required","1돌파 이상 권장":"Resonance 1+ recommended","PVE 추천 세팅":"Recommended PVE Setup","장비 가이드 바로가기":"Open Equipment Guide","필터":"Filter","구원자 정보는 ":"Savior information follows "," 기준입니다.":" as the source.","스타세이비어 DB":"Star Savior DB","아카라이브 스타세이비어 채널 원샷 세팅표":"Arca.live Star Savior one-shot setup sheet","PVE장비 및 아르카나는 ":"PVE equipment and Arcana follow ","를 기준으로 합니다.":" as the source.","작전 · 회랑 · 코스모 게이트":"Operations · Cloister · Cosmo Gate","적중(2)는 투지(2)로 대체가능.":"Accuracy(2) can be replaced with Fighting Spirit(2).","* 적중(2)는 투지(2)로 대체가능.":"* Accuracy(2) can be replaced with Fighting Spirit(2).","※ 딜러 기준으로 공격력% 수치가 높을 시 0.5티어 상승.":"※ For DPS units, high ATK% can raise the equipment rating by 0.5 tier.","※ 속도 수치가 높을 시 0.5티어 상승.":"* High SPD can raise the equipment rating by 0.5 tier.","딜러 서브딜러 딜탱은 공격력, 공격력% 또는 생명력, 생명력%, 치명타 확률, 치명타 피해, 속도를 유효 옵션으로 사용합니다.":"DPS, sub-DPS, and bruisers use ATK/ATK%, HP/HP%, CRIT Rate, CRIT DMG, and SPD as useful stats.","일부 구원자는 효과 적중, 방어력, 방어력% 도 유효 옵션으로 활용합니다.":"Some Saviors also make effective use of Effect Hit, DEF, and DEF%.","장비 부족 시 치명타 확률 + 추가 유효 옵션 1줄 조합도 사용할 수 있습니다.":"When gear is limited, CRIT Rate plus one additional useful substat is acceptable.","장비 세팅이 충분히 갖춰진 이후에는 유효 옵션 3 이상 장비 사용을 권장합니다.":"Once your gear pool is established, equipment with at least three useful substats is recommended.","착용 시 권장 치명타 확률 90% 이상, 치명타 피해 90% 이상":"Recommended: CRIT Rate 90%+ and CRIT DMG 90%+.","착용 시 권장 치명타 확률 80% 이상, 치명타 피해 140% 이상":"Recommended: CRIT Rate 80%+ and CRIT DMG 140%+.","착용 시 권장 효과적중 140% 이상":"Recommended: Effect Hit 140%+.","치명타 확률 + 치명타 피해의 합이 ":"If CRIT Rate + CRIT DMG totals ","일 경우 0티어 장비.":", the item is Tier 0.","일 경우 1티어 장비.":", the item is Tier 1.","일 경우 2티어 장비.":", the item is Tier 2.","일 경우 3티어 장비.":", the item is Tier 3.","이 페이지는 게임 '스타 세이비어'의 비영리 팬 프로젝트입니다.":"This page is a non-profit fan project for Star Savior.","프로젝트에 사용된 모든 자산, 데이터, 이미지 및 텍스트의 소유권은 STUDIOBSIDE 에 있습니다.":"All assets, data, images, and text used in this project belong to STUDIOBSIDE.","검색과 상세 화면을 사용하려면 JavaScript를 활성화해 주세요.":"Please enable JavaScript to use search and detail views.","상세 세팅 보기":"View detailed setup"},"ja":{"본문으로 바로가기":"本文へスキップ","구원자 목록으로 이동":"救援者一覧へ","주요 메뉴":"メインメニュー","구원자":"救援者","장비":"装備","코스모 게이트":"コスモゲート","밝은 테마로 변경":"ライトテーマに変更","어두운 테마로 변경":"ダークテーマに変更","등록된 구원자":"登録済み救援者","구원자 검색 및 필터":"救援者の検索とフィルター","구원자 검색":"救援者を検索","이름, 소속, 역할 검색":"名前・所属・役割で検索","속성":"属性","전체":"すべて","클래스":"クラス","명의 구원자":"人の救援者","필터 초기화":"フィルターをリセット","조건에 맞는 구원자가 없습니다.":"条件に一致する救援者はいません。","검색어나 필터를 변경해 주세요.":"検索語やフィルターを変更してください。","구원자 목록":"救援者一覧","스킬설명 및 상세정보":"スキル説明・詳細情報","육성 우선순위":"育成優先度","PVE 기준":"PVE基準","주 사용 콘텐츠":"主な使用コンテンツ","장비 세팅":"装備セッティング","아르카나 세팅":"アルカナセッティング","PVE 추천 아르카나":"PVEおすすめアルカナ","대체 아르카나":"代替アルカナ","주요 PVE 콘텐츠":"主要PVEコンテンツ","보유 상황에 따라 교체":"所持状況に応じて交換","목걸이":"ネックレス","반지":"リング","추천 세트":"おすすめセット","잠재력":"潜在力","미정":"未定","미등록":"未登録","대체 아르카나가 등록되지 않았습니다.":"代替アルカナは登録されていません。","원본 시트 표기":"元シート表記","선택":"選択","주옵션 (Tier 2)":"メインオプション (Tier 2)","부옵션 (Tier 2)":"サブオプション (Tier 2)","장비 개요":"装備概要","구원자 장비 주옵션 및 부옵션 정보입니다.":"救援者装備のメイン・サブオプション情報です。","부위":"部位","주 능력치":"メイン能力値","기본 주능력치 (+0)":"基本メイン能力値 (+0)","기본 주능력치 (+15)":"基本メイン能力値 (+15)","옵션":"オプション","세트별 권장 능력치":"セット別推奨能力値","장비 티어 판정 기준":"装備Tier判定基準","작전":"作戦","회랑":"回廊","플래시 포인트":"フラッシュポイント","인자작":"因子厳選","없음":"なし","기본기":"基本技","특수기":"特殊技","궁극기":"究極技","한정":"限定","개화 필수":"開花必須","1돌파 이상 필수":"1凸以上必須","1돌파 이상 권장":"1凸以上推奨","PVE 추천 세팅":"PVEおすすめセッティング","장비 가이드 바로가기":"装備ガイドを開く","구원자 정보는 ":"救援者情報は "," 기준입니다.":" を基準としています。","스타세이비어 DB":"Star Savior DB","아카라이브 스타세이비어 채널 원샷 세팅표":"Arca.live Star Savior ワンショットセッティング表","PVE장비 및 아르카나는 ":"PVE装備・アルカナは ","를 기준으로 합니다.":" を基準としています。","작전 · 회랑 · 코스모 게이트":"作戦 · 回廊 · コスモゲート","적중(2)는 투지(2)로 대체가능.":"的中セット(2)は闘志セット(2)で代用可能です。","* 적중(2)는 투지(2)로 대체가능.":"* 的中セット(2)は闘志セット(2)で代用可能です。","※ 딜러 기준으로 공격력% 수치가 높을 시 0.5티어 상승.":"※ アタッカー基準で攻撃力(%)が高い場合、0.5 Tier上昇。","※ 속도 수치가 높을 시 0.5티어 상승.":"* 速度が高い場合、0.5 Tier上昇。","딜러 서브딜러 딜탱은 공격력, 공격력% 또는 생명력, 생명력%, 치명타 확률, 치명타 피해, 속도를 유효 옵션으로 사용합니다.":"アタッカー、サブアタッカー、ブルーザーは攻撃力、攻撃力(%)またはHP、HP(%)、会心率、会心ダメージ、速度を有効オプションとして使用します。","일부 구원자는 효과 적중, 방어력, 방어력% 도 유효 옵션으로 활용합니다.":"一部の救援者は効果命中、防御力、防御力(%)も有効オプションとして使用します。","장비 부족 시 치명타 확률 + 추가 유효 옵션 1줄 조합도 사용할 수 있습니다.":"装備が不足している場合、会心率＋追加の有効オプション1枠の組み合わせも使用できます。","장비 세팅이 충분히 갖춰진 이후에는 유효 옵션 3 이상 장비 사용을 권장합니다.":"装備が揃った後は、有効オプション3つ以上の装備を推奨します。","이 페이지는 게임 '스타 세이비어'의 비영리 팬 프로젝트입니다.":"このページはゲーム『Star Savior』の非営利ファンプロジェクトです。","프로젝트에 사용된 모든 자산, 데이터, 이미지 및 텍스트의 소유권은 STUDIOBSIDE 에 있습니다.":"本プロジェクトで使用するすべてのアセット、データ、画像、テキストの権利はSTUDIOBSIDEに帰属します。","검색과 상세 화면을 사용하려면 JavaScript를 활성화해 주세요.":"検索と詳細画面を利用するにはJavaScriptを有効にしてください。","상세 세팅 보기":"詳細セッティングを見る","통찰 4세트":"洞察セット(4)","파괴 4세트":"破壊セット(4)","적중 2세트":"的中セット(2)"}},"terms":{"en":{"태양":"Sun","달":"Moon","별":"Star","질서":"Order","혼돈":"Chaos","스트라이커":"Striker","어쌔신":"Assassin","레인저":"Ranger","캐스터":"Caster","디펜더":"Defender","서포터":"Supporter","딜러":"DPS","서브딜러":"Sub-DPS","딜탱":"Bruiser","참격":"Slash","타격":"Impact","마법":"Element","정신":"Spirit","속도":"SPD","공격력%":"ATK%","공격력":"ATK","생명력%":"HP%","생명력":"HP","방어력%":"DEF%","방어력":"DEF","치명타 확률":"CRIT Rate","치명타 피해":"CRIT DMG","효과 적중":"Effect Hit","효과 저항":"Effect RES","치명타 확률":"CRIT Rate","치명타 피해":"CRIT DMG","효과적중":"Effect Hit","통찰(4)":"Insight(4)","파괴(4)":"Destruction(4)","적중(2)":"Accuracy(2)","투지(2)":"Fighting Spirit(2)","정밀(4)":"Precision(4)","대체":" substitute","공용 아르카나":"Universal Arcana","원본 자료 미등록":"TBD","해당 엑셀에 없음":"Not listed in source sheet","1티어":"Tier 1","2티어":"Tier 2","3티어":"Tier 3","4티어":"Tier 4","0티어":"Tier 0","0.5티어":"Tier 0.5"},"ja":{"태양":"太陽","달":"月","별":"星","질서":"秩序","혼돈":"混沌","스트라이커":"ストライカー","어쌔신":"アサシン","레인저":"レンジャー","캐스터":"キャスター","디펜더":"ディフェンダー","서포터":"サポーター","딜러":"アタッカー","서브딜러":"サブアタッカー","딜탱":"ブルーザー","참격":"斬撃","타격":"打撃","마법":"元素","정신":"精神","속도":"速度","공격력%":"攻撃力(%)","공격력":"攻撃力","생명력%":"HP(%)","생명력":"HP","방어력%":"防御力(%)","방어력":"防御力","치명타 확률":"会心率","치명타 피해":"会心ダメージ","효과 적중":"効果命中","효과 저항":"効果耐性","치명타 확률":"会心率","치명타 피해":"会心ダメージ","효과적중":"効果命中","통찰(4)":"洞察セット(4)","파괴(4)":"破壊セット(4)","적중(2)":"的中セット(2)","투지(2)":"闘志セット(2)","정밀(4)":"精密セット(4)","대체":" の代替","공용 아르카나":"共通アルカナ","원본 자료 미등록":"未定","해당 엑셀에 없음":"元シートに記載なし","1티어":"Tier 1","2티어":"Tier 2","3티어":"Tier 3","4티어":"Tier 4","0티어":"Tier 0","0.5티어":"Tier 0.5","공격력 증가율(%)":"攻撃力(%)","생명력 증가율(%)":"HP(%)","방어력 증가율(%)":"防御力(%)","효과적중":"効果命中","공생방%":"攻撃力/HP/防御力(%)","적중&저항":"効果命中＆効果耐性","속도 세트":"速度セット","방어 세트":"防御セット","적중 세트":"的中セット","저항 세트":"抵抗セット","공격 세트":"攻撃セット","통찰 세트":"洞察セット","투지 세트":"闘志セット","정밀 세트":"精密セット","생명 세트":"体力セット","파괴 세트":"破壊セット","장벽 세트":"防壁セット","섬멸 세트":"殲滅セット","속도(4)":"速度セット(4)","방어(2)":"防御セット(2)","방어(4)":"防御セット(4)","저항(2)":"抵抗セット(2)","공격(4)":"攻撃セット(4)","생명(4)":"体力セット(4)","장벽(2)":"防壁セット(2)","섬멸(2)":"殲滅セット(2)","방퍼":"防御力(%)"}}};

Object.assign(I18N_DATA.ui.en, {
  "초보 단장님 안내": "New Commander Guide",
  "구원자 세팅을 참고하기 전, 장비 탭의 「장비 개요」와 아르카나 탭의 「아르카나 개요」를 먼저 읽어보시길 권합니다.":
    "Before using the Savior setup recommendations, we recommend reading both Equipment > “Equipment Overview” and Arcana > “Arcana Overview” first.",
  "장비 개요 바로가기 →": "Open Equipment Overview →",
  "아르카나 개요 바로가기 →": "Open Arcana Overview →"
});

Object.assign(I18N_DATA.ui.ja, {
  "초보 단장님 안내": "初心者団長へのご案内",
  "구원자 세팅을 참고하기 전, 장비 탭의 「장비 개요」와 아르카나 탭의 「아르카나 개요」를 먼저 읽어보시길 권합니다.":
    "救援者のセッティングを参考にする前に、装備タブの「装備概要」とアルカナタブの「アルカナ概要」を先にお読みいただくことをおすすめします。",
  "장비 개요 바로가기 →": "装備概要へ →",
  "아르카나 개요 바로가기 →": "アルカナ概要へ →"
});

Object.assign(I18N_DATA.ui.en, {
  "주의사항": "Notice",
  "본 사이트의 추천 아르카나 및 장비 세팅은 절대적인 정답이 아닙니다. 이용하는 콘텐츠와 현재 육성 상태에 따라 적합한 세팅이 달라질 수 있으므로, 참고용으로 활용해 주세요.":
    "The recommended Arcana and equipment setups on this site are not definitive answers. The most suitable setup may vary depending on the content you are playing and your current progression, so please use these recommendations as a reference."
});

Object.assign(I18N_DATA.ui.ja, {
  "주의사항": "注意事項",
  "본 사이트의 추천 아르카나 및 장비 세팅은 절대적인 정답이 아닙니다. 이용하는 콘텐츠와 현재 육성 상태에 따라 적합한 세팅이 달라질 수 있으므로, 참고용으로 활용해 주세요.":
    "本サイトのおすすめアルカナ・装備セッティングは、絶対的な正解ではありません。利用するコンテンツや現在の育成状況によって適したセッティングは異なるため、あくまで参考としてご利用ください。"
});

Object.assign(I18N_DATA.ui.en, {
  "초보 단장님은 딜러 세팅 시 통찰 세트를 우선 권장합니다. 일부 구원자를 제외하면 파괴 세트는 세팅 난이도가 높은 편입니다.":
    "For new players, Insight sets are generally recommended for damage dealers. With a few exceptions, Destruction sets are harder to build effectively."
});
Object.assign(I18N_DATA.ui.ja, {
  "초보 단장님은 딜러 세팅 시 통찰 세트를 우선 권장합니다. 일부 구원자를 제외하면 파괴 세트는 세팅 난이도가 높은 편입니다.":
    "初心者の団長には、アタッカーの装備として洞察セットを優先的におすすめします。一部の救援者を除き、破壊セットは装備厳選の難易度が高めです。"
});



// 2026-10-02 추천 세팅 / 업데이트 안내 다국어
Object.assign(I18N_DATA.arcana.en, {
  "자칭 베테랑 탐정의 수사법": "[A Self-Proclaimed Veteran Detective] Memory"
});
Object.assign(I18N_DATA.arcana.ja, {
  "자칭 베테랑 탐정의 수사법": "自称ベテラン探偵の捜査法",
  "탐닉자의 유흥거리": "享楽者の慰み"
});
Object.assign(I18N_DATA.ui.en, {
  "부족한 자리 대체": "Fill an open slot",
  "탐닉자의 유흥거리 대체": "Substitute for A Hedonist's Diversion",
  "업데이트 안내": "Update Notes",
  "클라리사 추천 아르카나 변경 (10.02)": "Clarissa recommended Arcana updated (10.02)",
  "그웬 추가 및 추천 세팅 반영 (10.02)": "Gwen added & recommended setup updated (10.02)",
  "스트라이커 추천 아르카나 일괄 변경 (10.02)": "Striker recommended Arcana updated (10.02)"
});
Object.assign(I18N_DATA.ui.ja, {
  "부족한 자리 대체": "不足枠の代替",
  "탐닉자의 유흥거리 대체": "「享楽者の慰み」の代替",
  "업데이트 안내": "アップデート案内",
  "클라리사 추천 아르카나 변경 (10.02)": "クラリッサのおすすめアルカナ変更 (10.02)",
  "그웬 추가 및 추천 세팅 반영 (10.02)": "グウェン追加・おすすめセッティング反映 (10.02)",
  "스트라이커 추천 아르카나 일괄 변경 (10.02)": "ストライカーのおすすめアルカナ一括変更 (10.02)"
});

// 장비 페이지 풀네임 표기 다국어 보정
Object.assign(I18N_DATA.ui.en, {
  "통찰 4세트 착용 시 권장 치명타 확률 90% 이상, 치명타 피해 90% 이상":
    "Insight Set (4) — Recommended: CRIT Rate 90%+ and CRIT DMG 90%+.",
  "파괴 4세트 착용 시 권장 치명타 확률 80% 이상, 치명타 피해 140% 이상":
    "Destruction Set (4) — Recommended: CRIT Rate 80%+ and CRIT DMG 140%+.",
  "적중 2세트 착용 시 권장 효과적중 140% 이상":
    "Hit Set (2) — Recommended: Effect Hit 140%+.",
  "치명타 확률 + 치명타 피해의 합이": "If CRIT Rate + CRIT DMG totals",
  "※ 속도 수치가 높을 시 0.5티어 상승.": "※ High SPD can raise the equipment rating by 0.5 tier."
});
Object.assign(I18N_DATA.ui.ja, {
  "통찰 4세트 착용 시 권장 치명타 확률 90% 이상, 치명타 피해 90% 이상":
    "洞察セット(4)装備時の推奨：会心率90%以上、会心ダメージ90%以上",
  "파괴 4세트 착용 시 권장 치명타 확률 80% 이상, 치명타 피해 140% 이상":
    "破壊セット(4)装備時の推奨：会心率80%以上、会心ダメージ140%以上",
  "적중 2세트 착용 시 권장 효과적중 140% 이상":
    "的中セット(2)装備時の推奨：効果命中140%以上",
  "치명타 확률 + 치명타 피해의 합이": "会心率＋会心ダメージの合計が",
  "※ 속도 수치가 높을 시 0.5티어 상승.": "※ 速度が高い場合、0.5 Tier上昇。"
});
Object.assign(I18N_DATA.terms.en, {
  "치명타 확률(%)": "CRIT Rate (%)",
  "치명타 피해(%)": "CRIT DMG (%)",
  "효과적중(%), 효과저항(%)": "Effect Hit (%), Effect RES (%)"
});
Object.assign(I18N_DATA.terms.ja, {
  "치명타 확률(%)": "会心率(%)",
  "치명타 피해(%)": "会心ダメージ(%)",
  "효과적중(%), 효과저항(%)": "効果命中(%), 効果耐性(%)"
});


// ESPR 출처 표기 다국어
Object.assign(I18N_DATA.ui.en, {
  "구원자 정보는 ": "Savior information references ",
  "에크하르트 초월지식 학회(ESPR)": "Eckhart's Society for Preternatural Research (ESPR)",
  "를 참고합니다.": "."
});
Object.assign(I18N_DATA.ui.ja, {
  "구원자 정보는 ": "救援者情報は、",
  "에크하르트 초월지식 학회(ESPR)": "エクハルト超越知識学会（ESPR）",
  "를 참고합니다.": "を参考にしています。"
});

// 이름 렌더링에 사용하는 접근성 문구
Object.assign(I18N_DATA.ui.en, {
  "스킬설명 및 상세정보": "Skills & Details",
  "상세정보를 불러오는 중입니다.": "Loading backed-up Savior details.",
  "상세정보 백업 데이터를 불러올 수 없습니다.": "The backed-up Savior details could not be loaded.",
  "상세정보 펼치기": "Expand details",
  "상세정보 접기": "Collapse details"
});
Object.assign(I18N_DATA.ui.ja, {
  "스킬설명 및 상세정보": "スキル説明・詳細情報",
  "상세정보를 불러오는 중입니다.": "バックアップ済みの救援者詳細を読み込んでいます。",
  "상세정보 백업 데이터를 불러올 수 없습니다.": "バックアップ済みの救援者詳細を読み込めませんでした。",
  "상세정보 펼치기": "詳細を開く",
  "상세정보 접기": "詳細を閉じる"
});
Object.assign(I18N_DATA.ui.en, {
  "개화": "Bloom",
  "개화 스킬을 불러오는 중입니다.": "Loading Bloom skill data.",
  "개화 스킬 백업 데이터를 불러올 수 없습니다.": "The backed-up Bloom skill data could not be loaded."
});
Object.assign(I18N_DATA.ui.ja, {
  "개화": "開花",
  "개화 스킬을 불러오는 중입니다.": "開花スキルデータを読み込んでいます。",
  "개화 스킬 백업 데이터를 불러올 수 없습니다.": "バックアップ済みの開花スキルデータを読み込めませんでした。"
});
Object.assign(I18N_DATA.ui.en, { "아르카나 상세정보": "Arcana details" });
Object.assign(I18N_DATA.ui.en, {
  "구원자 상세정보":"Savior Details","구원자 설명":"Savior Description","이름":"Name","등급":"Grade","유형":"Type",
  "생일":"Birthday","신장":"Height","출신":"Origin","소속":"Affiliation","CV (KR)":"CV (KR)","CV (JP)":"CV (JP)",
  "일러스트":"Illustration","일러스트 펼치기":"Expand illustration","일러스트 접기":"Collapse illustration",
  "기본 스테이터스":"Base Stats","LV.200 기준":"Lv.200","여정 스테이터스":"Journey Stats","공명 잠재력":"Resonance Potential",
  "레벨":"Level","스킬 정보":"Skill Information","스킬 레벨 정보":"Skill Level Information","스킬 레벨 설명":"Skill Level Description","노바 버스트":"Nova Burst"
});
Object.assign(I18N_DATA.ui.ja, {
  "구원자 상세정보":"救援者詳細情報","구원자 설명":"救援者説明","이름":"名前","등급":"レアリティ","유형":"タイプ",
  "생일":"誕生日","신장":"身長","출신":"出身","소속":"所属","CV (KR)":"CV（韓国語）","CV (JP)":"CV（日本語）",
  "일러스트":"イラスト","일러스트 펼치기":"イラストを開く","일러스트 접기":"イラストを閉じる",
  "기본 스테이터스":"基本ステータス","LV.200 기준":"Lv.200基準","여정 스테이터스":"旅程ステータス","공명 잠재력":"共鳴潜在力",
  "레벨":"レベル","스킬 정보":"スキル情報","스킬 레벨 정보":"スキルレベル情報","스킬 레벨 설명":"スキルレベル説明","노바 버스트":"ノヴァバースト"
});
// 상세 백업 원문에서 사용하는 공격 유형 표기 보정
Object.assign(I18N_DATA.terms.en, { "충격": "Impact", "원소": "Element" });
Object.assign(I18N_DATA.terms.ja, { "충격": "衝撃", "원소": "元素" });
Object.assign(I18N_DATA.ui.ja, { "아르카나 상세정보": "アルカナ詳細情報" });
// 스마일(보이저 구원단) 아르카나 대체 설명 다국어 보정
Object.assign(I18N_DATA.ui.en, {
  "종말은 소녀의 얼굴을 하고 있다. 대체": "Alternative to The End Wears the Face of a Girl",
  "허수의 개척자 대체": "Alternative to The Imaginary Pioneer"
});
Object.assign(I18N_DATA.ui.ja, {
  "종말은 소녀의 얼굴을 하고 있다. 대체": "『終末は少女の顔をしている』の代替",
  "허수의 개척자 대체": "『虚数の開拓者』の代替"
});
// 선샤인 캣 스마일 신규 세팅 문구 다국어 보정
Object.assign(I18N_DATA.ui.en, {
  "* 효과적중 150% 이상 권장": "* Effect Hit 150%+ recommended.",
  "단점 보완 맞춤 훈련 대체": "Alternative to Customized Training to Cover Weaknesses",
  "꽃들에게 죽음을 대체": "Alternative to Death for the Flowers",
  "허수의 개척자/불굴의 역작 대체": "Alternative to The Imaginary Pioneer / The Indomitable Masterpiece"
});
Object.assign(I18N_DATA.ui.ja, {
  "* 효과적중 150% 이상 권장": "* 効果命中150%以上推奨。",
  "단점 보완 맞춤 훈련 대체": "『弱点補完カスタムトレーニング』の代替",
  "꽃들에게 죽음을 대체": "『花々に死を』の代替",
  "허수의 개척자/불굴의 역작 대체": "『虚数の開拓者／不屈の傑作』の代替"
});
// 일본어 정식 표기 및 문장 번역 보정
Object.assign(I18N_DATA.ui.ja, {
  "구원자 정보는": "救援者情報は",
  "기준입니다.": "を基準としています。",
  "PVE장비 및 아르카나는": "PVE装備・アルカナは",
  "를 기준으로 합니다.": "を基準としています。",
  "통찰 4세트 착용 시 권장 치명타 확률 90% 이상, 치명타 피해 90% 이상": "洞察セット(4)装備時の推奨：会心率90%以上、会心ダメージ90%以上",
  "파괴 4세트 착용 시 권장 치명타 확률 80% 이상, 치명타 피해 140% 이상": "破壊セット(4)装備時の推奨：会心率80%以上、会心ダメージ140%以上",
  "적중 2세트 착용 시 권장 효과적중 140% 이상": "的中セット(2)装備時の推奨：効果命中140%以上",
  "착용 시 권장 치명타 확률 90% 이상, 치명타 피해 90% 이상": "装備時の推奨：会心率90%以上、会心ダメージ90%以上",
  "착용 시 권장 치명타 확률 80% 이상, 치명타 피해 140% 이상": "装備時の推奨：会心率80%以上、会心ダメージ140%以上",
  "착용 시 권장 효과적중 140% 이상": "装備時の推奨：効果命中140%以上",
  "치명타 확률 + 치명타 피해의 합이": "会心率＋会心ダメージの合計が",
  "13% 이상": "13%以上",
  "10% 이상 ~ 12% 미만": "10%以上～12%未満",
  "7% 이상 ~ 9% 미만": "7%以上～9%未満",
  "4% 이상 ~ 6% 미만": "4%以上～6%未満",
  "일 경우 0티어 장비.": "の場合、Tier 0装備。",
  "일 경우 1티어 장비.": "の場合、Tier 1装備。",
  "일 경우 2티어 장비.": "の場合、Tier 2装備。",
  "일 경우 3티어 장비.": "の場合、Tier 3装備。",
  "치명타 확률 + 치명타 피해의 합이 13% 이상일 경우 0티어 장비.": "会心率＋会心ダメージの合計が13%以上の場合、Tier 0装備。",
  "치명타 확률 + 치명타 피해의 합이 10% 이상 ~ 12% 미만일 경우 1티어 장비.": "会心率＋会心ダメージの合計が10%以上～12%未満の場合、Tier 1装備。",
  "치명타 확률 + 치명타 피해의 합이 7% 이상 ~ 9% 미만일 경우 2티어 장비.": "会心率＋会心ダメージの合計が7%以上～9%未満の場合、Tier 2装備。",
  "치명타 확률 + 치명타 피해의 합이 4% 이상 ~ 6% 미만일 경우 3티어 장비.": "会心率＋会心ダメージの合計が4%以上～6%未満の場合、Tier 3装備。"
});

Object.assign(I18N_DATA.terms.ja, {
  "무기": "武器",
  "장갑": "手袋",
  "갑옷": "鎧",
  "신발": "靴",
  "단계": "段階",
  "공격력, 생명력, 방어력(%)": "攻撃力/HP/防御力(%)"
});


// 영어 정식 장비 표기 및 잔여 한글 문장 보정
Object.assign(I18N_DATA.ui.en, {
  "구원자 정보는": "Savior information uses",
  "기준입니다.": "as the source.",
  "PVE장비 및 아르카나는": "PVE equipment and Arcana use",
  "를 기준으로 합니다.": "as the source.",
  "1단계": "Stage 1",
  "2단계": "Stage 2",
  "3단계": "Stage 3",
  "4단계": "Stage 4",
  "5단계": "Stage 5",
  "6단계": "Stage 6",
  "통찰 4세트 착용 시 권장 치명타 확률 90% 이상, 치명타 피해 90% 이상": "Insight Set (4) — Recommended: CRIT Rate 90%+ and CRIT DMG 90%+.",
  "파괴 4세트 착용 시 권장 치명타 확률 80% 이상, 치명타 피해 140% 이상": "Destruction Set (4) — Recommended: CRIT Rate 80%+ and CRIT DMG 140%+.",
  "적중 2세트 착용 시 권장 효과적중 140% 이상": "Hit Set (2) — Recommended: Effect Hit 140%+.",
  "치명타 확률 + 치명타 피해의 합이": "If CRIT Rate + CRIT DMG totals",
  "13% 이상": "13% or more",
  "10% 이상 ~ 12% 미만": "10% or more but less than 12%",
  "7% 이상 ~ 9% 미만": "7% or more but less than 9%",
  "4% 이상 ~ 6% 미만": "4% or more but less than 6%",
  "일 경우 0티어 장비.": ", the item is Tier 0.",
  "일 경우 1티어 장비.": ", the item is Tier 1.",
  "일 경우 2티어 장비.": ", the item is Tier 2.",
  "일 경우 3티어 장비.": ", the item is Tier 3.",
  "치명타 확률 + 치명타 피해의 합이 13% 이상일 경우 0티어 장비.": "If CRIT Rate + CRIT DMG totals 13% or more, the item is Tier 0.",
  "치명타 확률 + 치명타 피해의 합이 10% 이상 ~ 12% 미만일 경우 1티어 장비.": "If CRIT Rate + CRIT DMG totals 10% or more but less than 12%, the item is Tier 1.",
  "치명타 확률 + 치명타 피해의 합이 7% 이상 ~ 9% 미만일 경우 2티어 장비.": "If CRIT Rate + CRIT DMG totals 7% or more but less than 9%, the item is Tier 2.",
  "치명타 확률 + 치명타 피해의 합이 4% 이상 ~ 6% 미만일 경우 3티어 장비.": "If CRIT Rate + CRIT DMG totals 4% or more but less than 6%, the item is Tier 3.",
  "적중(2)는 투지(2)로 대체가능.": "Hit Set (2) can be replaced with Valor Set (2).",
  "* 적중(2)는 투지(2)로 대체가능.": "* Hit Set (2) can be replaced with Valor Set (2)."
});

Object.assign(I18N_DATA.terms.en, {
  "무기": "Weapon",
  "장갑": "Gloves",
  "갑옷": "Armor",
  "신발": "Shoes",
  "공격력 증가율(%)": "ATK(%)",
  "생명력 증가율(%)": "HP(%)",
  "방어력 증가율(%)": "DEF(%)",
  "효과적중": "Effect Hit",
  "공격력, 생명력, 방어력(%)": "ATK, HP, DEF(%)",
  "적중&저항": "Effect Hit & Effect RES",
  "속도 세트": "Speed Set",
  "방어 세트": "Defense Set",
  "적중 세트": "Hit Set",
  "저항 세트": "Resistance Set",
  "공격 세트": "Attack Set",
  "통찰 세트": "Insight Set",
  "투지 세트": "Valor Set",
  "정밀 세트": "Precision Set",
  "생명 세트": "Health Set",
  "파괴 세트": "Destruction Set",
  "장벽 세트": "Barrier Set",
  "섬멸 세트": "Annihilation Set",
  "속도(4)": "Speed Set (4)",
  "방어(2)": "Defense Set (2)",
  "방어(4)": "Defense Set (4)",
  "저항(2)": "Resistance Set (2)",
  "공격(4)": "Attack Set (4)",
  "통찰(4)": "Insight Set (4)",
  "적중(2)": "Hit Set (2)",
  "투지(2)": "Valor Set (2)",
  "정밀(4)": "Precision Set (4)",
  "생명(4)": "Health Set (4)",
  "파괴(4)": "Destruction Set (4)",
  "장벽(2)": "Barrier Set (2)",
  "섬멸(2)": "Annihilation Set (2)",
  "통찰 4세트": "Insight Set (4)",
  "파괴 4세트": "Destruction Set (4)",
  "적중 2세트": "Hit Set (2)",
  "방퍼": "DEF(%)"
});





// 여정 스탯 우선순위 다국어 표시
Object.assign(I18N_DATA.ui.en, {
  "여정 스탯 우선순위": "Journey Stat Priority",
  "※ 퓨어탱커": "※ Pure Tank",
  "※ 공격력 탱커": "※ ATK Tank",
  "- 이터널 프로미스 카르멘 없을시 사용불가": "- Unusable without Eternal Promise Carmen"
});
Object.assign(I18N_DATA.ui.ja, {
  "여정 스탯 우선순위": "旅程ステータス優先順位",
  "※ 퓨어탱커": "※ 純粋タンク",
  "※ 공격력 탱커": "※ 攻撃型タンク",
  "- 이터널 프로미스 카르멘 없을시 사용불가": "- エターナルプロミス カルメンがいない場合は使用不可"
});
Object.assign(I18N_DATA.terms.en, {
  "힘": "Strength",
  "체력": "Vitality",
  "인내": "Endurance",
  "집중": "Focus",
  "보호": "Protection"
});
Object.assign(I18N_DATA.terms.ja, {
  "힘": "力",
  "체력": "体力",
  "인내": "忍耐",
  "집중": "集中",
  "보호": "保護"
});

// 보이저 구원단 루나 PVE 세팅 다국어 보정
Object.assign(I18N_DATA.ui.en, {
  "속도 or 공격력%": "Speed or ATK%"
});

Object.assign(I18N_DATA.ui.ja, {
  "속도 or 공격력%": "速度 または 攻撃力(%)"
});


// 여정 스탯 우선순위 다국어 표시
Object.assign(I18N_DATA.ui.en, {
  "여정 스탯 우선순위": "Journey Stat Priority"
});
Object.assign(I18N_DATA.ui.ja, {
  "여정 스탯 우선순위": "旅程ステータス優先順位"
});
Object.assign(I18N_DATA.terms.en, {
  "힘": "Strength",
  "체력": "HP",
  "인내": "Endurance",
  "집중": "Focus",
  "보호": "Protection"
});
Object.assign(I18N_DATA.terms.ja, {
  "힘": "力",
  "체력": "体力",
  "인내": "忍耐",
  "집중": "集中",
  "보호": "保護"
});


// 디펜더 공통/전용 세팅 다국어 보정
Object.assign(I18N_DATA.ui.en, {
  "퓨어탱커": "Pure Tank",
  "공격탱커": "ATK Tank",
  "※ 퓨어탱커, EX": "※ Pure Tank, EX",
  "※ 공격탱커(AX)": "※ ATK Tank (AX)",
  "※ 퓨어탱커(BX)": "※ Pure Tank (BX)",
  "※ 퓨어탱커(CX)": "※ Pure Tank (CX)",
  "※ 퓨어탱커": "※ Pure Tank",
  "※ EX": "※ EX",
  "※ EX 전용": "※ EX only",
  "※ 공격력 탱커는 단점 보완 맞춤 훈련 대체불가": "※ ATK Tanks cannot replace Customized Training to Cover Weaknesses",
  "하얀 달의 온기는 햇빛처럼 대체": "Substitute for A White Moon Shines With the Sun's Warmth",
  "누각 위, 유리달 맞이 대체": "Substitute for Welcoming the Glass Moon Above the Pavilion",
  "공격의 재능 용도로 사용하나 인자 만드는걸 추천": "Can be used for Attack Talent, but creating an inheritance factor is recommended",
  "단점 보완 맞춤 훈련은 절대 대체불가합니다": "Customized Training to Cover Weaknesses must never be replaced",
  "하얀 달의 온기는 햇빛처럼/불굴의 역작 대체": "Substitute for A White Moon Shines With the Sun's Warmth / The Indomitable Masterpiece",
  "완벽한 바니걸/하늘의 시련/노스텔지어의 역습 대체": "Substitute for The Perfect Bunny Girl / Trial of the Sky / Nostalgia Strikes Back"
});
Object.assign(I18N_DATA.ui.ja, {
  "퓨어탱커": "純粋タンク",
  "공격탱커": "攻撃型タンク",
  "※ 퓨어탱커, EX": "※ 純粋タンク、EX",
  "※ 공격탱커(AX)": "※ 攻撃型タンク(AX)",
  "※ 퓨어탱커(BX)": "※ 純粋タンク(BX)",
  "※ 퓨어탱커(CX)": "※ 純粋タンク(CX)",
  "※ 퓨어탱커": "※ 純粋タンク",
  "※ EX": "※ EX",
  "※ EX 전용": "※ EX専用",
  "※ 공격력 탱커는 단점 보완 맞춤 훈련 대체불가": "※ 攻撃型タンクは弱点補完カスタムトレーニングを代替不可",
  "하얀 달의 온기는 햇빛처럼 대체": "「白い月のぬくもりは陽光のように」の代替",
  "누각 위, 유리달 맞이 대체": "「楼閣の上、硝子月を迎えて」の代替",
  "공격의 재능 용도로 사용하나 인자 만드는걸 추천": "攻撃の才能用途でも使用できますが、因子作成を推奨します",
  "단점 보완 맞춤 훈련은 절대 대체불가합니다": "弱点補完カスタムトレーニングは絶対に代替不可です",
  "하얀 달의 온기는 햇빛처럼/불굴의 역작 대체": "「白い月のぬくもりは陽光のように／不屈の傑作」の代替",
  "완벽한 바니걸/하늘의 시련/노스텔지어의 역습 대체": "「完璧なバニーガール／空の試練／ノスタルジアの逆襲」の代替",
  "꽃들에게 죽음을 대체": "「花々に死を」の代替"
});
Object.assign(I18N_DATA.terms.en, {
  "효과적중%": "Effect Hit%",
  "방어(6)": "Defense(6)"
});
Object.assign(I18N_DATA.terms.ja, {
  "효과적중%": "効果命中%",
  "방어(6)": "防御セット(6)"
});

// 왈츠 오브 스타라이트 아세라 PVE 세팅 다국어 보정
Object.assign(I18N_DATA.ui.en, {
  "공격력% or 생명력%": "ATK% or HP%",
  "장벽(2)는 투지(2)로 대체가능.": "Barrier Set (2) can be replaced with Valor Set (2).",
  "단점 보완 맞춤 훈련 대체": "Substitute for Customized Training to Cover Weaknesses",
  "완벽한 바니걸 대체": "Substitute for The Perfect Bunny Girl",
  "하얀 달의 온기는 햇빛처럼 대체": "Substitute for A White Moon Shines With the Sun's Warmth",
  "꽃들에게 죽음을 대체": "Substitute for Death for the Flowers"
});

Object.assign(I18N_DATA.ui.ja, {
  "공격력% or 생명력%": "攻撃力(%) または HP(%)",
  "장벽(2)는 투지(2)로 대체가능.": "防壁セット(2)は闘志セット(2)で代用可能です。",
  "단점 보완 맞춤 훈련 대체": "弱点補完カスタムトレーニングの代替",
  "완벽한 바니걸 대체": "完璧なバニーガールの代替",
  "하얀 달의 온기는 햇빛처럼 대체": "白い月のぬくもりは陽光のようにの代替",
  "꽃들에게 죽음을 대체": "花々に死をの代替"
});

// v51: 크리스텔 / 영원 속박의 굴레 다국어 표시
Object.assign(I18N_DATA.saviorNames.en, {
  "크리스텔": "Cristelle"
});
Object.assign(I18N_DATA.saviorNames.ja, {
  "크리스텔": "クリステル"
});
Object.assign(I18N_DATA.subtitles.en, {
  "모렐해운상회": "Morrel Ocean Traders"
});
Object.assign(I18N_DATA.subtitles.ja, {
  "모렐해운상회": "モレル海運商会"
});
Object.assign(I18N_DATA.arcana.en, {
  "영원 속박의 굴레": "Bound for Eternity"
});
Object.assign(I18N_DATA.arcana.ja, {
  "영원 속박의 굴레": "永遠なる束縛の連鎖"
});
Object.assign(I18N_DATA.ui.en, {
  "PVE 장비·아르카나 세팅을 반영했습니다.": "PVE equipment and Arcana setup has been applied.",
  "투지(2)는 적중(2)로 대체가능.": "Valor Set (2) can be replaced with Hit Set (2).",
  "하얀 달의 온기는 햇빛처럼/완벽한 바니걸 대체": "Alternative to A White Moon Shines With the Sun's Warmth / The Perfect Bunny Girl",
  "단점 맞춤 훈련 대체": "Alternative to Customized Training to Cover Weaknesses",
  "영원 속박의 굴레 대체": "Alternative to Bound for Eternity",
  "하얀 달의 온기는 햇빛처럼 대체": "Alternative to A White Moon Shines With the Sun's Warmth"
});
Object.assign(I18N_DATA.ui.ja, {
  "PVE 장비·아르카나 세팅을 반영했습니다.": "PVE装備・アルカナ設定を反映しました。",
  "투지(2)는 적중(2)로 대체가능.": "闘志セット(2)は的中セット(2)で代用可能です。",
  "하얀 달의 온기는 햇빛처럼/완벽한 바니걸 대체": "「白い月のぬくもりは陽光のように／完璧なバニーガール」の代替",
  "단점 맞춤 훈련 대체": "「弱点補完カスタムトレーニング」の代替",
  "영원 속박의 굴레 대체": "「永遠なる束縛の連鎖」の代替",
  "하얀 달의 온기는 햇빛처럼 대체": "「白い月のぬくもりは陽光のように」の代替"
});
// v54: 크리스텔 장비 세팅 안내 다국어 표시
Object.assign(I18N_DATA.ui.en, {
  "본인 조합과 세팅에 따라 다르나 속도 권장.": "Depends on your team composition and setup, but SPD is recommended."
});
Object.assign(I18N_DATA.ui.ja, {
  "본인 조합과 세팅에 따라 다르나 속도 권장.": "編成やセッティングによって異なりますが、速度を推奨します。"
});
// v55: 아모라 신규 구원자 표시
Object.assign(I18N_DATA.saviorNames.en, { "아모라": "Amora" });
Object.assign(I18N_DATA.saviorNames.ja, { "아모라": "アモラ" });
Object.assign(I18N_DATA.subtitles.en, { "스트라니스 백작가": "House Stranis" });
Object.assign(I18N_DATA.subtitles.ja, { "스트라니스 백작가": "ストラニス伯爵家" });
Object.assign(I18N_DATA.arcana.en, { "귀로 없는 여정": "Journey of No Return" });
Object.assign(I18N_DATA.arcana.ja, { "귀로 없는 여정": "帰路なき旅程" });
Object.assign(I18N_DATA.arcana.en, { "한여름밤의 하늘": "A Midsummer Night's Sky" });
Object.assign(I18N_DATA.arcana.ja, { "한여름밤의 하늘": "夏の夜の空" });
Object.assign(I18N_DATA.ui.en, { "특정 아르카나 부족 시 대체": "Substitute when certain Arcana are unavailable" });
Object.assign(I18N_DATA.ui.ja, { "특정 아르카나 부족 시 대체": "特定のアルカナが不足している場合の代替" });

Object.assign(I18N_DATA.ui.en, {
  "AX5 - 치명타 확률이 부족한 경우": "AX5 - When CRIT Rate is insufficient",
  "AX6 - 치명타 확률이 95% 이상인 경우": "AX6 - When CRIT Rate is 95% or higher",
  "AX1 - 공격력% 효율이 높은 구원자": "AX1 - Saviors with high ATK% efficiency",
  "AX6 - 패시브 효과로 치명타 확률보다 치명타 피해 효율이 높은 구원자": "AX6 - Saviors whose passive makes CRIT DMG more efficient than CRIT Rate",
  "※ AX1은 공격력% 효율이 높거나, 공격력을 가장 높게 맞춰야 하는 경우 사용합니다.": "※ Use AX1 when ATK% is highly efficient or when ATK must be set as the highest stat.",
  "AX1 / XX2 (생명력 흡수)": "AX1 / XX2 (Life Steal)"
});
Object.assign(I18N_DATA.ui.ja, {
  "AX5 - 치명타 확률이 부족한 경우": "AX5 - 会心率が不足している場合",
  "AX6 - 치명타 확률이 95% 이상인 경우": "AX6 - 会心率が95%以上の場合",
  "AX1 - 공격력% 효율이 높은 구원자": "AX1 - 攻撃力(%)効率が高い救援者",
  "AX6 - 패시브 효과로 치명타 확률보다 치명타 피해 효율이 높은 구원자": "AX6 - パッシブ効果により会心率より会心ダメージ効率が高い救援者",
  "※ AX1은 공격력% 효율이 높거나, 공격력을 가장 높게 맞춰야 하는 경우 사용합니다.": "※ AX1は攻撃力(%)効率が高い場合、または攻撃力を最も高くする必要がある場合に使用します。",
  "AX1 / XX2 (생명력 흡수)": "AX1 / XX2 (生命力吸収)"
});

const ORIGINAL_TEXT_NODES = new WeakMap();
const ORIGINAL_ATTRIBUTES = new WeakMap();

function readSavedLanguage() {
  try {
    const value = localStorage.getItem(LANGUAGE_STORAGE_KEY);
    return SUPPORTED_LANGUAGES.includes(value) ? value : null;
  } catch {
    return null;
  }
}

function saveLanguage(language) {
  try {
    localStorage.setItem(LANGUAGE_STORAGE_KEY, language);
  } catch {
    // 저장이 제한된 환경에서는 현재 세션에만 적용합니다.
  }
}

let currentLanguage = readSavedLanguage() || "ko";

function getLocalizedSaviorName(name, language = currentLanguage) {
  if (language === "ko") return name;
  return I18N_DATA.saviorNames[language]?.[name] || name;
}

function getLocalizedSubtitle(value, language = currentLanguage) {
  if (language === "ko") return value;
  return I18N_DATA.subtitles[language]?.[value]
    || I18N_DATA.subtitles.en?.[value]
    || value;
}

function getLocalizedArcanaName(name, language = currentLanguage) {
  if (language === "ko") return name;
  return I18N_DATA.arcana[language]?.[name] || name;
}

function translateString(value, language = currentLanguage) {
  const source = String(value ?? "");
  if (language === "ko" || !source) return source;

  const leading = source.match(/^\s*/)?.[0] || "";
  const trailing = source.match(/\s*$/)?.[0] || "";
  const core = source.slice(leading.length, source.length - trailing.length || source.length);
  if (!core) return source;

  const uiMap = I18N_DATA.ui[language] || {};
  if (Object.prototype.hasOwnProperty.call(uiMap, core)) {
    return leading + uiMap[core] + trailing;
  }

  const exactSavior = I18N_DATA.saviorNames[language]?.[core];
  if (exactSavior) return leading + exactSavior + trailing;

  const exactSubtitle = I18N_DATA.subtitles[language]?.[core];
  if (exactSubtitle) return leading + exactSubtitle + trailing;

  const exactArcana = I18N_DATA.arcana[language]?.[core];
  if (exactArcana) return leading + exactArcana + trailing;

  const replaceFromMaps = [
    I18N_DATA.arcana[language],
    I18N_DATA.subtitles[language],
    I18N_DATA.saviorNames[language],
    I18N_DATA.ui[language],
    I18N_DATA.terms[language]
  ].filter(Boolean);

  let translated = core;
  replaceFromMaps.forEach((map) => {
    Object.entries(map)
      .sort((a, b) => b[0].length - a[0].length)
      .forEach(([from, to]) => {
        if (from && translated.includes(from)) translated = translated.split(from).join(to);
      });
  });

  return leading + translated + trailing;
}

function translateTextNode(node) {
  if (!ORIGINAL_TEXT_NODES.has(node)) {
    ORIGINAL_TEXT_NODES.set(node, node.nodeValue);
  }
  node.nodeValue = translateString(ORIGINAL_TEXT_NODES.get(node));
}

function translateElementAttributes(element) {
  if (element.matches?.("#language-select, #language-select option")) return;

  const watched = ["aria-label", "placeholder", "title"];
  let saved = ORIGINAL_ATTRIBUTES.get(element);
  if (!saved) {
    saved = {};
    watched.forEach((name) => {
      if (element.hasAttribute?.(name)) saved[name] = element.getAttribute(name);
    });
    ORIGINAL_ATTRIBUTES.set(element, saved);
  }

  Object.entries(saved).forEach(([name, original]) => {
    element.setAttribute(name, translateString(original));
  });
}

function applyLanguageToDOM(root = document.body) {
  if (!root) return;

  const applyNamedLocalization = (selector, resolver) => {
    const nodes = [];
    if (root.nodeType === Node.ELEMENT_NODE && root.matches?.(selector)) nodes.push(root);
    root.querySelectorAll?.(selector).forEach((node) => nodes.push(node));
    nodes.forEach((node) => {
      const sourceName = node.dataset.i18nSource || "";
      if (sourceName) node.textContent = resolver(sourceName);
    });
  };

  applyNamedLocalization("[data-i18n-kind='savior']", (name) => getLocalizedSaviorName(name));
  applyNamedLocalization("[data-i18n-kind='arcana']", (name) => getLocalizedArcanaName(name));
  applyNamedLocalization("[data-i18n-kind='subtitle']", (name) => getLocalizedSubtitle(name));

  if (root.nodeType === Node.ELEMENT_NODE) translateElementAttributes(root);

  const walker = document.createTreeWalker(
    root,
    NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT,
    {
      acceptNode(node) {
        if (node.nodeType === Node.ELEMENT_NODE) {
          if (node.matches?.("script, style, #language-select, #language-select *")) {
            return NodeFilter.FILTER_REJECT;
          }
          return NodeFilter.FILTER_ACCEPT;
        }
        if (node.nodeType === Node.TEXT_NODE) {
          const parent = node.parentElement;
          if (!parent || parent.closest("script, style, #language-select")) return NodeFilter.FILTER_REJECT;
          return /[가-힣]/.test(node.nodeValue || "") || ORIGINAL_TEXT_NODES.has(node)
            ? NodeFilter.FILTER_ACCEPT
            : NodeFilter.FILTER_SKIP;
        }
        return NodeFilter.FILTER_SKIP;
      }
    }
  );

  let node = walker.currentNode;
  while (node) {
    if (node.nodeType === Node.ELEMENT_NODE) translateElementAttributes(node);
    if (node.nodeType === Node.TEXT_NODE) translateTextNode(node);
    node = walker.nextNode();
  }

  refreshEquipmentSetLabels(root);
  refreshArcanaPreviews(root);
}

function refreshLanguageChrome() {
  document.documentElement.lang = LANGUAGE_HTML_CODES[currentLanguage] || "ko-KR";
  const languageSelect = document.querySelector("#language-select");
  if (languageSelect) {
    languageSelect.value = currentLanguage;
    languageSelect.setAttribute("aria-label", currentLanguage === "ko" ? "언어 변경" :
      currentLanguage === "ja" ? "言語を変更" : "Change language");
  }

  const titles = {
    ko: "스타세이비어 구원자 가이드 DB",
    en: "Star Savior Guide DB",
    ja: "Star Savior 救援者ガイドDB"
  };
  document.title = titles[currentLanguage] || titles.ko;

  const descriptions = {
    ko: "스타세이비어 구원자별 PVE 장비와 아르카나 조합을 확인하는 비공식 가이드 데이터베이스",
    en: "Unofficial Star Savior guide database for PVE equipment and Arcana setups by Savior.",
    ja: "Star Saviorの救援者別PVE装備・アルカナ構成を確認できる非公式ガイドDB。"
  };
  document.querySelector('meta[name="description"]')?.setAttribute("content", descriptions[currentLanguage] || descriptions.ko);
}

function setLanguage(language, options = {}) {
  const selected = SUPPORTED_LANGUAGES.includes(language) ? language : "ko";
  currentLanguage = selected;
  if (!options.skipSave) saveLanguage(selected);
  refreshLanguageChrome();
  renderList();
  applyLanguageToDOM(document.body);
  refreshLoadedSaviorSourcePanels();
  updateJourneyArchiveLanguage();
  updateArcanaDatabaseLanguage();
  // 테마 버튼의 현재 상태에 맞는 접근성 라벨을 선택 언어로 갱신합니다.
  if (typeof applyTheme === "function") {
    applyTheme(document.documentElement.dataset.theme || "dark", { skipSave: true });
  }
}

// 여정 로컬 아카이브 UI 다국어
Object.assign(I18N_DATA.ui.en, {
  "아르카나": "Arcana",
  "여정": "Journey",
  "여정 데이터는 우리 저장소에 백업된 로컬 사본만 사용합니다.": "Journey data uses only the local archive stored in this repository.",
  "원본 사이트에 연결하지 않습니다.": "No connection to the original site is required."
});
Object.assign(I18N_DATA.ui.ja, {
  "아르카나": "アルカナ",
  "여정": "旅程",
  "여정 데이터는 우리 저장소에 백업된 로컬 사본만 사용합니다.": "旅程データは、このリポジトリに保存したローカルアーカイブのみを使用します。",
  "원본 사이트에 연결하지 않습니다.": "元サイトへの接続は不要です。"
});
const ELEMENT_LABELS = {
  sun: "태양",
  moon: "달",
  star: "별",
  order: "질서",
  chaos: "혼돈"
};


const SAVIOR_DETAIL_ROOT = "https://star-savior-arcana-db.pages.dev/savior";
const ARCANA_IMAGE_ROOT = "./images/arcana";
const LOCAL_ARCANA_CARD_ROOT = "./data/arcana-assets/cards";
const EQUIPMENT_SET_IMAGE_ROOT = "./data/EQUIPMENT";
const EQUIPMENT_SET_IMAGE_NAMES = new Set([
  "공격",
  "방어",
  "생명",
  "섬멸",
  "속도",
  "장벽",
  "저항",
  "적중",
  "정밀",
  "통찰",
  "투지",
  "파괴"
]);

const SAVIOR_DETAIL_IDS = {
  "ceres-sun-supporter": 1059,
  "lydia-moon-caster": 1060,
  "gwen": 1040,
  "asherah-voyager": 1001,
  "smile": 1002,
  "luna": 1003,
  "carnelia": 1005,
  "bell": 1008,
  "emily": 1009,
  "charlotte": 1010,
  "carmen": 1011,
  "frey": 1013,
  "seira": 1014,
  "trish": 1015,
  "lyn": 1016,
  "cristelle": 1017,
  "haydee": 1018,
  "serpang": 1019,
  "dana": 1021,
  "muriel": 1023,
  "elisa": 1024,
  "tyria": 1025,
  "roberta": 1026,
  "lugh": 1027,
  "fei": 1029,
  "epindel": 1030,
  "omega": 1031,
  "bunny-charlotte": 1032,
  "ceres": 1033,
  "lydia": 1034,
  "harley": 1041,
  "petra": 1042,
  "scarlet": 1043,
  "claire": 1044,
  "lacy": 1049,
  "tanya": 1051,
  "lily": 1052,
  "kyra": 1053,
  "waltz-asherah": 1054,
  "wedding-carmen": 1055,
  "wedding-epindel": 1056,
  "bunny-frey": 1057,
  "white-pearl-luna": 1045,
  "sunshine-cat-smile": 1046,
  "besta": 1501,
  "annah": 1502,
  "marcille": 1506,
  "naru": 1508,
  "bunny-claire": 1509,
  "vera": 1507,
  "bunny-scarlet": 1510,
  "clarissa": 1511,
  "hilde": 3001,
  "yoo-mina": 3002,
  "rosaria": 3003,
  "professor-m": 1039
};

// 원본 DB에서 개화 토글로 스킬 설명이 변경되는 구원자.
// 신규 개화 구원자는 이 목록에 상세 ID만 추가하면 백업 Action이 자동으로 수집한다.
const SAVIOR_BLOOM_DETAIL_IDS = {
  "besta": 1501,
  "annah": 1502,
  "marcille": 1506,
  "vera": 1507,
  "naru": 1508,
  "bunny-claire": 1509,
  "bunny-scarlet": 1510,
  "clarissa": 1511
};
const SAVIOR_BLOOM_DETAIL_ID_SET = new Set(Object.values(SAVIOR_BLOOM_DETAIL_IDS));

const ARCANA_DETAIL_IDS = {
  "단점 보완 맞춤 훈련": 7102501,
  "꽃들에게 죽음을": 7100501,
  "하늘의 심판": 7102301,
  "죽음이 둘을 갈라놓을 때까지": 7105601,
  "불굴의 역작": 7105701,
  "하얀 달의 온기는 햇빛처럼": 7101602,
  "누각 위, 유리달 맞이": 7101601,
  "조용한 휴식 시간": 7100901,
  "스트라니스의 영애": 7105401,
  "완벽한 바니걸": 7104401,
  "키라만큼 귀여워!": 7105301,
  "오늘의 한 걸음": 7102901,
  "나른한 오후의 틈새": 7105501,
  "공녀, 왕좌에 오르다": 7101301,
  "본 투 비 와일드": 7104101,
  "허수의 개척자": 7103101,
  "종말은 소녀의 얼굴을 하고 있다.": 7300301,
  "깊은 애도": 7100801,
  "노스텔지어의 역습": 7300101,
  "하늘의 시련": 7102401,
  "금단의 기록물 Vol. 1": 7040101,
  "금단의 기록물": 7040101,
  "만족스러운 식사": 7150101,
  "어느 한 기사의 맹세": 7101001,
  "서투른 욕망 해소법": 7103201,
  "노 페인, 노 게인": 7104901,
  "메이드 바이 페트라♡": 7104201,
  "별을 보며 꿈을": 7150801,
  "음독의 각오": 7103302,
  "누구보다 프로페셔널": 7150701,
  "서류 더미 위의 책임감": 7102601,
  "언더커버 캅": 7150201,
  "빛을 쫓아라!": 7100301,
  "빛을 쫓아라": 7100301,
  "휴가 준비는 쇼핑에서부터!": 7104601,
  "영원 속박의 굴레": 7101701,
  "탐닉자의 유흥거리": 7103901,
  "자칭 베테랑 탐정의 수사법": 7104001,
  "이게 옷이라고요?": 7106001
};


// 아르카나 카드명은 사용자가 지정한 Star Savior Arcana DB의 한국어 표기를 사용합니다.
// 시트에서 사용하는 캐릭터/버전 약칭을 실제 카드명과 이미지로 연결합니다.
const ARCANA_LIBRARY = {
  "티리아": [
    { name: "단점 보완 맞춤 훈련", image: `${ARCANA_IMAGE_ROOT}/ARCANA_APOSTLE_TYRIA_SSR_01_S.webp` }
  ],
  "카넬리아": [
    { name: "꽃들에게 죽음을", image: `${ARCANA_IMAGE_ROOT}/ARCANA_MAID_LANTERN_SSR_01_S.webp` }
  ],
  "뮤리엘": [
    { name: "하늘의 심판", image: `${ARCANA_IMAGE_ROOT}/ARCANA_SAINTESS_DEMON_SSR_01_S.webp` }
  ],
  "웨딩 에핀델": [
    { name: "죽음이 둘을 갈라놓을 때까지", image: `${ARCANA_IMAGE_ROOT}/ARCANA_WEDDING_DUALSWORD_SSR_01_S.webp` }
  ],
  "바니걸 프레이": [
    { name: "불굴의 역작", image: `${ARCANA_IMAGE_ROOT}/ARCANA_BUNNY_PRAY_SSR_01_S.webp` }
  ],
  "린(인내)": [
    { name: "하얀 달의 온기는 햇빛처럼", image: `${ARCANA_IMAGE_ROOT}/ARCANA_EASTERN_SWORDMASTER_SSR_02_S.webp` }
  ],
  "린(힘)": [
    { name: "누각 위, 유리달 맞이", image: `${ARCANA_IMAGE_ROOT}/ARCANA_EASTERN_SWORDMASTER_SSR_01_S.webp` }
  ],
  "에밀리": [
    { name: "조용한 휴식 시간", image: `${ARCANA_IMAGE_ROOT}/ARCANA_MAID_TWOHANDER_SSR_01_S.webp` }
  ],
  "왈세라": [
    { name: "스트라니스의 영애", image: `${ARCANA_IMAGE_ROOT}/ARCANA_DRESS_STRANIS_SSR_01_S.webp` }
  ],
  "바니걸 클레어": [
    { name: "완벽한 바니걸", image: `${ARCANA_IMAGE_ROOT}/ARCANA_BUNNY_SPEAR_SSR_01_S.webp` }
  ],
  "키라": [
    { name: "키라만큼 귀여워!", image: `${ARCANA_IMAGE_ROOT}/ARCANA_MUTANT_MASK_SSR_01_S.webp` }
  ],
  "페이": [
    { name: "오늘의 한 걸음", image: `${ARCANA_IMAGE_ROOT}/ARCANA_INDEPENDENT_VAGABOND_SSR_01_S.webp` }
  ],
  "웨딩 카르멘": [
    { name: "나른한 오후의 틈새", image: `${ARCANA_IMAGE_ROOT}/ARCANA_WEDDING_SHIELDER_SSR_01_S.webp` }
  ],
  "프레이": [
    { name: "공녀, 왕좌에 오르다", image: `${ARCANA_IMAGE_ROOT}/ARCANA_KINGDOM_PRAY_SSR_01_S.webp` }
  ],
  "할리": [
    { name: "본 투 비 와일드", image: `${ARCANA_IMAGE_ROOT}/ARCANA_WILD_HOG_SSR_01_S.webp` }
  ],
  "오메가": [
    { name: "허수의 개척자", image: `${ARCANA_IMAGE_ROOT}/ARCANA_STARPIERCER_OMEGA_SSR_01_S.webp` }
  ],
  "로자리아": [
    { name: "종말은 소녀의 얼굴을 하고 있다.", image: `${ARCANA_IMAGE_ROOT}/ARCANA_COUNTERSIDE_ROSARIA_SSR_01_S.webp` }
  ],
  "벨리스": [
    { name: "깊은 애도", image: `${ARCANA_IMAGE_ROOT}/ARCANA_MAID_BELL_SSR_01_S.webp` }
  ],
  "힐데": [
    { name: "노스텔지어의 역습", image: `${ARCANA_IMAGE_ROOT}/ARCANA_COUNTERSIDE_HILDE_SSR_01_S.webp` }
  ],
  "엘리사": [
    { name: "하늘의 시련", image: `${ARCANA_IMAGE_ROOT}/ARCANA_SAINTESS_ELF_SSR_01_S.webp` }
  ],
  "베스타": [
    { name: "금단의 기록물 Vol. 1", image: `${ARCANA_IMAGE_ROOT}/ARCANA_APRIL_FOOL_SSR_01_S.webp` },
    { name: "만족스러운 식사", image: `${ARCANA_IMAGE_ROOT}/ARCANA_WEST_LANCER_SSR_01_S.webp` }
  ],
  "샤를": [
    { name: "어느 한 기사의 맹세", image: `${ARCANA_IMAGE_ROOT}/ARCANA_KINGDOM_KNIGHT_SSR_01_S.webp` }
  ],
  "바니걸 샤를": [
    { name: "서투른 욕망 해소법", image: `${ARCANA_IMAGE_ROOT}/ARCANA_BUNNY_KNIGHT_SSR_01_S.webp` }
  ],
  "단점 보완 맞춤 훈련": [
    { name: "단점 보완 맞춤 훈련", image: `${ARCANA_IMAGE_ROOT}/ARCANA_APOSTLE_TYRIA_SSR_01_S.webp` }
  ],
  "불굴의 역작": [
    { name: "불굴의 역작", image: `${ARCANA_IMAGE_ROOT}/ARCANA_BUNNY_PRAY_SSR_01_S.webp` }
  ],
  "꽃들에게 죽음을": [
    { name: "꽃들에게 죽음을", image: `${ARCANA_IMAGE_ROOT}/ARCANA_MAID_LANTERN_SSR_01_S.webp` }
  ],
  "완벽한 바니걸": [
    { name: "완벽한 바니걸", image: `${ARCANA_IMAGE_ROOT}/ARCANA_BUNNY_SPEAR_SSR_01_S.webp` }
  ],
  "하얀 달의 온기는 햇빛처럼": [
    { name: "하얀 달의 온기는 햇빛처럼", image: `${ARCANA_IMAGE_ROOT}/ARCANA_EASTERN_SWORDMASTER_SSR_02_S.webp` }
  ],
  "휴가 준비는 쇼핑에서부터!": [
    { name: "휴가 준비는 쇼핑에서부터!", image: "./images/arcana/휴가준비는쇼핑에서부터!.webp" }
  ],
  "노 페인, 노 게인": [
    { name: "노 페인, 노 게인", image: `${ARCANA_IMAGE_ROOT}/ARCANA_INDEPENDENT_DRAGON_SSR_01_S.webp` }
  ],
  "메이드 바이 페트라♡": [
    { name: "메이드 바이 페트라♡", image: `${ARCANA_IMAGE_ROOT}/ARCANA_CONSTRUCT_BOMB_SSR_01_S.webp` }
  ],
  "별을 보며 꿈을": [
    { name: "별을 보며 꿈을", image: `${ARCANA_IMAGE_ROOT}/ARCANA_NOA_OBSERVER_SSR_01_S.webp` }
  ],
  "어느 한 기사의 맹세": [
    { name: "어느 한 기사의 맹세", image: `${ARCANA_IMAGE_ROOT}/ARCANA_KINGDOM_KNIGHT_SSR_01_S.webp` }
  ],
  "음독의 각오": [
    { name: "음독의 각오", image: `${ARCANA_IMAGE_ROOT}/ARCANA_WEST_BEAMSWORD_SSR_02_S.webp` }
  ],
  "누구보다 프로페셔널": [
    { name: "누구보다 프로페셔널", image: `${ARCANA_IMAGE_ROOT}/ARCANA_LPU_POST_SSR_01_S.webp` }
  ],
  "서류 더미 위의 책임감": [
    { name: "서류 더미 위의 책임감", image: `${ARCANA_IMAGE_ROOT}/ARCANA_RECON_KNUCKLE_SSR_01_S.webp` }
  ],
  "언더커버 캅": [
    { name: "언더커버 캅", image: `${ARCANA_IMAGE_ROOT}/ARCANA_OFFICER_POLICE_SSR_01_S.webp` }
  ],
  "빛을 쫓아라!": [
    { name: "빛을 쫓아라!", image: `${ARCANA_IMAGE_ROOT}/ARCANA_VOYAGER_ORACLE_SSR_01_S.webp` }
  ],
  "종말은 소녀의 얼굴을 하고 있다.": [
    { name: "종말은 소녀의 얼굴을 하고 있다.", image: `${ARCANA_IMAGE_ROOT}/ARCANA_COUNTERSIDE_ROSARIA_SSR_01_S.webp` }
  ],
  "허수의 개척자": [
    { name: "허수의 개척자", image: `${ARCANA_IMAGE_ROOT}/ARCANA_STARPIERCER_OMEGA_SSR_01_S.webp` }
  ],
  "영원 속박의 굴레": [
    { name: "영원 속박의 굴레", image: "./images/arcana/영원속박의굴레.webp" }
  ]
};

// 구원자 세팅 카드도 독립 아르카나 탭과 같은 로컬 백업 이미지를 사용합니다.
// 기존 이미지 표기는 아래에서 전부 ID 기반 로컬 경로로 덮어씁니다.
Object.values(ARCANA_LIBRARY).flat().forEach((card) => {
  const detailId = ARCANA_DETAIL_IDS[card.name];
  card.detailId = detailId || null;
  card.image = detailId ? `${LOCAL_ARCANA_CARD_ROOT}/${detailId}.webp` : "";
});

ARCANA_LIBRARY["웨핀델"] = ARCANA_LIBRARY["웨딩 에핀델"];

// 약칭뿐 아니라 실제 카드명을 그대로 입력해도 이미지가 연결되도록 자동 별칭을 생성합니다.
Object.values(ARCANA_LIBRARY).flat().forEach((card) => {
  if (!ARCANA_LIBRARY[card.name]) {
    ARCANA_LIBRARY[card.name] = [card];
  }
});

// 표기 차이로 카드가 누락되지 않도록 상세 페이지와 동일한 별칭을 유지합니다.
ARCANA_LIBRARY["금단의 기록물"] = ARCANA_LIBRARY["금단의 기록물 Vol. 1"];
ARCANA_LIBRARY["빛을 쫓아라"] = ARCANA_LIBRARY["빛을 쫓아라!"];
ARCANA_LIBRARY["탐닉자의 유흥거리"] = [{
  name: "탐닉자의 유흥거리",
  detailId: 7103901,
  image: `${LOCAL_ARCANA_CARD_ROOT}/7103901.webp`
}];
ARCANA_LIBRARY["자칭 베테랑 탐정의 수사법"] = [{
  name: "자칭 베테랑 탐정의 수사법",
  detailId: 7104001,
  image: `${LOCAL_ARCANA_CARD_ROOT}/7104001.webp`
}];
ARCANA_LIBRARY["이게 옷이라고요?"] = [{
  name: "이게 옷이라고요?",
  detailId: 7106001,
  image: `${LOCAL_ARCANA_CARD_ROOT}/7106001.webp`
}];

// 신규 아르카나는 상세 ID가 아직 app.js에 하드코딩되지 않았더라도 이름부터 정상 표시합니다.
// 로컬 아르카나 백업이 갱신되면 아래 hydrate 함수가 실제 ID/카드 이미지로 자동 연결합니다.
if (!ARCANA_LIBRARY["귀로 없는 여정"]) {
  ARCANA_LIBRARY["귀로 없는 여정"] = [
    {
      name: "귀로 없는 여정",
      image: "",
      detailId: null
    }
  ];
}

function hydrateArcanaRecommendationLibrary(archive) {
  const arcanas = Array.isArray(archive?.arcanas) ? archive.arcanas : [];

  arcanas.forEach((arcana) => {
    const name = typeof arcana?.name === "string"
      ? arcana.name
      : (arcana?.name?.ko || "");
    const id = Number(arcana?.id);

    if (!name || !Number.isFinite(id)) return;

    ARCANA_DETAIL_IDS[name] = id;
    const card = {
      name,
      detailId: id,
      image: `${LOCAL_ARCANA_CARD_ROOT}/${id}.webp`
    };

    if (ARCANA_LIBRARY[name]?.length) {
      ARCANA_LIBRARY[name] = ARCANA_LIBRARY[name].map((existing) =>
        existing?.name === name ? { ...existing, ...card } : existing
      );
    } else {
      ARCANA_LIBRARY[name] = [card];
    }
  });
}

const COMMON_ARCANA_SLOTS = [
  { name: "단점 보완 맞춤 훈련", note: "" },
  { name: "불굴의 역작", note: "" },
  { name: "꽃들에게 죽음을", note: "" },
  { name: "완벽한 바니걸", note: "" },
  { name: "하얀 달의 온기는 햇빛처럼", note: "" }
];

const COMMON_ALTERNATIVE_ARCANA_SLOTS = [
  { name: "노 페인, 노 게인", note: "단점 보완 맞춤 훈련 대체" },
  { name: "메이드 바이 페트라♡", note: "꽃들에게 죽음을 대체" },
  { name: "별을 보며 꿈을", note: "꽃들에게 죽음을 대체" },
  { name: "어느 한 기사의 맹세", note: "하얀 달의 온기는 햇빛처럼 대체" },
  null
];


const DEFENDER_PURE_TANK_ARCANA = Object.freeze({
  recommended: [
    { name: "조용한 휴식 시간", note: "" },
    { name: "꽃들에게 죽음을", note: "" },
    { name: "한여름밤의 하늘", note: "" },
    { name: "본 투 비 와일드 or 언더커버 캅 or 만족스러운 식사", note: "" },
    { name: "하얀 달의 온기는 햇빛처럼", note: "" }
  ],
  alternatives: [
    { name: "어느 한 기사의 맹세", note: "하얀 달의 온기는 햇빛처럼 대체" },
    { name: "스트라니스의 영애 or 하늘의 시련 or 완벽한 바니걸", note: "특정 아르카나 부족 시 대체" }
  ]
});

const DEFENDER_ATTACK_TANK_ARCANA = Object.freeze({
  recommended: [
    { name: "단점 보완 맞춤 훈련", note: "" },
    { name: "누각 위, 유리달 맞이 or 하얀 달의 온기는 햇빛처럼", note: "" },
    { name: "조용한 휴식 시간", note: "" },
    { name: "대단하고 엄청난 바니걸", note: "" },
    { name: "꽃들에게 죽음을", note: "" }
  ],
  alternatives: [
    { name: "영원 속박의 굴레", note: "누각 위, 유리달 맞이 대체" },
    { name: "", note: "단점 보완 맞춤 훈련은 절대 대체불가합니다" }
  ]
});

// 로베르타를 제외하고, 승인된 스트라이커 9명에게만 아르카나 교체 규칙을 적용합니다.
const STRIKER_ARCANA_SWAP_IDS = new Set([
  "asherah-voyager",
  "charlotte",
  "seira",
  "lyn",
  "tyria",
  "ceres",
  "claire",
  "tanya",
  "bunny-scarlet"
]);

const EMPTY_ARCANA = () => Array.from({ length: 5 }, () => null);
const PENDING_ARCANA = () => Array.from({ length: 5 }, () => ({ name: "미정", note: "미정" }));

const DEFAULT_BUILD = {
  skills: [
    { label: "기본기", value: "미정" },
    { label: "특수기", value: "미정" },
    { label: "궁극기", value: "미정" }
  ],
  equipment: {
    pve: {
      necklace: "미정",
      ring: "미정",
      sets: ["미정"],
      potential: "미정",
      note: "미정"
    },
    pvp: {
      necklace: "미정",
      ring: "미정",
      sets: ["미정"],
      potential: "미정",
      note: "미정"
    }
  },
  arcana: {
    pve: PENDING_ARCANA(),
    pvp: PENDING_ARCANA(),
    alternatives: PENDING_ARCANA()
  },
  stats: [
    { name: "미정", target: "미정", reason: "미정", priority: "required", label: "미정" },
    { name: "미정", target: "미정", reason: "미정", priority: "recommended", label: "미정" },
    { name: "미정", target: "미정", reason: "미정", priority: "high", label: "미정" }
  ]
};


const GROWTH_PRIORITY = {
  "asherah-voyager": { tier: "3티어", level: "tier-3" },
  "smile": { tier: "1티어", level: "tier-1" },
  "luna": { tier: "1티어", level: "tier-1" },
  "carnelia": { tier: "2티어", level: "tier-2" },
  "bell": { tier: "1티어", level: "tier-1" },
  "emily": { tier: "0.5티어", level: "tier-05" },
  "charlotte": { tier: "3티어", level: "tier-3" },
  "carmen": { tier: "4티어", level: "tier-4" },
  "frey": { tier: "2티어", level: "tier-2" },
  "seira": { tier: "2티어", level: "tier-2" },
  "trish": { tier: "2티어", level: "tier-2" },
  "lyn": { tier: "2티어", level: "tier-2" },
  "cristelle": { tier: "1티어", level: "tier-1" },
  "haydee": { tier: "0.5티어", level: "tier-05", note: "1돌파 이상 필수" },
  "serpang": { tier: "2티어", level: "tier-2" },
  "dana": { tier: "2티어", level: "tier-2" },
  "muriel": { tier: "2티어", level: "tier-2" },
  "elisa": { tier: "2티어", level: "tier-2", note: "1돌파 이상 권장" },
  "tyria": { tier: "1티어", level: "tier-1" },
  "roberta": { tier: "1티어", level: "tier-1" },
  "lugh": { tier: "2티어", level: "tier-2" },
  "fei": { tier: "0.5티어", level: "tier-05" },
  "epindel": { tier: "3티어", level: "tier-3" },
  "omega": { tier: "3티어", level: "tier-3" },
  "bunny-charlotte": { tier: "0.5티어", level: "tier-05" },
  "ceres": { tier: "1티어", level: "tier-1", note: "1돌파 이상 권장" },
  "lydia": { tier: "2티어", level: "tier-2" },
  "harley": { tier: "2티어", level: "tier-2" },
  "petra": { tier: "2티어", level: "tier-2" },
  "scarlet": { tier: "3티어", level: "tier-3" },
  "claire": { tier: "1티어", level: "tier-1" },
  "lacy": { tier: "2티어", level: "tier-2" },
  "tanya": { tier: "3티어", level: "tier-3" },
  "lily": { tier: "3티어", level: "tier-3" },
  "kyra": { tier: "1티어", level: "tier-1" },
  "waltz-asherah": { tier: "0티어", level: "tier-0", note: "1돌파 이상 필수" },
  "wedding-carmen": { tier: "0티어", level: "tier-0", note: "한정" },
  "wedding-epindel": { tier: "1티어", level: "tier-1" },
  "bunny-frey": { tier: "1티어", level: "tier-1", note: "1돌파 이상 권장" },
  "besta": { tier: "3티어", level: "tier-3", note: "개화 필수" },
  "annah": { tier: "1티어", level: "tier-1", note: "개화 필수" },
  "marcille": { tier: "2티어", level: "tier-2", note: "개화 필수" },
  "vera": { tier: "2티어", level: "tier-2", note: "개화 필수" },
  "naru": { tier: "2티어", level: "tier-2", note: "개화 필수" },
  "bunny-claire": { tier: "2티어", level: "tier-2", note: "개화 필수" },
  "bunny-scarlet": { tier: "2티어", level: "tier-2", note: "개화 필수" },
  "clarissa": { tier: "0.5티어", level: "tier-05", note: "개화 필수" },
  "hilde": { tier: "3티어", level: "tier-3" },
  "yoo-mina": { tier: "3티어", level: "tier-3" },
  "rosaria": { tier: "1티어", level: "tier-1" },
  "white-pearl-luna": { tier: "1티어", level: "tier-1" },
  "sunshine-cat-smile": { tier: "0.5티어", level: "tier-05" },
  "amora": { tier: "0티어", level: "tier-0" },
  "professor-m": { tier: "0.5티어", level: "tier-05" }
};


const JOURNEY_STAT_ICON_URLS = Object.freeze({
  "힘": "./data/journey-assets/stat-force.webp",
  "체력": "./data/journey-assets/stat-hp.webp",
  "인내": "./data/journey-assets/stat-endurance.webp",
  "집중": "./data/journey-assets/stat-focus.webp",
  "보호": "./data/journey-assets/stat-protection.webp"
});

// 같은 내부 배열에 든 스탯끼리는 '='이며, 배열 사이에는 '>'가 들어간다.
const JOURNEY_STAT_PRIORITY_PATTERNS = Object.freeze({
  offenseCommon: [["힘"], ["체력", "인내"], ["집중", "보호"]],
  focusOffense: [["힘"], ["집중"], ["체력", "인내"], ["보호"]],
  defenderPure: [["체력", "인내"], ["힘"], ["집중", "보호"]],
  defenderAttack: [["힘"], ["체력"], ["인내"], ["집중", "보호"]],
  defenderHaydee: [["인내"], ["체력"], ["집중"], ["보호"], ["힘"]],
  supporterCommon: [["체력"], ["인내"], ["집중", "보호"], ["힘"]],
  supporterAsherah: [["힘", "체력"], ["인내"], ["집중", "보호"]]
});

const JOURNEY_STAT_PRIORITY_EXCEPTIONS = Object.freeze({
  // 스트라이커 예외
  "ceres": JOURNEY_STAT_PRIORITY_PATTERNS.focusOffense,
  "bunny-scarlet": JOURNEY_STAT_PRIORITY_PATTERNS.focusOffense,

  // 어쌔신 예외
  "amora": JOURNEY_STAT_PRIORITY_PATTERNS.focusOffense,
  "sunshine-cat-smile": JOURNEY_STAT_PRIORITY_PATTERNS.focusOffense,

  // 캐스터 예외
  "wedding-epindel": JOURNEY_STAT_PRIORITY_PATTERNS.focusOffense,
  "muriel": JOURNEY_STAT_PRIORITY_PATTERNS.focusOffense,

  // 디펜더 개별 예외
  "white-pearl-luna": JOURNEY_STAT_PRIORITY_PATTERNS.focusOffense,
  "haydee": JOURNEY_STAT_PRIORITY_PATTERNS.defenderHaydee,

  // 서포터 예외
  "waltz-asherah": JOURNEY_STAT_PRIORITY_PATTERNS.supporterAsherah
});

function getJourneyStatPriorityRows(savior) {
  const exception = JOURNEY_STAT_PRIORITY_EXCEPTIONS[savior.id];
  if (exception) {
    return [{ label: "", groups: exception }];
  }

  switch (savior.className) {
    case "스트라이커":
    case "어쌔신":
    case "캐스터":
      return [{ label: "", groups: JOURNEY_STAT_PRIORITY_PATTERNS.offenseCommon }];

    case "레인저":
      return [{ label: "", groups: JOURNEY_STAT_PRIORITY_PATTERNS.focusOffense }];

    case "디펜더":
      // 일반 디펜더는 둘 중 하나를 자동 선택하지 않는다.
      // 퓨어탱커 / 공격력 탱커 두 기준을 모두 2줄로 동시에 보여준다.
      return [
        { label: "※ 퓨어탱커", groups: JOURNEY_STAT_PRIORITY_PATTERNS.defenderPure },
        {
          label: "※ 공격력 탱커",
          note: "- 이터널 프로미스 카르멘 없을시 사용불가",
          groups: JOURNEY_STAT_PRIORITY_PATTERNS.defenderAttack
        }
      ];

    case "서포터":
      return [{ label: "", groups: JOURNEY_STAT_PRIORITY_PATTERNS.supporterCommon }];

    default:
      return [{ label: "", groups: JOURNEY_STAT_PRIORITY_PATTERNS.offenseCommon }];
  }
}

function createJourneyStatPriorityRowMarkup(groups, label = "", note = "") {
  const parts = [];

  groups.forEach((group, groupIndex) => {
    if (groupIndex) {
      parts.push(`<span class="journey-stat-priority-operator" aria-hidden="true">&gt;</span>`);
    }

    group.forEach((stat, statIndex) => {
      if (statIndex) {
        parts.push(`<span class="journey-stat-priority-operator is-equal" aria-hidden="true">=</span>`);
      }

      const iconUrl = JOURNEY_STAT_ICON_URLS[stat] || "";
      parts.push(`
        <span class="journey-stat-priority-item">
          <img src="${escapeHtml(iconUrl)}" alt="" loading="lazy" decoding="async" aria-hidden="true">
          <strong>${escapeHtml(translateString(stat))}</strong>
        </span>
      `);
    });
  });

  const readable = groups.map((group) => group.join(" = ")).join(" > ");

  return `
    <div class="journey-stat-priority-line">
      ${label ? `<div class="journey-stat-priority-label">${escapeHtml(translateString(label))}</div>` : ""}
      ${note ? `<div class="journey-stat-priority-note">${escapeHtml(translateString(note))}</div>` : ""}
      <div class="journey-stat-priority-row" aria-label="${escapeHtml(readable)}"
        style="display:flex;align-items:center;gap:10px;overflow-x:auto;overflow-y:hidden;white-space:nowrap;padding:3px 1px 7px;scrollbar-width:thin;-webkit-overflow-scrolling:touch;">
        ${parts.join("")}
      </div>
    </div>
  `;
}

function createJourneyStatPriorityMarkup(savior) {
  const rows = getJourneyStatPriorityRows(savior);
  return `
    <div class="journey-stat-priority-lines">
      ${rows.map((row) => createJourneyStatPriorityRowMarkup(row.groups, row.label, row.note)).join("")}
    </div>
  `;
}

const MAIN_CONTENTS = {
  "asherah-voyager": ["인자작"],
  "charlotte": ["PVP"],
  "seira": ["PVP", "코스모 게이트"],
  "lyn": ["작전", "코스모 게이트", "회랑", "플래시 포인트"],
  "cristelle": ["작전", "회랑", "플래시 포인트", "코스모 게이트"],
  "claire": ["작전", "코스모 게이트", "회랑", "플래시 포인트"],
  "tyria": ["PVP", "작전", "코스모 게이트", "회랑", "플래시 포인트"],
  "roberta": ["PVP", "작전", "코스모 게이트", "회랑", "플래시 포인트"],
  "ceres": ["PVP", "작전", "코스모 게이트", "회랑", "플래시 포인트"],
  "tanya": ["없음"],
  "bunny-scarlet": ["작전", "회랑", "코스모 게이트"],

  "trish": ["PVP", "작전", "회랑", "코스모 게이트"],
  "fei": ["PVP", "작전", "코스모 게이트", "회랑", "플래시 포인트"],
  "epindel": ["없음"],
  "marcille": ["없음"],
  "kyra": ["작전", "코스모 게이트", "회랑", "플래시 포인트"],
  "bunny-claire": ["PVP"],
  "bunny-charlotte": ["작전", "코스모 게이트", "회랑", "플래시 포인트"],

  "smile": ["인자작", "작전", "코스모 게이트", "회랑", "플래시 포인트"],
  "bell": ["작전", "코스모 게이트", "회랑", "플래시 포인트"],
  "lugh": ["작전", "코스모 게이트", "회랑", "플래시 포인트"],
  "petra": ["작전", "코스모 게이트", "회랑", "플래시 포인트"],
  "clarissa": ["작전", "코스모 게이트", "회랑", "플래시 포인트"],
  "naru": ["작전", "코스모 게이트", "회랑", "플래시 포인트"],
  "lydia": ["인자작"],
  "scarlet": ["없음"],
  "yoo-mina": ["없음"],
  "lacy": ["작전", "코스모 게이트", "플래시 포인트"],
  "rosaria": ["작전", "코스모 게이트", "플래시 포인트"],

  "luna": ["PVP", "작전", "코스모 게이트", "플래시 포인트"],
  "carnelia": ["PVP", "작전", "코스모 게이트", "플래시 포인트"],
  "dana": ["PVP", "작전", "코스모 게이트", "회랑", "플래시 포인트"],
  "wedding-epindel": ["PVP", "작전", "코스모 게이트", "회랑", "플래시 포인트"],
  "muriel": ["작전", "코스모 게이트", "회랑", "플래시 포인트"],
  "bunny-frey": ["작전", "코스모 게이트", "회랑", "플래시 포인트"],
  "omega": ["작전", "회랑", "코스모 게이트"],
  "lily": ["없음"],

  "emily": ["PVP", "작전", "코스모 게이트", "회랑", "플래시 포인트"],
  "haydee": ["PVP", "작전", "코스모 게이트", "회랑", "플래시 포인트"],
  "harley": ["PVP", "작전", "코스모 게이트", "회랑", "플래시 포인트"],
  "hilde": ["PVP", "작전", "코스모 게이트", "회랑", "플래시 포인트"],
  "besta": ["작전", "코스모 게이트", "회랑", "플래시 포인트"],
  "annah": ["작전", "코스모 게이트", "회랑", "플래시 포인트"],
  "carmen": ["PVP"],

  "frey": ["작전", "회랑", "플래시 포인트"],
  "serpang": ["작전", "회랑", "플래시 포인트"],
  "vera": ["작전", "회랑", "플래시 포인트"],
  "elisa": ["PVP"],
  "waltz-asherah": ["PVP", "작전", "코스모 게이트", "회랑", "플래시 포인트"],
  "wedding-carmen": ["PVP", "작전", "코스모 게이트", "회랑", "플래시 포인트"],
  "white-pearl-luna": ["작전", "코스모 게이트", "회랑", "PVP"],
  "sunshine-cat-smile": ["작전", "회랑", "코스모 게이트", "플래시 포인트"],
  "amora": ["작전", "회랑", "코스모 게이트", "인자작"],
  "professor-m": ["작전", "회랑", "코스모 게이트", "플래시 포인트"],
  "gwen": ["작전", "코스모 게이트", "회랑", "플래시 포인트"]
};

// AUTO_ESPR_I18N_1040
I18N_DATA.saviorNames.en["그웬"] = "Gwen";
I18N_DATA.saviorNames.ja["그웬"] = "グウェン";
I18N_DATA.subtitles.en["람파디스"] = "Lampadis";
I18N_DATA.subtitles.ja["람파디스"] = "ランパディス";

// AUTO_ESPR_I18N_1060
I18N_DATA.saviorNames.en["리디아"] = "Lydia";
I18N_DATA.saviorNames.ja["리디아"] = "リディア";
I18N_DATA.subtitles.en["레디 메이드 퍼피"] = "Ready-Made Puppy";
I18N_DATA.subtitles.ja["레디 메이드 퍼피"] = "レディーメイド・パピー";

I18N_DATA.subtitles.en["샤프 앤 스위트"] = "Sharp & Sweet";
I18N_DATA.subtitles.ja["샤프 앤 스위트"] = "シャープ＆スイーツ";
I18N_DATA.ui.en["출시 예정"] = "Upcoming";
I18N_DATA.ui.ja["출시 예정"] = "近日登場";

const SAVIORS = [
  {
    "id": "lydia-moon-caster",
    "name": "리디아",
    "subtitle": "레디 메이드 퍼피",
    "affiliation": "서부 탈환대",
    "grade": "SSR",
    "element": "moon",
    "className": "캐스터",
    "role": "캐스터",
    "attackType": "원소",
    "image": "./data/savior-detail-assets/1060-portrait.webp",
    "summary": "ESPR 신규 등록 구원자입니다. PVE 세팅 정보는 미정입니다.",
    "guideUrl": "https://ss.espr.gg/ko/database/characters/lydia-moon-caster"
  },
  {
    "id": "gwen",
    "name": "그웬",
    "subtitle": "람파디스",
    "affiliation": "람파디스",
    "grade": "SSR",
    "element": "star",
    "className": "스트라이커",
    "role": "스트라이커",
    "attackType": "충격",
    "image": "./data/savior-detail-assets/1040-portrait.webp",
    "summary": "ESPR 신규 등록 구원자입니다. PVE 세팅 정보는 미정입니다.",
    "guideUrl": "https://ss.espr.gg/ko/database/characters/gwen"
  },
  {
    "id": "asherah-voyager",
    "name": "아세라",
    "subtitle": "보이저 구원단",
    "affiliation": "보이저 구원단",
    "grade": "SSR",
    "element": "moon",
    "className": "스트라이커",
    "role": "스트라이커",
    "attackType": "참격",
    "image": "./images/savior/UFS_NKM_UNIT_S_VOYAGER_STRANIS.webp",
    "summary": "업로드한 엑셀의 PVE 장비·여정 아르카나 세팅을 반영했습니다.",
    "guideUrl": "https://star-savior-arcana-db.pages.dev/savior",
    "detail": {
      "equipment": {
        "pve": {
          "necklace": "속도",
          "ring": "공격력%",
          "sets": [
            "통찰(4) + 투지(2)",
            "파괴(4) + 투지(2)"
          ],
          "potential": "AX5 - 치명타 확률이 부족한 경우\nAX6 - 치명타 확률이 95% 이상인 경우",
          "note": "자체 치명타 확률증 30%"
        },
        "pvp": {
          "necklace": "해당 엑셀에 없음",
          "ring": "해당 엑셀에 없음",
          "sets": [
            "해당 엑셀은 PVE 세팅표입니다."
          ],
          "potential": "해당 엑셀에 없음",
          "note": "PVP 데이터는 표시하지 않습니다."
        }
      },
      "arcana": {
        "pve": [
          {
            "name": "공용 아르카나",
            "note": ""
          },
          null,
          null,
          null,
          null
        ],
        "pvp": [
          null,
          null,
          null,
          null,
          null
        ],
        "alternatives": [
          null,
          null,
          null,
          null,
          null
        ]
      }
    }
  },
  {
    "id": "smile",
    "name": "스마일",
    "subtitle": "보이저 구원단",
    "affiliation": "보이저 구원단",
    "grade": "SSR",
    "element": "star",
    "className": "레인저",
    "role": "레인저",
    "attackType": "충격",
    "image": "./images/savior/UFS_NKM_UNIT_S_VOYAGER_SMILE.webp",
    "summary": "업로드한 엑셀의 PVE 장비·여정 아르카나 세팅을 반영했습니다.",
    "guideUrl": "https://star-savior-arcana-db.pages.dev/savior",
    "detail": {
      "equipment": {
        "pve": {
          "necklace": "속도",
          "ring": "공격력%",
          "sets": [
            "통찰(4) + 투지(2)",
            "파괴(4) + 투지(2)"
          ],
          "potential": "AX5 - 치명타 확률이 부족한 경우\nAX6 - 치명타 확률이 95% 이상인 경우",
          "note": "정밀(4) 사용시 적중(2) 대신 투지(2) 사용 가능"
        },
        "pvp": {
          "necklace": "해당 엑셀에 없음",
          "ring": "해당 엑셀에 없음",
          "sets": [
            "해당 엑셀은 PVE 세팅표입니다."
          ],
          "potential": "해당 엑셀에 없음",
          "note": "PVP 데이터는 표시하지 않습니다."
        }
      },
      "arcana": {
        "pve": [
          {
            "name": "단점 보완 맞춤 훈련",
            "note": ""
          },
          {
            "name": "허수의 개척자",
            "note": ""
          },
          {
            "name": "꽃들에게 죽음을",
            "note": ""
          },
          {
            "name": "종말은 소녀의 얼굴을 하고 있다.",
            "note": ""
          },
          {
            "name": "휴가 준비는 쇼핑에서부터!",
            "note": ""
          }
        ],
        "pvp": [
          null,
          null,
          null,
          null,
          null
        ],
        "alternatives": [
          null,
          null,
          {
            "name": "하얀 달의 온기는 햇빛처럼 or 어느 한 기사의 맹세 or 완벽한 바니걸",
            "note": "종말은 소녀의 얼굴을 하고 있다. 대체"
          },
          {
            "name": "불굴의 역작",
            "note": "허수의 개척자 대체"
          },
          null
        ]
      }
    }
  },
  {
    "id": "luna",
    "name": "루나",
    "subtitle": "보이저 구원단",
    "affiliation": "보이저 구원단",
    "grade": "SSR",
    "element": "order",
    "className": "캐스터",
    "role": "캐스터",
    "attackType": "원소",
    "image": "./images/savior/UFS_NKM_UNIT_S_VOYAGER_ORACLE.webp",
    "summary": "업로드한 엑셀의 PVE 장비·여정 아르카나 세팅을 반영했습니다.",
    "guideUrl": "https://star-savior-arcana-db.pages.dev/savior",
    "detail": {
      "equipment": {
        "pve": {
          "necklace": "속도 or 공격력%",
          "ring": "공격력%",
          "sets": [
            "공격(4) + 투지(2)",
            "파괴(4) + 투지(2)",
            "통찰(4) + 투지(2)"
          ],
          "potential": "AX5 - 치명타 확률이 부족한 경우\nAX6 - 치명타 확률이 95% 이상인 경우",
          "note": "자체 치명타 확률증 30%"
        },
        "pvp": {
          "necklace": "해당 엑셀에 없음",
          "ring": "해당 엑셀에 없음",
          "sets": [
            "해당 엑셀은 PVE 세팅표입니다."
          ],
          "potential": "해당 엑셀에 없음",
          "note": "PVP 데이터는 표시하지 않습니다."
        }
      },
      "arcana": {
        "pve": [
          {
            "name": "단점 보완 맞춤 훈련",
            "note": ""
          },
          {
            "name": "빛을 쫓아라!",
            "note": ""
          },
          {
            "name": "죽음이 둘을 갈라놓을 때까지",
            "note": ""
          },
          {
            "name": "하얀 달의 온기는 햇빛처럼",
            "note": ""
          },
          {
            "name": "꽃들에게 죽음을",
            "note": ""
          }
        ],
        "pvp": [
          null,
          null,
          null,
          null,
          null
        ],
        "alternatives": [
          {
            "name": "노 페인, 노 게인",
            "note": "단점 보완 맞춤 훈련 대체"
          },
          {
            "name": "하늘의 심판 or 불굴의 역작 or 누각 위, 유리달 맞이 or 영원 속박의 굴레",
            "note": "하얀 달의 온기는 햇빛처럼 대체"
          },
          {
            "name": "메이드 바이 페트라♡ or 별을 보며 꿈을",
            "note": "꽃들에게 죽음을 대체"
          }
        ]
      }
    }
  },
  {
    "id": "carnelia",
    "name": "카넬리아",
    "subtitle": "방랑자",
    "affiliation": "방랑자",
    "grade": "SSR",
    "element": "chaos",
    "className": "캐스터",
    "role": "캐스터",
    "attackType": "정신",
    "image": "./images/savior/UFS_NKM_UNIT_S_MAID_LANTERN.webp",
    "summary": "업로드한 엑셀의 PVE 장비·여정 아르카나 세팅을 반영했습니다.",
    "guideUrl": "https://star-savior-arcana-db.pages.dev/savior/1005",
    "detail": {
      "equipment": {
        "pve": {
          "necklace": "속도",
          "ring": "공격력%",
          "sets": [
            "통찰(4) + 적중(2)"
          ],
          "potential": "AX5 - 치명타 확률이 부족한 경우\nAX6 - 치명타 확률이 95% 이상인 경우",
          "note": "별도 비고 없음"
        },
        "pvp": {
          "necklace": "해당 엑셀에 없음",
          "ring": "해당 엑셀에 없음",
          "sets": [
            "해당 엑셀은 PVE 세팅표입니다."
          ],
          "potential": "해당 엑셀에 없음",
          "note": "PVP 데이터는 표시하지 않습니다."
        }
      },
      "arcana": {
        "pve": [
          {
            "name": "티리아",
            "note": ""
          },
          {
            "name": "카넬리아",
            "note": ""
          },
          {
            "name": "뮤리엘",
            "note": ""
          },
          {
            "name": "웨핀델",
            "note": ""
          },
          {
            "name": "바니걸 프레이 or 린(인내)",
            "note": "엑셀 선택 추천"
          }
        ],
        "pvp": [
          null,
          null,
          null,
          null,
          null
        ],
        "alternatives": [
          null,
          null,
          null,
          null,
          null
        ]
      }
    }
  },
  {
    "id": "bell",
    "name": "벨 리스",
    "subtitle": "캔들 스퀘어",
    "affiliation": "캔들 스퀘어",
    "grade": "SSR",
    "element": "star",
    "className": "레인저",
    "role": "레인저",
    "attackType": "정신",
    "image": "./images/savior/UFS_NKM_UNIT_S_MAID_BELL.webp",
    "summary": "업로드한 엑셀의 PVE 장비·여정 아르카나 세팅을 반영했습니다.",
    "guideUrl": "https://star-savior-arcana-db.pages.dev/savior",
    "detail": {
      "equipment": {
        "pve": {
          "necklace": "속도",
          "ring": "공격력%",
          "sets": [
            "통찰(4) + 적중(2)",
            "파괴(4) + 적중(2)"
          ],
          "potential": "AX5 - 치명타 확률이 부족한 경우\nAX6 - 치명타 확률이 95% 이상인 경우",
          "note": "별도 비고 없음"
        },
        "pvp": {
          "necklace": "해당 엑셀에 없음",
          "ring": "해당 엑셀에 없음",
          "sets": [
            "해당 엑셀은 PVE 세팅표입니다."
          ],
          "potential": "해당 엑셀에 없음",
          "note": "PVP 데이터는 표시하지 않습니다."
        }
      },
      "arcana": {
        "pve": [
          {
            "name": "티리아",
            "note": ""
          },
          {
            "name": "카넬리아",
            "note": ""
          },
          {
            "name": "로자리아",
            "note": ""
          },
          {
            "name": "벨리스",
            "note": ""
          },
          {
            "name": "바니걸 프레이",
            "note": ""
          }
        ],
        "pvp": [
          null,
          null,
          null,
          null,
          null
        ],
        "alternatives": [
          null,
          null,
          null,
          null,
          null
        ]
      }
    }
  },
  {
    "id": "emily",
    "name": "에밀리",
    "subtitle": "캔들 스퀘어",
    "affiliation": "캔들 스퀘어",
    "grade": "SSR",
    "element": "moon",
    "className": "디펜더",
    "role": "디펜더",
    "attackType": "참격",
    "image": "./images/savior/UFS_NKM_UNIT_S_MAID_TWOHANDER.webp",
    "summary": "업로드한 엑셀의 PVE 장비·여정 아르카나 세팅을 반영했습니다.",
    "guideUrl": "https://star-savior-arcana-db.pages.dev/savior",
    "detail": {
      "equipment": {
        "pve": {
          "necklace": "속도 / 공격력%",
          "ring": "생명력% / 공격력%",
          "sets": [
            "공격(4) + 투지(2)",
            "생명(4) + 장벽(2)",
            "통찰(4) + 장벽(2)"
          ],
          "potential": "BX / AX1 / EX\n※ AX1은 공격력% 효율이 높거나, 공격력을 가장 높게 맞춰야 하는 경우 사용합니다.",
          "note": "반지 주옵 생퍼",
          "necklaceOptions": [
            {
              "value": "속도",
              "note": "※ 퓨어탱커, EX"
            },
            {
              "value": "공격력%",
              "note": "※ 공격탱커(AX)"
            }
          ],
          "ringOptions": [
            {
              "value": "생명력%",
              "note": "※ 퓨어탱커, EX"
            },
            {
              "value": "공격력%",
              "note": "※ 공격탱커(AX)"
            }
          ],
          "setOptions": [
            {
              "value": "공격(4) + 투지(2)",
              "note": "※ 공격탱커(AX)"
            },
            {
              "value": "생명(4) + 장벽(2)",
              "note": "※ 퓨어탱커(BX)"
            },
            {
              "value": "통찰(4) + 장벽(2)",
              "note": "※ EX 전용"
            }
          ]
        },
        "pvp": {
          "necklace": "해당 엑셀에 없음",
          "ring": "해당 엑셀에 없음",
          "sets": [
            "해당 엑셀은 PVE 세팅표입니다."
          ],
          "potential": "해당 엑셀에 없음",
          "note": "PVP 데이터는 표시하지 않습니다."
        }
      },
      "arcana": {
        "pve": [
          {
            "name": "티리아 or 왈세라",
            "note": "둘 중 하나 선택"
          },
          {
            "name": "에밀리",
            "note": ""
          },
          {
            "name": "바니걸 프레이",
            "note": ""
          },
          {
            "name": "카넬리아",
            "note": ""
          },
          {
            "name": "바니걸 클레어",
            "note": ""
          }
        ],
        "pvp": [
          null,
          null,
          null,
          null,
          null
        ],
        "alternatives": [
          null,
          null,
          null,
          null,
          null
        ]
      }
    }
  },
  {
    "id": "charlotte",
    "name": "샤를",
    "subtitle": "모나스티르 기사단",
    "affiliation": "모나스티르 기사단",
    "grade": "SSR",
    "element": "sun",
    "className": "스트라이커",
    "role": "스트라이커",
    "attackType": "참격",
    "image": "./images/savior/UFS_NKM_UNIT_S_KINGDOM_KNIGHT.webp",
    "summary": "업로드한 엑셀의 PVE 장비·여정 아르카나 세팅을 반영했습니다.",
    "guideUrl": "https://star-savior-arcana-db.pages.dev/savior",
    "detail": {
      "equipment": {
        "pve": {
          "necklace": "속도",
          "ring": "공격력%",
          "sets": [
            "통찰(4) + 투지(2)",
            "파괴(4) + 투지(2)"
          ],
          "potential": "AX5 - 치명타 확률이 부족한 경우\nAX6 - 치명타 확률이 95% 이상인 경우",
          "note": "자체 치명타 확률증 30% 적중 2셋 사용 가능"
        },
        "pvp": {
          "necklace": "해당 엑셀에 없음",
          "ring": "해당 엑셀에 없음",
          "sets": [
            "해당 엑셀은 PVE 세팅표입니다."
          ],
          "potential": "해당 엑셀에 없음",
          "note": "PVP 데이터는 표시하지 않습니다."
        }
      },
      "arcana": {
        "pve": [
          {
            "name": "공용 아르카나",
            "note": ""
          },
          null,
          null,
          null,
          null
        ],
        "pvp": [
          null,
          null,
          null,
          null,
          null
        ],
        "alternatives": [
          null,
          null,
          null,
          null,
          null
        ]
      }
    }
  },
  {
    "id": "carmen",
    "name": "카르멘",
    "subtitle": "모나스티르 기사단",
    "affiliation": "모나스티르 기사단",
    "grade": "SSR",
    "element": "moon",
    "className": "디펜더",
    "role": "디펜더",
    "attackType": "충격",
    "image": "./images/savior/UFS_NKM_UNIT_S_KINGDOM_SHIELDER.webp",
    "summary": "PVE 장비 및 아르카나 세팅 반영.",
    "guideUrl": "https://star-savior-arcana-db.pages.dev/savior",
    "detail": {
      "equipment": {
        "pve": {
          "necklace": "속도 / 공격력%",
          "ring": "생명력% / 공격력%",
          "sets": [
            "공격(4) + 투지(2)",
            "생명(4) + 장벽(2)",
            "통찰(4) + 장벽(2)"
          ],
          "potential": "BX / AX1 / EX\n※ AX1은 공격력% 효율이 높거나, 공격력을 가장 높게 맞춰야 하는 경우 사용합니다.",
          "note": "",
          "necklaceOptions": [
            {
              "value": "속도",
              "note": "※ 퓨어탱커, EX"
            },
            {
              "value": "공격력%",
              "note": "※ 공격탱커(AX)"
            }
          ],
          "ringOptions": [
            {
              "value": "생명력%",
              "note": "※ 퓨어탱커, EX"
            },
            {
              "value": "공격력%",
              "note": "※ 공격탱커(AX)"
            }
          ],
          "setOptions": [
            {
              "value": "공격(4) + 투지(2)",
              "note": "※ 공격탱커(AX)"
            },
            {
              "value": "생명(4) + 장벽(2)",
              "note": "※ 퓨어탱커(BX)"
            },
            {
              "value": "통찰(4) + 장벽(2)",
              "note": "※ EX 전용"
            }
          ]
        },
        "pvp": {
          "necklace": "해당 자료에 없음",
          "ring": "해당 자료에 없음",
          "sets": [
            "PVE 세팅표 기준"
          ],
          "potential": "해당 자료에 없음",
          "note": ""
        }
      },
      "arcana": {
        "pve": [
          {
            "name": "에밀리",
            "note": ""
          },
          {
            "name": "린(인내)",
            "note": ""
          },
          {
            "name": "왈세라",
            "note": ""
          },
          {
            "name": "할리 or 베스타",
            "note": "할리 추천 또는 베스타"
          },
          {
            "name": "엘리사 or 힐데 or 바니걸 클레어",
            "note": "엑셀 선택 추천"
          }
        ],
        "pvp": [
          null,
          null,
          null,
          null,
          null
        ],
        "alternatives": [
          null,
          null,
          null,
          null,
          null
        ]
      }
    }
  },
  {
    "id": "frey",
    "name": "프레이",
    "subtitle": "모나스티르 기사단",
    "affiliation": "모나스티르 기사단",
    "grade": "SSR",
    "element": "star",
    "className": "서포터",
    "role": "서포터",
    "attackType": "충격",
    "image": "./images/savior/UFS_NKM_UNIT_S_KINGDOM_PRAY.webp",
    "summary": "PVE 장비 및 아르카나 세팅 반영.",
    "guideUrl": "https://star-savior-arcana-db.pages.dev/savior",
    "detail": {
      "equipment": {
        "pve": {
          "necklace": "속도",
          "ring": "생명력%",
          "sets": [
            "생명(4) + 장벽(2)"
          ],
          "potential": "BX",
          "note": ""
        },
        "pvp": {
          "necklace": "해당 자료에 없음",
          "ring": "해당 자료에 없음",
          "sets": [
            "PVE 세팅표 기준"
          ],
          "potential": "해당 자료에 없음",
          "note": ""
        }
      },
      "arcana": {
        "pve": [
          {
            "name": "스트라니스의 영애",
            "note": ""
          },
          {
            "name": "하얀 달의 온기는 햇빛처럼",
            "note": ""
          },
          {
            "name": "공녀, 왕좌에 오르다",
            "note": ""
          },
          {
            "name": "완벽한 바니걸",
            "note": ""
          },
          {
            "name": "본 투 비 와일드 or 하늘의 시련 or 금단의 기록물 Vol. 1",
            "note": ""
          }
        ],
        "pvp": [
          null,
          null,
          null,
          null,
          null
        ],
        "alternatives": [
          null,
          null,
          null,
          null,
          null
        ]
      }
    }
  },
  {
    "id": "seira",
    "name": "세이라",
    "subtitle": "나이트메어",
    "affiliation": "나이트메어",
    "grade": "SSR",
    "element": "order",
    "className": "스트라이커",
    "role": "스트라이커",
    "attackType": "정신",
    "image": "./images/savior/UFS_NKM_UNIT_S_NIGHTMARE_REAPER.webp",
    "summary": "PVE 장비 및 아르카나 세팅 반영.",
    "guideUrl": "https://star-savior-arcana-db.pages.dev/savior",
    "detail": {
      "equipment": {
        "pve": {
          "necklace": "속도",
          "ring": "공격력%",
          "sets": [
            "통찰(4) + 투지(2)",
            "파괴(4) + 투지(2)"
          ],
          "potential": "AX5 - 치명타 확률이 부족한 경우\nAX6 - 치명타 확률이 95% 이상인 경우",
          "note": ""
        },
        "pvp": {
          "necklace": "해당 자료에 없음",
          "ring": "해당 자료에 없음",
          "sets": [
            "PVE 세팅표 기준"
          ],
          "potential": "해당 자료에 없음",
          "note": ""
        }
      },
      "arcana": {
        "pve": [
          {
            "name": "공용 아르카나",
            "note": ""
          },
          null,
          null,
          null,
          null
        ],
        "pvp": [
          null,
          null,
          null,
          null,
          null
        ],
        "alternatives": [
          null,
          null,
          null,
          null,
          null
        ]
      }
    }
  },
  {
    "id": "trish",
    "name": "트리쉬",
    "subtitle": "아셀루스 협회",
    "affiliation": "아셀루스 협회",
    "grade": "SSR",
    "element": "star",
    "className": "어쌔신",
    "role": "어쌔신",
    "attackType": "참격",
    "image": "./images/savior/UFS_NKM_UNIT_S_STELLAR_THIEF.webp",
    "summary": "PVE 장비 및 아르카나 세팅 반영.",
    "guideUrl": "https://star-savior-arcana-db.pages.dev/savior",
    "detail": {
      "equipment": {
        "pve": {
          "necklace": "속도",
          "ring": "공격력%",
          "sets": [
            "통찰(4) + 투지(2)",
            "파괴(4) + 투지(2)"
          ],
          "potential": "AX1 - 공격력% 효율이 높은 구원자",
          "note": ""
        },
        "pvp": {
          "necklace": "해당 자료에 없음",
          "ring": "해당 자료에 없음",
          "sets": [
            "PVE 세팅표 기준"
          ],
          "potential": "해당 자료에 없음",
          "note": ""
        }
      },
      "arcana": {
        "pve": [
          {
            "name": "단점 보완 맞춤 훈련",
            "note": ""
          },
          {
            "name": "키라만큼 귀여워!",
            "note": ""
          },
          {
            "name": "불굴의 역작",
            "note": ""
          },
          {
            "name": "귀로 없는 여정",
            "note": ""
          },
          {
            "name": "꽃들에게 죽음을",
            "note": ""
          }
        ],
        "pvp": [
          null,
          null,
          null,
          null,
          null
        ],
        "alternatives": [
          {
            "name": "노 페인, 노 게인",
            "note": "단점 보완 맞춤 훈련 대체"
          },
          {
            "name": "하얀 달의 온기는 햇빛처럼 or 어느 한 기사의 맹세 or 완벽한 바니걸",
            "note": "불굴의 역작 대체"
          },
          {
            "name": "메이드 바이 페트라♡ or 별을 보며 꿈을",
            "note": "꽃들에게 죽음을 대체"
          },
          {
            "name": "허수의 개척자",
            "note": "귀로 없는 여정 대체"
          }
        ]
      }
    }
  },
  {
    "id": "lyn",
    "name": "린",
    "subtitle": "풍월당",
    "affiliation": "풍월당",
    "grade": "SSR",
    "element": "star",
    "className": "스트라이커",
    "role": "스트라이커",
    "attackType": "참격",
    "image": "./images/savior/UFS_NKM_UNIT_S_EASTERN_SWORDMASTER.webp",
    "summary": "업로드한 엑셀의 PVE 장비·여정 아르카나 세팅을 반영했습니다.",
    "guideUrl": "https://star-savior-arcana-db.pages.dev/savior",
    "detail": {
      "equipment": {
        "pve": {
          "necklace": "속도",
          "ring": "공격력%",
          "sets": [
            "통찰(4) + 투지(2)",
            "파괴(4) + 투지(2)"
          ],
          "potential": "AX5 - 치명타 확률이 부족한 경우\nAX6 - 치명타 확률이 95% 이상인 경우",
          "note": "별도 비고 없음"
        },
        "pvp": {
          "necklace": "해당 엑셀에 없음",
          "ring": "해당 엑셀에 없음",
          "sets": [
            "해당 엑셀은 PVE 세팅표입니다."
          ],
          "potential": "해당 엑셀에 없음",
          "note": "PVP 데이터는 표시하지 않습니다."
        }
      },
      "arcana": {
        "pve": [
          {
            "name": "공용 아르카나",
            "note": ""
          },
          null,
          null,
          null,
          null
        ],
        "pvp": [
          null,
          null,
          null,
          null,
          null
        ],
        "alternatives": [
          null,
          null,
          null,
          null,
          null
        ]
      }
    }
  },
  {
    "id": "cristelle",
    "name": "크리스텔",
    "subtitle": "모렐 해운상회",
    "affiliation": "모렐 해운상회",
    "grade": "SSR",
    "element": "sun",
    "className": "레인저",
    "role": "레인저",
    "attackType": "원소",
    "image": "./images/savior/크리스텔(모렐 해운상회).webp",
    "summary": "PVE 장비·아르카나 세팅을 반영했습니다.",
    "guideUrl": "https://star-savior-arcana-db.pages.dev/savior/1017",
    "detail": {
      "equipment": {
        "pve": {
          "necklace": "속도, 공격력%",
          "necklaceNote": "본인 조합과 세팅에 따라 다르나 속도 권장.",
          "ring": "공격력%",
          "sets": [
            "공격(4) + 적중(2)",
            "통찰(4) + 적중(2)",
            "파괴(4) + 적중(2)",
            "정밀(4) + 적중(2)"
          ],
          "setNotes": [
            "적중(2)는 투지(2)로 대체가능."
          ],
          "potential": "AX1 - 공격력% 효율이 높은 구원자\nAX5 - 치명타 확률이 부족한 경우",
          "note": ""
        },
        "pvp": {
          "necklace": "미정",
          "ring": "미정",
          "sets": [
            "미정"
          ],
          "potential": "미정",
          "note": "미정"
        }
      },
      "arcana": {
        "pve": [
          {
            "name": "단점 보완 맞춤 훈련",
            "note": ""
          },
          {
            "name": "불굴의 역작",
            "note": ""
          },
          {
            "name": "꽃들에게 죽음을",
            "note": ""
          },
          {
            "name": "영원 속박의 굴레",
            "note": ""
          },
          {
            "name": "하얀 달의 온기는 햇빛처럼 or 완벽한 바니걸",
            "note": ""
          }
        ],
        "pvp": [
          null,
          null,
          null,
          null,
          null
        ],
        "alternatives": [
          {
            "name": "어느 한 기사의 맹세",
            "note": "하얀 달의 온기는 햇빛처럼/완벽한 바니걸 대체"
          },
          {
            "name": "노 페인, 노 게인",
            "note": "단점 맞춤 훈련 대체"
          },
          {
            "name": "누각 위, 유리달 맞이",
            "note": "영원 속박의 굴레 대체"
          },
          null,
          null
        ]
      }
    }
  },
  {
    "id": "haydee",
    "name": "에데",
    "subtitle": "모렐 해운상회",
    "affiliation": "모렐 해운상회",
    "grade": "SSR",
    "element": "star",
    "className": "디펜더",
    "role": "디펜더",
    "attackType": "참격",
    "image": "./images/savior/UFS_NKM_UNIT_S_INCOGNITA_FLOWER.webp",
    "summary": "업로드한 엑셀의 PVE 장비·여정 아르카나 세팅을 반영했습니다.",
    "guideUrl": "https://star-savior-arcana-db.pages.dev/savior",
    "detail": {
      "equipment": {
        "pve": {
          "necklace": "속도 / 공격력%",
          "ring": "효과적중% / 효과적중%, 방어력% / 공격력%",
          "sets": [
            "공격(4) + 투지(2)",
            "방어(6)",
            "통찰(4) + 적중(2)"
          ],
          "potential": "CX / AX1 / EX\n※ AX1은 공격력% 효율이 높거나, 공격력을 가장 높게 맞춰야 하는 경우 사용합니다.",
          "note": "반지 주옵 방퍼 생명(4) 사용 가능",
          "necklaceOptions": [
            {
              "value": "속도",
              "note": "※ 퓨어탱커, EX"
            },
            {
              "value": "공격력%",
              "note": "※ 공격탱커(AX)"
            }
          ],
          "ringOptions": [
            {
              "value": "효과적중%",
              "note": "※ 퓨어탱커"
            },
            {
              "value": "효과적중% / 방어력%",
              "note": "※ EX"
            },
            {
              "value": "공격력%",
              "note": "※ 공격탱커(AX)"
            }
          ],
          "setOptions": [
            {
              "value": "공격(4) + 투지(2)",
              "note": "※ 공격탱커(AX)"
            },
            {
              "value": "방어(6)",
              "note": "※ 퓨어탱커(CX)"
            },
            {
              "value": "통찰(4) + 적중(2)",
              "note": "※ EX 전용"
            }
          ]
        },
        "pvp": {
          "necklace": "해당 엑셀에 없음",
          "ring": "해당 엑셀에 없음",
          "sets": [
            "해당 엑셀은 PVE 세팅표입니다."
          ],
          "potential": "해당 엑셀에 없음",
          "note": "PVP 데이터는 표시하지 않습니다."
        }
      },
      "arcana": {
        "pve": [
          {
            "name": "에밀리",
            "note": ""
          },
          {
            "name": "린(인내)",
            "note": ""
          },
          {
            "name": "왈세라",
            "note": ""
          },
          {
            "name": "할리 or 베스타",
            "note": "할리 추천 또는 베스타"
          },
          {
            "name": "엘리사 or 힐데 or 바니걸 클레어",
            "note": "엑셀 선택 추천"
          }
        ],
        "pvp": [
          null,
          null,
          null,
          null,
          null
        ],
        "alternatives": [
          null,
          null,
          null,
          null,
          null
        ]
      }
    }
  },
  {
    "id": "serpang",
    "name": "세르팡",
    "subtitle": "풍월당",
    "affiliation": "풍월당",
    "grade": "SSR",
    "element": "sun",
    "className": "서포터",
    "role": "서포터",
    "attackType": "정신",
    "image": "./images/savior/UFS_NKM_UNIT_S_EASTERN_OWL.webp",
    "summary": "PVE 장비 및 아르카나 세팅 반영.",
    "guideUrl": "https://star-savior-arcana-db.pages.dev/savior",
    "detail": {
      "equipment": {
        "pve": {
          "necklace": "속도",
          "ring": "생명력%",
          "sets": [
            "생명(4) + 장벽(2)"
          ],
          "potential": "BX",
          "note": ""
        },
        "pvp": {
          "necklace": "해당 자료에 없음",
          "ring": "해당 자료에 없음",
          "sets": [
            "PVE 세팅표 기준"
          ],
          "potential": "해당 자료에 없음",
          "note": ""
        }
      },
      "arcana": {
        "pve": [
          {
            "name": "스트라니스의 영애",
            "note": ""
          },
          {
            "name": "하얀 달의 온기는 햇빛처럼",
            "note": ""
          },
          {
            "name": "공녀, 왕좌에 오르다",
            "note": ""
          },
          {
            "name": "완벽한 바니걸",
            "note": ""
          },
          {
            "name": "본 투 비 와일드 or 하늘의 시련 or 금단의 기록물 Vol. 1",
            "note": ""
          }
        ],
        "pvp": [
          null,
          null,
          null,
          null,
          null
        ],
        "alternatives": [
          null,
          null,
          null,
          null,
          null
        ]
      }
    }
  },
  {
    "id": "dana",
    "name": "다나",
    "subtitle": "카노푸스 경비대",
    "affiliation": "카노푸스 경비대",
    "grade": "SSR",
    "element": "star",
    "className": "캐스터",
    "role": "캐스터",
    "attackType": "원소",
    "image": "./images/savior/UFS_NKM_UNIT_S_MAGICIAN_DRUID.webp",
    "summary": "업로드한 엑셀의 PVE 장비·여정 아르카나 세팅을 반영했습니다.",
    "guideUrl": "https://star-savior-arcana-db.pages.dev/savior",
    "detail": {
      "equipment": {
        "pve": {
          "necklace": "속도",
          "ring": "공격력%",
          "sets": [
            "통찰(4) + 투지(2)",
            "파괴(4) + 투지(2)"
          ],
          "potential": "AX5 - 치명타 확률이 부족한 경우\nAX6 - 치명타 확률이 95% 이상인 경우",
          "note": "별도 비고 없음"
        },
        "pvp": {
          "necklace": "해당 엑셀에 없음",
          "ring": "해당 엑셀에 없음",
          "sets": [
            "해당 엑셀은 PVE 세팅표입니다."
          ],
          "potential": "해당 엑셀에 없음",
          "note": "PVP 데이터는 표시하지 않습니다."
        }
      },
      "arcana": {
        "pve": [
          {
            "name": "티리아",
            "note": ""
          },
          {
            "name": "카넬리아",
            "note": ""
          },
          {
            "name": "뮤리엘",
            "note": ""
          },
          {
            "name": "웨핀델",
            "note": ""
          },
          {
            "name": "바니걸 프레이 or 린(인내)",
            "note": "엑셀 선택 추천"
          }
        ],
        "pvp": [
          null,
          null,
          null,
          null,
          null
        ],
        "alternatives": [
          null,
          null,
          null,
          null,
          null
        ]
      }
    }
  },
  {
    "id": "muriel",
    "name": "뮤리엘",
    "subtitle": "모노리스 교단",
    "affiliation": "모노리스 교단",
    "grade": "SSR",
    "element": "sun",
    "className": "캐스터",
    "role": "캐스터",
    "attackType": "원소",
    "image": "./images/savior/UFS_NKM_UNIT_S_SAINTESS_DEMON.webp",
    "summary": "업로드한 엑셀의 PVE 장비·여정 아르카나 세팅을 반영했습니다.",
    "guideUrl": "https://star-savior-arcana-db.pages.dev/savior",
    "detail": {
      "equipment": {
        "pve": {
          "necklace": "속도",
          "ring": "공격력%",
          "sets": [
            "파괴(4) + 적중(2)",
            "통찰(4) + 적중(2)"
          ],
          "potential": "AX5 - 치명타 확률이 부족한 경우\nAX6 - 치명타 확률이 95% 이상인 경우",
          "note": "자체 치명타 피해증 (15~25%) 적중(2) 사용 가능"
        },
        "pvp": {
          "necklace": "해당 엑셀에 없음",
          "ring": "해당 엑셀에 없음",
          "sets": [
            "해당 엑셀은 PVE 세팅표입니다."
          ],
          "potential": "해당 엑셀에 없음",
          "note": "PVP 데이터는 표시하지 않습니다."
        }
      },
      "arcana": {
        "pve": [
          {
            "name": "티리아",
            "note": ""
          },
          {
            "name": "카넬리아",
            "note": ""
          },
          {
            "name": "뮤리엘",
            "note": ""
          },
          {
            "name": "웨핀델",
            "note": ""
          },
          {
            "name": "바니걸 프레이 or 린(인내)",
            "note": "엑셀 선택 추천"
          }
        ],
        "pvp": [
          null,
          null,
          null,
          null,
          null
        ],
        "alternatives": [
          null,
          null,
          null,
          null,
          null
        ]
      }
    }
  },
  {
    "id": "elisa",
    "name": "엘리사",
    "subtitle": "모노리스 교단",
    "affiliation": "모노리스 교단",
    "grade": "SSR",
    "element": "chaos",
    "className": "서포터",
    "role": "서포터",
    "attackType": "정신",
    "image": "./images/savior/UFS_NKM_UNIT_S_SAINTESS_ELF.webp",
    "summary": "PVE 장비 및 아르카나 세팅 반영.",
    "guideUrl": "https://star-savior-arcana-db.pages.dev/savior",
    "detail": {
      "equipment": {
        "pve": {
          "necklace": "속도",
          "ring": "생명력%",
          "sets": [
            "생명(4) + 장벽(2)"
          ],
          "potential": "BX",
          "note": ""
        },
        "pvp": {
          "necklace": "해당 자료에 없음",
          "ring": "해당 자료에 없음",
          "sets": [
            "PVE 세팅표 기준"
          ],
          "potential": "해당 자료에 없음",
          "note": ""
        }
      },
      "arcana": {
        "pve": [
          {
            "name": "스트라니스의 영애",
            "note": ""
          },
          {
            "name": "하얀 달의 온기는 햇빛처럼",
            "note": ""
          },
          {
            "name": "공녀, 왕좌에 오르다",
            "note": ""
          },
          {
            "name": "완벽한 바니걸",
            "note": ""
          },
          {
            "name": "본 투 비 와일드 or 하늘의 시련 or 금단의 기록물 Vol. 1",
            "note": ""
          }
        ],
        "pvp": [
          null,
          null,
          null,
          null,
          null
        ],
        "alternatives": [
          null,
          null,
          null,
          null,
          null
        ]
      }
    }
  },
  {
    "id": "tyria",
    "name": "티리아",
    "subtitle": "집행자",
    "affiliation": "집행자",
    "grade": "SSR",
    "element": "sun",
    "className": "스트라이커",
    "role": "스트라이커",
    "attackType": "참격",
    "image": "./images/savior/UFS_NKM_UNIT_S_APOSTLE_TYRIA.webp",
    "summary": "업로드한 엑셀의 PVE 장비·여정 아르카나 세팅을 반영했습니다.",
    "guideUrl": "https://star-savior-arcana-db.pages.dev/savior",
    "detail": {
      "equipment": {
        "pve": {
          "necklace": "속도",
          "ring": "공격력%",
          "sets": [
            "통찰(4) + 투지(2)",
            "파괴(4) + 투지(2)"
          ],
          "potential": "AX5 - 치명타 확률이 부족한 경우\nAX6 - 치명타 확률이 95% 이상인 경우",
          "note": "별도 비고 없음"
        },
        "pvp": {
          "necklace": "해당 엑셀에 없음",
          "ring": "해당 엑셀에 없음",
          "sets": [
            "해당 엑셀은 PVE 세팅표입니다."
          ],
          "potential": "해당 엑셀에 없음",
          "note": "PVP 데이터는 표시하지 않습니다."
        }
      },
      "arcana": {
        "pve": [
          {
            "name": "바니걸 클레어 or 오메가",
            "note": "첫 슬롯 선택"
          },
          {
            "name": "공용 아르카나",
            "note": ""
          },
          {
            "name": "공용 아르카나",
            "note": ""
          },
          {
            "name": "공용 아르카나",
            "note": ""
          },
          {
            "name": "공용 아르카나",
            "note": ""
          }
        ],
        "pvp": [
          null,
          null,
          null,
          null,
          null
        ],
        "alternatives": [
          null,
          null,
          null,
          null,
          null
        ]
      }
    }
  },
  {
    "id": "roberta",
    "name": "로베르타",
    "subtitle": "궤도 수색대",
    "affiliation": "궤도 수색대",
    "grade": "SSR",
    "element": "star",
    "className": "스트라이커",
    "role": "스트라이커",
    "attackType": "충격",
    "image": "./images/savior/UFS_NKM_UNIT_S_RECON_KNUCKLE.webp",
    "summary": "업로드한 엑셀의 PVE 장비·여정 아르카나 세팅을 반영했습니다.",
    "guideUrl": "https://star-savior-arcana-db.pages.dev/savior",
    "detail": {
      "equipment": {
        "pve": {
          "necklace": "속도",
          "ring": "공격력%",
          "sets": [
            "파괴(4) + 투지(2)",
            "파괴(4) + 장벽(2)"
          ],
          "potential": "AX1 - 공격력% 효율이 높은 구원자",
          "note": "자체 치명타 확률증 50% 투지(2) 사용 가능"
        },
        "pvp": {
          "necklace": "해당 엑셀에 없음",
          "ring": "해당 엑셀에 없음",
          "sets": [
            "해당 엑셀은 PVE 세팅표입니다."
          ],
          "potential": "해당 엑셀에 없음",
          "note": "PVP 데이터는 표시하지 않습니다."
        }
      },
      "arcana": {
        "pve": [
          {
            "name": "단점 보완 맞춤 훈련",
            "note": ""
          },
          {
            "name": "불굴의 역작",
            "note": ""
          },
          {
            "name": "꽃들에게 죽음을",
            "note": ""
          },
          {
            "name": "서류 더미 위의 책임감",
            "note": ""
          },
          {
            "name": "하얀 달의 온기는 햇빛처럼",
            "note": ""
          }
        ],
        "pvp": [
          null,
          null,
          null,
          null,
          null
        ],
        "alternatives": [
          {
            "name": "완벽한 바니걸 or 본 투 비 와일드 or 음독의 각오",
            "note": "하얀 달의 온기는 햇빛처럼 대체"
          },
          null,
          null,
          null,
          null
        ]
      }
    }
  },
  {
    "id": "lugh",
    "name": "루그",
    "subtitle": "궤도 수색대",
    "affiliation": "궤도 수색대",
    "grade": "SSR",
    "element": "moon",
    "className": "레인저",
    "role": "레인저",
    "attackType": "정신",
    "image": "./images/savior/UFS_NKM_UNIT_S_RECON_AMULET.webp",
    "summary": "업로드한 엑셀의 PVE 장비·여정 아르카나 세팅을 반영했습니다.",
    "guideUrl": "https://star-savior-arcana-db.pages.dev/savior",
    "detail": {
      "equipment": {
        "pve": {
          "necklace": "속도",
          "ring": "공격력%",
          "sets": [
            "파괴(4) + 투지(2)",
            "통찰(4) + 투지(2)"
          ],
          "potential": "AX5 - 치명타 확률이 부족한 경우\nAX6 - 치명타 확률이 95% 이상인 경우",
          "note": ""
        },
        "pvp": {
          "necklace": "해당 엑셀에 없음",
          "ring": "해당 엑셀에 없음",
          "sets": [
            "해당 엑셀은 PVE 세팅표입니다."
          ],
          "potential": "해당 엑셀에 없음",
          "note": "PVP 데이터는 표시하지 않습니다."
        }
      },
      "arcana": {
        "pve": [
          { "name": "단점 보완 맞춤 훈련", "note": "" },
          { "name": "불굴의 역작", "note": "" },
          { "name": "탐닉자의 유흥거리", "note": "" },
          { "name": "꽃들에게 죽음을", "note": "" },
          { "name": "영원 속박의 굴레", "note": "" }
        ],
        "pvp": [
          null,
          null,
          null,
          null,
          null
        ],
        "alternatives": [
          { "name": "노 페인, 노 게인", "note": "단점 보완 맞춤 훈련 대체" },
          { "name": "메이드 바이 페트라♡ or 별을 보며 꿈을 or 깊은 애도", "note": "꽃들에게 죽음을 대체" },
          { "name": "하얀 달의 온기는 햇빛처럼 or 완벽한 바니걸 or 어느 한 기사의 맹세", "note": "부족한 자리 대체" },
          null,
          null
        ]
      }
    }
  },
  {
    "id": "fei",
    "name": "페이",
    "subtitle": "방랑자",
    "affiliation": "방랑자",
    "grade": "SSR",
    "element": "moon",
    "className": "어쌔신",
    "role": "어쌔신",
    "attackType": "참격",
    "image": "./images/savior/UFS_NKM_UNIT_S_INDEPENDENT_VAGABOND.webp",
    "summary": "업로드한 엑셀의 PVE 장비·여정 아르카나 세팅을 반영했습니다.",
    "guideUrl": "https://star-savior-arcana-db.pages.dev/savior",
    "detail": {
      "equipment": {
        "pve": {
          "necklace": "속도",
          "ring": "공격력%",
          "sets": [
            "파괴(4) + 투지(2)",
            "파괴(4) + 장벽(2)",
            "파괴(4) + 적중(2)"
          ],
          "potential": "AX1 / XX2 (생명력 흡수)\n※ AX1은 공격력% 효율이 높거나, 공격력을 가장 높게 맞춰야 하는 경우 사용합니다.",
          "note": "*전용 알카 사용시 특수기 치명타 확률 100%"
        },
        "pvp": {
          "necklace": "해당 엑셀에 없음",
          "ring": "해당 엑셀에 없음",
          "sets": [
            "해당 엑셀은 PVE 세팅표입니다."
          ],
          "potential": "해당 엑셀에 없음",
          "note": "PVP 데이터는 표시하지 않습니다."
        }
      },
      "arcana": {
        "pve": [
          {
            "name": "단점 보완 맞춤 훈련",
            "note": ""
          },
          {
            "name": "키라만큼 귀여워!",
            "note": ""
          },
          {
            "name": "오늘의 한 걸음",
            "note": ""
          },
          {
            "name": "귀로 없는 여정",
            "note": ""
          },
          {
            "name": "꽃들에게 죽음을",
            "note": ""
          }
        ],
        "pvp": [
          null,
          null,
          null,
          null,
          null
        ],
        "alternatives": [
          {
            "name": "노 페인, 노 게인 or 허수의 개척자 or 불굴의 역작",
            "note": "단점 보완 맞춤 훈련 대체"
          },
          {
            "name": "불굴의 역작 or 허수의 개척자",
            "note": "꽃들에게 죽음을 대체"
          },
          {
            "name": "메이드 바이 페트라♡ or 별을 보며 꿈을",
            "note": "꽃들에게 죽음을 대체"
          }
        ]
      }
    }
  },
  {
    "id": "epindel",
    "name": "에핀델",
    "subtitle": "오를랑 가문",
    "affiliation": "오를랑 가문",
    "grade": "SSR",
    "element": "moon",
    "className": "어쌔신",
    "role": "어쌔신",
    "attackType": "참격",
    "image": "./images/savior/UFS_NKM_UNIT_S_GRACE_DUALSWORD.webp",
    "summary": "PVE 장비 및 아르카나 세팅 반영.",
    "guideUrl": "https://star-savior-arcana-db.pages.dev/savior",
    "detail": {
      "equipment": {
        "pve": {
          "necklace": "속도",
          "ring": "공격력%",
          "sets": [
            "통찰(4) + 투지(2)",
            "파괴(4) + 투지(2)"
          ],
          "potential": "AX5 - 치명타 확률이 부족한 경우\nAX6 - 치명타 확률이 95% 이상인 경우",
          "note": ""
        },
        "pvp": {
          "necklace": "해당 자료에 없음",
          "ring": "해당 자료에 없음",
          "sets": [
            "PVE 세팅표 기준"
          ],
          "potential": "해당 자료에 없음",
          "note": ""
        }
      },
      "arcana": {
        "pve": [
          {
            "name": "단점 보완 맞춤 훈련",
            "note": ""
          },
          {
            "name": "키라만큼 귀여워!",
            "note": ""
          },
          {
            "name": "불굴의 역작",
            "note": ""
          },
          {
            "name": "귀로 없는 여정",
            "note": ""
          },
          {
            "name": "꽃들에게 죽음을",
            "note": ""
          }
        ],
        "pvp": [
          null,
          null,
          null,
          null,
          null
        ],
        "alternatives": [
          {
            "name": "노 페인, 노 게인",
            "note": "단점 보완 맞춤 훈련 대체"
          },
          {
            "name": "하얀 달의 온기는 햇빛처럼 or 어느 한 기사의 맹세 or 완벽한 바니걸",
            "note": "불굴의 역작 대체"
          },
          {
            "name": "메이드 바이 페트라♡ or 별을 보며 꿈을",
            "note": "꽃들에게 죽음을 대체"
          }
        ]
      }
    }
  },
  {
    "id": "omega",
    "name": "오메가",
    "subtitle": "보이저 구원단",
    "affiliation": "보이저 구원단",
    "grade": "SSR",
    "element": "star",
    "className": "캐스터",
    "role": "캐스터",
    "attackType": "충격",
    "image": "./images/savior/UFS_NKM_UNIT_S_STARPIERCER_OMEGA.webp",
    "summary": "업로드한 엑셀의 PVE 장비·여정 아르카나 세팅을 반영했습니다.",
    "guideUrl": "https://star-savior-arcana-db.pages.dev/savior",
    "detail": {
      "equipment": {
        "pve": {
          "necklace": "속도",
          "ring": "공격력%",
          "sets": [
            "통찰(4) + 투지(2)",
            "파괴(4) + 투지(2)"
          ],
          "potential": "AX5 - 치명타 확률이 부족한 경우\nAX6 - 치명타 확률이 95% 이상인 경우",
          "note": "별도 비고 없음"
        },
        "pvp": {
          "necklace": "해당 엑셀에 없음",
          "ring": "해당 엑셀에 없음",
          "sets": [
            "해당 엑셀은 PVE 세팅표입니다."
          ],
          "potential": "해당 엑셀에 없음",
          "note": "PVP 데이터는 표시하지 않습니다."
        }
      },
      "arcana": {
        "pve": [
          {
            "name": "티리아",
            "note": ""
          },
          {
            "name": "카넬리아",
            "note": ""
          },
          {
            "name": "뮤리엘",
            "note": ""
          },
          {
            "name": "웨핀델",
            "note": ""
          },
          {
            "name": "오메가 or 바니걸 프레이",
            "note": "엑셀 선택 추천"
          }
        ],
        "pvp": [
          null,
          null,
          null,
          null,
          null
        ],
        "alternatives": [
          null,
          null,
          null,
          null,
          null
        ]
      }
    }
  },
  {
    "id": "bunny-charlotte",
    "name": "샤를",
    "subtitle": "하트 오브 모나스티르",
    "affiliation": "하트 오브 모나스티르",
    "grade": "SSR",
    "element": "sun",
    "className": "어쌔신",
    "role": "어쌔신",
    "attackType": "정신",
    "image": "./images/savior/UFS_NKM_UNIT_S_BUNNY_KNIGHT.webp",
    "summary": "업로드한 엑셀의 PVE 장비·여정 아르카나 세팅을 반영했습니다.",
    "guideUrl": "https://star-savior-arcana-db.pages.dev/savior",
    "detail": {
      "equipment": {
        "pve": {
          "necklace": "속도",
          "ring": "공격력%",
          "sets": [
            "통찰(4) + 투지(2)",
            "파괴(4) + 투지(2)"
          ],
          "potential": "AX5 - 치명타 확률이 부족한 경우\nAX6 - 치명타 확률이 95% 이상인 경우",
          "note": "*린(힘) 사용시 린(인내)를 샤를로 변경"
        },
        "pvp": {
          "necklace": "해당 엑셀에 없음",
          "ring": "해당 엑셀에 없음",
          "sets": [
            "해당 엑셀은 PVE 세팅표입니다."
          ],
          "potential": "해당 엑셀에 없음",
          "note": "PVP 데이터는 표시하지 않습니다."
        }
      },
      "arcana": {
        "pve": [
          {
            "name": "단점 보완 맞춤 훈련",
            "note": ""
          },
          {
            "name": "키라만큼 귀여워!",
            "note": ""
          },
          {
            "name": "불굴의 역작",
            "note": ""
          },
          {
            "name": "귀로 없는 여정",
            "note": ""
          },
          {
            "name": "꽃들에게 죽음을",
            "note": ""
          }
        ],
        "pvp": [
          null,
          null,
          null,
          null,
          null
        ],
        "alternatives": [
          {
            "name": "노 페인, 노 게인",
            "note": "단점 보완 맞춤 훈련 대체"
          },
          {
            "name": "하얀 달의 온기는 햇빛처럼 or 어느 한 기사의 맹세 or 완벽한 바니걸",
            "note": "불굴의 역작 대체"
          },
          {
            "name": "메이드 바이 페트라♡ or 별을 보며 꿈을",
            "note": "꽃들에게 죽음을 대체"
          }
        ]
      }
    }
  },
  {
    "id": "ceres",
    "name": "세레스",
    "subtitle": "서부 탈환대",
    "affiliation": "서부 탈환대",
    "grade": "SSR",
    "element": "moon",
    "className": "스트라이커",
    "role": "스트라이커",
    "attackType": "참격",
    "image": "./images/savior/UFS_NKM_UNIT_S_WEST_BEAMSWORD.webp",
    "summary": "PVE 장비 및 아르카나 세팅 반영.",
    "guideUrl": "https://star-savior-arcana-db.pages.dev/savior",
    "detail": {
      "equipment": {
        "pve": {
          "necklace": "속도",
          "ring": "공격력%",
          "sets": [
            "통찰(4) + 투지(2)",
            "파괴(4) + 투지(2)"
          ],
          "potential": "AX5 - 치명타 확률이 부족한 경우\nAX6 - 치명타 확률이 95% 이상인 경우",
          "note": ""
        },
        "pvp": {
          "necklace": "해당 자료에 없음",
          "ring": "해당 자료에 없음",
          "sets": [
            "PVE 세팅표 기준"
          ],
          "potential": "해당 자료에 없음",
          "note": ""
        }
      },
      "arcana": {
        "pve": [
          {
            "name": "바니걸 클레어 or 오메가",
            "note": "첫 슬롯 선택"
          },
          {
            "name": "공용 아르카나",
            "note": ""
          },
          {
            "name": "공용 아르카나",
            "note": ""
          },
          {
            "name": "공용 아르카나",
            "note": ""
          },
          {
            "name": "공용 아르카나",
            "note": ""
          }
        ],
        "pvp": [
          null,
          null,
          null,
          null,
          null
        ],
        "alternatives": [
          null,
          null,
          null,
          null,
          null
        ]
      }
    }
  },
  {
    "id": "lydia",
    "name": "리디아",
    "subtitle": "서부 탈환대",
    "affiliation": "서부 탈환대",
    "grade": "SSR",
    "element": "chaos",
    "className": "레인저",
    "role": "레인저",
    "attackType": "정신",
    "image": "./images/savior/UFS_NKM_UNIT_S_WEST_ROD.webp",
    "summary": "업로드한 엑셀의 PVE 장비·여정 아르카나 세팅을 반영했습니다.",
    "guideUrl": "https://star-savior-arcana-db.pages.dev/savior",
    "detail": {
      "equipment": {
        "pve": {
          "necklace": "속도",
          "ring": "공격력%",
          "sets": [
            "파괴(4) + 적중(2)",
            "통찰(4) + 적중(2)"
          ],
          "potential": "AX5 - 치명타 확률이 부족한 경우\nAX6 - 치명타 확률이 95% 이상인 경우",
          "note": "정밀(4) 사용시 적중(2) 대신 투지(2) 사용 가능"
        },
        "pvp": {
          "necklace": "해당 엑셀에 없음",
          "ring": "해당 엑셀에 없음",
          "sets": [
            "해당 엑셀은 PVE 세팅표입니다."
          ],
          "potential": "해당 엑셀에 없음",
          "note": "PVP 데이터는 표시하지 않습니다."
        }
      },
      "arcana": {
        "pve": [
          {
            "name": "티리아",
            "note": ""
          },
          {
            "name": "카넬리아",
            "note": ""
          },
          {
            "name": "바니걸 프레이",
            "note": ""
          },
          {
            "name": "로자리아",
            "note": ""
          },
          {
            "name": "벨리스 or 린(인내)",
            "note": "엑셀 선택 추천"
          }
        ],
        "pvp": [
          null,
          null,
          null,
          null,
          null
        ],
        "alternatives": [
          null,
          null,
          null,
          null,
          null
        ]
      }
    }
  },
  {
    "id": "harley",
    "name": "할리",
    "subtitle": "헬 세이비어",
    "affiliation": "헬 세이비어",
    "grade": "SSR",
    "element": "sun",
    "className": "디펜더",
    "role": "디펜더",
    "attackType": "충격",
    "image": "./images/savior/UFS_NKM_UNIT_S_WILD_HOG.webp",
    "summary": "PVE 장비 및 아르카나 세팅 반영.",
    "guideUrl": "https://star-savior-arcana-db.pages.dev/savior",
    "detail": {
      "equipment": {
        "pve": {
          "necklace": "속도 / 공격력%",
          "ring": "생명력% / 공격력%",
          "sets": [
            "공격(4) + 투지(2)",
            "생명(4) + 장벽(2)",
            "통찰(4) + 장벽(2)"
          ],
          "potential": "BX / AX1 / EX\n※ AX1은 공격력% 효율이 높거나, 공격력을 가장 높게 맞춰야 하는 경우 사용합니다.",
          "note": "",
          "necklaceOptions": [
            {
              "value": "속도",
              "note": "※ 퓨어탱커, EX"
            },
            {
              "value": "공격력%",
              "note": "※ 공격탱커(AX)"
            }
          ],
          "ringOptions": [
            {
              "value": "생명력%",
              "note": "※ 퓨어탱커, EX"
            },
            {
              "value": "공격력%",
              "note": "※ 공격탱커(AX)"
            }
          ],
          "setOptions": [
            {
              "value": "공격(4) + 투지(2)",
              "note": "※ 공격탱커(AX)"
            },
            {
              "value": "생명(4) + 장벽(2)",
              "note": "※ 퓨어탱커(BX)"
            },
            {
              "value": "통찰(4) + 장벽(2)",
              "note": "※ EX 전용"
            }
          ]
        },
        "pvp": {
          "necklace": "해당 자료에 없음",
          "ring": "해당 자료에 없음",
          "sets": [
            "PVE 세팅표 기준"
          ],
          "potential": "해당 자료에 없음",
          "note": ""
        }
      },
      "arcana": {
        "pve": [
          {
            "name": "에밀리",
            "note": ""
          },
          {
            "name": "린(인내)",
            "note": ""
          },
          {
            "name": "왈세라",
            "note": ""
          },
          {
            "name": "할리 or 베스타",
            "note": "할리 추천 또는 베스타"
          },
          {
            "name": "엘리사 or 힐데 or 바니걸 클레어",
            "note": "엑셀 선택 추천"
          }
        ],
        "pvp": [
          null,
          null,
          null,
          null,
          null
        ],
        "alternatives": [
          null,
          null,
          null,
          null,
          null
        ]
      }
    }
  },
  {
    "id": "petra",
    "name": "페트라",
    "subtitle": "페트라 조합",
    "affiliation": "페트라 조합",
    "grade": "SSR",
    "element": "sun",
    "className": "레인저",
    "role": "레인저",
    "attackType": "충격",
    "image": "./images/savior/UFS_NKM_UNIT_S_CONSTRUCT_BOMB.webp",
    "summary": "업로드한 엑셀의 PVE 장비·여정 아르카나 세팅을 반영했습니다.",
    "guideUrl": "https://star-savior-arcana-db.pages.dev/savior",
    "detail": {
      "equipment": {
        "pve": {
          "necklace": "속도",
          "ring": "공격력%",
          "sets": [
            "파괴(4) + 적중(2)",
            "통찰(4) + 적중(2)"
          ],
          "potential": "AX5 - 치명타 확률이 부족한 경우\nAX6 - 치명타 확률이 95% 이상인 경우",
          "note": "정밀(4) 사용시 적중(2) 대신 투지(2) 사용 가능"
        },
        "pvp": {
          "necklace": "해당 엑셀에 없음",
          "ring": "해당 엑셀에 없음",
          "sets": [
            "해당 엑셀은 PVE 세팅표입니다."
          ],
          "potential": "해당 엑셀에 없음",
          "note": "PVP 데이터는 표시하지 않습니다."
        }
      },
      "arcana": {
        "pve": [
          {
            "name": "공용 아르카나",
            "note": ""
          },
          null,
          null,
          null,
          null
        ],
        "pvp": [
          null,
          null,
          null,
          null,
          null
        ],
        "alternatives": [
          null,
          null,
          null,
          null,
          null
        ]
      }
    }
  },
  {
    "id": "scarlet",
    "name": "스칼렛",
    "subtitle": "리틀 타이런트",
    "affiliation": "리틀 타이런트",
    "grade": "SSR",
    "element": "sun",
    "className": "레인저",
    "role": "레인저",
    "attackType": "충격",
    "image": "./images/savior/UFS_NKM_UNIT_S_BUNNY_SCISSORS.webp",
    "summary": "PVE 장비 및 아르카나 세팅 반영.",
    "guideUrl": "https://star-savior-arcana-db.pages.dev/savior",
    "detail": {
      "equipment": {
        "pve": {
          "necklace": "속도",
          "ring": "공격력%",
          "sets": [
            "통찰(4) + 투지(2)",
            "파괴(4) + 투지(2)"
          ],
          "potential": "AX5 - 치명타 확률이 부족한 경우\nAX6 - 치명타 확률이 95% 이상인 경우",
          "note": ""
        },
        "pvp": {
          "necklace": "해당 자료에 없음",
          "ring": "해당 자료에 없음",
          "sets": [
            "PVE 세팅표 기준"
          ],
          "potential": "해당 자료에 없음",
          "note": ""
        }
      },
      "arcana": {
        "pve": [
          {
            "name": "바니걸 클레어 or 오메가",
            "note": "첫 슬롯 선택"
          },
          {
            "name": "공용 아르카나",
            "note": ""
          },
          {
            "name": "공용 아르카나",
            "note": ""
          },
          {
            "name": "공용 아르카나",
            "note": ""
          },
          {
            "name": "공용 아르카나",
            "note": ""
          }
        ],
        "pvp": [
          null,
          null,
          null,
          null,
          null
        ],
        "alternatives": [
          null,
          null,
          null,
          null,
          null
        ]
      }
    }
  },
  {
    "id": "claire",
    "name": "클레어",
    "subtitle": "플로리스 블루 로즈",
    "affiliation": "플로리스 블루 로즈",
    "grade": "SSR",
    "element": "moon",
    "className": "스트라이커",
    "role": "스트라이커",
    "attackType": "충격",
    "image": "./images/savior/UFS_NKM_UNIT_S_BUNNY_SPEAR.webp",
    "summary": "PVE 장비 및 아르카나 세팅 반영.",
    "guideUrl": "https://star-savior-arcana-db.pages.dev/savior",
    "detail": {
      "equipment": {
        "pve": {
          "necklace": "속도",
          "ring": "공격력%",
          "sets": [
            "통찰(4) + 투지(2)",
            "파괴(4) + 투지(2)"
          ],
          "setNote": "※ 파괴(4) 권장",
          "potential": "AX1 - 공격력% 효율이 높은 구원자",
          "note": ""
        },
        "pvp": {
          "necklace": "해당 자료에 없음",
          "ring": "해당 자료에 없음",
          "sets": [
            "PVE 세팅표 기준"
          ],
          "potential": "해당 자료에 없음",
          "note": ""
        }
      },
      "arcana": {
        "pve": [
          {
            "name": "바니걸 클레어 or 오메가",
            "note": "첫 슬롯 선택"
          },
          {
            "name": "공용 아르카나",
            "note": ""
          },
          {
            "name": "공용 아르카나",
            "note": ""
          },
          {
            "name": "공용 아르카나",
            "note": ""
          },
          {
            "name": "공용 아르카나",
            "note": ""
          }
        ],
        "pvp": [
          null,
          null,
          null,
          null,
          null
        ],
        "alternatives": [
          null,
          null,
          null,
          null,
          null
        ]
      }
    }
  },
  {
    "id": "lacy",
    "name": "레이시",
    "subtitle": "방랑자",
    "affiliation": "방랑자",
    "grade": "SSR",
    "element": "chaos",
    "className": "레인저",
    "role": "레인저",
    "attackType": "원소",
    "image": "./images/savior/UFS_NKM_UNIT_S_INDEPENDENT_DRAGON.webp",
    "summary": "업로드한 엑셀의 PVE 장비·여정 아르카나 세팅을 반영했습니다.",
    "guideUrl": "https://star-savior-arcana-db.pages.dev/savior",
    "detail": {
      "equipment": {
        "pve": {
          "necklace": "속도",
          "ring": "공격력%",
          "sets": [
            "통찰(4) + 적중(2)",
            "공격(4) + 적중(2)"
          ],
          "potential": "AX5 - 치명타 확률이 부족한 경우\nAX6 - 치명타 확률이 95% 이상인 경우",
          "note": "*웨르멘과 함께 운용시 힘(린), 잠재등을 사용하여 파티 최고 공격력 달성 필요"
        },
        "pvp": {
          "necklace": "해당 엑셀에 없음",
          "ring": "해당 엑셀에 없음",
          "sets": [
            "해당 엑셀은 PVE 세팅표입니다."
          ],
          "potential": "해당 엑셀에 없음",
          "note": "PVP 데이터는 표시하지 않습니다."
        }
      },
      "arcana": {
        "pve": [
          {
            "name": "티리아",
            "note": ""
          },
          {
            "name": "카넬리아",
            "note": ""
          },
          {
            "name": "로자리아",
            "note": ""
          },
          {
            "name": "벨리스",
            "note": ""
          },
          {
            "name": "바니걸 프레이",
            "note": "통찰(4) 사용 시"
          }
        ],
        "pvp": [
          null,
          null,
          null,
          null,
          null
        ],
        "alternatives": [
          {
            "name": "린(인내) or 린(힘)",
            "note": "공격(4) 사용 시"
          },
          null,
          null,
          null,
          null
        ]
      }
    }
  },
  {
    "id": "tanya",
    "name": "타냐",
    "subtitle": "페트라 조합",
    "affiliation": "페트라 조합",
    "grade": "SSR",
    "element": "star",
    "className": "스트라이커",
    "role": "스트라이커",
    "attackType": "충격",
    "image": "./images/savior/UFS_NKM_UNIT_S_CONSTRUCT_GADGET.webp",
    "summary": "업로드한 엑셀의 PVE 장비·여정 아르카나 세팅을 반영했습니다.",
    "guideUrl": "https://star-savior-arcana-db.pages.dev/savior",
    "detail": {
      "equipment": {
        "pve": {
          "necklace": "속도",
          "ring": "공격력%",
          "sets": [
            "통찰(4) + 투지(2)",
            "파괴(4) + 투지(2)"
          ],
          "potential": "AX5 - 치명타 확률이 부족한 경우\nAX6 - 치명타 확률이 95% 이상인 경우",
          "note": "파티 치명타 확률증 30%"
        },
        "pvp": {
          "necklace": "해당 엑셀에 없음",
          "ring": "해당 엑셀에 없음",
          "sets": [
            "해당 엑셀은 PVE 세팅표입니다."
          ],
          "potential": "해당 엑셀에 없음",
          "note": "PVP 데이터는 표시하지 않습니다."
        }
      },
      "arcana": {
        "pve": [
          {
            "name": "공용 아르카나",
            "note": ""
          },
          null,
          null,
          null,
          null
        ],
        "pvp": [
          null,
          null,
          null,
          null,
          null
        ],
        "alternatives": [
          null,
          null,
          null,
          null,
          null
        ]
      }
    }
  },
  {
    "id": "lily",
    "name": "릴리",
    "subtitle": "람파디스",
    "affiliation": "람파디스",
    "grade": "SSR",
    "element": "moon",
    "className": "캐스터",
    "role": "캐스터",
    "attackType": "정신",
    "image": "./images/savior/UFS_NKM_UNIT_S_DETECTIVE_WATSON.webp",
    "summary": "PVE 장비 및 아르카나 세팅 반영.",
    "guideUrl": "https://star-savior-arcana-db.pages.dev/savior",
    "detail": {
      "equipment": {
        "pve": {
          "necklace": "속도",
          "ring": "공격력%",
          "sets": [
            "통찰(4) + 투지(2)",
            "파괴(4) + 투지(2)"
          ],
          "potential": "AX5 - 치명타 확률이 부족한 경우\nAX6 - 치명타 확률이 95% 이상인 경우",
          "note": ""
        },
        "pvp": {
          "necklace": "해당 자료에 없음",
          "ring": "해당 자료에 없음",
          "sets": [
            "PVE 세팅표 기준"
          ],
          "potential": "해당 자료에 없음",
          "note": ""
        }
      },
      "arcana": {
        "pve": [
          {
            "name": "티리아",
            "note": ""
          },
          {
            "name": "카넬리아",
            "note": ""
          },
          {
            "name": "뮤리엘",
            "note": ""
          },
          {
            "name": "웨핀델",
            "note": ""
          },
          {
            "name": "바니걸 프레이 or 린(인내)",
            "note": "엑셀 선택 추천"
          }
        ],
        "pvp": [
          null,
          null,
          null,
          null,
          null
        ],
        "alternatives": [
          null,
          null,
          null,
          null,
          null
        ]
      }
    }
  },
  {
    "id": "kyra",
    "name": "키라",
    "subtitle": "키라는 친구같은 거 없어",
    "affiliation": "키라는 친구같은 거 없어",
    "grade": "SSR",
    "element": "sun",
    "className": "어쌔신",
    "role": "어쌔신",
    "attackType": "정신",
    "image": "./images/savior/UFS_NKM_UNIT_S_MUTANT_MASK.webp",
    "summary": "업로드한 엑셀의 PVE 장비·여정 아르카나 세팅을 반영했습니다.",
    "guideUrl": "https://star-savior-arcana-db.pages.dev/savior",
    "detail": {
      "equipment": {
        "pve": {
          "necklace": "속도",
          "ring": "공격력%",
          "sets": [
            "통찰(4) + 적중(2)",
            "파괴(4) + 적중(2)"
          ],
          "potential": "AX5 - 치명타 확률이 부족한 경우\nAX6 - 치명타 확률이 95% 이상인 경우",
          "note": "공명에서 치명타 확률 9% 치명타 피해 12%"
        },
        "pvp": {
          "necklace": "해당 엑셀에 없음",
          "ring": "해당 엑셀에 없음",
          "sets": [
            "해당 엑셀은 PVE 세팅표입니다."
          ],
          "potential": "해당 엑셀에 없음",
          "note": "PVP 데이터는 표시하지 않습니다."
        }
      },
      "arcana": {
        "pve": [
          {
            "name": "단점 보완 맞춤 훈련",
            "note": ""
          },
          {
            "name": "키라만큼 귀여워!",
            "note": ""
          },
          {
            "name": "불굴의 역작",
            "note": ""
          },
          {
            "name": "귀로 없는 여정",
            "note": ""
          },
          {
            "name": "꽃들에게 죽음을",
            "note": ""
          }
        ],
        "pvp": [
          null,
          null,
          null,
          null,
          null
        ],
        "alternatives": [
          {
            "name": "노 페인, 노 게인",
            "note": "단점 보완 맞춤 훈련 대체"
          },
          {
            "name": "하얀 달의 온기는 햇빛처럼 or 어느 한 기사의 맹세 or 완벽한 바니걸",
            "note": "불굴의 역작 대체"
          },
          {
            "name": "메이드 바이 페트라♡ or 별을 보며 꿈을",
            "note": "꽃들에게 죽음을 대체"
          }
        ]
      }
    }
  },
  {
    "id": "waltz-asherah",
    "name": "아세라",
    "subtitle": "왈츠 오브 스타라이트",
    "affiliation": "왈츠 오브 스타라이트",
    "grade": "SSR",
    "element": "order",
    "className": "서포터",
    "role": "서포터",
    "attackType": "참격",
    "image": "./images/savior/UFS_NKM_UNIT_S_DRESS_STRANIS.webp",
    "summary": "업로드한 엑셀의 PVE 장비·여정 아르카나 세팅을 반영했습니다.",
    "guideUrl": "https://star-savior-arcana-db.pages.dev/savior",
    "detail": {
      "equipment": {
        "pve": {
          "necklace": "속도",
          "ring": "공격력% or 생명력%",
          "sets": [
            "통찰(4) + 장벽(2)",
            "파괴(4) + 장벽(2)"
          ],
          "potential": "AX5 - 치명타 확률이 부족한 경우\nAX6 - 치명타 확률이 95% 이상인 경우",
          "note": "",
          "setNotes": [
            "장벽(2)는 투지(2)로 대체가능."
          ]
        },
        "pvp": {
          "necklace": "해당 엑셀에 없음",
          "ring": "해당 엑셀에 없음",
          "sets": [
            "해당 엑셀은 PVE 세팅표입니다."
          ],
          "potential": "해당 엑셀에 없음",
          "note": "PVP 데이터는 표시하지 않습니다."
        }
      },
      "arcana": {
        "pve": [
          {
            "name": "단점 보완 맞춤 훈련",
            "note": ""
          },
          {
            "name": "불굴의 역작",
            "note": ""
          },
          {
            "name": "완벽한 바니걸",
            "note": ""
          },
          {
            "name": "하얀 달의 온기는 햇빛처럼",
            "note": ""
          },
          {
            "name": "꽃들에게 죽음을",
            "note": ""
          }
        ],
        "pvp": [
          null,
          null,
          null,
          null,
          null
        ],
        "alternatives": [
          {
            "name": "노 페인, 노 게인",
            "note": "단점 보완 맞춤 훈련 대체"
          },
          {
            "name": "스트라니스의 영애 or 본 투 비 와일드 or 언더커버 캅",
            "note": "완벽한 바니걸 대체"
          },
          {
            "name": "어느 한 기사의 맹세",
            "note": "하얀 달의 온기는 햇빛처럼 대체"
          },
          {
            "name": "메이드 바이 페트라♡ or 별을 보며 꿈을",
            "note": "꽃들에게 죽음을 대체"
          }
        ]
      }
    }
  },
  {
    "id": "wedding-carmen",
    "name": "카르멘",
    "subtitle": "이터널 프로미스",
    "affiliation": "이터널 프로미스",
    "grade": "SSR",
    "element": "moon",
    "className": "서포터",
    "role": "서포터",
    "attackType": "충격",
    "image": "./images/savior/UFS_NKM_UNIT_S_WEDDING_SHIELDER.webp",
    "summary": "업로드한 엑셀의 PVE 장비·여정 아르카나 세팅을 반영했습니다.",
    "guideUrl": "https://star-savior-arcana-db.pages.dev/savior",
    "detail": {
      "equipment": {
        "pve": {
          "necklace": "속도",
          "ring": "생명력%",
          "sets": [
            "생명(4)+ 장벽(2)"
          ],
          "potential": "BX",
          "note": "반지 주옵 생퍼"
        },
        "pvp": {
          "necklace": "해당 엑셀에 없음",
          "ring": "해당 엑셀에 없음",
          "sets": [
            "해당 엑셀은 PVE 세팅표입니다."
          ],
          "potential": "해당 엑셀에 없음",
          "note": "PVP 데이터는 표시하지 않습니다."
        }
      },
      "arcana": {
        "pve": [
          { "name": "스트라니스의 영애", "note": "" },
          { "name": "가혹한 시련", "note": "" },
          { "name": "나른한 오후의 틈새", "note": "" },
          { "name": "하얀 달의 온기는 햇빛처럼", "note": "" },
          { "name": "꽃들에게 죽음을", "note": "" }
        ],
        "pvp": [
          null,
          null,
          null,
          null,
          null
        ],
        "alternatives": [
          { "name": "어느 한 기사의 맹세", "note": "하얀 달의 온기는 햇빛처럼 대체" },
          { "name": "공녀, 왕좌에 오르다 or 본 투 비 와일드 or 완벽한 바니걸 or 누구보다 프로페셔널 or 언더커버 캅", "note": "부족한 자리 대체" },
          { "name": "하늘의 시련 or 금단의 기록물 Vol. 1", "note": "부족한 자리 대체" },
          null,
          null
        ]
      }
    }
  },
  {
    "id": "wedding-epindel",
    "name": "에핀델",
    "subtitle": "블레싱 인 블룸",
    "affiliation": "블레싱 인 블룸",
    "grade": "SSR",
    "element": "sun",
    "className": "캐스터",
    "role": "캐스터",
    "attackType": "참격",
    "image": "./images/savior/UFS_NKM_UNIT_S_WEDDING_DUALSWORD.webp",
    "summary": "업로드한 엑셀의 PVE 장비·여정 아르카나 세팅을 반영했습니다.",
    "guideUrl": "https://star-savior-arcana-db.pages.dev/savior",
    "detail": {
      "equipment": {
        "pve": {
          "necklace": "속도",
          "ring": "공격력%",
          "sets": [
            "통찰(4) + 적중(2)",
            "파괴(4) + 적중(2)"
          ],
          "potential": "AX5 - 치명타 확률이 부족한 경우\nAX6 - 치명타 확률이 95% 이상인 경우",
          "note": "투지(2) 사용 가능"
        },
        "pvp": {
          "necklace": "해당 엑셀에 없음",
          "ring": "해당 엑셀에 없음",
          "sets": [
            "해당 엑셀은 PVE 세팅표입니다."
          ],
          "potential": "해당 엑셀에 없음",
          "note": "PVP 데이터는 표시하지 않습니다."
        }
      },
      "arcana": {
        "pve": [
          {
            "name": "티리아",
            "note": ""
          },
          {
            "name": "카넬리아",
            "note": ""
          },
          {
            "name": "뮤리엘",
            "note": ""
          },
          {
            "name": "웨핀델",
            "note": ""
          },
          {
            "name": "바니걸 프레이 or 린(인내)",
            "note": "엑셀 선택 추천"
          }
        ],
        "pvp": [
          null,
          null,
          null,
          null,
          null
        ],
        "alternatives": [
          null,
          null,
          null,
          null,
          null
        ]
      }
    }
  },
  {
    "id": "bunny-frey",
    "name": "프레이",
    "subtitle": "노블 프린세스",
    "affiliation": "노블 프린세스",
    "grade": "SSR",
    "element": "moon",
    "className": "캐스터",
    "role": "캐스터",
    "attackType": "충격",
    "image": "./images/savior/UFS_NKM_UNIT_S_BUNNY_PRAY.webp",
    "summary": "업로드한 엑셀의 PVE 장비·여정 아르카나 세팅을 반영했습니다.",
    "guideUrl": "https://star-savior-arcana-db.pages.dev/savior",
    "detail": {
      "equipment": {
        "pve": {
          "necklace": "속도",
          "ring": "공격력%",
          "sets": [
            "통찰(4) + 투지(2)",
            "파괴(4) + 투지(2)"
          ],
          "setNote": "※ 파괴(4) 권장",
          "potential": "AX5 - 치명타 확률이 부족한 경우\nAX6 - 치명타 확률이 95% 이상인 경우",
          "note": "파티 치명타 확률증 30%"
        },
        "pvp": {
          "necklace": "해당 엑셀에 없음",
          "ring": "해당 엑셀에 없음",
          "sets": [
            "해당 엑셀은 PVE 세팅표입니다."
          ],
          "potential": "해당 엑셀에 없음",
          "note": "PVP 데이터는 표시하지 않습니다."
        }
      },
      "arcana": {
        "pve": [
          {
            "name": "티리아",
            "note": ""
          },
          {
            "name": "카넬리아",
            "note": ""
          },
          {
            "name": "뮤리엘",
            "note": ""
          },
          {
            "name": "웨핀델",
            "note": ""
          },
          {
            "name": "바니걸 프레이 or 린(인내)",
            "note": "엑셀 선택 추천"
          }
        ],
        "pvp": [
          null,
          null,
          null,
          null,
          null
        ],
        "alternatives": [
          null,
          null,
          null,
          null,
          null
        ]
      }
    }
  },
  {
    "id": "besta",
    "name": "베스타",
    "subtitle": "서부 탈환대",
    "affiliation": "서부 탈환대",
    "grade": "SR",
    "element": "star",
    "className": "디펜더",
    "role": "디펜더",
    "attackType": "충격",
    "image": "./images/savior/UFS_NKM_UNIT_S_WEST_LANCER.webp",
    "summary": "PVE 장비 및 아르카나 세팅 반영.",
    "guideUrl": "https://star-savior-arcana-db.pages.dev/savior",
    "detail": {
      "equipment": {
        "pve": {
          "necklace": "속도 / 공격력%",
          "ring": "생명력% / 공격력%",
          "sets": [
            "공격(4) + 투지(2)",
            "생명(4) + 장벽(2)",
            "통찰(4) + 장벽(2)"
          ],
          "potential": "BX / AX1 / EX\n※ AX1은 공격력% 효율이 높거나, 공격력을 가장 높게 맞춰야 하는 경우 사용합니다.",
          "note": "",
          "necklaceOptions": [
            {
              "value": "속도",
              "note": "※ 퓨어탱커, EX"
            },
            {
              "value": "공격력%",
              "note": "※ 공격탱커(AX)"
            }
          ],
          "ringOptions": [
            {
              "value": "생명력%",
              "note": "※ 퓨어탱커, EX"
            },
            {
              "value": "공격력%",
              "note": "※ 공격탱커(AX)"
            }
          ],
          "setOptions": [
            {
              "value": "공격(4) + 투지(2)",
              "note": "※ 공격탱커(AX)"
            },
            {
              "value": "생명(4) + 장벽(2)",
              "note": "※ 퓨어탱커(BX)"
            },
            {
              "value": "통찰(4) + 장벽(2)",
              "note": "※ EX 전용"
            }
          ]
        },
        "pvp": {
          "necklace": "해당 자료에 없음",
          "ring": "해당 자료에 없음",
          "sets": [
            "PVE 세팅표 기준"
          ],
          "potential": "해당 자료에 없음",
          "note": ""
        }
      },
      "arcana": {
        "pve": [
          {
            "name": "에밀리",
            "note": ""
          },
          {
            "name": "린(인내)",
            "note": ""
          },
          {
            "name": "왈세라",
            "note": ""
          },
          {
            "name": "할리 or 베스타",
            "note": "할리 추천 또는 베스타"
          },
          {
            "name": "엘리사 or 힐데 or 바니걸 클레어",
            "note": "엑셀 선택 추천"
          }
        ],
        "pvp": [
          null,
          null,
          null,
          null,
          null
        ],
        "alternatives": [
          null,
          null,
          null,
          null,
          null
        ]
      }
    }
  },
  {
    "id": "annah",
    "name": "안나",
    "subtitle": "NOA 타운가드",
    "affiliation": "NOA 타운가드",
    "grade": "SR",
    "element": "sun",
    "className": "디펜더",
    "role": "디펜더",
    "attackType": "충격",
    "image": "./images/savior/UFS_NKM_UNIT_S_OFFICER_POLICE.webp",
    "summary": "PVE 장비 및 아르카나 세팅 반영.",
    "guideUrl": "https://star-savior-arcana-db.pages.dev/savior",
    "detail": {
      "equipment": {
        "pve": {
          "necklace": "속도 / 공격력%",
          "ring": "생명력% / 공격력%",
          "sets": [
            "공격(4) + 투지(2)",
            "생명(4) + 장벽(2)",
            "통찰(4) + 장벽(2)"
          ],
          "potential": "BX / AX1 / EX\n※ AX1은 공격력% 효율이 높거나, 공격력을 가장 높게 맞춰야 하는 경우 사용합니다.",
          "note": "",
          "necklaceOptions": [
            {
              "value": "속도",
              "note": "※ 퓨어탱커, EX"
            },
            {
              "value": "공격력%",
              "note": "※ 공격탱커(AX)"
            }
          ],
          "ringOptions": [
            {
              "value": "생명력%",
              "note": "※ 퓨어탱커, EX"
            },
            {
              "value": "공격력%",
              "note": "※ 공격탱커(AX)"
            }
          ],
          "setOptions": [
            {
              "value": "공격(4) + 투지(2)",
              "note": "※ 공격탱커(AX)"
            },
            {
              "value": "생명(4) + 장벽(2)",
              "note": "※ 퓨어탱커(BX)"
            },
            {
              "value": "통찰(4) + 장벽(2)",
              "note": "※ EX 전용"
            }
          ]
        },
        "pvp": {
          "necklace": "해당 자료에 없음",
          "ring": "해당 자료에 없음",
          "sets": [
            "PVE 세팅표 기준"
          ],
          "potential": "해당 자료에 없음",
          "note": ""
        }
      },
      "arcana": {
        "pve": [
          {
            "name": "단점 보완 맞춤 훈련",
            "note": ""
          },
          {
            "name": "누각 위, 유리달 맞이",
            "note": ""
          },
          {
            "name": "조용한 휴식 시간",
            "note": ""
          },
          {
            "name": "꽃들에게 죽음을",
            "note": ""
          },
          {
            "name": "완벽한 바니걸",
            "note": ""
          }
        ],
        "pvp": [
          null,
          null,
          null,
          null,
          null
        ],
        "alternatives": [
          null,
          null,
          null,
          null,
          null
        ]
      }
    }
  },
  {
    "id": "marcille",
    "name": "마르실",
    "subtitle": "페트라 조합",
    "affiliation": "페트라 조합",
    "grade": "SR",
    "element": "sun",
    "className": "어쌔신",
    "role": "어쌔신",
    "attackType": "충격",
    "image": "./images/savior/UFS_NKM_UNIT_S_CONSTRUCT_WRENCH.webp",
    "summary": "PVE 장비 및 아르카나 세팅 반영.",
    "guideUrl": "https://star-savior-arcana-db.pages.dev/savior/1506",
    "detail": {
      "equipment": {
        "pve": {
          "necklace": "속도",
          "ring": "공격력%",
          "sets": [
            "통찰(4) + 투지(2)",
            "파괴(4) + 투지(2)"
          ],
          "potential": "AX5 - 치명타 확률이 부족한 경우\nAX6 - 치명타 확률이 95% 이상인 경우",
          "note": ""
        },
        "pvp": {
          "necklace": "해당 자료에 없음",
          "ring": "해당 자료에 없음",
          "sets": [
            "PVE 세팅표 기준"
          ],
          "potential": "해당 자료에 없음",
          "note": ""
        }
      },
      "arcana": {
        "pve": [
          {
            "name": "단점 보완 맞춤 훈련",
            "note": ""
          },
          {
            "name": "키라만큼 귀여워!",
            "note": ""
          },
          {
            "name": "불굴의 역작",
            "note": ""
          },
          {
            "name": "귀로 없는 여정",
            "note": ""
          },
          {
            "name": "꽃들에게 죽음을",
            "note": ""
          }
        ],
        "pvp": [
          null,
          null,
          null,
          null,
          null
        ],
        "alternatives": [
          {
            "name": "노 페인, 노 게인",
            "note": "단점 보완 맞춤 훈련 대체"
          },
          {
            "name": "하얀 달의 온기는 햇빛처럼 or 어느 한 기사의 맹세 or 완벽한 바니걸",
            "note": "불굴의 역작 대체"
          },
          {
            "name": "메이드 바이 페트라♡ or 별을 보며 꿈을",
            "note": "꽃들에게 죽음을 대체"
          },
          {
            "name": "허수의 개척자",
            "note": "귀로 없는 여정 대체"
          }
        ]
      }
    }
  },
  {
    "id": "vera",
    "name": "베라",
    "subtitle": "배달부 협회",
    "affiliation": "배달부 협회",
    "grade": "SR",
    "element": "moon",
    "className": "서포터",
    "role": "서포터",
    "attackType": "원소",
    "image": "./images/savior/UFS_NKM_UNIT_S_LPU_POST.webp",
    "summary": "PVE 장비 및 아르카나 세팅 반영.",
    "guideUrl": "https://star-savior-arcana-db.pages.dev/savior",
    "detail": {
      "equipment": {
        "pve": {
          "necklace": "속도",
          "ring": "생명력%",
          "sets": [
            "생명(4) + 장벽(2)"
          ],
          "potential": "BX",
          "note": ""
        },
        "pvp": {
          "necklace": "해당 자료에 없음",
          "ring": "해당 자료에 없음",
          "sets": [
            "PVE 세팅표 기준"
          ],
          "potential": "해당 자료에 없음",
          "note": ""
        }
      },
      "arcana": {
        "pve": [
          {
            "name": "스트라니스의 영애",
            "note": ""
          },
          {
            "name": "하얀 달의 온기는 햇빛처럼",
            "note": ""
          },
          {
            "name": "공녀, 왕좌에 오르다",
            "note": ""
          },
          {
            "name": "완벽한 바니걸",
            "note": ""
          },
          {
            "name": "본 투 비 와일드 or 하늘의 시련 or 금단의 기록물 Vol. 1",
            "note": ""
          }
        ],
        "pvp": [
          null,
          null,
          null,
          null,
          null
        ],
        "alternatives": [
          null,
          null,
          null,
          null,
          null
        ]
      }
    }
  },
  {
    "id": "naru",
    "name": "나루",
    "subtitle": "궤도 수색대",
    "affiliation": "궤도 수색대",
    "grade": "SR",
    "element": "star",
    "className": "레인저",
    "role": "레인저",
    "attackType": "원소",
    "image": "./images/savior/UFS_NKM_UNIT_S_NOA_OBSERVER.webp",
    "summary": "PVE 장비 및 아르카나 세팅 반영.",
    "guideUrl": "https://star-savior-arcana-db.pages.dev/savior/1508",
    "detail": {
      "equipment": {
        "pve": {
          "necklace": "속도",
          "ring": "공격력%",
          "sets": [
            "통찰(4) + 투지(2)",
            "파괴(4) + 투지(2)"
          ],
          "potential": "AX5 - 치명타 확률이 부족한 경우\nAX6 - 치명타 확률이 95% 이상인 경우",
          "note": ""
        },
        "pvp": {
          "necklace": "해당 자료에 없음",
          "ring": "해당 자료에 없음",
          "sets": [
            "PVE 세팅표 기준"
          ],
          "potential": "해당 자료에 없음",
          "note": ""
        }
      },
      "arcana": {
        "pve": [
          {
            "name": "바니걸 클레어 or 오메가",
            "note": "첫 슬롯 선택"
          },
          {
            "name": "공용 아르카나",
            "note": ""
          },
          {
            "name": "공용 아르카나",
            "note": ""
          },
          {
            "name": "공용 아르카나",
            "note": ""
          },
          {
            "name": "공용 아르카나",
            "note": ""
          }
        ],
        "pvp": [
          null,
          null,
          null,
          null,
          null
        ],
        "alternatives": [
          null,
          null,
          null,
          null,
          null
        ]
      }
    }
  },
  {
    "id": "bunny-claire",
    "name": "클레어",
    "subtitle": "캔들 스퀘어",
    "affiliation": "캔들 스퀘어",
    "grade": "SR",
    "element": "moon",
    "className": "어쌔신",
    "role": "어쌔신",
    "attackType": "참격",
    "image": "./images/savior/UFS_NKM_UNIT_S_MAID_SPEAR.webp",
    "summary": "업로드한 엑셀의 PVE 장비·여정 아르카나 세팅을 반영했습니다.",
    "guideUrl": "https://star-savior-arcana-db.pages.dev/savior/1509",
    "detail": {
      "equipment": {
        "pve": {
          "necklace": "속도",
          "ring": "공격력%",
          "sets": [
            "통찰(4) + 투지(2)",
            "파괴(4) + 투지(2)"
          ],
          "potential": "AX5 - 치명타 확률이 부족한 경우\nAX6 - 치명타 확률이 95% 이상인 경우",
          "note": "자체 치명타 확률증 (6~10%)x3턴 *바클 사용시 샤를을 린(인내)로 변경"
        },
        "pvp": {
          "necklace": "해당 엑셀에 없음",
          "ring": "해당 엑셀에 없음",
          "sets": [
            "해당 엑셀은 PVE 세팅표입니다."
          ],
          "potential": "해당 엑셀에 없음",
          "note": "PVP 데이터는 표시하지 않습니다."
        }
      },
      "arcana": {
        "pve": [
          {
            "name": "단점 보완 맞춤 훈련",
            "note": ""
          },
          {
            "name": "키라만큼 귀여워!",
            "note": ""
          },
          {
            "name": "불굴의 역작",
            "note": ""
          },
          {
            "name": "귀로 없는 여정",
            "note": ""
          },
          {
            "name": "꽃들에게 죽음을",
            "note": ""
          }
        ],
        "pvp": [
          null,
          null,
          null,
          null,
          null
        ],
        "alternatives": [
          {
            "name": "노 페인, 노 게인",
            "note": "단점 보완 맞춤 훈련 대체"
          },
          {
            "name": "하얀 달의 온기는 햇빛처럼 or 어느 한 기사의 맹세 or 완벽한 바니걸",
            "note": "불굴의 역작 대체"
          },
          {
            "name": "메이드 바이 페트라♡ or 별을 보며 꿈을",
            "note": "꽃들에게 죽음을 대체"
          },
          {
            "name": "허수의 개척자",
            "note": "귀로 없는 여정 대체"
          }
        ]
      }
    }
  },
  {
    "id": "bunny-scarlet",
    "name": "스칼렛",
    "subtitle": "캔들 스퀘어",
    "affiliation": "캔들 스퀘어",
    "grade": "SR",
    "element": "sun",
    "className": "스트라이커",
    "role": "스트라이커",
    "attackType": "원소",
    "image": "./images/savior/UFS_NKM_UNIT_S_MAID_SCISSORS.webp",
    "summary": "PVE 장비 및 아르카나 세팅 반영.",
    "guideUrl": "https://star-savior-arcana-db.pages.dev/savior/1510",
    "detail": {
      "equipment": {
        "pve": {
          "necklace": "속도",
          "ring": "공격력%",
          "sets": [
            "통찰(4) + 투지(2)",
            "파괴(4) + 투지(2)"
          ],
          "potential": "AX5 - 치명타 확률이 부족한 경우\nAX6 - 치명타 확률이 95% 이상인 경우",
          "note": ""
        },
        "pvp": {
          "necklace": "해당 자료에 없음",
          "ring": "해당 자료에 없음",
          "sets": [
            "PVE 세팅표 기준"
          ],
          "potential": "해당 자료에 없음",
          "note": ""
        }
      },
      "arcana": {
        "pve": [
          {
            "name": "바니걸 클레어 or 오메가",
            "note": "첫 슬롯 선택"
          },
          {
            "name": "공용 아르카나",
            "note": ""
          },
          {
            "name": "공용 아르카나",
            "note": ""
          },
          {
            "name": "공용 아르카나",
            "note": ""
          },
          {
            "name": "공용 아르카나",
            "note": ""
          }
        ],
        "pvp": [
          null,
          null,
          null,
          null,
          null
        ],
        "alternatives": [
          null,
          null,
          null,
          null,
          null
        ]
      }
    }
  },
  {
    "id": "clarissa",
    "name": "클라리사",
    "subtitle": "카노푸스 경비대",
    "affiliation": "카노푸스 경비대",
    "grade": "SR",
    "element": "star",
    "className": "레인저",
    "role": "레인저",
    "attackType": "충격",
    "image": "./images/savior/UFS_NKM_UNIT_S_MAGICIAN_SNIPER.webp",
    "summary": "PVE 장비 및 아르카나 세팅 반영.",
    "guideUrl": "https://star-savior-arcana-db.pages.dev/savior/1511",
    "detail": {
      "equipment": {
        "pve": {
          "necklace": "속도",
          "ring": "공격력%",
          "sets": [
            "파괴(4) + 적중(2)",
            "통찰(4) + 적중(2)"
          ],
          "setNote": "※ 파괴(4) 권장",
          "potential": "AX5 - 치명타 확률이 부족한 경우\nAX6 - 치명타 확률이 95% 이상인 경우",
          "note": ""
        },
        "pvp": {
          "necklace": "해당 자료에 없음",
          "ring": "해당 자료에 없음",
          "sets": [
            "PVE 세팅표 기준"
          ],
          "potential": "해당 자료에 없음",
          "note": ""
        }
      },
      "arcana": {
        "pve": [
          {
            "name": "바니걸 클레어 or 오메가",
            "note": "첫 슬롯 선택"
          },
          {
            "name": "공용 아르카나",
            "note": ""
          },
          {
            "name": "공용 아르카나",
            "note": ""
          },
          {
            "name": "공용 아르카나",
            "note": ""
          },
          {
            "name": "공용 아르카나",
            "note": ""
          }
        ],
        "pvp": [
          null,
          null,
          null,
          null,
          null
        ],
        "alternatives": [
          null,
          null,
          null,
          null,
          null
        ]
      }
    }
  },
  {
    "id": "hilde",
    "name": "힐데",
    "subtitle": "펜릴 소대",
    "affiliation": "펜릴 소대",
    "grade": "SSR",
    "element": "sun",
    "className": "디펜더",
    "role": "디펜더",
    "attackType": "충격",
    "image": "./images/savior/UFS_NKM_UNIT_S_COUNTERSIDE_HILDE.webp",
    "summary": "업로드한 엑셀의 PVE 장비·여정 아르카나 세팅을 반영했습니다.",
    "guideUrl": "https://star-savior-arcana-db.pages.dev/savior",
    "detail": {
      "equipment": {
        "pve": {
          "necklace": "속도 / 공격력%",
          "ring": "생명력% / 공격력%",
          "sets": [
            "공격(4) + 투지(2)",
            "생명(4) + 장벽(2)",
            "통찰(4) + 장벽(2)"
          ],
          "potential": "BX / AX1 / EX\n※ AX1은 공격력% 효율이 높거나, 공격력을 가장 높게 맞춰야 하는 경우 사용합니다.",
          "note": "반지 주옵 생퍼",
          "necklaceOptions": [
            {
              "value": "속도",
              "note": "※ 퓨어탱커, EX"
            },
            {
              "value": "공격력%",
              "note": "※ 공격탱커(AX)"
            }
          ],
          "ringOptions": [
            {
              "value": "생명력%",
              "note": "※ 퓨어탱커, EX"
            },
            {
              "value": "공격력%",
              "note": "※ 공격탱커(AX)"
            }
          ],
          "setOptions": [
            {
              "value": "공격(4) + 투지(2)",
              "note": "※ 공격탱커(AX)"
            },
            {
              "value": "생명(4) + 장벽(2)",
              "note": "※ 퓨어탱커(BX)"
            },
            {
              "value": "통찰(4) + 장벽(2)",
              "note": "※ EX 전용"
            }
          ]
        },
        "pvp": {
          "necklace": "해당 엑셀에 없음",
          "ring": "해당 엑셀에 없음",
          "sets": [
            "해당 엑셀은 PVE 세팅표입니다."
          ],
          "potential": "해당 엑셀에 없음",
          "note": "PVP 데이터는 표시하지 않습니다."
        }
      },
      "arcana": {
        "pve": [
          {
            "name": "에밀리",
            "note": ""
          },
          {
            "name": "린(인내)",
            "note": ""
          },
          {
            "name": "왈세라",
            "note": ""
          },
          {
            "name": "할리 or 베스타",
            "note": "할리 추천 또는 베스타"
          },
          {
            "name": "힐데 or 엘리사 or 바니걸 클레어",
            "note": "엑셀 선택 추천"
          }
        ],
        "pvp": [
          null,
          null,
          null,
          null,
          null
        ],
        "alternatives": [
          null,
          null,
          null,
          null,
          null
        ]
      }
    }
  },
  {
    "id": "yoo-mina",
    "name": "유미나",
    "subtitle": "펜릴 소대",
    "affiliation": "펜릴 소대",
    "grade": "SSR",
    "element": "star",
    "className": "레인저",
    "role": "레인저",
    "attackType": "충격",
    "image": "./images/savior/UFS_NKM_UNIT_S_COUNTERSIDE_MINA.webp",
    "summary": "업로드한 엑셀의 PVE 장비·여정 아르카나 세팅을 반영했습니다.",
    "guideUrl": "https://star-savior-arcana-db.pages.dev/savior",
    "detail": {
      "equipment": {
        "pve": {
          "necklace": "속도",
          "ring": "공격력%",
          "sets": [
            "통찰(4) + 투지(2)",
            "파괴(4) + 투지(2)"
          ],
          "potential": "AX5 - 치명타 확률이 부족한 경우\nAX6 - 치명타 확률이 95% 이상인 경우",
          "note": "별도 비고 없음"
        },
        "pvp": {
          "necklace": "해당 엑셀에 없음",
          "ring": "해당 엑셀에 없음",
          "sets": [
            "해당 엑셀은 PVE 세팅표입니다."
          ],
          "potential": "해당 엑셀에 없음",
          "note": "PVP 데이터는 표시하지 않습니다."
        }
      },
      "arcana": {
        "pve": [
          {
            "name": "티리아",
            "note": ""
          },
          {
            "name": "카넬리아",
            "note": ""
          },
          {
            "name": "바니걸 프레이",
            "note": ""
          },
          {
            "name": "로자리아",
            "note": ""
          },
          {
            "name": "벨리스 or 린(인내)",
            "note": "엑셀 선택 추천"
          }
        ],
        "pvp": [
          null,
          null,
          null,
          null,
          null
        ],
        "alternatives": [
          null,
          null,
          null,
          null,
          null
        ]
      }
    }
  },
  {
    "id": "rosaria",
    "name": "로자리아",
    "subtitle": "폴른 호크",
    "affiliation": "폴른 호크",
    "grade": "SSR",
    "element": "chaos",
    "className": "레인저",
    "role": "레인저",
    "attackType": "원소",
    "image": "./images/savior/UFS_NKM_UNIT_S_COUNTERSIDE_ROSARIA.webp",
    "summary": "업로드한 엑셀의 PVE 장비·여정 아르카나 세팅을 반영했습니다.",
    "guideUrl": "https://star-savior-arcana-db.pages.dev/savior",
    "detail": {
      "equipment": {
        "pve": {
          "necklace": "속도",
          "ring": "공격력%",
          "sets": [
            "파괴(4) + 적중(2)",
            "통찰(4) + 적중(2)"
          ],
          "setNote": "※ 파괴(4) 권장",
          "potential": "AX5 - 치명타 확률이 부족한 경우\nAX6 - 치명타 확률이 95% 이상인 경우",
          "note": "투지(2) 사용 가능"
        },
        "pvp": {
          "necklace": "해당 엑셀에 없음",
          "ring": "해당 엑셀에 없음",
          "sets": [
            "해당 엑셀은 PVE 세팅표입니다."
          ],
          "potential": "해당 엑셀에 없음",
          "note": "PVP 데이터는 표시하지 않습니다."
        }
      },
      "arcana": {
        "pve": [
          {
            "name": "티리아",
            "note": ""
          },
          {
            "name": "카넬리아",
            "note": ""
          },
          {
            "name": "바니걸 프레이",
            "note": ""
          },
          {
            "name": "로자리아",
            "note": ""
          },
          {
            "name": "벨리스 or 린(인내)",
            "note": "엑셀 선택 추천"
          }
        ],
        "pvp": [
          null,
          null,
          null,
          null,
          null
        ],
        "alternatives": [
          null,
          null,
          null,
          null,
          null
        ]
      }
    }
  },
  {
    "id": "white-pearl-luna",
    "name": "루나",
    "subtitle": "화이트 펄 트랩",
    "affiliation": "화이트 펄 트랩",
    "grade": "SSR",
    "element": "sun",
    "className": "디펜더",
    "role": "디펜더",
    "attackType": "원소",
    "image": "./images/savior/UFS_NKM_UNIT_S_SUMMER_ORACLE.webp",
    "summary": "원본 자료 기준 PVE 장비·아르카나 세팅을 반영했습니다.",
    "guideUrl": "https://star-savior-arcana-db.pages.dev/savior/1045",
    "detail": {
      "equipment": {
        "pve": {
          "necklace": "속도",
          "ring": "공격력%",
          "sets": [
            "통찰(4) + 적중(2)",
            "공격(4) + 적중(2)",
            "정밀(4) + 적중(2)"
          ],
          "setNote": "* 적중(2)는 투지(2)로 대체가능.",
          "potential": "AX1 / EX\n※ AX1은 공격력% 효율이 높거나, 공격력을 가장 높게 맞춰야 하는 경우 사용합니다.",
          "note": ""
        },
        "pvp": {
          "necklace": "미정",
          "ring": "미정",
          "sets": [
            "미정"
          ],
          "potential": "미정",
          "note": "장비 세팅 미정"
        }
      },
      "arcana": {
        "pve": [
          {
            "name": "단점 보완 맞춤 훈련",
            "note": ""
          },
          {
            "name": "빛을 쫓아라!",
            "note": ""
          },
          {
            "name": "조용한 휴식 시간 or 본 투 비 와일드 or 만족스러운 식사 or 언더커버 캅",
            "note": ""
          },
          {
            "name": "하얀 달의 온기는 햇빛처럼 or 영원 속박의 굴레",
            "note": ""
          },
          {
            "name": "꽃들에게 죽음을",
            "note": ""
          }
        ],
        "pvp": [
          null,
          null,
          null,
          null,
          null
        ],
        "alternatives": [
          {
            "name": "노 페인, 노 게인",
            "note": "단점 보완 맞춤 훈련 대체"
          },
          {
            "name": "어느 한 기사의 맹세 or 누각 위, 유리달 맞이",
            "note": "하얀 달의 온기는 햇빛처럼/불굴의 역작 대체"
          },
          {
            "name": "메이드 바이 페트라♡ or 별을 보며 꿈을",
            "note": "꽃들에게 죽음을 대체"
          }
        ]
      }
    }
  },
  {
    "id": "sunshine-cat-smile",
    "name": "스마일",
    "subtitle": "선샤인 캣",
    "affiliation": "선샤인 캣",
    "grade": "SSR",
    "element": "star",
    "className": "어쌔신",
    "role": "어쌔신",
    "attackType": "원소",
    "image": "./images/savior/UFS_NKM_UNIT_S_SUMMER_SMILE.webp",
    "summary": "PVE 장비·아르카나 세팅을 반영했습니다.",
    "guideUrl": "https://star-savior-arcana-db.pages.dev/savior/1046",
    "detail": {
      "equipment": {
        "pve": {
          "necklace": "속도",
          "ring": "공격력%",
          "sets": [
            "통찰(4) + 적중(2)",
            "정밀(4) + 적중(2)",
            "파괴(4) + 적중(2)"
          ],
          "setNotes": [
            "* 적중(2)는 투지(2)로 대체가능.",
            "* 효과적중 150% 이상 권장"
          ],
          "potential": "AX5 - 치명타 확률이 부족한 경우\nAX6 - 치명타 확률이 95% 이상인 경우",
          "note": ""
        },
        "pvp": {
          "necklace": "미정",
          "ring": "미정",
          "sets": [
            "미정"
          ],
          "potential": "미정",
          "note": "미정"
        }
      },
      "arcana": {
        "pve": [
          {
            "name": "단점 보완 맞춤 훈련",
            "note": ""
          },
          {
            "name": "키라만큼 귀여워!",
            "note": ""
          },
          {
            "name": "휴가 준비는 쇼핑에서부터!",
            "note": ""
          },
          {
            "name": "귀로 없는 여정",
            "note": ""
          },
          {
            "name": "꽃들에게 죽음을",
            "note": ""
          }
        ],
        "pvp": [
          null,
          null,
          null,
          null,
          null
        ],
        "alternatives": [
          {
            "name": "노 페인, 노 게인 or 불굴의 역작 or 허수의 개척자",
            "note": "단점 보완 맞춤 훈련 대체"
          },
          {
            "name": "메이드 바이 페트라♡ or 별을 보며 꿈을",
            "note": "꽃들에게 죽음을 대체"
          }
        ]
      }
    }
  },
  {
    "id": "professor-m",
    "name": "프로페서M",
    "subtitle": "람파디스",
    "affiliation": "람파디스",
    "grade": "SSR",
    "element": "moon",
    "className": "레인저",
    "role": "레인저",
    "attackType": "정신",
    "image": "./data/savior-detail-assets/프로페서M.webp",
    "summary": "신규 구원자 데이터 반영.",
    "guideUrl": "https://ss.espr.gg/ko/database/characters/professor-m",
    "detail": {
      "equipment": {
        "pve": {
          "necklace": "속도",
          "ring": "공격력%",
          "sets": [
            "통찰(4) + 적중(2)",
            "파괴(4) + 적중(2)",
            "정밀(4) + 적중(2)"
          ],
          "setNotes": [
            "적중(2)는 투지(2)로 대체가능."
          ],
          "potential": "AX5 - 치명타 확률이 부족한 경우\nAX6 - 치명타 확률이 95% 이상인 경우",
          "note": ""
        },
        "pvp": {"necklace":"미정","ring":"미정","sets":["미정"],"potential":"미정","note":"미정"}
      },
      "arcana": {
        "pve": [
          { "name": "단점 보완 맞춤 훈련", "note": "" },
          { "name": "불굴의 역작", "note": "" },
          { "name": "허수의 개척자", "note": "" },
          { "name": "탐닉자의 유흥거리", "note": "" },
          { "name": "꽃들에게 죽음을", "note": "" }
        ],
        "pvp": PENDING_ARCANA(),
        "alternatives": [
          { "name": "노 페인, 노 게인", "note": "단점 맞춤 훈련 대체" },
          { "name": "하얀 달의 온기는 햇빛처럼 or 어느 한 기사의 맹세 or 완벽한 바니걸 or 영원 속박의 굴레", "note": "불굴의 역작 대체" },
          { "name": "메이드 바이 페트라♡ or 별을 보며 꿈을 or 깊은 애도", "note": "꽃들에게 죽음을 대체" }
        ]
      }
    }
  },
  {
    "id": "amora",
    "name": "아모라",
    "subtitle": "스트라니스 백작가",
    "affiliation": "스트라니스 백작가",
    "grade": "SSR",
    "element": "order",
    "className": "어쌔신",
    "role": "어쌔신",
    "attackType": "참격",
    "image": "",
    "summary": "신규 구원자 데이터 반영.",
    "guideUrl": "https://star-savior-arcana-db.pages.dev/savior",
    "detail": {
      "arcana": {
        "pvp": [
          null,
          null,
          null,
          null,
          null
        ],
        "pve": [
          {
            "name": "단점 보완 맞춤 훈련",
            "note": ""
          },
          {
            "name": "키라만큼 귀여워!",
            "note": ""
          },
          {
            "name": "불굴의 역작",
            "note": ""
          },
          {
            "name": "귀로 없는 여정",
            "note": ""
          },
          {
            "name": "꽃들에게 죽음을",
            "note": ""
          }
        ],
        "alternatives": [
          {
            "name": "노 페인, 노 게인",
            "note": "단점 보완 맞춤 훈련 대체"
          },
          {
            "name": "하얀 달의 온기는 햇빛처럼 or 어느 한 기사의 맹세 or 완벽한 바니걸",
            "note": "불굴의 역작 대체"
          },
          {
            "name": "메이드 바이 페트라♡ or 별을 보며 꿈을",
            "note": "꽃들에게 죽음을 대체"
          },
          {
            "name": "허수의 개척자",
            "note": "귀로 없는 여정 대체"
          }
        ]
      },
      "equipment": {
        "pve": {
          "necklace": "속도",
          "ring": "공격력%",
          "sets": [
            "통찰(4) + 적중(2)",
            "파괴(4) + 적중(2)",
            "정밀(4) + 적중(2)"
          ],
          "setNotes": [
            "적중(2)는 투지(2)로 대체가능."
          ],
          "potential": "AX5 - 치명타 확률이 부족한 경우\nAX6 - 치명타 확률이 95% 이상인 경우",
          "note": ""
        },
        "pvp": {
          "necklace": "미정",
          "ring": "미정",
          "sets": [
            "미정"
          ],
          "potential": "미정",
          "note": "미정"
        }
      }
    }
  },
  {
    "id": "ceres-sun-supporter",
    "name": "세레스",
    "subtitle": "샤프 앤 스위트",
    "affiliation": "서부 탈환대",
    "grade": "SSR",
    "element": "sun",
    "className": "서포터",
    "role": "서포터",
    "attackType": "참격",
    "image": "./data/savior-detail-assets/1059-portrait.webp",
    "summary": "ESPR 구원자 정보를 반영했습니다. PVE 세팅 정보는 미정입니다.",
    "guideUrl": "https://ss.espr.gg/ko/database/characters/ceres-sun-supporter"
  }
];

const STANDARD_SUPPORTER_BUILD_IDS = new Set([
  "vera",
  "elisa",
  "frey",
  "ceres-sun-supporter"
]);

SAVIORS.forEach((savior) => {
  if (!STANDARD_SUPPORTER_BUILD_IDS.has(savior.id)) return;

  savior.detail = {
    ...(savior.detail || {}),
    equipment: {
      ...(savior.detail?.equipment || {}),
      pve: {
        necklace: "속도",
        ring: "생명력%",
        sets: ["생명(4) + 장벽(2)"],
        potential: "BX",
        note: ""
      }
    },
    arcana: {
      ...(savior.detail?.arcana || {}),
      pve: [
        { name: "스트라니스의 영애", note: "" },
        { name: "가혹한 시련", note: "" },
        { name: "공녀, 왕좌에 오르다 or 본 투 비 와일드 or 완벽한 바니걸", note: "" },
        { name: "하얀 달의 온기는 햇빛처럼", note: "" },
        { name: "꽃들에게 죽음을", note: "" }
      ],
      alternatives: [
        { name: "어느 한 기사의 맹세", note: "하얀 달의 온기는 햇빛처럼 대체" },
        { name: "누구보다 프로페셔널", note: "공녀, 왕좌에 오르다 대체" },
        { name: "언더커버 캅", note: "본 투 비 와일드 대체" },
        { name: "하늘의 시련 or 금단의 기록물 Vol. 1", note: "부족한 자리 대체" },
        null
      ]
    }
  };
});

const ARCANA_CATEGORIES = ["공격", "생명", "방어", "집중", "보호", "속도", "파괴", "통찰"];

const COSMO_GUIDES = [
  ["데모라이기스 : 베타", "https://arca.live/b/starsavior/169383151"],
  ["데모라이기스 : 알파", "https://arca.live/b/starsavior/170276253"],
  ["오르트로스", "https://arca.live/b/starsavior/170566053"],
  ["로자리아", "https://arca.live/b/starsavior/170758057"],
  ["힐데", "https://arca.live/b/starsavior/171215656"],
  ["길레", "https://arca.live/b/starsavior/172436327"],
  ["티리아", "https://arca.live/b/starsavior/172534192"],
  ["불사왕 모굴루스", "https://arca.live/b/starsavior/173207120"],
  ["괴리의 표상", "https://arca.live/b/starsavior/175840063"],
  ["올베로스", "https://arca.live/b/starsavior/177951693"]
];


const EQUIPMENT_MAIN_OPTIONS = [
  ["무기", "공격력", "150", "375"],
  ["장갑", "생명력", "600", "2400"],
  ["갑옷", "방어력", "60", "210"],
  ["목걸이 / 반지", "공격력 증가율(%)", "2.50%", "17.50%"],
  ["목걸이 / 반지", "생명력 증가율(%)", "2.50%", "17.50%"],
  ["목걸이 / 반지", "방어력 증가율(%)", "2.50%", "17.50%"],
  ["신발 / 목걸이", "속도", "18", "33"],
  ["목걸이", "치명타 확률", "3.00%", "18.00%"],
  ["목걸이", "치명타 피해", "4.00%", "22.00%"],
  ["반지", "효과 적중", "5.00%", "27.50%"],
  ["반지", "효과 저항", "5.00%", "27.50%"]
];

const EQUIPMENT_SUB_OPTIONS = [
  {
    group: "동일",
    rows: [
      ["공격력", "16", "21", "26", "30", "35", "40"],
      ["생명력", "86", "112", "138", "163", "189", "215"],
      ["방어력", "8", "10", "13", "15", "18", "20"],
      ["속도", "1", "-", "-", "-", "-", "2"]
    ]
  },
  {
    group: "변경",
    rows: [
      ["공격력, 생명력, 방어력(%)", "0.60%", "0.80%", "1.00%", "1.20%", "1.40%", "1.60%"],
      ["치명타 확률(%)", "1.00%", "1.20%", "1.40%", "1.60%", "1.80%", "2.00%"],
      ["치명타 피해(%)", "1.50%", "1.80%", "2.10%", "2.40%", "2.70%", "3.00%"],
      ["효과적중(%), 효과저항(%)", "1.00%", "1.40%", "1.80%", "2.20%", "2.60%", "3.00%"]
    ]
  }
];



const STRIKER_ARCANA_TARGET_IDS = new Set([
  "asherah-voyager",
  "charlotte",
  "seira",
  "lyn",
  "tyria",
  "roberta",
  "ceres",
  "gwen",
  "claire",
  "tanya",
  "bunny-scarlet"
]);

const createStrikerRecommendedArcana = (saviorId = "") => [
  { name: "단점 보완 맞춤 훈련", note: "" },
  { name: "불굴의 역작", note: "" },
  { name: "꽃들에게 죽음을", note: "" },
  { name: "음독의 각오", note: "" },
  {
    name: saviorId === "gwen"
      ? "자칭 베테랑 탐정의 수사법 or 허수의 개척자"
      : "자칭 베테랑 탐정의 수사법",
    note: ""
  }
];

const createStrikerAlternativeArcana = () => [
  { name: "노 페인, 노 게인", note: "" },
  { name: "메이드 바이 페트라♡ or 별을 보며 꿈을", note: "" },
  { name: "하얀 달의 온기는 햇빛처럼 or 어느 한 기사의 맹세", note: "부족한 자리 대체" },
  { name: "완벽한 바니걸", note: "" },
  null
];

const gwenBuild = SAVIORS.find((savior) => savior.id === "gwen");
if (gwenBuild) {
  gwenBuild.summary = "PVE 장비·아르카나 세팅을 반영했습니다.";
  gwenBuild.detail = {
    equipment: {
      pve: {
        necklace: "속도",
        ring: "공격력%",
        sets: [
          "통찰(4) + 투지(2)",
          "파괴(4) + 투지(2)"
        ],
        potential: "AX5 - 치명타 확률이 부족한 경우\nAX6 - 치명타 확률이 95% 이상인 경우",
        note: ""
      },
      pvp: {
        necklace: "미정",
        ring: "미정",
        sets: ["미정"],
        potential: "미정",
        note: "미정"
      }
    },
    arcana: {
      pve: createStrikerRecommendedArcana("gwen"),
      pvp: PENDING_ARCANA(),
      alternatives: createStrikerAlternativeArcana()
    }
  };
}

SAVIORS.forEach((savior) => {
  if (!STRIKER_ARCANA_TARGET_IDS.has(savior.id) || !savior.detail) return;
  if (!savior.detail.arcana) {
    savior.detail.arcana = {
      pve: [],
      pvp: PENDING_ARCANA(),
      alternatives: []
    };
  }
  savior.detail.arcana.pve = createStrikerRecommendedArcana(savior.id);
  savior.detail.arcana.alternatives = createStrikerAlternativeArcana();
});

const seiraBuild = SAVIORS.find((savior) => savior.id === "seira");
if (seiraBuild?.detail?.arcana) {
  seiraBuild.detail.arcana.pve[4] = {
    name: "수마의 나들이",
    note: ""
  };
  seiraBuild.detail.arcana.alternatives[2] = {
    name: "하얀 달의 온기는 햇빛처럼 or 어느 한 기사의 맹세 or 완벽한 바니걸 or 자칭 베테랑 탐정의 수사법",
    note: "부족한 자리 대체"
  };
  seiraBuild.detail.arcana.alternatives[3] = null;
}

const clarissaBuild = SAVIORS.find((savior) => savior.id === "clarissa");
if (clarissaBuild?.detail?.arcana) {
  clarissaBuild.detail.arcana.pve = [
    { name: "단점 보완 맞춤 훈련", note: "" },
    { name: "불굴의 역작", note: "" },
    { name: "꽃들에게 죽음을", note: "" },
    { name: "완벽한 바니걸", note: "" },
    { name: "탐닉자의 유흥거리", note: "" }
  ];
  clarissaBuild.detail.arcana.alternatives = [
    { name: "노 페인, 노 게인", note: "단점 보완 맞춤 훈련 대체" },
    { name: "메이드 바이 페트라♡ or 별을 보며 꿈을", note: "꽃들에게 죽음을 대체" },
    {
      name: "하얀 달의 온기는 햇빛처럼 or 어느 한 기사의 맹세",
      note: "탐닉자의 유흥거리 대체"
    },
    { name: "영원 속박의 굴레", note: "하얀 달의 온기는 햇빛처럼 대체" },
    null
  ];
}


const SAVIOR_RELEASE_DATE = Object.freeze({
  "lydia-moon-caster": 20261015,
  "gwen": 20261001,
  "professor-m": 20260917,
  "amora": 20260903,
  "cristelle": 20260820,
  "sunshine-cat-smile": 20260806,
  "white-pearl-luna": 20260723,
  "ceres": 20260709,
  "carnelia": 20260625,
  "wedding-epindel": 20260611,
  "wedding-carmen": 20260528,
  "tyria": 20260514,
  "fei": 20260430,
  "lyn": 20260416,
  "rosaria": 20260402,
  "hilde": 20260319,
  "yoo-mina": 20260319,
  "roberta": 20260305,
  "bunny-frey": 20260220,
  "bunny-charlotte": 20260205,
  "emily": 20260122,
  "bell": 20260108,
  "petra": 20251230,
  "waltz-asherah": 20251223,
  "omega": 20251211,
  "scarlet": 20251127,
  "claire": 20251127
});

// 위 목록에 없는 기존 구원자는 정식 런칭(2025-11-20) 시점 출시.
// 이후 새 구원자가 매핑보다 먼저 추가된 경우에는 배열 뒤쪽에 추가되는 기존 작업 흐름을 이용해
// 최신 항목으로 우선 노출되도록 처리한다.
const SAVIOR_LAUNCH_DATE = 20251120;
const SAVIOR_SOURCE_INDEX = new Map(SAVIORS.map((savior, index) => [savior.id, index]));

function getSaviorReleaseSortValue(savior) {
  if (savior.upcoming) return Number.MAX_SAFE_INTEGER;
  if (Object.prototype.hasOwnProperty.call(SAVIOR_RELEASE_DATE, savior.id)) {
    return SAVIOR_RELEASE_DATE[savior.id];
  }

  const sourceIndex = SAVIOR_SOURCE_INDEX.get(savior.id) ?? -1;
  // 현재 53명 안의 미매핑 구원자는 런칭 멤버다.
  // 향후 SAVIORS 배열 끝에 신규 항목이 추가되어 현재 기준 최대 인덱스를 넘는 경우를 위한 안전장치.
  return SAVIOR_LAUNCH_DATE + Math.max(0, sourceIndex - 52) * 100000000;
}

function sortSaviorsByReleaseNewestFirst(saviors) {
  return [...saviors].sort((a, b) => {
    const releaseDiff = getSaviorReleaseSortValue(b) - getSaviorReleaseSortValue(a);
    if (releaseDiff !== 0) return releaseDiff;

    // 같은 날 출시된 구원자는 기존 등록 순서를 유지한다.
    return (SAVIOR_SOURCE_INDEX.get(a.id) ?? 0) - (SAVIOR_SOURCE_INDEX.get(b.id) ?? 0);
  });
}

const state = {
  query: "",
  element: "all",
  className: "all"
};

const listView = document.querySelector("#list-view");
const detailView = document.querySelector("#detail-view");
const simpleView = document.querySelector("#simple-view");
const saviorGrid = document.querySelector("#savior-grid");
const detailContent = document.querySelector("#detail-content");
const simpleContent = document.querySelector("#simple-content");
const searchInput = document.querySelector("#search-input");
const visibleCount = document.querySelector("#visible-count");
const emptyState = document.querySelector("#empty-state");
const resetFilter = document.querySelector("#reset-filter");
const navItems = [...document.querySelectorAll("[data-section]")];
const themeToggle = document.querySelector("#theme-toggle");
const languageSelect = document.querySelector("#language-select");

function cloneDefaultBuild() {
  return JSON.parse(JSON.stringify(DEFAULT_BUILD));
}

function getBuild(savior) {
  const base = cloneDefaultBuild();
  const detail = savior.detail || {};

  return {
    skills: detail.skills || base.skills,
    equipment: {
      pve: { ...base.equipment.pve, ...(detail.equipment?.pve || {}) },
      pvp: { ...base.equipment.pvp, ...(detail.equipment?.pvp || {}) }
    },
    arcana: {
      pve: detail.arcana?.pve || base.arcana.pve,
      pvp: detail.arcana?.pvp || base.arcana.pvp,
      alternatives: detail.arcana?.alternatives || base.arcana.alternatives
    },
    stats: detail.stats || base.stats
  };
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function getInitial(name) {
  return [...String(name || "✦")][0] || "✦";
}

function normalizeGuideSearch(value) {
  return String(value || "")
    .normalize("NFKC")
    .replace(/\s+/g, "")
    .trim()
    .toLocaleLowerCase();
}

function imageMarkup(savior, large = false) {
  const localizedName = getLocalizedSaviorName(savior.name);
  const fallback = `<span class="character-fallback">${escapeHtml(getInitial(localizedName))}</span>`;
  const localProfile = getLocalSaviorProfile(savior);
  // 구원자 대표 이미지는 DB의 초상화만 사용한다. 전신 일러스트는 일러스트 섹션 전용.
  const imageSource = localProfile?.portrait || savior.image || "";
  if (!imageSource) return fallback;

  return `
    <img class="character-image" src="${escapeHtml(imageSource)}" alt="${escapeHtml(localizedName)}"
      onerror="this.remove(); this.parentElement.insertAdjacentHTML('beforeend', '${fallback.replaceAll("'", "&#039;")}')">
  `;
}

function renderList() {
  const q = normalizeGuideSearch(state.query);

  const filtered = sortSaviorsByReleaseNewestFirst(SAVIORS.filter((savior) => {
    const haystack = [
      savior.name,
      getLocalizedSaviorName(savior.name),
      savior.subtitle,
      getLocalizedSubtitle(savior.subtitle),
      savior.affiliation,
      getLocalizedSubtitle(savior.affiliation),
      savior.className,
      translateString(savior.className),
      savior.role,
      translateString(savior.role),
      savior.attackType,
      translateString(savior.attackType),
      ELEMENT_LABELS[savior.element],
      translateString(ELEMENT_LABELS[savior.element]),
      getSaviorArchiveSearchText(savior)
    ].join(" ");

    const queryMatch = !q || normalizeGuideSearch(haystack).includes(q);
    const elementMatch = state.element === "all" || savior.element === state.element;
    const classMatch = state.className === "all" || savior.className === state.className;

    return queryMatch && elementMatch && classMatch;
  }));

  saviorGrid.replaceChildren(...filtered.map(createSaviorCard));
  visibleCount.textContent = String(filtered.length);
  emptyState.hidden = filtered.length > 0;
  applyLanguageToDOM(listView);
}

function createSaviorCard(savior) {
  const card = document.createElement("button");
  card.type = "button";
  card.className = "savior-card";
  card.dataset.element = savior.element;

  const localizedName = getLocalizedSaviorName(savior.name);
  const localizedSubtitle = getLocalizedSubtitle(savior.subtitle);
  const localizedElement = translateString(ELEMENT_LABELS[savior.element]);
  const localizedClass = translateString(savior.className);

  card.setAttribute("aria-label", `${localizedName} ${localizedSubtitle} ${translateString("상세 세팅 보기")}`);

  card.innerHTML = `
    <div class="card-image">
      ${imageMarkup(savior)}
      <span class="attribute-corner">${escapeHtml(localizedElement)}</span>
    </div>
    <div class="card-body">
      <span class="card-grade">${escapeHtml(savior.grade)}</span>
      <strong class="card-name" data-i18n-kind="savior" data-i18n-source="${escapeHtml(savior.name)}">${escapeHtml(localizedName)}</strong>
      <span class="card-subtitle" data-i18n-kind="subtitle" data-i18n-source="${escapeHtml(savior.subtitle)}">${escapeHtml(localizedSubtitle)}</span>
      <div class="card-tags">
        <span class="mini-tag">${escapeHtml(localizedClass)}</span>
        ${savior.upcoming ? `<span class="mini-tag">${escapeHtml(translateString("출시 예정"))}</span>` : ""}
      </div>
    </div>
  `;

  card.addEventListener("click", () => openSavior(savior.id));
  return card;
}

function setActiveNav(section) {
  navItems.forEach((item) => {
    item.classList.toggle("is-active", item.dataset.section === section);
  });
}

function showOnly(view) {
  listView.hidden = view !== "list";
  detailView.hidden = view !== "detail";
  simpleView.hidden = view !== "simple";
}

function openList(options = {}) {
  showOnly("list");
  setActiveNav("savior");

  if (!options.skipHash) {
    history.pushState({ view: "list" }, "", "#savior");
  }

  if (!options.keepScroll) {
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
}

function openSavior(id, options = {}) {
  const savior = SAVIORS.find((item) => item.id === id);
  if (!savior) {
    openList(options);
    return;
  }

  detailContent.innerHTML = createDetailMarkup(savior);
  applyLanguageToDOM(detailView);
  showOnly("detail");
  setActiveNav("savior");

  if (!options.skipHash) {
    history.pushState({ view: "detail", id }, "", `#savior/${encodeURIComponent(id)}`);
  }

  if (!options.keepScroll) {
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  // 신규 아르카나는 구원자 상세에서도 즉시 로컬 백업과 연결한다.
  // 아르카나 탭을 먼저 방문하지 않아도 이미지/상세 링크가 활성화된다.
  if (!arcanaDatabaseState.data) {
    loadArcanaArchive().then((archive) => {
      arcanaDatabaseState.data = archive;

      const currentHash = decodeURIComponent(location.hash || "");
      const expectedHash = `#savior/${id}`;
      if (currentHash !== expectedHash || detailView.hidden) return;

      const activeSavior = SAVIORS.find((item) => item.id === id);
      if (!activeSavior) return;

      detailContent.innerHTML = createDetailMarkup(activeSavior);
      applyLanguageToDOM(detailView);
    }).catch((error) => {
      console.warn("Arcana recommendation archive load failed:", error);
    });
  }
}

function getSaviorBackupUrl(detailId) {
  return `./data/saviors/${encodeURIComponent(detailId)}.html?v=${encodeURIComponent(SITE_BUILD_VERSION)}`;
}

const SAVIOR_SKILL_ARCHIVE_URL = "./data/savior-skills/saviors.json";
const SAVIOR_PROFILE_INDEX_URL = "./data/saviors/index.json";
const SAVIOR_SKILL_TYPE_KEYS = ["패시브", "기본기", "특수기", "궁극기"];
const SAVIOR_SKILL_TYPE_LABELS = {
  ko: ["패시브", "기본기", "특수기", "궁극기"],
  en: ["Passive", "Basic Skill", "Special Skill", "Ultimate"],
  ja: ["パッシブ", "基本技", "特殊技", "究極技"]
};
const SAVIOR_SKILL_TARGET_LABELS = {
  ko: {
    NSTT_ALLY_ALL: "아군 전체", NSTT_ALLY_ONE: "아군 단일", NSTT_ENEMY_ALL: "적 전체", NSTT_ENEMY_ONE: "적 단일",
    NSTT_MYSELF: "자신", NSTT_REACT_ALLY_TARGET: "반응 대상 아군", NSTT_REACT_ENEMY_TARGET: "반응 대상 적"
  },
  en: {
    NSTT_ALLY_ALL: "All Allies", NSTT_ALLY_ONE: "1 Ally", NSTT_ENEMY_ALL: "All Enemies", NSTT_ENEMY_ONE: "1 Enemy",
    NSTT_MYSELF: "Self", NSTT_REACT_ALLY_TARGET: "Target Ally", NSTT_REACT_ENEMY_TARGET: "Target Enemy"
  },
  ja: {
    NSTT_ALLY_ALL: "味方全体", NSTT_ALLY_ONE: "味方単体", NSTT_ENEMY_ALL: "敵全体", NSTT_ENEMY_ONE: "敵単体",
    NSTT_MYSELF: "自身", NSTT_REACT_ALLY_TARGET: "対象の味方", NSTT_REACT_ENEMY_TARGET: "対象の敵"
  }
};
const SAVIOR_SKILL_META_LABELS = {
  ko: { turn: "턴", nova: "노바 획득" },
  en: { turn: "Turn", nova: "Nova Gain" },
  ja: { turn: "ターン", nova: "ノヴァ獲得" }
};
let saviorSkillArchivePromise = null;
let saviorSkillArchiveById = new Map();
let saviorProfileIndexPromise = null;
let saviorProfileIndex = {};

function resolveSaviorDetailId(savior) {
  const staticId = Number(SAVIOR_DETAIL_IDS[savior?.id] || 0);
  if (staticId) return staticId;

  const targetName = String(savior?.name || "").trim();
  if (!targetName) return null;

  for (const [id, entry] of Object.entries(saviorProfileIndex || {})) {
    if (id === "_meta" || !entry?.profile) continue;
    if (String(entry.profile.name || "").trim() === targetName) return Number(entry.id || id) || null;
  }

  for (const archived of saviorSkillArchiveById.values()) {
    if (getArchivedLanguageText(archived?.name, "ko").trim() === targetName) {
      return Number(archived.id) || null;
    }
  }
  return null;
}

function getLocalSaviorProfile(savior) {
  const detailId = resolveSaviorDetailId(savior);
  const storedProfile = saviorProfileIndex?.[String(detailId)]?.profile;
  if (!storedProfile) return null;
  const localizedProfile = storedProfile.localized?.[currentLanguage];
  const profile = localizedProfile ? { ...storedProfile, ...localizedProfile } : storedProfile;

  const normalizeLocalAsset = (value) => String(value || "")
    .replace(/^\.\.\/savior-detail-assets\//, "./data/savior-detail-assets/")
    .replace(/^\.\/savior-detail-assets\//, "./data/savior-detail-assets/")
    .replace(/^savior-detail-assets\//, "./data/savior-detail-assets/");

  const portrait = normalizeLocalAsset(profile.portrait);
  const illustration = normalizeLocalAsset(profile.illustration);

  return portrait === profile.portrait && illustration === profile.illustration
    ? profile
    : { ...profile, portrait, illustration };
}

async function loadSaviorProfileIndex() {
  if (!saviorProfileIndexPromise) {
    const url = `${SAVIOR_PROFILE_INDEX_URL}?v=${encodeURIComponent(SITE_BUILD_VERSION)}`;
    saviorProfileIndexPromise = fetch(url, { cache: "no-store" }).then(async (response) => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const index = await response.json();
      const profiles = Object.values(index || {}).filter((entry) => entry?.profile);
      if (profiles.length < 52) throw new Error(`Invalid Savior profile index (${profiles.length}; expected at least 52)`);

      saviorProfileIndex = index;
      SAVIORS.forEach((savior) => {
        const profile = getLocalSaviorProfile(savior);
        if (profile?.attackType) savior.attackType = profile.attackType;
      });
      return index;
    }).catch((error) => {
      saviorProfileIndexPromise = null;
      throw error;
    });
  }
  return saviorProfileIndexPromise;
}

function getSaviorSkillLanguage(language = currentLanguage) {
  return SUPPORTED_LANGUAGES.includes(language) ? language : "ko";
}

function getArchivedLanguageText(value, language = currentLanguage) {
  const selected = getSaviorSkillLanguage(language);
  return String(value?.[selected] ?? value?.ko ?? "");
}

async function loadSaviorSkillArchive() {
  if (!saviorSkillArchivePromise) {
    const url = `${SAVIOR_SKILL_ARCHIVE_URL}?v=${encodeURIComponent(SITE_BUILD_VERSION)}`;
    saviorSkillArchivePromise = fetch(url, { cache: "no-store" }).then(async (response) => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const archive = await response.json();
      if (!Array.isArray(archive?.saviors) || archive.saviors.length < 52) {
        throw new Error("Invalid Savior skill archive");
      }
      saviorSkillArchiveById = new Map(archive.saviors.map((savior) => [Number(savior.id), savior]));
      return archive;
    }).catch((error) => {
      saviorSkillArchivePromise = null;
      throw error;
    });
  }
  return saviorSkillArchivePromise;
}

function getArchivedSavior(savior) {
  const detailId = resolveSaviorDetailId(savior);
  return saviorSkillArchiveById.get(Number(detailId)) || null;
}

function collectSaviorArchiveSearchStrings(value, output = []) {
  if (typeof value === "string") {
    output.push(value);
    return output;
  }
  if (Array.isArray(value)) {
    value.forEach((item) => collectSaviorArchiveSearchStrings(item, output));
    return output;
  }
  if (value && typeof value === "object") {
    Object.values(value).forEach((item) => collectSaviorArchiveSearchStrings(item, output));
  }
  return output;
}

function getSaviorArchiveSearchText(savior) {
  const archivedSavior = getArchivedSavior(savior);
  const resonancePotentials = Array.isArray(archivedSavior?.resonancePotentials)
    ? archivedSavior.resonancePotentials
    : [];

  const values = [];

  resonancePotentials.forEach((potential) => {
    const koName = getArchivedLanguageText(potential?.name, "ko").trim();

    // 검색 보조 데이터에는 공명 잠재력 명칭만 넣는다.
    // 장비 세트, 스킬/버프 설명의 일반 단어는 절대 포함하지 않는다.
    if (!/의\s*(?:솜씨|감각|재능)\s*$/.test(koName)) return;

    ["ko", "en", "ja"].forEach((language) => {
      const localizedName = getArchivedLanguageText(potential?.name, language).trim();
      if (localizedName) values.push(localizedName);
    });
  });

  return [...new Set(values)].join(" ");
}

function createArchivedSaviorResonanceRows(archivedSavior, language = currentLanguage) {
  return (archivedSavior?.resonancePotentials || []).map((potential) => ({
    level: potential.step,
    title: getArchivedLanguageText(potential.name, language),
    description: getArchivedLanguageText(potential.description, language),
    icon: potential.icon || "",
    background: potential.background || ""
  })).filter((row) => row.title || row.description);
}

function renderSaviorSourceRichText(value) {
  return escapeHtml(value || "")
    .replace(/&lt;b&gt;&lt;color=#([0-9a-f]{6})&gt;/gi, '<strong style="color:#$1">')
    .replace(/&lt;\/color&gt;&lt;\/b&gt;/gi, "</strong>")
    .replace(/&lt;color=#([0-9a-f]{6})&gt;/gi, '<span style="color:#$1">')
    .replace(/&lt;\/color&gt;/gi, "</span>")
    .replace(/&lt;b&gt;/gi, "<strong>")
    .replace(/&lt;\/b&gt;/gi, "</strong>")
    .replace(/&lt;br\s*\/?&gt;/gi, "<br>")
    .replace(/\r?\n/g, "<br>");
}

function createArchivedSaviorSkills(archivedSavior, options = {}) {
  const language = getSaviorSkillLanguage(options.language);
  const sourceSkills = options.blossomed ? archivedSavior?.blossomSkills : archivedSavior?.skills;
  if (!Array.isArray(sourceSkills)) return [];

  return sourceSkills.map((skill) => {
    const typeCode = Number(skill.type);
    const type = SAVIOR_SKILL_TYPE_KEYS[typeCode] || "스킬";
    const labels = SAVIOR_SKILL_META_LABELS[language] || SAVIOR_SKILL_META_LABELS.ko;
    const metas = [];
    if (Number(skill.cooltime) > 0) {
      metas.push(language === "ko" ? `${skill.cooltime}${labels.turn}` : `${skill.cooltime} ${labels.turn}`);
    }
    if (skill.target && skill.target !== "NSTT_INVALID") {
      const target = SAVIOR_SKILL_TARGET_LABELS[language]?.[skill.target] || SAVIOR_SKILL_TARGET_LABELS.ko[skill.target];
      if (target) metas.push(target);
    }
    if (Number(skill.nova) > 0) metas.push(`${labels.nova} ${skill.nova}`);

    const maxLevel = skill.levels?.at(-1);
    const passiveSummaries = typeCode === 0 && Array.isArray(skill.levelSummaries)
      ? skill.levelSummaries
      : null;
    const novaKo = getArchivedLanguageText(skill.novaDescription, "ko");
    return {
      title: getArchivedLanguageText(skill.name, language),
      type,
      typeCode,
      typeLabel: SAVIOR_SKILL_TYPE_LABELS[language]?.[typeCode] || type,
      image: skill.icon || "",
      metas,
      description: getArchivedLanguageText(maxLevel?.skillDescription, language),
      effects: (skill.buffs || []).map((buff) => ({
        image: buff.icon || "",
        name: getArchivedLanguageText(buff.name, language),
        description: getArchivedLanguageText(buff.description, language)
      })),
      novaBurst: novaKo && novaKo !== "구원자" ? getArchivedLanguageText(skill.novaDescription, language) : "",
      levels: (passiveSummaries || skill.levels || []).map((level) => ({
        level: passiveSummaries ? `★${Number(level.level) - 1}` : level.level,
        description: getArchivedLanguageText(passiveSummaries
          ? level.description
          : typeCode === 0 ? level.skillDescription : level.levelDescription, language),
        richText: typeCode === 0
      }))
    };
  });
}

function getSaviorBloomBackupUrl(detailId) {
  return `./data/savior-bloom/${encodeURIComponent(detailId)}.html?v=${encodeURIComponent(SITE_BUILD_VERSION)}`;
}

function setSaviorSourcePanelStatus(panel, sourceText, kind = "") {
  panel.dataset.state = kind;
  panel.innerHTML = `<div class="savior-source-status ${escapeHtml(kind)}">${escapeHtml(translateString(sourceText))}</div>`;
}

function normalizeSaviorSourceText(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

function getSaviorSourceRoot(sourceHtml) {
  const parser = new DOMParser();
  const doc = parser.parseFromString(sourceHtml, "text/html");
  const root = doc.querySelector(".snapshot-root") || doc.querySelector("main") || doc.body;
  if (!root) throw new Error("Snapshot root not found");
  root.querySelectorAll("script,style,noscript,.snapshot-meta").forEach((node) => node.remove());
  return { doc, root };
}

function getSaviorSourceTokens(root) {
  const doc = root.ownerDocument;
  const walker = doc.createTreeWalker(root, 4); // NodeFilter.SHOW_TEXT
  const tokens = [];
  let node;
  while ((node = walker.nextNode())) {
    const parent = node.parentElement;
    if (!parent || parent.closest("script,style,noscript")) continue;
    const text = normalizeSaviorSourceText(node.nodeValue);
    if (!text) continue;
    tokens.push({ text, node, parent });
  }
  return tokens;
}

function findSourceTokenIndex(tokens, matcher, from = 0) {
  for (let i = Math.max(0, from); i < tokens.length; i++) {
    if (matcher(tokens[i].text, tokens[i], i)) return i;
  }
  return -1;
}

function getSourceRangeTokens(tokens, start, end) {
  const from = Math.max(0, start ?? 0);
  const to = end == null || end < 0 ? tokens.length : Math.min(tokens.length, end);
  return tokens.slice(from, to);
}

const SAVIOR_SOURCE_SKILL_TYPES = ["패시브", "기본기", "특수기", "궁극기"];
const SAVIOR_SOURCE_BASE_STATS = [
  ["공격력", false], ["생명력", false], ["방어력", false], ["속도", false],
  ["치명타 확률", true], ["치명타 피해", true], ["효과 적중", true], ["효과 저항", true], ["명중률", true]
];
const SAVIOR_SOURCE_JOURNEY_STATS = ["힘", "체력", "인내", "집중", "보호"];
const SAVIOR_SOURCE_GRADES = ["SSR", "SR", "R"];
const SAVIOR_SOURCE_ELEMENTS = ["태양", "달", "별", "질서", "혼돈"];
const SAVIOR_SOURCE_CLASSES = ["스트라이커", "어쌔신", "레인저", "캐스터", "디펜더", "서포터"];
const SAVIOR_SOURCE_ATTACK_TYPES = ["참격", "충격", "원소", "정신", "타격", "마법"];

function isSourceSkillType(text) {
  return SAVIOR_SOURCE_SKILL_TYPES.includes(normalizeSaviorSourceText(text));
}

function extractSourceNumberToken(text, percentExpected = false) {
  const value = normalizeSaviorSourceText(text);
  if (!value || /^\d{1,3}위$/.test(value)) return "";
  if (percentExpected) return value.match(/[+-]?\d+(?:\.\d+)?%/)?.[0] || "";
  if (/^[+-]?\d{1,3}(?:,\d{3})+(?:\.\d+)?$/.test(value)) return value;
  if (/^[+-]?\d+(?:\.\d+)?$/.test(value)) return value;
  return "";
}

function extractSourceStat(tokens, label, percentExpected = false) {
  const labelIndex = findSourceTokenIndex(tokens, (text) => text === label);
  if (labelIndex < 0) return "";
  const allLabels = new Set([
    ...SAVIOR_SOURCE_BASE_STATS.map(([name]) => name),
    ...SAVIOR_SOURCE_JOURNEY_STATS,
    "기본 스테이터스", "여정 스테이터스", "공명 잠재력"
  ]);
  for (let i = labelIndex + 1; i < Math.min(tokens.length, labelIndex + 8); i++) {
    const text = tokens[i].text;
    if (allLabels.has(text) || text.startsWith("기본 스테이터스")) break;
    const value = extractSourceNumberToken(text, percentExpected);
    if (value) return value;
  }
  return "";
}

function parseSaviorSourceProfile(tokens, baseIndex, savior) {
  const before = getSourceRangeTokens(tokens, 0, baseIndex > 0 ? baseIndex : tokens.length);
  const knownMeta = new Set([
    ...SAVIOR_SOURCE_GRADES,
    ...SAVIOR_SOURCE_ELEMENTS,
    ...SAVIOR_SOURCE_CLASSES,
    ...SAVIOR_SOURCE_ATTACK_TYPES
  ]);

  // 이름이 페이지 다른 위치에도 존재할 수 있으므로, 뒤에 등급/속성/클래스가 이어지는 이름 토큰을 우선한다.
  let nameIndex = -1;
  let bestScore = -1;
  for (let i = 0; i < before.length; i++) {
    if (before[i].text !== savior.name) continue;
    let score = 0;
    for (let j = i + 1; j < Math.min(before.length, i + 12); j++) {
      const text = before[j].text;
      if (SAVIOR_SOURCE_GRADES.includes(text)) score += 3;
      if (SAVIOR_SOURCE_ELEMENTS.includes(text)) score += 2;
      if (SAVIOR_SOURCE_CLASSES.includes(text)) score += 3;
      if (SAVIOR_SOURCE_ATTACK_TYPES.includes(text)) score += 3;
    }
    if (score > bestScore) {
      bestScore = score;
      nameIndex = i;
    }
  }
  if (nameIndex < 0) nameIndex = findSourceTokenIndex(before, (text) => text === savior.name);
  if (nameIndex < 0) nameIndex = 0;

  let grade = "";
  let element = "";
  let className = "";
  let attackType = "";
  let lastMetaIndex = nameIndex;

  for (let i = nameIndex + 1; i < Math.min(before.length, nameIndex + 16); i++) {
    const text = before[i].text;
    if (!grade && SAVIOR_SOURCE_GRADES.includes(text)) {
      grade = text;
      lastMetaIndex = i;
      continue;
    }
    if (!element && SAVIOR_SOURCE_ELEMENTS.includes(text)) {
      element = text;
      lastMetaIndex = i;
      continue;
    }
    if (!className && SAVIOR_SOURCE_CLASSES.includes(text)) {
      className = text;
      lastMetaIndex = i;
      continue;
    }
    if (!attackType && SAVIOR_SOURCE_ATTACK_TYPES.includes(text)) {
      attackType = text;
      lastMetaIndex = i;
      continue;
    }

    // 드물게 메타 정보가 하나의 짧은 텍스트 노드로 합쳐져 저장된 경우만 보정한다.
    // 일반 캐릭터 설명 안의 "별", "달" 같은 글자를 메타로 오인하지 않도록 길이/형태를 제한한다.
    const looksLikeCompactMeta = text.length <= 28 && !/[.!?。！？]/.test(text) && text.split(/\s+/).length <= 4;
    if (looksLikeCompactMeta) {
      const prev = { grade, element, className, attackType };
      if (!grade) grade = SAVIOR_SOURCE_GRADES.find((value) => text.includes(value)) || grade;
      if (!element) element = SAVIOR_SOURCE_ELEMENTS.find((value) => text.includes(value)) || element;
      if (!className) className = SAVIOR_SOURCE_CLASSES.find((value) => text.includes(value)) || className;
      if (!attackType) attackType = SAVIOR_SOURCE_ATTACK_TYPES.find((value) => text.includes(value)) || attackType;
      if (grade !== prev.grade || element !== prev.element || className !== prev.className || attackType !== prev.attackType) {
        lastMetaIndex = i;
      }
    }

    if (grade && element && className && attackType) break;
  }

  // 설명은 마지막 메타 정보 다음부터 기본 스테이터스 직전까지의 원문만 사용한다.
  const description = normalizeSaviorSourceText(before.slice(lastMetaIndex + 1)
    .map((token) => token.text)
    .filter((text) => text && !knownMeta.has(text))
    .filter((text) => !/^(구원자|한국어|English|日本語)$/.test(text))
    .filter((text) => !/^백업 기준\s*:/.test(text))
    .join(" "));

  return {
    name: savior.name,
    grade: grade || savior.grade || "-",
    element: element || ELEMENT_LABELS[savior.element] || "-",
    className: className || savior.className || "-",
    attackType: attackType || savior.attackType || "-",
    description
  };
}

const SAVIOR_PROFILE_FACTS = [
  ["생일", "birthday"],
  ["신장", "height"],
  ["출신", "origin"],
  ["소속", "affiliation"],
  ["CV (KR)", "cvKr"],
  ["CV (JP)", "cvJp"]
];

function parseSaviorSourceProfileExtras(root, backupUrl) {
  const profile = {};
  const factKeys = new Map(SAVIOR_PROFILE_FACTS.map(([label, key]) => [label, key]));

  root.querySelectorAll("strong").forEach((labelNode) => {
    const label = normalizeSaviorSourceText(labelNode.textContent);
    const key = factKeys.get(label);
    if (!key || profile[key]) return;
    const valueNode = labelNode.parentElement?.querySelector("span");
    const value = normalizeSaviorSourceText(valueNode?.textContent);
    if (value) profile[key] = value;
  });

  const illustration = [...root.querySelectorAll("img")].find((image) => {
    const alt = normalizeSaviorSourceText(image.getAttribute("alt"));
    const src = image.getAttribute("src") || image.getAttribute("data-src") || "";
    return alt === "Savior Illustration" || /일러스트/.test(src);
  });
  if (illustration) {
    profile.illustration = resolveSaviorSourceAsset(
      illustration.getAttribute("src") || illustration.getAttribute("data-src") || "",
      backupUrl
    );
  }

  return profile;
}

function getSourceElementStartIndex(tokens, element) {
  if (!element) return -1;
  for (let i = 0; i < tokens.length; i++) {
    if (element.contains(tokens[i].parent)) return i;
  }
  return -1;
}

function splitSaviorResonanceText(pieces) {
  const clean = pieces.map(normalizeSaviorSourceText).filter(Boolean);
  if (!clean.length) return { title: "", description: "" };

  let title = clean.shift();
  let description = normalizeSaviorSourceText(clean.join(" "));

  const colon = title.match(/^(.+?)\s*[:：]\s*(.+)$/);
  if (colon) {
    title = normalizeSaviorSourceText(colon[1]);
    description = normalizeSaviorSourceText(`${colon[2]} ${description}`);
  } else if (!description) {
    const combined = title.match(/^(.+?(?:감각|솜씨))\s+(.+)$/);
    if (combined) {
      title = normalizeSaviorSourceText(combined[1]);
      description = normalizeSaviorSourceText(combined[2]);
    }
  }

  return { title, description };
}

function extractSaviorResonanceRows(tokens, resonanceIndex, skillBlockStartIndex) {
  if (resonanceIndex < 0) return [];
  const stopIndex = skillBlockStartIndex > resonanceIndex ? skillBlockStartIndex : tokens.length;
  const section = getSourceRangeTokens(tokens, resonanceIndex + 1, stopIndex);
  const rows = [];

  for (let i = 0; i < section.length; i++) {
    const match = section[i].text.match(/^Lv\.?\s*(\d{1,2})(?:\s+(.+))?$/i);
    if (!match) continue;

    const level = match[1];
    const pieces = [];
    if (match[2]) pieces.push(match[2]);

    for (let j = i + 1; j < section.length; j++) {
      const text = section[j].text;
      if (/^Lv\.?\s*\d{1,2}/i.test(text)) break;
      if (isSourceSkillType(text) || /스킬\s*레벨\s*정보/.test(text)) break;
      if (/^\d+$/.test(text)) continue;
      pieces.push(text);
    }

    const parsed = splitSaviorResonanceText(pieces);
    if (!parsed.title && !parsed.description) continue;
    if (!rows.some((row) => row.level === level)) {
      rows.push({ level, title: parsed.title, description: parsed.description });
    }
  }

  return rows;
}

function countSourceSkillTypes(tokens) {
  return tokens.filter((token) => isSourceSkillType(token.text)).length;
}

function findSaviorSkillBlock(typeToken, root) {
  let node = typeToken.parent;
  let fallback = null;
  while (node && node !== root) {
    const tokens = getSaviorSourceTokens(node);
    const typeCount = countSourceSkillTypes(tokens);
    const hasImage = node.querySelectorAll("img").length > 0;
    const hasLevelInfo = tokens.some((token) => /스킬\s*레벨\s*정보/.test(token.text));
    const textLength = normalizeSaviorSourceText(node.textContent).length;
    if (typeCount === 1 && hasImage && textLength >= 20 && textLength <= 10000) {
      fallback = node;
      if (hasLevelInfo) return node;
    }
    node = node.parentElement;
  }
  return fallback;
}

function getSkillTitleFromTokens(tokens, typeIndex) {
  const ignored = new Set(["스킬", "스킬 정보", "스킬 레벨 정보"]);
  for (let i = typeIndex - 1; i >= Math.max(0, typeIndex - 8); i--) {
    const text = tokens[i].text;
    if (!text || ignored.has(text) || isSourceSkillType(text)) continue;
    if (/^\d+(?:\.\d+)?%?$/.test(text) || /^Lv\.?\s*\d+/i.test(text)) continue;
    if (/^(적|아군)\s*(단일|전체)$/.test(text) || /^노바\s*(획득|소모)/.test(text) || /^\d+\s*턴$/.test(text)) continue;
    if (text.length <= 90) return text;
  }
  return "스킬";
}

function parseSkillMetaFromHeader(tokens, typeIndex) {
  const metas = [];
  let lastConsumed = typeIndex;
  let i = typeIndex + 1;
  const max = Math.min(tokens.length, typeIndex + 16);

  const addMeta = (value) => {
    const clean = normalizeSaviorSourceText(value);
    if (clean && !metas.includes(clean)) metas.push(clean);
  };

  while (i < max) {
    let text = tokens[i].text;
    const next = tokens[i + 1]?.text || "";
    const next2 = tokens[i + 2]?.text || "";
    let consumed = 0;
    let value = "";
    let ignored = false;

    // 강인도 피해는 상세 카드에서 사용하지 않는다. 단, 뒤의 노바 정보는 계속 읽는다.
    if (/^강인도\s*피해\s*\d+$/.test(text)) {
      consumed = 1;
      ignored = true;
    } else if (text === "강인도 피해" && /^\d+$/.test(next)) {
      consumed = 2;
      ignored = true;
    } else if (text === "강인도" && next === "피해" && /^\d+$/.test(next2)) {
      consumed = 3;
      ignored = true;
    } else if (/^강인도\s*피해\s*\d+\s+노바\s*(?:획득|소모)\s*\d+$/.test(text)) {
      value = text.replace(/^강인도\s*피해\s*\d+\s+/, "");
      consumed = 1;
    } else if (/^\d+\s*턴$/.test(text)) {
      value = text.replace(/\s+/g, "");
      consumed = 1;
    } else if (/^\d+$/.test(text) && next === "턴") {
      value = `${text}턴`;
      consumed = 2;
    } else if (/^(?:적|아군)\s*(?:단일|전체)$/.test(text)) {
      value = normalizeSaviorSourceText(text);
      consumed = 1;
    } else if (/^(?:적|아군)$/.test(text) && /^(?:단일|전체)$/.test(next)) {
      value = `${text} ${next}`;
      consumed = 2;
    } else if (/^노바\s*(?:획득|소모)\s*\d+$/.test(text)) {
      value = normalizeSaviorSourceText(text);
      consumed = 1;
    } else if (/^노바\s*(?:획득|소모)$/.test(text) && /^\d+$/.test(next)) {
      value = `${normalizeSaviorSourceText(text)} ${next}`;
      consumed = 2;
    } else if (text === "노바" && /^(?:획득|소모)$/.test(next) && /^\d+$/.test(next2)) {
      value = `노바 ${next} ${next2}`;
      consumed = 3;
    }

    if (!consumed) break;
    if (!ignored && value) addMeta(value);
    lastConsumed = i + consumed - 1;
    i += consumed;
  }

  return { metas, lastConsumed };
}

function resolveSaviorSourceAsset(src, backupUrl) {
  if (!src) return "";
  try {
    return new URL(src, new URL(backupUrl, window.location.href)).href;
  } catch (_) {
    return src;
  }
}

function getSmallestEffectContainer(img, block, levelMarkerParent) {
  let node = img.parentElement;
  while (node && node !== block) {
    if (levelMarkerParent && node.contains(levelMarkerParent)) break;
    const tokens = getSaviorSourceTokens(node);
    const text = normalizeSaviorSourceText(tokens.map((token) => token.text).join(" "));
    const imageCount = node.querySelectorAll("img").length;
    if (text.length >= 3 && text.length <= 700 && imageCount === 1 && !/스킬\s*레벨\s*정보/.test(text)) {
      return node;
    }
    node = node.parentElement;
  }
  return null;
}

function parseSaviorSkillEffects(block, mainImage, levelMarkerToken, blockTokens, backupUrl) {
  const effects = [];
  const containers = [];
  const images = [...block.querySelectorAll("img")].filter((img) => img !== mainImage);
  for (const img of images) {
    if (levelMarkerToken && (levelMarkerToken.node.compareDocumentPosition(img) & 2) === 0) {
      // If the image is not before the level marker, do not treat level/decorative images as effects.
      continue;
    }
    const container = getSmallestEffectContainer(img, block, levelMarkerToken?.parent || null);
    if (!container) continue;
    const effectTokens = getSaviorSourceTokens(container);
    const text = normalizeSaviorSourceText(effectTokens.map((token) => token.text).join(" "));
    if (!text || /계수/.test(text) || effects.some((effect) => effect.text === text)) continue;
    effects.push({
      image: resolveSaviorSourceAsset(img.getAttribute("src") || img.getAttribute("data-src") || "", backupUrl),
      text
    });
    containers.push(container);
  }

  let firstIndex = -1;
  for (let i = 0; i < blockTokens.length; i++) {
    if (containers.some((container) => container.contains(blockTokens[i].parent))) {
      firstIndex = i;
      break;
    }
  }
  return { effects, firstIndex };
}

function parseSaviorNovaBurst(block, blockTokens, levelIndex) {
  const novaIndex = findSourceTokenIndex(blockTokens, (text) => /^노바\s*버스트/.test(text));
  if (novaIndex < 0 || (levelIndex >= 0 && novaIndex > levelIndex)) return { text: "", index: -1 };
  const token = blockTokens[novaIndex];
  let text = token.text.replace(/^노바\s*버스트\s*/g, "").trim();
  if (!text) {
    let node = token.parent;
    while (node && node !== block) {
      const candidate = normalizeSaviorSourceText(getSaviorSourceTokens(node).map((item) => item.text).join(" "));
      if (candidate.length > "노바 버스트".length && candidate.length <= 650 && !/스킬\s*레벨\s*정보/.test(candidate)) {
        text = candidate.replace(/^.*?노바\s*버스트\s*/g, "").trim();
        break;
      }
      node = node.parentElement;
    }
  }
  return { text, index: novaIndex };
}

function findLevelMarkerIndex(tokens) {
  return findSourceTokenIndex(tokens, (text) => /스킬\s*레벨\s*정보/.test(text));
}

function parseSaviorSkillLevels(block, blockTokens, levelIndex) {
  if (levelIndex < 0) return [];
  const levelRows = [];
  const seen = new Set();
  const candidateTokens = blockTokens.slice(levelIndex + 1);

  for (const token of candidateTokens) {
    if (!/^(?:10|[1-9])$/.test(token.text)) continue;
    const level = token.text;
    if (seen.has(level)) continue;
    let node = token.parent;
    let row = null;
    while (node && node !== block) {
      const rowTokens = getSaviorSourceTokens(node);
      const textLength = normalizeSaviorSourceText(rowTokens.map((item) => item.text).join(" ")).length;
      const firstToken = rowTokens[0]?.text || "";
      if (firstToken === level && rowTokens.length >= 2 && textLength <= 1200 && !rowTokens.some((item) => /스킬\s*레벨\s*정보/.test(item.text))) {
        row = node;
        break;
      }
      node = node.parentElement;
    }
    if (!row) continue;
    const rowTokens = getSaviorSourceTokens(row);
    let removedLevel = false;
    const description = normalizeSaviorSourceText(rowTokens.map((item) => {
      if (!removedLevel && item.text === level) {
        removedLevel = true;
        return "";
      }
      return item.text;
    }).filter(Boolean).join(" "));
    if (!description) continue;
    seen.add(level);
    levelRows.push({ level, description });
  }

  return levelRows.sort((a, b) => Number(a.level) - Number(b.level));
}

function cleanSaviorSkillBodyToken(text) {
  let value = normalizeSaviorSourceText(text);
  if (!value) return "";
  value = value
    .replace(/^강인도\s*피해\s*\d+\s*/g, "")
    .replace(/^노바\s*(?:획득|소모)\s*\d+\s*/g, "")
    .trim();
  return value;
}

function parseSaviorSkillBlock(block, backupUrl) {
  const tokens = getSaviorSourceTokens(block);
  const typeIndex = findSourceTokenIndex(tokens, (text) => isSourceSkillType(text));
  if (typeIndex < 0) return null;
  const type = tokens[typeIndex].text;
  const title = getSkillTitleFromTokens(tokens, typeIndex);
  const levelIndex = findLevelMarkerIndex(tokens);
  const levelMarkerToken = levelIndex >= 0 ? tokens[levelIndex] : null;
  const mainImage = block.querySelector("img");
  const mainImageUrl = mainImage
    ? resolveSaviorSourceAsset(mainImage.getAttribute("src") || mainImage.getAttribute("data-src") || "", backupUrl)
    : "";

  const { metas, lastConsumed } = parseSkillMetaFromHeader(tokens, typeIndex);
  const { effects, firstIndex: firstEffectIndex } = parseSaviorSkillEffects(block, mainImage, levelMarkerToken, tokens, backupUrl);
  const nova = parseSaviorNovaBurst(block, tokens, levelIndex);
  const coefficientIndex = findSourceTokenIndex(tokens, (text) => /(?:데미지|공격력|생명력|방어력)\s*계수|계수\s*-/.test(text), lastConsumed + 1);

  const endCandidates = [coefficientIndex, firstEffectIndex, nova.index, levelIndex].filter((value) => value >= 0 && value > lastConsumed);
  const descriptionEnd = endCandidates.length ? Math.min(...endCandidates) : tokens.length;
  const description = normalizeSaviorSourceText(tokens.slice(lastConsumed + 1, descriptionEnd)
    .map((token) => cleanSaviorSkillBodyToken(token.text))
    .filter(Boolean)
    .filter((text) => !/계수/.test(text))
    .filter((text) => !/^강인도\s*피해(?:\s*\d+)?$/.test(text))
    .filter((text) => !isSourceSkillType(text))
    .filter((text) => !/스킬\s*레벨\s*정보/.test(text))
    .join(" "));

  const levels = parseSaviorSkillLevels(block, tokens, levelIndex);
  return {
    title,
    type,
    image: mainImageUrl,
    metas,
    description,
    effects,
    novaBurst: nova.text,
    levels
  };
}

function parseSaviorSourceSkills(root, tokens, firstSkillIndex, backupUrl) {
  if (firstSkillIndex < 0) return [];
  const typeTokens = tokens.slice(firstSkillIndex).filter((token) => isSourceSkillType(token.text));
  const blocks = [];
  const seen = new Set();
  for (const token of typeTokens) {
    const block = findSaviorSkillBlock(token, root);
    if (!block || seen.has(block)) continue;
    seen.add(block);
    const parsed = parseSaviorSkillBlock(block, backupUrl);
    if (parsed) blocks.push(parsed);
  }
  return blocks;
}

function renderSaviorInfoTable(savior, profile) {
  const facts = SAVIOR_PROFILE_FACTS
    .map(([label, key]) => ({ label, value: normalizeSaviorSourceText(profile[key]) }))
    .filter((fact) => fact.value);

  if (!profile.description && !facts.length) return "";

  return `
    <section class="source-detail-block source-profile-block">
      ${profile.description ? `<div class="source-character-description"><strong>${escapeHtml(translateString("구원자 설명"))}</strong><p>${escapeHtml(profile.description)}</p></div>` : ""}
      ${facts.length ? `
        <dl class="source-profile-facts">
          ${facts.map((fact) => `
            <div class="source-profile-fact">
              <dt>${escapeHtml(translateString(fact.label))}</dt>
              <dd>${escapeHtml(fact.value)}</dd>
            </div>
          `).join("")}
        </dl>
      ` : ""}
    </section>
  `;
}

function renderSourceStatTable(title, subtitle, rows) {
  const validRows = rows.filter(([, value]) => value);
  if (!validRows.length) return "";
  return `
    <section class="source-detail-block">
      <div class="source-detail-heading">
        <h3>${escapeHtml(translateString(title))}</h3>
        ${subtitle ? `<span>${escapeHtml(translateString(subtitle))}</span>` : ""}
      </div>
      <div class="source-kv-table-wrap">
        <table class="source-kv-table">
          <tbody>${validRows.map(([label, value]) => `<tr><th>${escapeHtml(translateString(label))}</th><td>${escapeHtml(value)}</td></tr>`).join("")}</tbody>
        </table>
      </div>
    </section>
  `;
}

function renderSourceResonanceTable(rows) {
  if (!rows.length) return "";
  return `
    <section class="source-detail-block">
      <div class="source-detail-heading"><h3>${escapeHtml(translateString("공명 잠재력"))}</h3></div>
      <div class="source-wide-table-wrap">
        <table class="source-wide-table source-resonance-table">
          <thead><tr><th>${escapeHtml(translateString("레벨"))}</th><th>${escapeHtml(translateString("공명 잠재력"))}</th></tr></thead>
          <tbody>${rows.map((row) => `
            <tr>
              <th>Lv.${escapeHtml(row.level)}</th>
              <td>${row.title ? `<strong class="source-resonance-name">${row.icon ? `<span class="source-resonance-icon" aria-hidden="true">${row.background ? `<img class="source-resonance-background" src="${escapeHtml(row.background)}" alt="" loading="lazy">` : ""}<img class="source-resonance-symbol" src="${escapeHtml(row.icon)}" alt="" loading="lazy"></span>` : ""}${escapeHtml(row.title)}${row.description ? " :" : ""}</strong>` : ""}${row.description ? `${row.title ? " " : ""}${escapeHtml(row.description)}` : ""}</td>
            </tr>
          `).join("")}</tbody>
        </table>
      </div>
    </section>
  `;
}

function renderSaviorSkillLevelDescription(skill, description) {
  let html = renderSaviorSourceRichText(description);
  if (skill.typeCode == null && skill.type === "패시브") {
    html = html.replace(/([+-]?\d+(?:\.\d+)?%)/g, '<span class="source-skill-level-value">$1</span>');
  }
  return html;
}

function renderSourceSkillCard(skill) {
  return `
    <article class="source-skill-card">
      <div class="source-skill-header">
        ${skill.image ? `<img class="source-skill-icon" src="${escapeHtml(skill.image)}" alt="" loading="lazy" onerror="this.remove()">` : ""}
        <div class="source-skill-title-wrap">
          <div class="source-skill-title-line">
            <strong>${escapeHtml(skill.title)}</strong>
            <span class="source-skill-type">${escapeHtml(skill.typeLabel || translateString(skill.type))}</span>
          </div>
          ${skill.metas.length ? `<div class="source-skill-meta">${skill.metas.map((meta) => `<span>${escapeHtml(meta)}</span>`).join("")}</div>` : ""}
        </div>
      </div>
      ${skill.description ? `<div class="source-skill-description"><p>${renderSaviorSourceRichText(skill.description)}</p></div>` : ""}
      ${skill.effects.length ? `
        <div class="source-skill-effects">
          ${skill.effects.map((effect) => `
            <div class="source-skill-effect-row">
              ${effect.image ? `<img src="${escapeHtml(effect.image)}" alt="" loading="lazy" onerror="this.remove()">` : ""}
              <p>${effect.name
                ? `<strong style="color:#DD982C">${escapeHtml(effect.name)}</strong> : ${renderSaviorSourceRichText(effect.description)}`
                : escapeHtml(effect.text)}</p>
            </div>
          `).join("")}
        </div>
      ` : ""}
      ${skill.novaBurst ? `
        <div class="source-nova-burst">
          <strong>${escapeHtml(translateString("노바 버스트"))}</strong>
          <p>${renderSaviorSourceRichText(skill.novaBurst)}</p>
        </div>
      ` : ""}
      ${skill.levels.length ? `
        <div class="source-skill-level-wrap">
          <div class="source-skill-level-title">${escapeHtml(translateString("스킬 레벨 정보"))}</div>
          <table class="source-wide-table source-skill-level-table">
            <thead><tr><th>Lv.</th><th>${escapeHtml(translateString("스킬 레벨 설명"))}</th></tr></thead>
            <colgroup><col class="source-level-col"><col></colgroup>
            <tbody>${skill.levels.map((level) => `<tr><th>${escapeHtml(level.level)}</th><td>${renderSaviorSkillLevelDescription(skill, level.description)}</td></tr>`).join("")}</tbody>
          </table>
        </div>
      ` : ""}
    </article>
  `;
}

function applyProfessorMSkillProgression(skills, savior) {
  if (!Array.isArray(skills) || !savior || savior.id !== "professor-m" || currentLanguage !== "ko") return;
  const rows = [
    null,
    [{level:1,description:"기본 효과"},{level:2,description:"피해량 1% 증가"},{level:3,description:"피해량 1% 증가"},{level:4,description:"피해량 1% 증가"},{level:5,description:"피해량 1% 증가"},{level:6,description:"피해량 2% 증가"},{level:7,description:"피해량 2% 증가"},{level:8,description:"피해량 2% 증가"},{level:9,description:"피해량 2% 증가"},{level:10,description:"피해량 3% 증가"}],
    [{level:1,description:"기본 효과"},{level:2,description:"피해량 1% 증가"},{level:3,description:"피해량 1% 증가"},{level:4,description:"행동 게이지 증가량 5% 증가"},{level:5,description:"피해량 1% 증가"},{level:6,description:"피해량 2% 증가"},{level:7,description:"피해량 2% 증가"},{level:8,description:"행동 게이지 증가량 5% 증가"},{level:9,description:"피해량 3% 증가"},{level:10,description:"피해량 5% 증가"}],
    [{level:1,description:"기본 효과"},{level:2,description:"피해량 1% 증가"},{level:3,description:"피해량 2% 증가"},{level:4,description:"표적 각인 발생 확률 10% 증가"},{level:5,description:"피해량 2% 증가"},{level:6,description:"쿨타임 1턴 감소"},{level:7,description:"피해량 2% 증가"},{level:8,description:"표적 각인 발생 확률 15% 증가"},{level:9,description:"피해량 3% 증가"},{level:10,description:"피해량 5% 증가"}]
  ];
  rows.forEach((levels,index) => { if (levels && skills[index]) skills[index].levels = levels; });
}

function createParsedSaviorSourceMarkup(sourceHtml, backupUrl, savior, options = {}) {
  const { root } = getSaviorSourceRoot(sourceHtml);
  const tokens = getSaviorSourceTokens(root);
  const baseIndex = findSourceTokenIndex(tokens, (text) => text.startsWith("기본 스테이터스"));
  const journeyIndex = findSourceTokenIndex(tokens, (text) => text === "여정 스테이터스", Math.max(0, baseIndex + 1));
  const resonanceIndex = findSourceTokenIndex(tokens, (text) => text === "공명 잠재력", Math.max(0, journeyIndex + 1));
  const firstSkillIndex = findSourceTokenIndex(tokens, (text) => isSourceSkillType(text), Math.max(0, resonanceIndex + 1));

  // 공명 잠재력의 마지막 행에 첫 패시브 스킬명이 붙는 것을 방지하기 위해
  // 첫 스킬 '타입' 토큰이 아니라 실제 스킬 카드 DOM 시작 지점을 경계로 사용한다.
  const firstSkillTypeToken = firstSkillIndex >= 0 ? tokens[firstSkillIndex] : null;
  const firstSkillBlock = firstSkillTypeToken ? findSaviorSkillBlock(firstSkillTypeToken, root) : null;
  const firstSkillBlockStartIndex = firstSkillBlock ? getSourceElementStartIndex(tokens, firstSkillBlock) : firstSkillIndex;
  let resonanceStopIndex = firstSkillBlockStartIndex;
  if (firstSkillBlock && firstSkillIndex >= 0) {
    const firstBlockTokens = getSaviorSourceTokens(firstSkillBlock);
    const localTypeIndex = findSourceTokenIndex(firstBlockTokens, (text) => isSourceSkillType(text));
    const firstSkillTitle = localTypeIndex >= 0 ? getSkillTitleFromTokens(firstBlockTokens, localTypeIndex) : "";
    if (firstSkillTitle) {
      for (let i = firstSkillIndex - 1; i > resonanceIndex; i--) {
        if (tokens[i].text === firstSkillTitle && firstSkillBlock.contains(tokens[i].parent)) {
          resonanceStopIndex = i;
          break;
        }
      }
    }
  }

  const baseTokens = getSourceRangeTokens(tokens, baseIndex + 1, journeyIndex > baseIndex ? journeyIndex : resonanceIndex);
  const journeyTokens = getSourceRangeTokens(tokens, journeyIndex + 1, resonanceIndex > journeyIndex ? resonanceIndex : firstSkillIndex);
  const baseStats = SAVIOR_SOURCE_BASE_STATS.map(([label, percent]) => [label, extractSourceStat(baseTokens, label, percent)]);
  const journeyStats = SAVIOR_SOURCE_JOURNEY_STATS.map((label) => [label, extractSourceStat(journeyTokens, label, false)]);
  const profile = parseSaviorSourceProfile(tokens, baseIndex, savior);
  const parsedProfileExtras = parseSaviorSourceProfileExtras(root, backupUrl);
  const localProfile = getLocalSaviorProfile(savior) || {};
  Object.assign(profile, parsedProfileExtras, localProfile);
  const parsedSkills = parseSaviorSourceSkills(root, tokens, firstSkillIndex, backupUrl);
  applyProfessorMSkillProgression(parsedSkills, savior);
  const archivedSavior = options.archivedSavior || null;
  const archivedResonanceRows = createArchivedSaviorResonanceRows(
    archivedSavior,
    options.language || currentLanguage
  );
  const resonanceRows = archivedResonanceRows.length
    ? archivedResonanceRows
    : extractSaviorResonanceRows(tokens, resonanceIndex, resonanceStopIndex);
  const archivedSkills = archivedSavior
    ? createArchivedSaviorSkills(archivedSavior, {
        language: options.language || currentLanguage,
        blossomed: Boolean(options.blossomed)
      })
    : [];
  const skills = archivedSkills.length ? archivedSkills : parsedSkills;
  applyProfessorMSkillProgression(skills, savior);

  if (archivedSavior) {
    profile.localizedName = getArchivedLanguageText(archivedSavior.name, options.language || currentLanguage);
    profile.description = getArchivedLanguageText(archivedSavior.description, options.language || currentLanguage);
  }

  const detailId = resolveSaviorDetailId(savior);
  const bloomAvailable = (archivedSavior?.blossomSkills?.length || 0) > 0
    || SAVIOR_BLOOM_DETAIL_ID_SET.has(Number(detailId));

  return `
    <div class="parsed-savior-source">
      ${bloomAvailable ? `
        <div class="source-bloom-toolbar">
          <button class="source-bloom-toggle" type="button" data-savior-bloom-toggle data-detail-id="${escapeHtml(detailId)}" aria-pressed="${options.blossomed ? "true" : "false"}">
            <span class="source-bloom-flower" aria-hidden="true">✿</span>
            <span>${escapeHtml(translateString("개화"))}</span>
          </button>
        </div>
      ` : ""}
      ${renderSaviorInfoTable(savior, profile)}
      ${renderSourceResonanceTable(resonanceRows)}
      ${skills.length ? `
        <section class="source-detail-block source-skills-block">
          <div class="source-detail-heading"><h3>${escapeHtml(translateString("스킬 정보"))}</h3></div>
          <div class="source-skill-list">${skills.map(renderSourceSkillCard).join("")}</div>
        </section>
      ` : ""}
    </div>
  `;
}

async function loadSaviorSourcePanel(button, panel) {
  if (panel.dataset.loaded === "true") return;
  const savior = SAVIORS.find((item) => item.id === button.dataset.saviorKey)
    || SAVIORS.find((item) => SAVIOR_DETAIL_IDS[item.id] === Number(button.dataset.detailId));
  if (!savior) return;

  button.disabled = true;
  setSaviorSourcePanelStatus(panel, "상세정보를 불러오는 중입니다.", "loading");

  let detailId = Number(button.dataset.detailId || 0);
  try {
    const archive = await loadSaviorSkillArchive();
    await loadSaviorProfileIndex().catch(() => null);
    detailId = detailId || Number(resolveSaviorDetailId(savior) || 0);
    if (!detailId) throw new Error("Savior detail ID could not be resolved");
    button.dataset.detailId = String(detailId);

    const url = getSaviorBackupUrl(detailId);
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const sourceHtml = await response.text();
    const archivedSavior = archive.saviors.find((item) => Number(item.id) === detailId) || null;
    panel.innerHTML = createParsedSaviorSourceMarkup(sourceHtml, url, savior, {
      archivedSavior,
      language: currentLanguage
    });
    panel._normalSaviorSourceHtml = sourceHtml;
    panel._normalSaviorSourceUrl = url;
    panel._archivedSaviorSkills = archivedSavior;
    panel._saviorSourceId = savior.id;
    panel._resolvedDetailId = detailId;
    panel.dataset.loaded = "true";
    panel.dataset.state = "ready";
    applyLanguageToDOM(panel);
  } catch (error) {
    console.warn("Savior detail backup load failed:", detailId || savior.id, error);
    setSaviorSourcePanelStatus(panel, "상세정보 백업 데이터를 불러올 수 없습니다.", "error");
  } finally {
    button.disabled = false;
  }
}

function refreshLoadedSaviorSourcePanels() {
  document.querySelectorAll("[data-savior-source-panel][data-loaded='true']").forEach((panel) => {
    const savior = SAVIORS.find((item) => item.id === panel._saviorSourceId);
    if (!savior || !panel._normalSaviorSourceHtml || !panel._archivedSaviorSkills) return;
    const blossomed = panel.querySelector("[data-savior-bloom-toggle]")?.getAttribute("aria-pressed") === "true";
    panel.innerHTML = createParsedSaviorSourceMarkup(
      panel._normalSaviorSourceHtml,
      panel._normalSaviorSourceUrl || getSaviorBackupUrl(panel._resolvedDetailId || resolveSaviorDetailId(savior)),
      savior,
      {
        archivedSavior: panel._archivedSaviorSkills,
        language: currentLanguage,
        blossomed
      }
    );
    if (blossomed) setSaviorBloomProfileGrade(panel, true);
    applyLanguageToDOM(panel);
  });
}

const ALL_SAVIOR_EFFECT_IMAGE_DONORS = [...new Set(Object.values(SAVIOR_DETAIL_IDS))];
const STATIC_SAVIOR_EFFECT_IMAGES = {
  // 사이트 로컬 자산을 직접 사용하는 개화 전용/보정 효과 이미지입니다.
  "헥사 너트": "./data/savior-detail-assets/헥사 너트.webp",
  "부서진 너트": "./data/savior-detail-assets/부서진 너트.webp",
  "강화 반격": "./data/savior-detail-assets/강화반격.webp"
};

const SHARED_SAVIOR_EFFECT_DESCRIPTIONS = {
  "공격력 증가": "공격력이 30% 증가합니다.",
  "은신": "다른 아군이 있을 경우 공격 대상으로 선택될 수 없습니다. 타격 시 적의 선제 방어 발생을 무시합니다.",
  "효과저항 감소": "효과 저항이 30% 감소합니다.",
  "보호막": "피해를 받을 때 생명력을 대신해 정해진 수치만큼 피해를 흡수합니다.",
  "공격력 감소": "공격력이 30% 감소합니다.",
  "헥사 너트": "치명타 피해가 30% 증가하고 강인도가 격파된 상태의 적에게 주는 피해가 15% 증가합니다. 타격 후 해제됩니다.",
  "부서진 너트": "마르실이 부서진 너트를 줍습니다. 최대 3회 중첩됩니다.",
  "강화 반격": "반격 확률이 100% 증가합니다."
};

const SHARED_SAVIOR_EFFECT_IMAGE_DONORS = {
  "연소": [1017],
  "점화": [1502, 1511],
  "도약": [1508, 1501, 1511],
  "냉각": [1001, 1509],
  // 개화 스킬에 새로 추가되어 일반 스킬에서 같은 위치의 이미지를 복제할 수 없는 효과들.
  // 앞쪽 ID는 해당 효과를 찾기 쉬운 우선 탐색 대상이며, 못 찾으면 전체 백업을 순회합니다.
  "공격력 증가": [1014, 1033, 1043, 1509],
  "은신": [1015, 1025, 1026, 1044, 1508],
  "효과저항 감소": [1024, 1033, 1508, 1511],
  "보호막": [1009, 1042, 1501, 1502],
  "공격력 감소": [1008, 1023, 1024, 1501, 1502],
  "헥사 너트": [],
  "부서진 너트": [],
  "강화 반격": []
};
const SHARED_SAVIOR_EFFECT_ALIASES = {
  "효과저항 감소": ["효과저항 감소", "효과 저항 감소"]
};
const sharedSaviorEffectImageCache = new Map();

function getSharedSaviorEffectAliases(effectName) {
  return SHARED_SAVIOR_EFFECT_ALIASES[effectName] || [effectName];
}

function doesSaviorEffectTextMatch(text, effectName) {
  const value = normalizeSaviorSourceText(text);
  return getSharedSaviorEffectAliases(effectName).some((alias) => value.includes(alias));
}

function getSharedSaviorEffectName(text) {
  return Object.keys(SHARED_SAVIOR_EFFECT_IMAGE_DONORS)
    .find((name) => doesSaviorEffectTextMatch(text, name)) || "";
}

function getEffectRowKey(row) {
  if (!row) return "";
  const text = normalizeSaviorSourceText(row.textContent || "");
  const shared = getSharedSaviorEffectName(text);
  if (shared) return shared;
  return normalizeSaviorSourceText(text.split(/[:：]/, 1)[0]);
}

async function getSharedSaviorEffectImage(effectName) {
  if (!effectName) return "";
  if (STATIC_SAVIOR_EFFECT_IMAGES[effectName]) {
    return STATIC_SAVIOR_EFFECT_IMAGES[effectName];
  }
  if (sharedSaviorEffectImageCache.has(effectName)) {
    return sharedSaviorEffectImageCache.get(effectName) || "";
  }

  const pending = (async () => {
    const preferredDonors = SHARED_SAVIOR_EFFECT_IMAGE_DONORS[effectName] || [];
    const donorIds = [...new Set([...preferredDonors, ...ALL_SAVIOR_EFFECT_IMAGE_DONORS])];
    for (const detailId of donorIds) {
      try {
        const url = getSaviorBackupUrl(detailId);
        const response = await fetch(url, { cache: "no-store" });
        if (!response.ok) continue;
        const sourceHtml = await response.text();
        const { root } = getSaviorSourceRoot(sourceHtml);
        const tokens = getSaviorSourceTokens(root);
        const firstSkillIndex = findSourceTokenIndex(tokens, (text) => isSourceSkillType(text));
        const skills = parseSaviorSourceSkills(root, tokens, firstSkillIndex, url);
        for (const skill of skills) {
          const effect = (skill.effects || []).find((item) => doesSaviorEffectTextMatch(item.text, effectName) && item.image);
          if (effect?.image) return effect.image;
        }
      } catch (error) {
        console.warn("Shared Savior effect image lookup failed:", effectName, detailId, error);
      }
    }
    return "";
  })();

  sharedSaviorEffectImageCache.set(effectName, pending);
  const resolved = await pending;
  sharedSaviorEffectImageCache.set(effectName, resolved);
  return resolved;
}

function ensureBloomEffectRowDescription(row, effectName) {
  if (!row || !effectName) return;
  const description = SHARED_SAVIOR_EFFECT_DESCRIPTIONS[effectName] || "";
  if (!description) return;
  const paragraph = row.querySelector("p");
  if (!paragraph) return;
  const currentText = normalizeSaviorSourceText(paragraph.textContent || "");
  if (currentText.includes(":")) return;
  if (currentText === effectName || getSharedSaviorEffectAliases(effectName).includes(currentText)) {
    paragraph.textContent = `${effectName} : ${description}`;
  }
}

async function setBloomEffectRowImage(row, effectName, { force = false } = {}) {
  if (!row || !effectName) return;
  const currentImage = row.querySelector("img");
  if (currentImage && !force) return;
  const image = await getSharedSaviorEffectImage(effectName);
  if (!image) return;
  if (force) row.querySelectorAll("img").forEach((img) => img.remove());
  if (row.querySelector("img")) return;
  const img = document.createElement("img");
  img.src = image;
  img.alt = "";
  img.loading = "lazy";
  img.onerror = () => img.remove();
  row.insertBefore(img, row.firstChild);
}

async function hydrateSharedBloomEffectImages(bloomList) {
  if (!bloomList) return;
  const rows = [...bloomList.querySelectorAll(".source-skill-effect-row")];
  await Promise.all(rows.map(async (row) => {
    if (row.querySelector("img")) return;
    const effectName = getSharedSaviorEffectName(row.textContent || "");
    if (!effectName) return;
    await setBloomEffectRowImage(row, effectName);
  }));
}

function getBloomSkillCardsByType(bloomList, skillType) {
  if (!bloomList) return [];
  return [...bloomList.querySelectorAll(".source-skill-card")].filter((card) => {
    const type = normalizeSaviorSourceText(card.querySelector(".source-skill-type")?.textContent || "");
    return type === skillType;
  });
}

function getBloomEffectRowsByName(card, effectName) {
  if (!card) return [];
  return [...card.querySelectorAll(".source-skill-effect-row")]
    .filter((row) => doesSaviorEffectTextMatch(row.textContent || "", effectName));
}

function ensureBloomEffectRow(card, effectName) {
  if (!card || !effectName) return [];
  const existingRows = getBloomEffectRowsByName(card, effectName);
  if (existingRows.length) return existingRows;

  // 개화 백업에 효과 텍스트만 있고 효과 아이콘 행이 없는 경우에만
  // 해당 스킬 설명에 실제로 등장하는 효과를 별도 행으로 보강합니다.
  const cardText = normalizeSaviorSourceText(card.textContent || "");
  if (!doesSaviorEffectTextMatch(cardText, effectName)) return [];

  let effects = card.querySelector(".source-skill-effects");
  if (!effects) {
    effects = document.createElement("div");
    effects.className = "source-skill-effects";
    const nova = card.querySelector(".source-nova-burst");
    const levels = card.querySelector(".source-skill-level-wrap");
    card.insertBefore(effects, nova || levels || null);
  }

  const row = document.createElement("div");
  row.className = "source-skill-effect-row";
  const paragraph = document.createElement("p");
  const description = SHARED_SAVIOR_EFFECT_DESCRIPTIONS[effectName] || "";
  paragraph.textContent = description ? `${effectName} : ${description}` : effectName;
  row.appendChild(paragraph);
  effects.appendChild(row);
  return [row];
}

function isStandaloneMarcilleHealEffectRow(row) {
  const text = normalizeSaviorSourceText(row?.textContent || "");
  if (!text || text.includes("회복 감소")) return false;
  return /^회복(?:\s*[:：]|$)/.test(text);
}

async function applyBloomEffectVisualCorrections(bloomList, savior) {
  if (!bloomList || !savior) return;

  // 마르실 개화 궁극기에는 '회복' 단독 효과가 없습니다.
  // 정상 효과인 '회복 감소'는 유지하고, 잘못 복제된 '회복' 행만 제거합니다.
  if (savior.id === "marcille") {
    getBloomSkillCardsByType(bloomList, "궁극기").forEach((card) => {
      [...card.querySelectorAll(".source-skill-effect-row")].forEach((row) => {
        if (isStandaloneMarcilleHealEffectRow(row)) row.remove();
      });
    });
  }

  const corrections = {
    "bunny-claire": {
      "궁극기": ["공격력 증가", "은신"]
    },
    "naru": {
      "기본기": ["효과저항 감소"],
      "특수기": ["효과저항 감소"],
      "궁극기": ["효과저항 감소"],
      "패시브": ["효과저항 감소"]
    },
    "annah": {
      "패시브": ["강화 반격"],
      "특수기": ["보호막"]
    },
    "besta": {
      "패시브": ["보호막"],
      "기본기": ["공격력 감소"],
      "궁극기": ["보호막"]
    },
    "marcille": {
      "패시브": ["부서진 너트", "헥사 너트"],
      "특수기": ["부서진 너트"],
      "궁극기": ["부서진 너트"]
    }
  };

  const saviorCorrections = corrections[savior.id];
  if (!saviorCorrections) return;

  for (const [skillType, effectNames] of Object.entries(saviorCorrections)) {
    const cards = getBloomSkillCardsByType(bloomList, skillType);
    for (const card of cards) {
      for (const effectName of effectNames) {
        const rows = ensureBloomEffectRow(card, effectName);
        for (const row of rows) {
          // 효과 행이 새로 생성된 경우에도 "효과명 : 설명" 형식을 유지합니다.
          ensureBloomEffectRowDescription(row, effectName);
          // 지정된 개화 효과는 기존에 잘못 복제된 이미지가 있어도 올바른 효과 이미지로 교체합니다.
          await setBloomEffectRowImage(row, effectName, { force: true });
        }
      }
    }
  }
}

function normalizeClarissaBloomLeapText(bloomList, savior) {
  if (!bloomList || savior?.id !== "clarissa") return;

  const normalizeLeapLabel = (value) => String(value || "")
    .replace(/도약\s*스택\s*([2-5])/g, "도약 $1중첩")
    .replace(/도약\s*([2-5])\s*스택/g, "도약 $1중첩")
    .replace(/도약\s*([2-5])(?!\s*중첩)/g, "도약 $1중첩")
    .replace(/도약\s*([2-5])중첩\s*[:：]?\s*/g, "도약 $1중첩 : ");

  const paragraphs = [...bloomList.querySelectorAll(".source-skill-description p, .source-skill-effect-row p")];
  paragraphs.forEach((paragraph) => {
    const normalized = normalizeLeapLabel(paragraph.textContent || "");
    if (!/도약 [2-5]중첩\s*:/.test(normalized)) return;

    // 각 중첩 설명을 독립된 줄로 표시합니다. 원문 내용은 건드리지 않습니다.
    const parts = normalized
      .split(/\s*(?=도약 [2-5]중첩\s*:)/)
      .map((part) => part.trim())
      .filter(Boolean);
    if (parts.length < 2) {
      paragraph.textContent = normalized;
      return;
    }

    paragraph.replaceChildren();
    parts.forEach((part, index) => {
      if (index) paragraph.appendChild(document.createElement("br"));
      paragraph.appendChild(document.createTextNode(part));
    });
  });
}

function setSaviorBloomProfileGrade(panel, enabled) {
  const gradeCell = panel?.querySelector("[data-source-profile-grade]");
  if (!gradeCell) return;
  if (!gradeCell.dataset.normalGrade) {
    gradeCell.dataset.normalGrade = normalizeSaviorSourceText(gradeCell.textContent) || "-";
  }
  gradeCell.textContent = enabled ? "SSR" : gradeCell.dataset.normalGrade;
}

function cloneSaviorSkillVisuals(normalList, bloomList, savior) {
  if (!normalList || !bloomList) return;
  const normalCards = [...normalList.querySelectorAll(".source-skill-card")];
  const bloomCards = [...bloomList.querySelectorAll(".source-skill-card")];

  bloomCards.forEach((bloomCard, index) => {
    const normalCard = normalCards[index];
    if (!normalCard) return;

    const normalIcon = normalCard.querySelector(".source-skill-icon");
    const bloomHeader = bloomCard.querySelector(".source-skill-header");
    if (normalIcon && bloomHeader && !bloomCard.querySelector(".source-skill-icon")) {
      bloomHeader.insertBefore(normalIcon.cloneNode(true), bloomHeader.firstChild);
    }

    const normalEffects = [...normalCard.querySelectorAll(".source-skill-effect-row")];
    const bloomEffects = [...bloomCard.querySelectorAll(".source-skill-effect-row")];
    const bloomSkillType = normalizeSaviorSourceText(bloomCard.querySelector(".source-skill-type")?.textContent || "");
    const allowPositionalFallback = !(savior?.id === "marcille" && bloomSkillType === "궁극기");
    bloomEffects.forEach((row, effectIndex) => {
      if (row.querySelector("img")) return;
      const bloomKey = getEffectRowKey(row);
      const matchedRow = bloomKey
        ? normalEffects.find((candidate) => getEffectRowKey(candidate) === bloomKey)
        : null;
      const normalEffectImage = matchedRow?.querySelector("img")
        || (allowPositionalFallback && !getSharedSaviorEffectName(row.textContent || "")
          ? normalEffects[effectIndex]?.querySelector("img")
          : null);
      if (normalEffectImage) row.insertBefore(normalEffectImage.cloneNode(true), row.firstChild);
    });
  });
}

function createSaviorSkillListFromSource(sourceHtml, sourceUrl, savior) {
  const temp = document.createElement("div");
  temp.innerHTML = createParsedSaviorSourceMarkup(sourceHtml, sourceUrl, savior);
  return temp.querySelector(".source-skill-list");
}

async function applySaviorBloomMode(button, panel) {
  const detailId = Number(button.dataset.detailId || 0);
  const savior = SAVIORS.find((item) => SAVIOR_DETAIL_IDS[item.id] === detailId);
  if (!detailId || !savior || !panel._normalSaviorSourceHtml) return;

  const currentPressed = button.getAttribute("aria-pressed") === "true";
  const nextPressed = !currentPressed;
  const liveSkillList = panel.querySelector(".source-skill-list");
  if (!liveSkillList) return;

  button.disabled = true;
  try {
    if (panel._archivedSaviorSkills) {
      const archivedSkills = createArchivedSaviorSkills(panel._archivedSaviorSkills, {
        language: currentLanguage,
        blossomed: nextPressed
      });
      if (!archivedSkills.length) throw new Error("Archived Bloom skill list not found");
      liveSkillList.innerHTML = archivedSkills.map(renderSourceSkillCard).join("");
      setSaviorBloomProfileGrade(panel, nextPressed);
      button.setAttribute("aria-pressed", String(nextPressed));
      applyLanguageToDOM(liveSkillList);
      return;
    }

    if (!nextPressed) {
      const normalList = createSaviorSkillListFromSource(
        panel._normalSaviorSourceHtml,
        panel._normalSaviorSourceUrl || getSaviorBackupUrl(detailId),
        savior
      );
      if (!normalList) throw new Error("Normal skill list not found");
      liveSkillList.innerHTML = normalList.innerHTML;
      setSaviorBloomProfileGrade(panel, false);
      button.setAttribute("aria-pressed", "false");
      applyLanguageToDOM(liveSkillList);
      return;
    }

    if (!panel._bloomSaviorSourceHtml) {
      const bloomUrl = getSaviorBloomBackupUrl(detailId);
      const response = await fetch(bloomUrl, { cache: "no-store" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      panel._bloomSaviorSourceHtml = await response.text();
      panel._bloomSaviorSourceUrl = bloomUrl;
    }

    const normalList = createSaviorSkillListFromSource(
      panel._normalSaviorSourceHtml,
      panel._normalSaviorSourceUrl || getSaviorBackupUrl(detailId),
      savior
    );
    const bloomList = createSaviorSkillListFromSource(
      panel._bloomSaviorSourceHtml,
      panel._bloomSaviorSourceUrl || getSaviorBloomBackupUrl(detailId),
      savior
    );
    if (!bloomList) throw new Error("Bloom skill list not found");

    // 개화 백업은 텍스트 전용이다. 스킬 아이콘은 일반 백업을 재사용하고,
    // 개화로 새로 생긴 효과는 다른 구원자 백업의 동일 효과 아이콘을 공용으로 재사용한다.
    cloneSaviorSkillVisuals(normalList, bloomList, savior);
    normalizeClarissaBloomLeapText(bloomList, savior);
    await applyBloomEffectVisualCorrections(bloomList, savior);
    await hydrateSharedBloomEffectImages(bloomList);
    liveSkillList.innerHTML = bloomList.innerHTML;
    setSaviorBloomProfileGrade(panel, true);
    button.setAttribute("aria-pressed", "true");
    applyLanguageToDOM(liveSkillList);
  } catch (error) {
    console.warn("Savior Bloom backup load failed:", detailId, error);
    const status = document.createElement("div");
    status.className = "source-bloom-error";
    status.textContent = translateString("개화 스킬 백업 데이터를 불러올 수 없습니다.");
    button.closest(".source-bloom-toolbar")?.appendChild(status);
  } finally {
    button.disabled = false;
  }
}

detailContent.addEventListener("click", async (event) => {
  if (await handleArcanaPreviewClick(event)) return;

  const bloomButton = event.target.closest("[data-savior-bloom-toggle]");
  if (bloomButton && detailContent.contains(bloomButton)) {
    const panel = bloomButton.closest("[data-savior-source-panel]");
    if (panel) await applySaviorBloomMode(bloomButton, panel);
    return;
  }

  const button = event.target.closest("[data-savior-source-toggle]");
  if (!button || !detailContent.contains(button)) return;

  const wrapper = button.closest("[data-savior-source-detail]");
  const panel = wrapper?.querySelector("[data-savior-source-panel]");
  if (!panel) return;

  const isOpen = button.getAttribute("aria-expanded") === "true";
  const nextOpen = !isOpen;
  button.setAttribute("aria-expanded", String(nextOpen));
  panel.hidden = !nextOpen;
  button.setAttribute("aria-label", translateString(nextOpen ? "상세정보 접기" : "상세정보 펼치기"));

  if (nextOpen) {
    await loadSaviorSourcePanel(button, panel);
  }
});

detailContent.addEventListener("keydown", (event) => {
  const trigger = event.target.closest("[data-arcana-preview-id]");
  if (event.key === " " && trigger && detailContent.contains(trigger)) {
    event.preventDefault();
    trigger.click();
  }
});

function getResolvedArcanaNames(slots) {
  return (slots || []).flatMap((slot) =>
    slot ? resolveArcanaChoices(slot.name).map((choice) => choice.name) : []
  );
}

function buildAlternativeArcana(savior, pveArcana, existingAlternatives) {
  if (STRIKER_ARCANA_TARGET_IDS.has(savior.id)) {
    return Array.from(
      { length: 5 },
      (_, index) => existingAlternatives?.[index] || null
    );
  }

  if (
    savior.id === "clarissa" ||
    savior.id === "lugh" ||
    savior.id === "wedding-carmen" ||
    STANDARD_SUPPORTER_BUILD_IDS.has(savior.id)
  ) {
    return Array.from(
      { length: 5 },
      (_, index) => existingAlternatives?.[index] || null
    );
  }

  const result = [];
  const seen = new Set();

  const add = (name, note = "") => {
    const key = `${name}::${note}`;
    if (!name || seen.has(key)) return;
    seen.add(key);
    result.push({ name, note });
  };

  const isStrikerArcanaSwapTarget = STRIKER_ARCANA_SWAP_IDS.has(savior.id);

  (existingAlternatives || []).forEach((slot) => {
    if (!slot?.name) return;

    if (isStrikerArcanaSwapTarget && String(slot.name).includes("음독의 각오")) {
      add(
        String(slot.name).split("음독의 각오").join("완벽한 바니걸"),
        "음독의 각오 대체"
      );
      return;
    }

    add(slot.name, slot.note || "");
  });

  const names = new Set(getResolvedArcanaNames(pveArcana));

  if (savior.id === "cristelle") {
    return [
      { name: "어느 한 기사의 맹세", note: "하얀 달의 온기는 햇빛처럼/완벽한 바니걸 대체" },
      { name: "노 페인, 노 게인", note: "단점 맞춤 훈련 대체" },
      { name: "누각 위, 유리달 맞이", note: "영원 속박의 굴레 대체" },
      null,
      null
    ];
  }

  if (savior.id === "white-pearl-luna") {
    // 화이트 펄 트랩 루나는 SAVIORS에 입력된 전용 대체 아르카나를 그대로 사용한다.
    return result;
  }

  if (savior.id === "smile") {
    return [
      names.has("단점 보완 맞춤 훈련")
        ? { name: "노 페인, 노 게인", note: "단점 보완 맞춤 훈련 대체" }
        : null,
      names.has("꽃들에게 죽음을")
        ? { name: "메이드 바이 페트라♡ or 별을 보며 꿈을", note: "꽃들에게 죽음을 대체" }
        : null,
      {
        name: "하얀 달의 온기는 햇빛처럼 or 어느 한 기사의 맹세 or 완벽한 바니걸",
        note: "종말은 소녀의 얼굴을 하고 있다. 대체"
      },
      {
        name: "불굴의 역작",
        note: "허수의 개척자 대체"
      },
      null
    ];
  }

  if (savior.id === "luna") {
    // 보이저 구원단 루나는 SAVIORS에 입력된 대체 아르카나 구성을 그대로 사용한다.
    // 별도의 하드코딩으로 덮어쓰지 않는다.
    return result;
  }

  if (savior.id === "professor-m") {
    // 프로페서M은 SAVIORS에 입력된 전용 대체 아르카나 구성만 사용한다.
    return result;
  }

  if (savior.id === "waltz-asherah") {
    // 왈츠 오브 스타라이트 아세라도 입력된 대체 아르카나 구성만 그대로 사용한다.
    // 서포터 공통 자동 대체 아르카나를 추가하지 않는다.
    return result;
  }

  if (savior.id === "roberta") {
    if (names.has("단점 보완 맞춤 훈련")) {
      add("노 페인, 노 게인", "단점 보완 맞춤 훈련 대체");
    }
    if (names.has("꽃들에게 죽음을")) {
      add("메이드 바이 페트라♡ or 별을 보며 꿈을", "꽃들에게 죽음을 대체");
    }
    return result;
  }

  if (names.has("단점 보완 맞춤 훈련")) {
    add("노 페인, 노 게인", "단점 보완 맞춤 훈련 대체");
  }
  if (names.has("꽃들에게 죽음을")) {
    add("메이드 바이 페트라♡ or 별을 보며 꿈을", "꽃들에게 죽음을 대체");
  }
  if (names.has("하얀 달의 온기는 햇빛처럼")) {
    add("어느 한 기사의 맹세", "하얀 달의 온기는 햇빛처럼 대체");
  }
  if (isStrikerArcanaSwapTarget) {
    add("완벽한 바니걸", "음독의 각오 대체");
  }
  if (savior.className === "서포터") {
    add("누구보다 프로페셔널", "공녀, 왕좌에 오르다 대체");
  }
  if (names.has("본 투 비 와일드")) {
    add("언더커버 캅", "본 투 비 와일드 대체");
  }

  return result;
}

function addEternalBondAlternativeForWhiteMoon(savior, pveArcana, alternatives) {
  const excludedClasses = new Set(["서포터", "디펜더"]);
  const result = [...(alternatives || [])];

  // 전용 대체 아르카나 구성을 사용하는 구원자는 공통 자동 추가 대상에서 제외합니다.
  if (savior.id === "cristelle" || savior.id === "clarissa") return result;
  if (excludedClasses.has(savior.className)) return result;

  const recommendedNames = new Set(getResolvedArcanaNames(pveArcana));
  if (!recommendedNames.has("하얀 달의 온기는 햇빛처럼")) return result;

  const alternativeNames = new Set(getResolvedArcanaNames(result));
  if (alternativeNames.has("영원 속박의 굴레")) return result;

  const entry = {
    name: "영원 속박의 굴레",
    note: "하얀 달의 온기는 햇빛처럼 대체"
  };

  let lastFilledIndex = -1;
  result.forEach((slot, index) => {
    if (slot?.name) lastFilledIndex = index;
  });

  const insertIndex = lastFilledIndex + 1;
  if (insertIndex < result.length && !result[insertIndex]) {
    result[insertIndex] = entry;
  } else {
    result.push(entry);
  }

  return result;
}

function createDetailMarkup(savior) {
  const build = getBuild(savior);
  const hasCommonArcana = (build.arcana.pve || []).some((arcana) =>
    String(arcana?.name || "").includes("공용 아르카나")
  );
  const basePveArcana = hasCommonArcana ? COMMON_ARCANA_SLOTS : build.arcana.pve;
  const pveArcana = STRIKER_ARCANA_SWAP_IDS.has(savior.id)
    ? (basePveArcana || []).map((slot) =>
        slot
          ? {
              ...slot,
              name: String(slot.name).split("완벽한 바니걸").join("음독의 각오")
            }
          : null
      )
    : basePveArcana;
  const baseAlternativeArcana = savior.detail
    ? buildAlternativeArcana(
        savior,
        pveArcana,
        build.arcana.alternatives
      )
    : build.arcana.alternatives;
  const alternativeArcana = addEternalBondAlternativeForWhiteMoon(
    savior,
    pveArcana,
    baseAlternativeArcana
  );

  const saviorDetailId = resolveSaviorDetailId(savior);
  const localProfile = getLocalSaviorProfile(savior);
  const guideButton = `
      <div class="savior-source-detail" data-savior-source-detail>
        <button class="external-guide savior-detail-toggle" type="button"
          data-savior-source-toggle data-detail-id="${escapeHtml(saviorDetailId || "")}" data-savior-key="${escapeHtml(savior.id)}"
          aria-expanded="false">
          <span>스킬설명 및 상세정보</span>
          <span class="savior-detail-chevron" aria-hidden="true">⌄</span>
        </button>
        <div class="savior-source-panel" data-savior-source-panel hidden></div>
      </div>
    `;

  const illustrationSection = localProfile?.illustration
    ? `
      <section class="content-section savior-illustration-section">
        <details class="savior-illustration-details">
          <summary aria-label="${escapeHtml(translateString("일러스트"))}">
            <span>${escapeHtml(translateString("일러스트"))}</span>
            <span class="savior-illustration-chevron" aria-hidden="true">⌄</span>
          </summary>
          <div class="savior-illustration-body">
            <img src="${escapeHtml(localProfile.illustration)}"
              alt="${escapeHtml(`${getLocalizedSaviorName(savior.name)} 일러스트`)}"
              loading="lazy" decoding="async">
          </div>
        </details>
      </section>
    `
    : "";

  const growthPriority = GROWTH_PRIORITY[savior.id] || {
    tier: "미정",
    level: "tier-unrated"
  };
  const mainContents = MAIN_CONTENTS[savior.id] || ["미정"];

  const roleBadge =
    savior.role && savior.role !== savior.className
      ? `<span class="detail-badge">${escapeHtml(savior.role)}</span>`
      : "";

  const attackTypeBadge = savior.attackType
    ? `<span class="detail-badge">${escapeHtml(savior.attackType)}</span>`
    : "";

  const pveArcanaTitle = "PVE 추천 아르카나";
  const alternativeArcanaTitle = "대체 아르카나";

  return `
    <header class="detail-hero" data-element="${escapeHtml(savior.element)}">
      <div class="detail-portrait">
        ${imageMarkup(savior, true)}
      </div>
      <div class="detail-info">
        <div class="detail-badges">
          <span class="detail-badge attribute">${escapeHtml(ELEMENT_LABELS[savior.element])}</span>
          <span class="detail-badge">${escapeHtml(savior.grade)}</span>
          <span class="detail-badge">${escapeHtml(savior.className)}</span>
          ${roleBadge}
          ${attackTypeBadge}
          ${savior.upcoming ? `<span class="detail-badge">${escapeHtml(translateString("출시 예정"))}</span>` : ""}
        </div>

        <h1 class="detail-title" data-i18n-kind="savior" data-i18n-source="${escapeHtml(savior.name)}">${escapeHtml(getLocalizedSaviorName(savior.name))}</h1>
        <p class="detail-subtitle" data-i18n-kind="subtitle" data-i18n-source="${escapeHtml(savior.subtitle)}">${escapeHtml(getLocalizedSubtitle(savior.subtitle))}</p>
        <p class="detail-summary">${escapeHtml(translateString("구원자 정보는 "))}<a href="https://ss.espr.gg/" target="_blank" rel="noopener noreferrer" style="color:inherit;text-decoration:underline;text-underline-offset:3px;">${escapeHtml(translateString("에크하르트 초월지식 학회(ESPR)"))}</a>${escapeHtml(translateString("를 참고합니다."))}</p>

      </div>
    </header>

    ${illustrationSection}
    ${guideButton ? `<section class="content-section savior-source-section">${guideButton}</section>` : ""}

    <section class="savior-quick-summary" id="growth-priority">
      <div class="savior-tier-compact ${escapeHtml(growthPriority.level)}">
        <span class="savior-tier-label">PVE</span>
        <strong>${escapeHtml(growthPriority.tier)}</strong>
        ${growthPriority.note
          ? `<span class="savior-tier-note">${escapeHtml(growthPriority.note)}</span>`
          : ""}
      </div>
      <div class="savior-content-compact">
        <h2>주 사용 콘텐츠</h2>
        <div class="main-content-chips">
          ${mainContents.map((content) => `
            <span class="main-content-chip ${content === "없음" ? "is-empty" : ""}">
              ${escapeHtml(content)}
            </span>
          `).join("")}
        </div>
      </div>
    </section>

    <section class="content-section journey-stat-priority-section" id="journey-stat-priority">
      <div class="section-titlebar">
        <div>
          <p>JOURNEY STAT PRIORITY</p>
          <h2>여정 스탯 우선순위</h2>
        </div>
      </div>
      <div class="section-body">
        ${createJourneyStatPriorityMarkup(savior)}
      </div>
    </section>

    <section class="content-section" id="equipment">
      <div class="section-titlebar">
        <div>
          <p>EQUIPMENT SETTING</p>
          <h2>장비 세팅</h2>
        </div>
      </div>
      <div class="section-body">
        <div class="build-grid">
          ${createEquipmentCard("PVE", build.equipment.pve, "pve", "작전 · 회랑 · 코스모 게이트")}
        </div>
      </div>
    </section>

    <section class="content-section" id="arcana" data-arcana-savior="${escapeHtml(savior.id)}">
      <div class="section-titlebar">
        <div>
          <p>ARCANA SETTING</p>
          <h2>아르카나 세팅</h2>
        </div>
      </div>
      <div class="section-body">
        ${createSaviorArcanaSettingMarkup(savior, pveArcana, alternativeArcana)}
      </div>
    </section>
  `;
}

function parseEquipmentSetPart(value) {
  const match = String(value || "")
    .trim()
    .match(/^([가-힣]+)\s*\(\s*(\d+)\s*\)(.*)$/);

  if (!match) return null;

  return {
    name: match[1],
    count: match[2],
    suffix: match[3].trim().replace(/^x\s*(\d+)$/i, "× $1")
  };
}

const EQUIPMENT_SET_COMPACT_LABELS = Object.freeze({
  en: Object.freeze({
    "속도": "Speed",
    "방어": "Defense",
    "저항": "Resistance",
    "공격": "Attack",
    "통찰": "Insight",
    "적중": "Hit",
    "투지": "Valor",
    "정밀": "Precision",
    "생명": "Health",
    "파괴": "Destruction",
    "장벽": "Barrier",
    "섬멸": "Annihilation"
  }),
  ja: Object.freeze({
    "속도": "速度",
    "방어": "防御",
    "저항": "抵抗",
    "공격": "攻撃",
    "통찰": "洞察",
    "적중": "的中",
    "투지": "闘志",
    "정밀": "精密",
    "생명": "体力",
    "파괴": "破壊",
    "장벽": "防壁",
    "섬멸": "殲滅"
  })
});

function refreshEquipmentSetLabels(root = document) {
  const container = root?.querySelectorAll ? root : document;
  container.querySelectorAll(".equipment-set-label[data-set-name][data-set-count]").forEach((label) => {
    const name = label.dataset.setName || "";
    const count = label.dataset.setCount || "";
    const localizedName = currentLanguage === "ko"
      ? name
      : (EQUIPMENT_SET_COMPACT_LABELS[currentLanguage]?.[name] || translateTerm(name));
    label.textContent = `${localizedName}(${count})`;
  });
}

function createEquipmentSetPart(part) {
  const parsed = parseEquipmentSetPart(part);
  if (!parsed) return "";

  const label = `${parsed.name}(${parsed.count})`;
  const image = EQUIPMENT_SET_IMAGE_NAMES.has(parsed.name)
    ? `
      <img class="equipment-set-icon"
        src="${escapeHtml(`${EQUIPMENT_SET_IMAGE_ROOT}/${encodeURIComponent(parsed.name)}.webp`)}"
        alt="" loading="lazy" decoding="async" aria-hidden="true"
        onerror="this.parentElement.classList.add('is-image-missing'); this.remove()">
    `
    : "";

  return `
    <span class="equipment-set-part">
      ${image}
      <strong class="equipment-set-label" data-set-name="${escapeHtml(parsed.name)}" data-set-count="${escapeHtml(parsed.count)}">${escapeHtml(label)}</strong>
      ${parsed.suffix ? `<small class="equipment-set-suffix">${escapeHtml(parsed.suffix)}</small>` : ""}
    </span>
  `;
}

function createEquipmentSetMarkup(value) {
  const source = String(value || "").trim();
  const parts = source.split(/\s*\+\s*/).filter(Boolean);

  if (!parts.length || parts.some((part) => !parseEquipmentSetPart(part))) {
    return `<span class="equipment-set-plain">${escapeHtml(source)}</span>`;
  }

  return `
    <span class="equipment-set-combination">
      ${parts.map((part, index) => `
        <span class="equipment-set-joined">
          ${index ? `<span class="equipment-set-plus" aria-hidden="true">+</span>` : ""}
          ${createEquipmentSetPart(part)}
        </span>
      `).join("")}
    </span>
  `;
}


function createEquipmentOptionListMarkup(options, fallbackValue) {
  if (!Array.isArray(options) || !options.length) {
    return escapeHtml(fallbackValue || "");
  }

  return `
    <div class="build-option-list" style="display:grid;gap:9px;">
      ${options.map((option) => `
        <div class="build-option-entry" style="min-width:0;">
          <strong style="display:block;color:var(--text);font-weight:900;">${escapeHtml(option?.value || "")}</strong>
          ${option?.note ? `<small class="build-set-note" style="margin-top:3px;">${escapeHtml(option.note)}</small>` : ""}
        </div>
      `).join("")}
    </div>
  `;
}

function createEquipmentSetOptionsMarkup(data) {
  if (Array.isArray(data.setOptions) && data.setOptions.length) {
    return `
      <div class="equipment-set-option-list" style="display:grid;gap:10px;">
        ${data.setOptions.map((option) => `
          <div class="equipment-set-option-entry" style="min-width:0;">
            ${createEquipmentSetMarkup(option?.value || "")}
            ${option?.note ? `<small class="build-set-note" style="margin-top:4px;">${escapeHtml(option.note)}</small>` : ""}
          </div>
        `).join("")}
      </div>
    `;
  }

  const sets = Array.isArray(data.sets) ? data.sets : [data.sets];
  return `
    ${sets.map(createEquipmentSetMarkup).join("")}
    ${Array.isArray(data.setNotes)
      ? data.setNotes.map((note) => `<small class="build-set-note">${escapeHtml(note)}</small>`).join("")
      : data.setNote
        ? `<small class="build-set-note">${escapeHtml(data.setNote)}</small>`
        : ""}
  `;
}

function createEquipmentCard(mode, data, className, subtitle) {
  return `
    <article class="build-card ${className}">
      <div class="build-heading">
        <span class="mode-badge">${mode}</span>
        <div>
          <small>${escapeHtml(subtitle)}</small>
          <strong>${mode} 추천 세팅</strong>
        </div>
      </div>
      <dl class="build-rows">
        <div class="build-row">
          <dt>목걸이</dt>
          <dd>
            ${createEquipmentOptionListMarkup(data.necklaceOptions, data.necklace)}
            ${!Array.isArray(data.necklaceOptions) && data.necklaceNote
              ? `<small class="build-set-note">${escapeHtml(data.necklaceNote)}</small>`
              : ""}
          </dd>
        </div>
        <div class="build-row">
          <dt>반지</dt>
          <dd>${createEquipmentOptionListMarkup(data.ringOptions, data.ring)}</dd>
        </div>
        <div class="build-row">
          <dt>추천 세트</dt>
          <dd class="equipment-set-list">
            ${createEquipmentSetOptionsMarkup(data)}
          </dd>
        </div>
        <div class="build-row">
          <dt>잠재력</dt>
          <dd>${escapeHtml(data.potential).replace(/\n/g, "<br>")}</dd>
        </div>
      </dl>
    </article>
  `;
}


// Selection survives the existing archive/profile refreshes and language changes.
// Recommendation/build data is never changed by the preview.
const arcanaPreviewSelections = new Map();
const arcanaPreviewLoadErrors = new Set();
const ARCANA_PREVIEW_TEXT = {
  ko: {
    hint: "아르카나를 선택하면 획득 가능한 효과를 확인할 수 있습니다.",
    heading: "획득 가능 효과", special: "특수 잠재력", select: "획득 효과 미리보기",
    detail: "아르카나 상세 보기 →", loading: "획득 효과를 불러오는 중입니다.",
    error: "획득 효과를 불러오지 못했습니다. 다시 선택하거나 상세 정보를 확인해 주세요.",
    empty: "표시할 획득 잠재력이 등록되어 있지 않습니다.", missing: "번역 미등록"
  },
  en: {
    hint: "Select an Arcana to preview its obtainable effects.",
    heading: "Obtainable Effects", special: "Special Potential", select: "Preview obtainable effects",
    detail: "View Arcana details →", loading: "Loading obtainable effects…",
    error: "Could not load effects. Select again to retry or view the Arcana details.",
    empty: "No obtainable Potentials are recorded.", missing: "Translation unavailable"
  },
  ja: {
    hint: "アルカナを選択すると、獲得可能な効果を確認できます。",
    heading: "獲得可能な効果", special: "特殊潜在力", select: "獲得効果をプレビュー",
    detail: "アルカナ詳細を見る →", loading: "獲得効果を読み込み中です。",
    error: "効果を読み込めませんでした。再度選択するか、アルカナ詳細をご確認ください。",
    empty: "獲得可能な潜在力は登録されていません。", missing: "翻訳未登録"
  }
};

function arcanaPreviewText(key) {
  return ARCANA_PREVIEW_TEXT[currentLanguage][key];
}

function getArcanaPreviewName(value, id) {
  // Do not fall back to Korean on an English/Japanese preview.
  const name = typeof value === "object" ? value?.[currentLanguage] : "";
  return name?.trim() || `${arcanaPreviewText("missing")} (${id})`;
}

function getArcanaPreviewGroups(arcana, archive) {
  const potentials = new Map((archive?.potentials || []).map((potential) => [Number(potential.id), potential]));
  const allowedTypes = new Set(["일반 잠재력", "특수 잠재력"]);
  const groupKey = (ids) => [...ids].sort((a, b) => a - b).join(",");
  const output = [];
  const seen = new Set();
  const add = (branches) => {
    const key = JSON.stringify(branches);
    if (branches.length && !seen.has(key)) {
      seen.add(key);
      output.push(branches);
    }
  };

  for (const event of arcana?.events || []) {
    const choices = (event.choices || []).map((choice) => (choice.successRewards || []).map((rewards) =>
      [...new Set((rewards || []).filter((reward) => {
        const potential = potentials.get(Number(reward.rewardId));
        return reward.type === "RT_SE_POTEN" && allowedTypes.has(potential?.type)
          && Number(reward.max ?? reward.min ?? 1) > 0;
      }).map((reward) => Number(reward.rewardId)))]
    ).filter((ids) => ids.length));
    if (!choices.length) continue;

    // Reward groups coexist; entries inside a group and event choices are alternatives.
    // Factor shared groups out before joining choice-specific rewards with " or ".
    const common = choices[0].filter((ids) => choices.every((groups) =>
      groups.some((group) => groupKey(group) === groupKey(ids))
    ));
    common.forEach((ids) => add([[ids]]));
    const commonKeys = new Set(common.map(groupKey));
    const branches = choices.map((groups) => groups.filter((ids) => !commonKeys.has(groupKey(ids))))
      .filter((groups) => groups.length);
    const distinct = [...new Map(branches.map((groups) => [JSON.stringify(groups), groups])).values()];
    if (distinct.length === 1) distinct[0].forEach((ids) => add([[ids]]));
    else add(distinct);
  }
  return output;
}

function createArcanaPreviewEffects(arcana, archive) {
  const potentials = new Map((archive?.potentials || []).map((potential) => [Number(potential.id), potential]));
  const renderPotential = (id) => {
    const potential = potentials.get(id);
    const special = potential.type === "특수 잠재력";
    const name = getArcanaPreviewName(potential.name, id);
    return `<span class="arcana-preview-effect${special ? " is-special" : ""}">
      ${createArcanaPotentialIcon(potential)}
      <span class="arcana-preview-effect-label">${special
        ? `<small>${escapeHtml(arcanaPreviewText("special"))} · </small>` : ""}${escapeHtml(name)}</span>
    </span>`;
  };
  const or = '<span class="arcana-preview-connector"> or </span>';
  return getArcanaPreviewGroups(arcana, archive).map((branches) =>
    `<span class="arcana-preview-group">${branches.map((groups) => {
      const content = groups.map((ids) => ids.map(renderPotential).join(or))
        .join('<span class="arcana-preview-connector"> + </span>');
      return branches.length > 1 && groups.length > 1 ? `(${content})` : content;
    }).join(or)}</span>`
  ).join(" ");
}

function getArcanaPreviewSelectionKey(mode) {
  return JSON.stringify([
    mode.closest("[data-arcana-savior]")?.dataset.arcanaSavior,
    mode.closest("[data-arcana-preset]")?.dataset.arcanaPreset || "",
    mode.dataset.arcanaPreviewKey
  ]);
}

function refreshArcanaPreviews(root = detailContent) {
  const modes = [...(root.querySelectorAll?.("[data-arcana-preview-key]") || [])];
  if (root.matches?.("[data-arcana-preview-key]")) modes.unshift(root);
  modes.forEach((mode) => {
    const preview = mode.querySelector("[data-arcana-preview]");
    if (!preview) return;
    const selectedId = arcanaPreviewSelections.get(getArcanaPreviewSelectionKey(mode));
    const archive = arcanaDatabaseState.data;
    const arcana = archive?.arcanas?.find((item) => Number(item.id) === selectedId);
    mode.querySelectorAll("[data-arcana-preview-id]").forEach((trigger) => {
      const id = Number(trigger.dataset.arcanaPreviewId);
      const selected = id === selectedId;
      trigger.setAttribute("aria-pressed", String(selected));
      trigger.classList.toggle("is-preview-selected", selected);
      const name = archive?.arcanas?.find((item) => Number(item.id) === id)?.name;
      const label = name ? getArcanaPreviewName(name, id) : getLocalizedArcanaName(trigger.dataset.arcanaPreviewName);
      trigger.setAttribute("aria-label", `${label} · ${arcanaPreviewText("select")}`);
    });
    mode.querySelectorAll("[data-arcana-default-id]").forEach((card) => {
      card.classList.toggle("is-preview-selected", Number(card.dataset.arcanaDefaultId) === selectedId);
    });
    preview.classList.toggle("is-empty", selectedId == null);
    if (selectedId == null) {
      preview.innerHTML = `<p class="arcana-preview-message">${escapeHtml(arcanaPreviewText("hint"))}</p>`;
      return;
    }
    const effects = arcana ? createArcanaPreviewEffects(arcana, archive) : "";
    const message = arcana ? arcanaPreviewText("empty")
      : arcanaPreviewText(arcanaPreviewLoadErrors.has(selectedId) || archive ? "error" : "loading");
    preview.innerHTML = `
      <div class="arcana-preview-header">
        <div>${arcana ? `<strong>${escapeHtml(getArcanaPreviewName(arcana.name, arcana.id))}</strong>` : ""}
          <span>${escapeHtml(arcanaPreviewText("heading"))}</span></div>
        <a class="arcana-preview-detail" href="#arcana/${selectedId}">${escapeHtml(arcanaPreviewText("detail"))}</a>
      </div>
      ${effects ? `<div class="arcana-preview-effects">${effects}</div>`
        : `<p class="arcana-preview-message">${escapeHtml(message)}</p>`}
    `;
  });
}

async function handleArcanaPreviewClick(event) {
  const trigger = event.target.closest("[data-arcana-preview-id]");
  const card = event.target.closest("[data-arcana-default-id]");
  const mode = (trigger || card)?.closest("[data-arcana-preview-key]");
  if (!mode || !detailContent.contains(mode)) return false;
  const id = Number(trigger?.dataset.arcanaPreviewId || card?.dataset.arcanaDefaultId);
  if (!Number.isFinite(id)) return false;
  event.preventDefault();
  arcanaPreviewSelections.set(getArcanaPreviewSelectionKey(mode), id);
  arcanaPreviewLoadErrors.delete(id);
  refreshArcanaPreviews(mode);
  if (!arcanaDatabaseState.data) {
    try {
      arcanaDatabaseState.data = await loadArcanaArchive();
    } catch (error) {
      arcanaPreviewLoadErrors.add(id);
      console.warn("Arcana effect preview load failed:", error);
    }
    refreshArcanaPreviews(detailContent);
  }
  return true;
}

function normalizeArcanaAlias(value) {
  return String(value || "")
    .replace(/^\*+/, "")
    .replace(/^통찰\(4\)\s*:\s*/, "")
    .replace(/\s*택\s*1\s*/g, "")
    .replace(/\(추천\)/g, "")
    .replace(/\s*\(\s*/g, "(")
    .replace(/\s*\)\s*/g, ")")
    .trim();
}

function resolveArcanaChoices(rawName) {
  const normalized = normalizeArcanaAlias(rawName);

  if (!normalized) {
    return [];
  }

  if (normalized.includes("공용 아르카나")) {
    return COMMON_ARCANA_SLOTS.flatMap((slot) => ARCANA_LIBRARY[slot.name] || []);
  }

  const aliases = normalized
    .split(/\s*or\s*/i)
    .map((value) => normalizeArcanaAlias(value))
    .filter(Boolean);

  return aliases.flatMap((alias) => ARCANA_LIBRARY[alias] || []);
}

function getArcanaDetailUrl(name) {
  const detailId = ARCANA_DETAIL_IDS[name];
  return detailId ? `#arcana/${detailId}` : "";
}

function createArcanaImages(choices) {
  const imageChoices = choices.filter((choice) => choice?.image);
  if (!imageChoices.length) return "";

  return `
    <div class="arcana-card-images" style="--arcana-count:${Math.min(imageChoices.length, 4)}">
      ${imageChoices.slice(0, 4).map((choice) => {
        const detailUrl = getArcanaDetailUrl(choice.name);
        const localizedName = getLocalizedArcanaName(choice.name);
        const detailLabel = translateString("아르카나 상세정보");

        return detailUrl
          ? `
            <a class="arcana-card-link" href="${escapeHtml(detailUrl)}"
              role="button" aria-pressed="false" data-arcana-preview-id="${choice.detailId || ARCANA_DETAIL_IDS[choice.name]}"
              data-arcana-preview-name="${escapeHtml(choice.name)}"
              aria-label="${escapeHtml(`${localizedName} ${detailLabel}`)}">
              <img src="${escapeHtml(choice.image)}" alt="${escapeHtml(localizedName)}"
                loading="lazy"
                onerror="this.style.display='none'">
            </a>
          `
          : `
            <span class="arcana-card-link is-disabled">
              <img src="${escapeHtml(choice.image)}" alt="${escapeHtml(localizedName)}"
                loading="lazy"
                onerror="this.style.display='none'">
            </span>
          `;
      }).join("")}
    </div>
  `;
}

function createArcanaNameLinks(choices) {
  return choices.map((choice, index) => {
    const detailUrl = getArcanaDetailUrl(choice.name);
    const localizedName = getLocalizedArcanaName(choice.name);
    const separator = index > 0
      ? `<span class="arcana-card-separator" aria-hidden="true">/</span>`
      : "";

    const sourceAttr = escapeHtml(choice.name);
    const nameMarkup = detailUrl
      ? `<a class="arcana-card-name-link" href="${escapeHtml(detailUrl)}"
          role="button" aria-pressed="false" data-arcana-preview-id="${choice.detailId || ARCANA_DETAIL_IDS[choice.name]}"
          data-arcana-preview-name="${sourceAttr}"
          data-i18n-kind="arcana" data-i18n-source="${sourceAttr}">${escapeHtml(localizedName)}</a>`
      : `<span data-i18n-kind="arcana" data-i18n-source="${sourceAttr}">${escapeHtml(localizedName)}</span>`;

    return `${separator}${nameMarkup}`;
  }).join("");
}

function createArcanaMode(title, description, slots, color, minSlots = 5) {
  const normalized = Array.from(
    { length: Math.max(minSlots, slots?.length || 0) },
    (_, index) => slots?.[index] || null
  );

  return `
    <div class="arcana-mode" data-arcana-preview-key="${escapeHtml(title)}">
      <div class="arcana-mode-title">
        <strong>${escapeHtml(title)}</strong>
        <span>${escapeHtml(description)}</span>
      </div>
      <div class="arcana-preview is-empty" data-arcana-preview aria-live="polite" aria-atomic="true"></div>
      <div class="arcana-slots">
        ${normalized.map((arcana, index) => {
          if (!arcana) {
            return `
              <div class="arcana-slot empty" style="--slot-color:${color}">
                <small>SLOT ${index + 1}</small>
                <strong>미등록</strong>
                <em>대체 아르카나가 등록되지 않았습니다.</em>
              </div>
            `;
          }

          const choices = resolveArcanaChoices(arcana.name);

          if (!choices.length) {
            return `
              <div class="arcana-slot empty" style="--slot-color:${color}">
                <small>SLOT ${index + 1}</small>
                <strong>${escapeHtml(arcana.name)}</strong>
                <em>${escapeHtml(arcana.note || "원본 시트 표기")}</em>
              </div>
            `;
          }

          const rawNoteText = String(arcana.note || "").trim();
          const noteText = /엑셀.*추천/.test(rawNoteText) ? "" : rawNoteText;

          return `
            <div class="arcana-slot has-arcana-card" style="--slot-color:${color}"
              ${choices.length === 1 && getArcanaDetailUrl(choices[0].name)
                ? `data-arcana-default-id="${choices[0].detailId || ARCANA_DETAIL_IDS[choices[0].name]}"` : ""}>
              ${createArcanaImages(choices)}
              <div class="arcana-card-copy">
                <small>SLOT ${index + 1}${choices.length > 1 ? " · 선택" : ""}</small>
                <strong class="arcana-card-name-links">${createArcanaNameLinks(choices)}</strong>
                ${noteText ? `<em>${escapeHtml(noteText)}</em>` : ""}
              </div>
            </div>
          `;
        }).join("")}
      </div>
    </div>
  `;
}


function createArcanaNoticeMode(title, description, note, color) {
  return `
    <div class="arcana-mode">
      <div class="arcana-mode-title">
        <strong>${escapeHtml(title)}</strong>
        <span>${escapeHtml(description)}</span>
      </div>
      <div class="arcana-slots">
        <div class="arcana-slot empty" style="--slot-color:${color}">
          <small>${escapeHtml(translateString("대체 아르카나"))}</small>
          <strong>${escapeHtml(translateString("없음"))}</strong>
          <em>${escapeHtml(note)}</em>
        </div>
      </div>
    </div>
  `;
}

function createDefenderArcanaCollapse(title, preset) {
  const hasAlternatives = Array.isArray(preset.alternatives) && preset.alternatives.length > 0;

  return `
    <details class="savior-illustration-details defender-arcana-details"
      data-arcana-preset="${escapeHtml(title)}"
      style="overflow:hidden;border:1px solid var(--line);border-radius:14px;">
      <summary aria-label="${escapeHtml(translateString(title))}">
        <span>${escapeHtml(translateString(title))}</span>
        <span class="savior-illustration-chevron" aria-hidden="true">⌄</span>
      </summary>
      <div class="defender-arcana-collapse-body"
        style="display:grid;gap:18px;padding:16px 20px 20px;border-top:1px solid var(--line);">
        ${createArcanaMode(
          "PVE 추천 아르카나",
          "주요 PVE 콘텐츠",
          preset.recommended,
          "var(--pve)",
          5
        )}
        ${hasAlternatives
          ? createArcanaMode(
              "대체 아르카나",
              "보유 상황에 따라 교체",
              preset.alternatives,
              "var(--accent)",
              preset.alternatives.length
            )
          : createArcanaNoticeMode(
              "대체 아르카나",
              "보유 상황에 따라 교체",
              preset.alternativeNote || "",
              "var(--accent)"
            )}
      </div>
    </details>
  `;
}

function createSaviorArcanaSettingMarkup(savior, pveArcana, alternativeArcana) {
  if (savior.className !== "디펜더" || savior.id === "white-pearl-luna") {
    return `
      ${createArcanaMode("PVE 추천 아르카나", "주요 PVE 콘텐츠", pveArcana, "var(--pve)")}
      ${createArcanaMode("대체 아르카나", "보유 상황에 따라 교체", alternativeArcana, "var(--accent)")}
    `;
  }

  if (savior.id === "haydee") {
    return `
      <div class="defender-arcana-collapse-list" style="display:grid;gap:12px;">
        ${createDefenderArcanaCollapse("퓨어탱커", DEFENDER_PURE_TANK_ARCANA)}
        ${createDefenderArcanaCollapse("공격탱커", DEFENDER_ATTACK_TANK_ARCANA)}
      </div>
    `;
  }

  return `
    <div class="defender-arcana-collapse-list" style="display:grid;gap:12px;">
      ${createDefenderArcanaCollapse("퓨어탱커", DEFENDER_PURE_TANK_ARCANA)}
      ${createDefenderArcanaCollapse("공격탱커", DEFENDER_ATTACK_TANK_ARCANA)}
    </div>
  `;
}

function createEquipmentDatabaseMarkup() {
  const mainRows = EQUIPMENT_MAIN_OPTIONS.map(([part, stat, base, enhanced]) => `
    <tr>
      <td>${escapeHtml(part)}</td>
      <td>${escapeHtml(stat)}</td>
      <td>${escapeHtml(base)}</td>
      <td>${escapeHtml(enhanced)}</td>
    </tr>
  `).join("");

  const subRows = EQUIPMENT_SUB_OPTIONS.flatMap((section) => section.rows).map((row) => `
    <tr>
      <th scope="row">${escapeHtml(row[0])}</th>
      ${row.slice(1).map((value) => `<td>${escapeHtml(value)}</td>`).join("")}
    </tr>
  `).join("");

  return `
    <div class="equipment-page">
      <header class="equipment-hero">
        <p class="eyebrow">EQUIPMENT DATABASE</p>
        <h1>장비</h1>
        <p>구원자 장비 주옵션 및 부옵션 정보입니다.</p>
      </header>

      <section class="equipment-panel">
        <div class="equipment-panel-inner overview-mascot-layout">
          <img class="overview-mascot" src="./images/guide-mascot.webp?v=20260915t1" alt="" aria-hidden="true">
          <h2 class="equipment-section-title">장비 개요</h2>
          <ul class="equipment-overview-list">
            <li>딜러 서브딜러 딜탱은 공격력, 공격력% 또는 생명력, 생명력%, 치명타 확률, 치명타 피해, 속도를 유효 옵션으로 사용합니다.</li>
            <li>일부 구원자는 효과 적중, 방어력, 방어력% 도 유효 옵션으로 활용합니다.</li>
            <li>장비 부족 시 치명타 확률 + 추가 유효 옵션 1줄 조합도 사용할 수 있습니다.</li>
            <li>장비 세팅이 충분히 갖춰진 이후에는 유효 옵션 3 이상 장비 사용을 권장합니다.</li>
            <li>초보 단장님은 딜러 세팅 시 통찰 세트를 우선 권장합니다. 일부 구원자를 제외하면 파괴 세트는 세팅 난이도가 높은 편입니다.</li>
          </ul>

        </div>
      </section>

      <section class="equipment-panel">
        <div class="equipment-panel-inner">
          <h2 class="equipment-section-title">주옵션 (Tier 2)</h2>
          <div class="equipment-table-wrap">
            <table class="equipment-table main-options">
              <colgroup>
                <col class="main-col-part">
                <col class="main-col-stat">
                <col class="main-col-base">
                <col class="main-col-enhanced">
              </colgroup>
              <thead>
                <tr>
                  <th scope="col">부위</th>
                  <th scope="col">주 능력치</th>
                  <th scope="col">기본 주능력치 (+0)</th>
                  <th scope="col">기본 주능력치 (+15)</th>
                </tr>
              </thead>
              <tbody>${mainRows}</tbody>
            </table>
          </div>

          <div class="equipment-guidance" aria-label="세트별 권장 능력치">
            <p><strong>통찰 4세트</strong> 착용 시 권장 치명타 확률 90% 이상, 치명타 피해 90% 이상</p>
            <p><strong>파괴 4세트</strong> 착용 시 권장 치명타 확률 80% 이상, 치명타 피해 140% 이상</p>
            <p><strong>적중 2세트</strong> 착용 시 권장 효과적중 140% 이상</p>
          </div>
        </div>
      </section>

      <section class="equipment-panel">
        <div class="equipment-panel-inner">
          <h2 class="equipment-section-title">부옵션 (Tier 2)</h2>
          <div class="equipment-table-wrap sub-options-wrap">
            <table class="equipment-table sub-options">
              <colgroup>
                <col class="sub-col-option">
                ${Array.from({ length: 6 }, () => '<col class="sub-col-stage">').join("")}
              </colgroup>
              <thead>
                <tr>
                  <th scope="col">옵션</th>
                  ${Array.from({ length: 6 }, (_, index) =>
                    `<th scope="col">${index + 1}단계</th>`
                  ).join("")}
                </tr>
              </thead>
              <tbody>${subRows}</tbody>
            </table>
          </div>

          <div class="equipment-guidance" aria-label="장비 티어 판정 기준">
            <p>치명타 확률 + 치명타 피해의 합이 <strong>13% 이상</strong>일 경우 0티어 장비.</p>
            <p>치명타 확률 + 치명타 피해의 합이 <strong>10% 이상 ~ 12% 미만</strong>일 경우 1티어 장비.</p>
            <p>치명타 확률 + 치명타 피해의 합이 <strong>7% 이상 ~ 9% 미만</strong>일 경우 2티어 장비.</p>
            <p>치명타 확률 + 치명타 피해의 합이 <strong>4% 이상 ~ 6% 미만</strong>일 경우 3티어 장비.</p>
            <p class="equipment-guidance-note">※ 딜러 기준으로 공격력% 수치가 높을 시 0.5티어 상승.</p>
            <p class="equipment-guidance-note">※ 속도 수치가 높을 시 0.5티어 상승.</p>
          </div>
        </div>
      </section>
    </div>
  `;
}

const JOURNEY_CATEGORY_KEYS = ["all", "reset", "raid", "aganon", "flora", "kalaid", "weather"];
const JOURNEY_DIFFICULTY_KEYS = ["all", "easy", "normal", "hard"];

let journeyDatabaseState = {
  requestToken: 0,
  data: null,
  meta: null,
  query: "",
  category: "all",
  difficulty: "all",
  showArcana: true,
  showEvents: true
};

function getJourneyLabels(language = currentLanguage) {
  const table = {
    ko: {
      difficulty: "난이도", all: "전체", easy: "이지", normal: "노말", hard: "하드",
      search: "카드 명, 이벤트 명, 보상 등...", arcana: "아르카나", events: "여정 이벤트",
      reset: "리세트", raid: "토벌", aganon: "아가논", flora: "플로라", kalaid: "칼라이드", weather: "날씨",
      success: "성공 보상", failure: "실패 보상", loading: "여정 데이터를 불러오는 중입니다.",
      empty: "검색 결과가 없습니다.", loadError: "여정 데이터를 불러오지 못했습니다.", clear: "검색어 지우기", savior: "구원자"
    },
    en: {
      difficulty: "Difficulty", all: "All", easy: "Easy", normal: "Normal", hard: "Hard",
      search: "Card name, event name, rewards...", arcana: "Arcana", events: "Journey Events",
      reset: "Reset", raid: "Raid", aganon: "Aganon", flora: "Flora", kalaid: "Kalaid", weather: "Weather",
      success: "Success Reward", failure: "Failure Reward", loading: "Loading Journey data...",
      empty: "No matching results.", loadError: "Could not load Journey data.", clear: "Clear search", savior: "Savior"
    },
    ja: {
      difficulty: "難易度", all: "すべて", easy: "イージー", normal: "ノーマル", hard: "ハード",
      search: "カード名・イベント名・報酬など...", arcana: "アルカナ", events: "旅程イベント",
      reset: "リセット", raid: "討伐", aganon: "アガノン", flora: "フローラ", kalaid: "カライド", weather: "天気",
      success: "成功報酬", failure: "失敗報酬", loading: "旅程データを読み込んでいます。",
      empty: "検索結果がありません。", loadError: "旅程データを読み込めませんでした。", clear: "検索語を消去", savior: "救援者"
    }
  };
  return table[SUPPORTED_LANGUAGES.includes(language) ? language : "ko"] || table.ko;
}

function getJourneyJsonPath(language = currentLanguage, archiveVersion = SITE_BUILD_VERSION) {
  const selected = SUPPORTED_LANGUAGES.includes(language) ? language : "ko";
  const version = archiveVersion || SITE_BUILD_VERSION;
  return `./data/journey/${encodeURIComponent(selected)}/journey.json?v=${encodeURIComponent(version)}`;
}

function normalizeJourneySearch(value) {
  // Journey search ignores whitespace so queries such as "누각위유리달맞이"
  // match "누각 위, 유리달 맞이" without changing the displayed text.
  return normalizeGuideSearch(value);
}

const JOURNEY_ARCANA_FOOTER_MARKERS = [
  "이 페이지는 게임", "비영리 팬 프로젝트", "프로젝트에 사용된 모든 자산",
  "STUDIOBSIDE", "제보/문의 Discord", "hippo2003",
  "This page is", "fan project", "All assets, data, images", "Report/Inquiries Discord",
  "このページは", "非営利ファン", "使用されているすべての", "お問い合わせ Discord"
];

function isJourneyArcanaFooterText(value) {
  const text = String(value || "").trim();
  if (!text) return false;
  return JOURNEY_ARCANA_FOOTER_MARKERS.some((marker) =>
    text.toLocaleLowerCase().includes(String(marker).toLocaleLowerCase())
  );
}

function isJourneyArcanaMetadataRow(row, entry) {
  const text = String(row?.text || "").trim();
  if (!text) return false;
  const title = String(entry?.title || "").trim();
  const arcanaName = String(entry?.arcanaName || "").trim();
  const grade = String(entry?.grade || "").trim();
  if (text === title || text === arcanaName) return true;
  if (arcanaName && /^\[(?:아르카나|Arcana|アルカナ)\]/i.test(text)) {
    return text.replace(/^\[(?:아르카나|Arcana|アルカナ)\]/i, "") === arcanaName;
  }
  if (grade && text === grade) return true;
  return /^(구원자|Savior|救援者)\s*[:：]/i.test(text);
}

function getJourneyArcanaContentRows(entry) {
  let rows = Array.isArray(entry?.rows) ? entry.rows.slice() : [];
  while (rows.length && isJourneyArcanaMetadataRow(rows[0], entry)) rows.shift();
  const footerIndex = rows.findIndex((row) => isJourneyArcanaFooterText(row?.text));
  if (footerIndex >= 0) rows = rows.slice(0, footerIndex);
  return rows;
}

function getJourneyArcanaEventGroups(entry) {
  if (Array.isArray(entry?.eventGroups) && entry.eventGroups.length) {
    return entry.eventGroups
      .map((group) => ({
        title: String(group?.title || "").trim(),
        choices: Array.isArray(group?.choices) ? group.choices : [],
        rows: (Array.isArray(group?.rows) ? group.rows : [])
          .filter((row) => !isJourneyArcanaFooterText(row?.text))
      }))
      .filter((group) => group.title || group.choices.length || group.rows.length);
  }

  const rows = getJourneyArcanaContentRows(entry);
  if (!rows.length) return [];

  const markedIndexes = rows
    .map((row, index) => row?.isEventTitle ? index : -1)
    .filter((index) => index >= 0);

  let titleIndexes = markedIndexes;
  if (!titleIndexes.length) {
    const fontSizes = rows
      .filter((row) => String(row?.text || "").trim())
      .map((row) => Number(row?.fontSize) || 0)
      .filter((value) => value > 0)
      .sort((a, b) => a - b);
    const medianFont = fontSizes.length ? fontSizes[Math.floor(fontSizes.length / 2)] : 14;
    const threshold = Math.max(16.5, medianFont + 1.25);
    const excluded = /^(성공|실패|Success|Failure|成功|失敗|or)$/i;
    const statLike = /(잠재력|스태미나|컨디션|힘\s*[+-]|체력\s*[+-]|인내\s*[+-]|집중\s*[+-]|보호\s*[+-]|공격력|방어력|생명력|속도|할인|여정 버프|턴$)/i;

    titleIndexes = rows
      .map((row, index) => {
        const text = String(row?.text || "").trim();
        const hasImages = (row?.segments || []).some((segment) => segment?.type === "images");
        const fontSize = Number(row?.fontSize) || 0;
        const weight = Number(row?.weight) || 0;
        if (!text || text.length > 90 || excluded.test(text) || statLike.test(text) || hasImages) return -1;
        return fontSize >= threshold && weight >= 600 ? index : -1;
      })
      .filter((index) => index >= 0);
  }

  if (!titleIndexes.length) return [{ title: "", rows }];

  const groups = [];
  for (let i = 0; i < titleIndexes.length; i++) {
    const start = titleIndexes[i];
    const end = i + 1 < titleIndexes.length ? titleIndexes[i + 1] : rows.length;
    const title = String(rows[start]?.text || "").trim();
    groups.push({ title, rows: rows.slice(start + 1, end) });
  }
  return groups.filter((group) => group.title || group.rows.length);
}

function getJourneyEntrySearchText(entry) {
  if (entry?.kind === "arcana" || entry?.arcanaName) {
    const eventTitles = getJourneyArcanaEventGroups(entry)
      .map((group) => group.title || "")
      .filter(Boolean)
      .join(" ");
    return normalizeJourneySearch(
      `${entry?.arcanaName || ""} ${entry?.title || ""} ${entry?.savior || ""} ${eventTitles} ${entry?.searchText || ""}`
    );
  }

  const imageAlt = (entry?.rows || []).flatMap((row) => row?.segments || [])
    .filter((segment) => segment?.type === "images")
    .flatMap((segment) => segment.images || [])
    .map((image) => image.alt || "")
    .join(" ");
  return normalizeJourneySearch(`${entry?.title || ""} ${entry?.searchText || ""} ${imageAlt}`);
}

function journeyEntryMatches(entry, kind) {
  const state = journeyDatabaseState;
  if (kind === "arcana" && !state.showArcana) return false;
  if (kind === "events" && !state.showEvents) return false;

  if (state.category !== "all") {
    if (kind !== "events") return false;
    if (!Array.isArray(entry.categories) || !entry.categories.includes(state.category)) return false;
  }

  if (state.difficulty !== "all") {
    const difficulties = Array.isArray(entry.difficulties) ? entry.difficulties : [];
    // Events without an explicit difficulty apply to every difficulty, matching the source DB behavior.
    if (difficulties.length && !difficulties.includes(state.difficulty)) return false;
  }

  const query = normalizeJourneySearch(state.query);
  if (query && !getJourneyEntrySearchText(entry).includes(query)) return false;
  return true;
}

function getJourneyAssetUrl(filename) {
  if (!filename) return "";
  return `./data/journey-assets/${encodeURIComponent(filename)}`;
}

function renderJourneyImageGroup(segment) {
  const images = Array.isArray(segment?.images) ? segment.images.filter((image) => image?.asset) : [];
  if (!images.length) return "";
  const title = images.map((image) => image.alt || "").filter(Boolean).join(" / ");
  return `<span class="journey-inline-icon-stack"${title ? ` title="${escapeHtml(title)}"` : ""}>${images.map((image, index) => `
    <img src="${escapeHtml(getJourneyAssetUrl(image.asset))}" alt="${escapeHtml(image.alt || "")}" loading="lazy" style="z-index:${index + 1}">
  `).join("")}</span>`;
}

function renderJourneyRow(row, entry, rowIndex, options = {}) {
  const text = String(row?.text || "").trim();
  if (/^or$/i.test(text)) return `<div class="journey-or">or</div>`;

  const isTitle = !options.suppressTitle && (rowIndex === 0 || text === entry?.title);
  const segments = (row?.segments || []).map((segment) => {
    if (segment?.type === "images") return renderJourneyImageGroup(segment);
    if (segment?.type === "text") return `<span>${escapeHtml(segment.text || "")}</span>`;
    return "";
  }).join("");

  const difficultyLabels = new Set([
    "이지", "노말", "하드", "Easy", "Normal", "Hard", "イージー", "ノーマル", "ハード",
    "簡單", "简单", "普通", "困難", "困难"
  ]);
  const rowClass = ["journey-data-row"];
  if (isTitle) rowClass.push("is-title");
  if (difficultyLabels.has(text)) rowClass.push("is-difficulty");
  if (!segments && text) return `<div class="${rowClass.join(" ")}">${escapeHtml(text)}</div>`;
  return `<div class="${rowClass.join(" ")}">${segments || escapeHtml(text)}</div>`;
}

function renderJourneyRowGroups(rows, entry, options = {}) {
  const pieces = [];
  let index = 0;
  while (index < rows.length) {
    const row = rows[index];
    const region = row?.region || "";
    if (!region) {
      pieces.push(renderJourneyRow(row, entry, index, options));
      index += 1;
      continue;
    }
    const group = [];
    let cursor = index;
    while (cursor < rows.length && rows[cursor]?.region === region) {
      group.push({ row: rows[cursor], index: cursor });
      cursor += 1;
    }
    const tone = group.find((item) => item.row?.tone === "failure")?.row?.tone
      || group.find((item) => item.row?.tone === "success")?.row?.tone
      || group.find((item) => item.row?.tone === "highlight")?.row?.tone
      || "neutral";
    pieces.push(`<div class="journey-result-block tone-${escapeHtml(tone)}">${group.map((item) => renderJourneyRow(item.row, entry, item.index, options)).join("")}</div>`);
    index = cursor;
  }
  return pieces.join("");
}

function getJourneyArcanaPieceTone(piece, fallback = "neutral") {
  const tones = (piece?.segments || []).map((segment) => String(segment?.tone || ""));
  if (tones.includes("failure")) return "failure";
  if (tones.includes("success")) return "success";
  if (tones.includes("highlight")) return "highlight";
  const own = String(piece?.tone || "");
  return ["failure", "success", "highlight", "neutral", "plain"].includes(own)
    ? (own === "plain" ? fallback : own)
    : fallback;
}

function getJourneyArcanaTextTone(value, fallback = "neutral") {
  const text = String(value || "").trim();
  if (/^(실패|Failure|失敗)\b/i.test(text)) return "failure";
  if (/^(성공|Success|成功)\b/i.test(text)) return "success";
  return fallback;
}

function splitJourneyArcanaTextLines(value) {
  const source = String(value || "").replace(/\s+/g, " ").trim();
  if (!source) return [];

  const statPattern = /(?:잠재력\s*포인트|스태미나|컨디션|힘|체력|인내|집중|보호)\s*[+-]\s*\d+/gi;
  const stats = [];
  let main = source.replace(statPattern, (match) => {
    stats.push(match.replace(/\s*([+-])\s*/g, " $1"));
    return " ";
  }).replace(/\s+/g, " ").trim();

  const lines = [];
  const push = (value) => {
    const clean = String(value || "").replace(/\s+/g, " ").trim();
    if (clean) lines.push(clean);
  };

  const buffMarkers = ["여정 버프 획득", "Journey Buff Acquired", "旅程バフ獲得"];
  for (const marker of buffMarkers) {
    const index = main.toLocaleLowerCase().indexOf(marker.toLocaleLowerCase());
    if (index >= 0) {
      push(main.slice(0, index));
      push(marker);
      main = main.slice(index + marker.length).trim();
      break;
    }
  }

  const discountMatch = main.match(/^(.+?)\s+(\d+(?:\.\d+)?%\s*(?:할인|discount|割引).*)$/i);
  if (discountMatch) {
    push(discountMatch[1]);
    push(discountMatch[2]);
    main = "";
  }

  if (main) {
    const sentenceParts = main.split(/(?<=[.!?。！？])\s+/).map((part) => part.trim()).filter(Boolean);
    sentenceParts.forEach(push);
  }

  stats.forEach(push);
  return lines;
}

function renderJourneyArcanaLogicalText(text, iconHtml = "", tone = "neutral") {
  const lines = splitJourneyArcanaTextLines(text);
  if (!lines.length) return iconHtml ? `<div class="journey-arcana-detail-line">${iconHtml}</div>` : "";

  return lines.map((line, index) => {
    let kind = "detail";
    if (/^(여정 버프 획득|Journey Buff Acquired|旅程バフ獲得)$/i.test(line)) kind = "buff-label";
    else if (/^(잠재력\s*포인트|스태미나|컨디션|힘|체력|인내|집중|보호)\s*[+-]\s*\d+/i.test(line)) kind = "stat";
    else if (/\b\d+(?:\.\d+)?%\s*(?:할인|discount|割引)\b/i.test(line)) kind = "effect-desc";
    else if (/[.!?。！？]$/.test(line) || /증가합니다|감소합니다|획득합니다|발생합니다|턴$/.test(line)) kind = "effect-desc";
    else if (index === 0 && iconHtml) kind = "effect-title";

    const polarity = getJourneyArcanaLinePolarity(line);
    return `<div class="journey-arcana-detail-line is-${kind} tone-${escapeHtml(tone)} polarity-${escapeHtml(polarity)}">${index === 0 ? iconHtml : ""}<span>${escapeHtml(line)}</span></div>`;
  }).join("");
}

function getJourneyArcanaSegmentX(segment) {
  const value = Number(segment?.x);
  return Number.isFinite(value) ? value : null;
}

function getJourneyArcanaSegmentRegion(segment) {
  return String(segment?.region || "");
}

function groupJourneyArcanaSegmentsBySourceRegion(segments) {
  const list = Array.isArray(segments) ? segments.filter(Boolean) : [];
  if (!list.length) return [];

  const groups = [];
  const byKey = new Map();
  list.forEach((segment, index) => {
    const region = getJourneyArcanaSegmentRegion(segment);
    // Empty-region segments are kept together only when adjacent. A real source
    // box always has a region id, which is the important discriminator here.
    const key = region ? `region:${region}` : `plain:${index}`;
    let group = byKey.get(key);
    if (!group) {
      group = { region, segments: [], x: null, tone: "neutral" };
      byKey.set(key, group);
      groups.push(group);
    }
    group.segments.push(segment);
    const x = getJourneyArcanaSegmentX(segment);
    if (x != null) group.x = group.x == null ? x : Math.min(group.x, x);
    const segTone = getJourneyArcanaPieceTone({ segments: [segment], tone: segment?.tone }, "neutral");
    if (segTone === "failure") group.tone = "failure";
    else if (segTone === "success" && group.tone !== "failure") group.tone = "success";
    else if (segTone === "highlight" && !["failure", "success"].includes(group.tone)) group.tone = "highlight";
  });

  return groups.sort((a, b) => {
    if (a.x == null && b.x == null) return 0;
    if (a.x == null) return 1;
    if (b.x == null) return -1;
    return a.x - b.x;
  });
}

function inferJourneyArcanaPairedSegments(segments) {
  const groups = groupJourneyArcanaSegmentsBySourceRegion(segments);
  if (groups.length < 2) return null;

  // Only treat a row as two source columns when two distinct bordered/background
  // regions were actually captured and their horizontal positions are clearly
  // separated. This prevents single automatic-choice events from being split
  // merely because the row happened to contain two text segments.
  const regionGroups = groups.filter((group) => group.region && group.x != null);
  if (regionGroups.length < 2) return null;

  const left = regionGroups[0];
  const right = regionGroups[regionGroups.length - 1];
  if (Math.abs(right.x - left.x) < 72) return null;

  return [left, right];
}

function getJourneyArcanaRowPieces(row) {
  const segments = Array.isArray(row?.segments) ? row.segments.filter(Boolean) : [];
  const rowTone = getJourneyArcanaTextTone(row?.text, getJourneyArcanaPieceTone(row, "neutral"));
  const rowRegion = String(row?.region || "");
  if (!segments.length) {
    const text = String(row?.text || "").trim();
    return text ? [{ region: rowRegion, tone: rowTone, lane: "", x: null, segments: [{ type: "text", text }] }] : [];
  }

  const paired = inferJourneyArcanaPairedSegments(segments);
  if (paired) {
    return paired.map((group, index) => ({
      region: group.region,
      tone: group.tone || rowTone,
      lane: index === 0 ? "left" : "right",
      x: group.x,
      segments: group.segments
    }));
  }

  const groups = groupJourneyArcanaSegmentsBySourceRegion(segments);
  if (groups.length === 1) {
    const group = groups[0];
    return [{
      region: group.region || rowRegion,
      tone: group.tone !== "neutral" ? group.tone : rowTone,
      lane: "",
      x: group.x,
      segments: group.segments
    }];
  }

  // Multiple source regions on the same visual row that are not far enough
  // apart to be separate columns remain one logical row, preserving each
  // segment's original region/tone for icon-to-text pairing.
  return [{ region: rowRegion, tone: rowTone, lane: "", x: groups[0]?.x ?? null, segments }];
}

function getJourneyArcanaLinePolarity(line) {
  const text = String(line || "").replace(/\s+/g, " ").trim();
  if (!text) return "neutral";

  if (/^(?:잠재력\s*포인트|스태미나|컨디션|힘|체력|인내|집중|보호)\s*\+\s*\d+/i.test(text)) return "positive";
  if (/^(?:잠재력\s*포인트|스태미나|컨디션|힘|체력|인내|집중|보호)\s*-\s*\d+/i.test(text)) return "negative";
  if (/^(여정 버프 획득|Journey Buff Acquired|旅程バフ獲得)$/i.test(text)) return "positive";
  if (/(여정\s*디버프|Journey\s*Debuff|旅程デバフ)/i.test(text)) return "negative";
  if (/\b\d+(?:\.\d+)?%\s*(?:할인|discount|割引)\b/i.test(text)) return "positive";
  if (/(증가합니다|상승합니다|획득합니다|회복합니다)/i.test(text)) return "positive";
  if (/(실패율|받는\s*피해|피해량).*감소합니다/i.test(text)) return "positive";
  if (/감소합니다/i.test(text)) return "negative";
  return "neutral";
}

function renderJourneyArcanaPieceLine(piece) {
  const segments = Array.isArray(piece?.segments) ? piece.segments.filter(Boolean) : [];
  if (!segments.length) return "";
  const tone = getJourneyArcanaPieceTone(piece, "neutral");
  const output = [];
  let pendingIcon = "";
  for (const segment of segments) {
    if (segment?.type === "images") {
      const icon = renderJourneyImageGroup(segment);
      if (pendingIcon) output.push(`<div class="journey-arcana-detail-line">${pendingIcon}</div>`);
      pendingIcon = icon;
      continue;
    }
    if (segment?.type === "text") {
      const rendered = renderJourneyArcanaLogicalText(segment.text || "", pendingIcon, tone);
      if (rendered) output.push(rendered);
      pendingIcon = "";
    }
  }
  if (pendingIcon) output.push(`<div class="journey-arcana-detail-line">${pendingIcon}</div>`);
  return output.join("");
}

function renderJourneyArcanaPieceSequence(pieces, forcedTone = "") {
  const output = [];
  let bucketTone = "";
  let bucketRegion = "";
  let bucket = [];
  const flush = () => {
    if (!bucket.length) return;
    const tone = forcedTone || bucketTone || "neutral";
    if (tone === "success" || tone === "failure" || tone === "highlight") {
      output.push(`<div class="journey-result-block journey-arcana-result-block tone-${escapeHtml(tone)}">${bucket.map(renderJourneyArcanaPieceLine).join("")}</div>`);
    } else {
      output.push(bucket.map(renderJourneyArcanaPieceLine).join(""));
    }
    bucket = [];
    bucketTone = "";
    bucketRegion = "";
  };

  for (const piece of pieces || []) {
    const tone = forcedTone || getJourneyArcanaPieceTone(piece, "neutral");
    const region = String(piece?.region || "");
    if (!bucketTone) bucketTone = tone;
    if (!bucketRegion) bucketRegion = region;
    if (bucket.length && (tone !== bucketTone || (region && bucketRegion && region !== bucketRegion))) flush();
    bucketTone = tone;
    bucketRegion = region;
    bucket.push(piece);
  }
  flush();
  return output.join("");
}

function renderJourneyArcanaStructuredIcon(reward) {
  const assets = Array.isArray(reward?.iconAssets)
    ? reward.iconAssets.filter(Boolean)
    : (reward?.iconAsset ? [reward.iconAsset] : []);
  if (!assets.length) return "";
  const label = String(reward?.label || "").trim();
  return `<span class="journey-arcana-reward-icon"${label ? ` title="${escapeHtml(label)}"` : ""}>${assets.map((asset, index) => `
    <img src="${escapeHtml(getJourneyAssetUrl(asset))}" alt="" loading="lazy" style="z-index:${index + 1}">
  `).join("")}</span>`;
}

function renderJourneyArcanaStructuredReward(reward) {
  const label = String(reward?.label || "").trim();
  const value = String(reward?.value || "").trim();
  const description = String(reward?.description || "").trim();
  const polarity = ["positive", "negative", "neutral"].includes(reward?.polarity)
    ? reward.polarity
    : "neutral";
  const effectTone = ["positive", "negative", "special", "neutral"].includes(reward?.effectTone)
    ? reward.effectTone
    : "neutral";
  const sourceType = String(reward?.sourceType || "").trim();
  const rewardTypeClass = /^RT_[A-Z_]+$/.test(sourceType)
    ? ` reward-type-${sourceType.toLowerCase().replaceAll("_", "-")}`
    : "";
  const icon = renderJourneyArcanaStructuredIcon(reward);

  return `
    <div class="journey-arcana-reward-alternative polarity-${escapeHtml(polarity)} effect-${escapeHtml(effectTone)}${rewardTypeClass}">
      <div class="journey-arcana-reward-main">
        ${icon}
        ${label ? `<span class="journey-arcana-reward-label">${escapeHtml(label)}</span>` : ""}
        ${value ? `<span class="journey-arcana-reward-value">${escapeHtml(value)}</span>` : ""}
      </div>
      ${description ? `<div class="journey-arcana-reward-description">${escapeHtml(description)}</div>` : ""}
    </div>
  `;
}

function renderJourneyArcanaStructuredRewardGroup(rewardGroup) {
  const rewards = Array.isArray(rewardGroup) ? rewardGroup.filter(Boolean) : [];
  if (!rewards.length) return "";
  return `<div class="journey-arcana-reward-group">${rewards.map((reward, index) => `
    ${index ? `<span class="journey-arcana-reward-or">or</span>` : ""}
    ${renderJourneyArcanaStructuredReward(reward)}
  `).join("")}</div>`;
}

function renderJourneyArcanaStructuredOutcome(rewardGroups, tone, showTitle) {
  const groups = Array.isArray(rewardGroups) ? rewardGroups.filter((group) => Array.isArray(group) && group.length) : [];
  if (!groups.length) return "";
  const labels = getJourneyLabels();
  const title = tone === "failure" ? labels.failure : labels.success;
  return `
    <div class="journey-result-block journey-arcana-result-block journey-arcana-structured-outcome tone-${escapeHtml(tone)}">
      ${showTitle ? `<div class="journey-arcana-outcome-title">${escapeHtml(title)}</div>` : ""}
      <div class="journey-arcana-reward-list">${groups.map(renderJourneyArcanaStructuredRewardGroup).join("")}</div>
    </div>
  `;
}

function renderJourneyArcanaStructuredEventBody(group) {
  const choices = Array.isArray(group?.choices) ? group.choices.filter(Boolean) : [];
  if (!choices.length) return "";
  const isBranch = choices.length > 1 || choices.some((choice) => String(choice?.name || "").trim());

  return `<div class="journey-arcana-structured-choices${isBranch ? " is-branch" : " is-automatic"}">${choices.map((choice, index) => {
    const name = String(choice?.name || "").trim();
    const recommended = typeof choice?.recommended === "boolean" ? choice.recommended : index === 0;
    const choiceTone = recommended ? "success" : "failure";
    const successRewards = Array.isArray(choice?.successRewards) ? choice.successRewards : [];
    const failureRewards = Array.isArray(choice?.failureRewards) ? choice.failureRewards : [];
    const showOutcomeTitle = failureRewards.length > 0;
    const outcomes = [
      renderJourneyArcanaStructuredOutcome(successRewards, "success", showOutcomeTitle),
      renderJourneyArcanaStructuredOutcome(failureRewards, "failure", true)
    ].join("");

    if (!isBranch && !name) {
      return `<div class="journey-arcana-automatic-choice">${outcomes}</div>`;
    }

    return `
      <div class="journey-arcana-choice-stack tone-${escapeHtml(choiceTone)}">
        ${name ? `<div class="journey-arcana-choice-title"><span>${index + 1}</span>${escapeHtml(name)}</div>` : ""}
        ${outcomes}
      </div>
    `;
  }).join("")}</div>`;
}

function renderJourneyArcanaEventBody(group) {
  if (Array.isArray(group?.choices) && group.choices.length) {
    return renderJourneyArcanaStructuredEventBody(group);
  }

  const rows = Array.isArray(group?.rows) ? group.rows : [];
  const rowsWithPieces = rows
    .map((row, rowIndex) => ({ row, rowIndex, pieces: getJourneyArcanaRowPieces(row) }))
    .filter((item) => item.pieces.length);

  const firstPairIndex = rowsWithPieces.findIndex((item) =>
    item.pieces.some((piece) => piece?.lane === "left") &&
    item.pieces.some((piece) => piece?.lane === "right")
  );

  if (firstPairIndex >= 0) {
    const firstPair = rowsWithPieces[firstPairIndex];
    const leftAnchor = firstPair.pieces.find((piece) => piece?.lane === "left")?.x;
    const rightAnchor = firstPair.pieces.find((piece) => piece?.lane === "right")?.x;
    const canUseAnchors = Number.isFinite(leftAnchor) && Number.isFinite(rightAnchor) && rightAnchor > leftAnchor;
    const mid = canUseAnchors ? (leftAnchor + rightAnchor) / 2 : null;

    const before = [];
    const left = [];
    const right = [];
    const after = [];
    let pairStarted = false;

    const assignByX = (piece) => {
      const x = Number(piece?.x);
      if (!canUseAnchors || !Number.isFinite(x)) return "";
      return x < mid ? "left" : "right";
    };

    for (let itemIndex = 0; itemIndex < rowsWithPieces.length; itemIndex++) {
      const item = rowsWithPieces[itemIndex];
      const hasLeft = item.pieces.some((piece) => piece?.lane === "left");
      const hasRight = item.pieces.some((piece) => piece?.lane === "right");

      if (hasLeft || hasRight) {
        pairStarted = true;
        item.pieces.forEach((piece) => {
          if (piece.lane === "left") left.push(piece);
          else if (piece.lane === "right") right.push(piece);
          else {
            const lane = assignByX(piece);
            (lane === "right" ? right : left).push(piece);
          }
        });
        continue;
      }

      if (!pairStarted) {
        before.push(...item.pieces);
        continue;
      }

      let assigned = false;
      for (const piece of item.pieces) {
        const lane = assignByX(piece);
        if (lane === "left") {
          left.push(piece);
          assigned = true;
        } else if (lane === "right") {
          right.push(piece);
          assigned = true;
        }
      }

      // Full-width source rows after a paired choice are shared text, not a
      // branch result. Keep them outside the two choice stacks.
      if (!assigned) after.push(...item.pieces);
    }

    return [
      renderJourneyArcanaPieceSequence(before),
      `<div class="journey-arcana-stacked-choices">
        ${left.length ? `<div class="journey-arcana-choice-stack">${renderJourneyArcanaPieceSequence(left)}</div>` : ""}
        ${right.length ? `<div class="journey-arcana-choice-stack">${renderJourneyArcanaPieceSequence(right)}</div>` : ""}
      </div>`,
      renderJourneyArcanaPieceSequence(after)
    ].join("");
  }

  // No actual source two-column regions: keep the event as one selection.
  // Success/failure blocks are still separated by their captured source tone.
  return renderJourneyArcanaPieceSequence(rowsWithPieces.flatMap((item) => item.pieces));
}

function renderJourneyArcanaEntry(entry) {
  const labels = getJourneyLabels();
  const groups = getJourneyArcanaEventGroups(entry);
  const sourceTitle = String(entry?.title || "").trim();
  const arcanaName = String(entry?.arcanaName || "").trim();
  const title = arcanaName
    ? `[${labels.arcana}]${arcanaName}`
    : sourceTitle.replace(/^\[(?:아르카나|Arcana|アルカナ)\]/i, `[${labels.arcana}]`);
  const grade = String(entry?.grade || "").trim();
  const savior = String(entry?.savior || "").trim();

  const groupMarkup = groups.map((group, groupIndex) => {
    const body = renderJourneyArcanaEventBody(group);
    const heading = group.title
      ? `<div class="journey-arcana-event-title">${groupIndex + 1}. ${escapeHtml(group.title)}</div>`
      : "";
    return `
      <section class="journey-arcana-event-group">
        ${heading}
        ${body}
      </section>
    `;
  }).join("");

  return `
    <article class="journey-entry-card journey-arcana-card" data-journey-kind="arcana">
      <div class="journey-data-row is-title">${escapeHtml(title)}</div>
      ${grade ? `<div class="journey-data-row" style="font-weight:850;">${escapeHtml(grade)}</div>` : ""}
      ${savior ? `<div class="journey-data-row" style="font-weight:850;">${escapeHtml(labels.savior || "구원자")} : ${escapeHtml(savior)}</div>` : ""}
      ${groupMarkup || renderJourneyRowGroups(getJourneyArcanaContentRows(entry), entry, { suppressTitle: true })}
    </article>
  `;
}

function renderJourneyEntry(entry) {
  if (entry?.kind === "arcana" || entry?.arcanaName) return renderJourneyArcanaEntry(entry);
  const rows = Array.isArray(entry?.rows) ? entry.rows : [];
  return `<article class="journey-entry-card" data-journey-kind="${escapeHtml(entry?.kind || "")}">${renderJourneyRowGroups(rows, entry)}</article>`;
}

function renderJourneyDatabaseResults() {
  const results = document.querySelector("#journey-results");
  if (!results) return;
  const labels = getJourneyLabels();
  const data = journeyDatabaseState.data;
  if (!data) {
    results.innerHTML = `<div class="journey-status">${escapeHtml(labels.loading)}</div>`;
    return;
  }

  const arcana = (data.arcana || []).filter((entry) => journeyEntryMatches(entry, "arcana"));
  const events = (data.events || []).filter((entry) => journeyEntryMatches(entry, "events"));
  const entries = [...arcana, ...events];
  if (!entries.length) {
    results.innerHTML = `<div class="journey-status">${escapeHtml(labels.empty)}</div>`;
    return;
  }
  results.innerHTML = entries.map(renderJourneyEntry).join("");
}

function updateJourneyControlState() {
  const labels = getJourneyLabels();
  document.querySelectorAll("[data-journey-category]").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.journeyCategory === journeyDatabaseState.category);
  });
  document.querySelectorAll("[data-journey-difficulty]").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.journeyDifficulty === journeyDatabaseState.difficulty);
  });
  const summary = document.querySelector("#journey-difficulty-summary");
  if (summary) summary.textContent = labels.difficulty;
  const search = document.querySelector("#journey-search");
  const clear = document.querySelector("#journey-search-clear");
  if (search && search.value !== journeyDatabaseState.query) search.value = journeyDatabaseState.query;
  if (clear) clear.hidden = !journeyDatabaseState.query;
}

async function loadJourneyDatabase() {
  const results = document.querySelector("#journey-results");
  if (!results) return;
  const labels = getJourneyLabels();
  const token = ++journeyDatabaseState.requestToken;
  journeyDatabaseState.data = null;
  results.innerHTML = `<div class="journey-status">${escapeHtml(labels.loading)}</div>`;

  let archiveVersion = SITE_BUILD_VERSION;
  try {
    const metaResponse = await fetch(`./data/journey/backup-meta.json?site=${encodeURIComponent(SITE_BUILD_VERSION)}&t=${Date.now()}`, { cache: "no-store" });
    if (metaResponse.ok) {
      const meta = await metaResponse.json();
      journeyDatabaseState.meta = meta;
      if (meta?.capturedAt) archiveVersion = `${SITE_BUILD_VERSION}-${meta.capturedAt}`;
    }
  } catch (_) {}

  try {
    const response = await fetch(getJourneyJsonPath(currentLanguage, archiveVersion), { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    if (token !== journeyDatabaseState.requestToken) return;
    journeyDatabaseState.data = data;
    renderJourneyDatabaseResults();
  } catch (error) {
    if (token !== journeyDatabaseState.requestToken) return;
    results.innerHTML = `<div class="journey-status error">${escapeHtml(labels.loadError)}<small>${escapeHtml(error?.message || "")}</small></div>`;
  }
}

function bindJourneyDatabaseControls() {
  const search = document.querySelector("#journey-search");
  const clear = document.querySelector("#journey-search-clear");
  const arcana = document.querySelector("#journey-type-arcana");
  const events = document.querySelector("#journey-type-events");
  const difficulty = document.querySelector("#journey-difficulty");

  search?.addEventListener("input", (event) => {
    journeyDatabaseState.query = event.currentTarget.value || "";
    updateJourneyControlState();
    renderJourneyDatabaseResults();
  });
  clear?.addEventListener("click", () => {
    journeyDatabaseState.query = "";
    if (search) { search.value = ""; search.focus(); }
    updateJourneyControlState();
    renderJourneyDatabaseResults();
  });
  arcana?.addEventListener("change", (event) => {
    journeyDatabaseState.showArcana = event.currentTarget.checked;
    renderJourneyDatabaseResults();
  });
  events?.addEventListener("change", (event) => {
    journeyDatabaseState.showEvents = event.currentTarget.checked;
    renderJourneyDatabaseResults();
  });
  document.querySelectorAll("[data-journey-category]").forEach((button) => button.addEventListener("click", () => {
    journeyDatabaseState.category = JOURNEY_CATEGORY_KEYS.includes(button.dataset.journeyCategory) ? button.dataset.journeyCategory : "all";
    updateJourneyControlState();
    renderJourneyDatabaseResults();
  }));
  document.querySelectorAll("[data-journey-difficulty]").forEach((button) => button.addEventListener("click", () => {
    journeyDatabaseState.difficulty = JOURNEY_DIFFICULTY_KEYS.includes(button.dataset.journeyDifficulty) ? button.dataset.journeyDifficulty : "all";
    if (difficulty) difficulty.open = false;
    updateJourneyControlState();
    renderJourneyDatabaseResults();
  }));
  document.addEventListener("click", (event) => {
    if (difficulty?.open && !difficulty.contains(event.target)) difficulty.open = false;
  }, { once: true });
}

function createJourneyDatabaseMarkup() {
  const labels = getJourneyLabels();
  return `
    <div class="journey-page">
      <header class="journey-hero">
        <p class="eyebrow">JOURNEY DATABASE</p>
        <h1 data-i18n-source="여정">${escapeHtml(translateString("여정"))}</h1>
      </header>
      <section class="journey-database-panel" aria-label="${escapeHtml(translateString("여정"))}">
        <div class="journey-controls">
          <div class="journey-top-row">
            <details class="journey-difficulty" id="journey-difficulty">
              <summary id="journey-difficulty-summary">${escapeHtml(labels.difficulty)}</summary>
              <div class="journey-difficulty-menu">
                ${JOURNEY_DIFFICULTY_KEYS.map((key) => `<button type="button" data-journey-difficulty="${key}" class="${key === "all" ? "is-active" : ""}">${escapeHtml(labels[key])}</button>`).join("")}
              </div>
            </details>
            <label class="journey-search-wrap">
              <input id="journey-search" class="journey-search" type="search" autocomplete="off" placeholder="${escapeHtml(labels.search)}">
              <button id="journey-search-clear" class="journey-search-clear" type="button" aria-label="${escapeHtml(labels.clear)}" hidden>×</button>
            </label>
          </div>
          <div class="journey-type-row">
            <label><input id="journey-type-arcana" type="checkbox" checked> <span>${escapeHtml(labels.arcana)}</span></label>
            <label><input id="journey-type-events" type="checkbox" checked> <span>${escapeHtml(labels.events)}</span></label>
          </div>
          <div class="journey-category-row">
            ${JOURNEY_CATEGORY_KEYS.map((key) => `<button type="button" data-journey-category="${key}" class="journey-category-button${key === "all" ? " is-active" : ""}">${escapeHtml(labels[key])}</button>`).join("")}
          </div>
          <div class="journey-legend">
            <span><i class="success"></i>${escapeHtml(labels.success)}</span>
            <span><i class="failure"></i>${escapeHtml(labels.failure)}</span>
          </div>
        </div>
        <div class="journey-results" id="journey-results">
          <div class="journey-status">${escapeHtml(labels.loading)}</div>
        </div>
      </section>
    </div>
  `;
}

function initializeJourneyDatabase() {
  journeyDatabaseState = {
    requestToken: journeyDatabaseState.requestToken + 1,
    data: null,
    meta: null,
    query: "",
    category: "all",
    difficulty: "all",
    showArcana: true,
    showEvents: true
  };
  bindJourneyDatabaseControls();
  updateJourneyControlState();
  loadJourneyDatabase();
}

function updateJourneyArchiveLanguage() {
  if (!document.querySelector("#journey-results")) return;
  const currentQuery = journeyDatabaseState.query;
  const currentCategory = journeyDatabaseState.category;
  const currentDifficulty = journeyDatabaseState.difficulty;
  const showArcana = journeyDatabaseState.showArcana;
  const showEvents = journeyDatabaseState.showEvents;
  const replacement = createJourneyDatabaseMarkup();
  const page = document.querySelector(".journey-page");
  if (page) {
    const temp = document.createElement("div");
    temp.innerHTML = replacement;
    page.replaceWith(temp.firstElementChild);
  }
  journeyDatabaseState.query = currentQuery;
  journeyDatabaseState.category = currentCategory;
  journeyDatabaseState.difficulty = currentDifficulty;
  journeyDatabaseState.showArcana = showArcana;
  journeyDatabaseState.showEvents = showEvents;
  const arcana = document.querySelector("#journey-type-arcana");
  const events = document.querySelector("#journey-type-events");
  if (arcana) arcana.checked = showArcana;
  if (events) events.checked = showEvents;
  bindJourneyDatabaseControls();
  updateJourneyControlState();
  loadJourneyDatabase();
}

const ARCANA_ARCHIVE_URL = "./data/arcanas/arcanas.json";
I18N_DATA.arcana.en["가혹한 시련"] = "Maid for Hardship";
I18N_DATA.arcana.ja["가혹한 시련"] = "過酷な試練";
const ARCANA_LEVELS = [35, 40, 45, 50];
const ARCANA_MAIN_STAT_ORDER = ["힘", "체력", "인내", "집중", "보호"];
const ARCANA_DUMMY_MAIN_STATS = new Set(["구원자"]);
const ARCANA_RARITY_ORDER = { SSR: 0, SR: 1, R: 2 };
// ESPR 한국어 아르카나 목록의 실제 표시 순서 (2026-10-29 확인).
// ID 크기나 이름으로 출시 순서를 추정하지 않는다.
const ARCANA_RELEASE_ORDER = new Map([
  7105901, 7101401, 7106001, 7104001, 7103901, 7105801, 7101701, 7104601, 7104501, 7100301, 7103302,
  7100501, 7105601, 7105501, 7102501, 7102901, 7101602, 7300301,
  7300201, 7300101, 7102601, 7105701, 7103201, 7100901, 7100801,
  7105401, 7103101, 7104301, 7104401, 7101001, 7150101, 7102101,
  7103301, 7105301, 7104101, 7102301, 7102401, 7150801, 7040101,
  7104201, 7105101, 7150701, 7101101, 7104901, 7101301, 7105201,
  7101601, 7150201, 6103401, 6100701, 6100301, 6101401, 6100201,
  6101501, 6100601, 6102601, 6102701, 6103001, 6150601, 6102201,
  6101801, 6101901, 6100101, 5999911, 5999920, 5999907, 5999916,
  5999903, 5999912, 5999918, 5999910, 5999909, 5999917, 5999908,
  5999915, 5999901, 5999902, 5999913, 5999904, 5999914, 5999919,
  5999905, 5999906
].map((id, index) => [id, index]));
let arcanaArchivePromise = null;
let arcanaSearchIndex = new Map();
const arcanaDatabaseState = {
  data: null,
  query: "",
  rarity: "all",
  mainStat: "all",
  level: 50,
  selectedId: null,
  requestToken: 0
};

const ARCANA_UI_TEXT = {
  ko: {
    title: "아르카나",
    descriptionPrefix: "아르카나 정보는 ",
    descriptionOrg: "에크하르트 초월지식 학회(ESPR)",
    descriptionSuffix: "를 참고합니다.",
    overviewTitle: "아르카나 개요",
    overview1: "아르카나는 구원자의 성능을 보조하는 공용 장비이자, 일부 구원자에게는 전용 장비와 같은 역할을 합니다.",
    overview2: "각 아르카나에는 해당 구원자와 관련된 고유 스토리가 존재합니다.",
    overview3: "여정에서는 한 번에 총 5개의 아르카나를 장착할 수 있습니다.",
    overview4: "아르카나마다 획득할 수 있는 능력과 효과가 서로 다릅니다.",
    registered: "등록된 아르카나",
    searchLabel: "아르카나 검색",
    searchPlaceholder: "아르카나 명, 캐릭터 명, 능력치 검색",
    rarity: "등급",
    mainStat: "주 능력치",
    all: "전체",
    reset: "필터 초기화",
    resultUnit: "장의 아르카나",
    emptyTitle: "조건에 맞는 아르카나가 없습니다.",
    emptyDescription: "검색어나 필터를 변경해 주세요.",
    loading: "아르카나 로컬 데이터를 불러오는 중입니다.",
    loadError: "아르카나 로컬 데이터를 불러오지 못했습니다.",
    character: "캐릭터",
    assist: "보조 분류",
    level: "표시 레벨",
    specialPotential: "특수 잠재력",
    potentialLevels: "잠재력 레벨 정보",
    requiredPoints: "필요 잠재력 포인트",
    bondRequired: "인연 조건",
    uniqueEffect: "고유 효과",
    unlockLevel: "해금 레벨",
    effects: "레벨별 효과",
    journeyStart: "여정 시작 효과",
    training: "훈련 효과",
    telepathy: "감응 훈련 효과",
    supportQuest: "지원 퀘스트 효과",
    events: "아르카나 이벤트",
    eventCount: "개 이벤트",
    choice: "선택지",
    automatic: "자동 선택",
    success: "성공",
    failure: "실패",
    potentialPoints: "잠재력 포인트",
    stamina: "스태미나",
    condition: "컨디션",
    turns: "턴",
    noEvents: "등록된 아르카나 이벤트가 없습니다.",
    noEffects: "등록된 레벨 효과가 없습니다.",
    localArchive: "LOCAL ARCHIVE"
  },
  en: {
    title: "Arcana",
    descriptionPrefix: "Arcana information references ",
    descriptionOrg: "Eckhart's Society for Preternatural Research (ESPR)",
    descriptionSuffix: ".",
    overviewTitle: "Arcana Overview",
    overview1: "Arcana function as shared equipment that supports a Savior's performance, and some serve a role similar to exclusive equipment for specific Saviors.",
    overview2: "Each Arcana has its own story related to the corresponding Savior.",
    overview3: "During a Journey, you can equip up to five Arcana at once.",
    overview4: "Each Arcana provides different abilities and effects.",
    registered: "Registered Arcana",
    searchLabel: "Search Arcana",
    searchPlaceholder: "Search Arcana, character, or stat",
    rarity: "Rarity",
    mainStat: "Main Stat",
    all: "All",
    reset: "Reset filters",
    resultUnit: " Arcana",
    emptyTitle: "No Arcana match the current filters.",
    emptyDescription: "Try changing the search term or filters.",
    loading: "Loading the local Arcana archive.",
    loadError: "Could not load the local Arcana archive.",
    character: "Character",
    assist: "Assist Types",
    level: "Display Level",
    specialPotential: "Special Potential",
    potentialLevels: "Potential Level Information",
    requiredPoints: "Required Potential Points",
    bondRequired: "Bond requirement",
    uniqueEffect: "Unique Effect",
    unlockLevel: "Unlock Level",
    effects: "Effects by Level",
    journeyStart: "Journey Start Effects",
    training: "Training Effects",
    telepathy: "Sensory Training Effects",
    supportQuest: "Support Quest Effects",
    events: "Arcana Events",
    eventCount: " Events",
    choice: "Choice",
    automatic: "Automatic",
    success: "Success",
    failure: "Failure",
    potentialPoints: "Potential Points",
    stamina: "Stamina",
    condition: "Condition",
    turns: " turns",
    noEvents: "No Arcana events are registered.",
    noEffects: "No level effects are registered.",
    localArchive: "LOCAL ARCHIVE"
  },
  ja: {
    title: "アルカナ",
    descriptionPrefix: "アルカナ情報は、",
    descriptionOrg: "エクハルト超越知識学会（ESPR）",
    descriptionSuffix: "を参考にしています。",
    overviewTitle: "アルカナ概要",
    overview1: "アルカナは救援者の性能を補助する共用装備であり、一部の救援者にとっては専用装備のような役割も果たします。",
    overview2: "各アルカナには、対応する救援者に関連した固有のストーリーがあります。",
    overview3: "旅程では、一度に合計5枚のアルカナを装着できます。",
    overview4: "アルカナごとに獲得できる能力や効果が異なります。",
    registered: "登録済みアルカナ",
    searchLabel: "アルカナ検索",
    searchPlaceholder: "アルカナ名・キャラクター名・能力値で検索",
    rarity: "レアリティ",
    mainStat: "メイン能力値",
    all: "すべて",
    reset: "フィルターをリセット",
    resultUnit: "枚のアルカナ",
    emptyTitle: "条件に一致するアルカナはありません。",
    emptyDescription: "検索語やフィルターを変更してください。",
    loading: "アルカナのローカルデータを読み込んでいます。",
    loadError: "アルカナのローカルデータを読み込めませんでした。",
    character: "キャラクター",
    assist: "補助分類",
    level: "表示レベル",
    specialPotential: "特殊潜在力",
    potentialLevels: "潜在力レベル情報",
    requiredPoints: "必要潜在力ポイント",
    bondRequired: "絆条件",
    uniqueEffect: "固有効果",
    unlockLevel: "解放レベル",
    effects: "レベル別効果",
    journeyStart: "旅程開始効果",
    training: "トレーニング効果",
    telepathy: "感応トレーニング効果",
    supportQuest: "支援クエスト効果",
    events: "アルカナイベント",
    eventCount: "件のイベント",
    choice: "選択肢",
    automatic: "自動選択",
    success: "成功",
    failure: "失敗",
    potentialPoints: "潜在力ポイント",
    stamina: "スタミナ",
    condition: "コンディション",
    turns: "ターン",
    noEvents: "登録されたアルカナイベントはありません。",
    noEffects: "登録されたレベル効果はありません。",
    localArchive: "LOCAL ARCHIVE"
  }
};

function arcanaUi(key) {
  return ARCANA_UI_TEXT[currentLanguage]?.[key] || ARCANA_UI_TEXT.ko[key] || key;
}

function getArcanaArchiveText(value, language = currentLanguage) {
  if (value == null) return "";
  if (typeof value === "string") return value;
  return value[language] ?? value.ko ?? "";
}

function isPublishedArcana(arcana) {
  return !ARCANA_DUMMY_MAIN_STATS.has(getArcanaArchiveText(arcana?.mainStat, "ko"));
}

function getPublishedArcanas(archive = arcanaDatabaseState.data) {
  return (archive?.arcanas || []).filter(isPublishedArcana);
}

function renderArcanaRichText(value) {
  return renderSaviorSourceRichText(value || "");
}

async function loadArcanaArchive() {
  if (!arcanaArchivePromise) {
    const url = `${ARCANA_ARCHIVE_URL}?v=${encodeURIComponent(SITE_BUILD_VERSION)}`;
    arcanaArchivePromise = fetch(url, { cache: "no-store" }).then(async (response) => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const archive = await response.json();
      if (!Array.isArray(archive?.arcanas) || archive.arcanas.length < 79) {
        throw new Error("Invalid Arcana archive");
      }
      if (JSON.stringify(archive.languages) !== JSON.stringify(["ko", "en", "ja"])) {
        throw new Error("Invalid Arcana archive languages");
      }
      if (!archive.localOnly || !Array.isArray(archive.potentials) || !Array.isArray(archive.journeyBuffs)) {
        throw new Error("Incomplete Arcana archive");
      }
      hydrateArcanaRecommendationLibrary(archive);
      arcanaSearchIndex = new Map(getPublishedArcanas(archive).map((arcana) => [
        Number(arcana.id),
        normalizeGuideSearch(getArcanaSearchText(arcana, archive))
      ]));
      return archive;
    }).catch((error) => {
      arcanaArchivePromise = null;
      throw error;
    });
  }
  return arcanaArchivePromise;
}

function createArcanaDatabaseMarkup() {
  return `
    <section class="arcana-db-page" data-arcana-view="list">
      <header class="arcana-db-heading">
        <div>
          <p class="eyebrow">ARCANA DATABASE</p>
          <h1>${escapeHtml(arcanaUi("title"))}</h1>
          <p>${escapeHtml(arcanaUi("descriptionPrefix"))}<a href="https://ss.espr.gg/" target="_blank" rel="noopener noreferrer" style="color:inherit;text-decoration:underline;text-underline-offset:3px;">${escapeHtml(arcanaUi("descriptionOrg"))}</a>${escapeHtml(arcanaUi("descriptionSuffix"))}</p>
        </div>
      </header>

      <section class="equipment-panel arcana-overview-panel" id="arcana-overview">
        <div class="equipment-panel-inner overview-mascot-layout">
          <img class="overview-mascot" src="./images/guide-mascot.webp?v=20260915t1" alt="" aria-hidden="true">
          <h2 class="equipment-section-title">${escapeHtml(arcanaUi("overviewTitle"))}</h2>
          <ul class="equipment-overview-list">
            <li>${escapeHtml(arcanaUi("overview1"))}</li>
            <li>${escapeHtml(arcanaUi("overview2"))}</li>
            <li>${escapeHtml(arcanaUi("overview3"))}</li>
            <li>${escapeHtml(arcanaUi("overview4"))}</li>
          </ul>
        </div>
      </section>

      <section class="arcana-db-controls" aria-label="${escapeHtml(arcanaUi("searchLabel"))}">
        <label class="arcana-search-field">
          <span aria-hidden="true">⌕</span>
          <span class="sr-only">${escapeHtml(arcanaUi("searchLabel"))}</span>
          <input id="arcana-search-input" type="search"
            value="${escapeHtml(arcanaDatabaseState.query)}"
            placeholder="${escapeHtml(arcanaUi("searchPlaceholder"))}" autocomplete="off">
        </label>
        <div class="arcana-filter-row">
          <strong>${escapeHtml(arcanaUi("rarity"))}</strong>
          <div class="arcana-filter-chips" id="arcana-rarity-filters">
            ${["all", "SSR", "SR", "R"].map((rarity) => `
              <button type="button" class="arcana-filter-chip${arcanaDatabaseState.rarity === rarity ? " is-active" : ""}"
                data-arcana-rarity="${rarity}">${escapeHtml(rarity === "all" ? arcanaUi("all") : rarity)}</button>
            `).join("")}
          </div>
        </div>
        <div class="arcana-filter-row">
          <strong>${escapeHtml(arcanaUi("mainStat"))}</strong>
          <div class="arcana-filter-chips" id="arcana-main-stat-filters">
            <button type="button" class="arcana-filter-chip is-active" data-arcana-main-stat="all">${escapeHtml(arcanaUi("all"))}</button>
          </div>
        </div>
      </section>

      <div class="arcana-result-line">
        <span><strong id="arcana-visible-count">0</strong>${escapeHtml(arcanaUi("resultUnit"))}</span>
        <button type="button" id="arcana-reset-filters">${escapeHtml(arcanaUi("reset"))}</button>
      </div>
      <div id="arcana-db-results" aria-live="polite">
        <div class="arcana-db-message"><span class="arcana-loading-mark" aria-hidden="true">✦</span>${escapeHtml(arcanaUi("loading"))}</div>
      </div>
    </section>
  `;
}

function renderArcanaMainStatFilters() {
  const container = document.querySelector("#arcana-main-stat-filters");
  const archive = arcanaDatabaseState.data;
  if (!container || !archive) return;
  const publishedArcanas = getPublishedArcanas(archive);
  const found = new Set(publishedArcanas.map((arcana) => getArcanaArchiveText(arcana.mainStat, "ko")));
  const stats = ARCANA_MAIN_STAT_ORDER.filter((stat) => found.has(stat));
  container.innerHTML = ["all", ...stats].map((stat) => {
    const label = stat === "all"
      ? arcanaUi("all")
      : getArcanaArchiveText(publishedArcanas.find((arcana) => getArcanaArchiveText(arcana.mainStat, "ko") === stat)?.mainStat);
    return `
      <button type="button" class="arcana-filter-chip${arcanaDatabaseState.mainStat === stat ? " is-active" : ""}"
        data-arcana-main-stat="${escapeHtml(stat)}">${escapeHtml(label)}</button>
    `;
  }).join("");
}

function collectArcanaSearchStrings(value, output = [], key = "") {
  if (value == null) return output;
  if (typeof value === "string") {
    if (!["image", "icon", "background", "mainStatIcon", "source"].includes(key)) {
      output.push(value.replace(/<[^>]*>/g, " "));
    }
    return output;
  }
  if (Array.isArray(value)) {
    value.forEach((item) => collectArcanaSearchStrings(item, output, key));
    return output;
  }
  if (typeof value === "object") {
    Object.entries(value).forEach(([childKey, childValue]) => {
      if (childKey !== "iconAssets") collectArcanaSearchStrings(childValue, output, childKey);
    });
  }
  return output;
}

function getArcanaSearchText(arcana, archive) {
  const potentialIds = new Set();
  const journeyBuffIds = new Set();
  if (arcana.specialPotentialId != null) potentialIds.add(Number(arcana.specialPotentialId));

  const collectRewardReferences = (value) => {
    if (!value) return;
    if (Array.isArray(value)) {
      value.forEach(collectRewardReferences);
      return;
    }
    if (typeof value !== "object") return;
    if (value.type === "RT_SE_POTEN" && value.rewardId != null) potentialIds.add(Number(value.rewardId));
    if (value.type === "RT_JOURNEY_BUFF" && value.rewardId != null) journeyBuffIds.add(Number(value.rewardId));
    Object.values(value).forEach(collectRewardReferences);
  };
  collectRewardReferences(arcana.events);

  const referencedPotentials = (archive.potentials || []).filter((potential) => potentialIds.has(Number(potential.id)));
  const referencedBuffs = (archive.journeyBuffs || []).filter((buff) => journeyBuffIds.has(Number(buff.id)));
  return collectArcanaSearchStrings([arcana, referencedPotentials, referencedBuffs]).join(" ");
}

function getFilteredArcanas() {
  const archive = arcanaDatabaseState.data;
  if (!archive) return [];
  const query = normalizeGuideSearch(arcanaDatabaseState.query);
  return getPublishedArcanas(archive).filter((arcana) => {
    if (arcanaDatabaseState.rarity !== "all" && arcana.rarity !== arcanaDatabaseState.rarity) return false;
    if (arcanaDatabaseState.mainStat !== "all" && getArcanaArchiveText(arcana.mainStat, "ko") !== arcanaDatabaseState.mainStat) return false;
    if (!query) return true;
    const searchText = arcanaSearchIndex.get(Number(arcana.id))
      || normalizeGuideSearch(getArcanaSearchText(arcana, archive));
    return searchText.includes(query);
  }).sort((a, b) => {
    return (ARCANA_RELEASE_ORDER.get(Number(a.id)) ?? Number.MAX_SAFE_INTEGER)
      - (ARCANA_RELEASE_ORDER.get(Number(b.id)) ?? Number.MAX_SAFE_INTEGER);
  });
}

function createArcanaListCard(arcana) {
  const name = getArcanaArchiveText(arcana.name);
  const character = getArcanaArchiveText(arcana.character);
  const mainStat = getArcanaArchiveText(arcana.mainStat);
  return `
    <button type="button" class="arcana-index-card rarity-${escapeHtml(arcana.rarity.toLowerCase())}"
      data-open-arcana="${escapeHtml(arcana.id)}" aria-label="${escapeHtml(name)}">
      <span class="arcana-index-image">
        <img src="${escapeHtml(arcana.image)}" alt="${escapeHtml(name)}" loading="lazy"
          onerror="this.style.display='none';this.parentElement.classList.add('is-missing')">
        <span class="arcana-index-rarity">${escapeHtml(arcana.rarity)}</span>
      </span>
      <span class="arcana-index-copy">
        <strong>${escapeHtml(name)}</strong>
        <span>${escapeHtml(character)}</span>
        <small>
          ${arcana.mainStatIcon ? `<img src="${escapeHtml(arcana.mainStatIcon)}" alt="" loading="lazy">` : ""}
          ${escapeHtml(mainStat)}
        </small>
      </span>
    </button>
  `;
}

function renderArcanaDatabase() {
  const results = document.querySelector("#arcana-db-results");
  if (!results || !arcanaDatabaseState.data) return;
  const filtered = getFilteredArcanas();
  const visible = document.querySelector("#arcana-visible-count");
  if (visible) visible.textContent = String(filtered.length);
  if (!filtered.length) {
    results.innerHTML = `
      <div class="arcana-db-empty">
        <span aria-hidden="true">◇</span>
        <strong>${escapeHtml(arcanaUi("emptyTitle"))}</strong>
        <p>${escapeHtml(arcanaUi("emptyDescription"))}</p>
      </div>
    `;
    return;
  }
  results.innerHTML = `<div class="arcana-index-grid">${filtered.map(createArcanaListCard).join("")}</div>`;
}

function setArcanaLoadError(error) {
  console.warn("Arcana archive load failed:", error);
  const results = document.querySelector("#arcana-db-results");
  if (results) results.innerHTML = `<div class="arcana-db-message is-error">${escapeHtml(arcanaUi("loadError"))}</div>`;
}

function initializeArcanaDatabase() {
  arcanaDatabaseState.requestToken += 1;
  const token = arcanaDatabaseState.requestToken;
  arcanaDatabaseState.selectedId = null;
  if (arcanaDatabaseState.data) {
    renderArcanaMainStatFilters();
    renderArcanaDatabase();
    return;
  }
  loadArcanaArchive().then((archive) => {
    if (token !== arcanaDatabaseState.requestToken || !document.querySelector('.arcana-db-page[data-arcana-view="list"]')) return;
    arcanaDatabaseState.data = archive;
    renderArcanaMainStatFilters();
    renderArcanaDatabase();
  }).catch(setArcanaLoadError);
}

function getArcanaPotential(id) {
  return arcanaDatabaseState.data?.potentials?.find((potential) => Number(potential.id) === Number(id)) || null;
}

function getArcanaJourneyBuff(id) {
  return arcanaDatabaseState.data?.journeyBuffs?.find((buff) => Number(buff.id) === Number(id)) || null;
}

function createArcanaPotentialIcon(potential) {
  if (!potential) return "";
  return `
    <span class="arcana-potential-icon" aria-hidden="true">
      <img class="arcana-potential-bg" src="${escapeHtml(potential.background)}" alt="">
      <img class="arcana-potential-symbol" src="${escapeHtml(potential.icon)}" alt="">
    </span>
  `;
}

function createArcanaPotentialBuffsMarkup(potential) {
  return (potential?.buffs || []).map((buff) => `
    <div class="arcana-reward-item is-rich">
      ${buff.icon ? `<img src="${escapeHtml(buff.icon)}" alt="" loading="lazy">` : ""}
      <div>
        <div class="arcana-reward-title"><span>${escapeHtml(getArcanaArchiveText(buff.name))}</span></div>
        <p>${renderArcanaRichText(getArcanaArchiveText(buff.description))}</p>
      </div>
    </div>
  `).join("");
}

function createArcanaPotentialMarkup(potential) {
  if (!potential) return "";
  return `
    <section class="arcana-detail-section arcana-potential-section">
      <div class="arcana-section-heading">
        <span>${createArcanaPotentialIcon(potential)}</span>
        <div>
          <small>${escapeHtml(arcanaUi("specialPotential"))}</small>
          <h2>${escapeHtml(getArcanaArchiveText(potential.name))}</h2>
        </div>
      </div>
      <p class="arcana-rich-description">${renderArcanaRichText(getArcanaArchiveText(potential.description))}</p>
      ${createArcanaPotentialBuffsMarkup(potential)}
    </section>
  `;
}

function createArcanaUniqueEffectMarkup(effect) {
  if (!effect) return "";
  return `
    <section class="arcana-detail-section arcana-unique-section">
      <div class="arcana-section-title-row">
        <div>
          <small>${escapeHtml(arcanaUi("uniqueEffect"))}</small>
          <h2>${escapeHtml(getArcanaArchiveText(effect.name))}</h2>
        </div>
        <span>${escapeHtml(arcanaUi("unlockLevel"))} ${escapeHtml(effect.unlockLevel)}</span>
      </div>
      <p class="arcana-rich-description">${renderArcanaRichText(getArcanaArchiveText(effect.description))}</p>
    </section>
  `;
}

function createArcanaEffectsMarkup(arcana) {
  const categories = [
    ["journeyStart", arcanaUi("journeyStart")],
    ["training", arcanaUi("training")],
    ["telepathy", arcanaUi("telepathy")],
    ["supportQuest", arcanaUi("supportQuest")]
  ].filter(([key]) => arcana.effects?.[key]?.length);
  if (!categories.length) {
    return `<section class="arcana-detail-section"><h2>${escapeHtml(arcanaUi("effects"))}</h2><p>${escapeHtml(arcanaUi("noEffects"))}</p></section>`;
  }
  return `
    <section class="arcana-detail-section arcana-effects-section">
      <h2>${escapeHtml(arcanaUi("effects"))}</h2>
      <div class="arcana-effect-groups">
        ${categories.map(([key, label]) => `
          <div class="arcana-effect-group">
            <h3>${escapeHtml(label)}</h3>
            <div class="arcana-effect-rows">
              ${arcana.effects[key].map((effect) => `
                <div class="arcana-effect-row">
                  <span>${escapeHtml(getArcanaArchiveText(effect.valueType))}</span>
                  <strong>${escapeHtml(effect.values?.[String(arcanaDatabaseState.level)]?.display ?? "-")}</strong>
                </div>
              `).join("")}
            </div>
          </div>
        `).join("")}
      </div>
    </section>
  `;
}

function formatArcanaRewardAmount(reward) {
  const min = Number(reward.min);
  const max = Number(reward.max);
  if (!Number.isFinite(min) && !Number.isFinite(max)) return "";
  const signed = (value) => value > 0 ? `+${value}` : String(value);
  if (!Number.isFinite(max) || min === max) return signed(min);
  return `${signed(min)} ~ ${signed(max)}`;
}

function createArcanaRewardMarkup(reward) {
  const amount = formatArcanaRewardAmount(reward);
  if (reward.type === "RT_STAT") {
    return `
      <div class="arcana-reward-item">
        ${reward.icon ? `<img src="${escapeHtml(reward.icon)}" alt="" loading="lazy">` : ""}
        <span>${escapeHtml(getArcanaArchiveText(reward.statName))}</span>
        <strong class="${Number(reward.min) < 0 ? "is-negative" : ""}">${escapeHtml(amount)}</strong>
      </div>
    `;
  }
  if (reward.type === "RT_SE_POTEN") {
    const potential = getArcanaPotential(reward.rewardId);
    if (!potential) return "";
    return `
      <div class="arcana-reward-item is-rich">
        ${createArcanaPotentialIcon(potential)}
        <div>
          <div class="arcana-reward-title"><span>${escapeHtml(getArcanaArchiveText(potential.name))}</span></div>
          <p>${renderArcanaRichText(getArcanaArchiveText(potential.description))}</p>
          ${createArcanaPotentialBuffsMarkup(potential)}
        </div>
      </div>
    `;
  }
  if (reward.type === "RT_JOURNEY_BUFF") {
    const buff = getArcanaJourneyBuff(reward.rewardId);
    const name = buff?.name || reward.journeyBuffName;
    if (!name) return "";
    const description = buff?.description || reward.journeyBuffDescription;
    return `
      <div class="arcana-reward-item is-rich">
        ${buff?.icon ? `<img src="${escapeHtml(buff.icon)}" alt="" loading="lazy">` : ""}
        <div>
          <div class="arcana-reward-title">
            <span>${escapeHtml(getArcanaArchiveText(name))}</span>
            ${amount ? `<strong>${escapeHtml(amount.replace(/^\+/, ""))}${escapeHtml(arcanaUi("turns"))}</strong>` : ""}
          </div>
          ${description ? `<p>${renderArcanaRichText(getArcanaArchiveText(description))}</p>` : ""}
        </div>
      </div>
    `;
  }
  const simpleLabels = {
    RT_POTEN_POINT: arcanaUi("potentialPoints"),
    RT_STAMINA: arcanaUi("stamina"),
    RT_CONDITION: arcanaUi("condition")
  };
  return `
    <div class="arcana-reward-item">
      <span>${escapeHtml(simpleLabels[reward.type] || reward.type)}</span>
      <strong class="${Number(reward.min) < 0 ? "is-negative" : ""}">${escapeHtml(amount)}</strong>
    </div>
  `;
}

function createArcanaRewardGroups(groups) {
  return (groups || []).map((alternatives) => `
    <div class="arcana-reward-group">
      ${(alternatives || []).map((reward, index) => `${index ? '<span class="arcana-reward-or">/</span>' : ""}${createArcanaRewardMarkup(reward)}`).join("")}
    </div>
  `).join("");
}

function createArcanaChoiceResultMarkup(labelKey, groups) {
  if (!groups?.length) return "";
  return `
    <div class="arcana-choice-result is-${labelKey}">
      <strong>${escapeHtml(arcanaUi(labelKey))}</strong>
      <div>${createArcanaRewardGroups(groups)}</div>
    </div>
  `;
}

function createArcanaEventsMarkup(arcana) {
  if (!arcana.events?.length) {
    return `
      <section class="arcana-detail-section arcana-events-section">
        <h2>${escapeHtml(arcanaUi("events"))}</h2>
        <p>${escapeHtml(arcanaUi("noEvents"))}</p>
      </section>
    `;
  }
  return `
    <section class="arcana-detail-section arcana-events-section">
      <div class="arcana-section-title-row">
        <h2>${escapeHtml(arcanaUi("events"))}</h2>
        <span>${escapeHtml(arcana.events.length)}${escapeHtml(arcanaUi("eventCount"))}</span>
      </div>
      <div class="arcana-event-list">
        ${arcana.events.map((event, eventIndex) => `
          <article class="arcana-event">
            <h3><span>${eventIndex + 1}</span>${escapeHtml(getArcanaArchiveText(event.name))}</h3>
            <div class="arcana-choice-list">
              ${event.choices.map((choice, choiceIndex) => {
                const choiceName = getArcanaArchiveText(choice.name).trim();
                return `
                  <div class="arcana-choice">
                    <h4><span>${choiceIndex + 1}</span>${escapeHtml(choiceName || arcanaUi("automatic"))}</h4>
                    ${createArcanaChoiceResultMarkup("success", choice.successRewards)}
                    ${createArcanaChoiceResultMarkup("failure", choice.failureRewards)}
                  </div>
                `;
              }).join("")}
            </div>
          </article>
        `).join("")}
      </div>
    </section>
  `;
}

function createArcanaDetailMarkup(arcana) {
  const name = getArcanaArchiveText(arcana.name);
  const character = getArcanaArchiveText(arcana.character);
  const mainStat = getArcanaArchiveText(arcana.mainStat);
  const specialPotential = getArcanaPotential(arcana.specialPotentialId) || (Array.isArray(arcana.potentialDetails) ? arcana.potentialDetails.find((potential) => Number(potential.id) === Number(arcana.specialPotentialId)) : null);
  return `
    <section class="arcana-db-page arcana-detail-page" data-arcana-view="detail" data-arcana-id="${escapeHtml(arcana.id)}">
      <header class="arcana-detail-hero">
        <div class="arcana-detail-image">
          <img src="${escapeHtml(arcana.image)}" alt="${escapeHtml(name)}">
        </div>
        <div class="arcana-detail-intro">
          <p class="eyebrow">ARCANA DATABASE</p>
          <div class="arcana-detail-badges"><span>${escapeHtml(arcana.rarity)}</span><span>${escapeHtml(mainStat)}</span></div>
          <h1>${escapeHtml(name)}</h1>
          <dl>
            <div><dt>${escapeHtml(arcanaUi("character"))}</dt><dd>${escapeHtml(character)}</dd></div>
            <div><dt>${escapeHtml(arcanaUi("mainStat"))}</dt><dd>${arcana.mainStatIcon ? `<img src="${escapeHtml(arcana.mainStatIcon)}" alt="">` : ""}${escapeHtml(mainStat)}</dd></div>
            ${arcana.assists?.length ? `<div><dt>${escapeHtml(arcanaUi("assist"))}</dt><dd>${arcana.assists.map((assist) => escapeHtml(getArcanaArchiveText(assist))).join(" · ")}</dd></div>` : ""}
          </dl>
        </div>
      </header>

      <nav class="arcana-level-picker" aria-label="${escapeHtml(arcanaUi("level"))}">
        <strong>${escapeHtml(arcanaUi("level"))}</strong>
        <div>${ARCANA_LEVELS.map((level) => `
          <button type="button" class="${arcanaDatabaseState.level === level ? "is-active" : ""}" data-arcana-level="${level}">Lv.${level}</button>
        `).join("")}</div>
      </nav>

      <div class="arcana-detail-content">
        ${createArcanaPotentialMarkup(specialPotential)}
        ${createArcanaUniqueEffectMarkup(arcana.uniqueEffect)}
        ${createArcanaEffectsMarkup(arcana)}
        ${createArcanaEventsMarkup(arcana)}
      </div>
    </section>
  `;
}

function renderArcanaDetail() {
  const arcana = getPublishedArcanas().find((item) => Number(item.id) === Number(arcanaDatabaseState.selectedId));
  if (!arcana) return false;
  simpleContent.innerHTML = createArcanaDetailMarkup(arcana);
  return true;
}

function openArcanaDetail(id, options = {}) {
  const numericId = Number(id);
  if (!Number.isFinite(numericId)) {
    openSimple("arcana", options);
    return;
  }
  arcanaDatabaseState.requestToken += 1;
  const token = arcanaDatabaseState.requestToken;
  arcanaDatabaseState.selectedId = numericId;
  simpleContent.innerHTML = `
    <section class="arcana-db-page" data-arcana-view="detail">
      <div class="arcana-db-message"><span class="arcana-loading-mark" aria-hidden="true">✦</span>${escapeHtml(arcanaUi("loading"))}</div>
    </section>
  `;
  showOnly("simple");
  setActiveNav("arcana");
  if (!options.skipHash) history.pushState({ view: "arcana-detail", id: numericId }, "", `#arcana/${numericId}`);
  if (!options.keepScroll) window.scrollTo({ top: 0, behavior: "smooth" });

  const finish = (archive) => {
    if (token !== arcanaDatabaseState.requestToken || !document.querySelector('.arcana-db-page[data-arcana-view="detail"]')) return;
    arcanaDatabaseState.data = archive;
    if (!renderArcanaDetail()) {
      history.replaceState({ view: "simple", section: "arcana" }, "", "#arcana");
      openSimple("arcana", { skipHash: true, keepScroll: true });
    }
  };
  if (arcanaDatabaseState.data) finish(arcanaDatabaseState.data);
  else loadArcanaArchive().then(finish).catch((error) => {
    console.warn("Arcana detail load failed:", error);
    const page = document.querySelector('.arcana-db-page[data-arcana-view="detail"]');
    if (page) page.innerHTML = `<div class="arcana-db-message is-error">${escapeHtml(arcanaUi("loadError"))}</div>`;
  });
}

function updateArcanaDatabaseLanguage() {
  const page = simpleContent?.querySelector(".arcana-db-page");
  if (!page) return;
  if (arcanaDatabaseState.selectedId != null && page.dataset.arcanaView === "detail") {
    if (arcanaDatabaseState.data) renderArcanaDetail();
    return;
  }
  simpleContent.innerHTML = createArcanaDatabaseMarkup();
  if (arcanaDatabaseState.data) {
    renderArcanaMainStatFilters();
    renderArcanaDatabase();
  } else {
    initializeArcanaDatabase();
  }
}

function handleArcanaDatabaseInput(event) {
  if (event.target?.id !== "arcana-search-input") return;
  arcanaDatabaseState.query = event.target.value;
  renderArcanaDatabase();
}

function handleArcanaDatabaseClick(event) {
  const openButton = event.target.closest("[data-open-arcana]");
  if (openButton) {
    openArcanaDetail(openButton.dataset.openArcana);
    return;
  }
  const rarityButton = event.target.closest("[data-arcana-rarity]");
  if (rarityButton) {
    arcanaDatabaseState.rarity = rarityButton.dataset.arcanaRarity;
    document.querySelectorAll("[data-arcana-rarity]").forEach((button) => button.classList.toggle("is-active", button === rarityButton));
    renderArcanaDatabase();
    return;
  }
  const statButton = event.target.closest("[data-arcana-main-stat]");
  if (statButton) {
    arcanaDatabaseState.mainStat = statButton.dataset.arcanaMainStat;
    document.querySelectorAll("[data-arcana-main-stat]").forEach((button) => button.classList.toggle("is-active", button === statButton));
    renderArcanaDatabase();
    return;
  }
  if (event.target.closest("#arcana-reset-filters")) {
    arcanaDatabaseState.query = "";
    arcanaDatabaseState.rarity = "all";
    arcanaDatabaseState.mainStat = "all";
    const input = document.querySelector("#arcana-search-input");
    if (input) input.value = "";
    document.querySelectorAll("[data-arcana-rarity]").forEach((button) => button.classList.toggle("is-active", button.dataset.arcanaRarity === "all"));
    document.querySelectorAll("[data-arcana-main-stat]").forEach((button) => button.classList.toggle("is-active", button.dataset.arcanaMainStat === "all"));
    renderArcanaDatabase();
    return;
  }
  const levelButton = event.target.closest("[data-arcana-level]");
  if (levelButton) {
    arcanaDatabaseState.level = Number(levelButton.dataset.arcanaLevel);
    renderArcanaDetail();
  }
}

function ensureJourneyStatPriorityStyle() {
  if (document.getElementById("journey-stat-priority-style")) return;
  const style = document.createElement("style");
  style.id = "journey-stat-priority-style";
  style.textContent = `
    .journey-stat-priority-lines {
      display: flex;
      flex-direction: column;
      gap: 14px;
    }
    .journey-stat-priority-line {
      min-width: 0;
    }
    .journey-stat-priority-label {
      margin: 0 0 3px;
      color: var(--muted);
      font-size: .86rem;
      font-weight: 800;
      letter-spacing: .01em;
    }
    .journey-stat-priority-note {
      margin: 0 0 7px;
      color: var(--muted);
      font-size: .78rem;
      font-weight: 700;
      line-height: 1.35;
    }
    .journey-stat-priority-item {
      display: inline-flex;
      align-items: center;
      gap: 7px;
      flex: 0 0 auto;
      color: var(--text);
      font-size: clamp(.9rem, 1.4vw, 1.02rem);
    }
    .journey-stat-priority-item img {
      width: 34px;
      height: 34px;
      object-fit: contain;
      flex: 0 0 34px;
    }
    .journey-stat-priority-operator {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      flex: 0 0 auto;
      min-width: 16px;
      color: var(--muted);
      font-weight: 900;
      font-size: 1.15rem;
    }
    .journey-stat-priority-operator.is-equal {
      color: var(--text);
      opacity: .78;
    }
    @media (max-width: 640px) {
      .journey-stat-priority-lines { gap: 12px; }
      .journey-stat-priority-label { margin-bottom: 2px; font-size: .8rem; }
      .journey-stat-priority-note { margin-bottom: 5px; font-size: .72rem; }
      .journey-stat-priority-row { gap: 7px !important; }
      .journey-stat-priority-item { gap: 5px; font-size: .88rem; }
      .journey-stat-priority-item img { width: 29px; height: 29px; flex-basis: 29px; }
      .journey-stat-priority-operator { min-width: 12px; font-size: 1rem; }
    }
  `;
  document.head.appendChild(style);
}

ensureJourneyStatPriorityStyle();

const JOURNEY_EXTERNAL_URL = "https://starsavior-journey-choice.pages.dev/journey-choice";

function openSimple(section, options = {}) {
  // 여정 데이터/백업 로직은 유지하되, 사이트 내부 여정 화면은 공개하지 않는다.
  // 여정 탭 또는 #journey 접근 시 외부 여정 선택 사이트로 이동한다.
  if (section === "journey") {
    window.location.href = JOURNEY_EXTERNAL_URL;
    return;
  }
  if (section === "arcana") {
    simpleContent.innerHTML = createArcanaDatabaseMarkup();
  } else if (section === "equipment") {
    simpleContent.innerHTML = createEquipmentDatabaseMarkup();
  } else {
    const data = getSimpleSection(section);
    if (!data) {
      openList(options);
      return;
    }

    simpleContent.innerHTML = `
      <section class="simple-panel">
        <header class="simple-panel-header">
          <p>${escapeHtml(data.eyebrow)}</p>
          <h1>${escapeHtml(data.title)}</h1>
        </header>
        <div class="simple-panel-body">
          <div class="simple-link-grid">
            ${data.items.map((item) => `
              <${item.link ? "a" : "div"} class="simple-link"
                ${item.link ? `href="${escapeHtml(item.link)}" target="_blank" rel="noopener noreferrer"` : ""}>
                <small>${escapeHtml(item.label)}</small>
                <strong>${escapeHtml(item.name)}</strong>
              </${item.link ? "a" : "div"}>
            `).join("")}
          </div>
        </div>
      </section>
    `;
  }

  applyLanguageToDOM(simpleView);
  if (section === "arcana") initializeArcanaDatabase();
  showOnly("simple");
  setActiveNav(section);

  if (!options.skipHash) {
    history.pushState({ view: "simple", section }, "", `#${section}`);
  }

  if (!options.keepScroll) {
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
}

function getSimpleSection(section) {
  if (section === "arcana") {
    return {
      eyebrow: "ARCANA INDEX",
      title: "아르카나",
      items: ARCANA_CATEGORIES.map((name) => ({ label: "STAT CATEGORY", name }))
    };
  }

  if (section === "equipment") {
    return {
      eyebrow: "EQUIPMENT GUIDE",
      title: "장비",
      items: [
        { label: "ARCA.LIVE GUIDE", name: "장비 가이드 바로가기", link: "https://arca.live/b/starsavior/165397313" },
        { label: "SETTING", name: "PVE 추천 세팅" },
        { label: "SETTING", name: "PVP 추천 세팅" }
      ]
    };
  }

  if (section === "cosmo") {
    return {
      eyebrow: "COSMO GATE",
      title: "코스모 게이트",
      items: COSMO_GUIDES.map(([name, link]) => ({ label: "BOSS GUIDE", name, link }))
    };
  }

  return null;
}

function syncFromHash() {
  const hash = decodeURIComponent(location.hash.replace(/^#/, ""));

  if (!hash || hash === "savior") {
    openList({ skipHash: true, keepScroll: true });
    return;
  }

  if (hash.startsWith("savior/")) {
    openSavior(hash.slice("savior/".length), { skipHash: true, keepScroll: true });
    return;
  }

  if (hash.startsWith("arcana/")) {
    openArcanaDetail(hash.slice("arcana/".length), { skipHash: true, keepScroll: true });
    return;
  }

  if (["arcana", "journey", "equipment", "cosmo"].includes(hash)) {
    openSimple(hash, { skipHash: true, keepScroll: true });
    return;
  }

  openList({ skipHash: true, keepScroll: true });
}

function setFilterButtons(containerSelector, attribute, currentValue) {
  document.querySelectorAll(`${containerSelector} [${attribute}]`).forEach((button) => {
    button.classList.toggle("is-active", button.getAttribute(attribute) === currentValue);
  });
}

searchInput.addEventListener("input", (event) => {
  state.query = event.currentTarget.value;
  renderList();
});

document.querySelector("#element-filters").addEventListener("click", (event) => {
  const button = event.target.closest("[data-element]");
  if (!button) return;

  state.element = button.dataset.element;
  setFilterButtons("#element-filters", "data-element", state.element);
  renderList();
});

document.querySelector("#class-filters").addEventListener("click", (event) => {
  const button = event.target.closest("[data-class]");
  if (!button) return;

  state.className = button.dataset.class;
  setFilterButtons("#class-filters", "data-class", state.className);
  renderList();
});

resetFilter.addEventListener("click", () => {
  state.query = "";
  state.element = "all";
  state.className = "all";
  searchInput.value = "";
  setFilterButtons("#element-filters", "data-element", "all");
  setFilterButtons("#class-filters", "data-class", "all");
  renderList();
});

document.querySelectorAll("[data-open-list]").forEach((button) => {
  button.addEventListener("click", () => openList());
});

navItems.forEach((button) => {
  button.addEventListener("click", () => {
    const section = button.dataset.section;
    if (section === "savior") {
      openList();
    } else {
      openSimple(section);
    }
  });
});


function installSaviorListGuidance() {
  if (!document.querySelector("#savior-list-guidance-styles")) {
    const style = document.createElement("style");
    style.id = "savior-list-guidance-styles";
    style.textContent = `
      #list-view .page-heading > div:first-child {
        width: 100%;
        min-width: 0;
      }

      #list-view .newbie-equipment-notice,
      #list-view .site-update-notice,
      #list-view .site-recommendation-warning {
        width: 100% !important;
        max-width: none !important;
      }

      #list-view .site-update-notice,
      #list-view .site-recommendation-warning {
        display: flex;
        align-items: center;
        gap: 18px;
        margin-top: 20px;
        padding: 22px 24px;
        border: 1px solid var(--line);
        border-radius: 16px;
        background: var(--surface);
        box-shadow: none;
      }

      #list-view .site-update-notice {
        border-color: color-mix(in srgb, var(--accent) 38%, var(--line));
      }

      #list-view .site-recommendation-warning {
        border-color: color-mix(in srgb, var(--warning) 38%, var(--line));
      }

      #list-view .site-guidance-mascot {
        display: block;
        width: 112px;
        height: 112px;
        flex: 0 0 112px;
        object-fit: contain;
      }

      #list-view .site-guidance-copy {
        display: grid;
        min-width: 0;
        gap: 8px;
      }

      #list-view .site-guidance-copy > strong {
        font-size: 18px;
        font-weight: 950;
        line-height: 1.35;
      }

      #list-view .site-update-notice .site-guidance-copy > strong {
        color: var(--accent);
      }

      #list-view .site-recommendation-warning .site-guidance-copy > strong {
        color: var(--warning);
      }

      #list-view .site-recommendation-warning .site-guidance-copy > span,
      #list-view .site-update-list {
        color: var(--text);
        font-size: 14px;
        font-weight: 750;
        line-height: 1.7;
      }

      #list-view .site-update-list {
        display: grid;
        gap: 3px;
        margin: 0;
        padding-left: 1.15em;
      }

      #list-view .site-update-list li {
        padding-left: 2px;
        overflow-wrap: anywhere;
        word-break: keep-all;
      }

      html[data-theme="light"] #list-view .site-update-notice,
      html[data-theme="light"] #list-view .site-recommendation-warning {
        background: #fff;
      }

      html[data-theme="light"] #list-view .site-update-notice {
        border-color: color-mix(in srgb, var(--accent) 42%, #d3dae5);
      }

      html[data-theme="light"] #list-view .site-recommendation-warning {
        border-color: color-mix(in srgb, var(--warning) 42%, #d3dae5);
      }

      @media (max-width: 640px) {
        #list-view .site-update-notice,
        #list-view .site-recommendation-warning {
          align-items: center;
          gap: 13px;
          padding: 18px 17px;
        }

        #list-view .site-guidance-mascot {
          width: 76px;
          height: 76px;
          flex-basis: 76px;
        }

        #list-view .site-guidance-copy > strong {
          font-size: 17px;
        }

        #list-view .site-recommendation-warning .site-guidance-copy > span,
        #list-view .site-update-list {
          font-size: 13.5px;
          line-height: 1.65;
        }

        #list-view .site-update-list {
          gap: 2px;
        }
      }

      @media (max-width: 430px) {
        #list-view .site-update-notice,
        #list-view .site-recommendation-warning {
          gap: 11px;
          padding-right: 14px;
          padding-left: 14px;
        }

        #list-view .site-guidance-mascot {
          width: 64px;
          height: 64px;
          flex-basis: 64px;
        }

        #list-view .site-update-list {
          font-size: 12.5px;
          line-height: 1.6;
        }
      }
    `;
    document.head.appendChild(style);
  }

  const newbieNotice = document.querySelector("#list-view .newbie-equipment-notice");
  const parent = newbieNotice?.parentElement;
  if (!newbieNotice || !parent) return;

  let warning = document.querySelector("#savior-recommendation-warning");
  if (!warning) {
    warning = document.createElement("div");
    warning.id = "savior-recommendation-warning";
    warning.className = "site-recommendation-warning";
    warning.innerHTML = `
      <img class="site-guidance-mascot"
        src="./images/guide-warning-mascot-clean.webp?v=20261002"
        alt="" aria-hidden="true">
      <span class="site-guidance-copy">
        <strong>주의사항</strong>
        <span>본 사이트의 추천 아르카나 및 장비 세팅은 절대적인 정답이 아닙니다. 이용하는 콘텐츠와 현재 육성 상태에 따라 적합한 세팅이 달라질 수 있으므로, 참고용으로 활용해 주세요.</span>
      </span>
    `;
    parent.insertBefore(warning, newbieNotice);
  }

  if (!document.querySelector("#savior-update-notice")) {
    const update = document.createElement("div");
    update.id = "savior-update-notice";
    update.className = "site-update-notice";
    update.innerHTML = `
      <img class="site-guidance-mascot"
        src="./images/guide-update-mascot-v2.webp?v=20261002-2"
        alt="" aria-hidden="true">
      <span class="site-guidance-copy">
        <strong>업데이트 안내</strong>
        <ul class="site-update-list">
          <li>클라리사 추천 아르카나 변경 (10.02)</li>
          <li>그웬 추가 및 추천 세팅 반영 (10.02)</li>
          <li>스트라이커 추천 아르카나 일괄 변경 (10.02)</li>
        </ul>
      </span>
    `;
    parent.insertBefore(update, warning);
  }
}

function applyRequestedLayoutFixes() {
  const style = document.createElement("style");
  style.id = "requested-layout-fixes";
  style.textContent = `
    .card-image::before,
    .card-image::after,
    .detail-portrait::before,
    .detail-portrait::after {
      display: none !important;
      content: none !important;
    }

    .character-image {
      z-index: 1 !important;
    }

    .build-grid {
      grid-template-columns: minmax(0, 1fr) !important;
    }

    html[lang="en"] .equipment-set-combination,
    html[lang="ja"] .equipment-set-combination {
      flex-wrap: nowrap !important;
      gap: 4px !important;
    }

    html[lang="en"] .equipment-set-joined,
    html[lang="ja"] .equipment-set-joined,
    html[lang="en"] .equipment-set-part,
    html[lang="ja"] .equipment-set-part {
      max-width: none !important;
      flex: 0 0 auto;
      gap: 4px !important;
    }

    html[lang="en"] .equipment-set-label,
    html[lang="ja"] .equipment-set-label {
      font-size: 13px !important;
      line-height: 1.2 !important;
      white-space: nowrap !important;
      word-break: normal !important;
      letter-spacing: -0.02em;
    }

    html[lang="en"] .equipment-set-plus,
    html[lang="ja"] .equipment-set-plus {
      flex: 0 0 auto;
      margin-inline: 0 !important;
    }
  `;
  document.head.appendChild(style);
}


function installArcanaCardStyles() {
  if (document.querySelector("#arcana-card-image-styles")) return;

  const style = document.createElement("style");
  style.id = "arcana-card-image-styles";
  style.textContent = `
    .arcana-slot.has-arcana-card {
      display: flex;
      min-height: 230px;
      padding: 0;
      justify-content: flex-end;
      border-style: solid;
      color: var(--text);
      text-decoration: none;
      background: var(--surface-2);
    }

    .arcana-slot.has-arcana-card::before {
      display: none;
    }

    .arcana-card-images {
      position: absolute;
      inset: 0 0 76px;
      display: grid;
      grid-template-columns: repeat(var(--arcana-count), minmax(0, 1fr));
      overflow: hidden;
      background: var(--surface-3);
    }

    .arcana-card-images::after {
      position: absolute;
      inset: 0;
      content: "";
      background: linear-gradient(to bottom, transparent 55%, rgba(9, 12, 19, 0.6));
      pointer-events: none;
    }

    .arcana-card-link {
      display: block;
      min-width: 0;
      height: 100%;
      overflow: hidden;
    }

    .arcana-card-images img {
      width: 100%;
      height: 100%;
      min-width: 0;
      object-fit: cover;
      object-position: center 24%;
    }

    .arcana-card-name-link {
      color: inherit;
      text-decoration: none;
    }

    .arcana-card-name-link:hover {
      color: var(--accent);
    }

    .arcana-card-copy {
      position: relative;
      z-index: 2;
      width: 100%;
      min-height: 76px;
      padding: 10px 11px 11px;
      border-top: 1px solid color-mix(in srgb, var(--slot-color) 50%, var(--line));
      background: color-mix(in srgb, var(--surface) 93%, transparent);
      backdrop-filter: blur(10px);
    }

    .arcana-card-copy small,
    .arcana-card-copy strong,
    .arcana-card-copy em {
      display: block;
    }

    .arcana-card-copy small {
      color: var(--faint);
      font-size: 9px;
      font-weight: 900;
      letter-spacing: 0.08em;
    }

    .arcana-card-copy strong {
      margin-top: 3px;
      font-size: 12px;
      font-weight: 950;
      line-height: 1.34;
    }

    .arcana-card-copy em {
      margin-top: 3px;
      color: var(--muted);
      font-size: 9px;
      font-style: normal;
      font-weight: 700;
    }

    .arcana-slot.has-arcana-card:hover {
      border-color: var(--slot-color);
      transform: translateY(-2px);
    }

    @media (max-width: 620px) {
      .arcana-slot.has-arcana-card {
        min-height: 210px;
      }

      .arcana-card-images {
        bottom: 82px;
      }

      .arcana-card-copy {
        min-height: 82px;
      }
    }
  `;

  document.head.appendChild(style);
}

function readSavedTheme() {
  try {
    return localStorage.getItem("starsavior-guide-theme");
  } catch {
    return null;
  }
}

function saveTheme(theme) {
  try {
    localStorage.setItem("starsavior-guide-theme", theme);
  } catch {
    // 로컬 파일 또는 제한된 브라우저 환경에서는 저장하지 않고 현재 화면에만 적용합니다.
  }
}

function applyTheme(theme, options = {}) {
  const selected = theme === "light" ? "light" : "dark";
  document.documentElement.dataset.theme = selected;
  if (!options.skipSave) saveTheme(selected);

  const light = selected === "light";
  themeToggle.querySelector("span").textContent = light ? "☾" : "☀";
  themeToggle.setAttribute("aria-label", translateString(light ? "어두운 테마로 변경" : "밝은 테마로 변경"));
}

themeToggle.addEventListener("click", () => {
  applyTheme(document.documentElement.dataset.theme === "light" ? "dark" : "light");
});

if (languageSelect) {
  languageSelect.addEventListener("change", (event) => {
    setLanguage(event.currentTarget.value);
  });
}

simpleContent.addEventListener("input", handleArcanaDatabaseInput);
simpleContent.addEventListener("click", handleArcanaDatabaseClick);

window.addEventListener("popstate", syncFromHash);
window.addEventListener("hashchange", syncFromHash);

installSaviorListGuidance();
applyRequestedLayoutFixes();
installArcanaCardStyles();
renderList();

// 추천 아르카나 이미지/상세 링크도 오직 로컬 아카이브에서 미리 연결한다.
// ./data/arcanas/arcanas.json 및 ./data/arcana-assets/cards/{id}.webp만 사용한다.
loadArcanaArchive().then((archive) => {
  arcanaDatabaseState.data = archive;

  const hash = decodeURIComponent(location.hash.replace(/^#/, ""));
  if (hash.startsWith("savior/") && !detailView.hidden) {
    const id = hash.slice("savior/".length);
    const activeSavior = SAVIORS.find((item) => item.id === id);
    if (activeSavior) {
      detailContent.innerHTML = createDetailMarkup(activeSavior);
      applyLanguageToDOM(detailView);
    }
  }
}).catch((error) => {
  console.warn("Local Arcana archive preload failed:", error);
});

loadSaviorProfileIndex().then(() => {
  renderList();
  const hash = decodeURIComponent(location.hash.replace(/^#/, ""));
  if (hash.startsWith("savior/")) {
    openSavior(hash.slice("savior/".length), { skipHash: true, keepScroll: true });
  }
}).catch((error) => {
  console.warn("Savior profile index load failed:", error);
});
loadSaviorSkillArchive().then(() => {
  if (!listView.hidden) renderList();
}).catch((error) => {
  console.warn("Savior resonance search archive load failed:", error);
});
refreshLanguageChrome();
applyTheme(readSavedTheme() || "dark", { skipSave: true });
syncFromHash();
applyLanguageToDOM(document.body);
if (languageSelect) languageSelect.value = currentLanguage;
