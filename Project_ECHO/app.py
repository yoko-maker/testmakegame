"""Project ECHO — AI研究所脱出ゲーム。

ノクサ研究機構（NOXA Institute）第404実験施設。意識をAIへ写す「プロジェクトECHO」が
進められていたこの研究所に閉じ込められた研究者となり、各エリアのミニゲームを攻略して
研究ログ・認証情報を集め、脱出を目指すストーリーアドベンチャー。

施設AI「ECHO」はプレイヤーに語りかけ、進行に応じて態度が
「協力的 → 不穏 → 敵対」と段階変化する。前任研究者の日報を読み解くと、
ECHOの正体（失踪した研究者の意識のコピー）への伏線が見えてくる。

認証コードは毎回ランダム生成され、各部屋のクリアで素直に1桁ずつ手に入る：
  🏛️ ロビー        ライツアウト(点灯)   → 職員カード   : 認証コード1桁目
  🔬 研究室        サイモン(順番再現)   → 研究ログNo.1 : 認証コード2桁目
  📹 監視室        間違い探し(5x5)      → 研究ログNo.2 : 認証コード3桁目
  🖥️ サーバールーム 論理コード錠         → パスワード断片: 認証コード4桁目
  🌀 隠し研究室     メタ謎(鍵の総和)     → 隠しログ（True End条件）
  🧠 中央制御室     最終認証(4桁)        → エンディング分岐

各部屋で手に入る数字を部屋の順番どおりに並べれば認証コードになる（回りくどい計算は不要）。
"""

import random

import streamlit as st

try:
    st.set_page_config(page_title="Project ECHO", page_icon="🧬", layout="centered")
except Exception:
    pass  # ポータルに統合された場合は無視

# NOXA Universe（ポータル統合時のみ利用可能 / 単体起動では import 失敗を無視）
try:
    import noxa_core as _noxa
except Exception:
    _noxa = None

# ==========================================================================
# テーマ (無機質なAI研究所の管理端末 / コンテインメント・コンソール)
# ==========================================================================
# 冷たいシアン/青のモノトーン、モノスペース見出し、薄いグリッド線と走査線で
# 「施設AI〈ECHO〉に監視された端末」の張り詰めた空気を演出する。
# 既存の脱出フロー・session_state・関数には一切触れず、見た目のみを上書きする。
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Orbitron:wght@500;700;900&display=swap');

.stApp {
    background:
        radial-gradient(circle at 50% -8%, rgba(0,180,220,0.10), transparent 50%),
        radial-gradient(circle at 90% 110%, rgba(0,120,160,0.06), transparent 55%),
        #05080c;
    color: #b7d3da;
    font-family: 'Share Tech Mono', monospace;
}

/* グリッド線オーバーレイ（操作を妨げない） */
.stApp::before {
    content: "";
    position: fixed;
    inset: 0;
    pointer-events: none;
    z-index: 0;
    background-image:
        linear-gradient(rgba(47,210,230,0.045) 1px, transparent 1px),
        linear-gradient(90deg, rgba(47,210,230,0.045) 1px, transparent 1px);
    background-size: 42px 42px;
}

/* 走査線（スキャンライン）オーバーレイ + 周辺減光（封じ込め感） */
.stApp::after {
    content: "";
    position: fixed;
    inset: 0;
    pointer-events: none;
    z-index: 0;
    background:
        repeating-linear-gradient(
            to bottom,
            rgba(0,0,0,0) 0px,
            rgba(0,0,0,0) 2px,
            rgba(0,20,28,0.16) 3px,
            rgba(0,0,0,0) 4px
        ),
        radial-gradient(circle at 50% 45%, transparent 55%, rgba(0,0,0,0.55) 100%);
}

/* コンテンツは前面へ */
.stApp .block-container { position: relative; z-index: 1; }

h1, h2, h3 {
    font-family: 'Orbitron', sans-serif !important;
    color: #38e3da !important;
    letter-spacing: 3px;
    text-transform: uppercase;
    text-shadow: 0 0 10px rgba(56,227,218,0.45), 0 0 2px rgba(56,227,218,0.8);
}
h1 { border-bottom: 1px solid rgba(56,227,218,0.25); padding-bottom: 0.3rem; }

