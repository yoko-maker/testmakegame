"""ミニゲームアーケード — Streamlit製の遊べる作品集。

共通のコイン経済・プレイヤープロフィール・実績システムで全ゲームがつながった
1つの作品です。サイドバーでホーム／各ゲームを切り替えて遊べます。

  🏠 ホーム（プロフィール・実績・統計）
  🔢 数当てゲーム
  ✊ じゃんけんバトル
  🧠 神経衰弱（メモリーマッチ）
  ❓ クイズ
  🎰 スロットマシン
  🔤 ハングマン
"""

import random

import streamlit as st

try:
    st.set_page_config(page_title="ミニゲームアーケード", page_icon="🎮", layout="centered")
except Exception:
    pass  # ポータルに統合された場合は無視


# ==========================================================================
# 共通システム（コイン経済・プロフィール・実績）
# ==========================================================================
ACHIEVEMENTS = {
    "first_play": ("🌱 はじめの一歩", "初めてゲームを開いた"),
    "sharp_eye": ("🎯 千里眼", "数当てを5回以内でクリア"),
    "rps_king": ("👑 じゃんけん王", "じゃんけんで5勝した"),
    "memory_master": ("🧠 記憶の達人", "神経衰弱を20手以内でクリア"),
    "quiz_master": ("📚 クイズマスター", "クイズで全問正解"),
    "jackpot": ("💰 ジャックポット", "スロットで3つ揃えた"),
    "word_master": ("🔤 言葉の達人", "ハングマンをクリア"),
    "rich": ("🤑 大富豪", "コインを500枚ためた"),
}

STARTING_COINS = 100
LEVEL_STEP = 100  # この枚数を稼ぐごとに1レベルアップ


def init_state(key, value):
    """セッション状態にキーが無ければ初期値を設定する。"""
    if key not in st.session_state:
        st.session_state[key] = value


def init_global_state():
    """プレイヤー共通の状態を初期化する。"""
    init_state("player_name", "プレイヤー1")
    init_state("coins", STARTING_COINS)
    init_state("coins_earned", 0)  # 累計獲得コイン（レベルの素）
    init_state("achievements", set())
    init_state("clears", 0)  # 累計クリア回数


def add_coins(amount):
    """ウォレットにコインを加算（マイナスで消費）。累計と実績も更新。"""
    st.session_state.coins += amount
    if amount > 0:
        st.session_state.coins_earned += amount
        if st.session_state.coins >= 500:
            unlock("rich")


def unlock(key):
    """実績を解除する。新規ならトースト通知を出す。"""
    if key not in st.session_state.achievements:
        st.session_state.achievements.add(key)
        name = ACHIEVEMENTS[key][0]
        st.toast(f"実績解除: {name}", icon="🏅")


def player_level():
    return 1 + st.session_state.coins_earned // LEVEL_STEP


def level_progress():
    """次のレベルまでの進捗 (0.0〜1.0, 現在の端数, あと何枚) を返す。"""
    into = st.session_state.coins_earned % LEVEL_STEP
    return into / LEVEL_STEP, into, LEVEL_STEP - into


def reward_banner(amount):
    """獲得コインを表示する共通バナー。"""
    if amount > 0:
        st.success(f"💴 +{amount} コインを獲得！")


# ==========================================================================
# ホーム画面
# ==========================================================================
def page_home():
    st.title("🎮 ミニゲームアーケード")
    st.write("6つのゲームで遊んでコインを稼ぎ、レベルと実績を集めよう！")

    name = st.text_input("プレイヤー名", value=st.session_state.player_name, max_chars=12)
    if name != st.session_state.player_name:
        st.session_state.player_name = name

    st.markdown("---")
    st.subheader(f"👤 {st.session_state.player_name} さんのプロフィール")

    c1, c2, c3 = st.columns(3)
    c1.metric("💴 コイン", st.session_state.coins)
    c2.metric("⭐ レベル", player_level())
    c3.metric("🏆 クリア回数", st.session_state.clears)

    prog, into, remain = level_progress()
    st.progress(prog, text=f"次のレベルまで あと {remain} コイン（{into}/{LEVEL_STEP}）")

    st.markdown("---")
    st.subheader("🏅 実績")
    unlocked = st.session_state.achievements
    st.caption(f"解除: {len(unlocked)} / {len(ACHIEVEMENTS)}")
    cols = st.columns(2)
    for i, (key, (name, desc)) in enumerate(ACHIEVEMENTS.items()):
        with cols[i % 2]:
            if key in unlocked:
                st.success(f"**{name}**\n\n{desc}")
            else:
                st.markdown(f"🔒 **???**\n\n_{desc}_")

    st.markdown("---")
    st.caption("👈 サイドバーからゲームを選んで遊ぼう！")


