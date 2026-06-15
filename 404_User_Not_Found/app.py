"""404_User_Not_Found — ARG (Streamlit)

実行: streamlit run app.py
"""

import streamlit as st

from game import audio, endings, stages, state, style

try:
    st.set_page_config(
        page_title="404_User_Not_Found",
        page_icon="🛑",
        layout="centered",
        initial_sidebar_state="expanded",
    )
except Exception:
    pass  # ポータルに統合された場合は無視

style.inject()
state.init()


# ------------------------------------------------------------------
# サイドバー : セッション状態モニタ
# ------------------------------------------------------------------
def sidebar():
    with st.sidebar:
        st.markdown("### ▌SESSION MONITOR")
        st.caption("session_state")
        g = state.game()
        st.write(f"clues : **{len(g['clues'])}**")
        st.write(f"decoded : **{len(g['decoded_messages'])}**")
        st.write(f"flags : **{state.flag_count()} / {len(state.TRUE_END_FLAGS)}**")
        st.write(f"ending : **{g['ending'] or 'None'}**")
        st.divider()

        # 進行バー
        prog = min(st.session_state.stage, 5) / 5 if st.session_state.stage <= 5 else 1.0
        st.progress(prog, text=f"STAGE {min(st.session_state.stage,5)}/5")
        st.caption(f"周回: {st.session_state.loops + 1} 周目")

        if g["clues"]:
            with st.expander("CLUES"):
                for c in g["clues"]:
                    st.write(f"- {c}")

        st.divider()
        if st.button("⟲ 最初から", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()


# ------------------------------------------------------------------
# タイトル画面
# ------------------------------------------------------------------
def title_screen():
    style.glitch_text("404")
    st.markdown("<h1>USER NOT FOUND</h1>", unsafe_allow_html=True)
    st.caption("ARG / 都市伝説 / ホラー / 謎解き ── 想定プレイ時間 60〜120分")

    st.audio(audio.dread_wav_bytes(seconds=8.0), format="audio/wav")
    st.caption("🎧 ヘッドホン推奨。暗い部屋で、ひとりで。")

    style.boxed(
        "ある日、あなたの元に一通のメッセージが届く。<br><br>"
        "<b style='color:#ff003c;font-size:1.4rem'>「HELP」</b><br><br>"
        "調査を進めるにつれ、失踪事件と謎の組織の存在が明らかになる。<br>"
        "<span class='whisper'>——そして、画面のこちら側にいるあなたのことも、奴らは知っている。</span>"
    )

    st.markdown("<p class='corrupt'>⚠ 本作はホラー表現（突然の点滅・大きな音・名指しの演出）を含みます。</p>",
                unsafe_allow_html=True)

    st.text_input("オペレーター名 (あなたの本名) を入力",
                  key="player_name",
                  placeholder="本名を入れるほど、物語はあなたに近づく……")
    st.caption("※ この名前は物語の後半で牙を剥く。")

    if st.button("▶ 接続を開始する", type="primary", use_container_width=True):
        state.goto(1)
        st.rerun()

    with st.expander("遊び方 / 仕様"):
        st.markdown(
            "- 全5ステージ: メール → 画像 → 音声 → Webログ → 真相\n"
            "- ミニゲーム: シーザー暗号 / QR復元 / 画像探索 / モールス / ヴィジュネル暗号\n"
            "- エンディングは4種 (Normal / Secret / Horror / True)\n"
            "- 隠しページ・隠しイベント・第四の壁・周回プレイ要素あり\n"
            "- 全8フラグ回収で **TRUE END**"
        )


# ------------------------------------------------------------------
# ルーター
# ------------------------------------------------------------------
ROUTES = {
    1: stages.stage1,
    2: stages.stage2,
    3: stages.stage3,
    4: stages.stage4,
    5: stages.stage5,
    99: stages.hidden_page,
    100: endings.show,
}


def main():
    sidebar()
    stage = st.session_state.stage
    if stage == 0:
        title_screen()
    else:
        ROUTES.get(stage, title_screen)()


main()
