"""4種のエンディングと周回プレイ。"""

import streamlit as st

from . import audio, state, style

ENDINGS = {
    "normal": {
        "title": "NORMAL END — 失踪者救出",
        "color": "#39ff14",
        "body": (
            "あなたは手がかりを繋ぎ、AKIRA の居場所を特定した。<br>"
            "回線の向こうから、震える声が届く。「……ありがとう。やっと、見つけてくれた」<br>"
            "AKIRA は救出された。だが組織 NULL の影は、まだ消えていない。"
        ),
    },
    "secret": {
        "title": "SECRET END — 組織の正体発見",
        "color": "#00b3ff",
        "body": (
            "あなたは AKIRA よりも『NULL』を選んだ。<br>"
            "消去された人間たちの集合体——その全貌をあなたは記録し、世界に公開する。<br>"
            "真実は暴かれた。しかし、暴いた者もまた『記録される側』になる。"
        ),
    },
    "horror": {
        "title": "HORROR END — 標的はあなた",
        "color": "#ff003c",
        "body": (
            "あなたは自分の名前で接続した。その瞬間、部屋の温度が下がる。<br>"
            "背後で、椅子が軋む音。振り返る前に、画面が反転する。<br>"
            "<b class='corrupt'>『404 - User Not Found』</b><br>"
            "次に消えるのは AKIRA ではない。あなたの名前は、検索結果から静かに抜け落ちる。<br>"
            "家族も、友人も、明日にはあなたを思い出せない。<br>"
            "<span class='whisper'>おかえり。こちら側へ。</span>"
        ),
    },
    "true": {
        "title": "TRUE END — 全フラグ回収",
        "color": "#ffb000",
        "body": (
            "メール、画像、音声、ログ、隠しページ、そして第四の壁の向こう——<br>"
            "全ての断片を集めたあなただけが、本当の出口に辿り着く。<br>"
            "AKIRA を救い、NULL を解体し、そして<b>あなた自身の名前を取り戻した</b>。<br>"
            "404 は、404 ではなくなった。"
        ),
    },
}


def show():
    key = state.game().get("ending") or "normal"
    e = ENDINGS.get(key, ENDINGS["normal"])

    if key == "horror":
        style.jumpscare()
        st.audio(audio.dread_wav_bytes(seconds=5.0), format="audio/wav")

    st.markdown(
        f"<h1 style='color:{e['color']};text-align:center'>{e['title']}</h1>",
        unsafe_allow_html=True,
    )
    style.boxed(e["body"])

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.metric("回収フラグ", f"{state.flag_count()} / {len(state.TRUE_END_FLAGS)}")
    with col2:
        st.metric("周回数", f"{st.session_state.loops + 1} 周目")

    with st.expander("収集した手がかり / 解読メッセージ"):
        st.write("**clues**")
        for c in state.game()["clues"]:
            st.write(f"- {c}")
        st.write("**decoded_messages**")
        for d in state.game()["decoded_messages"]:
            st.write(f"- {d}")
        st.write("**hidden_flags**")
        st.write(", ".join(state.game()["hidden_flags"]) or "(なし)")

    if key != "true":
        st.info("💡 全フラグ(隠しページ・第四の壁を含む)を回収すると "
                "**TRUE END** に到達できる。周回プレイで挑戦しよう。")

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔁 周回プレイ (NEW GAME +)", use_container_width=True):
            state.reset_keep_loops()
            st.rerun()
    with c2:
        if st.button("⏏ タイトルに戻る", use_container_width=True):
            st.session_state.stage = 0
            st.session_state.game = state._default_state()
            st.rerun()