# --------------------------------------------------------------------------
# ゲーム1: 数当てゲーム
# --------------------------------------------------------------------------
def game_number_guess():
    st.header("🔢 数当てゲーム")
    st.caption("1〜100 の隠された数字を当てよう。少ない回数ほど高報酬！")

    init_state("ng_secret", random.randint(1, 100))
    init_state("ng_tries", 0)
    init_state("ng_cleared", False)
    init_state("ng_history", [])
    init_state("ng_reward", 0)

    if st.session_state.ng_cleared:
        st.success(
            f"🎉 正解！ 答えは {st.session_state.ng_secret} でした。"
            f" {st.session_state.ng_tries} 回で当てました！"
        )
        reward_banner(st.session_state.ng_reward)
        if st.button("もう一度あそぶ", key="ng_replay"):
            st.session_state.ng_secret = random.randint(1, 100)
            st.session_state.ng_tries = 0
            st.session_state.ng_cleared = False
            st.session_state.ng_history = []
            st.rerun()
        return

    guess = st.number_input("予想する数字", min_value=1, max_value=100, value=50, step=1)
    if st.button("これだ！", key="ng_guess"):
        st.session_state.ng_tries += 1
        secret = st.session_state.ng_secret
        if guess == secret:
            st.session_state.ng_cleared = True
            reward = max(5, 60 - st.session_state.ng_tries * 5)
            st.session_state.ng_reward = reward
            add_coins(reward)
            st.session_state.clears += 1
            if st.session_state.ng_tries <= 5:
                unlock("sharp_eye")
            st.rerun()
        elif guess < secret:
            hint = "⬆️ もっと大きい"
        else:
            hint = "⬇️ もっと小さい"
        st.session_state.ng_history.insert(0, f"{int(guess)} → {hint}")

    if st.session_state.ng_history:
        st.metric("挑戦回数", st.session_state.ng_tries)
        st.write("**ヒント履歴**")
        for line in st.session_state.ng_history:
            st.write(line)


# --------------------------------------------------------------------------
# ゲーム2: じゃんけんバトル
# --------------------------------------------------------------------------
HANDS = {"グー": "✊", "チョキ": "✌️", "パー": "✋"}
BEATS = {"グー": "チョキ", "チョキ": "パー", "パー": "グー"}


