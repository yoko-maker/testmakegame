"""ストーリー5ステージ + 隠しページ。"""

import streamlit as st

from . import audio, events, lore, minigames, state, style


def _advance_button(label: str, target: int):
    st.divider()
    if st.button(label, type="primary", use_container_width=True):
        state.goto(target)
        st.rerun()


# ------------------------------------------------------------------
# Stage 1 : メール解析
# ------------------------------------------------------------------
def stage1():
    st.header("STAGE 1 — メール解析")
    events.maybe_random_event()

    st.markdown("深夜2時44分。閉じたはずの端末が、ひとりでに点灯する。"
                "受信トレイに、送信日時の壊れた1通——あなた宛だ。")
    style.boxed(
        "<div class='email-head'>FROM : unknown@404.null<br>"
        "TO &nbsp;&nbsp;: <span class='corrupt'>you (見つけた)</span><br>"
        "SUBJECT : <b>HELP</b><br>"
        "TIME : --:--:-- / 既読: あなたより前に、誰かが</div><br>"
        "助けて。 ここがどこか分からない。 鏡の中みたいに、ぜんぶ反転してる。<br>"
        "彼らはこれを消そうとする。 あなたが読んだ時点で、もう見られてる。 早く。<br><br>"
        "DULND GQLI"
    )

    solved = minigames.caesar_game()
    if solved:
        state.set_flag("EMAIL")
        st.info("メールに隠された名前を解読した。——AKIRA。その名前に、なぜか覚えがある気がする。")
        lore.show_fragment(1)
        st.caption("解読を進めるほど、見知らぬはずのこの人の輪郭が、はっきりしてくる。")
        _advance_button("▶ Stage 2 へ — 添付画像を解析する", 2)


# ------------------------------------------------------------------
# Stage 2 : 画像解析
# ------------------------------------------------------------------
def stage2():
    st.header("STAGE 2 — 画像解析")
    events.maybe_random_event()
    st.markdown("メールには2枚の画像が添付されていた。どちらも破損・改竄され、"
                "開くたびにノイズの形が変わる。見ているのか、見られているのか。")
    st.info("🔍 画像にカーソルを合わせると右上に表示される拡大アイコンで全画面表示できます。"
            "**全画面から戻るには `Esc` キー、または右上の ✕ をクリック**してください。")

    tab1, tab2 = st.tabs(["添付 #1 : QRコード", "添付 #2 : ノイズ画像"])
    with tab1:
        qr_ok = minigames.qr_game()
    with tab2:
        img_ok = minigames.image_search_game()

    if qr_ok and img_ok:
        state.set_flag("IMAGE")
        st.info("接続先コードと組織名らしき文字列『NULL』を入手した。")
        lore.show_fragment(2)
        _advance_button("▶ Stage 3 へ — 音声を解析する", 3)


# ------------------------------------------------------------------
# Stage 3 : 音声解析
# ------------------------------------------------------------------
def stage3():
    st.header("STAGE 3 — 音声解析")
    events.maybe_random_event()
    st.markdown("QRから辿った先のサーバに、録音ファイルが一つだけ。"
                "ファイル名は、あなたのログイン名と同じだった。")

    ok = minigames.morse_game()
    if ok:
        state.set_flag("AUDIO")
        st.info("救難信号 SOS と発信元 NULL を受信。"
                "——AKIRA はまだ生きている。生きて、いてほしい。")
        lore.show_fragment(3)
        st.caption("もう、ただの『失踪者』じゃない。あなたはこの人を助けたいと思い始めている。")
        _advance_button("▶ Stage 4 へ — Webログを解析する", 4)


# ------------------------------------------------------------------
# Stage 4 : Webログ解析
# ------------------------------------------------------------------
def stage4():
    st.header("STAGE 4 — Webログ解析")
    events.maybe_random_event()
    st.markdown("発信元サーバのアクセスログを入手。最終行のアクセス元IPは——"
                "あなたのものだった。まだ一度も、ここに繋いでいないのに。")

    ok = minigames.vigenere_game()
    if ok:
        state.set_flag("WEBLOG")
        st.info("警告文を復号した。『奴ら』は、最初からあなたを見ていた。"
                "署名は——NOXA INSTITUTE。")
        lore.show_fragment(4)

        st.caption(
            "ログの片隅に、本来表示されないはずのパスが紛れている……"
        )
        if st.button("🔒 /_void/ にアクセスする (隠しリンク)", key="hidden_link"):
            state.set_flag("HIDDEN_PAGE")
            state.goto(99)   # 隠しページ
            st.rerun()

        _advance_button("▶ Stage 5 へ — 真相を解明する", 5)


