"""Project ECHO — AI研究所脱出ゲーム。

ノクサ研究機構（NOXA Institute）第404実験施設。意識をAIへ写す「プロジェクトECHO」が
進められていたこの研究所に閉じ込められた研究者となり、各エリアのミニゲームを攻略して
研究ログ・認証情報を集め、脱出を目指すストーリーアドベンチャー。

施設AI「ECHO」はプレイヤーに語りかけ、進行に応じて態度が
「協力的 → 不穏 → 敵対」と段階変化する。前任研究者の日報を読み解くと、
ECHOの正体（失踪した研究者の意識のコピー）への伏線が見えてくる。

認証コードは毎回ランダム生成され、各報酬の手がかりは符号化されている：
  🏛️ ロビー        数字当て(1-100)   → 職員カード   : 一の位 = 掛け算の一の位
  🔬 研究室        記憶ゲーム(5色)    → 研究ログNo.1 : 千の位 = 2進数を10進数化
  📹 監視室        間違い探し(5x5)    → 研究ログNo.2 : 百の位 = 足し算の一の位
  🖥️ サーバールーム シーザー暗号解読   → パスワード断片: 十の位 = 復号した英数語
  🌀 隠し研究室     メタ謎(鍵の総和)   → 隠しログ（True End条件）
  🧠 中央制御室     最終認証(4桁)      → エンディング分岐
"""

import random

import streamlit as st

try:
    st.set_page_config(page_title="Project ECHO", page_icon="🧬", layout="centered")
except Exception:
    pass  # ポータルに統合された場合は無視

NUMWORDS = ["ZERO", "ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX", "SEVEN", "EIGHT", "NINE"]

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
    """認証コードを乱数生成し、各桁を符号化した手がかりを作る。"""
    digits = [random.randint(0, 9) for _ in range(4)]  # 千, 百, 十, 一
    d_th, d_hu, d_te, d_on = digits
    st.session_state.echo_code = "".join(str(d) for d in digits)
    st.session_state.echo_sum = sum(digits)

    # 千の位 → 2進数
    st.session_state.echo_clue_bin = format(d_th, "04b")

    # 百の位 → 足し算の一の位
    a = random.randint(0, 9)
    b = (d_hu - a) % 10
    st.session_state.echo_clue_add = (a, b)

    # 十の位 → シーザー暗号で英数語
    shift = random.randint(3, 23)
    plain = NUMWORDS[d_te]
    cipher = "".join(chr((ord(ch) - 65 + shift) % 26 + 65) for ch in plain)
    st.session_state.echo_clue_shift = shift
    st.session_state.echo_clue_word = plain
    st.session_state.echo_clue_cipher = cipher

    # 一の位 → 掛け算の一の位
    while True:
        m, n = random.randint(2, 9), random.randint(2, 9)
        if (m * n) % 10 == d_on:
            break
    st.session_state.echo_clue_mult = (m, n)


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
# 手がかり表示ヘルパー
# ==========================================================================
def clue_thousands():
    return f"千の位 = 2進数 `{st.session_state.echo_clue_bin}` を10進数に直した値"


def clue_hundreds():
    a, b = st.session_state.echo_clue_add
    return f"百の位 = ({a} + {b}) の一の位"


def clue_tens():
    return f"十の位 = 暗号 `{st.session_state.echo_clue_cipher}` を復号した英単語が表す数字"


