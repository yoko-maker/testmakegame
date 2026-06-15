"""LAST 30 MINUTES — 世界崩壊カウントダウン。

巨大隕石が地球へ接近。残り時間内に5つの施設を復旧し、迎撃成功率を高めて
人類滅亡を回避するタイムアタック・ミニゲーム集。

  ⚡ 発電所     計算問題      → 電力復旧
  📡 通信施設   タイピング    → 通信回復
  🔬 研究所     科学クイズ    → 隕石解析
  🪖 軍司令部   反射神経      → 迎撃精度向上
  🚀 宇宙センター 最終迎撃     → 復旧施設数でエンディング分岐

リアルタイム制限時間つき。0になると Bad End（人類滅亡）。
"""

import random
import time

import streamlit as st

try:
    st.set_page_config(page_title="LAST 30 MINUTES", page_icon="☄️", layout="centered")
except Exception:
    pass  # ポータルに統合された場合は無視

# 施設定義: (名称, アイコン, フラグキー, ビュー, 成功時メッセージ)
FACILITIES = [
    ("発電所", "⚡", "lz_power", "calc", "電力復旧"),
    ("通信施設", "📡", "lz_comm", "type", "各国との通信回復"),
    ("研究所", "🔬", "lz_analysis", "quiz", "隕石解析率向上"),
    ("軍司令部", "🪖", "lz_military", "reflex", "迎撃成功率向上"),
]

DIFFICULTY = {"☄️ 特訓（5分）": 300, "🌍 標準（15分）": 900, "💀 本番（30分）": 1800}


# ==========================================================================
# 状態 & 時間
# ==========================================================================
def init_state(key, value):
    if key not in st.session_state:
        st.session_state[key] = value


def init_game():
    init_state("lz_started", False)
    init_state("lz_view", "hub")
    init_state("lz_total", 1800)
    init_state("lz_start", 0.0)
    for _, _, flag, _, _ in FACILITIES:
        init_state(flag, False)
    init_state("lz_ending", None)


def reset_game():
    for key in list(st.session_state.keys()):
        if key.startswith("lz_") or key.startswith("mg_"):
            del st.session_state[key]
    init_game()


def remaining():
    return max(0.0, st.session_state.lz_total - (time.time() - st.session_state.lz_start))


def facilities_done():
    return sum(1 for _, _, flag, _, _ in FACILITIES if st.session_state[flag])


def goto(view):
    st.session_state.lz_view = view
    st.rerun()


def broadcast(frac):
    if frac > 0.5:
        return "info", "🛰️ 緊急放送: 隕石は大気圏外。各施設の復旧を急げ。"
    if frac > 0.25:
        return "warning", "📡 ニュース速報: 隕石接近中。全世界が避難を開始した。"
    if frac > 0.1:
        return "warning", "🚨 ニュース速報: 衝突軌道を確認。迎撃準備を急げ！"
    return "error", "⚠️ 最終警告: 衝突まであと僅か！ 今すぐ宇宙センターへ！！"


def timer_color(frac):
    if frac > 0.5:
        return "#2e7d32"
    if frac > 0.25:
        return "#ef6c00"
    return "#c62828"


# ==========================================================================
# HUD（リアルタイムタイマー）
# ==========================================================================
@st.fragment(run_every="1s")
def render_hud():
    rem = remaining()
    if rem <= 0 and st.session_state.lz_ending is None:
        st.session_state.lz_ending = "bad_timeout"
        st.rerun(scope="app")
        return

    frac = rem / st.session_state.lz_total if st.session_state.lz_total else 0
    mm, ss = divmod(int(rem), 60)
    color = timer_color(frac)
    st.markdown(
        f"<div style='text-align:center; font-size:64px; font-weight:bold; "
        f"font-family:monospace; color:{color};'>⏱️ {mm:02d}:{ss:02d}</div>",
        unsafe_allow_html=True,
    )
    st.progress(frac)
    level, msg = broadcast(frac)
    getattr(st, level)(msg)


