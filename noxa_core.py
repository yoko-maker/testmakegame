"""NOXA Universe — ポータル横断の共有状態・進行管理・永続化。

各ゲームページとポータル本体が共有する「メタ進行」を一元管理する。

  - プレイヤー名
  - 各作品のクリア状況（段階解放の素）
  - 共通調査ボード（NOXAの真相マップ）
  - 作品横断の選択フラグ

進行はプレイヤー名をキーに JSON ファイルへ保存し、ブラウザを閉じても残る。

各ゲームを単体起動（`streamlit run <game>/app.py`）した場合は、このモジュールが
import できないことがある。その場合でもゲーム側は壊れないよう、各ゲームは
import を try/except で包み、本モジュールの関数は Streamlit 未接続でも安全に動く。
"""

import datetime
import json
import os
import random
import re
import time

import streamlit as st

ROOT = os.path.dirname(os.path.abspath(__file__))
SAVE_DIR = os.path.join(ROOT, "noxa_saves")

# 作品キー（ポータルの url_path と一致させる）
GAME_KEYS = ["arcade", "case001", "echo", "arg", "pairlock", "last30"]
GAME_TITLES = {
    "arcade": "ミニゲームアーケード",
    "case001": "消えた研究者",
    "echo": "Project ECHO",
    "arg": "404 User Not Found",
    "pairlock": "PAIR LOCK",
    "last30": "LAST 30 MINUTES",
}
GAME_ICONS = {
    "arcade": "🎮", "case001": "🕵️", "echo": "🧬",
    "arg": "🛑", "pairlock": "🔒", "last30": "☄️",
}

# 段階解放チェーン: あるキーをクリアすると次の作品が解放される
UNLOCK_CHAIN = {
    "case001": "echo",
    "echo": "arg",
    "arg": "pairlock",
    "pairlock": "last30",
}
INITIAL_UNLOCKED = ["arcade", "case001"]

# --------------------------------------------------------------------------
# 管理者設定
# --------------------------------------------------------------------------
# ADMIN_MODE を True にすると、ポータル下部の「⚙ プレイヤーデータ」内に
# 管理者パネルが常時表示され、ワンクリックで全作品クリア状態にできる。
# （デモ・審査・動作確認用。通常配布時は False のままにしておく）
ADMIN_MODE = False
# コードを入れて解放する方式でも有効化できる（コード編集不要）。
# 空文字にするとコードによる解放を無効化する。
ADMIN_CODE = "noxa-admin"

# 共通調査ボード: NOXAの真相に関わる調査対象
BOARD_ITEMS = ["天城 真", "被験者404", "霧島 玲", "ECHO", "NOXA", "第7研究棟", "赤い女"]
# 各作品クリアで明らかになる調査項目
BOARD_REVEAL = {
    "arcade": ["NOXA"],
    "case001": ["霧島 玲", "NOXA"],
    "echo": ["被験者404", "ECHO", "霧島 玲"],
    "arg": ["NOXA", "天城 真", "赤い女"],
    "pairlock": ["第7研究棟", "霧島 玲"],
    "last30": ["ECHO", "天城 真"],
}
# 調査ボードに表示するヒント（解放後に読める）
BOARD_HINTS = {
    "天城 真": "NOXA創設者。全作品に痕跡（A.T.承認済 / amagi@noxa.jp）。全事件の起点。",
    "被験者404": "ただの数字 → 被験者番号 → 人格コピー成功体。観測者であり失踪者。",
    "霧島 玲": "失踪した主任研究員。ECHOの原型となった人物。",
    "ECHO": "人間の意識をAIへ写すプロジェクト、およびその成功体。",
    "NOXA": "意識・記憶・AIを研究する巨大組織。各地に複数の施設を持つ。",
    "第7研究棟": "封鎖された施設。事故と失踪の中心。",
    "赤い女": "全作品の映像の隅に現れる、説明されない存在。",
}


def _default_state():
    return {
        "player": "",
        "cleared": {k: False for k in GAME_KEYS},
        "board": {item: False for item in BOARD_ITEMS},
        "choices": {},
        "seen_intro": False,
        "seen_unlocks": [],  # 解放お知らせを既に出した作品キー
        "obs": _default_obs(),  # 観察ログ（プレイヤーの行動記録）
    }


