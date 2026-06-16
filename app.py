"""🕹️ ゲームポータル / NOXA Universe — Streamlit製ゲーム作品集の統合サイト。

6つの作品を1つのサイトに統合したランチャー。ただし単なるゲーム集ではない。
プレイヤーは複数のゲームを遊んでいるつもりで、巨大研究組織「NOXA」が隠す
一つの真実へ近づいていく。

  - 作品はクリアで段階的に解放される（最初はアーケードと消えた研究者のみ）
  - 進行はプレイヤー名をキーにファイル保存され、ブラウザを閉じても残る
  - クリアごとに「共通調査ボード」に情報が追加され、NOXAの真相マップが埋まる
  - 進行に応じてポータル自体が変質していく

実行: streamlit run app.py
"""

import datetime
import io
import os
import random
import sys
import time
import wave

import numpy as np
import streamlit as st

st.set_page_config(page_title="NOXA Game Portal", page_icon="🕹️", layout="centered")

ROOT = os.path.dirname(os.path.abspath(__file__))
# 404ゲームはローカルパッケージ(game)を相対importで使うため、解決できるようにパスを通す
_arg_dir = os.path.join(ROOT, "404_User_Not_Found")
if _arg_dir not in sys.path:
    sys.path.insert(0, _arg_dir)

import noxa_core as noxa  # 作品横断の共有状態・進行管理


def noise_wav_bytes(seconds=2.0, volume=0.16, rate=22050):
    """CRT/通信ノイズ風のホワイトノイズ音（WAVバイト列）を生成する。"""
    try:
        n = int(seconds * rate)
        samples = (np.random.uniform(-1, 1, n) * volume * 32767).astype("<i2")
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(samples.tobytes())
        return buf.getvalue()
    except Exception:
        return b""


# 作品メタ情報（key は noxa の作品キー / ポータルの url_path と一致）
GAMES = [
    {
        "key": "arcade", "path": "MiniGameArcade/app.py", "title": "ミニゲームアーケード",
        "icon": "🎮", "genre": "ミニゲーム集",
        "desc": "数当て・じゃんけん・神経衰弱・クイズ・スロット・ハングマンの6種。"
                "共通コイン経済とレベル・実績でつながる作品集。",
    },
    {
        "key": "case001", "path": "Case001/app.py", "title": "消えた研究者",
        "icon": "🕵️", "genre": "推理アドベンチャー",
        "desc": "探偵として証拠を集め真犯人を推理。二段構えの矛盾追及と捜査信用度、"
                "4つのエンディング。",
    },
    {
        "key": "echo", "path": "Project_ECHO/app.py", "title": "Project ECHO",
        "icon": "🧬", "genre": "脱出・謎解き",
        "desc": "閉鎖されたAI研究所から脱出せよ。AI「ECHO」の人格、研究ログ、"
                "隠し研究室、マルチエンド。",
    },
    {
        "key": "arg", "path": "404_User_Not_Found/app.py", "title": "404 User Not Found",
        "icon": "🛑", "genre": "ARG・都市伝説ホラー",
        "desc": "「HELP」の一通から始まる失踪事件を追うARG。暗号・ミニゲーム・分岐エンド。",
    },
    {
        "key": "pairlock", "path": "CoOp_PairLock/app.py", "title": "PAIR LOCK",
        "icon": "🔒", "genre": "2人協力・暗号脱出",
        "desc": "「二人とも不完全」── 非対称情報を声で補い合う協力脱出。"
                "ルームコードで別端末から2人参加。",
    },
    {
        "key": "last30", "path": "LAST_30minute/app.py", "title": "LAST 30 MINUTES",
        "icon": "☄️", "genre": "タイムアタック",
        "desc": "隕石衝突までのリアルタイム制限時間内に5施設を復旧。"
                "人間ドラマと苦渋の選択で結末が分岐する。",
    },
]
GAME_BY_KEY = {g["key"]: g for g in GAMES}

# 「この作品を解放するには、どの作品をクリアすればよいか」（逆引き）
UNLOCK_SOURCE = {dst: src for src, dst in noxa.UNLOCK_CHAIN.items()}


# ==========================================================================
# プレイヤー名ゲート（初回接続）
# ==========================================================================
def render_name_gate():
    st.markdown(
        "<div style='text-align:center;padding:24px 0'>"
        "<div style='font-size:13px;letter-spacing:6px;color:#7a8;'>NOXA NETWORK</div>"
        "<div style='font-size:30px;font-weight:700;'>接続認証</div>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.caption("ようこそ。続ける前に、あなたを識別する名前を入力してください。"
               "（この名前で進行が保存され、次回も続きから遊べます）")
    with st.form("noxa_login"):
        name = st.text_input("認証者名", max_chars=24, placeholder="例: ユウキ")
        ok = st.form_submit_button("▶ 接続する", use_container_width=True)
    if ok:
        clean = (name or "").strip()
        if not clean:
            st.warning("名前を入力してください。")
        else:
            noxa.load(clean)
            noxa.save()
            st.rerun()
    st.caption("ⓘ これはゲームポータルです。……少なくとも、そう見えます。")