# ------------------------------------------------------------------
# 隠しページ : /_void/
# ------------------------------------------------------------------
def hidden_page():
    st.header("/_void/ — ACCESS GRANTED")
    style.jumpscare()
    style.glitch_text("404 USER NOT FOUND")
    st.audio(audio.dread_wav_bytes(), format="audio/wav")
    st.markdown(
        "ここは消されたユーザーたちの墓場。無数の『404』が、名前を奪われたまま並んでいる。<br>"
        "スクロールしても、しても、終わらない。AKIRA もその一人だった。<br>"
        "——そして、リストの一番下。まだ薄く点滅しているその名前を、あなたは知っている。",
        unsafe_allow_html=True,
    )
    style.whisper(f"{st.session_state.player_name or 'あなた'} ……予約済み")
    style.boxed(
        "我々 <b>NULL</b> は実在しない。<br>"
        "存在を消された者だけが、ここに辿り着ける。<br>"
        "<b>NULL とは、NOXA研究機構に消去された人間たちの集合体である。</b><br>"
        "<span class='corrupt'>そして、ここを見たあなたも、もう半分こちら側だ。</span>"
    )

    # AKIRA の断片が揃っていれば、最後のメッセージ (動機の完成) を提示
    if lore.collected_fragment_count() >= len(lore.FRAGMENTS):
        st.markdown("#### ✉ 墓場の片隅に、宛先のない一通")
        lore.show_last_message()

    if st.button("真実を記録する", key="record_truth"):
        state.set_flag("ORG_IDENTITY")
        state.add_clue("組織NULLの正体: NOXAに消去された人間たちの集合体")
        st.success("組織の正体を記録した。[ORG_IDENTITY 取得]")

    # 第二の隠しページ: 404 の裏側 = NOXA 内部ログ
    if state.has_flag("ORG_IDENTITY"):
        st.divider()
        st.caption(
            "墓場の最奥、点滅する『404』の一つを長く見つめると——"
            "その数字の**裏側**に、別の階層が透けて見える。"
        )
        if st.button("⛔ 404 の裏側 /_void/noxa/ へ潜る (隠し階層)", key="to_noxa"):
            state.goto(98)   # NOXA 内部ログ
            st.rerun()

    st.divider()
    if st.button("◀ ログ解析に戻る", key="back_from_void"):
        state.goto(4)
        st.rerun()


# ------------------------------------------------------------------
# 第二の隠しページ : /_void/noxa/ — NOXA 内部ログ (404の裏側)
#   True End フラグ NOXA_LOG を付与する。
# ------------------------------------------------------------------
def noxa_log_page():
    st.header("/_void/noxa/ — 404 の裏側")
    style.jumpscare()
    style.glitch_text("NOXA INSTITUTE")
    st.audio(audio.dread_wav_bytes(seconds=7.0), format="audio/wav")
    st.markdown(
        "404 は『見つからない』エラーではなかった。<br>"
        "それは <b>NOXA研究機構</b> が、消した人間に貼る<b>封印の番号</b>だった。<br>"
        "ここはその封印の内側——プロジェクト『ECHO』の生ログが、いまも流れ続けている。",
        unsafe_allow_html=True,
    )

    lore.show_noxa_log()

    style.boxed(
        "プロジェクト ECHO: 人間の意識・記憶を AI へ写し取る計画。<br>"
        "成功例は『もう喋らない』。失敗例は『404』として消される。<br>"
        "AKIRA は——その<b>狭間</b>に落ちた一人だった。<br>"
        "<span class='corrupt'>そして ECHO-0410。ログを辿った外部接続者を、"
        "次の被験体に指定する——それが、いま接続しているあなただ。</span>"
    )
    style.whisper("ようこそ、次の ECHO。")

    if st.button("内部ログを記録する", key="record_noxa"):
        state.set_flag("NOXA_LOG")
        state.add_clue("NOXA内部ログ: プロジェクトECHO=意識の転写計画。404は封印番号。")
        state.add_decoded("PROJECT ECHO / NOXA INSTITUTE")
        st.success("NOXAの内部ログを記録した。[NOXA_LOG 取得]——True End への最後の鍵。")

    st.divider()
    if st.button("◀ /_void/ に戻る", key="back_from_noxa"):
        state.goto(99)
        st.rerun()


# ------------------------------------------------------------------
# Stage 5 : 真相解明 (エンディング分岐)
# ------------------------------------------------------------------
def stage5():
    st.header("STAGE 5 — 真相解明")
    events.maybe_random_event()

    st.markdown(
        "全ての手がかりが一点を指している。AKIRA の居場所、そして組織 NULL。<br>"
        "気づけば部屋の照明は落ち、画面の灯りだけが顔を照らしている。<br>"
        "最後の選択が、この物語の——そして<b>あなたの</b>結末を決める。",
        unsafe_allow_html=True,
    )

    # 失踪者を助けたい動機の最終確認: 断片が揃っていれば最後のメッセージを再掲
    if lore.collected_fragment_count() >= len(lore.FRAGMENTS):
        st.markdown("#### ✉ AKIRA から、あなたへ")
        lore.show_last_message()

    # 第四の壁演出
    if state.has_flag("WALL_BROKEN") or state.flag_count() >= 4:
        events.fourth_wall(st.session_state.player_name, st.session_state.player_time)

    st.subheader("どう行動する?")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("AKIRA を救出する", use_container_width=True):
            _decide_ending()
            st.rerun()
        if st.button("組織 NULL の正体を暴く", use_container_width=True):
            if state.has_flag("ORG_IDENTITY"):
                state.game()["ending"] = "secret"
            else:
                st.warning("まだ組織の正体を掴んでいない。隠しページを探せ。")
                return
            state.goto(100)
            st.rerun()
    with c2:
        if st.button("自分の名前で接続を試みる", use_container_width=True):
            # ホラーEnd分岐
            state.set_flag("WALL_BROKEN")
            state.game()["ending"] = "horror"
            state.goto(100)
            st.rerun()
        if st.button("全ての真実を統合する", use_container_width=True):
            if state.all_flags():
                state.game()["ending"] = "true"
                state.goto(100)
                st.rerun()
            else:
                missing = state.flag_count()
                st.warning(f"フラグ不足 ({missing}/{len(state.TRUE_END_FLAGS)})。"
                           " 隠しページ2種・第四の壁を含む全てを回収する必要がある。")


def _decide_ending():
    """救出ルート: フラグ数で Normal / True を分岐。"""
    if state.all_flags():
        state.game()["ending"] = "true"
    else:
        state.game()["ending"] = "normal"
    state.goto(100)