def _default_obs():
    return {
        "login_count": 0,
        "first_seen": "",
        "last_login": "",
        "logins": [],                      # 直近の接続時刻（最大10）
        "plays": {k: 0 for k in GAME_KEYS},  # 作品ごとの起動回数
        "void_visits": 0,                  # /_void 閲覧回数
        "midnight_visits": 0,              # 深夜404チャットを開いた回数
        "msg_progress": 0,                 # 偽物通知の進行
    }


def state():
    """セッション内の共有state（無ければ初期化）を返す。

    旧バージョンのセッション/セーブ（キー欠落・型違い・None）でも壊れないよう
    全サブ構造を防御的に整える。これにより開発中のホットリロードで残った
    古い session_state でも AttributeError を出さない。
    """
    if not isinstance(st.session_state.get("noxa"), dict):
        st.session_state["noxa"] = _default_state()
    s = st.session_state["noxa"]
    # 必須サブ構造を保証（欠落・None・型違いを修復）
    if not isinstance(s.get("cleared"), dict):
        s["cleared"] = {}
    for k in GAME_KEYS:
        s["cleared"].setdefault(k, False)
    if not isinstance(s.get("board"), dict):
        s["board"] = {}
    for item in BOARD_ITEMS:
        s["board"].setdefault(item, False)
    if not isinstance(s.get("choices"), dict):
        s["choices"] = {}
    if not isinstance(s.get("seen_unlocks"), list):
        s["seen_unlocks"] = []
    s.setdefault("seen_intro", False)
    s.setdefault("player", "")
    if not isinstance(s.get("obs"), dict):
        s["obs"] = _default_obs()
    return s


# --------------------------------------------------------------------------
# 観察ログ（プレイヤーの行動記録）
# --------------------------------------------------------------------------
# 日本標準時（JST, UTC+9）。サーバ時刻(UTC)に依らず日本時間で記録する。
_JST = datetime.timezone(datetime.timedelta(hours=9))


def _now_str():
    try:
        return datetime.datetime.now(_JST).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ""


# --------------------------------------------------------------------------
# スマホ / PC 対応
# --------------------------------------------------------------------------
def is_mobile():
    """User-Agent からスマホ系端末かどうかを推定する（取得不可なら False）。"""
    try:
        ua = (st.context.headers.get("User-Agent", "") or "")
    except Exception:
        return False
    return bool(re.search(r"Mobi|Android|iPhone|iPad|iPod|Windows Phone", ua, re.I))


# 画面幅に応じた共通レスポンシブCSS（グリッド型ミニゲームは崩さない安全な範囲）
RESPONSIVE_CSS = """
<style>
@media (max-width: 640px) {
    .block-container { padding: 0.9rem 0.6rem !important; }
    h1 { font-size: 1.5rem !important; letter-spacing: 1px !important; line-height: 1.25 !important; }
    h2 { font-size: 1.2rem !important; letter-spacing: 0.5px !important; }
    h3 { font-size: 1.05rem !important; letter-spacing: 0.5px !important; }
    /* ボタンを押しやすく＆文字あふれ防止 */
    .stButton > button {
        padding: 0.5rem 0.5rem !important;
        font-size: 0.9rem !important;
        white-space: normal !important;
        line-height: 1.2 !important;
    }
    /* 横スクロール防止 */
    .stApp, .block-container { overflow-x: hidden !important; }
    /* 大きすぎる装飾文字（スロット/ハングマン等の特大表示）を縮小 */
    div[style*="font-size:72px"], div[style*="font-size:80px"],
    div[style*="font-size: 72px"], div[style*="font-size: 80px"] {
        font-size: 44px !important;
        letter-spacing: 6px !important;
    }
}
</style>
"""


def inject_responsive():
    """共通レスポンシブCSSを注入する（ポータル本体で1回呼べば全ページに効く）。"""
    try:
        st.markdown(RESPONSIVE_CSS, unsafe_allow_html=True)
    except Exception:
        pass


