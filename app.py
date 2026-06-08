import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build

SPREADSHEET_ID = st.secrets.get("SPREADSHEET_ID", "1eG_r-ylF9xc40sg717ZBxBQ9-zrPoMpTi32vovSCfZ4")
SHEET_NAME = "予算管理"

@st.cache_resource
def get_sheets_service():
    if "gcp_service_account" in st.secrets:
        creds = service_account.Credentials.from_service_account_info(
            dict(st.secrets["gcp_service_account"]),
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
    else:
        creds = service_account.Credentials.from_service_account_file(
            "/Users/kairyu/Downloads/hailong-498813-ba0288185dc7.json",
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
    return build("sheets", "v4", credentials=creds).spreadsheets()

def ensure_sheet_exists(service):
    meta = service.get(spreadsheetId=SPREADSHEET_ID).execute()
    names = [s["properties"]["title"] for s in meta["sheets"]]
    if SHEET_NAME not in names:
        service.batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={"requests": [{"addSheet": {"properties": {"title": SHEET_NAME}}}]},
        ).execute()

def save_budget_to_sheets(trip_label, budget_dict):
    service = get_sheets_service()
    ensure_sheet_exists(service)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    rows = [["旅行", "項目", "金額（円）", "最終更新"]]
    for item, amount in budget_dict.items():
        rows.append([trip_label, item, amount, now])
    # 既存データを削除して上書き
    service.values().clear(
        spreadsheetId=SPREADSHEET_ID, range=f"{SHEET_NAME}!A1:Z1000"
    ).execute()
    service.values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_NAME}!A1",
        valueInputOption="RAW",
        body={"values": rows},
    ).execute()
    return now

def load_budget_from_sheets(trip_label):
    service = get_sheets_service()
    result = service.values().get(
        spreadsheetId=SPREADSHEET_ID, range=f"{SHEET_NAME}!A1:D1000"
    ).execute()
    rows = result.get("values", [])
    if len(rows) <= 1:
        return None, None
    loaded = {}
    last_update = None
    for row in rows[1:]:
        if len(row) >= 3 and row[0] == trip_label:
            loaded[row[1]] = int(row[2])
            if len(row) >= 4:
                last_update = row[3]
    return (loaded, last_update) if loaded else (None, None)

st.set_page_config(page_title="💑 ハネムーン旅行プランナー", page_icon="💑", layout="wide")

