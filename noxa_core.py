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

import json
import os
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
    }


def state():
    """セッション内の共有state（無ければ初期化）を返す。"""
    if "noxa" not in st.session_state:
        st.session_state["noxa"] = _default_state()
    s = st.session_state["noxa"]
    # 旧バージョンのsaveに無いキーを補完
    for k in GAME_KEYS:
        s["cleared"].setdefault(k, False)
    for item in BOARD_ITEMS:
        s["board"].setdefault(item, False)
    s.setdefault("seen_unlocks", [])
    return s


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
def portal_title():
    """クリア進行に応じて変化するポータル名。"""
    s = state()
    if all_cleared():
        return "NOXA Monitoring System"
    if s["cleared"].get("pairlock"):
        return "NOXA Monitoring System"
    if s["cleared"].get("arg"):
        return "NOXA G̶a̶m̶e̶ Portal"
    if s["cleared"].get("echo"):
        return "NOXA G_me Portal"
    return "🕹️ ゲームポータル"


def portal_stage():
    """ホーム演出の段階を表す文字列を返す。

    'normal' → 'noise'(ECHO後) → 'glitch'(404後) → 'monitor'(PAIRLOCK後) → 'system'(全クリア)
    """
    s = state()
    if all_cleared():
        return "system"
    if s["cleared"].get("pairlock"):
        return "monitor"
    if s["cleared"].get("arg"):
        return "glitch"
    if s["cleared"].get("echo"):
        return "noise"
    return "normal"
