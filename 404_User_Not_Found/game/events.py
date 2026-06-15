"""ランダムイベント演出 と 第四の壁演出 (ホラー強化版)。"""

import streamlit as st

from . import state, style

# 仕様書のランダムイベント
RANDOM_EVENTS = [
    "SYSTEM ERROR",
    "Connection Lost",
    "Unknown User Joined",
]

# それぞれの不穏なサブテキスト
_SUBTEXT = {
    "SYSTEM ERROR": "> 記録が、ひとりでに書き換わっていく……",
    "Connection Lost": "> 誰かが回線を、内側から切った。",
    "Unknown User Joined": "> あなたの後ろから、画面を覗いている。",
}

# 画面の隅に走る短い囁き
_WHISPERS = [
    "うしろ", "みてる", "だれ", "にげて", "もう おそい",
    "そこにいるの", "けして", "たすけて", "404",
]


def _rng_int(mod: int, salt: int = 0) -> int:
    """Math.random 不使用。進行状態から擬似乱数を作る。"""
    seed = (len(state.game()["clues"]) * 7
            + len(state.game()["decoded_messages"]) * 13
            + len(st.session_state.event_log) * 31
            + st.session_state.stage * 101
            + st.session_state.loops * 997
            + salt * 5)
    return seed % mod


def maybe_random_event():
    """進行状態依存で、高確率(約半分)に不穏なイベントを表示。"""
    # 囁きはほぼ毎回うっすら出す
    style.whisper(_WHISPERS[_rng_int(len(_WHISPERS), salt=3)])

    if _rng_int(2) == 0:
        idx = _rng_int(len(RANDOM_EVENTS), salt=1)
        ev = RANDOM_EVENTS[idx]
        st.session_state.event_log.append(ev)
        style.jumpscare()
        style.glitch_text(ev)
        st.caption(_SUBTEXT[ev])

        # Unknown User Joined は本人に言及して恐怖を煽る
        if ev == "Unknown User Joined" and st.session_state.player_name:
            style.whisper(f"……{st.session_state.player_name}。ねえ、{st.session_state.player_name}。")


def fourth_wall(player_name: str):
    """第四の壁演出: プレイヤー本人を名指しで追い詰める。"""
    name = player_name.strip() or "そこにいる あなた"
    style.jumpscare()
    style.boxed(
        f"<span class='corrupt' style='font-size:1.3rem'>[ 404 ]</span><br><br>"
        f"……<b>{name}</b>。そう、画面の前の <b>{name}</b>。<br>"
        f"これはゲームじゃない。あなたの IP も、起動時刻も、もう記録した。<br>"
        f"AKIRA を探していたつもり? <br>"
        f"<span class='whisper'>次に消えるのは、{name}、あなただ。</span><br>"
        f"<span class='blink' style='color:#ff003c'>_</span>"
    )
    if not state.has_flag("WALL_BROKEN"):
        state.set_flag("WALL_BROKEN")
        state.add_clue("画面の中の存在がこちらを認識した (第四の壁崩壊)")