def game_rps():
    st.header("✊✌️✋ じゃんけんバトル")
    st.caption("勝つたびに +8コイン。先に5勝するとボーナス！")

    init_state("rps_win", 0)
    init_state("rps_lose", 0)
    init_state("rps_draw", 0)
    init_state("rps_last", None)
    init_state("rps_match_awarded", False)

    col1, col2, col3 = st.columns(3)
    cols = {"グー": col1, "チョキ": col2, "パー": col3}
    for name, col in cols.items():
        with col:
            if st.button(f"{HANDS[name]}\n{name}", key=f"rps_{name}", use_container_width=True):
                cpu = random.choice(list(HANDS))
                if name == cpu:
                    result = "draw"
                    st.session_state.rps_draw += 1
                elif BEATS[name] == cpu:
                    result = "win"
                    st.session_state.rps_win += 1
                    add_coins(8)
                    if st.session_state.rps_win >= 5 and not st.session_state.rps_match_awarded:
                        st.session_state.rps_match_awarded = True
                        st.session_state.clears += 1
                        add_coins(30)
                        unlock("rps_king")
                else:
                    result = "lose"
                    st.session_state.rps_lose += 1
                st.session_state.rps_last = (name, cpu, result)
                st.rerun()

    if st.session_state.rps_last:
        you, cpu, result = st.session_state.rps_last
        msg = {"win": "🎉 勝ち！ +8コイン", "lose": "😢 負け…", "draw": "🤝 あいこ"}[result]
        st.subheader(f"あなた {HANDS[you]} vs {HANDS[cpu]} CPU　→ {msg}")

    a, b, c = st.columns(3)
    a.metric("勝ち", st.session_state.rps_win)
    b.metric("負け", st.session_state.rps_lose)
    c.metric("あいこ", st.session_state.rps_draw)

    if st.session_state.rps_win >= 5:
        st.success("🏆 5勝達成！ ボーナス +30コイン！")
    elif st.session_state.rps_lose >= 5:
        st.error("💀 5敗… CPUの勝ちです。")

    if st.button("スコアをリセット", key="rps_reset"):
        for k in ("rps_win", "rps_lose", "rps_draw"):
            st.session_state[k] = 0
        st.session_state.rps_last = None
        st.session_state.rps_match_awarded = False
        st.rerun()


# --------------------------------------------------------------------------
# ゲーム3: 神経衰弱（メモリーマッチ）
# --------------------------------------------------------------------------
EMOJIS = ["🍎", "🍌", "🍇", "🍓", "🍑", "🍍", "🥝", "🍒"]


def setup_memory():
    deck = EMOJIS * 2
    random.shuffle(deck)
    st.session_state.mm_deck = deck
    st.session_state.mm_revealed = [False] * len(deck)
    st.session_state.mm_matched = [False] * len(deck)
    st.session_state.mm_moves = 0
    st.session_state.mm_clear_pending = None
    st.session_state.mm_awarded = False


def game_memory():
    st.header("🧠 神経衰弱")
    st.caption("同じ絵柄のペアを全部めくろう。少ない手数ほど高報酬！")

    if "mm_deck" not in st.session_state:
        setup_memory()

    deck = st.session_state.mm_deck
    revealed = st.session_state.mm_revealed
    matched = st.session_state.mm_matched

    # 2枚めくった状態なら、判定して伏せる
    pending = [i for i in range(len(deck)) if revealed[i] and not matched[i]]
    if len(pending) == 2:
        i, j = pending
        if deck[i] == deck[j]:
            matched[i] = matched[j] = True
        st.session_state.mm_clear_pending = pending

    cleared = all(matched)

    # クリア報酬（1回だけ）
    if cleared and not st.session_state.mm_awarded:
        st.session_state.mm_awarded = True
        moves = st.session_state.mm_moves
        st.session_state.mm_reward = max(10, 80 - moves * 2)
        add_coins(st.session_state.mm_reward)
        st.session_state.clears += 1
        if moves <= 20:
            unlock("memory_master")

    # 4x4 グリッド
    for row in range(4):
        cols = st.columns(4)
        for col_idx in range(4):
            idx = row * 4 + col_idx
            face = deck[idx] if (revealed[idx] or matched[idx]) else "❓"
            disabled = revealed[idx] or matched[idx] or cleared
            if cols[col_idx].button(face, key=f"mm_{idx}", use_container_width=True, disabled=disabled):
                # めくる前に、保留中の2枚があれば伏せる
                pend = st.session_state.get("mm_clear_pending")
                if pend:
                    for p in pend:
                        if not matched[p]:
                            revealed[p] = False
                    st.session_state.mm_clear_pending = None
                revealed[idx] = True
                st.session_state.mm_moves += 1
                st.rerun()

    st.metric("手数", st.session_state.mm_moves)

    if cleared:
        st.balloons()
        st.success(f"🎉 コンプリート！ {st.session_state.mm_moves} 手でクリア！")
        reward_banner(st.session_state.get("mm_reward", 0))

    if st.button("新しいゲーム", key="mm_new"):
        setup_memory()
        st.rerun()