# ==========================================================================
# イントロ
# ==========================================================================
def page_intro():
    st.title("☄️ LAST 30 MINUTES")
    st.subheader("― 世界崩壊カウントダウン ―")
    st.markdown(
        """
        **緊急事態。** 直径10kmの巨大隕石が地球へ向かっている。
        衝突まで、残された時間はわずか。

        あなたは危機管理本部の最高指揮官。制限時間内に **5つの施設** を復旧し、
        迎撃システムを起動して、人類滅亡を回避せよ。

        施設は **順不同** で攻略可能。だが時間は刻一刻と失われていく——。
        """
    )
    diff = st.radio("難易度（制限時間）を選択", list(DIFFICULTY.keys()), index=0)
    st.caption("※ タイマーは選択直後ではなく『開始』を押した瞬間から動き出す。")
    if st.button("🚀 ミッション開始", use_container_width=True):
        st.session_state.lz_started = True
        st.session_state.lz_total = DIFFICULTY[diff]
        st.session_state.lz_start = time.time()
        st.session_state.lz_view = "hub"
        st.rerun()


# ==========================================================================
# 司令室（ハブ）
# ==========================================================================
def page_hub():
    render_hud()
    st.markdown("---")
    st.header("🛰️ 危機管理本部")
    done = facilities_done()
    st.write(f"復旧施設: **{done} / 4**　／　現在の迎撃成功率: **{done * 25}%**")

    for name, icon, flag, view, _ in FACILITIES:
        ok = st.session_state[flag]
        label = f"{icon} {name}" + ("　✅ 復旧済み" if ok else "")
        if st.button(label, key=f"hub_{view}", use_container_width=True, disabled=ok):
            goto(view)

    st.markdown("---")
    if st.button("🚀 宇宙センター（最終迎撃）", use_container_width=True):
        goto("space")
    st.caption("※ 迎撃は宇宙センターから。施設の復旧数が多いほど成功率が上がる。")


# ==========================================================================
# 発電所 — 計算問題
# ==========================================================================
def gen_calc():
    op = random.choice(["+", "-", "×"])
    if op == "×":
        a, b = random.randint(2, 12), random.randint(2, 12)
        ans = a * b
    elif op == "-":
        a, b = random.randint(10, 40), random.randint(1, 10)
        a = max(a, b)
        ans = a - b
    else:
        a, b = random.randint(5, 40), random.randint(5, 40)
        ans = a + b
    return {"text": f"{a} {op} {b}", "ans": ans}


def setup_calc():
    st.session_state.mg_calc = [gen_calc() for _ in range(3)]
    st.session_state.mg_calc_idx = 0
    st.session_state.mg_calc_msg = ""


def view_calc():
    render_hud()
    st.markdown("---")
    st.header("⚡ 発電所 ― 計算問題")
    st.caption("配電制御の計算を3問連続で正解し、電力を復旧せよ。")

    if st.session_state.lz_power:
        st.success("✅ 電力は復旧済み。")
        if st.button("🛰️ 司令室に戻る"):
            goto("hub")
        return

    if "mg_calc" not in st.session_state:
        setup_calc()

    idx = st.session_state.mg_calc_idx
    prob = st.session_state.mg_calc[idx]
    st.progress(idx / 3, text=f"問題 {idx + 1} / 3")
    st.subheader(f"{prob['text']} = ?")
    val = st.number_input("答え", value=0, step=1, key=f"calc_in_{idx}")
    if st.button("⚙️ 入力", use_container_width=True):
        if int(val) == prob["ans"]:
            st.session_state.mg_calc_idx += 1
            if st.session_state.mg_calc_idx >= 3:
                st.session_state.lz_power = True
            st.session_state.mg_calc_msg = ""
        else:
            st.session_state.mg_calc_msg = "miss"
        st.rerun()

    if st.session_state.mg_calc_msg == "miss":
        st.error("❌ 計算ミス。慎重に！（時間は刻々と過ぎている）")

    if st.session_state.lz_power:
        st.balloons()

    if st.button("🛰️ 司令室に戻る"):
        goto("hub")


