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

# NOXA Universe（ポータル統合時のみ利用可能 / 単体起動では import 失敗を無視）
try:
    import noxa_core as _noxa
except Exception:
    _noxa = None

# 施設定義: (名称, アイコン, フラグキー, ビュー, 成功時メッセージ)
FACILITIES = [
    ("発電所", "⚡", "lz_power", "calc", "電力復旧"),
    ("通信施設", "📡", "lz_comm", "type", "各国との通信回復"),
    ("研究所", "🔬", "lz_analysis", "quiz", "隕石解析率向上"),
    ("軍司令部", "🪖", "lz_military", "reflex", "迎撃成功率向上"),
]

DIFFICULTY = {"☄️ 特訓（5分）": 300, "🌍 標準（15分）": 900, "💀 本番（30分）": 1800}

# 各施設に常駐する人物の声。施設画面で表示し、生死・言葉が結末に反映される。
FACILITY_VOICES = {
    "lz_power": (
        "👷 発電所員・ハル",
        "「第3市民病院の人工呼吸器が、うちの送電で動いてる。"
        "あそこには俺の母さんもいるんだ……頼む、電気を戻してくれ」",
    ),
    "lz_comm": (
        "📻 通信士・ミナ",
        "「各国の避難指示が、この回線一本に懸かってます。"
        "ノイズの向こうで、みんなが救難信号を送り続けてるんです」",
    ),
    "lz_analysis": (
        "🔬 主任研究員・霧島",
        "「ここはNOXA研究機構の解析施設。隕石の組成に……"
        "見覚えのある波形が混じってる。プロジェクトECHOの観測記録と同じだ」",
    ),
    "lz_military": (
        "🎖️ 軍司令官・ガロ大佐",
        "「照準を預ける。撃ち損じれば終わりだ。"
        "部下たちは最後の一人まで持ち場を離れん。指揮官、頼んだぞ」",
    ),
}

# 施設復旧時に流れる、命に直結する人間味ある速報。
RESTORE_NEWS = {
    "lz_power": "🏥 速報: 北区市民病院に電気が戻った。停止寸前だった新生児集中治療室の保育器が、再び静かに動き始めた。",
    "lz_comm": "📞 速報: 通信回復。沿岸部に取り残された避難者2,000人へ、ようやく高台への誘導が届いた。",
    "lz_analysis": "🔬 速報: 隕石の弱点となる断層を解析班が特定。研究所からの最後の通信は途切れ気味だった。",
    "lz_military": "🎖️ 速報: 迎撃システムの照準補正が完了。各国の防衛軍が司令部の指揮下に集結した。",
}


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
    # トレードオフの選択: 限られた予備電力を「軍」優先 / 「民間」優先 のどちらに回すか。
    # None=未選択。エンディング分岐に効く。
    init_state("lz_priority", None)


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
        return "info", (
            "🛰️ 緊急放送: 隕石は大気圏外。各施設の復旧を急げ。"
            "──画面の隅に流れる気象局の識別番号『404』が、なぜか点滅している。"
        )
    if frac > 0.25:
        return "warning", (
            "📡 ニュース速報: 隕石接近中。全世界が避難を開始。"
            "各地の研究機関から研究者の連絡途絶が相次いでいるとの情報も。"
            "──無人のはずの避難所の監視映像の隅に、赤い服の女が一瞬だけ映っていた。"
        )
    if frac > 0.1:
        return "warning", "🚨 ニュース速報: 衝突軌道を確認。各都市の病院・避難所が祈るように迎撃を待っている。"
    return "error", "⚠️ 最終警告: 衝突まであと僅か！ 街の灯りが次々消えていく。今すぐ宇宙センターへ！！"


def timer_color(frac):
    if frac > 0.5:
        return "#2e7d32"
    if frac > 0.25:
        return "#ef6c00"
    return "#c62828"


def facility_voice(flag):
    """施設に常駐する人物の声を表示する。"""
    if flag in FACILITY_VOICES:
        speaker, line = FACILITY_VOICES[flag]
        st.info(f"**{speaker}**\n\n{line}")