def obs():
    s = state()
    if not isinstance(s.get("obs"), dict):
        s["obs"] = _default_obs()
    o = s["obs"]
    o.setdefault("login_count", 0)
    o.setdefault("first_seen", "")
    o.setdefault("last_login", "")
    if not isinstance(o.get("logins"), list):
        o["logins"] = []
    if not isinstance(o.get("plays"), dict):
        o["plays"] = {}
    for k in GAME_KEYS:
        o["plays"].setdefault(k, 0)
    o.setdefault("void_visits", 0)
    o.setdefault("midnight_visits", 0)
    o.setdefault("msg_progress", 0)
    return o


def record_login():
    o = obs()
    ts = _now_str()
    o["login_count"] += 1
    if not o["first_seen"]:
        o["first_seen"] = ts
    o["last_login"] = ts
    o["logins"].append(ts)
    o["logins"] = o["logins"][-10:]
    save()


def record_play(key):
    o = obs()
    if key in o["plays"]:
        o["plays"][key] += 1
        save()


def record_void_visit():
    obs()["void_visits"] += 1
    save()


def record_midnight_visit():
    o = obs()
    o["midnight_visits"] += 1
    save()
    return o["midnight_visits"]


def most_played_key():
    o = obs()
    if not any(o["plays"].values()):
        return None
    return max(o["plays"], key=lambda k: o["plays"][k])


# --------------------------------------------------------------------------
# 作品間干渉（⑦）と 赤い女の侵食（⑥）
# --------------------------------------------------------------------------
RED_WOMAN_GLIMPSES = [
    "視界の隅を、赤い服の女が横切った気がした。",
    "画面の端に、赤い影。振り向くと、もういない。",
    "……ずっと、赤い服の女がこちらを見ている。",
]


def red_woman_level():
    """進行度に応じた赤い女の侵食レベル（0:なし 〜 3:ほぼ全作品）。"""
    n = clear_count()
    if n >= 5:
        return 3
    if n >= 3:
        return 2
    if n >= 1:
        return 1
    return 0


def interference_lines(game_key):
    """他作品の進行に応じてこの作品に現れる干渉メッセージ (icon, text) のリスト。"""
    out = []
    if game_key == "case001" and is_cleared("echo"):
        out.append(("📡", "ECHO ACCESS DETECTED ── この事件に、別の施設からアクセスがあった。"))
    if is_cleared("pairlock") and game_key in ("arcade", "case001", "echo", "last30"):
        out.append(("🔢", "端末の隅に見覚えのない刻印 ── 施設番号 404。"))
    if is_cleared("arg") and game_key not in ("arg",):
        out.append(("📶", "接続にノイズが混じる。どこかから覗かれている気配。"))
    return out


def _gather_intrusion(game_key):
    """この作品に出す干渉メッセージ (text, color) を集める。赤い女の出現可否は
    セッション内で作品ごとに一度だけ判定（ちらつき防止）。"""
    lines = [(f"{icon} {text}", "#e58a8a")
             for icon, text in interference_lines(game_key)]
    lvl = red_woman_level()
    if lvl > 0:
        key = f"_redwoman_{game_key}"
        if key not in st.session_state:
            prob = [0.0, 0.25, 0.5, 0.85][lvl]
            st.session_state[key] = (random.random() < prob)
        if st.session_state[key]:
            msg = RED_WOMAN_GLIMPSES[min(lvl - 1, len(RED_WOMAN_GLIMPSES) - 1)]
            lines.append(("🔴 " + msg, "#ff6060"))
    return lines


def _intrusion_cinematic(lines):
    """画面暗転 → 一文字ずつ打ち込む演出（初回オープン時のみ）。

    z-index を最前面にしてサイドバーごと覆い（文字被り防止）、テキストは
    画面中央の固定幅パネルに左寄せで表示する。
    """
    ph = st.empty()
    # 全面を黒で覆う（サイドバーより必ず手前）＋テキストは中央のパネルへ
    outer = ("position:fixed;inset:0;z-index:2147483000;background:#050505;"
             "display:flex;align-items:center;justify-content:center;")
    panel = ("width:min(680px,86vw);text-align:left;font-family:monospace;"
             "font-size:1.05rem;line-height:1.8;")
    done = ""
    for text, color in lines:
        typed = ""
        for ch in text:
            typed += ch
            cur = done + (f"<div style='color:{color};margin:6px 0;'>{typed}"
                          f"<span style='opacity:.55'>▌</span></div>")
            ph.markdown(f"<div style='{outer}'><div style='{panel}'>{cur}</div></div>",
                        unsafe_allow_html=True)
            time.sleep(0.055)
        done += f"<div style='color:{color};margin:6px 0;'>{text}</div>"
        time.sleep(0.6)
    # 全文が出そろってから、しばらく読ませてから消す
    time.sleep(3.0)
    ph.empty()