# --------------------------------------------------------------------------
# ゲーム4: クイズ
# --------------------------------------------------------------------------
QUIZ = [
    {"q": "日本で一番高い山は？", "choices": ["富士山", "北岳", "槍ヶ岳", "御嶽山"], "answer": 0},
    {"q": "光の三原色に含まれないのは？", "choices": ["赤", "緑", "青", "黄"], "answer": 3},
    {"q": "1年で最も昼が長い日は？", "choices": ["春分", "夏至", "秋分", "冬至"], "answer": 1},
    {"q": "「H2O」は何の化学式？", "choices": ["二酸化炭素", "酸素", "水", "塩"], "answer": 2},
    {"q": "世界で一番広い海洋は？", "choices": ["大西洋", "インド洋", "北極海", "太平洋"], "answer": 3},
    {"q": "正五角形の内角の合計は？", "choices": ["360度", "540度", "720度", "900度"], "answer": 1},
    {"q": "サッカーで1チームの出場人数は？", "choices": ["9人", "10人", "11人", "12人"], "answer": 2},
    {"q": "日本の通貨単位は？", "choices": ["ウォン", "円", "元", "ドル"], "answer": 1},
]


def game_quiz():
    st.header("❓ クイズ")
    st.caption("全 {} 問の4択クイズ。正解ごとに +5コイン！".format(len(QUIZ)))

    init_state("qz_index", 0)
    init_state("qz_score", 0)
    init_state("qz_answered", False)
    init_state("qz_finished", False)
    init_state("qz_awarded", False)

    if st.session_state.qz_finished:
        total = len(QUIZ)
        score = st.session_state.qz_score
        # 完了報酬（1回だけ）
        if not st.session_state.qz_awarded:
            st.session_state.qz_awarded = True
            st.session_state.clears += 1
            if score == total:
                add_coins(30)
                unlock("quiz_master")
        st.success(f"🎉 終了！ スコア: {score} / {total}")
        if score == total:
            st.balloons()
            st.write("**全問正解！ パーフェクト！ ボーナス +30コイン！** 🏆")
        elif score >= total * 0.6:
            st.write("**なかなかの好成績！** 👍")
        else:
            st.write("**次はもっといけるはず！** 💪")
        if st.button("もう一度", key="qz_replay"):
            st.session_state.qz_index = 0
            st.session_state.qz_score = 0
            st.session_state.qz_answered = False
            st.session_state.qz_finished = False
            st.session_state.qz_awarded = False
            st.rerun()
        return

    idx = st.session_state.qz_index
    item = QUIZ[idx]
    st.progress((idx) / len(QUIZ), text=f"第 {idx + 1} 問 / {len(QUIZ)}")
    st.subheader(item["q"])

    if not st.session_state.qz_answered:
        for i, choice in enumerate(item["choices"]):
            if st.button(choice, key=f"qz_{idx}_{i}", use_container_width=True):
                st.session_state.qz_answered = True
                st.session_state.qz_correct = i == item["answer"]
                if st.session_state.qz_correct:
                    st.session_state.qz_score += 1
                    add_coins(5)
                st.rerun()
    else:
        if st.session_state.qz_correct:
            st.success("⭕ 正解！ +5コイン")
        else:
            st.error(f"❌ 不正解… 正解は「{item['choices'][item['answer']]}」")
        label = "結果を見る" if idx + 1 == len(QUIZ) else "次の問題へ"
        if st.button(label, key=f"qz_next_{idx}"):
            st.session_state.qz_answered = False
            if idx + 1 == len(QUIZ):
                st.session_state.qz_finished = True
            else:
                st.session_state.qz_index += 1
            st.rerun()

    st.metric("現在のスコア", st.session_state.qz_score)


# --------------------------------------------------------------------------
# ゲーム5: スロットマシン
# --------------------------------------------------------------------------
SLOT_SYMBOLS = ["🍒", "🍋", "🔔", "⭐", "💎", "7️⃣"]
SLOT_PAYOUT = {"🍒": 10, "🍋": 15, "🔔": 20, "⭐": 30, "💎": 50, "7️⃣": 100}
SPIN_COST = 10