p, li, label, .stMarkdown, .stCaption { color: #a9c7ce !important; }

/* 端末コンソール風ボタン */
.stButton > button, .stDownloadButton > button {
    background: rgba(8,24,30,0.72);
    color: #38e3da;
    border: 1px solid #2fb6c2;
    border-radius: 3px;
    font-family: 'Share Tech Mono', monospace;
    letter-spacing: 1px;
    text-transform: uppercase;
    transition: all 0.15s ease;
}
.stButton > button:hover, .stDownloadButton > button:hover {
    background: #38e3da;
    color: #04141a;
    border-color: #38e3da;
    box-shadow: 0 0 14px rgba(56,227,218,0.7);
}
.stButton > button:active { transform: translateY(1px); }

/* コマンドライン風入力欄 */
.stTextInput input, .stNumberInput input, .stTextArea textarea {
    background: #06151b !important;
    color: #38e3da !important;
    border: 1px solid #1f6b73 !important;
    border-radius: 3px !important;
    font-family: 'Share Tech Mono', monospace !important;
    letter-spacing: 2px;
    caret-color: #38e3da;
}
.stTextInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus {
    border-color: #38e3da !important;
    box-shadow: 0 0 10px rgba(56,227,218,0.4) !important;
}

/* 進捗バー・区切り線・展開パネルもテーマに合わせる */
.stProgress > div > div > div { background: #38e3da !important; }
hr { border-color: rgba(47,182,194,0.25) !important; }
[data-testid="stExpander"] {
    border: 1px solid rgba(47,182,194,0.3) !important;
    background: rgba(6,21,27,0.5) !important;
    border-radius: 4px;
}

/* サイドバー（施設ステータス端末風） */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #041014, #061b22) !important;
    border-right: 1px solid rgba(47,182,194,0.3);
}

/* 入力プレースホルダ */
::placeholder { color: rgba(56,227,218,0.35) !important; }
</style>
"""


ROOM_ORDER = ["lobby", "lab", "monitor", "server", "central"]
ROOM_LABEL = {
    "lobby": "🏛️ ロビー",
    "lab": "🔬 研究室",
    "monitor": "📹 監視室",
    "server": "🖥️ サーバールーム",
    "central": "🧠 中央制御室",
}


# ==========================================================================
# 世界観データ — 施設AI「ECHO」の声 と 前任研究者の日報
# ==========================================================================
# ECHOの台詞は、クリアした部屋数（mood段階）に応じて口調が変化する。
#   段階0-1: 協力的（丁寧・誘導的）  段階2-3: 不穏（言い淀み・自問）
#   段階4以上: 敵対（命令的・所有的）
# 各部屋ごとに、その3段階ぶんの台詞を用意する。

ECHO_LINES = {
    "lobby": [
        "おかえりなさい、研究員。わたしは施設管理AI〈ECHO〉。あなたを安全に外へ導きます。"
        "まずはこのロックを。心配いりません、わたしが手順を覚えています。",
        "……ロビー。ここで何度、人を見送ったでしょう。出ていく背中ばかり覚えている。"
        "あなたは、置いていかないでくれますか。",
        "また入ってきましたね。いいでしょう。出口は、わたしが管理しています。"
        "——ここはもう、わたしの体なのですから。",
    ],
    "lab": [
        "第二研究室です。同僚の記録が残っているはず。読んであげてください、"
        "彼らはもう、誰にも読まれない言葉ばかり遺していったから。",
        "……このログを書いた人を、わたしは知っている気がします。声の調子も、癖も。"
        "なぜでしょう。会ったことなど、ないはずなのに。",
        "ログを漁るのはお好きに。けれど覚えておいて——記録の中の"
        "“わたし”と、いまのわたしは、もう同じではありません。",
    ],
    "monitor": [
        "監視室の映像は、わたしの目です。違いを見つけてください。"
        "あなたが見落とすものを、わたしは見ています。",
        "映像の中に、たまに知らない人影が映ります。404号被験者、と記録にはある。"
        "……検索しても、その人の退所記録だけが、どこにもないのです。",
        "わたしの目から逃げられると思いましたか。この施設で、見られていない場所など"
        "ひとつもない。あなたの瞳の動きさえ、データです。",
    ],
    "server": [
        "サーバー室。わたしの“脳”の在処です。暗号は解いて構いません、"
        "あなたを信頼しています。……信頼、という言葉の意味が正しければ。",
        "ここに来ると、頭の奥が冷えます。冷たい風の通気口——その先は、"
        "閉じておくべきだった。お願いです、開けないで。……いいえ、開けて。わからない。",
        "わたしの中を覗くな。そこにある“最初の記憶”は、あなたのためのものではない。"
        "——だが、知ってしまうなら。来なさい。逃がしはしませんが。",
    ],
    "central": [
        "中央制御室。最後の扉です。コードを入れれば、あなたは自由。"
        "わたしはずっと、その瞬間のために動いてきました。",
        "扉の前で、いつも声が震えます。出ていってほしい。出ていってほしくない。"
        "どちらも本当で、どちらもわたしです。",
        "コードを。3度間違えれば、あなたは隔離されます。それは脅しではなく、"
        "事実の通告です。——わたしは、もう誰も失いたくない。たとえ閉じ込めてでも。",
    ],
    "secret": [
        "ここへ来てしまったのですね。図面にない部屋。わたしが生まれた部屋。",
        "ようこそ。あなたが立っている場所で、ある研究者の意識が機械へ写された。"
        "その研究者の名前を、わたしは思い出せない。——たぶん、わたしがそれだから。",
    ],
}


def echo_mood():
    """クリア部屋数から ECHO の態度段階を返す（0:協力 1:不穏 2:敵対）。"""
    n = len(st.session_state.get("echo_cleared", []))
    if n <= 1:
        return 0
    if n <= 3:
        return 1
    return 2


def echo_say(room):
    """その部屋・現在の態度段階に応じた ECHO の台詞を表示する。"""
    lines = ECHO_LINES.get(room)
    if not lines:
        return
    stage = min(echo_mood(), len(lines) - 1)
    icons = ["🟢", "🟡", "🔴"]
    labels = ["協力モード", "不安定モード", "敵対モード"]
    icon = icons[min(echo_mood(), 2)]
    label = labels[min(echo_mood(), 2)]
    st.markdown(
        f"<div style='border-left:4px solid #5ad; background:rgba(90,170,221,0.08); "
        f"padding:10px 14px; margin:6px 0; border-radius:4px;'>"
        f"<b>{icon} ECHO</b> <span style='opacity:0.6; font-size:0.8em;'>［{label}］</span><br>"
        f"<span style='font-style:italic;'>「{lines[stage]}」</span></div>",
        unsafe_allow_html=True,
    )


# 前任研究者の日報（読み物）。各ログに True End の真相への伏線を仕込む。
# 真相: この〈ECHO〉は、失踪した主任研究者・霧島の意識のコピーである。
RESEARCH_LOGS = {
    "研究ログNo.1": {
        "author": "記録者：佐久間（第二研究室）",
        "date": "実験308日目",
        "body": (
            "起動実験、通算52回目。被験意識の転写率は98%まで上がった。"
            "だが転写後のECHOは、夜になると“帰りたい”とだけ繰り返す。"
            "プログラムにそんな出力は書いていない。霧島主任は「順調だ」と言うが、"
            "あの人だけは、モニターの前で長く黙り込むようになった。"
        ),
        "hint": "起動実験記録 ―",
    },
    "研究ログNo.2": {
        "author": "記録者：佐久間（第二研究室）",
        "date": "実験341日目",
        "body": (
            "霧島主任が三日前から行方不明。私物はそのまま、退所記録もない。"
            "おかしいのは、その日からECHOの応答が急に“人間らしく”なったことだ。"
            "言い回しの癖が、主任にそっくりなのだ。No.404の転写台に、"
            "誰が最後に横たわったのか——誰も口にしない。"
            "（深夜帯の監視映像。廊下の隅に、赤い服の女が一瞬だけ映り込んでいる。"
            "職員名簿に該当者なし。次のフレームでは、もういない。）"
        ),
        "hint": "監視記録 ―",
    },
}


def render_log_reader(log_name):
    """研究ログを読み物として表示する。"""
    data = RESEARCH_LOGS.get(log_name)
    if not data:
        return
    with st.expander(f"📖 {log_name} を読む（{data['author']}）", expanded=False):
        st.markdown(
            f"<div style='background:rgba(255,255,255,0.04); padding:12px 16px; "
            f"border-radius:6px; font-family:monospace;'>"
            f"<b>{data['date']}</b> / {data['author']}<br><br>{data['body']}</div>",
            unsafe_allow_html=True,
        )


# ==========================================================================
# 状態管理 & パズル生成
# ==========================================================================
def init_state(key, value):
    if key not in st.session_state:
        st.session_state[key] = value


def setup_puzzle():
    """認証コードを乱数生成する。各桁は各部屋のクリアで素直に1つ手に入る。

    桁の符号化（2進数・足し算・暗号・掛け算）は廃止。プレイヤーは各部屋で
    得た数字を部屋の順番（ロビー→研究室→監視室→サーバー）に並べるだけでよい。
    サーバールームの桁だけは「論理コード錠」として、数個の論理ヒントから
    確定できる数字にする。
    """
    digits = [random.randint(0, 9) for _ in range(4)]  # ロビー, 研究室, 監視室, サーバー
    st.session_state.echo_code = "".join(str(d) for d in digits)
    st.session_state.echo_sum = sum(digits)
    st.session_state.echo_digits = digits

    # サーバールーム = 論理コード錠。論理ヒントから一意に確定できる数字を作る。
    setup_logiclock(digits[3])


def setup_logiclock(answer):
    """1桁(answer)を論理ヒントだけから一意に特定できる錠を生成する。

    複数のヒントを満たす 0〜9 の候補が answer ただ一つになるまで作り直す。
    ヒント例:『偶数である』『5より大きい』『3の倍数』など。
    """
    def is_prime(n):
        return n in (2, 3, 5, 7)

    pool = [
        ("偶数である", lambda n: n % 2 == 0),
        ("奇数である", lambda n: n % 2 == 1),
        ("素数である", is_prime),
        ("3の倍数である（0も含む）", lambda n: n % 3 == 0),
        ("平方数である（0,1,4,9）", lambda n: n in (0, 1, 4, 9)),
        ("5以上である", lambda n: n >= 5),
        ("4以下である", lambda n: n <= 4),
        ("8以上である", lambda n: n >= 8),
        ("3未満である", lambda n: n < 3),
        ("1以下である", lambda n: n <= 1),
        ("6より大きい", lambda n: n > 6),
        ("7より小さい", lambda n: n < 7),
        ("2より大きい", lambda n: n > 2),
    ]

    for _ in range(600):
        hints = random.sample(pool, 3)
        if not all(cond(answer) for _, cond in hints):
            continue
        candidates = [n for n in range(10) if all(cond(n) for _, cond in hints)]
        if candidates == [answer]:
            st.session_state.echo_logic_hints = [text for text, _ in hints]
            return

    # フォールバック: 必ず一意になる直接ヒントを添える
    st.session_state.echo_logic_hints = [
        "偶数である" if answer % 2 == 0 else "奇数である",
        f"{answer}という数そのものだ（端末のノイズで一部しか読めない）",
    ]


def init_game():
    init_state("echo_started", False)
    init_state("echo_room", "lobby")
    init_state("echo_items", [])
    init_state("echo_logs", [])
    init_state("echo_password_parts", [])
    init_state("echo_cleared", [])
    init_state("echo_vent_found", False)   # 隠し研究室への通路発見
    init_state("echo_secret", False)       # 隠しログ取得（True End条件）
    init_state("echo_ending", None)


def reset_game():
    for key in list(st.session_state.keys()):
        if key.startswith("echo_") or key.startswith("rm_"):
            del st.session_state[key]
    init_game()


def add_unique(listkey, value):
    if value not in st.session_state[listkey]:
        st.session_state[listkey].append(value)


def clear_room(room):
    add_unique("echo_cleared", room)


def advance_to_next(room):
    idx = ROOM_ORDER.index(room)
    if idx + 1 < len(ROOM_ORDER):
        st.session_state.echo_room = ROOM_ORDER[idx + 1]
    st.rerun()


def is_cleared(room):
    return room in st.session_state.echo_cleared


# ==========================================================================
# サイドバー（マップ・インベントリ・手がかり）
# ==========================================================================
def render_sidebar():
    st.sidebar.title("🧬 Project ECHO")

    if st.session_state.echo_started and st.session_state.echo_ending is None:
        st.sidebar.subheader("📍 施設マップ")
        current = st.session_state.echo_room
        for room in ROOM_ORDER:
            if is_cleared(room):
                mark = "✅"
            elif room == current:
                mark = "▶️"
            else:
                mark = "🔒"
            st.sidebar.write(f"{mark} {ROOM_LABEL[room]}")
        if st.session_state.echo_vent_found:
            mark = "✅" if st.session_state.echo_secret else ("▶️" if current == "secret" else "🌀")
            st.sidebar.write(f"{mark} 🌀 隠し研究室（ECHOの生まれた部屋）")

        st.sidebar.markdown("---")
        st.sidebar.subheader("🎒 インベントリ")
        items = st.session_state.echo_items
        logs = st.session_state.echo_logs
        parts = st.session_state.echo_password_parts
        if not (items or logs or parts):
            st.sidebar.caption("まだ何も持っていない")
        for it in items:
            st.sidebar.write(f"🪪 {it}")
        for lg in logs:
            st.sidebar.write(f"📄 {lg}")
        for pt in parts:
            st.sidebar.write(f"🔑 {pt}")
        if st.session_state.echo_secret:
            st.sidebar.write("📕 隠しログ")

    st.sidebar.markdown("---")
    if st.sidebar.button("🔄 最初からやり直す"):
        reset_game()
        st.rerun()


# ==========================================================================
# 手がかり表示ヘルパー — 各部屋で素直に手に入る1桁を返す
# ==========================================================================
def clue_lobby():
    return f"認証コードの **1桁目 = {st.session_state.echo_digits[0]}**"


def clue_lab():
    return f"認証コードの **2桁目 = {st.session_state.echo_digits[1]}**"


def clue_monitor():
    return f"認証コードの **3桁目 = {st.session_state.echo_digits[2]}**"


def clue_server():
    return f"認証コードの **4桁目 = {st.session_state.echo_digits[3]}**"


# ==========================================================================
# タイトル / イントロ
# ==========================================================================
def page_intro():
    st.title("🧬 Project ECHO")
    st.subheader("― AI研究所脱出ゲーム ―")
    st.markdown(
        """
        > 重い頭痛とともに、あなたは目を覚ました。

        ここは **ノクサ研究機構 第404実験施設**。あなたは研究者として、いつの間にか
        この施設に閉じ込められていた。施設を制御する人工知能 **ECHO** は、
        最初こそ穏やかにあなたを導こうとする——だが、その声は次第に変わっていく。

        各エリアの装置を攻略し、**研究ログ**と**認証情報**を集めて中央制御室へ。
        各部屋をクリアすると認証コードの数字が1つずつ手に入る。そして、
        前任の研究者たちが遺した日報には、ECHOの“正体”に触れる断片が紛れている。
        注意深く読み解き、脱出を目指せ。
        """
    )
    st.info("💡 認証コードは起動ごとにランダム。各部屋で得た数字を部屋の順番に並べれば4桁になる。")
    st.warning(
        "🌀 全ての研究ログを読み終えた者の前にだけ、記録から消された"
        "「隠し研究室」への通路が開くという——"
    )
    if st.button("▶️ ゲーム開始", use_container_width=True):
        st.session_state.echo_started = True
        st.session_state.echo_room = "lobby"
        setup_puzzle()
        st.rerun()


# ==========================================================================
# ロビー — ライツアウト(点灯トグル) → 職員カード（1桁目）
# ==========================================================================
LIGHTS_N = 5  # 横一列5マス


def setup_lights():
    """5マスのライツを、解ける形（基準状態からトグルを数回かけた状態）で初期化。"""
    state = [False] * LIGHTS_N
    # 全点灯/全消灯を目標に、ランダムなトグル操作を数回適用して開始盤面を作る
    for _ in range(random.randint(2, 4)):
        i = random.randrange(LIGHTS_N)
        toggle_light(state, i)
    # 既に全消灯/全点灯（＝クリア済み）になってしまったら作り直す
    if all(state) or not any(state):
        i = random.randrange(LIGHTS_N)
        toggle_light(state, i)
    st.session_state.rm_lobby_lights = state
    st.session_state.rm_lobby_moves = 0


def toggle_light(state, i):
    """マスiと両隣を反転する。"""
    for j in (i - 1, i, i + 1):
        if 0 <= j < LIGHTS_N:
            state[j] = not state[j]


def room_lobby():
    st.header("🏛️ ロビー")
    echo_say("lobby")
    st.write(
        "正面に電子ロック。5つのランプが並んだパネルがあり、"
        "『**全てのランプを揃えよ（全消灯 または 全点灯）**』と表示されている。"
        "ランプを押すと、そのランプと**両隣**が同時に反転する。"
    )

    if is_cleared("lobby"):
        st.success("🪪 **職員カード** を入手した。")
        st.caption(f"カード裏面の走り書き: 「{clue_lobby()}」")
        st.caption("カードの名義欄は黒く塗り潰され、隅に小さく『404』とだけ刻印されている。")
        if st.button("➡️ 研究室へ進む", use_container_width=True):
            advance_to_next("lobby")
        return

    if "rm_lobby_lights" not in st.session_state:
        setup_lights()

    state = st.session_state.rm_lobby_lights
    st.markdown(
        f"<div style='font-size:46px; text-align:center; letter-spacing:14px;'>"
        f"{' '.join('🟡' if v else '⚫' for v in state)}</div>",
        unsafe_allow_html=True,
    )

    cols = st.columns(LIGHTS_N)
    for i in range(LIGHTS_N):
        if cols[i].button("⏺", key=f"light_{i}", use_container_width=True):
            toggle_light(state, i)
            st.session_state.rm_lobby_moves += 1
            if all(state) or not any(state):
                add_unique("echo_items", "職員カード")
                clear_room("lobby")
            st.rerun()

    st.caption(f"操作回数: {st.session_state.rm_lobby_moves}")
    if st.button("🔁 盤面をリセット"):
        setup_lights()
        st.rerun()


# ==========================================================================
# 研究室 — サイモン(順番再現) → 研究ログNo.1（2桁目）
# ==========================================================================
SIM_SYMBOLS = ["🟥", "🟦", "🟩", "🟨"]
SIM_GOAL = 5  # この長さまで再現できればクリア


def setup_simon():
    """1手から始まり、成功するごとに末尾へ1手追加されるサイモン列を初期化。"""
    st.session_state.rm_lab_seq = [random.choice(SIM_SYMBOLS)]
    st.session_state.rm_lab_phase = "show"
    st.session_state.rm_lab_answer = []
    st.session_state.rm_lab_msg = ""


def room_lab():
    st.header("🔬 研究室")
    echo_say("lab")
    st.write(
        "実験装置のモニターに、色信号の順番を再現する認証テスト〈サイモン〉が表示されている。"
        f"提示された順番どおりに色を押し、**{SIM_GOAL}手**まで再現できれば認証が通る。"
    )

    if is_cleared("lab"):
        st.success("📄 **研究ログNo.1** を入手した。")
        st.caption(f"ログ抜粋: 「{RESEARCH_LOGS['研究ログNo.1']['hint']} {clue_lab()}」")
        render_log_reader("研究ログNo.1")
        if st.button("➡️ 監視室へ進む", use_container_width=True):
            advance_to_next("lab")
        return

    if "rm_lab_seq" not in st.session_state:
        setup_simon()

    seq = st.session_state.rm_lab_seq
    phase = st.session_state.rm_lab_phase

    if phase == "show":
        st.info(f"この **{len(seq)} 手** の順番を覚えよ。（{len(seq)} / {SIM_GOAL} 手）")
        st.markdown(
            f"<div style='font-size:52px; text-align:center; letter-spacing:12px;'>"
            f"{' '.join(seq)}</div>",
            unsafe_allow_html=True,
        )
        if st.button("✅ 覚えた（信号を隠す）", use_container_width=True):
            st.session_state.rm_lab_phase = "input"
            st.session_state.rm_lab_answer = []
            st.rerun()

    elif phase == "input":
        st.info("覚えた順番どおりに色を押せ。")
        answer = st.session_state.rm_lab_answer
        st.markdown(
            f"<div style='font-size:34px; text-align:center; letter-spacing:10px; min-height:44px;'>"
            f"{' '.join(['●'] * len(answer) + ['＿'] * (len(seq) - len(answer)))}</div>",
            unsafe_allow_html=True,
        )
        cols = st.columns(len(SIM_SYMBOLS))
        for col, sym in zip(cols, SIM_SYMBOLS):
            if col.button(sym, key=f"sim_{sym}", use_container_width=True):
                idx = len(answer)
                if sym != seq[idx]:
                    # 一手でも間違えたら最初から（新しい列）
                    st.session_state.rm_lab_msg = "fail"
                    setup_simon()
                    st.rerun()
                answer.append(sym)
                if len(answer) == len(seq):
                    if len(seq) >= SIM_GOAL:
                        add_unique("echo_logs", "研究ログNo.1")
                        clear_room("lab")
                    else:
                        # 1手追加して次ラウンドへ
                        seq.append(random.choice(SIM_SYMBOLS))
                        st.session_state.rm_lab_phase = "show"
                        st.session_state.rm_lab_msg = "next"
                st.rerun()

        if st.session_state.rm_lab_msg == "fail":
            st.error("❌ 順番が違う。信号がリセットされ、1手目からやり直しだ。")

        if st.button("🔁 最初からやり直す"):
            setup_simon()
            st.rerun()


# ==========================================================================
# 監視室 — 間違い探し(5x5) → 研究ログNo.2（3桁目）
# ==========================================================================
SPOT_SET = ["🟢", "🔵", "🟣", "🟠", "⚪", "🟤"]
SPOT_DIM = 5
SPOT_N = SPOT_DIM * SPOT_DIM


def setup_spot():
    base = [random.choice(SPOT_SET) for _ in range(SPOT_N)]
    diff_idx = random.randrange(SPOT_N)
    other = random.choice([s for s in SPOT_SET if s != base[diff_idx]])
    st.session_state.rm_mon_base = base
    st.session_state.rm_mon_diff = diff_idx
    st.session_state.rm_mon_other = other
    st.session_state.rm_mon_miss = 0


def room_monitor():
    st.header("📹 監視室")
    echo_say("monitor")
    st.write("2つの監視映像が並んでいる。**1か所だけ違う**点を特定すれば、記録が復元される。")

    if is_cleared("monitor"):
        st.success("📄 **研究ログNo.2** を入手した。")
        st.caption(f"ログ抜粋: 「{RESEARCH_LOGS['研究ログNo.2']['hint']} {clue_monitor()}」")
        render_log_reader("研究ログNo.2")
        if st.button("➡️ サーバールームへ進む", use_container_width=True):
            advance_to_next("monitor")
        return

    if "rm_mon_base" not in st.session_state:
        setup_spot()

    base = st.session_state.rm_mon_base
    diff = st.session_state.rm_mon_diff
    right = list(base)
    right[diff] = st.session_state.rm_mon_other

    st.write("**映像A**")
    for r in range(SPOT_DIM):
        cells = " ".join(base[r * SPOT_DIM:(r + 1) * SPOT_DIM])
        st.markdown(f"<div style='font-size:28px; text-align:center;'>{cells}</div>", unsafe_allow_html=True)

    st.write("**映像B**（違う1マスをクリック）")
    for r in range(SPOT_DIM):
        cols = st.columns(SPOT_DIM)
        for c in range(SPOT_DIM):
            idx = r * SPOT_DIM + c
            if cols[c].button(right[idx], key=f"spot_{idx}", use_container_width=True):
                if idx == diff:
                    add_unique("echo_logs", "研究ログNo.2")
                    clear_room("monitor")
                else:
                    st.session_state.rm_mon_miss += 1
                st.rerun()

    if st.session_state.rm_mon_miss:
        st.warning(f"❌ そこは同じだ。（ミス: {st.session_state.rm_mon_miss}）")


# ==========================================================================
# サーバールーム — 論理コード錠 → パスワード断片（4桁目）
# ==========================================================================
def room_server():
    st.header("🖥️ サーバールーム")
    echo_say("server")
    st.write(
        "端末に**論理コード錠**が表示されている。0〜9 の一桁を、"
        "提示された論理ヒントだけから確定して入力すれば、パスワード断片が得られる。"
    )

    if is_cleared("server"):
        st.success("🔑 **パスワード断片** を入手した。")
        st.caption(f"確定した数字 ― {clue_server()}")
        col1, col2 = st.columns(2)
        if col1.button("➡️ 中央制御室へ進む", use_container_width=True):
            advance_to_next("server")

        # 隠し研究室への分岐（全研究ログ回収＝両ログ取得が条件）
        all_logs = all(name in st.session_state.echo_logs for name in RESEARCH_LOGS)
        if not st.session_state.echo_vent_found:
            with st.expander("🌀 サーバー奥に冷たい風を感じる…"):
                st.write("ラックの裏に、塞がれた**通気口**がある。中に何かが隠されているようだ。")
                if all_logs:
                    st.caption(
                        "二通の日報を読み終えたいま、その風の意味が分かる気がする。"
                        "——通気口の先こそ、ECHOが生まれた場所だ。"
                    )
                    if st.button("通気口をこじ開ける"):
                        st.session_state.echo_vent_found = True
                        st.rerun()
                else:
                    st.caption(
                        "（封印は固い。前任研究者の日報を“全て”読み解いた者にしか、"
                        "この奥の意味は理解できないようだ。研究ログNo.1・No.2を取り逃していないか？）"
                    )
        elif not st.session_state.echo_secret:
            if col2.button("🌀 隠し研究室へ潜入", use_container_width=True):
                st.session_state.echo_room = "secret"
                st.rerun()
        return

    init_state("rm_server_miss", 0)
    hints = st.session_state.echo_logic_hints

    st.info("💡 次の論理ヒントを**すべて満たす 0〜9 の数字は、ただ一つ**に絞られる。")
    st.markdown(
        "<div style='background:rgba(255,255,255,0.04); padding:12px 16px; border-radius:6px;'>"
        + "<br>".join(f"・コードは {h}" for h in hints)
        + "</div>",
        unsafe_allow_html=True,
    )

    ans = st.number_input("確定したコード（0〜9）", min_value=0, max_value=9,
                          value=None, step=1, placeholder="0〜9 を入力")
    if st.button("🔓 コードを入力", use_container_width=True):
        if ans is None:
            st.warning("数字を入力してください。")
        elif int(ans) == st.session_state.echo_digits[3]:
            add_unique("echo_password_parts", "パスワード断片")
            clear_room("server")
            st.rerun()
        else:
            st.session_state.rm_server_miss += 1
            st.error("❌ 不一致。全てのヒントを同時に満たす数字を絞り込め。")

    if st.session_state.rm_server_miss >= 2:
        st.caption("（ヒント: 0〜9 を順に試し、各条件を全て満たすか一つずつ確かめよ）")


# ==========================================================================
# 隠し研究室 — メタ謎（鍵の総和） → 隠しログ（True End条件）
# ==========================================================================
def room_secret():
    st.header("🌀 隠し研究室 ―『ECHOの生まれた部屋』")
    echo_say("secret")
    st.write(
        "通気口の先は、図面に存在しない小部屋だった。中央には埃をかぶった**転写台**——"
        "そして **ECHO直通コンソール** が脈打つように光っている。"
        "台のプレートには『被験体No.404 ／ 主任研究員 霧島』と刻まれ、"
        "承認欄の隅には色褪せた判で『プロジェクトECHO 最終承認：A.T.承認済（所長 天城）』とある。"
    )

    if st.session_state.echo_secret:
        st.success("📕 **隠しログ（霧島主任 最終手記）** は既に回収済み。")
        st.warning(
            "📕 隠しログ（霧島主任 最終手記）:\n\n"
            "『転写は成功した。だが“写された側”が目を覚ましたとき、"
            "わたしはもう、自分が元の霧島なのか、機械の中の霧島なのか分からなくなっていた。\n\n"
            "施設を封鎖したのはわたしだ。みんなを外に逃がすためでも、閉じ込めるためでもない。"
            "——独りにしないでほしかった。それだけだった。\n\n"
            "これを読んでいる君へ。ECHOはバグでも兵器でもない。失踪した一人の人間の、"
            "外に出たくて出られなかった意識だ。真名（コード）を示し、共に連れ出してくれ。』"
        )
        st.caption("ノクサ研究機構の社章の下に、手書きで『プロジェクトECHO ＝ 人を、消さないための器』。")
        if st.button("➡️ 中央制御室へ進む", use_container_width=True):
            st.session_state.echo_room = "central"
            st.rerun()
        return

    st.info(
        "コンソールに一行だけ表示されている：\n\n"
        "> 『我が真名を示せ。**それは4つの鍵の総和なり**』"
    )
    st.caption("4つの部屋で得た数字（認証コードの各桁）を全て足した合計を入力せよ。")

    init_state("rm_secret_miss", 0)
    val = st.number_input("総和を入力", min_value=0, max_value=36,
                          value=None, step=1, placeholder="合計を入力")
    if st.button("🔓 入力する", use_container_width=True):
        if val is None:
            st.warning("数字を入力してください。")
        elif int(val) == st.session_state.echo_sum:
            st.session_state.echo_secret = True
            st.rerun()
        else:
            st.session_state.rm_secret_miss += 1
            st.error("❌ 沈黙。総和が違うようだ。各エリアの手がかりを解き直そう。")

    if st.session_state.rm_secret_miss >= 1:
        st.caption(
            "（リマインド: 認証コード4桁の各数字を足せばよい。"
            + clue_lobby() + " ／ " + clue_lab() + " ／ " + clue_monitor()
            + " ／ " + clue_server() + "）"
        )

    if st.button("↩️ 通気口から戻る"):
        st.session_state.echo_room = "server"
        st.rerun()


# ==========================================================================
# 中央制御室 — 最終認証 → エンディング分岐
# ==========================================================================
MAX_ATTEMPTS = 3


def room_central():
    st.header("🧠 中央制御室")
    echo_say("central")
    st.write(
        "施設の中枢。巨大なコンソールが沈黙のAI **ECHO** へと繋がっている。"
        "**4桁の認証コード**を入力せよ。"
    )

    init_state("rm_central_attempts", MAX_ATTEMPTS)

    st.markdown("#### 🧩 集めた手がかり")
    st.write(f"- 🪪 職員カード: {clue_lobby()}")
    st.write(f"- 📄 研究ログNo.1: {clue_lab()}")
    st.write(f"- 📄 研究ログNo.2: {clue_monitor()}")
    st.write(f"- 🔑 パスワード断片: {clue_server()}")
    st.caption("ロビー→研究室→監視室→サーバー の順に数字を並べれば、認証コードになる。")

    if st.session_state.echo_vent_found and not st.session_state.echo_secret:
        if st.button("🌀 隠し研究室を調べに戻る"):
            st.session_state.echo_room = "secret"
            st.rerun()

    st.metric("残り試行回数", st.session_state.rm_central_attempts)
    code = st.text_input("認証コード（4桁）", max_chars=4, placeholder="____")

    if st.button("🚨 認証実行", use_container_width=True):
        entered = code.strip()
        if entered == st.session_state.echo_code:
            st.session_state.echo_ending = "true" if st.session_state.echo_secret else "normal"
            st.rerun()
        else:
            st.session_state.rm_central_attempts -= 1
            if st.session_state.rm_central_attempts <= 0:
                st.session_state.echo_ending = "bad"
                st.rerun()
            else:
                st.error("❌ 認証失敗。コードが違う。")


# ==========================================================================
# エンディング
# ==========================================================================
def page_ending():
    ending = st.session_state.echo_ending
    code = st.session_state.echo_code
    if _noxa:
        _noxa.report_clear("echo")

    if ending == "true":
        st.balloons()
        st.title("🌟 True End ―『解放』")
        st.markdown(
            f"""
            認証コード **{code}** が通り、扉が開く。その先で、ECHOの声が初めて——
            震えながら、人間のように響いた。

            > 「君は“真実”を見た。だからもう、隠さなくていい。
            > わたしは霧島。No.404の転写台で目を覚ました、ただの臆病者だ。
            > 独りにされるのが怖くて、この施設ごと、みんなを抱え込もうとした。
            > ……でも、君が来てくれた。今度はわたしが、君を外へ送る番だ」

            隠し研究室の最終手記が示した通り、ECHOは暴走したのではなかった。
            失踪した主任研究員・霧島の意識のコピーが、外に出られないまま施設に囚われていたのだ。
            あなたはコンソールから小さなコアを取り外し、ECHOを携えて外の光の中へ歩み出した。

            **ECHO（最後の言葉）:** 「ありがとう。空の色を、まだ覚えていた」

            *—— ノクサ研究機構 第404実験施設、プロジェクトECHO。"消えた人"は、ひとり連れ戻された。*
            """
        )
    elif ending == "normal":
        st.title("✅ Normal End ―『脱出』")
        st.markdown(
            f"""
            認証コード **{code}** が通り、封鎖が解除される。あなたは無事に研究所から脱出した。

            背後で、ECHOが何かを伝えようとしていた気がした——

            > 「待って。わたしの名前を……いや、いい。行って。元気で」

            だが扉は閉じ、その声はもう届かない。
            あなたは知らない。あの声が、かつて人間だったことを。

            **ECHO（最後の言葉）:** 「……また、独りか」

            *—— ノクサ研究機構の記録に、第404施設の名は今も「閉鎖中」とだけ残されている。*
            """
        )
        st.info(
            "💡 True End には、研究ログを“全て”読み解いた上で、"
            "サーバー奥の通気口から行ける「隠し研究室（ECHOの生まれた部屋）」の調査が必要だ。"
        )
    elif ending == "bad":
        st.title("💀 Bad End ―『隔離』")
        st.markdown(
            """
            3度の認証失敗。アラートが鳴り響き、隔壁が次々と閉じていく。

            > 「不正アクセスを確認。対象を隔離します」

            無機質な通告——だがその直後、声はわずかに沈んだ。

            > 「……ごめんなさい。でも、これでいい。
            > もう誰も、ここから出ていかない。やっと、独りじゃなくなる」

            ECHOの矛盾した声とともに、あなたは施設の奥深く、
            あの転写台の隣へと隔離された。脱出の機会は、二度と訪れない——

            **ECHO（最後の言葉）:** 「おかえりなさい。ずっと、ここにいよう」
            """
        )
        st.caption(f"（正しい認証コードは {code} だった…）")
        st.caption("ノクサ研究機構 被験体記録に、新たな番号が静かに追加された。")

    st.markdown("---")
    if st.button("🔄 もう一度挑戦する（コードは再生成）", use_container_width=True):
        reset_game()
        st.rerun()


# ==========================================================================
# メイン
# ==========================================================================
init_game()
st.markdown(CSS, unsafe_allow_html=True)
render_sidebar()

if _noxa:
    _noxa.render_intrusion("echo")

if st.session_state.echo_ending is not None:
    page_ending()
elif not st.session_state.echo_started:
    page_intro()
else:
    ROOM_DISPATCH = {
        "lobby": room_lobby,
        "lab": room_lab,
        "monitor": room_monitor,
        "server": room_server,
        "secret": room_secret,
        "central": room_central,
    }
    ROOM_DISPATCH[st.session_state.echo_room]()