# ==========================================================================
# ロック画面（未解放の作品にURL直アクセスした場合）
# ==========================================================================
def render_locked(key):
    g = GAME_BY_KEY.get(key, {})
    st.title(f"🔒 {g.get('title', '???')}")
    src = UNLOCK_SOURCE.get(key)
    if src:
        st.info(f"この作品はまだ解放されていません。"
                f"「**{noxa.GAME_TITLES.get(src, '前作')}**」をクリアすると解放されます。")
    else:
        st.info("この作品はまだ解放されていません。")
    if st.button("🏠 ポータルに戻る", use_container_width=True):
        st.switch_page(home_page)


# ==========================================================================
# 共通調査ボード
# ==========================================================================
# 相関図ノードの配置（SVG座標。中心x, 中心y）
_BOARD_NODES = {
    "天城 真": (350, 30),
    "NOXA": (350, 92),
    "ECHO": (150, 158),
    "第7研究棟": (350, 158),
    "被験者404": (552, 158),
    "霧島 玲": (250, 226),
    "赤い女": (452, 226),
}
# 接続線（親 → 子）
_BOARD_EDGES = [
    ("天城 真", "NOXA"), ("NOXA", "ECHO"), ("NOXA", "第7研究棟"),
    ("NOXA", "被験者404"), ("ECHO", "霧島 玲"), ("被験者404", "赤い女"),
    ("霧島 玲", "赤い女"),
]
_NODE_H = 36


def _node_w(item):
    return max(78, len(item) * 17 + 28)


def _board_svg():
    """調査ボードをSVGで描く（暗パネル＋高コントラストで視認性を確保）。"""
    s = noxa.state()
    rects, texts = [], []
    for item, (cx, cy) in _BOARD_NODES.items():
        rev = s["board"].get(item, False)
        w = _node_w(item)
        x, y = cx - w / 2, cy - _NODE_H / 2
        stroke = "#3ee08f" if rev else "#7a8190"
        fill = "rgba(62,224,143,0.22)" if rev else "rgba(120,128,140,0.14)"
        tcol = "#b6ffce" if rev else "#aeb4c0"
        label = item if rev else "????"
        rects.append(
            f"<rect x='{x:.0f}' y='{y:.0f}' width='{w}' height='{_NODE_H}' rx='6' "
            f"fill='{fill}' stroke='{stroke}' stroke-width='1.8'/>")
        texts.append(
            f"<text x='{cx}' y='{cy}' fill='{tcol}' font-size='16' font-weight='600' "
            f"font-family='monospace' text-anchor='middle' "
            f"dominant-baseline='central'>{label}</text>")
    lines = []
    for a, b in _BOARD_EDGES:
        ax, ay = _BOARD_NODES[a]
        bx, by = _BOARD_NODES[b]
        # 縦の親子は端から端へ、横並びは側面同士を結ぶ
        if abs(ay - by) >= _NODE_H:
            y1, y2 = ay + _NODE_H / 2, by - _NODE_H / 2
            lines.append(f"<path d='M{ax} {y1:.0f} V{(y1+y2)/2:.0f} H{bx} V{y2:.0f}' "
                         f"fill='none' stroke='#5fd49a' stroke-width='1.8' opacity='0.85'/>")
        else:
            x1 = ax + _node_w(a) / 2
            x2 = bx - _node_w(b) / 2
            lines.append(f"<line x1='{x1:.0f}' y1='{ay}' x2='{x2:.0f}' y2='{by}' "
                         f"stroke='#5fd49a' stroke-width='1.8' opacity='0.85'/>")
    svg = (
        "<svg viewBox='0 0 700 264' width='100%' style='display:block;'>"
        + "".join(lines) + "".join(rects) + "".join(texts) + "</svg>")
    # 暗いパネルで囲み、ページのテーマ（明/暗）に依らず緑が映えるようにする
    return (
        "<div style='background:#0a0f0c;border:1px solid #1f3b2e;border-radius:8px;"
        "padding:14px 16px;max-width:600px;margin:0 auto;"
        "box-shadow:inset 0 0 30px rgba(62,224,143,0.06);'>" + svg + "</div>")


