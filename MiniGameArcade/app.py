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
  🛒 景品交換所
  🔢 数列の記憶（隠しゲーム・コインで解放）
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
    "listener": ("☕ 聞き上手", "マスターの身の上話を最後まで聞いた"),
    "echo_seeker": ("📼 ECHOの残響", "隠しゲーム「数列の記憶」を解放した"),
}

STARTING_COINS = 100
LEVEL_STEP = 100  # この枚数を稼ぐごとに1レベルアップ


# --------------------------------------------------------------------------
# 店主「マスター」— 累計獲得コインのしきい値で独白が段階解放される。
# 真相は最後の段階で明かされる（元NOXA研究員／ECHO計画から逃げてきた）。
# --------------------------------------------------------------------------
MASTER_MONOLOGUES = [
    (0,
     "「いらっしゃい。ここは古い筐体ばかりの小さなアーケードさ。"
     "わたしのことは“マスター”とでも呼んでくれ。ゆっくり遊んでいきな。」"),
    (100,
     "「ほう、もう100コインか。筋がいいね。"
     "……この店を始める前は、別の仕事をしていてね。人にはあまり話さないが。」"),
    (300,
     "「むかし、わたしは“研究”の仕事をしていた。とある機構でね。"
     "頭の良い連中ばかりだったが……みんな、少しずつ姿を消していった。」"),
    (600,
     "「ECHO（エコー）——そう呼ばれていた計画があった。"
     "人の意識を、そっくり機械へ写し取ろうという試みさ。美しい夢に見えたんだがね。」"),
    (1000,
     "「気づけば同僚は名簿から消え、残ったのは番号だけ。"
     "決まって“404”——どこにも見つからない、という意味の番号だった。怖くなってね。」"),
    (1500,
     "「だから逃げた。データを少しだけ抱えてね。"
     "この古い筐体——実は中身は空っぽじゃない。あの計画の記録を隠す“擬装”なのさ。」"),
    (2500,
     "「わたしは“ノクサ研究機構”の元研究員だ。ECHOから逃げ出した臆病者さ。"
     "だがここでなら、消えた仲間の記憶も、こうして遊ぶ誰かの笑顔も、まだ残せる。"
     "……長話に付き合ってくれて、ありがとう。」"),
]


def master_unlocked_count():
    """累計獲得コインで解放済みのマスター独白の本数。"""
    earned = st.session_state.coins_earned + st.session_state.get("master_bonus_coins", 0)
    return sum(1 for threshold, _ in MASTER_MONOLOGUES if earned >= threshold)


# --------------------------------------------------------------------------
# 景品交換所のカタログ
# --------------------------------------------------------------------------
SHOP_BADGES = {
    "badge_cherry": ("🍒 チェリーピン", "スロット好きの証", 120),
    "badge_seven": ("7️⃣ ラッキーセブン章", "幸運を呼ぶ収集バッジ", 250),
    "badge_404": ("📟 “404”の欠片", "見つからないはずのバッジ。なぜここに？", 404),
}


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
    # マスター／景品交換所まわり
    init_state("master_extra", False)       # 追加エピソード解放済みか
    init_state("master_bonus_coins", 0)     # 独白解放を進めるための加算分
    init_state("badges", set())             # 交換した収集バッジ
    init_state("secret_unlocked", False)    # 隠しゲーム「数列の記憶」解放済みか


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
    st.write("ゲームで遊んでコインを稼ぎ、レベルと実績を集めよう！")

    name = st.text_input("プレイヤー名", value=st.session_state.player_name, max_chars=12)
    if name != st.session_state.player_name:
        st.session_state.player_name = name

    st.markdown("---")
    render_master()

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
    st.caption("👈 サイドバーからゲームや景品交換所を選んで遊ぼう！")


