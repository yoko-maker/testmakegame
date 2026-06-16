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
def _now_str():
    try:
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ""


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


def render_intrusion(game_key):
    """各ゲーム冒頭で呼ぶ。作品間干渉(⑦)と赤い女の侵食(⑥)を控えめに描く。

    ポータル未統合・Streamlit未接続でも安全（no-op）。赤い女の出現可否は
    セッション内で作品ごとに一度だけ判定し、再描画でのちらつきを防ぐ。
    """
    try:
        for icon, text in interference_lines(game_key):
            st.markdown(
                f"<div style='font-family:monospace;color:#d66;font-size:0.82em;"
                f"border-left:3px solid #c33;padding:2px 8px;margin:4px 0;"
                f"background:rgba(120,20,20,0.08);'>{icon} {text}</div>",
                unsafe_allow_html=True)

        lvl = red_woman_level()
        if lvl <= 0:
            return
        key = f"_redwoman_{game_key}"
        if key not in st.session_state:
            prob = [0.0, 0.25, 0.5, 0.85][lvl]
            st.session_state[key] = (random.random() < prob)
        if st.session_state[key]:
            msg = RED_WOMAN_GLIMPSES[min(lvl - 1, len(RED_WOMAN_GLIMPSES) - 1)]
            st.markdown(
                f"<div style='color:#e44;font-size:0.82em;opacity:0.85;margin:4px 0;'>"
                f"🔴 {msg}</div>", unsafe_allow_html=True)
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