# ==========================================================================
# 深度拡張: 「NOXAが常に動いている」演出のデータ／ロジック
# ==========================================================================
def progress_tier():
    """演出段階: 'early'(0-1) → 'mid'(2-3) → 'late'(4+) → 'post'(Project000完了)。"""
    if seen_000():
        return "post"
    n = clear_count()
    if n >= 4:
        return "late"
    if n >= 2:
        return "mid"
    return "early"


# ① NOXA活動ログ（進行段階で内容が変わる内部フィード）
NOXA_FEED = {
    "early": ["Research Division Updated", "Archive Synced", "Routine Backup Completed"],
    "mid":   ["Sector 7 Accessed", "Subject 404 Activity Detected", "Memory Index Rebuilt"],
    "late":  ["Unauthorized Memory Recovery", "Containment Failure", "Subject 404 — location lost"],
    "post":  ["Observer present", "Experiment ongoing", "Subject ID retained"],
}


def feed_lines():
    return NOXA_FEED.get(progress_tier(), NOXA_FEED["early"])


# ④ NOXAタイムライン (解放しきい値 clear_count, 年, 出来事)
NOXA_TIMELINE = [
    (0, "1987", "ノクサ研究機構 設立"),
    (1, "1994", "第7研究棟 建設"),
    (2, "2001", "ECHO計画 開始"),
    (3, "2007", "最初の消失事件"),
    (4, "2013", "Project 404"),
    (6, "20XX", "あなたの接続"),
]


def timeline_rows():
    """(年, 出来事, 解放済みか) のリスト。未解放は伏せる。"""
    n = clear_count()
    out = []
    for thr, year, ev in NOXA_TIMELINE:
        unlocked = n >= thr or (thr >= 6 and seen_000())
        out.append((year, ev, True) if unlocked else ("????", "── 未発掘 ──", False))
    return out


# ⑤ 消えた職員名簿 (解放しきい値, 氏名, ステータス)
STAFF_ROSTER = [
    (0, "Kirishima Rei", "STATUS UNKNOWN"),
    (1, "Sakuma",        "RESIGNED?"),
    (2, "Akira",         "DELETED"),
    (3, "Yamada S.",     "MISSING"),
    (4, "██████",        "REMOVED"),
    (6, "Amagi M.",      "FOUNDER / ACTIVE"),
]


def roster_rows():
    n = clear_count()
    return [(nm, stt) for thr, nm, stt in STAFF_ROSTER
            if n >= thr or (thr >= 6 and seen_000())]


# ③ 消された記録 / ⑧ Observer
def erased_recovered():
    """消された記録が復元できる段階か（late/post）。"""
    return progress_tier() in ("late", "post")


def observer_unlocked():
    """⑧ 壁の向こうの観察者（Project000後に解放）。"""
    return seen_000()


# ② 観測不能イベント / ⑥ ランダム会話盗聴（テキスト素材）
CONVO_FRAGMENTS = [
    [("A", "Did you hear that?"), ("B", "About 404?"), ("A", "Keep your voice down.")],
    [("A", "Sector 7 again?"), ("B", "Don't write it down."), ("A", "……")],
    [("B", "She's still in the system."), ("A", "That's impossible."), ("B", "Is it?")],
]
MISSED_EVENTS = [
    ("03:14", "Unknown Connection", "Data Unavailable"),
    ("04:04", "Memory Transfer", "Access Logged Elsewhere"),
    ("02:51", "Subject 404 — Online", "Trace Lost"),
]


# ⑦ 深夜チャットで稀に出る 404 の記憶断片
MEMORY_FRAGMENTS = [
    "I remember rain.",
    "I remember a hospital.",
    "I remember her voice.",
    "I remember a door that wouldn't open.",
    "……was that me?",
]


