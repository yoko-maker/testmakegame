"""セッション管理。仕様書の session_state 構造を実装する。"""

import streamlit as st

# 仕様書のフラグ定義
FLAGS = {
    "EMAIL": "Stage1 メール解析クリア",
    "IMAGE": "Stage2 画像解析クリア",
    "AUDIO": "Stage3 音声解析クリア",
    "WEBLOG": "Stage4 Webログ解析クリア",
    "ORG_IDENTITY": "組織[NULL]の正体を発見",   # Secret End 条件
    "HIDDEN_PAGE": "隠しページ到達",
    "WALL_BROKEN": "第四の壁を越えた",
    "MORSE_SOS": "モールスでSOSを受信",
}

# 全フラグ回収 (True End) に必要なフラグ
TRUE_END_FLAGS = ["EMAIL", "IMAGE", "AUDIO", "WEBLOG",
                  "ORG_IDENTITY", "HIDDEN_PAGE", "WALL_BROKEN", "MORSE_SOS"]


def _default_state():
    return {
        "clues": [],
        "decoded_messages": [],
        "hidden_flags": [],
        "ending": None,
    }


def init():
    """セッション初期化。周回プレイのカウントは保持する。"""
    if "game" not in st.session_state:
        st.session_state.game = _default_state()
    if "stage" not in st.session_state:
        st.session_state.stage = 0          # 0 = タイトル
    if "loops" not in st.session_state:
        st.session_state.loops = 0          # 周回数
    if "player_name" not in st.session_state:
        st.session_state.player_name = ""
    if "event_log" not in st.session_state:
        st.session_state.event_log = []


def game():
    return st.session_state.game


def add_clue(text: str):
    if text not in game()["clues"]:
        game()["clues"].append(text)


def add_decoded(text: str):
    if text not in game()["decoded_messages"]:
        game()["decoded_messages"].append(text)


def set_flag(flag: str):
    if flag not in game()["hidden_flags"]:
        game()["hidden_flags"].append(flag)


def has_flag(flag: str) -> bool:
    return flag in game()["hidden_flags"]


def flag_count() -> int:
    return len([f for f in TRUE_END_FLAGS if has_flag(f)])


def all_flags() -> bool:
    return all(has_flag(f) for f in TRUE_END_FLAGS)


def goto(stage: int):
    st.session_state.stage = stage


def reset_keep_loops():
    """周回プレイ: フラグ・進行をリセットし周回数を加算。"""
    st.session_state.loops += 1
    st.session_state.game = _default_state()
    st.session_state.stage = 1
    st.session_state.event_log = []
