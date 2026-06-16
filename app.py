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

# 日本標準時（JST, UTC+9）。クラウドのサーバ時刻(UTC)に依らず日本時間で表示・判定する。
JST = datetime.timezone(datetime.timedelta(hours=9))


def jst_now():
    return datetime.datetime.now(JST)


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


def tone_wav_bytes(freq=110.0, seconds=1.2, volume=0.12, rate=22050):
    """サイン波の単音（ハム/ビープ用）WAVバイト列を生成する。"""
    try:
        n = int(seconds * rate)
        t = np.arange(n) / rate
        wave_arr = np.sin(2 * np.pi * freq * t)
        # 端のプチノイズ防止に簡単なフェード
        fade = min(int(rate * 0.02), n // 4) or 1
        env = np.ones(n)
        env[:fade] = np.linspace(0, 1, fade)
        env[-fade:] = np.linspace(1, 0, fade)
        samples = (wave_arr * env * volume * 32767).astype("<i2")
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(samples.tobytes())
        return buf.getvalue()
    except Exception:
        return b""


# ==========================================================================
# スマホ / PC 対応（app.py に自己完結。noxa_core の更新に依存しない）
# ==========================================================================
def _is_mobile():
    """User-Agent からスマホ系端末かを推定（取得不可なら False＝PC扱い）。"""
    try:
        ua = (st.context.headers.get("User-Agent", "") or "").lower()
    except Exception:
        return False
    return any(t in ua for t in
               ("mobi", "android", "iphone", "ipad", "ipod", "windows phone"))


# 共通レスポンシブCSS。ポータル本体で1回入れると各ゲームページにも効く。
# グリッド型ミニゲーム（神経衰弱/五十音/スライド/PAIR LOCK等）が
# スマホでも1行に収まり、タップしやすいことを重視。
_RESPONSIVE_CSS = """
<style>
@media (max-width: 680px) {
  /* 左右は詰めて表示幅を稼ぐが、上は十分にあけて
     Streamlitの上部ツールバーにコンテンツが潜り込む（見切れ）のを防ぐ */
  .block-container { padding: 3rem 0.6rem 2.5rem !important; }
  .stApp, .block-container { overflow-x: hidden !important; }

  h1 { font-size: 1.5rem !important; letter-spacing: 1px !important; line-height: 1.25 !important; }
  h2 { font-size: 1.2rem !important; letter-spacing: 0.5px !important; }
  h3 { font-size: 1.05rem !important; }

  /* カラム(グリッド)をスマホ幅に収める核心:
     既定の min-width を外し、横並びのまま縮ませ、間隔も詰める */
  [data-testid="stHorizontalBlock"] { gap: 0.25rem !important; flex-wrap: nowrap !important; }
  [data-testid="column"], [data-testid="stColumn"] {
      min-width: 0 !important;
      padding: 0 1px !important;
  }

  /* グリッドのボタンが潰れず、かつ指で押しやすいサイズに */
  .stButton > button {
      min-height: 44px;
      padding: 0.3rem 0.15rem !important;
      font-size: 1rem !important;
      white-space: normal !important;
      line-height: 1.15 !important;
  }

  /* PAIR LOCK のマス目グリッドを縮小 */
  .pl-grid td, .pl-grid th {
      width: 38px !important; height: 38px !important; font-size: 1.0rem !important;
  }
  .pl-cipher { font-size: 1.8rem !important; letter-spacing: 0.3rem !important; }

  /* 特大の装飾文字（スロット/ハングマン/ハイ&ロー/数字表示の40〜80px）を縮小 */
  div[style*="font-size:72px"], div[style*="font-size: 72px"],
  div[style*="font-size:80px"], div[style*="font-size: 80px"],
  div[style*="font-size:40px"], div[style*="font-size: 40px"] {
      font-size: 40px !important; letter-spacing: 4px !important;
  }
}
</style>
"""


# 演出CSS（ポータル限定）: 背景データストリーム / ティッカー / フッター / 赤い女
_PORTAL_FX_CSS = """
<style>
.block-container { padding-bottom: 3rem !important; }

/* F. 背景の生命感（極薄のデータストリーム。操作を妨げない） */
.noxa-bg {
  position: fixed; inset: 0; pointer-events: none; z-index: 0;
  background: repeating-linear-gradient(0deg, rgba(80,200,160,0.035) 0 1px, transparent 1px 5px);
  opacity: 0.5; animation: noxa-drift 14s linear infinite;
}
@keyframes noxa-drift { from { background-position: 0 0; } to { background-position: 0 200px; } }

/* E. システム音声テロップ（流れるティッカー） */
.noxa-ticker {
  overflow: hidden; white-space: nowrap; margin: 2px 0 8px;
  border-top: 1px solid rgba(80,200,160,0.22); border-bottom: 1px solid rgba(80,200,160,0.22);
  font-family: monospace; font-size: 0.78rem; color: #79b6a0; background: rgba(6,14,12,0.45);
}
.noxa-ticker span { display: inline-block; padding-left: 100%; animation: noxa-tick 26s linear infinite; }
@keyframes noxa-tick { from { transform: translateX(0); } to { transform: translateX(-100%); } }

/* B. 常設ステータスフッター */
.noxa-footer {
  position: fixed; left: 0; right: 0; bottom: 0; z-index: 9995; pointer-events: none;
  font-family: monospace; font-size: 0.72rem; color: #7a9; letter-spacing: 1px; text-align: center;
  background: rgba(4,8,10,0.85); border-top: 1px solid rgba(80,200,160,0.25); padding: 3px 8px;
}

/* B. 常時監視インジケータ（画面隅で点滅する ●REC / 👁 MONITORING） */
.noxa-rec {
  position: fixed; top: 8px; right: 10px; z-index: 9996; pointer-events: none;
  font-family: monospace; font-size: 0.72rem; color: #ff5555; letter-spacing: 1px;
}
.noxa-rec .dot {
  display: inline-block; width: 9px; height: 9px; border-radius: 50%;
  background: #ff3030; margin-right: 5px; vertical-align: middle;
  animation: noxa-blink var(--rec-speed, 1.4s) steps(1) infinite;
}
@keyframes noxa-blink { 0%,49% { opacity: 1; } 50%,100% { opacity: 0.15; } }

/* C. 赤い女 ＝ 監視カメラ映像フレーム（一瞬よぎる人影） */
.noxa-cctv {
  position: fixed; top: 14%; right: 5%; width: 150px; height: 200px; z-index: 9994;
  pointer-events: none; border: 1px solid rgba(255,60,60,0.5); border-radius: 3px;
  background: #0a0a0c; overflow: hidden; opacity: 0;
  animation: noxa-cctv-show 3.6s ease-in-out 1 forwards;
  box-shadow: 0 0 18px rgba(255,30,30,0.25);
}
.noxa-cctv::before {  /* 走査線 */
  content: ""; position: absolute; inset: 0;
  background: repeating-linear-gradient(0deg, rgba(255,255,255,0.05) 0 1px, transparent 1px 3px);
}
.noxa-cctv .fig {  /* 赤い人影 */
  position: absolute; left: 50%; bottom: 6%; transform: translateX(-50%);
  width: 40px; height: 78%;
  background: linear-gradient(to bottom, rgba(220,30,30,0.0), rgba(220,20,20,0.6) 30%,
              rgba(130,0,0,0.5) 75%, transparent);
  filter: blur(4px);
}
.noxa-cctv .lbl {
  position: absolute; top: 3px; left: 5px; font-family: monospace; font-size: 0.62rem;
  color: #ff6a6a; letter-spacing: 1px; z-index: 2;
}
.noxa-cctv .rec2 {
  position: absolute; top: 3px; right: 5px; width: 7px; height: 7px; border-radius: 50%;
  background: #ff3030; animation: noxa-blink 0.8s steps(1) infinite; z-index: 2;
}
@keyframes noxa-cctv-show {
  0% { opacity: 0; } 18% { opacity: 0.92; } 70% { opacity: 0.85; } 100% { opacity: 0; }
}
</style>
"""


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
    rows = [
        ("Subject", name),
        ("Login Count", str(o["login_count"])),
        ("Most Played", mp_title),
        ("Last Login", o["last_login"] or "—"),
        ("/_void Visits", str(o["void_visits"])),
    ]
    # 各行を個別の div にして、枠（範囲）と中身の行ぞろえのズレを防ぐ
    lines = "".join(
        f"<div style='margin:2px 0;'>{k}: "
        f"<span style='color:#d7ffe6;'>{v}</span></div>" for k, v in rows)
    lines += ("<div style='margin:2px 0;'>Status: "
              "<span style='color:#ff8a8a;'>Still investigating.</span></div>")
    st.markdown(
        "<div style='background:#05070b;border:1px solid #2ec27a;border-radius:6px;"
        "padding:14px 16px;font-family:monospace;color:#8fffb0;font-size:0.9rem;"
        f"line-height:1.7;box-shadow:0 0 12px rgba(46,194,122,0.25);'>{lines}</div>",
        unsafe_allow_html=True)


# ==========================================================================
# 深度拡張: 「NOXAが常に動いている」演出（ホーム）
# ==========================================================================
def render_persist_message():
    """⑨(置換) 累計ゲーム起動回数で進むパーソナルメッセージ。"""
    try:
        msg = noxa.persist_message()
    except Exception:
        return  # noxa_core が古い等で関数が無くてもポータルは落とさない
    if msg:
        st.markdown(
            f"<div style='text-align:center;font-family:monospace;color:#caa;"
            f"opacity:0.85;margin:2px 0 6px;'>{msg}</div>", unsafe_allow_html=True)


def render_ambient_event():
    """② 観測不能イベント / ⑥ ランダム会話盗聴。セッション1回だけ抽選（ちらつき防止）。"""
    try:
        if noxa.clear_count() < 1:
            return
        if "_ambient" not in st.session_state:
            r = random.random()
            if r < 0.12:
                st.session_state["_ambient"] = ("missed",
                    noxa.MISSED_EVENTS[random.randrange(len(noxa.MISSED_EVENTS))])
            elif r < 0.24:
                st.session_state["_ambient"] = ("audio",
                    noxa.CONVO_FRAGMENTS[random.randrange(len(noxa.CONVO_FRAGMENTS))])
            else:
                st.session_state["_ambient"] = None
    except Exception:
        return
    amb = st.session_state.get("_ambient")
    if not amb:
        return
    kind, data = amb
    if kind == "missed":
        t, title, sub = data
        st.markdown(
            "<div style='font-family:monospace;border:1px dashed #a55;color:#caa;"
            "padding:8px 12px;border-radius:4px;margin:4px 0;'>"
            f"⚠ Event Missed<br>{t} ── {title}<br>"
            f"<span style='opacity:.6'>{sub}</span></div>", unsafe_allow_html=True)
    else:
        lines = "<br>".join(f"<b>{spk}:</b> {txt}" for spk, txt in data)
        st.markdown(
            "<div style='font-family:monospace;border-left:3px solid #577;color:#9bb;"
            "padding:6px 12px;background:rgba(20,30,40,0.4);margin:4px 0;'>"
            f"🎧 [Audio Fragment]<br>{lines}</div>", unsafe_allow_html=True)


def render_phantom_file():
    """⑪ 存在しないファイル memo_404.txt。初日は File Not Found、別の日に開くと HELP。"""
    try:
        if noxa.clear_count() < 2:
            return
        ch = noxa.state()["choices"]
        today = noxa.today_str()
    except Exception:
        return
    if not ch.get("phantom_seen"):
        if random.random() >= 0.10:
            return
        ch["phantom_seen"] = True
        noxa.save()
    with st.expander("🗂 memo_404.txt"):
        first = ch.get("phantom_date")
        if not first:
            ch["phantom_date"] = today
            noxa.save()
            st.error("File Not Found")
            st.caption("……また別の日に開いてみると、何か変わるかもしれない。")
        elif first != today:
            st.markdown("<div style='font-family:monospace;color:#ff4444;font-size:1.5rem;"
                        "letter-spacing:4px;'>HELP</div>", unsafe_allow_html=True)
            st.caption("昨日は開けなかったファイルが、今日は開いた。")
        else:
            st.error("File Not Found")
            st.caption("……まだ開かない。別の日に。")


def render_noxa_feed():
    """① 活動ログ ＋ ④ タイムライン ＋ ⑤ 名簿 ＋ ③ 消された記録 ＋ ⑧ Observer。"""
    # 先に noxa の新APIをまとめて取得（古い版なら静かにスキップ）
    try:
        feed_data = noxa.feed_lines()
        timeline = noxa.timeline_rows()
        roster = noxa.roster_rows()
        recovered = noxa.erased_recovered()
        observer = noxa.observer_unlocked()
    except Exception:
        return
    with st.expander("📡 NOXA INTERNAL FEED"):
        feed = "<br>".join(
            f"<span style='color:#6a9'>[LOG]</span> {l}" for l in feed_data)
        st.markdown(f"<div style='font-family:monospace;font-size:0.85rem;color:#9bb;'>"
                    f"{feed}</div>", unsafe_allow_html=True)

        st.markdown("---")
        st.caption("🕰 NOXA TIMELINE")
        for year, ev, unlocked in timeline:
            color = "#cdb" if unlocked else "#667"
            st.markdown(f"<div style='font-family:monospace;color:{color};'>"
                        f"{year} ── {ev}</div>", unsafe_allow_html=True)

        st.markdown("---")
        st.caption("👥 消えた職員名簿")
        for nm, stt in roster:
            st.markdown(f"<div style='font-family:monospace;'>{nm} "
                        f"<span style='color:#c77'>{stt}</span></div>",
                        unsafe_allow_html=True)

        st.markdown("---")
        st.caption("🗑 消された記録")
        if recovered:
            st.markdown("<div style='font-family:monospace;color:#cdb;'>Recovered Fragment:<br>"
                        "<i>There was another subject.</i><br>"
                        "<span style='opacity:.6'>……詳細は不明。</span></div>",
                        unsafe_allow_html=True)
        else:
            st.markdown("<div style='font-family:monospace;color:#955;'>"
                        "██████████ — <b>ACCESS DENIED</b></div>", unsafe_allow_html=True)

        if observer:
            st.markdown("---")
            st.markdown("<div style='font-family:monospace;color:#f99;'>"
                        "👁 Observer — <b>Unknown</b><br>"
                        "<span style='opacity:.6'>NOXAの記録を、さらに上から見ている何か。</span>"
                        "</div>", unsafe_allow_html=True)

        render_phantom_file()


# ==========================================================================
# 演出・画面表示（A:起動 / B:フッター / C:遷移 / D:赤い女 / E:ティッカー）
# ==========================================================================
def _boot_sequence():
    """A. 初回接続時の端末起動演出（セッション1回）。"""
    if st.session_state.get("_booted"):
        return
    st.session_state["_booted"] = True
    name = noxa.state().get("player", "guest")
    try:  # E. 起動時の低いハム音（端末が起動する臨場感）
        st.audio(tone_wav_bytes(70.0, 2.2, volume=0.10), format="audio/wav", autoplay=True)
    except Exception:
        pass
    lines = ["NOXA NETWORK",
             "> establishing connection ...",
             f"> authenticating subject: {name}",
             "> access granted."]
    base = ("position:fixed;inset:0;z-index:2147483600;background:#04060a;"
            "display:flex;flex-direction:column;justify-content:center;padding:0 12%;"
            "font-family:monospace;color:#5fd49a;font-size:1.05rem;line-height:2;")
    ph = st.empty()
    shown = []
    for ln in lines:
        shown.append(ln)
        html = "<br>".join(shown) + "<span style='opacity:.6'>▌</span>"
        ph.markdown(f"<div style='{base}'>{html}</div>", unsafe_allow_html=True)
        time.sleep(0.45)
    time.sleep(0.5)
    ph.empty()


def _sector_transition(title):
    """C. 作品を開く瞬間の『ACCESSING SECTOR』暗転（switch_pageの直前に呼ぶ）。"""
    base = ("position:fixed;inset:0;z-index:2147483600;background:#050505;"
            "display:flex;align-items:center;justify-content:center;text-align:center;"
            "font-family:monospace;color:#7fd0ff;font-size:1.35rem;letter-spacing:3px;")
    st.empty().markdown(
        f"<div style='{base}'>ACCESSING SECTOR<br>// {title}</div>",
        unsafe_allow_html=True)
    time.sleep(0.9)


def render_portal_footer():
    """B. 画面下に常設するNOXA端末ステータスバー。"""
    name = noxa.state().get("player", "guest")
    now = jst_now().strftime("%H:%M")
    cc = noxa.clear_count()
    st.markdown(
        f"<div class='noxa-footer'>NOXA SYS v2.3.4 ｜ MONITORING ｜ Subject: {name} ｜ "
        f"cleared {cc}/{len(noxa.GAME_KEYS)} ｜ {now}</div>", unsafe_allow_html=True)


_SYS_TICKER = ["archive synced", "memory index nominal", "subject observed",
               "sector 7 sealed", "404 — monitoring", "containment stable",
               "backup completed", "trace re-routed"]


def render_system_ticker():
    """E. 流れるシステム音声テロップ。"""
    line = "　•　".join(f"&gt; {t}" for t in _SYS_TICKER)
    st.markdown(f"<div class='noxa-ticker'><span>{line}　•　{line}</span></div>",
                unsafe_allow_html=True)


def _unlock_animation(title):
    """A. 作品が解放される瞬間の端末演出（解放1回だけ）。"""
    try:
        st.audio(tone_wav_bytes(880.0, 0.18, volume=0.18), format="audio/wav", autoplay=True)
    except Exception:
        pass
    base = ("position:fixed;inset:0;z-index:2147483600;background:#04060a;"
            "display:flex;align-items:center;justify-content:center;text-align:center;"
            "font-family:monospace;letter-spacing:3px;")
    ph = st.empty()
    frames = [
        ("<div style='color:#9bb;font-size:1.1rem;'>&gt; verifying clearance ...</div>", 0.7),
        ("<div style='color:#5fd49a;font-size:1.5rem;'>&gt; ACCESS GRANTED</div>", 0.7),
        (f"<div style='color:#ffd24d;font-size:1.4rem;'>▣ SECTOR UNLOCKED<br>"
         f"<span style='color:#fff'>{title}</span></div>", 1.1),
    ]
    for html, dur in frames:
        ph.markdown(f"<div style='{base}'>{html}</div>", unsafe_allow_html=True)
        time.sleep(dur)
    ph.empty()


def render_disconnect():
    """D. 物語の節目で一度だけ起きる強制切断イベント（全画面＋再接続ボタン）。"""
    st.markdown("<style>.stApp{background:#070303 !important;}</style>",
                unsafe_allow_html=True)
    try:
        st.audio(noise_wav_bytes(1.4, volume=0.22), format="audio/wav", autoplay=True)
    except Exception:
        pass
    st.markdown("<div style='height:16vh'></div>", unsafe_allow_html=True)
    st.markdown(
        "<div style='text-align:center;font-family:monospace;color:#ff4040;'>"
        "<div style='font-size:1.8rem;letter-spacing:5px;'>CONNECTION TERMINATED</div>"
        "<div style='margin-top:8px;opacity:.8;letter-spacing:3px;'>BY NOXA</div>"
        "<div style='margin-top:16px;color:#caa;font-size:0.9rem;'>"
        "……あなたは、見過ぎたのかもしれない。</div></div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    if c2.button("▶ 再接続する", use_container_width=True, key="reconnect"):
        noxa.set_choice("seen_disconnect", True)
        st.rerun()


def render_monitoring_indicator():
    """B. 画面隅に常時点滅する監視インジケータ。進行度で点滅が速くなる。"""
    try:
        cc = noxa.clear_count()
    except Exception:
        cc = 0
    speed = max(0.5, 1.6 - cc * 0.18)   # 進むほど速く＝監視が強まる
    st.markdown(
        f"<div class='noxa-rec'><span class='dot' style='--rec-speed:{speed}s'></span>"
        f"REC ｜ MONITORING</div>", unsafe_allow_html=True)


def render_red_woman():
    """C. 進行度に応じて、監視カメラ映像に赤い人影が一瞬よぎる（セッション1回だけ抽選）。"""
    if st.session_state.get("_rw_done"):
        return
    st.session_state["_rw_done"] = True
    try:
        lvl = noxa.red_woman_level()
    except Exception:
        lvl = 0
    prob = [0.0, 0.2, 0.4, 0.7][lvl] if 0 <= lvl <= 3 else 0.7
    if random.random() < prob:
        st.markdown(
            "<div class='noxa-cctv'>"
            "<span class='lbl'>CAM 04</span><span class='rec2'></span>"
            "<span class='fig'></span></div>", unsafe_allow_html=True)


# ==========================================================================
# 深夜イベント（現実時間連動 00:00〜04:04）
# ==========================================================================
def is_midnight_window():
    now = jst_now().time()
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

    # ⑦ 404の記憶断片（深夜チャットで低確率・セッション1回抽選）
    if "_chat_frag" not in st.session_state:
        try:
            frags = noxa.MEMORY_FRAGMENTS
            st.session_state["_chat_frag"] = (
                frags[random.randrange(len(frags))] if random.random() < 0.45 else None)
        except Exception:
            st.session_state["_chat_frag"] = None
    if st.session_state["_chat_frag"]:
        st.markdown(
            "<div style='font-family:monospace;color:#8fbf8f;opacity:0.85;"
            "margin-top:10px;font-style:italic;'>"
            f"404 ▸ {st.session_state['_chat_frag']}</div>", unsafe_allow_html=True)
        st.caption("……誰の記憶だろう。")

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


def _p000_status(name):
    """研究所端末UIのステータスヘッダHTML（セクターと同じ1要素にまとめて描く）。"""
    return ("<div style='background:#0a0608;border:1px solid #a33;border-radius:6px;"
            "padding:10px 14px;margin-bottom:6px;font-family:monospace;color:#f99;"
            "font-size:0.9em;line-height:1.6;'>"
            f"Subject ID: <b>{name}</b><br>"
            "Observation Status: <span style='color:#ff5555'>ACTIVE</span><br>"
            "Memory Collection: <span style='color:#7CFC9A'>COMPLETE</span></div>")


def project000():
    s = noxa.state()
    name = s.get("player", "guest")

    # 崩壊イントロ（1回）。専用の実行で再生し、終わったら即 rerun する。
    # こうすると以降は常に「コンテンツのみ」の同じ要素構成になり、
    # 実行ごとの要素ズレで前のセクター/ヘッダが薄く残る現象を防げる。
    if not st.session_state.get("p000_intro_done"):
        st.session_state["p000_intro_done"] = True
        try:
            st.audio(noise_wav_bytes(2.6), format="audio/wav", autoplay=True)
        except Exception:
            pass
        _p000_intro(name)
        st.rerun()

    st.session_state.setdefault("p000_step", 0)
    typed = st.session_state.setdefault("p000_typed", set())
    step = st.session_state.p000_step
    total = len(P000_PARTS)

    def _box_full(i):
        t, b = P000_PARTS[i]
        return _p000_box(i + 1, t, b(name).replace("\n", "<br>"))

    header = _p000_status(name)
    completed = "".join(_box_full(i) for i in range(step))

    # ステータスヘッダ＋確定セクター＋進行中セクターを“単一の要素”に描く。
    # これでタイプ中にヘッダや前セクターが二重表示／残像になることがない。
    ph = st.empty()
    if step in typed:
        ph.markdown(header + completed + _box_full(step), unsafe_allow_html=True)
    else:
        title, body = P000_PARTS[step]
        shown = ""
        for ch in body(name):
            shown += ch
            cur = _p000_box(step + 1, title,
                            shown.replace("\n", "<br>")
                            + "<span style='opacity:.7'>▌</span>")
            ph.markdown(header + completed + cur, unsafe_allow_html=True)
            time.sleep(0.02)
        ph.markdown(header + completed + _box_full(step), unsafe_allow_html=True)
        typed.add(step)

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
    _boot_sequence()           # A. 初回接続の起動演出（セッション1回）
    maybe_fake_error()
    render_red_woman()         # D. 赤い女が画面隅を一瞬よぎる（進行度で確率）
    render_portal_header()
    st.caption(f"認証者: {s.get('player', 'guest')} さん　／　"
               f"クリア: {noxa.clear_count()} / {len(noxa.GAME_KEYS)}")
    render_system_ticker()     # E. システム音声テロップ（ティッカー）

    render_persist_message()   # ⑨(置換) 累計起動回数のパーソナルメッセージ
    maybe_fake_update()
    render_ambient_event()     # ② 観測不能イベント / ⑥ 会話盗聴（セッション1回抽選）
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

    # A. 新規解放の演出（前作クリアで作品が解放された瞬間に1回だけ）
    seen = s.setdefault("seen_unlocks", [])
    announced = False
    for g in GAMES:
        if g["key"] in unlocked and g["key"] not in noxa.INITIAL_UNLOCKED \
                and g["key"] not in seen:
            _unlock_animation(g["title"])
            st.success(f"🔓 新たな作品が解放された ── 「{g['title']}」")
            seen.append(g["key"])
            announced = True
    if noxa.project000_unlocked() and "project000" not in seen:
        _unlock_animation("PROJECT 000")
        st.success("🔓 最終作品 **Project 000** が解放された。")
        seen.append("project000")
        announced = True
    if announced:
        noxa.save()

    mobile = _is_mobile()
    for g in GAMES:
        is_unlocked = g["key"] in unlocked
        cleared = noxa.is_cleared(g["key"])
        with st.container(border=True):
            # スマホではアイコン列を省き1カラム、PCでは [アイコン | 内容] の2カラム
            if mobile:
                body = st
            else:
                c1, c2 = st.columns([1, 4])
                body = c2
            if is_unlocked:
                badge = " ✅クリア済" if cleared else ""
                if mobile:
                    body.subheader(f"{g['icon']} {g['title']}{badge}")
                else:
                    c1.markdown(f"<div style='font-size:52px;text-align:center;'>{g['icon']}</div>",
                                unsafe_allow_html=True)
                    body.subheader(f"{g['title']}{badge}")
                if body.button(f"▶ {g['title']} を遊ぶ", key=f"play_{g['key']}",
                               use_container_width=True):
                    noxa.record_play(g["key"])
                    _sector_transition(g["title"])   # C. 遷移演出
                    st.switch_page(g["path"])
            else:
                src = UNLOCK_SOURCE.get(g["key"])
                hint = (f"「{noxa.GAME_TITLES.get(src, '前作')}」をクリアすると解放"
                        if (src and src in unlocked) else "？？？")
                if mobile:
                    body.subheader("🔒 ？？？")
                else:
                    c1.markdown("<div style='font-size:52px;text-align:center;opacity:.4;'>🔒</div>",
                                unsafe_allow_html=True)
                    body.subheader("？？？")
                body.caption(hint)
                body.write("ロックされた作品。")

    # 最終作品 Project 000（全作品クリアで解放）
    with st.container(border=True):
        if mobile:
            body = st
        else:
            c1, c2 = st.columns([1, 4])
            body = c2
        if noxa.project000_unlocked():
            if mobile:
                body.subheader("🌀 Project 000")
            else:
                c1.markdown("<div style='font-size:52px;text-align:center;'>🌀</div>",
                            unsafe_allow_html=True)
                body.subheader("Project 000")
            if body.button("▶ Project 000 を起動", key="play_p000", use_container_width=True):
                _sector_transition("PROJECT 000")   # C. 遷移演出
                st.switch_page(p000_page)
        else:
            if mobile:
                body.subheader("🌀 █████ 000")
            else:
                c1.markdown("<div style='font-size:52px;text-align:center;opacity:.4;'>🌀</div>",
                            unsafe_allow_html=True)
                body.subheader("█████ 000")
            body.caption("全作品クリアで解放")
            body.write("存在だけが示唆された、最後の何か。")

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

    # NOXAが動いている演出（活動ログ・タイムライン・名簿・消された記録・Observer）
    st.markdown("---")
    render_noxa_feed()

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

# 共通レスポンシブCSS（ここで1回入れると以降のゲームページ描画にも効く）
st.markdown(_RESPONSIVE_CSS, unsafe_allow_html=True)

# ポータル統合中であることを各ゲームへ知らせる（「ポータルに戻る」ボタン表示の判定用）
st.session_state["_in_portal"] = True

# 各ゲームのクリア画面から「ポータルに戻る」が押されたらホームへ遷移
if st.session_state.pop("_noxa_go_home", False):
    st.switch_page(home_page)

# --- 初回接続: プレイヤー名が無ければ認証ゲートを出して停止 ---
_s = noxa.state()
if not _s.get("player"):
    render_name_gate()
    st.stop()

# 観察ログ: セッション開始（ログイン）を1回だけ記録する
if not st.session_state.get("obs_logged"):
    st.session_state["obs_logged"] = True
    noxa.record_login()

_target = getattr(nav, "url_path", "")
_is_home = _target not in noxa.GAME_KEYS and _target not in ("void", "project000", "chat404")

# D. 強制切断イベント（PAIR LOCKクリア後・ホームで一度だけ）。
# FX/フッターより前で全画面を占有し、再接続するまで先へ進ませない。
if _is_home and noxa.is_cleared("pairlock") and not noxa.get_choice("seen_disconnect"):
    render_disconnect()
    st.stop()

# ゲームページ以外（ホーム等）ではサイドバーを隠す。
# ゲームから「ポータルに戻る」で戻った際、空のサイドバー（展開状態）が
# 残って特にスマホで画面を覆ってしまうのを防ぐ。
if _target not in noxa.GAME_KEYS:
    st.markdown(
        "<style>"
        "[data-testid='stSidebar'],"
        "[data-testid='stSidebarCollapsedControl'],"
        "[data-testid='collapsedControl'] { display:none !important; }"
        "</style>", unsafe_allow_html=True)
    # 演出: 背景データストリーム＋常設ステータスフッター＋監視インジケータ
    st.markdown(_PORTAL_FX_CSS, unsafe_allow_html=True)
    st.markdown("<div class='noxa-bg'></div>", unsafe_allow_html=True)
    render_portal_footer()
    render_monitoring_indicator()

# --- ロック: 未解放の作品にURL直アクセスしたら遊ばせない ---
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
