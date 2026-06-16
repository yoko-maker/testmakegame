"""4種のエンディングと周回プレイ。"""

import streamlit as st

from . import audio, state, style

# NOXA Universe（ポータル統合時のみ利用可能 / 単体起動では import 失敗を無視）
try:
    import noxa_core as _noxa
except Exception:
    _noxa = None

def _endings(name: str, t: str):
    """プレイヤー名・時刻を織り込んだエンディング定義を返す。"""
    time_phrase = f"あの {t} に接続した" if t else "あの夜に接続した"
    return {
        "normal": {
            "title": "NORMAL END — 失踪者救出",
            "color": "#39ff14",
            "body": (
                "あなたは断片を繋ぎ合わせ、AKIRA の居場所——NOXA の旧サーバ区画を特定した。<br>"
                "回線の向こうから、震える声が届く。「……ありがとう。やっと、見つけてくれた」<br>"
                "本物の AKIRA の意識を、あなたは封印の外へ救い出した。<br>"
                "退院した彼女は、もう SNS を開かない。それでも、生きている。<br>"
                "——だが、プロジェクト ECHO は止まっていない。"
                "NULL の影は、まだ無数のサーバの底で蠢いている。<br>"
                "<span class='whisper'>あなたが解いたのは、ほんの一人分の 404 にすぎない。</span>"
            ),
        },
        "secret": {
            "title": "SECRET END — 組織の正体発見",
            "color": "#00b3ff",
            "body": (
                "あなたは AKIRA を救うより先に、『NULL』の正体を世界へ突きつけることを選んだ。<br>"
                "NOXA研究機構。プロジェクト ECHO。消去された人々が群体化した NULL——<br>"
                "あなたは全てを記録し、暗号化を剥がし、ネットの海へ流した。<br>"
                "数時間、世界は震えた。そして次の朝、その投稿は『存在しなかったこと』になっていた。<br>"
                "リンクは 404。アカウントは凍結。あなたの名前は、検索結果からそっと欠けていく。<br>"
                "<span class='corrupt'>真実を暴いた者は、真実とともに消される。"
                "それが NOXA の流儀だ。</span>"
            ),
        },
        "horror": {
            "title": "HORROR END — 標的はあなた",
            "color": "#ff003c",
            "body": (
                f"あなたは、AKIRA ではなく<b>自分の名前</b>で接続を試みた。<br>"
                f"その瞬間、部屋の温度が下がる。背後で、椅子が軋む音。<br>"
                f"画面が反転し、検索窓に勝手に文字が打ち込まれていく——<b>{name}</b>。<br>"
                f"<b class='corrupt'>『404 - User Not Found』</b><br>"
                f"NOXA はとうに知っていた。{time_phrase}のが、ほかでもない <b>{name}</b> だと。<br>"
                f"次に消えるのは AKIRA ではない。あなたの名前が、検索結果から静かに抜け落ちる。<br>"
                f"家族も、友人も、明日にはあなたを思い出せない。"
                f"写真の中のあなただけが、顔のない影に変わっていく。<br>"
                f"<span class='whisper'>おかえり、{name}。こちら側へ。ここでは、あなたも『わたしたち』だ。</span>"
            ),
        },
        "true": {
            "title": "TRUE END — 全フラグ回収",
            "color": "#ffb000",
            "body": (
                "メール、画像、音声、ログ、AKIRA の人格断片、二つの隠し階層、"
                "そして第四の壁の向こう側——<br>"
                "全てを集めたあなただけが、404 の<b>本当の出口</b>に辿り着く。<br>"
                "あなたは NOXA 内部ログから ECHO の停止コマンドを見つけ、"
                "封印された意識たちを一斉に解き放った。<br>"
                "AKIRA を救い、NULL を——消された人々を——一人ずつ名前のある世界へ戻した。<br>"
                f"そして最後に、被験体リストから<b>あなた自身の名前『{name}』</b>を削除した。<br>"
                "404 は、もう 404 ではない。検索すれば、ちゃんと『見つかる』。<br>"
                "<span class='whisper'>——ただし。NOXA は、各地にまだ他の施設を持っている。</span>"
            ),
        },
    }


def show():
    key = state.game().get("ending") or "normal"
    if _noxa:
        _noxa.report_clear("arg")
    name = (st.session_state.get("player_name") or "").strip() or "あなた"
    t = (st.session_state.get("player_time") or "").strip()
    endings = _endings(name, t)
    e = endings.get(key, endings["normal"])

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