# ⑨(置換) 累計ゲーム起動回数で進むパーソナルメッセージ
PERSIST_MSGS = [(6, "You are persistent."),
                (14, "Why do you keep returning?"),
                (24, "We knew you would.")]


def total_plays():
    o = obs()
    try:
        return sum(o.get("plays", {}).values())
    except Exception:
        return 0


def persist_message():
    t = total_plays()
    msg = None
    for thr, m in PERSIST_MSGS:
        if t >= thr:
            msg = m
    return msg


def today_str():
    try:
        return datetime.datetime.now(_JST).date().isoformat()
    except Exception:
        return ""


def render_intrusion(game_key):
    """各ゲーム冒頭で呼ぶ。作品間干渉(⑦)と赤い女の侵食(⑥)を描く。

    初回オープン時に「暗転→一文字ずつ表示」の演出を一度だけ再生し、消える。
    以降は上部に何も残さない。ポータル未統合・Streamlit未接続でも安全（no-op）。
    """
    try:
        shown_key = f"_intrusion_shown_{game_key}"
        if st.session_state.get(shown_key):
            return  # 既に演出済み。上部には何も残さない
        lines = _gather_intrusion(game_key)
        if not lines:
            return
        st.session_state[shown_key] = True
        _intrusion_cinematic(lines)
    except Exception:
        pass


# --------------------------------------------------------------------------
# 永続化（プレイヤー名キーのJSON）
# --------------------------------------------------------------------------
def _safe_name(name):
    # 英数字・ひらがな・カタカナ・漢字・アンダースコア・ハイフン・空白のみ許可
    s = re.sub(r"[^0-9A-Za-z぀-ゟ゠-ヿ一-鿿_\- ]", "_",
               (name or "").strip())
    s = s.strip().replace(" ", "_")
    return s[:32] or "guest"


def _save_path(name):
    return os.path.join(SAVE_DIR, _safe_name(name) + ".json")