# ==========================================================================
# 通信施設 — タイピング
# ==========================================================================
TYPE_WORDS = ["SOS", "MAYDAY", "EVACUATE", "SHELTER", "INTERCEPT", "COUNTDOWN", "RESCUE", "ALERT"]


def setup_type():
    st.session_state.mg_type = random.sample(TYPE_WORDS, 3)
    st.session_state.mg_type_idx = 0
    st.session_state.mg_type_msg = ""


def view_type():
    render_hud()
    st.markdown("---")
    st.header("📡 通信施設 ― タイピング")
    st.caption("通信コードを正確に入力し、各国との通信を回復せよ。")

    if st.session_state.lz_comm:
        st.success("✅ 通信は回復済み。")
        if st.button("🛰️ 司令室に戻る"):
            goto("hub")
        return

    if "mg_type" not in st.session_state:
        setup_type()

    idx = st.session_state.mg_type_idx
    word = st.session_state.mg_type[idx]
    st.progress(idx / 3, text=f"コード {idx + 1} / 3")
    st.markdown(f"<div style='font-size:40px; text-align:center; letter-spacing:6px; font-family:monospace;'>{word}</div>", unsafe_allow_html=True)
    typed = st.text_input("上のコードを正確に入力（大文字）", key=f"type_in_{idx}")
    if st.button("📨 送信", use_container_width=True):
        if typed.strip().upper() == word:
            st.session_state.mg_type_idx += 1
            if st.session_state.mg_type_idx >= 3:
                st.session_state.lz_comm = True
            st.session_state.mg_type_msg = ""
        else:
            st.session_state.mg_type_msg = "miss"
        st.rerun()

    if st.session_state.mg_type_msg == "miss":
        st.error("❌ コード不一致。正確に入力せよ。")

    if st.session_state.lz_comm:
        st.balloons()

    if st.button("🛰️ 司令室に戻る"):
        goto("hub")


# ==========================================================================
# 研究所 — 科学クイズ
# ==========================================================================
SCI_QUIZ = [
    {"q": "隕石が大気圏に突入して光る現象は？", "choices": ["流星", "オーロラ", "虹", "雷"], "answer": 0},
    {"q": "隕石に多く含まれる金属は？", "choices": ["アルミ", "鉄", "金", "銅"], "answer": 1},
    {"q": "恐竜絶滅の一因とされる巨大衝突が起きた場所は？",
     "choices": ["サハラ砂漠", "ユカタン半島", "シベリア", "アマゾン"], "answer": 1},
]


def setup_quiz():
    st.session_state.mg_quiz_idx = 0
    st.session_state.mg_quiz_correct = 0
    st.session_state.mg_quiz_answered = False
    st.session_state.mg_quiz_fail = False