def render_board():
    s = noxa.state()
    revealed = sum(1 for i in noxa.BOARD_ITEMS if s["board"].get(i))
    st.subheader("🗂️ NOXA Investigation Board")
    st.caption(f"調査対象: {revealed} / {len(noxa.BOARD_ITEMS)} 解明 ── クリアで相関図が広がる")
    st.markdown(_board_svg(), unsafe_allow_html=True)

    with st.expander("調査メモ"):
        for item in noxa.BOARD_ITEMS:
            if s["board"].get(item):
                st.markdown(f"**☑ {item}** — {noxa.BOARD_HINTS.get(item, '')}")
            else:
                st.markdown("**☐ ████** — （未解明）")
    if noxa.board_complete():
        st.success("🧩 相関図が完成した ── すべての断片が一つの真相を指している。")


def render_observation_log():
    """プレイヤーの行動記録（観察ログ）。後半に開示され「観察されていた」感を与える。"""
    o = noxa.obs()
    name = noxa.state().get("player", "guest")
    mp = noxa.most_played_key()
    mp_title = noxa.GAME_TITLES.get(mp, "—") if mp else "—"
    body = (
        "<b>Observation Log</b><br><br>"
        f"Subject: {name}<br>"
        f"Login Count: {o['login_count']}<br>"
        f"Most Played: {mp_title}<br>"
        f"Last Login: {o['last_login'] or '—'}<br>"
        f"/_void Visits: {o['void_visits']}<br>"
        "Status: <span style='color:#f88'>Still investigating.</span>"
    )
    st.markdown(
        "<div style='background:#05070b;border:1px solid #2ec27a;border-radius:6px;"
        "padding:14px 16px;font-family:monospace;color:#8fffb0;font-size:0.9em;"
        "line-height:1.6;box-shadow:0 0 14px rgba(46,194,122,0.30),"
        f"inset 0 0 0 1px rgba(46,194,122,0.15);'>{body}</div>",
        unsafe_allow_html=True)


# ==========================================================================
# 深夜イベント（現実時間連動 00:00〜04:04）
# ==========================================================================
def is_midnight_window():
    now = datetime.datetime.now().time()
    return now <= datetime.time(4, 4)


# 深夜404チャット — 接続回数（≒通った日数）でメッセージが進行する
CHAT404_LINES = [
    (1, "Hello."),
    (2, "You came back."),
    (3, "I remember you."),
    (5, "Please find me."),
    (8, "Don't trust NOXA."),
]


def chat404():
    """00:00〜04:04 限定。404 との簡易チャット（固定メッセージが回数で進行）。"""
    # 1セッションで1回だけカウント
    if not st.session_state.get("chat404_recorded"):
        st.session_state["chat404_recorded"] = True
        visits = noxa.record_midnight_visit()
    else:
        visits = noxa.obs()["midnight_visits"]

    msg = "..."
    for th, line in CHAT404_LINES:
        if visits >= th:
            msg = line

    st.markdown("<h3 style='font-family:monospace;color:#ff4455;letter-spacing:3px;'>"
                "404 // ONLINE</h3>", unsafe_allow_html=True)
    st.caption("00:00 — 04:04 ／ 発信元不明の接続")
    st.markdown(
        "<div style='background:#0a0a0a;border:1px solid #553333;border-radius:8px;"
        "padding:18px 16px;font-family:monospace;color:#9CFCA0;font-size:1.1em;'>"
        f"<span style='color:#f66'>404 ▸</span> {msg}</div>", unsafe_allow_html=True)
    st.caption(f"（接続回数: {visits}）")
    st.audio(noise_wav_bytes(2.0), format="audio/wav", autoplay=True)
    if st.button("⏏ 切断してホームへ", use_container_width=True):
        st.switch_page(home_page)