def save():
    """現在の進行をファイルへ保存する（プレイヤー名が無ければ何もしない）。"""
    try:
        s = state()
    except Exception:
        return
    if not s.get("player"):
        return
    try:
        os.makedirs(SAVE_DIR, exist_ok=True)
        with open(_save_path(s["player"]), "w", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def delete_save(name=None):
    """プレイヤーの進行ファイルを削除する（name 省略時は現在のプレイヤー）。"""
    try:
        target = name or state().get("player")
    except Exception:
        target = name
    if not target:
        return
    try:
        p = _save_path(target)
        if os.path.exists(p):
            os.remove(p)
    except Exception:
        pass


def reset_session():
    """セッション内の進行を初期化する（次の描画で名前ゲートに戻る）。"""
    st.session_state["noxa"] = _default_state()


def load(name):
    """名前の保存をロードしてセッションへ反映する。無ければ新規開始。"""
    s = _default_state()
    s["player"] = name
    try:
        p = _save_path(name)
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
            for k in ("cleared", "board", "choices"):
                if isinstance(data.get(k), dict) and isinstance(s.get(k), dict):
                    s[k].update(data[k])
            s["seen_intro"] = bool(data.get("seen_intro", False))
    except Exception:
        pass
    st.session_state["noxa"] = s
    return s


# --------------------------------------------------------------------------
# クリア記録 / 解放ロジック
# --------------------------------------------------------------------------
def report_clear(key):
    """ゲーム側から呼ぶ。クリアを記録し調査ボードを更新、保存する。

    ポータル未統合・Streamlit未接続でも例外を投げず安全に動く（no-op化）。
    同じ画面で何度呼ばれても冪等。
    """
    try:
        s = state()
    except Exception:
        return
    if key not in s["cleared"]:
        return
    changed = not s["cleared"][key]
    s["cleared"][key] = True
    for item in BOARD_REVEAL.get(key, []):
        if item in s["board"] and not s["board"][item]:
            s["board"][item] = True
            changed = True
    if changed:
        save()


def unlock_all(complete=False):
    """【管理者用】全作品をクリア済みにし、調査ボードも全開示する。

    complete=True のときは Project 000 も完了扱い（ホーム演出を 'done' に）にし、
    「全クリアした状態」で最初から遊べるようにする。冪等で、保存も行う。
    """
    try:
        s = state()
    except Exception:
        return
    for k in GAME_KEYS:
        s["cleared"][k] = True
    for item in BOARD_ITEMS:
        s["board"][item] = True
    s["seen_intro"] = True
    if complete:
        s["choices"]["seen_000"] = True
    save()


def lock_all():
    """【管理者用】クリア状況・調査ボードを未クリア状態へ戻す（進行リセット）。

    プレイヤー名や観察ログは保持したまま、クリア/ボード/横断フラグだけ初期化する。
    """
    try:
        s = state()
    except Exception:
        return
    for k in GAME_KEYS:
        s["cleared"][k] = False
    for item in BOARD_ITEMS:
        s["board"][item] = False
    s["choices"] = {}
    s["seen_unlocks"] = []
    save()


def admin_enabled():
    """管理者パネルを表示してよいか（設定フラグ or セッションで解放済み）。"""
    if ADMIN_MODE:
        return True
    try:
        return bool(st.session_state.get("_noxa_admin"))
    except Exception:
        return False


def try_admin_unlock(code):
    """入力コードが管理者コードと一致すればセッションを管理者解放する。"""
    if not ADMIN_CODE:
        return False
    if (code or "").strip() == ADMIN_CODE:
        try:
            st.session_state["_noxa_admin"] = True
        except Exception:
            pass
        return True
    return False


def set_choice(key, value):
    """作品横断の選択フラグを記録（例: LAST30の軍/民間優先）。"""
    try:
        s = state()
    except Exception:
        return
    s["choices"][key] = value
    save()


def get_choice(key, default=None):
    try:
        return state()["choices"].get(key, default)
    except Exception:
        return default


def is_cleared(key):
    try:
        return bool(state()["cleared"].get(key))
    except Exception:
        return False


def clear_count():
    s = state()
    return sum(1 for k in GAME_KEYS if s["cleared"].get(k))


def clears_excluding(key):
    """指定キー以外のクリア数（例: アーケードの段階解放で自己依存の循環を避ける）。"""
    s = state()
    return sum(1 for k in GAME_KEYS if k != key and s["cleared"].get(k))


def all_cleared():
    s = state()
    return all(s["cleared"].get(k) for k in GAME_KEYS)


def unlocked_games():
    """現在解放されている作品キーの集合。"""
    s = state()
    unlocked = set(INITIAL_UNLOCKED)
    for src, dst in UNLOCK_CHAIN.items():
        if s["cleared"].get(src):
            unlocked.add(dst)
    return unlocked


def newly_unlocked_by(key):
    """keyをクリアしたことで解放される作品キー（演出用）。"""
    return UNLOCK_CHAIN.get(key)


def project000_unlocked():
    return all_cleared()


def board_complete():
    s = state()
    return all(s["board"].get(item) for item in BOARD_ITEMS)


# --------------------------------------------------------------------------
# ホーム画面の進化
# --------------------------------------------------------------------------
def seen_000():
    """Project 000 を最後まで見た（実験完了）か。"""
    try:
        return bool(state()["choices"].get("seen_000"))
    except Exception:
        return False


def portal_stage():
    """ホーム演出の段階を返す。

    'normal'  … 初期
    'echo'    … Project ECHO クリア後（Welcome back.）
    'arg'     … 404 クリア後（Welcome back, name）
    'pairlock'… PAIR LOCK クリア後（You have been here before.）
    'await'   … 全作品クリア・Project000未完（Subject Connected. / 待っていた）
    'done'    … Project000 完了後（ホームは元に戻るが Subject ID が残る）
    """
    s = state()
    if seen_000():
        return "done"
    if all_cleared():
        return "await"
    if s["cleared"].get("pairlock"):
        return "pairlock"
    if s["cleared"].get("arg"):
        return "arg"
    if s["cleared"].get("echo"):
        return "echo"
    return "normal"


# 演出の強度（UI侵食用 0:なし 〜 4:研究所端末）
STAGE_INTENSITY = {"normal": 0, "echo": 1, "arg": 2, "pairlock": 3, "await": 4, "done": 1}