def restore_news(flag):
    """復旧した施設の、命に直結する人間味ある速報を流す。"""
    if flag in RESTORE_NEWS:
        st.success(RESTORE_NEWS[flag])


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

        あなたは危機管理本部の最高指揮官。制限時間内に各施設を復旧し、
        迎撃システムを起動して、人類滅亡を回避せよ。

        施設の向こうには、電気を待つ病院、回線にすがる避難者、
        持ち場を離れない部下たち——**一つひとつの作業が、誰かの命に直結している。**

        施設は **順不同** で攻略可能。だが時間は刻一刻と失われていく——。
        """
    )
    st.caption("※ 隕石解析を担うのは、意識・記憶を研究する巨大組織『NOXA研究機構』の一施設だという。")
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

    # 復旧した施設の速報を流す（命に直結する人間味のあるニュース）。
    for _, _, flag, _, _ in FACILITIES:
        if st.session_state[flag]:
            restore_news(flag)

    # ── トレードオフの選択 ──
    # 全部は間に合わないと気づいた指揮官に、限られた予備電力の配分を迫る。
    if done >= 2 and st.session_state.lz_priority is None:
        st.markdown("---")
        st.error(
            "⚡ **苦渋の判断** ⚡\n\n"
            "予備電力が底をつきかけている。残り時間で全施設を満たすことは、もう不可能だ。"
            "わずかな電力を、どちらへ回す？"
        )
        ch1, ch2 = st.columns(2)
        with ch1:
            if st.button("🎖️ 軍を優先（確実な迎撃）", use_container_width=True):
                st.session_state.lz_priority = "military"
                st.rerun()
            st.caption("迎撃の確度は上がる。だが避難中の市民の灯りが消える。")
        with ch2:
            if st.button("🏥 民間を優先（市民の命）", use_container_width=True):
                st.session_state.lz_priority = "civilian"
                st.rerun()
            st.caption("病院と避難所は守られる。だが迎撃の余力は削られる。")
    elif st.session_state.lz_priority == "military":
        st.warning("🎖️ 配分方針: **軍優先**。市街は暗い。だが迎撃の刃は鋭い。")
    elif st.session_state.lz_priority == "civilian":
        st.warning("🏥 配分方針: **民間優先**。街には灯りが残る。迎撃は人の手に懸かる。")

    st.markdown("---")
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
    facility_voice("lz_power")

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
    val = st.number_input("答え", value=None, step=1, key=f"calc_in_{idx}",
                          placeholder="答えを入力")
    if st.button("⚙️ 入力", use_container_width=True):
        if val is None:
            st.warning("答えを入力してください。")
        else:
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
    facility_voice("lz_comm")

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
# 研究所 — 数列予測（隕石の軌道予測）
# ==========================================================================
SEQ_LEN = 3  # 解析率100%に必要な連続正解数


def gen_seq():
    """隕石の軌道観測値を模した数列を生成し、次の値を当てさせる。

    等差・等比・階差（二次）の3パターンからランダムに選ぶ。
    返り値: {"shown": 表示する数列, "ans": 次の値, "rule": 規則名}
    """
    kind = random.choice(["arith", "geo", "diff"])
    if kind == "arith":
        start = random.randint(1, 12)
        step = random.randint(2, 9)
        vals = [start + step * i for i in range(5)]
        rule = f"等差（公差 {step}）"
    elif kind == "geo":
        start = random.randint(1, 4)
        ratio = random.randint(2, 3)
        vals = [start * ratio ** i for i in range(5)]
        rule = f"等比（公比 {ratio}）"
    else:  # 階差が等差になる二次数列
        a0 = random.randint(1, 8)
        d0 = random.randint(1, 5)
        dd = random.randint(1, 4)
        vals = [a0]
        d = d0
        for _ in range(5):
            vals.append(vals[-1] + d)
            d += dd
        vals = vals[:6]
        rule = f"階差が一定ずつ増える（二次）"
    return {"shown": vals[:-1], "ans": vals[-1], "rule": rule}


def setup_seq():
    st.session_state.mg_seq = [gen_seq() for _ in range(SEQ_LEN)]
    st.session_state.mg_seq_idx = 0
    st.session_state.mg_seq_msg = ""


def view_quiz():
    render_hud()
    st.markdown("---")
    st.header("🔬 研究所 ― 隕石の軌道予測")
    st.caption("観測された軌道データ列の『次の値』を読み、隕石の進路を予測して解析率を高めよ。")
    facility_voice("lz_analysis")
    st.caption("📁 解析端末の片隅に、古い研究ログのタイトルが残っている── "
               "『ECHO-404: 被験者の意識同期記録（破棄予定）』。今は気に留めている時間はない。")
    st.caption("📁 ログ最終署名: `amagi@noxa.jp`（Amagi Research Center / 承認待ち）。"
               "差出人の所在は、もう誰も知らない。")

    if st.session_state.lz_analysis:
        st.success("✅ 隕石解析は完了済み。")
        if st.button("🛰️ 司令室に戻る"):
            goto("hub")
        return

    if "mg_seq" not in st.session_state:
        setup_seq()

    idx = st.session_state.mg_seq_idx
    prob = st.session_state.mg_seq[idx]
    st.progress(idx / SEQ_LEN, text=f"観測データ {idx + 1} / {SEQ_LEN}")
    seq_text = "　,　".join(str(v) for v in prob["shown"]) + "　,　 ？"
    st.markdown(
        f"<div style='font-size:34px; text-align:center; letter-spacing:2px; "
        f"font-family:monospace;'>{seq_text}</div>",
        unsafe_allow_html=True,
    )
    st.caption("軌道観測値の規則を見抜き、次に来る値を入力せよ。")
    val = st.number_input("次の値", value=None, step=1, key=f"seq_in_{idx}",
                          placeholder="次に来る値を入力")
    if st.button("🛰️ 予測を確定", use_container_width=True):
        if val is None:
            st.warning("次の値を入力してください。")
        else:
            if int(val) == prob["ans"]:
                st.session_state.mg_seq_idx += 1
                if st.session_state.mg_seq_idx >= SEQ_LEN:
                    st.session_state.lz_analysis = True
                st.session_state.mg_seq_msg = ""
            else:
                st.session_state.mg_seq_msg = f"miss:{prob['rule']}:{prob['ans']}"
            st.rerun()

    if st.session_state.mg_seq_msg.startswith("miss"):
        _, rule, ans = st.session_state.mg_seq_msg.split(":", 2)
        st.error(f"❌ 予測がずれた。軌道を見失えば迎撃は不可能だ。（規則: {rule} / 正しい値: {ans}）")

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
    facility_voice("lz_military")

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

    if st.session_state.lz_priority == "military":
        st.caption("🎖️ 電力は軍へ。迎撃精度に余力が回っている──だが暗い街で待つ人々の顔が浮かぶ。")
    elif st.session_state.lz_priority == "civilian":
        st.caption("🏥 電力は民間へ。街には灯りが残る──迎撃は人の練度だけが頼りだ。")

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
def priority_epilogue(ending):
    """トレードオフの選択が結末にどう響いたかを描く後日談。"""
    prio = st.session_state.lz_priority
    if prio is None:
        return  # 選択するほど施設を復旧しなかった場合は何も語らない

    survived = ending in ("true", "good", "normal")
    if prio == "military":
        if survived:
            st.markdown(
                "> 🎖️ ガロ大佐「迎撃は成った。指揮官、あなたの判断は正しかった。"
                "……だが暗闇で耐えた市民たちのことを、私たちは決して忘れない」"
            )
        else:
            st.markdown(
                "> 🎖️ 軍へ電力を回した代償に、街の灯りは早くに消えていた。"
                "捧げた犠牲は、報われなかった。"
            )
    elif prio == "civilian":
        if survived:
            st.markdown(
                "> 🏥 病院の保育器は最後まで止まらなかった。"
                "灯りの下で抱かれた赤子の泣き声が、生き延びた世界の最初の音になった。"
            )
        else:
            st.markdown(
                "> 🏥 市民の灯りは守り抜いた。"
                "最期の瞬間まで、誰一人として暗闇の中にはいなかった——それだけが、せめてもの慰めだった。"
            )


def page_ending():
    ending = st.session_state.lz_ending
    done = facilities_done()
    if _noxa:
        _noxa.report_clear("last30")
        if st.session_state.get("lz_priority"):
            _noxa.set_choice("last30_priority", st.session_state.lz_priority)

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

    priority_epilogue(ending)

    # 復旧した施設の人物の声を、結末に反映させる。
    if ending in ("true", "good", "normal"):
        survivors = [FACILITY_VOICES[flag][0] for _, _, flag, _, _ in FACILITIES
                     if st.session_state[flag] and flag in FACILITY_VOICES]
        if survivors:
            st.success("🕊️ 生還が確認された声: " + "、".join(survivors))
    if st.session_state.lz_analysis:
        st.caption("📁 研究所の解析ログは『NOXA研究機構』本部へ自動転送された。"
                   "ECHO-404の項目だけが、なぜか送信記録から欠落していた。")

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
        if st.session_state.lz_priority == "military":
            st.sidebar.caption("⚡ 配分: 🎖️ 軍優先")
        elif st.session_state.lz_priority == "civilian":
            st.sidebar.caption("⚡ 配分: 🏥 民間優先")
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