st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
    /* ── 変数 ── */
    :root {
        --navy:   #1B2A4A;
        --gold:   #C9974C;
        --coral:  #D96B5A;
        --sage:   #4A8063;
        --sky:    #4A7FB5;
        --cream:  #FAFAF7;
        --white:  #FFFFFF;
        --text:   #2D3748;
        --muted:  #718096;
        --shadow: 0 4px 20px rgba(27,42,74,0.10);
        --shadow-lg: 0 8px 32px rgba(27,42,74,0.18);
    }

    /* ── グローバル ── */
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* ── ヒーローヘッダー ── */
    .hero-header {
        background: linear-gradient(135deg, #1B2A4A 0%, #243868 60%, #1B2A4A 100%);
        padding: 44px 24px 36px;
        border-radius: 20px;
        text-align: center;
        margin-bottom: 28px;
        position: relative;
        overflow: hidden;
    }
    .hero-header::before {
        content: '';
        position: absolute;
        top: -80px; left: -80px;
        width: 260px; height: 260px;
        background: radial-gradient(circle, rgba(201,151,76,0.18) 0%, transparent 70%);
        border-radius: 50%;
    }
    .hero-header::after {
        content: '';
        position: absolute;
        bottom: -60px; right: -60px;
        width: 200px; height: 200px;
        background: radial-gradient(circle, rgba(217,107,90,0.12) 0%, transparent 70%);
        border-radius: 50%;
    }
    .main-title {
        font-family: 'Playfair Display', serif;
        font-size: 2.8rem;
        font-weight: 700;
        color: #FFFFFF !important;
        letter-spacing: 1px;
        margin: 0 0 10px;
        position: relative; z-index: 1;
    }
    .sub-title {
        font-family: 'Inter', sans-serif;
        font-size: 0.85rem;
        color: #C9974C !important;
        letter-spacing: 4px;
        text-transform: uppercase;
        margin: 0;
        position: relative; z-index: 1;
    }

    /* ── サイドバー ── */
    section[data-testid="stSidebar"] > div:first-child {
        background: linear-gradient(180deg, #1B2A4A 0%, #243556 100%);
    }
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] div { color: #E2E8F0 !important; }
    section[data-testid="stSidebar"] .stSelectbox label { color: #C9974C !important; font-weight: 600; }

    /* ── タブ ── */
    .stTabs [data-baseweb="tab-list"] { gap: 6px; }
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px 10px 0 0;
        padding: 10px 22px;
        font-weight: 500;
        color: var(--muted);
        transition: all 0.2s ease;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #1B2A4A, #2D4A7A) !important;
        color: white !important;
    }

    /* ── カード共通 ── */
    .city-card, .food-card, .move-card {
        background: var(--white);
        border-radius: 14px;
        padding: 16px 20px;
        margin-bottom: 12px;
        box-shadow: var(--shadow);
        transition: transform 0.25s ease, box-shadow 0.25s ease;
        animation: fadeUp 0.35s ease;
        color: var(--text) !important;
    }
    .city-card *, .food-card *, .move-card * { color: var(--text) !important; }

    .city-card  { border-left: 5px solid var(--gold); }
    .food-card  { border-left: 5px solid var(--coral); }
    .move-card  { border-left: 5px solid var(--sky); }

    .city-card:hover  { transform: translateY(-3px); box-shadow: var(--shadow-lg); }
    .food-card:hover  { transform: translateX(5px); }
    .move-card:hover  { transform: translateY(-2px); box-shadow: var(--shadow-lg); }

    /* ── ヒントボックス ── */
    .tip-box {
        background: linear-gradient(135deg, #EEF7F2 0%, #F5FBF7 100%);
        border: 1.5px solid #A8D5B8;
        border-radius: 14px;
        padding: 14px 18px;
        font-size: 0.92rem;
        color: #2D4A38 !important;
        margin-top: 12px;
        box-shadow: 0 2px 10px rgba(74,128,99,0.10);
    }
    .tip-box * { color: #2D4A38 !important; }

    /* ── 予算ボックス ── */
    .budget-box {
        background: linear-gradient(135deg, #1B2A4A 0%, #2D4A7A 100%);
        border-radius: 18px;
        padding: 28px 20px;
        text-align: center;
        box-shadow: 0 8px 32px rgba(27,42,74,0.28);
        color: white !important;
        position: relative;
        overflow: hidden;
    }
    .budget-box::before {
        content: '✈';
        position: absolute;
        font-size: 5rem;
        opacity: 0.05;
        right: 16px; bottom: -10px;
    }
    .budget-box * { color: white !important; }

    /* ── Sheetsリンク ── */
    .sheets-link {
        display: inline-flex; align-items: center; gap: 6px;
        background: linear-gradient(135deg, #0F9D58, #34A853);
        color: white !important;
        padding: 8px 16px;
        border-radius: 8px;
        font-size: 0.88rem;
        font-weight: 600;
        text-decoration: none;
        box-shadow: 0 2px 8px rgba(15,157,88,0.30);
        transition: opacity 0.2s;
    }
    .sheets-link:hover { opacity: 0.85; }

    /* ── アニメーション ── */
    @keyframes fadeUp {
        from { opacity: 0; transform: translateY(12px); }
        to   { opacity: 1; transform: translateY(0); }
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# データ定義
# ============================================================
TRIPS = {
    "🔴 Year 1 — 2027年 GW｜スペイン・フランス・イタリア": {
        "season": "春 4月末〜5月初旬", "days": 13, "color": "red",
        "cities": [
            {
                "name": "バルセロナ 🇪🇸", "lat": 41.3851, "lng": 2.1734,
                "stay": "1〜3日目（3泊）",
                "itinerary": [
                    ("1日目", "午後到着・ゴシック地区散策・タパスで乾杯🍷"),
                    ("2日目", "サグラダ・ファミリア（午前）→ グエル公園（午後）→ バルセロネータビーチ（夕方）"),
                    ("3日目", "カサ・バトリョ → ラス・ランブラス → ボケリア市場 → 夜はフラメンコショー"),
                ],
                "food": [
                    ("パエリア", "バルセロナの名物。シーフードたっぷりの本場の味"),
                    ("タパス", "色々な小皿料理。バルセロナのバルでワインと一緒に"),
                    ("クレマ・カタラナ", "カタルーニャ発祥のクリームブリュレ。スイーツ好きに必須"),
                    ("パン・コン・トマテ", "トマトをこすりつけたトースト。朝食の定番"),
                    ("サングリア", "フルーツ入りワイン。テラス席でのんびり飲んで"),
                ],
                "tip": "サグラダ・ファミリアは必ず事前オンライン予約！当日券なし",
                "move_next": "✈️ バルセロナ → パリ（Vueling/Air France 約2時間 ¥8,000〜20,000）",
            },
            {
                "name": "パリ 🇫🇷", "lat": 48.8566, "lng": 2.3522,
                "stay": "4〜6日目（3泊）",
                "itinerary": [
                    ("4日目", "エッフェル塔（昼）→ セーヌ川クルーズ（夕方）→ 夜景のエッフェル塔点灯を見る✨"),
                    ("5日目", "ルーブル美術館（午前）→ チュイルリー公園 → シャンゼリゼ通り散策"),
                    ("6日目", "ヴェルサイユ宮殿（日帰り）→ モンマルトル・サクレクール寺院（夕方）"),
                ],
                "food": [
                    ("クロワッサン", "パリのカフェで朝食に。バターの香りが格別"),
                    ("エスカルゴ", "ニンニクバターのカタツムリ。勇気を出して食べて！"),
                    ("フォアグラ", "フランス料理の真髄。ハネムーンの特別ディナーに"),
                    ("マカロン", "ラデュレやピエール・エルメのマカロンをお土産に"),
                    ("ワイン＆チーズ", "マルシェでチーズを買ってセーヌ川沿いでピクニック"),
                ],
                "tip": "エッフェル塔は夜21時〜の点灯タイムが最ロマンチック。必見！",
                "move_next": "✈️ パリ → ローマ（Air France/Alitalia 約2時間30分 ¥10,000〜25,000）",
            },
            {
                "name": "ローマ 🇮🇹", "lat": 41.9028, "lng": 12.4964,
                "stay": "7〜9日目（3泊）",
                "itinerary": [
                    ("7日目", "コロッセオ・フォロ・ロマーノ（午前）→ チルコ・マッシモ → トレビの泉（夕方）🪙"),
                    ("8日目", "バチカン美術館・システィーナ礼拝堂（午前・要予約）→ サン・ピエトロ大聖堂"),
                    ("9日目", "スペイン広場 → ナヴォーナ広場 → ボルゲーゼ公園でゆっくり"),
                ],
                "food": [
                    ("カルボナーラ", "ローマ発祥。本場は生クリームなし・卵とチーズのみ"),
                    ("カチョ・エ・ペペ", "チーズと黒胡椒だけのシンプルなパスタ。奥深い味"),
                    ("ジェラート", "ローマの街角で食べ歩き。毎日食べても飽きない"),
                    ("ピッツァ・マルゲリータ", "薄くてパリパリのローマ風ピッツァ"),
                    ("ティラミス", "イタリア発祥のデザート。カフェで必ず食べて"),
                ],
                "tip": "バチカン美術館は絶対事前予約！当日は数時間待ちになる",
                "move_next": "🚂 ローマ → ヴェネツィア（フレッチャロッサ高速鉄道 約3時間30分 ¥5,000〜10,000）",
            },
            {
                "name": "ヴェネツィア 🇮🇹", "lat": 45.4408, "lng": 12.3155,
                "stay": "10〜12日目（3泊）",
                "itinerary": [
                    ("10日目", "到着後ゴンドラ乗船🚤 → サン・マルコ広場 → リアルト橋 → 夕暮れの運河散歩"),
                    ("11日目", "ブラーノ島（カラフルな家）→ ムラーノ島（ガラス工芸）"),
                    ("12日目", "ドゥカーレ宮殿 → 路地散策 → 最後の夜はキャンドルディナー🕯️"),
                ],
                "food": [
                    ("チケッティ", "ヴェネツィア風タパス。バーカロ（立ち飲み屋）でプロセッコと"),
                    ("イカ墨リゾット", "真っ黒なリゾット。ヴェネツィアの名物"),
                    ("スプリッツ・アペロール", "オレンジ色のカクテル。カフェのテラスで"),
                    ("フリット・ミスト", "魚介の揚げ物。お祭りの屋台でも食べられる"),
                    ("プロセッコ", "イタリアのスパークリングワイン。乾杯に！🥂"),
                ],
                "tip": "ゴンドラは1艘€80〜100（2人で乗れる）。日没前後が最ロマンチック",
                "move_next": "✈️ ヴェネツィア → 東京（経由便 約15時間）",
            },
        ],
    },
    "🔵 Year 2 — 2028年 SW｜トルコ・ギリシャ": {
        "season": "初秋 9月中旬〜下旬", "days": 11, "color": "blue",
        "cities": [
            {
                "name": "イスタンブール 🇹🇷", "lat": 41.0082, "lng": 28.9784,
                "stay": "1〜2日目（2泊）",
                "itinerary": [
                    ("1日目", "到着・ブルーモスク → アヤソフィア → グランドバザール散策"),
                    ("2日目", "トプカプ宮殿 → ボスポラス海峡クルーズ🛳️ → スパイスバザール"),
                ],
                "food": [
                    ("ケバブ", "トルコの国民食。ドネル・シシ・アダナなど種類豊富"),
                    ("バクラヴァ", "ナッツとはちみつのパイ菓子。甘くて濃厚"),
                    ("チャイ", "トルコの紅茶。小さなグラスで何杯も飲む文化"),
                    ("メゼ", "前菜の盛り合わせ。フムス・ドルマなど色々"),
                    ("バリック・エクメキ", "サバのサンドイッチ。橋のたもとの屋台で"),
                ],
                "tip": "トルコ航空の成田→イスタンブール直行便で約12時間。疲れにくい",
                "move_next": "✈️ イスタンブール → カッパドキア（カイセリ空港 約1時間30分 ¥5,000〜12,000）",
            },
            {
                "name": "カッパドキア 🇹🇷", "lat": 38.6431, "lng": 34.8289,
                "stay": "3〜5日目（3泊）",
                "itinerary": [
                    ("3日目", "到着・ギョレメ野外博物館 → 奇岩群ハイキング（ローズバレー）"),
                    ("4日目", "🎈早朝4:30起床！熱気球フライト（日の出と奇岩の絶景）→ 地下都市デリンクユ"),
                    ("5日目", "洞窟ホテルでゆっくり朝食 → 陶器・絨毯のお土産探し → 夕日鑑賞"),
                ],
                "food": [
                    ("テスティ・ケバブ", "壺に入ったシチューケバブ。テーブルで壺を割る演出あり！"),
                    ("ギョズレメ", "薄焼きパンに具材を詰めたクレープ風軽食"),
                    ("トルコアイス", "伸びるアイス。売り子のパフォーマンスが楽しい"),
                    ("ローカルワイン", "カッパドキアはワインの産地。洞窟レストランで"),
                    ("朝食ビュッフェ", "洞窟ホテルの朝食は絶景付き。早起きして外で食べて"),
                ],
                "tip": "熱気球は必ず事前予約（€150〜200/人）。天候欠航もあるので余裕を持って",
                "move_next": "✈️ カッパドキア → アテネ（イスタンブール経由 約4時間）",
            },
            {
                "name": "アテネ 🇬🇷", "lat": 37.9838, "lng": 23.7275,
                "stay": "6〜7日目（2泊）",
                "itinerary": [
                    ("6日目", "アクロポリス・パルテノン神殿（午前）→ アクロポリス博物館 → プラカ地区"),
                    ("7日目", "国立考古学博物館 → シンタグマ広場 → 夕方フェリーか飛行機でサントリーニへ"),
                ],
                "food": [
                    ("ムサカ", "ナスとひき肉のギリシャ風グラタン。家庭料理の定番"),
                    ("スブラキ", "ギリシャ版焼き鳥。ピタパンに包んで食べる"),
                    ("ギリシャサラダ", "フェタチーズたっぷり。オリーブオイルが絶品"),
                    ("ウゾ", "アニス風味のギリシャの蒸留酒。食前酒として"),
                    ("バクラバ", "ギリシャ版もおいしい。お菓子屋で買い食い"),
                ],
                "tip": "アクロポリスは朝一番（8時）に行くと空いていて光が美しい",
                "move_next": "✈️ アテネ → サントリーニ（約45分 ¥5,000〜15,000）",
            },
            {
                "name": "サントリーニ 🇬🇷", "lat": 36.3932, "lng": 25.4615,
                "stay": "8〜10日目（3泊）",
                "itinerary": [
                    ("8日目", "フィラ散策 → カルデラ展望 → ワイナリー訪問🍷"),
                    ("9日目", "カタマランクルーズ（海・温泉・スノーケリング）→ 9月は海が温かい！"),
                    ("10日目", "イアへ移動 → 白と青の路地を散策 → 世界一美しい夕日を2人で🌅"),
                ],
                "food": [
                    ("フレッシュシーフード", "タコ・エビ・魚介。カルデラビューのレストランで"),
                    ("ファヴァ", "黄色いレンズ豆のピューレ。サントリーニ島の名産"),
                    ("トマトのフリッター", "島産ミニトマトのコロッケ。甘くて絶品"),
                    ("アシルティコ", "サントリーニ産白ワイン。ミネラル豊かな辛口"),
                    ("サンセットカクテル", "イアの夕日を見ながらカクテル。絶対やって"),
                ],
                "tip": "イアの夕日スポットは17時頃から場所取りが始まる。早めに行って！",
                "move_next": "✈️ サントリーニ → アテネ → 東京（帰国）",
            },
        ],
    },
    "🟢 Year 3 — 2029年 GW｜中欧・クロアチア": {
        "season": "春 4月末〜5月初旬", "days": 13, "color": "green",
        "cities": [
            {
                "name": "アムステルダム 🇳🇱", "lat": 52.3676, "lng": 4.9041,
                "stay": "1〜3日目（3泊）",
                "itinerary": [
                    ("1日目", "到着・運河クルーズ🚢 → ヨルダン地区散策 → カフェでゆっくり"),
                    ("2日目", "キューケンホフ（チューリップ満開！）→ アムステルダム国立美術館"),
                    ("3日目", "ゴッホ美術館 → アンネ・フランクの家 → レンタサイクルで街を回る🚲"),
                ],
                "food": [
                    ("ニシンの酢漬け", "ハーリングと呼ばれる生ニシン。屋台で食べ歩き"),
                    ("ストロープワッフェル", "シロップ入りワッフルクッキー。コーヒーに乗せて溶かして食べる"),
                    ("オランダチーズ", "ゴーダ・エダム。チーズ市場でまとめ買い"),
                    ("パンネクーケン", "薄いオランダ風パンケーキ。甘い・しょっぱいどちらも"),
                    ("クラフトビール", "アムステルダムのブラウプブでクラフトビールを"),
                ],
                "tip": "GWのキューケンホフ（チューリップ公園）は必見！5月中旬まで開園",
                "move_next": "✈️ アムステルダム → プラハ（約1時間30分 ¥8,000〜18,000）",
            },
            {
                "name": "プラハ 🇨🇿", "lat": 50.0755, "lng": 14.4378,
                "stay": "4〜6日目（3泊）",
                "itinerary": [
                    ("4日目", "プラハ城（午前）→ カレル橋（夕方の光が最高）→ 旧市街散策"),
                    ("5日目", "旧市街広場・天文時計 → ユダヤ人地区 → ヴルタヴァ川クルーズ"),
                    ("6日目", "ヴィシェフラト要塞 → ストラホフ修道院 → ピルスナーウルケル🍺"),
                ],
                "food": [
                    ("スヴィーチコバー", "牛肉の煮込みにクリームソース・クネドリーキ添え。国民食"),
                    ("グラーシュ", "牛肉シチュー。黒パンと一緒に食べる"),
                    ("トルデルニーク", "チムニーケーキ。旧市街の屋台で食べ歩き"),
                    ("ピルスナー・ウルケル", "ピルスナービールの発祥地チェコ。1杯€1〜2の安さ！"),
                    ("スヴァルコヴァー", "チェコのホットワイン（春でも夜は冷える）"),
                ],
                "tip": "プラハは物価が安い！高級レストランでも€20〜30/人。コスパ最高",
                "move_next": "🚂 プラハ → ウィーン（電車 約4時間 ¥3,000〜8,000）",
            },
            {
                "name": "ウィーン 🇦🇹", "lat": 48.2082, "lng": 16.3738,
                "stay": "7〜9日目（3泊）",
                "itinerary": [
                    ("7日目", "シェーンブルン宮殿（午前）→ ベルヴェデーレ宮殿（午後）→ リングシュトラーセ散策"),
                    ("8日目", "美術史美術館 → ナッシュマルクト（市場）→ 夜はオペラ鑑賞🎭"),
                    ("9日目", "聖シュテファン大聖堂 → カフェ・ツェントラルでコーヒー → ウィーンの森"),
                ],
                "food": [
                    ("ウィーナー・シュニッツェル", "薄く叩いた仔牛のカツレツ。ウィーン料理の代表"),
                    ("ザッハートルテ", "ホテル・ザッハーのチョコレートケーキ。本店で食べて"),
                    ("アプフェルシュトゥルーデル", "アップルパイ風ペイストリー。カフェの定番"),
                    ("メランジュ", "ウィーン風カフェオレ。カフェでゆっくり過ごす文化"),
                    ("グリューナー・ヴェルトリーナー", "オーストリアの白ワイン。ホイリゲ（ワイン酒場）で"),
                ],
                "tip": "国立歌劇場のオペラは当日立見席が€5〜！ドレスコードあるので服装に注意",
                "move_next": "✈️ ウィーン → ドゥブロヴニク（約1時間30分 ¥8,000〜20,000）",
            },
            {
                "name": "ドゥブロヴニク 🇭🇷", "lat": 42.6507, "lng": 18.0944,
                "stay": "10〜12日目（3泊）",
                "itinerary": [
                    ("10日目", "旧市街城壁ウォーク（2km、絶景！）→ スラドゥレド通り散策"),
                    ("11日目", "ロープウェイで山頂から絶景 → エルフィン島ボートツアー🏖️"),
                    ("12日目", "アドリア海シュノーケリング → カヤックツアー → 最後のサンセットディナー🌅"),
                ],
                "food": [
                    ("ペカ", "肉や魚介を炭火でじっくり焼いた郷土料理。要予約"),
                    ("イカ墨リゾット", "クロアチアでも絶品。アドリア海の新鮮な食材"),
                    ("プルシュット", "クロアチアのドライハム。チーズと一緒に"),
                    ("グラシュ", "クロアチア風グラーシュ。寒い日に"),
                    ("クロアチアワイン", "ディンガッチ（赤）が有名。地元のコナヴレ産も"),
                ],
                "tip": "城壁ウォークは朝8時が空いていて光も美しい。夏は暑いので早朝がベスト",
                "move_next": "✈️ ドゥブロヴニク → 東京（帰国）",
            },
        ],
    },
}

CHECKLIST = {
    "📋 事前準備": [
        "パスポート有効期限確認（帰国後6ヶ月以上）",
        "航空券予約",
        "ホテル予約",
        "海外旅行保険加入",
        "サグラダ・ファミリア予約（Year1）",
        "バチカン美術館予約（Year1）",
        "カッパドキア熱気球予約（Year2）",
        "ユーロ・トルコリラ・クロアチアクーナ両替",
        "スーツケース・機内持ち込みバッグ準備",
        "海外対応クレジットカード確認",
    ],
    "👗 持ち物": [
        "パスポート・コピー",
        "航空券・ホテル予約確認書（印刷）",
        "旅行保険証書",
        "常備薬・胃薬",
        "日焼け止め（SPF50以上）",
        "歩きやすいスニーカー",
        "ドレスアップ用の服（オペラ・ディナー用）",
        "水着・サンダル（ビーチ・船）",
        "モバイルバッテリー",
        "変換プラグ（ヨーロッパ用Cタイプ）",
        "カメラ・SDカード予備",
    ],
    "📱 アプリ": [
        "Google翻訳（オフライン辞書DL）",
        "Google マップ（オフライン地図DL）",
        "Booking.com / Airbnb",
        "Rome2Rio（交通検索）",
        "XE（為替レート）",
        "Whatsapp（現地連絡用）",
    ],
}

BUDGET = {
    "🔴 Year 1（スペイン・フランス・イタリア）": {
        "✈️ 航空券（往復）":    230000,
        "🏨 ホテル（13泊・1人分）": 160000,
        "🍽️ 食費":           130000,
        "🎟️ 観光・入場料":      55000,
        "🚆 域内交通":          45000,
        "🎁 お土産・旅行保険・雑費": 45000,
    },
    "🔵 Year 2（トルコ・ギリシャ）": {
        "✈️ 航空券（往復）":    160000,
        "🏨 ホテル（11泊・1人分）": 130000,
        "🍽️ 食費":           100000,
        "🎟️ 観光・入場料（熱気球含む）": 80000,
        "🚆 域内交通":          40000,
        "🎁 お土産・旅行保険・雑費": 35000,
    },
    "🟢 Year 3（中欧・クロアチア）": {
        "✈️ 航空券（往復）":    210000,
        "🏨 ホテル（13泊・1人分）": 145000,
        "🍽️ 食費":           115000,
        "🎟️ 観光・入場料":      50000,
        "🚆 域内交通":          45000,
        "🎁 お土産・旅行保険・雑費": 45000,
    },
}

BUDGET_NOTES = {
    "🔴 Year 1（スペイン・フランス・イタリア）": {
        "✈️ 航空券（往復）":    "GWはピーク運賃。1年前早期予約で¥180,000〜、直前は¥300,000超も。カタール/エミレーツ航空経由が多い",
        "🏨 ホテル（13泊・1人分）": "3〜4つ星ホテル2人部屋の1人分。パリ・ヴェネツィアは€170〜200/泊と高め",
        "🍽️ 食費":           "朝€8+昼€15+夕€40の想定。現地カフェ・市場活用で節約可能",
        "🎟️ 観光・入場料":      "サグラダ・ファミリア€26、バチカン€30、コロッセオ€18、ルーブル€22など",
        "🚆 域内交通":          "バルセロナ→パリ€80・パリ→ローマ€100・ローマ→ヴェネツィア新幹線€50+各都市内交通",
        "🎁 お土産・旅行保険・雑費": "海外旅行保険¥15,000+お土産¥20,000+現地雑費¥10,000",
    },
    "🔵 Year 2（トルコ・ギリシャ）": {
        "✈️ 航空券（往復）":    "SW（9月）はGWより安い。トルコ航空直行便¥130,000〜¥180,000が目安",
        "🏨 ホテル（11泊・1人分）": "サントリーニが高め（€200〜250/泊）。洞窟ホテルもプレミアム価格€120〜150/泊",
        "🍽️ 食費":           "トルコは安い（€30〜40/日）。サントリーニは観光地価格で€60〜70/日",
        "🎟️ 観光・入場料（熱気球含む）": "熱気球¥29,000が最大の出費。カタマランクルーズ€80、遺跡入場料合計€80程度",
        "🚆 域内交通":          "国内線3本（イスタンブール→カッパドキア・カッパドキア→アテネ・アテネ→サントリーニ）合計€250程度",
        "🎁 お土産・旅行保険・雑費": "海外旅行保険¥12,000+絨毯・陶器などトルコみやげ多め+雑費",
    },
    "🟢 Year 3（中欧・クロアチア）": {
        "✈️ 航空券（往復）":    "GW。KLM成田→アムステルダム直行便¥190,000〜¥250,000。早期予約推奨",
        "🏨 ホテル（13泊・1人分）": "プラハが安い（€80〜90/泊）。ドゥブロヴニクは観光地で高め（€150〜160/泊）",
        "🍽️ 食費":           "プラハは€30/日と格安。アムステルダム・ウィーン・ドゥブロヴニクは€55〜65/日",
        "🎟️ 観光・入場料":      "キューケンホフ€20、ゴッホ美術館€22、シェーンブルン€20、城壁ウォーク€35など",
        "🚆 域内交通":          "アムステルダム→プラハ€90・プラハ→ウィーン電車€40・ウィーン→ドゥブロヴニク€120+各都市内交通",
        "🎁 お土産・旅行保険・雑費": "海外旅行保険¥15,000+お土産¥20,000+現地雑費¥10,000",
    },
}

BUDGET_SAVINGS = {
    "🔴 Year 1（スペイン・フランス・イタリア）": [
        "航空券は1年前購入で¥50,000〜¥70,000節約可能",
        "ホテルをAirbnbにすると30〜40%削減",
        "ローマ→ヴェネツィアは新幹線の早割（Italo/Trenitalia）が格安",
        "ランチはバルのタパス・ピッツァで€10以下に抑えられる",
    ],
    "🔵 Year 2（トルコ・ギリシャ）": [
        "SW（9月）はGWより航空券が¥50,000〜¥70,000安い",
        "サントリーニはフィラ泊よりイア以外の場所で宿泊すると半額以下も",
        "熱気球は代理店より現地直接予約が安い場合あり",
        "アテネ→サントリーニはフェリー（€40）が飛行機より格安",
    ],
    "🟢 Year 3（中欧・クロアチア）": [
        "プラハは物価が安く、1日€30で十分食べられる",
        "ウィーンのオペラ立見席は€5〜10で本場の雰囲気を体験できる",
        "アムステルダムは自転車レンタル（€15/日）で交通費を大幅削減",
        "キューケンホフは事前オンライン購入で€2〜3割引",
    ],
}

def make_map(trip_data, color_map={"red": "#e74c3c", "blue": "#2980b9", "green": "#27ae60"}):
    cities = trip_data["cities"]
    center_lat = sum(c["lat"] for c in cities) / len(cities)
    center_lng = sum(c["lng"] for c in cities) / len(cities)
    m = folium.Map(location=[center_lat, center_lng], zoom_start=5, tiles="CartoDB positron")
    color = color_map.get(trip_data["color"], "#e74c3c")

    coords = [(c["lat"], c["lng"]) for c in cities]
    folium.PolyLine(coords, color=color, weight=3, opacity=0.8, dash_array="8").add_to(m)

    for i, city in enumerate(cities, 1):
        popup_html = f"""
        <div style='font-family:sans-serif;min-width:200px;'>
            <h4 style='margin:0 0 6px;color:#2c3e50;'>{city['name']}</h4>
            <b>📅 {city['stay']}</b>
            <ul style='margin:6px 0;padding-left:16px;font-size:13px;'>
                {''.join(f"<li>{s[1][:40]}…</li>" if len(s[1])>40 else f"<li>{s[1]}</li>" for s in city['itinerary'])}
            </ul>
            <div style='background:#fef9e7;padding:6px;border-radius:5px;font-size:11px;'>💡 {city['tip']}</div>
        </div>"""
        folium.Marker(
            [city["lat"], city["lng"]],
            popup=folium.Popup(popup_html, max_width=260),
            tooltip=f"{'①②③④'[i-1]} {city['name']} ({city['stay']})",
            icon=folium.Icon(color=trip_data["color"], icon="heart", prefix="fa"),
        ).add_to(m)
    return m

# ============================================================
# UI
# ============================================================
st.markdown("""
<div class="hero-header">
    <div class="main-title">💑 ハネムーン旅行プランナー</div>
    <div class="sub-title">3 Years Plan · Europe · Turkey · Greece</div>
</div>
""", unsafe_allow_html=True)

trip_name = st.sidebar.selectbox("🗓️ 旅行を選択", list(TRIPS.keys()))
trip = TRIPS[trip_name]

st.sidebar.markdown(f"""
---
**🌤️ 季節:** {trip['season']}
**📅 日数:** {trip['days']}日間
**🏙️ 都市数:** {len(trip['cities'])}都市
""")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["🗺️ マップ", "📅 しおり", "🍽️ グルメ", "🚗 移動", "✅ 準備 & 予算"])

# ── Tab1: マップ ──
with tab1:
    st.subheader(f"📍 ルートマップ — {trip_name}")
    m = make_map(trip)
    st_folium(m, width=None, height=500)

# ── Tab2: しおり ──
with tab2:
    st.subheader("📅 日程しおり")
    city_names = [c["name"] for c in trip["cities"]]
    selected_city = st.selectbox("都市を選択", city_names)
    city = next(c for c in trip["cities"] if c["name"] == selected_city)

    st.markdown(f'<div class="city-card"><b style="color:#C9974C;font-family:Playfair Display,serif;font-size:1.1rem;">{city["name"]}</b><span style="color:#718096;font-size:0.88rem;margin-left:10px;">📅 {city["stay"]}</span></div>', unsafe_allow_html=True)
    for day, plan in city["itinerary"]:
        with st.expander(f"📌 {day}", expanded=True):
            st.write(plan)
    st.markdown(f'<div class="tip-box">💡 <b style="color:#4A8063;">現地のコツ：</b> {city["tip"]}</div>', unsafe_allow_html=True)

# ── Tab3: グルメ ──
with tab3:
    st.subheader("🍽️ グルメガイド")
    city_names = [c["name"] for c in trip["cities"]]
    selected_city = st.selectbox("都市を選択", city_names, key="food_city")
    city = next(c for c in trip["cities"] if c["name"] == selected_city)

    st.markdown(f"**{city['name']} のおすすめグルメ**")
    for dish, desc in city["food"]:
        st.markdown(f'<div class="food-card"><b style="color:#D96B5A;font-size:1rem;">🍴 {dish}</b><br><span style="font-size:0.88rem;color:#4A5568;margin-top:4px;display:block;">{desc}</span></div>', unsafe_allow_html=True)

# ── Tab4: 移動 ──
with tab4:
    st.subheader("🚗 移動・交通情報")
    for city in trip["cities"]:
        st.markdown(f'<div class="move-card"><b style="color:#4A7FB5;font-size:1rem;">📍 {city["name"]}</b><br><span style="color:#4A5568;font-size:0.88rem;margin-top:4px;display:block;">{city["move_next"]}</span></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("**✈️ 東京からの直行便**")
    data = {
        "路線": ["成田→イスタンブール", "成田→アムステルダム", "成田→バルセロナ（経由）", "成田→パリ（経由）"],
        "所要時間": ["約12時間", "約11時間", "約13〜16時間", "約12〜14時間"],
        "航空会社": ["トルコ航空", "KLM", "カタール航空/エミレーツ等", "Air France/JAL等"],
        "目安運賃(往復)": ["¥80,000〜150,000", "¥90,000〜160,000", "¥100,000〜170,000", "¥90,000〜160,000"],
    }
    st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

# ── Tab5: チェックリスト & 予算 ──
with tab5:
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("✅ 旅行準備チェックリスト")
        for category, items in CHECKLIST.items():
            st.markdown(f"**{category}**")
            for item in items:
                st.checkbox(item, key=f"check_{item}")

    with col2:
        st.subheader("💰 予算シミュレーター（1人あたり）")
        selected_trip = st.selectbox("旅行を選択", list(BUDGET.keys()), key="budget_trip")

        state_key = f"budget_loaded_{selected_trip}"
        if state_key not in st.session_state:
            st.session_state[state_key] = None

        st.markdown(
            '<a href="https://docs.google.com/spreadsheets/d/1eG_r-ylF9xc40sg717ZBxBQ9-zrPoMpTi32vovSCfZ4/edit" '
            'target="_blank" class="sheets-link">📊 Google スプレッドシートを開く →</a>',
            unsafe_allow_html=True,
        )
        st.markdown("<br>", unsafe_allow_html=True)

        bc1, bc2 = st.columns(2)
        with bc1:
            if st.button("📥 Sheetsから読み込む", use_container_width=True):
                with st.spinner("読み込み中..."):
                    loaded, last_update = load_budget_from_sheets(selected_trip)
                if loaded:
                    st.session_state[state_key] = loaded
                    st.success(f"読み込み完了（最終保存: {last_update}）")
                else:
                    st.warning("Sheetsにデータがありません")

        base = st.session_state[state_key] or BUDGET[selected_trip]
        notes = BUDGET_NOTES.get(selected_trip, {})
        total = 0
        new_budget = {}
        for item, default in BUDGET[selected_trip].items():
            val = st.number_input(
                f"{item}",
                value=int(base.get(item, default)),
                step=5000,
                key=f"budget_{selected_trip}_{item}",
                help=notes.get(item, ""),
            )
            new_budget[item] = val
            total += val

        with bc2:
            if st.button("📤 Sheetsに保存", use_container_width=True, type="primary"):
                with st.spinner("保存中..."):
                    saved_at = save_budget_to_sheets(selected_trip, new_budget)
                st.success(f"保存完了 ✅（{saved_at}）")
                st.session_state[state_key] = new_budget

        st.markdown("---")
        default_total = sum(BUDGET[selected_trip].values())
        diff = total - default_total
        diff_str = f"（目安比 {'＋' if diff >= 0 else '－'}¥{abs(diff):,}）" if diff != 0 else "（目安通り）"
        st.markdown(
            f'<div class="budget-box">'
            f'<p style="color:#C9974C;font-size:0.75rem;letter-spacing:3px;text-transform:uppercase;margin:0 0 6px;">1人あたり合計</p>'
            f'<h2 style="color:white;margin:0;font-family:Playfair Display,serif;font-size:2.2rem;">¥{total:,}</h2>'
            f'<p style="color:rgba(255,255,255,0.6);margin:6px 0 4px;font-size:0.85rem;">2人合計 ¥{total*2:,}</p>'
            f'<p style="color:rgba(201,151,76,0.85);font-size:0.8rem;margin:0;">{diff_str}</p>'
            f'</div>',
            unsafe_allow_html=True,
        )

        st.markdown("---")
        st.markdown("**📊 内訳グラフ**")
        clean_labels = {k: k.split(" ", 1)[-1] for k in new_budget}
        df = pd.DataFrame({"項目": list(clean_labels.values()), "金額": list(new_budget.values())})
        st.bar_chart(df.set_index("項目"))

        st.markdown("---")
        st.markdown("**💡 節約のコツ**")
        for tip in BUDGET_SAVINGS.get(selected_trip, []):
            st.markdown(f'<div class="tip-box" style="margin-bottom:8px;">💡 {tip}</div>', unsafe_allow_html=True)