def view_quiz():
    render_hud()
    st.markdown("---")
    st.header("🔬 研究所 ― 科学クイズ")
    st.caption("隕石に関する設問に全問正解し、解析率を高めよ。")

    if st.session_state.lz_analysis:
        st.success("✅ 隕石解析は完了済み。")
        if st.button("🛰️ 司令室に戻る"):
            goto("hub")
        return

    if "mg_quiz_idx" not in st.session_state:
        setup_quiz()

    idx = st.session_state.mg_quiz_idx
    item = SCI_QUIZ[idx]
    st.progress(idx / len(SCI_QUIZ), text=f"第 {idx + 1} 問 / {len(SCI_QUIZ)}")
    st.subheader(item["q"])

    if not st.session_state.mg_quiz_answered:
        for i, ch in enumerate(item["choices"]):
            if st.button(ch, key=f"sq_{idx}_{i}", use_container_width=True):
                st.session_state.mg_quiz_answered = True
                st.session_state.mg_quiz_last = (i == item["answer"])
                if st.session_state.mg_quiz_last:
                    st.session_state.mg_quiz_correct += 1
                st.rerun()
    else:
        if st.session_state.mg_quiz_last:
            st.success("⭕ 正解！")
        else:
            st.error(f"❌ 不正解… 正解は「{item['choices'][item['answer']]}」")
        last = idx + 1 == len(SCI_QUIZ)
        if st.button("結果" if last else "次へ", key=f"sq_next_{idx}"):
            st.session_state.mg_quiz_answered = False
            if last:
                if st.session_state.mg_quiz_correct == len(SCI_QUIZ):
                    st.session_state.lz_analysis = True
                else:
                    setup_quiz()
                    st.session_state.mg_quiz_fail = True
            else:
                st.session_state.mg_quiz_idx += 1
            st.rerun()

    if st.session_state.get("mg_quiz_fail"):
        st.warning("⚠️ 全問正解が必要だ。最初からやり直し。")

    if st.session_state.lz_analysis:
        st.balloons()

    if st.button("🛰️ 司令室に戻る"):
        goto("hub")


# ==========================================================================
# 軍司令部 — 反射神経
# ==========================================================================
REFLEX_GOAL = 5


def setup_reflex():
    st.session_state.mg_reflex_hits = 0
    st.session_state.mg_reflex_target = random.randrange(9)
    st.session_state.mg_reflex_msg = ""


def view_reflex():
    render_hud()
    st.markdown("---")
    st.header("🪖 軍司令部 ― 反射神経")
    st.caption(f"🎯 を狙って連続 {REFLEX_GOAL} 回タップ。外すと最初から！")

    if st.session_state.lz_military:
        st.success("✅ 迎撃システムの照準補正は完了済み。")
        if st.button("🛰️ 司令室に戻る"):
            goto("hub")
        return

    if "mg_reflex_hits" not in st.session_state:
        setup_reflex()

    hits = st.session_state.mg_reflex_hits
    target = st.session_state.mg_reflex_target
    st.progress(hits / REFLEX_GOAL, text=f"命中 {hits} / {REFLEX_GOAL}")

    for r in range(3):
        cols = st.columns(3)
        for c in range(3):
            i = r * 3 + c
            face = "🎯" if i == target else "・"
            if cols[c].button(face, key=f"rf_{i}", use_container_width=True):
                if i == target:
                    st.session_state.mg_reflex_hits += 1
                    if st.session_state.mg_reflex_hits >= REFLEX_GOAL:
                        st.session_state.lz_military = True
                    else:
                        st.session_state.mg_reflex_target = random.randrange(9)
                    st.session_state.mg_reflex_msg = ""
                else:
                    st.session_state.mg_reflex_hits = 0
                    st.session_state.mg_reflex_target = random.randrange(9)
                    st.session_state.mg_reflex_msg = "miss"
                st.rerun()

    if st.session_state.mg_reflex_msg == "miss":
        st.error("❌ 照準ミス！ 連続命中がリセットされた。")

    if st.session_state.lz_military:
        st.balloons()

    if st.button("🛰️ 司令室に戻る"):
        goto("hub")


# ==========================================================================
# 宇宙センター — 最終迎撃
# ==========================================================================
def ending_for(count):
    if count >= 4:
        return "true"
    if count == 3:
        return "good"
    if count >= 1:
        return "normal"
    return "bad"


def view_space():
    render_hud()
    st.markdown("---")
    st.header("🚀 宇宙センター ― 最終迎撃")
    done = facilities_done()
    rate = done * 25

    st.write("各施設の復旧状況：")
    for name, icon, flag, _, _ in FACILITIES:
        st.write(f"- {icon} {name}: {'✅ 復旧' if st.session_state[flag] else '❌ 未復旧'}")
    st.metric("迎撃成功率", f"{rate}%")

    if done < 4:
        st.warning("⚠️ 未復旧の施設がある。このまま迎撃すると被害が出る恐れがある。")

    st.markdown("---")
    if st.button("🚀 迎撃ミサイル発射", use_container_width=True):
        st.session_state.lz_ending = ending_for(done)
        st.rerun()
    if st.button("🛰️ 司令室に戻る"):
        goto("hub")


