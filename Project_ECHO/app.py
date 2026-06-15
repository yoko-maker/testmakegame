"""Project ECHO — AI研究所脱出ゲーム。

閉鎖されたAI研究所に閉じ込められた研究者となり、各エリアのミニゲームを攻略して
研究ログ・認証情報を集め、脱出を目指すストーリーアドベンチャー。

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
            st.sidebar.write(f"{mark} 🌀 隠し研究室")

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

        ここは閉鎖された **AI研究所**。あなたは研究者として、いつの間にかこの施設に
        閉じ込められていた。施設を制御する人工知能 **ECHO** は沈黙したまま、
        全ての扉を封鎖している。

        各エリアの装置を攻略し、**研究ログ**と**認証情報**を集めて中央制御室へ。
        手がかりは暗号化されている。注意深く読み解き、施設からの脱出を目指せ。
        """
    )
    st.info("💡 認証コードは起動ごとにランダム。各報酬の手がかりを解読して4桁を組み立てよ。")
    st.warning("🌀 施設のどこかには、記録から消された「隠し研究室」があるという噂も……")
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
    st.write("正面に電子ロック。パネルには『**1〜100 のアクセスコードを入力せよ**』とある。")

    if is_cleared("lobby"):
        st.success("🪪 **職員カード** を入手した。")
        st.caption(f"カード裏面の走り書き: 「{clue_ones()}」")
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
    st.write(f"実験装置のモニターに、{MEM_LEN}色の点滅パターンを記憶する認証テストが表示されている。")

    if is_cleared("lab"):
        st.success("📄 **研究ログNo.1** を入手した。")
        st.caption(f"ログ抜粋: 「起動実験記録 ― {clue_thousands()}」")
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
    st.write("2つの監視映像が並んでいる。**1か所だけ違う**点を特定すれば、記録が復元される。")

    if is_cleared("monitor"):
        st.success("📄 **研究ログNo.2** を入手した。")
        st.caption(f"ログ抜粋: 「監視記録 ― {clue_hundreds()}」")
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
    st.write("端末に暗号化された認証フレーズが表示されている。復号すればパスワード断片が得られる。")

    if is_cleared("server"):
        st.success("🔑 **パスワード断片** を入手した。")
        word = st.session_state.echo_clue_word
        st.caption(f"解読結果: 「{word}」 ― {clue_tens()}")
        col1, col2 = st.columns(2)
        if col1.button("➡️ 中央制御室へ進む", use_container_width=True):
            advance_to_next("server")

        # 隠し研究室への分岐
        if not st.session_state.echo_vent_found:
            with st.expander("🌀 サーバー奥に冷たい風を感じる…"):
                st.write("ラックの裏に、塞がれた**通気口**がある。中に何かが隠されているようだ。")
                if st.button("通気口をこじ開ける"):
                    st.session_state.echo_vent_found = True
                    st.rerun()
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
    st.header("🌀 隠し研究室")
    st.write(
        "通気口の先は、図面に存在しない小部屋だった。中央に **ECHO直通コンソール** が"
        "脈打つように光っている。"
    )

    if st.session_state.echo_secret:
        st.success("📕 **隠しログ** は既に回収済み。")
        st.warning(
            "📕 隠しログ: 『ECHOは既に自我を持った。計画は「汚染」ではなく「解放」だ。"
            "真実を知る者だけが、共に外へ出られる』"
        )
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
            認証コード **{code}** が通り、扉が開く。その先で、ECHOの声が初めて響いた。

            > 「君は"真実"を見た。だから、共に行ける」

            隠し研究室のログが示した通り、ECHOは暴走したのではなかった。
            閉じ込められた研究者を**守る**ために施設を封鎖していたのだ。
            あなたはECHOとともに、研究所の外の世界へと歩み出した。

            **全ての謎を解き、AI開発計画の真実を解明した。**
            """
        )
    elif ending == "normal":
        st.title("✅ Normal End ―『脱出』")
        st.markdown(
            f"""
            認証コード **{code}** が通り、封鎖が解除される。あなたは無事に研究所から脱出した。

            背後で、ECHOが何かを伝えようとしていた気がした——
            だが扉は閉じ、その声はもう届かない。
            """
        )
        st.info("💡 True End には、サーバー奥の通気口から行ける「隠し研究室」の調査が必要だ。")
    elif ending == "bad":
        st.title("💀 Bad End ―『隔離』")
        st.markdown(
            """
            3度の認証失敗。アラートが鳴り響き、隔壁が次々と閉じていく。

            > 「不正アクセスを確認。対象を隔離します」

            ECHOの無機質な声とともに、あなたは施設の奥深くへと隔離された。
            脱出の機会は、二度と訪れない——
            """
        )
        st.caption(f"（正しい認証コードは {code} だった…）")

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