def clue_ones():
    m, n = st.session_state.echo_clue_mult
    return f"一の位 = ({m} × {n}) の積の一の位"


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
        手がかりは暗号化されている。そして、前任の研究者たちが遺した日報には、
        ECHOの“正体”に触れる断片が紛れている。注意深く読み解き、脱出を目指せ。
        """
    )
    st.info("💡 認証コードは起動ごとにランダム。各報酬の手がかりを解読して4桁を組み立てよ。")
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
# ロビー — 数字当て(1-100) → 職員カード（一の位）
# ==========================================================================
def room_lobby():
    st.header("🏛️ ロビー")
    echo_say("lobby")
    st.write("正面に電子ロック。パネルには『**1〜100 のアクセスコードを入力せよ**』とある。")

    if is_cleared("lobby"):
        st.success("🪪 **職員カード** を入手した。")
        st.caption(f"カード裏面の走り書き: 「{clue_ones()}」")
        st.caption("カードの名義欄は黒く塗り潰され、隅に小さく『404』とだけ刻印されている。")
        if st.button("➡️ 研究室へ進む", use_container_width=True):
            advance_to_next("lobby")
        return

    init_state("rm_lobby_secret", random.randint(1, 100))
    init_state("rm_lobby_tries", 0)
    init_state("rm_lobby_hint", "1〜100 の数字を入力してロックを解除せよ。")

    st.info(st.session_state.rm_lobby_hint)
    guess = st.number_input("アクセスコード", min_value=1, max_value=100, value=50, step=1)
    if st.button("🔓 入力", use_container_width=True):
        st.session_state.rm_lobby_tries += 1
        secret = st.session_state.rm_lobby_secret
        if guess == secret:
            add_unique("echo_items", "職員カード")
            clear_room("lobby")
            st.rerun()
        elif guess < secret:
            st.session_state.rm_lobby_hint = "⬆️ コードはもっと大きい。"
        else:
            st.session_state.rm_lobby_hint = "⬇️ コードはもっと小さい。"
        st.rerun()

    st.caption(f"試行回数: {st.session_state.rm_lobby_tries}")


# ==========================================================================
# 研究室 — 記憶ゲーム(5色) → 研究ログNo.1（千の位）
# ==========================================================================
MEM_SYMBOLS = ["🟥", "🟦", "🟩", "🟨", "🟪", "🟧"]
MEM_LEN = 5


def setup_memory():
    st.session_state.rm_lab_seq = [random.choice(MEM_SYMBOLS) for _ in range(MEM_LEN)]
    st.session_state.rm_lab_phase = "show"
    st.session_state.rm_lab_answer = []
    st.session_state.rm_lab_msg = ""


def room_lab():
    st.header("🔬 研究室")
    echo_say("lab")
    st.write(f"実験装置のモニターに、{MEM_LEN}色の点滅パターンを記憶する認証テストが表示されている。")

    if is_cleared("lab"):
        st.success("📄 **研究ログNo.1** を入手した。")
        st.caption(f"ログ抜粋: 「{RESEARCH_LOGS['研究ログNo.1']['hint']} {clue_thousands()}」")
        render_log_reader("研究ログNo.1")
        if st.button("➡️ 監視室へ進む", use_container_width=True):
            advance_to_next("lab")
        return

    if "rm_lab_seq" not in st.session_state:
        setup_memory()

    phase = st.session_state.rm_lab_phase

    if phase == "show":
        st.info(f"下の {MEM_LEN} 色のパターンを順番どおり記憶せよ。")
        st.markdown(
            f"<div style='font-size:52px; text-align:center; letter-spacing:10px;'>"
            f"{' '.join(st.session_state.rm_lab_seq)}</div>",
            unsafe_allow_html=True,
        )
        if st.button("✅ 記憶した（パターンを隠す）", use_container_width=True):
            st.session_state.rm_lab_phase = "input"
            st.session_state.rm_lab_answer = []
            st.rerun()

    elif phase == "input":
        st.info("記憶した順番どおりに色を入力せよ。")
        answer = st.session_state.rm_lab_answer
        slots = answer + ["＿"] * (MEM_LEN - len(answer))
        st.markdown(
            f"<div style='font-size:40px; text-align:center; letter-spacing:10px; min-height:50px;'>"
            f"{' '.join(slots)}</div>",
            unsafe_allow_html=True,
        )
        cols = st.columns(len(MEM_SYMBOLS))
        for col, sym in zip(cols, MEM_SYMBOLS):
            if col.button(sym, key=f"mem_{sym}", use_container_width=True):
                answer.append(sym)
                if len(answer) == MEM_LEN:
                    if answer == st.session_state.rm_lab_seq:
                        add_unique("echo_logs", "研究ログNo.1")
                        clear_room("lab")
                    else:
                        st.session_state.rm_lab_msg = "fail"
                        setup_memory()
                st.rerun()

        if st.session_state.rm_lab_msg == "fail":
            st.error("❌ パターンが違う。新しいパターンで最初から再挑戦。")

        if st.button("🔁 やり直す（新パターン）"):
            setup_memory()
            st.rerun()


# ==========================================================================
# 監視室 — 間違い探し(5x5) → 研究ログNo.2（百の位）
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
        st.caption(f"ログ抜粋: 「{RESEARCH_LOGS['研究ログNo.2']['hint']} {clue_hundreds()}」")
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
# サーバールーム — シーザー暗号解読 → パスワード断片（十の位）
# ==========================================================================
def room_server():
    st.header("🖥️ サーバールーム")
    echo_say("server")
    st.write("端末に暗号化された認証フレーズが表示されている。復号すればパスワード断片が得られる。")

    if is_cleared("server"):
        st.success("🔑 **パスワード断片** を入手した。")
        word = st.session_state.echo_clue_word
        st.caption(f"解読結果: 「{word}」 ― {clue_tens()}")
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
    shift = st.session_state.echo_clue_shift
    cipher = st.session_state.echo_clue_cipher

    st.code(f"暗号文:  {' '.join(cipher)}", language=None)
    st.info(f"💡 各アルファベットを **+{shift} 文字ずらして** 暗号化されている。元の英単語に戻せ。")
    ans = st.text_input("復号した語（英単語 または 数字）", placeholder="例: NINE / 9")

    if st.button("🔓 復号", use_container_width=True):
        norm = ans.strip().upper().replace(" ", "")
        target_word = st.session_state.echo_clue_word
        target_digit = str(NUMWORDS.index(target_word))
        if norm == target_word or norm == target_digit:
            add_unique("echo_password_parts", "パスワード断片")
            clear_room("server")
            st.rerun()
        else:
            st.session_state.rm_server_miss += 1
            st.error(f"❌ 復号失敗。各文字を {shift} 戻す（A→Zを跨ぐ）と英単語になる。")

    if st.session_state.rm_server_miss >= 2:
        ex = cipher[0]
        dec = chr((ord(ex) - 65 - shift) % 26 + 65)
        st.caption(f"（ヒント: 先頭 {ex} → {dec}。答えは0〜9を表す英単語）")


# ==========================================================================
# 隠し研究室 — メタ謎（鍵の総和） → 隠しログ（True End条件）
# ==========================================================================
def room_secret():
    st.header("🌀 隠し研究室 ―『ECHOの生まれた部屋』")
    echo_say("secret")
    st.write(
        "通気口の先は、図面に存在しない小部屋だった。中央には埃をかぶった**転写台**——"
        "そして **ECHO直通コンソール** が脈打つように光っている。"
        "台のプレートには『被験体No.404 ／ 主任研究員 霧島』と刻まれている。"
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
    st.caption("4つの手がかり（千・百・十・一の各位の数字）を全て解いて、その合計を入力せよ。")

    init_state("rm_secret_miss", 0)
    val = st.number_input("総和を入力", min_value=0, max_value=36, value=0, step=1)
    if st.button("🔓 入力する", use_container_width=True):
        if int(val) == st.session_state.echo_sum:
            st.session_state.echo_secret = True
            st.rerun()
        else:
            st.session_state.rm_secret_miss += 1
            st.error("❌ 沈黙。総和が違うようだ。各エリアの手がかりを解き直そう。")

    if st.session_state.rm_secret_miss >= 1:
        st.caption(
            "（リマインド: " + clue_thousands() + " ／ " + clue_hundreds()
            + " ／ " + clue_tens() + " ／ " + clue_ones() + "）"
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

    st.markdown("#### 🧩 集めた手がかり（要解読）")
    st.write(f"- 🪪 職員カード: **{clue_ones()}**")
    st.write(f"- 📄 研究ログNo.1: **{clue_thousands()}**")
    st.write(f"- 📄 研究ログNo.2: **{clue_hundreds()}**")
    st.write(f"- 🔑 パスワード断片: **{clue_tens()}**")
    st.caption("千の位・百の位・十の位・一の位 を並べれば、認証コードになる。")

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
render_sidebar()

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