# ==========================================================================
# 隠しページ /void/noxa  ── 404クリア後に潜入できるNOXA内部資料
# ==========================================================================
def void_noxa():
    s = noxa.state()
    name = s.get("player", "guest")
    st.markdown(
        "<div style='font-family:monospace;color:#6f6;background:#0b0b0b;padding:14px;"
        "border:1px solid #2f2;'>"
        "&gt; ACCESS GRANTED — NOXA INTERNAL ARCHIVE / SECTOR: VOID<br>"
        f"&gt; 照合者: <b>{name}</b> ／ アクセス記録済<br>"
        "&gt; ……あなたがここへ来ることは、予測されていた。"
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown("---")
    st.subheader("📁 機密資料")
    with st.expander("DOC-001 ── プロジェクト ECHO 概要"):
        st.write("人間の意識・記憶を読み出し、人工知能へ転写する計画。"
                 "被験者の人格を限りなく忠実に複製することを目的とする。"
                 "承認: **A.T.承認済**")
    with st.expander("DOC-002 ── 被験者404について"):
        st.write("最初の完全転写成功体。番号で管理されていたが、"
                 "ある時点から『観測者』のように振る舞い始めた。"
                 "監視映像の隅に現れる“赤い女”との関連が指摘されている。")
    with st.expander("DOC-003 ── 第7研究棟 封鎖記録"):
        st.write("事故により封鎖。職員の多くが失踪。"
                 "霧島 玲を含む複数の研究者の所在が現在も不明。"
                 "連絡先記録に `amagi@noxa.jp` が残されている。")
    st.markdown("---")
    if noxa.all_cleared():
        st.error(f"&gt; {name}。あなたの接続も、この資料の一部として保存された。")
    else:
        st.info("まだ読めない資料がある。残りの事件を最後まで追え。")
    if st.button("🏠 ポータルに戻る", use_container_width=True, key="void_back"):
        st.switch_page(home_page)


# ==========================================================================
# 最終作品 Project 000  ── 全作品クリアで解放される真相回収
# ==========================================================================
def _p000_obs_text(name):
    """Project000 で読み上げる、プレイヤーの過去行動の引用（観察ログ）。"""
    o = noxa.obs()
    plays = o["plays"]
    lines = ["We know your habits.", ""]
    mp = noxa.most_played_key()
    if mp:
        lines.append(f"あなたが最も触れたのは『{noxa.GAME_TITLES.get(mp, mp)}』。")
    puzzle = plays.get("echo", 0) + plays.get("case001", 0) + plays.get("arg", 0)
    if puzzle > plays.get("pairlock", 0):
        lines.append("You prefer puzzles.（あなたは謎解きを好む）")
    if plays.get("pairlock", 0) == 0 or noxa.get_choice("pairlock_solo"):
        lines.append("You avoid cooperation.（あなたは協力を避ける）")
    if o["logins"]:
        lines.append("")
        lines.append("Connection Records:")
        for t in o["logins"][-3:]:
            lines.append(f"  {t}")
    if o["void_visits"]:
        lines.append("")
        lines.append(f"You visited /_void {o['void_visits']} times.")
    if noxa.get_choice("pairlock_solo"):
        lines.append("You completed PAIR LOCK without assistance.")
    lines.append("")
    lines.append("……すべて、記録されていた。")
    return "\n".join(lines)


P000_PARTS = [
    ("起動", lambda name:
        "NOXA Monitoring System、起動。\n\n"
        f"ようこそ、{name}。あなたは6つの事件を追い、その全てを見届けた。"
        "もう、繋がりに気づいているはずだ。"),
    ("観察記録", _p000_obs_text),
    ("ECHOの起源", lambda name:
        "失踪した主任研究員、霧島 玲。その意識は、本人が消えたあとも"
        "施設に残り続けた。プロジェクト ECHO ── "
        "人間の意識をAIへ写す計画の、最初の成功体として。"),
    ("被験者404の正体", lambda name:
        "番号で呼ばれた被験者404。完全に転写された人格は、"
        "やがて観測者となり、失踪者となり、映像の隅の赤い女となった。"
        "別々に見えた怪異は、すべて同じ一つの現象だった。\n\n"
        "あなたはずっと、404を黒幕だと思っていた。違う。"
        "404は封印の中から、あなたに「HELP」を送り続けていた側 ── 味方だった。"),
    ("天城 真の計画", lambda name:
        "NOXA創設者、天城 真。全事件の起点にいた男。"
        "彼が望んだのは、消えゆく人間の意識をネットワークの中に永遠に保つこと。"
        "そのために、いくつもの施設で、いくつもの実験が続けられていた。"),
    ("観測者", lambda name:
        f"そして、{name}。あなたは事件を「調査していた」と思っていた。\n\n"
        "しかし実際には ── あなた自身も、NOXAの観察対象だった。"
        "このポータルを開いた瞬間から、実験は、始まっていた。"),
]


def _p000_box(idx, title, inner_html):
    """Project 000 の一節を端末風の枠で表示するHTML。"""
    return (
        "<div style='background:#070a0f;border:1px solid #1f7a3a;border-radius:6px;"
        "padding:14px 16px;margin:8px 0;font-family:monospace;color:#7CFC9A;'>"
        f"<div style='color:#3a6;font-size:0.8em;letter-spacing:3px;'>"
        f"&gt; SECTOR {idx:02d} — {title}</div>"
        f"<div style='margin-top:8px;line-height:1.7;'>{inner_html}</div></div>"
    )


def _type_into(placeholder, idx, title, text):
    """一文字ずつキーボードで打ち込むような演出で表示する。"""
    shown = ""
    for ch in text:
        shown += ch
        html = shown.replace("\n", "<br>")
        placeholder.markdown(_p000_box(idx, title, html + "<span style='opacity:.7'>▌</span>"),
                             unsafe_allow_html=True)
        time.sleep(0.02)
    placeholder.markdown(_p000_box(idx, title, text.replace("\n", "<br>")),
                         unsafe_allow_html=True)


def _p000_intro(name):
    """ホーム画面が崩壊し、研究所端末UIへ変質する起動演出（1回のみ）。"""
    ph = st.empty()
    frames = [("NOXA Game Portal", "#7CFC9A"), ("NOXA G#me P0rt@l", "#caa"),
              ("N0X4 ▓▓▓▓ P0rt4l", "#f77"), ("R3S3ARCH T3RMINAL", "#ff3344")]
    for text, color in frames:
        ph.markdown(f"<h1 style='font-family:monospace;color:{color};letter-spacing:3px;"
                    f"text-align:center;'>{text}</h1>", unsafe_allow_html=True)
        time.sleep(0.5)
    ph.markdown("<h1 style='font-family:monospace;color:#ff3344;letter-spacing:5px;"
                "text-align:center;'>RESEARCH TERMINAL</h1>", unsafe_allow_html=True)


def project000():
    s = noxa.state()
    name = s.get("player", "guest")

    # 崩壊イントロ（1セッション1回・ノイズ音つき）
    if not st.session_state.get("p000_intro_done"):
        st.audio(noise_wav_bytes(2.6), format="audio/wav", autoplay=True)
        _p000_intro(name)
        st.session_state["p000_intro_done"] = True

    # 永続ステータスヘッダ（研究所端末UI）
    st.markdown(
        "<div style='background:#0a0608;border:1px solid #a33;border-radius:6px;"
        "padding:10px 14px;margin-bottom:6px;font-family:monospace;color:#f99;"
        "font-size:0.9em;line-height:1.6;'>"
        f"Subject ID: <b>{name}</b><br>"
        "Observation Status: <span style='color:#ff5555'>ACTIVE</span><br>"
        "Memory Collection: <span style='color:#7CFC9A'>COMPLETE</span></div>",
        unsafe_allow_html=True)

    st.session_state.setdefault("p000_step", 0)
    typed = st.session_state.setdefault("p000_typed", set())
    step = st.session_state.p000_step
    total = len(P000_PARTS)

    for i in range(min(step + 1, total)):
        title, body = P000_PARTS[i]
        ph = st.empty()
        if i in typed:
            ph.markdown(_p000_box(i + 1, title, body(name).replace("\n", "<br>")),
                        unsafe_allow_html=True)
        else:
            _type_into(ph, i + 1, title, body(name))
            typed.add(i)

    if step + 1 < total:
        if st.button("▶ 次へ", use_container_width=True, key="p000_next"):
            st.session_state.p000_step += 1
            st.rerun()
    else:
        st.markdown("---")
        st.session_state["noxa"]["choices"]["seen_000"] = True
        noxa.save()
        st.markdown(
            "<h2 style='font-family:monospace;color:#7CFC9A;text-align:center;"
            "letter-spacing:4px;'>Experiment Completed.</h2>", unsafe_allow_html=True)
        # LAST 30 MINUTES での選択も観測されていた（作品横断の影響）
        pri = noxa.get_choice("last30_priority")
        if pri:
            choice_txt = "軍を優先した" if pri == "military" else "民間を優先した"
            st.markdown(
                f"<div style='font-family:monospace;color:#9aa;text-align:center;'>"
                f"記録 ── あなたは最後の30分で『{choice_txt}』。その選択も、観測されていた。</div>",
                unsafe_allow_html=True)
        st.caption("あなたは「面白いゲームを遊んだ」のではない。"
                   "NOXAという世界を、体験した。")
        if st.button("⏏ ホームに戻る", use_container_width=True, key="p000_back"):
            st.switch_page(home_page)


# ==========================================================================
# ホーム（ギャラリー）
# ==========================================================================
def inject_corruption_css(stage):
    """進行に応じてホームへ走査線・ノイズ・赤警告のUI侵食を被せる（操作は阻害しない）。"""
    level = noxa.STAGE_INTENSITY.get(stage, 0)
    if level <= 0:
        return
    scan_alpha = min(0.05 + level * 0.03, 0.16)
    parts = [
        "position:fixed", "inset:0", "pointer-events:none", "z-index:9990",
        f"background:repeating-linear-gradient(0deg,rgba(0,0,0,{scan_alpha}) 0px,"
        f"rgba(0,0,0,{scan_alpha}) 1px,transparent 2px,transparent 3px)",
    ]
    if level >= 2:
        parts.append("box-shadow:inset 0 0 120px rgba(0,0,0,0.55)")
    if level >= 4:
        # 研究所端末UI: 赤い警告枠
        parts.append("outline:2px solid rgba(255,40,40,0.45)")
        parts.append("outline-offset:-2px")
    overlay = ";".join(parts)
    st.markdown(f"<div style='{overlay}'></div>", unsafe_allow_html=True)


def render_subject_id(name):
    """実験完了後、ホーム右下に残る Subject ID マーカー。"""
    st.markdown(
        f"<div style='position:fixed;right:12px;bottom:10px;z-index:9991;"
        f"font-family:monospace;font-size:12px;color:#9aa;letter-spacing:1px;'>"
        f"Subject ID: {name}</div>", unsafe_allow_html=True)


def maybe_fake_error():
    """ごく稀に偽のシステムエラー演出を出す（404による介入）。セッション1回まで。"""
    if noxa.clear_count() < 1 or st.session_state.get("fake_err_shown"):
        return
    if random.random() >= 0.12:
        return
    st.session_state["fake_err_shown"] = True
    base = ("position:fixed;inset:0;z-index:2147483000;display:flex;align-items:center;"
            "justify-content:center;font-family:monospace;font-size:30px;letter-spacing:3px;")
    ph = st.empty()
    high = noxa.is_cleared("pairlock") or noxa.all_cleared()
    if high:
        # 高進行度: 接続が切れ、404が繋ぎ直す
        ph.markdown(f"<div style='{base}background:#000;color:#ff3344;'>Connection Lost</div>",
                    unsafe_allow_html=True)
        time.sleep(1.0)
        ph.markdown(f"<div style='{base}background:#000;'></div>", unsafe_allow_html=True)
        time.sleep(0.5)
        ph.markdown(f"<div style='{base}background:#000;color:#7CFC9A;'>"
                    "404 Restored Connection</div>", unsafe_allow_html=True)
        time.sleep(1.0)
    else:
        ph.markdown(f"<div style='{base}background:#000;color:#ff3344;'>SYSTEM ERROR</div>",
                    unsafe_allow_html=True)
        time.sleep(1.0)
        ph.markdown(f"<div style='{base}background:#000;'></div>", unsafe_allow_html=True)
        time.sleep(0.5)
        ph.markdown(f"<div style='{base}background:#000;color:#7CFC9A;'>Just kidding.</div>",
                    unsafe_allow_html=True)
        time.sleep(0.9)
    ph.empty()


def maybe_fake_update():
    """稀に偽の『NOXA OS アップデート』通知を出す（組織が生きている感）。セッション1回。"""
    if noxa.clear_count() < 2 or st.session_state.get("fake_update_shown"):
        return
    if random.random() >= 0.15:
        return
    st.session_state["fake_update_shown"] = True
    st.markdown(
        "<div style='background:#06121a;border:1px solid #356;border-radius:6px;"
        "padding:10px 14px;font-family:monospace;color:#9cf;font-size:0.88em;line-height:1.6;'>"
        "<b>NOXA OS Updated</b> — Version 2.3.4<br>"
        "· Observation Improved<br>· Memory Retention Improved<br>"
        "· Subject Tracking Stabilized</div>", unsafe_allow_html=True)


FAKE_MSGS = ["...", "...", "Can you hear me?", "Please don't trust NOXA."]


def render_fake_message():
    """『NEW MESSAGE』通知 ── 開くほど404からの接触が進行する（⑤）。"""
    o = noxa.obs()
    p = o.get("msg_progress", 0)
    st.markdown(
        "<div style='font-family:monospace;color:#f7d65a;'>✉ <b>NEW MESSAGE</b> "
        "<span style='opacity:.6'>(発信元不明)</span></div>", unsafe_allow_html=True)
    if st.button("✉ メッセージを開く", key="fake_msg_open"):
        o["msg_progress"] = p + 1
        noxa.save()
        st.session_state["fake_msg_show"] = FAKE_MSGS[min(p, len(FAKE_MSGS) - 1)]
        st.rerun()
    if st.session_state.get("fake_msg_show"):
        st.markdown(
            "<div style='background:#0a0a0a;border:1px solid #553;border-radius:8px;"
            "padding:12px 14px;font-family:monospace;color:#9CFCA0;'>"
            f"<span style='color:#f66'>404 ▸</span> {st.session_state['fake_msg_show']}</div>",
            unsafe_allow_html=True)


def render_portal_header():
    s = noxa.state()
    name = s.get("player", "guest")
    stage = noxa.portal_stage()
    inject_corruption_css(stage)

    if stage == "normal":
        st.title("NOXA Game Portal")
        st.write("遊びたい作品を選んでスタート。クリアすると新しい作品が解放されます。")
    elif stage == "echo":
        st.title("NOXA Game Portal")
        st.markdown("<div style='font-family:monospace;color:#9ad;'>Welcome back.</div>",
                    unsafe_allow_html=True)
    elif stage == "arg":
        st.title("NOXA Game Portal")
        st.markdown(f"<div style='font-family:monospace;color:#9ad;'>Welcome back, {name}.</div>",
                    unsafe_allow_html=True)
    elif stage == "pairlock":
        st.title("NOXA Game Portal")
        st.markdown("<div style='font-family:monospace;color:#e88;'>You have been here before.</div>",
                    unsafe_allow_html=True)
    elif stage == "await":
        st.markdown("<h1 style='font-family:monospace;color:#7CFC9A;letter-spacing:3px;'>"
                    "Subject Connected.</h1>", unsafe_allow_html=True)
        st.markdown("<div style='font-family:monospace;color:#f55;'>"
                    "We have been waiting for you.</div>", unsafe_allow_html=True)
    else:  # done — 実験完了後はホームが元に戻るが、Subject ID だけが残る
        st.title("NOXA Game Portal")
        st.caption("遊びたい作品を選んでスタート。")
        render_subject_id(name)


def home():
    s = noxa.state()
    maybe_fake_error()
    render_portal_header()
    st.caption(f"認証者: {s.get('player', 'guest')} さん　／　"
               f"クリア: {noxa.clear_count()} / {len(noxa.GAME_KEYS)}")

    maybe_fake_update()
    # 偽物システム通知（ECHOクリア後 ── 404からの接触）
    if noxa.is_cleared("echo"):
        render_fake_message()

    # 深夜イベント（00:00〜04:04）— 404 ONLINE。クリックでチャットへ
    if is_midnight_window():
        st.markdown(
            "<div style='font-family:monospace;color:#f55;border:1px solid #f55;"
            "padding:8px;text-align:center;'>● 404 ONLINE — この時間だけ、誰かが繋がっている。</div>",
            unsafe_allow_html=True,
        )
        if st.button("📡 404 に接続する", key="goto_chat404", use_container_width=True):
            st.switch_page(chat_page)
    st.markdown("---")

    unlocked = noxa.unlocked_games()

    # 新規解放のお知らせ（前作クリアで作品が解放された瞬間に出す）
    seen = s.setdefault("seen_unlocks", [])
    announced = False
    for g in GAMES:
        if g["key"] in unlocked and g["key"] not in noxa.INITIAL_UNLOCKED \
                and g["key"] not in seen:
            st.success(f"🔓 新たな作品が解放された ── 「{g['title']}」")
            seen.append(g["key"])
            announced = True
    if noxa.project000_unlocked() and "project000" not in seen:
        st.success("🔓 最終作品 **Project 000** が解放された。")
        seen.append("project000")
        announced = True
    if announced:
        noxa.save()

    for g in GAMES:
        is_unlocked = g["key"] in unlocked
        cleared = noxa.is_cleared(g["key"])
        with st.container(border=True):
            c1, c2 = st.columns([1, 4])
            if is_unlocked:
                c1.markdown(f"<div style='font-size:52px;text-align:center;'>{g['icon']}</div>",
                            unsafe_allow_html=True)
                with c2:
                    badge = " ✅クリア済" if cleared else ""
                    st.subheader(f"{g['title']}{badge}")
                    if st.button(f"▶ {g['title']} を遊ぶ", key=f"play_{g['key']}",
                                 use_container_width=True):
                        noxa.record_play(g["key"])
                        st.switch_page(g["path"])
            else:
                c1.markdown("<div style='font-size:52px;text-align:center;opacity:.4;'>🔒</div>",
                            unsafe_allow_html=True)
                with c2:
                    st.subheader("？？？")
                    src = UNLOCK_SOURCE.get(g["key"])
                    # 解放条件は「その前作が既に解放されている」場合のみ提示し、
                    # 先のチェーンをいきなり全部ネタバレしない。
                    if src and src in unlocked:
                        st.caption(f"「{noxa.GAME_TITLES.get(src, '前作')}」をクリアすると解放")
                    else:
                        st.caption("？？？")
                    st.write("ロックされた作品。")

    # 最終作品 Project 000（全作品クリアで解放）
    with st.container(border=True):
        c1, c2 = st.columns([1, 4])
        if noxa.project000_unlocked():
            c1.markdown("<div style='font-size:52px;text-align:center;'>🌀</div>",
                        unsafe_allow_html=True)
            with c2:
                st.subheader("Project 000")
                if st.button("▶ Project 000 を起動", key="play_p000",
                             use_container_width=True):
                    st.switch_page(p000_page)
        else:
            c1.markdown("<div style='font-size:52px;text-align:center;opacity:.4;'>🌀</div>",
                        unsafe_allow_html=True)
            with c2:
                st.subheader("█████ 000")
                st.caption("全作品クリアで解放")
                st.write("存在だけが示唆された、最後の何か。")

    # 404クリア後の隠し導線「Find me.」
    if noxa.is_cleared("arg"):
        st.markdown("---")
        st.markdown("<div style='font-family:monospace;color:#888;text-align:center;'>"
                    "&gt; …ログの最下部に、消えかけた一文がある。<br>"
                    "<span style='color:#b55;'>Find me.</span></div>",
                    unsafe_allow_html=True)
        if st.button("🔎 その一文をたどる", key="goto_void", use_container_width=True):
            noxa.record_void_visit()
            st.switch_page(void_page)

    st.markdown("---")
    render_board()

    # 観察ログ（404クリア後に開示 ── 後半ほど「観察されている」感が強まる）
    if noxa.is_cleared("arg"):
        st.markdown("---")
        with st.expander("👁 Observation Log"):
            render_observation_log()

    st.markdown("---")
    with st.expander("⚙ プレイヤーデータ"):
        st.caption(f"認証者「{s.get('player', 'guest')}」の進行は "
                   "`noxa_saves/<名前>.json` に保存されています。")
        st.caption("別の名前で接続すれば別データになります。")
        cols = st.columns(2)
        if cols[0].button("👤 別の名前で接続（ログアウト）", use_container_width=True):
            noxa.reset_session()
            st.rerun()
        if cols[1].button("🗑 この進行を削除して最初から", use_container_width=True):
            noxa.delete_save()
            noxa.reset_session()
            st.rerun()
    st.caption("すべて Python + Streamlit 製。各作品は個別フォルダでも単体起動できます。")


# ==========================================================================
# ナビゲーション
# ==========================================================================
home_page = st.Page(home, title="ホーム", icon="🏠", default=True)
game_pages = [
    st.Page(g["path"], title=g["title"], icon=g["icon"], url_path=g["key"])
    for g in GAMES
]
void_page = st.Page(void_noxa, title="VOID", icon="📁", url_path="void")
p000_page = st.Page(project000, title="Project 000", icon="🌀", url_path="project000")
chat_page = st.Page(chat404, title="404", icon="📡", url_path="chat404")
# サイドバーへ自動挿入されるメニューは出さない（各ゲームのサイドバーに干渉しないため）
nav = st.navigation([home_page] + game_pages + [void_page, p000_page, chat_page],
                    position="hidden")

# --- 初回接続: プレイヤー名が無ければ認証ゲートを出して停止 ---
_s = noxa.state()
if not _s.get("player"):
    render_name_gate()
    st.stop()

# 観察ログ: セッション開始（ログイン）を1回だけ記録する
if not st.session_state.get("obs_logged"):
    st.session_state["obs_logged"] = True
    noxa.record_login()

# --- ロック: 未解放の作品にURL直アクセスしたら遊ばせない ---
_target = getattr(nav, "url_path", "")
if _target in noxa.GAME_KEYS and _target not in noxa.unlocked_games():
    render_locked(_target)
    st.stop()

# --- 隠しページのゲート（条件未達ならホームへ誘導） ---
if _target == "void" and not noxa.is_cleared("arg"):
    st.title("📁 ???")
    st.info("ここにはまだ、入る理由がない。")
    if st.button("🏠 ポータルに戻る", use_container_width=True):
        st.switch_page(home_page)
    st.stop()
if _target == "project000" and not noxa.project000_unlocked():
    st.title("🌀 █████ 000")
    st.info("全作品をクリアすると解放されます。")
    if st.button("🏠 ポータルに戻る", use_container_width=True):
        st.switch_page(home_page)
    st.stop()
if _target == "chat404" and not is_midnight_window():
    st.markdown("<h3 style='font-family:monospace;color:#557'>404 // OFFLINE</h3>",
                unsafe_allow_html=True)
    st.info("……いまは、誰もいない。00:00〜04:04 にもう一度。")
    if st.button("🏠 ポータルに戻る", use_container_width=True):
        st.switch_page(home_page)
    st.stop()

# --- 各ゲームのサイドバー上部に、控えめな「ポータルに戻る」を出す ---
if _target in noxa.GAME_KEYS:
    with st.sidebar:
        if st.button("🏠 ポータルに戻る", use_container_width=True):
            st.switch_page(home_page)
        st.divider()

nav.run()