def game_slot():
    st.header("🎰 スロットマシン")
    st.caption(f"1回 {SPIN_COST}コインでスピン。コインは他のゲームでも稼げるよ！")

    init_state("sl_reels", ["❔", "❔", "❔"])
    init_state("sl_message", "コインを賭けてスピン！")

    st.markdown(
        f"<div style='font-size:72px; text-align:center; letter-spacing:16px;'>"
        f"{' '.join(st.session_state.sl_reels)}</div>",
        unsafe_allow_html=True,
    )
    st.info(st.session_state.sl_message)
    st.metric("💴 所持コイン", st.session_state.coins)

    can_spin = st.session_state.coins >= SPIN_COST
    if st.button(f"🎯 スピン（-{SPIN_COST}コイン）", use_container_width=True, disabled=not can_spin):
        add_coins(-SPIN_COST)
        reels = [random.choice(SLOT_SYMBOLS) for _ in range(3)]
        st.session_state.sl_reels = reels
        if reels[0] == reels[1] == reels[2]:
            win = SLOT_PAYOUT[reels[0]]
            add_coins(win)
            st.session_state.sl_message = f"💰 ジャックポット！ +{win}コイン！"
            st.session_state.clears += 1
            unlock("jackpot")
            st.balloons()
        elif reels[0] == reels[1] or reels[1] == reels[2] or reels[0] == reels[2]:
            add_coins(5)
            st.session_state.sl_message = "✨ 2つ揃い！ +5コイン"
        else:
            st.session_state.sl_message = "残念！ もう一度どうぞ"
        st.rerun()

    if not can_spin:
        st.warning("コインが足りません。他のゲームで稼ごう！")

    with st.expander("配当表"):
        for sym, pay in SLOT_PAYOUT.items():
            st.write(f"{sym} × 3　→　+{pay} コイン")
        st.write("いずれか2つ揃い　→　+5 コイン")


# --------------------------------------------------------------------------
# ゲーム6: ハングマン
# --------------------------------------------------------------------------
HANGMAN_WORDS_EN = [
    ("PYTHON", "プログラミング言語"),
    ("STREAMLIT", "このアプリのフレームワーク"),
    ("BANANA", "黄色いフルーツ"),
    ("COMPUTER", "電子計算機"),
    ("ELEPHANT", "鼻の長い動物"),
    ("GUITAR", "弦楽器"),
    ("RAINBOW", "雨上がりの空にかかる"),
    ("DIAMOND", "硬い宝石"),
]
HANGMAN_WORDS_JA = [
    ("すいか", "夏に食べる果物"),
    ("ひこうき", "空を飛ぶ乗り物"),
    ("とけい", "時間を知る道具"),
    ("さくら", "春に咲く花"),
    ("ねこ", "ペットの定番の動物"),
    ("にわ", "家の外にある地面"),
    ("ほし", "夜空に光る"),
    ("やま", "高くそびえる地形"),
    ("みかん", "冬に食べる果物"),
    ("ゆき", "冬に降る白いもの"),
    ("くも", "空に浮かぶ白いもの"),
]
# 五十音キーボードの配列（空文字は空白セル）
KANA_ROWS = [
    ["あ", "い", "う", "え", "お"],
    ["か", "き", "く", "け", "こ"],
    ["さ", "し", "す", "せ", "そ"],
    ["た", "ち", "つ", "て", "と"],
    ["な", "に", "ぬ", "ね", "の"],
    ["は", "ひ", "ふ", "へ", "ほ"],
    ["ま", "み", "む", "め", "も"],
    ["や", "", "ゆ", "", "よ"],
    ["ら", "り", "る", "れ", "ろ"],
    ["わ", "", "", "", "を"],
    ["ん", "", "", "", ""],
]
MAX_MISS = 6