# --------------------------------------------------------------------------
# 店主「マスター」の演出（ホーム画面）
# --------------------------------------------------------------------------
def render_master():
    """累計獲得コインに応じてマスターの独白を段階表示する。"""
    st.subheader("☕ アーケードの店主「マスター」")
    count = master_unlocked_count()
    total = len(MASTER_MONOLOGUES)
    extra = st.session_state.master_extra

    # 直近に解放された独白を一番上に大きく表示
    latest_idx = count - 1
    if latest_idx >= 0:
        st.info(MASTER_MONOLOGUES[latest_idx][1])
        # 最終段階まで聞いたら実績
        if count >= total:
            unlock("listener")

    with st.expander(f"マスターの話を読み返す（{count} / {total} 解放済み）"):
        for i, (threshold, line) in enumerate(MASTER_MONOLOGUES):
            if i < count:
                st.markdown(f"**◆ その{i + 1}**")
                st.write(line)
            else:
                need = threshold - (st.session_state.coins_earned + st.session_state.master_bonus_coins)
                st.markdown(f"🔒 _まだ聞けない話（累計あと {max(need, 0)} コイン）_")
        if extra:
            st.markdown("---")
            st.markdown("**◆ 追加エピソード（景品交換所で解放）**")
            st.write(
                "「ひとつだけ白状しよう。逃げたあの夜、わたしは“404号”の端末から"
                "ひとり分の意識データを持ち出した。それが誰のものだったか——"
                "いつかこの筐体の奥で、もう一度あいさつできる日が来るといいんだがね。」"
            )
        else:
            st.markdown("---")
            st.caption("🔒 追加エピソードは「🛒 景品交換所」で解放できる。")


# --------------------------------------------------------------------------
# 景品交換所
# --------------------------------------------------------------------------
def page_shop():
    st.header("🛒 景品交換所")
    st.caption("貯めたコインで、マスターの追加エピソード・収集バッジ・隠しゲームと交換しよう。")
    st.metric("💴 所持コイン", st.session_state.coins)
    st.markdown("---")

    # ① マスターの追加エピソード
    st.subheader("📖 マスターの追加エピソード")
    EXTRA_COST = 200
    if st.session_state.master_extra:
        st.success("解放済み。ホーム画面のマスターの話で読めるよ。")
    else:
        st.write(f"マスターが胸の内に隠した、もう一つの告白を解放する。（{EXTRA_COST} コイン）")
        if st.button(f"交換する（-{EXTRA_COST}）", key="shop_extra",
                     disabled=st.session_state.coins < EXTRA_COST):
            add_coins(-EXTRA_COST)
            st.session_state.master_extra = True
            st.toast("マスターの追加エピソードを解放！", icon="📖")
            st.rerun()

    st.markdown("---")

    # ② 収集バッジ
    st.subheader("🎖️ レトロ収集バッジ")
    for key, (name, desc, cost) in SHOP_BADGES.items():
        owned = key in st.session_state.badges
        c1, c2 = st.columns([3, 1])
        with c1:
            st.markdown(f"**{name}** — {desc}")
            st.caption(f"価格: {cost} コイン")
        with c2:
            if owned:
                st.success("所持")
            elif st.button(f"-{cost}", key=f"shop_{key}",
                           disabled=st.session_state.coins < cost):
                add_coins(-cost)
                st.session_state.badges.add(key)
                st.toast(f"{name} を手に入れた！", icon="🎖️")
                if key == "badge_404":
                    st.info("……端末がかすかに「404」と明滅した気がした。")
                st.rerun()

    if st.session_state.badges:
        st.write("**コレクション:** " +
                 "　".join(SHOP_BADGES[k][0] for k in SHOP_BADGES if k in st.session_state.badges))

    st.markdown("---")

    # ③ 隠しミニゲーム
    st.subheader("🔢 隠しゲーム「数列の記憶」")
    SECRET_COST = 300
    if st.session_state.secret_unlocked:
        st.success("解放済み。サイドバーのメニューから遊べるよ。")
    else:
        st.write(
            f"古い筐体の奥に眠る7本目のゲーム。マスター曰く“ECHO計画の名残”だとか。"
            f"（{SECRET_COST} コイン）"
        )
        if st.button(f"解放する（-{SECRET_COST}）", key="shop_secret",
                     disabled=st.session_state.coins < SECRET_COST):
            add_coins(-SECRET_COST)
            st.session_state.secret_unlocked = True
            unlock("echo_seeker")
            st.toast("隠しゲーム「数列の記憶」を解放！", icon="🔢")
            st.balloons()
            st.rerun()


# --------------------------------------------------------------------------
# ゲーム7（隠し）: 数列の記憶
# --------------------------------------------------------------------------
SECRET_FLAVOR = [
    "端末に古いログが流れる……「被験体の記憶列、再生開始」",
    "画面の隅に小さく「NOXA / ECHO」のロゴが明滅する。",
    "「この数列は、消えた研究者が遺した暗号だ」とマスターは言った。",
    "ログの末尾はいつも同じ番号で途切れている——404。",
]