# ==========================================================================
# エンディング
# ==========================================================================
def page_ending():
    ending = st.session_state.lz_ending
    done = facilities_done()

    if ending == "true":
        st.balloons()
        st.title("🌟 True End ―『完全回避』")
        st.markdown(
            """
            全施設が完全復旧し、迎撃システムは100%の性能を発揮した。
            放たれた迎撃ミサイルは隕石を寸分の狂いなく捉え、上空ではじけ散らせた。

            破片の一つも地表に届かなかった。人類は、完璧な勝利を手にした。
            あなたの指揮が、世界を救ったのだ。
            """
        )
    elif ending == "good":
        st.title("🙂 Good End ―『被害最小』")
        st.markdown(
            """
            迎撃ミサイルは隕石本体を破壊。だが砕けた小片の一部が各地に落下した。

            局地的な被害は出たものの、人類滅亡は回避された。
            あと一歩で完全勝利だった——残された施設を思うと、悔いも残る。
            """
        )
        st.info("💡 True End には4施設すべての復旧が必要だ。")
    elif ending == "normal":
        st.title("😔 Normal End ―『被害甚大、されど生存』")
        st.markdown(
            """
            不完全な迎撃システムでは、隕石を逸らすのが精一杯だった。
            本体は浅い角度で大気をかすめ、巨大な衝撃波が大地を襲う。

            多くの犠牲を払いながらも、人類はかろうじて生き延びた。
            """
        )
        st.info("💡 復旧施設を増やせば、被害をもっと減らせる。")
    elif ending == "bad":
        st.title("💀 Bad End ―『迎撃失敗・人類滅亡』")
        st.markdown(
            """
            復旧の足りない迎撃システムは隕石を捉えきれなかった。
            閃光が空を覆い、文明は一瞬で塵に帰した——。
            """
        )
    elif ending == "bad_timeout":
        st.title("💀 Bad End ―『時間切れ・人類滅亡』")
        st.markdown(
            """
            ——時間切れ。迎撃の時は、永遠に失われた。

            カウントダウンがゼロを指した瞬間、空が白く燃え上がった。
            人類に、次の30分は訪れない。
            """
        )

    st.caption(f"最終復旧施設: {done} / 4")
    st.markdown("---")
    if st.button("🔄 もう一度挑戦する", use_container_width=True):
        reset_game()
        st.rerun()


# ==========================================================================
# サイドバー
# ==========================================================================
def render_sidebar():
    st.sidebar.title("☄️ LAST 30 MIN")
    if st.session_state.lz_started and st.session_state.lz_ending is None:
        st.sidebar.subheader("🏭 復旧状況")
        for name, icon, flag, _, _ in FACILITIES:
            st.sidebar.write(f"{'✅' if st.session_state[flag] else '⬜'} {icon} {name}")
        st.sidebar.caption(f"迎撃成功率: {facilities_done() * 25}%")
    st.sidebar.markdown("---")
    if st.sidebar.button("🔄 ミッションをやり直す"):
        reset_game()
        st.rerun()


# ==========================================================================
# メイン
# ==========================================================================
init_game()
render_sidebar()

if st.session_state.lz_ending is not None:
    page_ending()
elif not st.session_state.lz_started:
    page_intro()
elif remaining() <= 0:
    st.session_state.lz_ending = "bad_timeout"
    page_ending()
else:
    VIEW_DISPATCH = {
        "hub": page_hub,
        "calc": view_calc,
        "type": view_type,
        "quiz": view_quiz,
        "reflex": view_reflex,
        "space": view_space,
    }
    VIEW_DISPATCH[st.session_state.lz_view]()