def setup_hangman(mode):
    words = HANGMAN_WORDS_JA if mode == "日本語(ひらがな)" else HANGMAN_WORDS_EN
    word, hint = random.choice(words)
    st.session_state.hm_word = word
    st.session_state.hm_hint = hint
    st.session_state.hm_guessed = set()
    st.session_state.hm_miss = 0
    st.session_state.hm_mode = mode
    st.session_state.hm_awarded = False


def game_hangman():
    st.header("🔤 ハングマン")
    st.caption(f"文字を推理して単語を当てよう。クリアで +25コイン！（ミスは {MAX_MISS} 回まで）")

    mode = st.radio("モード", ["English", "日本語(ひらがな)"], horizontal=True, key="hm_mode_select")

    # 初回、またはモードを切り替えたら新しい単語をセット
    if "hm_word" not in st.session_state or st.session_state.get("hm_mode") != mode:
        setup_hangman(mode)

    word = st.session_state.hm_word
    guessed = st.session_state.hm_guessed
    miss = st.session_state.hm_miss

    won = all(c in guessed for c in word)
    lost = miss >= MAX_MISS

    # クリア報酬（1回だけ）
    if won and not st.session_state.hm_awarded:
        st.session_state.hm_awarded = True
        add_coins(25)
        st.session_state.clears += 1
        unlock("word_master")

    display = " ".join(c if (c in guessed or won or lost) else "＿" for c in word)
    st.markdown(f"<div style='font-size:40px; text-align:center; letter-spacing:6px;'>{display}</div>", unsafe_allow_html=True)
    st.write(f"💡 ヒント: **{st.session_state.hm_hint}**")

    hearts = "❤️" * (MAX_MISS - miss) + "🖤" * miss
    st.write(f"残りミス: {hearts}")

    if won:
        st.success("🎉 正解！ クリアしました！ +25コイン")
        st.balloons()
    elif lost:
        st.error(f"💀 ゲームオーバー… 正解は「{word}」でした。")

    disabled_all = won or lost

    def on_guess(letter):
        guessed.add(letter)
        if letter not in word:
            st.session_state.hm_miss += 1
        st.rerun()

    if st.session_state.hm_mode == "日本語(ひらがな)":
        # 五十音キーボード（5列）
        for row in KANA_ROWS:
            cols = st.columns(5)
            for col, kana in zip(cols, row):
                if kana == "":
                    continue
                used = kana in guessed
                if col.button(kana, key=f"hm_{kana}", disabled=used or disabled_all, use_container_width=True):
                    on_guess(kana)
    else:
        # A-Z ボタン（7列×4段）
        letters = [chr(c) for c in range(ord("A"), ord("Z") + 1)]
        for row_start in range(0, 26, 7):
            cols = st.columns(7)
            for col, letter in zip(cols, letters[row_start:row_start + 7]):
                used = letter in guessed
                if col.button(letter, key=f"hm_{letter}", disabled=used or disabled_all, use_container_width=True):
                    on_guess(letter)

    if st.button("新しい単語で遊ぶ", key="hm_new"):
        setup_hangman(st.session_state.hm_mode)
        st.rerun()


# ==========================================================================
# メイン
# ==========================================================================
init_global_state()

PAGES = {
    "🏠 ホーム": page_home,
    "🔢 数当てゲーム": game_number_guess,
    "✊ じゃんけんバトル": game_rps,
    "🧠 神経衰弱": game_memory,
    "❓ クイズ": game_quiz,
    "🎰 スロットマシン": game_slot,
    "🔤 ハングマン": game_hangman,
}

st.sidebar.title("🎮 ミニゲームアーケード")
st.sidebar.metric("💴 コイン", st.session_state.coins)
st.sidebar.metric("⭐ レベル", player_level())
st.sidebar.markdown("---")
choice = st.sidebar.radio("メニュー", list(PAGES.keys()))
st.sidebar.markdown("---")
st.sidebar.caption(f"👤 {st.session_state.player_name}")

# ゲームを開いたら「はじめの一歩」を解除
if choice != "🏠 ホーム":
    unlock("first_play")

PAGES[choice]()
