"""PAIR LOCK — 二人協力・非対称情報の暗号脱出ゲーム (Streamlit)。

「二人とも不完全」をコンセプトに、各プレイヤーは自分にしか見えない情報と
相手にしか見えない情報を持つ。声・チャットで伝え合わないと絶対に解けない。

同期方式:
  ルームコードで2人が別端末から参加し、@st.cache_resource のサーバ内共有
  ストアで状態を同期する（同一サーバプロセスに両者が接続している前提）。
  リアルタイム反映は st.fragment(run_every=...) のポーリングで行う。

実行:
  単体     : streamlit run app.py
  ポータル : ルートの app.py から st.navigation 経由で読み込まれる
"""

import copy
import random
import threading
import time

import streamlit as st

try:
    st.set_page_config(page_title="PAIR LOCK", page_icon="🔒", layout="centered")
except Exception:
    pass  # ポータルに統合された場合は無視


# ==========================================================================
# テーマ (管制室 / インダストリアル)
# ==========================================================================
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Orbitron:wght@600;800&display=swap');

.stApp {
    background:
        radial-gradient(circle at 50% -10%, rgba(0,200,255,0.08), transparent 55%),
        #0a1016;
    color: #cfe9ef;
    font-family: 'Share Tech Mono', monospace;
}
h1, h2, h3 {
    font-family: 'Orbitron', sans-serif !important;
    color: #2fe6d6 !important;
    letter-spacing: 2px;
    text-shadow: 0 0 8px rgba(47,230,214,0.4);
}
p, li, label, .stMarkdown { color: #c2dde3 !important; }

.stButton > button {
    background: rgba(10,30,38,0.6);
    color: #2fe6d6;
    border: 1px solid #2fe6d6;
    border-radius: 4px;
    font-family: 'Share Tech Mono', monospace;
    transition: all 0.15s ease;
}
.stButton > button:hover {
    background: #2fe6d6;
    color: #06141a;
    box-shadow: 0 0 12px rgba(47,230,214,0.7);
}
.stTextInput input {
    background: #0c1c24 !important;
    color: #2fe6d6 !important;
    border: 1px solid #1f6b6b !important;
    font-family: 'Share Tech Mono', monospace !important;
    letter-spacing: 2px;
}

.pl-panel {
    border: 1px solid #1f6b6b;
    background: rgba(10,24,30,0.6);
    border-radius: 6px;
    padding: 0.9rem 1.1rem;
    margin: 0.5rem 0;
    box-shadow: inset 0 0 18px rgba(47,230,214,0.06);
}
.pl-cipher {
    font-size: 2.6rem;
    letter-spacing: 0.6rem;
    text-align: center;
    color: #ffd24d;
    text-shadow: 0 0 10px rgba(255,210,77,0.4);
    padding: 0.6rem 0;
}
.pl-legend { font-size: 1.5rem; letter-spacing: 0.3rem; color: #2fe6d6; }

.pl-grid { border-collapse: collapse; margin: 0.4rem auto; }
.pl-grid td, .pl-grid th {
    width: 52px; height: 52px; text-align: center; vertical-align: middle;
    border: 1px solid #1f4b52; font-size: 1.5rem; line-height: 1.0;
}
.pl-grid th { color: #6fb6c0; font-size: 0.9rem; background: rgba(31,75,82,0.3); }
.pl-grid .lett { display:block; font-size: 0.7rem; color:#ffd24d; letter-spacing:0; }

.pl-role-p1 { color:#ffd24d; font-weight:bold; }
.pl-role-p2 { color:#7fd0ff; font-weight:bold; }
.pl-stamp {
    display:inline-block; padding:0.15rem 0.6rem; border:1px solid #2fe6d6;
    border-radius: 12px; color:#2fe6d6; margin-left:0.4rem;
    animation: pop 0.3s ease;
}
@keyframes pop { 0% { transform: scale(0.6); opacity:0;} 100%{transform:scale(1);opacity:1;} }
.pl-half { color:#ff9f43; font-size:1.2rem; letter-spacing:0.3rem; }
</style>
"""


# ==========================================================================
# 共有ストア (サーバ内・全セッション共通)
# ==========================================================================
@st.cache_resource
def get_store():
    return {"rooms": {}, "lock": threading.Lock()}


STAGE_NAMES = {1: "通信復旧", 2: "認証解除", 3: "監視室", 4: "研究データ解析", 5: "中央制御室"}
LAST_STAGE = 5  # Final


def _new_room(seed: int) -> dict:
    return {
        "seed": seed,
        "stage": 1,                       # 現在の共有ステージ (1..5, 6=クリア)
        "solved": {s: {"p1": False, "p2": False} for s in range(1, LAST_STAGE + 1)},
        "stability": 100,
        "misses": 0,
        "p1_joined": False,
        "p2_joined": False,
        "stamp": {"p1": None, "p2": None},  # (text, timestamp)
        "hidden_log": False,
        "ending": None,
    }


def _make_code() -> str:
    return "".join(random.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(4))


def create_room() -> str:
    store = get_store()
    with store["lock"]:
        code = _make_code()
        while code in store["rooms"]:
            code = _make_code()
        room = _new_room(random.randint(1, 999999))
        room["p1_joined"] = True
        store["rooms"][code] = room
    return code


def join_room(code: str) -> str:
    """戻り値: 'p2'(参加成功) / 'full' / 'notfound'。"""
    store = get_store()
    with store["lock"]:
        room = store["rooms"].get(code)
        if room is None:
            return "notfound"
        if room["p2_joined"]:
            return "full"
        room["p2_joined"] = True
        return "p2"


def room_snapshot(code: str):
    store = get_store()
    with store["lock"]:
        room = store["rooms"].get(code)
        return copy.deepcopy(room) if room else None


def submit_answer(code: str, role: str, stage: int, correct: bool):
    store = get_store()
    with store["lock"]:
        room = store["rooms"].get(code)
        if room is None:
            return
        if correct:
            room["solved"][stage][role] = True
            both = room["solved"][stage]["p1"] and room["solved"][stage]["p2"]
            if both and room["stage"] == stage:
                room["stage"] = stage + 1
        else:
            room["misses"] += 1
            room["stability"] = max(0, 100 - 5 * room["misses"])


def set_stamp(code: str, role: str, text: str):
    store = get_store()
    with store["lock"]:
        room = store["rooms"].get(code)
        if room:
            room["stamp"][role] = (text, time.time())


def set_hidden_log(code: str):
    store = get_store()
    with store["lock"]:
        room = store["rooms"].get(code)
        if room:
            room["hidden_log"] = True


def finalize_ending(code: str):
    store = get_store()
    with store["lock"]:
        room = store["rooms"].get(code)
        if room and room["ending"] is None:
            if room["misses"] == 0 and room["hidden_log"]:
                room["ending"] = "true"
            elif room["hidden_log"]:
                room["ending"] = "secret"
            else:
                room["ending"] = "normal"


def restart_room(code: str):
    store = get_store()
    with store["lock"]:
        room = store["rooms"].get(code)
        if room:
            seed = room["seed"]
            p1, p2 = room["p1_joined"], room["p2_joined"]
            fresh = _new_room(seed)
            fresh["p1_joined"], fresh["p2_joined"] = p1, p2
            store["rooms"][code] = fresh


# ==========================================================================
# パズル生成 (room seed から決定的に — 両端末で同一になる)
# ==========================================================================
CMAP = {"赤": "#ff5c5c", "青": "#5c9bff", "黄": "#ffd24d", "緑": "#46d27f",
        "白": "#eaeaea", "橙": "#ff9f43", "紫": "#c264ff"}


@st.cache_data(show_spinner=False)
def build_puzzle(seed: int) -> dict:
    rng = random.Random(seed)

    # --- Stage1 : 記号暗号 ---
    words = ["CORE", "NODE", "LOCK", "GRID", "HALO", "IRIS", "ECHO", "DUSK", "VEIL", "GATE"]
    word = rng.choice(words)
    pool = list("▲●■◆★◇♦♥♠✦◉▼")
    uniq = list(dict.fromkeys(word))
    syms = rng.sample(pool, len(uniq))
    l2s = dict(zip(uniq, syms))
    s1_symbols = " ".join(l2s[c] for c in word)
    s1_legend = [(l2s[c], c) for c in uniq]
    rng.shuffle(s1_legend)

    # --- Stage2 : 配線 ---
    colors = rng.sample(["赤", "青", "黄", "緑", "白", "橙"], 4)
    nodes = rng.sample(["A", "B", "C", "D", "E", "F"], 4)
    c2n = dict(zip(colors, nodes))
    order = colors[:]
    rng.shuffle(order)
    s2_map = [(c, c2n[c]) for c in colors]   # P1: 配線図
    s2_order = order[:]                       # P2: 起動順 (色のみ)
    s2_answer = "".join(c2n[c] for c in order)

    # --- Stage3 : 座標 / 図形 ---
    shapes = ["○", "△", "□", "◇", "☆"]
    scolors = ["赤", "青", "緑", "黄", "紫"]
    combos = [(c, s) for c in scolors for s in shapes]
    chosen = rng.sample(combos, 5)
    cells = rng.sample([(r, c) for r in range(5) for c in range(5)], 5)
    letters = rng.sample(list("ABCDEFGHJKLMNPQRSTUVWXYZ"), 5)
    ti = rng.randrange(5)
    s3_answer = letters[ti]
    s3_target = chosen[ti]                     # P2: 目標の (色,形)
    s3_grid = list(zip(chosen, cells, letters))  # P1: グリッド

    # --- Stage4 : ファイル復元 ---
    names = ["天野", "桐生", "榊原", "志村", "早乙女", "鷹野", "九条", "氷室"]
    name = rng.choice(names)
    code4 = rng.randint(10, 99)
    s4_answer = f"{name}{code4}"
    # 隠しログ (True/Secret 条件)
    hid = rng.choice(["GENESIS", "ORACLE", "PHANTOM", "ABYSS"])
    half = (len(hid) + 1) // 2
    s4_hid_p1, s4_hid_p2 = hid[:half], hid[half:]

    # --- Final : 統合 ---
    final = f"{word[0]}{s3_answer}{code4}"

    return {
        "s1_symbols": s1_symbols, "s1_legend": s1_legend, "s1_answer": word,
        "s2_map": s2_map, "s2_order": s2_order, "s2_answer": s2_answer,
        "s3_grid": s3_grid, "s3_target": s3_target, "s3_answer": s3_answer,
        "s4_front_code": code4, "s4_back_name": name, "s4_answer": s4_answer,
        "s4_hid_p1": s4_hid_p1, "s4_hid_p2": s4_hid_p2, "s4_hidword": hid,
        "final_word": word, "final_letter": s3_answer, "final_code4": code4,
        "final_answer": final,
    }


# ==========================================================================
# ユーティリティ
# ==========================================================================
def norm(s: str) -> str:
    return "".join(str(s).split()).upper()


def other(role: str) -> str:
    return "p2" if role == "p1" else "p1"


def role_tag(role: str) -> str:
    cls = "pl-role-p1" if role == "p1" else "pl-role-p2"
    label = "P1 (端末α)" if role == "p1" else "P2 (端末β)"
    return f"<span class='{cls}'>{label}</span>"


def app_rerun():
    try:
        st.rerun(scope="app")
    except Exception:
        st.rerun()


def leave_room():
    for k in ("pl_code", "pl_role", "pl_seen_stage"):
        st.session_state.pop(k, None)


# ==========================================================================
# 共通UIパーツ
# ==========================================================================
def stamp_bar(code: str, role: str, loc: str):
    st.caption("クイック送信（通話できない時の合図）:")
    cols = st.columns(4)
    stamps = [("👍", "OK"), ("🔁", "もう一回"), ("❓", "わからない"), ("✋", "待って")]
    for i, (emo, txt) in enumerate(stamps):
        if cols[i].button(f"{emo} {txt}", key=f"stamp_{loc}_{role}_{i}",
                          use_container_width=True):
            set_stamp(code, role, f"{emo} {txt}")
            app_rerun()


@st.fragment(run_every=2)
def live_sync(code: str, role: str):
    room = room_snapshot(code)
    if room is None:
        return

    # ステージが進んだ / 失敗した → 全体を再描画して追従
    if room["stage"] != st.session_state.get("pl_seen_stage"):
        app_rerun()
        return
    if room["stability"] <= 0:
        app_rerun()
        return

    partner = other(role)
    c1, c2, c3 = st.columns([2, 1, 2])
    with c1:
        st.markdown(f"ROOM **{code}** / {role_tag(role)}", unsafe_allow_html=True)
    with c2:
        st.markdown(f"安定度 **{room['stability']}%**")
    with c3:
        pj = room[f"{partner}_joined"]
        if not pj:
            st.markdown("相手: ⚪ 未接続")
        else:
            stg = room["stage"]
            done = stg > LAST_STAGE or room["solved"][stg][partner]
            st.markdown("相手: 🟢 " + ("✅ パート完了" if done else "⌛ 攻略中"))
    st.progress(room["stability"] / 100)

    s = room["stamp"][partner]
    if s and time.time() - s[1] < 18:
        st.markdown(f"相手からの合図: <span class='pl-stamp'>{s[0]}</span>",
                    unsafe_allow_html=True)


@st.fragment(run_every=2)
def poll_change(code: str):
    """エンディング/失敗画面で、相手のルーム再起動などのステージ変化に追従する。"""
    room = room_snapshot(code)
    if room is None:
        return
    if room["stage"] != st.session_state.get("pl_seen_stage"):
        app_rerun()


@st.fragment(run_every=2)
def waiting_view(code: str, role: str, stage: int):
    room = room_snapshot(code)
    if room is None or room["stage"] != stage:
        app_rerun()
        return
    st.success("✅ 送信完了 — あなたのパートはクリア。")
    st.markdown(f"**相手はまだ『{STAGE_NAMES[stage]}』を攻略中です…**")
    st.caption("先にクリアした側は、自分が見た情報を相手に伝えてヒントを出せる。"
               "焦らせず、正確に描写してあげよう。")
    stamp_bar(code, role, f"wait{stage}")


def answer_block(code: str, role: str, stage: int, expected: str, label: str,
                 placeholder: str = ""):
    room = room_snapshot(code)
    if room["solved"][stage][role]:
        waiting_view(code, role, stage)
        return
    key = f"in_{stage}_{role}"
    guess = st.text_input(label, key=key, placeholder=placeholder)
    if st.button("▶ 送信", key=f"sub_{stage}_{role}", type="primary",
                 use_container_width=True):
        ok = norm(guess) == norm(expected)
        submit_answer(code, role, stage, ok)
        if ok:
            st.toast("✅ 認証成功", icon="✅")
        else:
            st.toast("❌ 不正解 — 施設安定度が低下", icon="⚠️")
        app_rerun()
    stamp_bar(code, role, f"ans{stage}")


# ==========================================================================
# 各ステージ描画 (role により見える情報が異なる = 非対称情報)
# ==========================================================================
def render_grid_html(grid):
    head = "<tr><th></th>" + "".join(f"<th>{c+1}</th>" for c in range(5)) + "</tr>"
    body = ""
    lookup = {(r, c): (combo, lett) for combo, (r, c), lett in grid}
    for r in range(5):
        row = f"<th>{r+1}</th>"
        for c in range(5):
            if (r, c) in lookup:
                (col, shp), lett = lookup[(r, c)]
                row += (f"<td><span style='color:{CMAP[col]}'>{shp}</span>"
                        f"<span class='lett'>{lett}</span></td>")
            else:
                row += "<td></td>"
        body += f"<tr>{row}</tr>"
    return f"<table class='pl-grid'>{head}{body}</table>"


def stage1(code, role, pz):
    st.subheader("STAGE 1 — 通信復旧  ★☆☆☆☆")
    st.caption("記号列と対応表が、2台に分かれて表示されている。声で伝え合い、英単語を解読せよ。")
    if role == "p1":
        st.markdown("**あなたの端末に届いた記号列:**")
        st.markdown(f"<div class='pl-panel'><div class='pl-cipher'>{pz['s1_symbols']}</div></div>",
                    unsafe_allow_html=True)
        st.info("対応表(記号=文字)は相手だけが持っている。記号を順番どおり正確に伝えよう。")
    else:
        st.markdown("**あなたの端末に届いた対応表:**")
        rows = "　".join(f"{sym}={ch}" for sym, ch in pz["s1_legend"])
        st.markdown(f"<div class='pl-panel'><span class='pl-legend'>{rows}</span></div>",
                    unsafe_allow_html=True)
        st.info("記号列は相手だけが持っている。並び順を聞き取って単語を組み立てよう。")
    answer_block(code, role, 1, pz["s1_answer"], "解読した英単語を入力",
                 placeholder="例: WORD")


def stage2(code, role, pz):
    st.subheader("STAGE 2 — 認証解除  ★★☆☆☆")
    st.caption("配線図と起動シーケンス、半分ずつ。色を端子に翻訳し合わないと並びが出ない。")
    if role == "p1":
        st.markdown("**配線図（各色がどの端子に繋がっているか）:**")
        lines = "<br>".join(
            f"<span style='color:{CMAP[c]}'>●</span> {c}の配線 → 端子 <b>{n}</b>"
            for c, n in pz["s2_map"])
        st.markdown(f"<div class='pl-panel'>{lines}</div>", unsafe_allow_html=True)
        st.info("起動する『色の順番』は相手が持っている。順番を聞いて端子記号に置き換えよう。")
    else:
        st.markdown("**起動シーケンス（点灯させる色の順番）:**")
        seq = " <b>→</b> ".join(f"<span style='color:{CMAP[c]}'>{c}</span>" for c in pz["s2_order"])
        st.markdown(f"<div class='pl-panel' style='font-size:1.4rem'>{seq}</div>",
                    unsafe_allow_html=True)
        st.info("各色がどの端子かは相手が持っている。色を伝えて端子記号を教えてもらおう。")
    answer_block(code, role, 2, pz["s2_answer"], "端子記号を起動順に並べて入力",
                 placeholder="例: ACBD")


def stage3(code, role, pz):
    st.subheader("STAGE 3 — 監視室  ★★★☆☆")
    st.caption("片方だけが監視カメラ(グリッド)を見られる。色・形・座標を描写して目標を特定せよ。")
    if role == "p1":
        st.markdown("**監視カメラ映像（5×5。各図形の下に刻印文字）:**")
        st.markdown(f"<div class='pl-panel'>{render_grid_html(pz['s3_grid'])}</div>",
                    unsafe_allow_html=True)
        st.info("どの図形が『目標』かは相手が知っている。色・形・座標を正確に描写しよう。")
    else:
        col, shp = pz["s3_target"]
        st.markdown("**目標指示書:**")
        st.markdown(
            f"<div class='pl-panel' style='font-size:1.3rem'>認証記号が刻まれているのは "
            f"<span style='color:{CMAP[col]}'>{col}い{shp}</span> のマス。</div>",
            unsafe_allow_html=True)
        st.info("グリッドは相手だけが見られる。目標の図形を伝え、刻印文字を読み取ってもらおう。")
    answer_block(code, role, 3, pz["s3_answer"], "目標マスの刻印文字を入力",
                 placeholder="例: A")


def stage4(code, role, pz):
    st.subheader("STAGE 4 — 研究データ解析  ★★★★☆")
    st.caption("復元データが前半・後半に分断されている。両方を突き合わせないと意味をなさない。")
    if role == "p1":
        st.markdown("**復元データ〔前半〕:**")
        st.markdown(
            f"<div class='pl-panel'>……事故当夜、最終施錠を行った人物の記録。<br>"
            f"職員コードの<b>下2桁</b>は <b style='color:#ffd24d'>{pz['s4_front_code']}</b>。"
            f"担当区画は——（以降欠損）</div>", unsafe_allow_html=True)
        st.info("施錠者の『氏名』は後半（相手側）にある。氏名＋コードを統合せよ。")
    else:
        st.markdown("**復元データ〔後半〕:**")
        st.markdown(
            f"<div class='pl-panel'>（前半欠損）——第7研究棟。<br>"
            f"施錠者の氏名は <b style='color:#7fd0ff'>『{pz['s4_back_name']}』</b>。<br>"
            f"以降、当該人物の出勤記録は存在しない……</div>", unsafe_allow_html=True)
        st.info("『職員コード』は前半（相手側）にある。氏名＋コードを統合せよ。")

    answer_block(code, role, 4, pz["s4_answer"], "氏名＋職員コードを入力",
                 placeholder="例: 山田12")

    # 隠しログ (任意 / True・Secret 条件)
    with st.expander("🔍 復元しきれなかった断片がある…"):
        frag = pz["s4_hid_p1"] if role == "p1" else pz["s4_hid_p2"]
        st.markdown(f"判読できた断片: <span class='pl-half'>{frag}</span>",
                    unsafe_allow_html=True)
        st.caption("相手の断片と繋ぎ合わせると、1つの単語になるかもしれない。")
        room = room_snapshot(code)
        if room["hidden_log"]:
            st.success("🩸 裏ログ照合済み — 隠された真相データを確保した。")
        else:
            hg = st.text_input("繋ぎ合わせた単語を照合", key=f"hid_{role}")
            if st.button("裏ログを照合", key=f"hidbtn_{role}"):
                if norm(hg) == norm(pz["s4_hidword"]):
                    set_hidden_log(code)
                    st.toast("🩸 裏ログを確保", icon="🩸")
                    app_rerun()
                else:
                    st.warning("一致しない。両者の断片を正しく繋げてみよう。")


def final_stage(code, role, pz):
    st.subheader("FINAL — 中央制御室  ★★★★★")
    st.caption("これまでの手がかりを統合し、最終認証コードを生成せよ。構成ルールも分割されている。")
    st.markdown("**最終認証コードの構成ルール（両端末共通）:**")
    st.markdown(
        "<div class='pl-panel'>最終コード ＝ <b>①</b> + <b>②</b> + <b>③</b><br>"
        "① = Stage1で解読した語の【先頭1文字】<br>"
        "② = Stage3で読み取った【認証記号】<br>"
        "③ = Stage4で復元した【職員コード下2桁】</div>",
        unsafe_allow_html=True)

    if role == "p1":
        st.markdown(
            f"<div class='pl-panel'>あなたの端末に残る記録:<br>"
            f"・Stage1の語 = <b style='color:#ffd24d'>{pz['final_word']}</b><br>"
            f"・Stage3の認証記号 = <b style='color:#ffd24d'>{pz['final_letter']}</b><br>"
            f"・Stage4のコード = <b>???</b>（相手の端末）</div>", unsafe_allow_html=True)
        st.info("③のコードは相手だけが保持。①②を伝え、③を聞いて連結せよ。")
    else:
        st.markdown(
            f"<div class='pl-panel'>あなたの端末に残る記録:<br>"
            f"・Stage1の語 = <b>???</b>（相手の端末）<br>"
            f"・Stage3の認証記号 = <b>???</b>（相手の端末）<br>"
            f"・Stage4のコード = <b style='color:#7fd0ff'>{pz['final_code4']}</b></div>",
            unsafe_allow_html=True)
        st.info("①②は相手だけが保持。③を伝え、①②を聞いて連結せよ。")

    answer_block(code, role, LAST_STAGE, pz["final_answer"], "最終認証コードを入力",
                 placeholder="例: AB12")


STAGE_FUNCS = {1: stage1, 2: stage2, 3: stage3, 4: stage4, 5: final_stage}


# ==========================================================================
# 画面: 失敗 / エンディング
# ==========================================================================
def fail_screen(code, role):
    poll_change(code)
    st.markdown("## ☠ 施設安定度 0% — 封鎖完了")
    st.error("制御端末が沈黙した。PAIR LOCK は二人を残したまま、永遠に閉ざされた……")
    st.caption("不正解を重ねすぎた。落ち着いて、正確に伝え合うのが脱出の鍵。")
    if st.button("♻ ルームを再起動（同じ施設・最初から）", use_container_width=True):
        restart_room(code)
        app_rerun()


def ending_screen(code, role):
    poll_change(code)
    finalize_ending(code)
    room = room_snapshot(code)
    ending = room["ending"]
    if ending == "true":
        st.markdown("## 🌟 TRUE END — 完全脱出")
        st.success("ノーミスで全認証を突破し、隠された真相ログも回収した。")
        st.markdown(
            "<div class='pl-panel'>二人は外へ出た。手にした裏ログには、"
            "事故が『事故』ではなかった記録が残されていた。<br>"
            "——だが今は、隣にいる相棒と交わした無数の言葉だけで充分だった。</div>",
            unsafe_allow_html=True)
    elif ending == "secret":
        st.markdown("## 🩸 SECRET END — 暴かれた真相")
        st.warning("脱出と引き換えに、PAIR LOCK 事故の真相に触れてしまった。")
        st.markdown(
            "<div class='pl-panel'>裏ログが示していたのは、被験者を『二人一組』で"
            "閉じ込め続けた施設の本当の目的。<br>協力できる者だけが生き残る——"
            "その観察記録の、最新の1行に二人の名が加わった。</div>",
            unsafe_allow_html=True)
    else:
        st.markdown("## ✅ NORMAL END — 脱出成功")
        st.success("二人で全認証を突破し、PAIR LOCK から脱出した。")
        st.markdown(
            "<div class='pl-panel'>片方だけでは、どの扉も開かなかった。<br>"
            "見えないものを言葉にし、相手の言葉で世界を補う——"
            "それだけで、ここは抜けられた。</div>", unsafe_allow_html=True)

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.metric("ミス回数", room["misses"])
    with c2:
        st.metric("最終安定度", f"{room['stability']}%")
    extra = []
    if not room["hidden_log"]:
        extra.append("裏ログ未回収（Stage4の断片を繋ぐと別エンドへ）")
    if room["misses"] > 0:
        extra.append("ノーミスで TRUE END に到達できる")
    if extra:
        st.caption("やりこみ: " + " / ".join(extra))

    st.divider()
    if st.button("♻ もう一度遊ぶ（新しい施設）", use_container_width=True):
        restart_room(code)
        app_rerun()


# ==========================================================================
# 画面: ロビー / 待機
# ==========================================================================
def lobby():
    st.markdown("# 🔒 PAIR LOCK")
    st.caption("二人協力・非対称情報の暗号脱出 ── 想定プレイ時間 15〜25分")
    st.markdown(
        "<div class='pl-panel'>地下研究施設 <b>PAIR LOCK</b> が封鎖された。<br>"
        "脱出には2つの制御端末を<b>同時に</b>操作する必要がある。<br>"
        "だが事故の影響で、各端末には施設情報の<b>半分しか</b>表示されない。<br><br>"
        "<span class='pl-role-p1'>あなたにしか見えない情報</span>と "
        "<span class='pl-role-p2'>相手にしか見えない情報</span>を、"
        "声やチャットで補い合え。片方だけでは絶対に解けない。</div>",
        unsafe_allow_html=True)

    st.info("遊び方: 1人が『ルームを作成』→ 4文字のコードを相手に共有 → "
            "相手は別の端末で『ルームに参加』。2人揃うと開始。")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 🆕 ルームを作成 (P1)")
        if st.button("ルームを作成する", type="primary", use_container_width=True):
            code = create_room()
            st.session_state.pl_code = code
            st.session_state.pl_role = "p1"
            app_rerun()
    with c2:
        st.markdown("#### 🔑 ルームに参加 (P2)")
        join_code = st.text_input("ルームコード (4文字)", key="join_code",
                                  max_chars=4, placeholder="例: 7K2P")
        if st.button("参加する", use_container_width=True):
            code = norm(join_code)
            res = join_room(code)
            if res == "p2":
                st.session_state.pl_code = code
                st.session_state.pl_role = "p2"
                app_rerun()
            elif res == "full":
                st.error("そのルームは既に2人埋まっている。")
            else:
                st.error("ルームが見つからない。コードを確認して。")


@st.fragment(run_every=2)
def waiting_for_join(code: str, role: str):
    room = room_snapshot(code)
    if room is None:
        st.warning("ルームが解散された。")
        if st.button("ロビーに戻る"):
            leave_room()
            app_rerun()
        return
    if room["p1_joined"] and room["p2_joined"]:
        app_rerun()
        return
    st.markdown("# 🛰 相手の接続を待っています…")
    st.markdown(f"### ルームコード: <span style='color:#ffd24d'>{code}</span>",
                unsafe_allow_html=True)
    st.caption("このコードを相手に伝え、別の端末から『ルームに参加』してもらおう。")
    st.caption("接続を待機中 …")


# ==========================================================================
# サイドバー
# ==========================================================================
def sidebar():
    with st.sidebar:
        code = st.session_state.get("pl_code")
        if code:
            st.markdown("### 🔒 PAIR LOCK")
            st.markdown(f"ROOM **{code}**")
            st.markdown(role_tag(st.session_state.get("pl_role", "p1")),
                        unsafe_allow_html=True)
            st.divider()
            if st.button("🚪 ルームを出る", use_container_width=True):
                leave_room()
                app_rerun()
        else:
            st.markdown("### 🔒 PAIR LOCK")
            st.caption("2人協力・非対称情報の脱出ゲーム。")


# ==========================================================================
# メイン
# ==========================================================================
def main():
    st.markdown(CSS, unsafe_allow_html=True)
    sidebar()

    code = st.session_state.get("pl_code")
    role = st.session_state.get("pl_role")

    # 未入室 → ロビー
    if not code:
        lobby()
        return

    room = room_snapshot(code)
    if room is None:
        st.warning("ルームが解散された。ロビーに戻ります。")
        leave_room()
        if st.button("ロビーへ"):
            app_rerun()
        return

    # 相手の参加待ち
    if not (room["p1_joined"] and room["p2_joined"]):
        waiting_for_join(code, role)
        return

    # 失敗判定
    if room["stability"] <= 0:
        st.session_state.pl_seen_stage = room["stage"]
        fail_screen(code, role)
        return

    # クリア → エンディング
    if room["stage"] > LAST_STAGE:
        st.session_state.pl_seen_stage = room["stage"]
        ending_screen(code, role)
        return

    # 通常: ステージ進行
    st.session_state.pl_seen_stage = room["stage"]
    live_sync(code, role)
    st.divider()
    pz = build_puzzle(room["seed"])
    STAGE_FUNCS[room["stage"]](code, role, pz)


main()