def setup_secret_round():
    """新しい数列を生成して出題状態にする。"""
    length = 3 + st.session_state.sm_level  # レベルが上がるほど長くなる
    st.session_state.sm_sequence = [random.randint(0, 9) for _ in range(length)]
    st.session_state.sm_input = ""
    st.session_state.sm_phase = "show"   # show → input → result
    st.session_state.sm_awarded = False


def game_secret():
    st.header("🔢 数列の記憶")
    st.caption("表示された数列を覚えて、同じ順番で入力しよう。長く続けるほど高報酬！")
    st.caption(f"📼 {random.choice(SECRET_FLAVOR)}")

    init_state("sm_level", 0)
    init_state("sm_best", 0)
    if "sm_sequence" not in st.session_state:
        setup_secret_round()

    seq = st.session_state.sm_sequence
    phase = st.session_state.sm_phase
    st.metric("現在のレベル", st.session_state.sm_level + 1)

    if phase == "show":
        st.markdown(
            f"<div style='font-size:48px; text-align:center; letter-spacing:14px;'>"
            f"{' '.join(str(n) for n in seq)}</div>",
            unsafe_allow_html=True,
        )
        st.info("この数列を覚えよう。覚えたら下のボタンへ。")
        if st.button("覚えた！ 入力へ進む", key="sm_ready", use_container_width=True):
            st.session_state.sm_phase = "input"
            st.rerun()
        return

    if phase == "input":
        st.markdown(
            f"<div style='font-size:48px; text-align:center; letter-spacing:14px;'>"
            f"{' '.join('＿' for _ in seq)}</div>",
            unsafe_allow_html=True,
        )
        answer = st.text_input("覚えた数列を続けて入力（例: 0314）", key="sm_answer", max_chars=len(seq))
        if st.button("回答する", key="sm_submit", use_container_width=True):
            correct = "".join(str(n) for n in seq)
            if answer == correct:
                level = st.session_state.sm_level
                reward = 10 + level * 8
                add_coins(reward)
                st.session_state.clears += 1
                st.session_state.sm_reward = reward
                st.session_state.sm_level += 1
                st.session_state.sm_best = max(st.session_state.sm_best, st.session_state.sm_level)
                st.session_state.sm_result = "win"
            else:
                st.session_state.sm_result = "lose"
                st.session_state.sm_correct = correct
                st.session_state.sm_level = 0
            st.session_state.sm_phase = "result"
            st.rerun()
        return

    # result
    if st.session_state.get("sm_result") == "win":
        st.success(f"🎉 正解！ +{st.session_state.get('sm_reward', 0)}コイン")
        st.balloons()
        st.write("マスター: 「いい記憶力だ。……あの計画も、こんな風に人を覚えていられたらよかった。」")
        if st.button("次の数列へ（もっと長くなる）", key="sm_next", use_container_width=True):
            setup_secret_round()
            st.rerun()
    else:
        st.error(f"💀 不正解… 正解は「{st.session_state.get('sm_correct', '')}」でした。")
        st.write("ログが途切れる——「…記憶列、損失。コード 404。」")
        if st.button("もう一度はじめから", key="sm_retry", use_container_width=True):
            setup_secret_round()
            st.rerun()

    st.metric("自己ベスト（到達レベル）", st.session_state.sm_best)


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
    {"q": "「echo」の日本語の意味は？", "choices": ["反響（こだま）", "稲妻", "潮流", "霧"], "answer": 0},
    {"q": "マスターがこの店で何度も口にする“見つからない”を表す番号は？",
     "choices": ["200", "404", "500", "302"], "answer": 1},
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
        # 極稀イースターエッグ: リールに「404」が浮かぶ
        if random.random() < 0.01:
            st.session_state.sl_reels = ["4️⃣", "0️⃣", "4️⃣"]
            add_coins(40)
            st.session_state.sl_message = (
                "📟 リールに見覚えのない「404」が浮かんだ……マスターがこちらを見た。 +40コイン"
            )
            st.rerun()
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
    ("ECHO", "マスターが逃げてきた“計画”の名"),
    ("NOXA", "とある巨大研究機構の名"),
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
    ("こだま", "山びこ。“ECHO”の日本語"),
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
    "🛒 景品交換所": page_shop,
}
# 隠しゲームは景品交換所で解放したときだけメニューに現れる
if st.session_state.secret_unlocked:
    PAGES["🔢 数列の記憶（隠し）"] = game_secret

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
