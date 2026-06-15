"""ミニゲーム5種。各関数は解けたら True を返す。

仕様書のミニゲーム:
  - QRコード復元
  - モールス信号解読
  - シーザー暗号
  - ヴィジュネル暗号
  - 画像探索
"""

import streamlit as st

from . import audio, ciphers, images, state, style


def _solved_key(name: str) -> str:
    return f"solved::{name}::{st.session_state.loops}"


def _is_solved(name: str) -> bool:
    return st.session_state.get(_solved_key(name), False)


def _mark_solved(name: str):
    st.session_state[_solved_key(name)] = True


# ------------------------------------------------------------------
# シーザー暗号
# ------------------------------------------------------------------
def caesar_game() -> bool:
    """暗号文 'ILQG DNLUD' (shift 3) を 'FIND AKIRA' に復号。"""
    name = "caesar"
    answer = "FINDAKIRA"
    cipher = "ILQG DNLUD"

    st.markdown("#### ▌シーザー暗号")
    st.write("メール本文の末尾に、ずらされた文字列が紛れている。")
    style.boxed(f"暗号文: <code>{cipher}</code>")
    st.caption("ヒント: 各文字を逆方向に一定数ずらす。シフト量は 3。")

    if _is_solved(name):
        st.success("復号済み: FIND AKIRA")
        return True

    shift = st.slider("シフト量を選択", 1, 25, 1, key="caesar_shift")
    st.write("プレビュー:")
    st.code(ciphers.caesar(cipher, -shift))

    guess = st.text_input("復号文を入力", key="caesar_in")
    if st.button("解読", key="caesar_btn"):
        if ciphers.normalize(guess) == answer:
            _mark_solved(name)
            state.add_decoded("FIND AKIRA")
            state.add_clue("失踪者の名前: AKIRA (明)")
            st.rerun()
        else:
            st.error("ACCESS DENIED — 復号に失敗。")
    return _is_solved(name)


# ------------------------------------------------------------------
# QRコード復元
# ------------------------------------------------------------------
def qr_game() -> bool:
    name = "qr"
    st.markdown("#### ▌QRコード復元")
    st.write("添付画像のQRコードは左上のファインダーパターンが欠損している。"
             "正しいパターンを選んで復元せよ。")

    correct, candidates = images.make_qr_puzzle()
    # 欠損QRの表示
    import numpy as np
    full = np.zeros((11, 11), dtype=int)
    full[:7, :7] = correct
    mask = np.zeros((11, 11), dtype=bool)
    mask[:7, :7] = True
    st.image(images.matrix_to_image(full, missing_mask=mask),
             caption="破損したQRコード [左上が欠損]")

    if _is_solved(name):
        st.success("復元成功: コード [7A-NULL] を取得")
        return True

    labels = ["パターン A", "パターン B", "パターン C", "パターン D"]
    st.write("欠損部に当てはまるパターンを選んで『復元』せよ。")
    cols = st.columns(4)
    picked = None
    for i, col in enumerate(cols):
        with col:
            st.image(images.qr_candidate(candidates[i]), caption=labels[i])
            if st.button(f"{labels[i]} で復元", key=f"qr_pick_{i}"):
                picked = i
    if picked is not None:
        # candidates[0] が正解
        if picked == 0:
            _mark_solved(name)
            state.add_clue("復元したQRから抽出: 接続先 7A-NULL")
            st.rerun()
        else:
            st.error("読み取り不能 — パターンが一致しない。")
    return _is_solved(name)


# ------------------------------------------------------------------
# 画像探索
# ------------------------------------------------------------------
def image_search_game() -> bool:
    name = "imgsearch"
    secret = "NULL"
    st.markdown("#### ▌画像探索")
    st.write("ノイズ画像のどこかに隠し文字が埋め込まれている。読み取って入力せよ。")
    st.image(images.make_hidden_image(secret), caption="復元された添付画像 #2")
    st.caption("ヒント: 画面の明るさを上げる / 目を細めると浮かび上がる。")

    if _is_solved(name):
        st.success("隠し文字を発見: NULL")
        return True

    guess = st.text_input("隠し文字を入力", key="img_in")
    if st.button("照合", key="img_btn"):
        if ciphers.normalize(guess) == secret:
            _mark_solved(name)
            state.add_clue("画像から組織名らしき文字列: NULL")
            st.rerun()
        else:
            st.error("該当なし — もう一度画像を観察せよ。")
    return _is_solved(name)


# ------------------------------------------------------------------
# モールス信号解読
# ------------------------------------------------------------------
def morse_game() -> bool:
    name = "morse"
    message = "SOS NULL"   # 解読対象
    st.markdown("#### ▌モールス信号解読")
    st.write("ノイズに埋もれた録音が、ひとりでに再生され始める。"
             "ヘッドホンを着けて、耳を澄ませ——聞き取れるのは、信号だけではないかもしれない。")
    st.audio(audio.morse_to_wav_bytes(message), format="audio/wav")
    style.whisper("……たすけて……ここから だして……")
    st.caption("※ 視覚的な補助はない。音だけが頼りだ。長音(—)と短音(・)を聞き分けよ。")

    if _is_solved(name):
        st.success("解読完了: SOS NULL")
        return True

    guess = st.text_input("解読したメッセージを入力", key="morse_in")
    if st.button("解読", key="morse_btn"):
        if ciphers.normalize(guess) == ciphers.normalize(message):
            _mark_solved(name)
            state.add_decoded("SOS NULL")
            state.add_clue("音声の救難信号: SOS / 発信元 NULL")
            state.set_flag("MORSE_SOS")
            st.rerun()
        else:
            st.error("ノイズに埋もれた — 解読失敗。")
    return _is_solved(name)


# ------------------------------------------------------------------
# ヴィジュネル暗号
# ------------------------------------------------------------------
def vigenere_game() -> bool:
    name = "vigenere"
    plain = "THEY ARE WATCHING YOU"
    key = "NULL"
    cipher = ciphers.vigenere_encrypt(plain, key)

    st.markdown("#### ▌ヴィジュネル暗号")
    st.write("Webログから抽出した暗号文。鍵はこれまでに何度も見た4文字。")
    style.boxed(f"暗号文: <code>{cipher}</code>")
    st.caption("ヒント: 鍵は組織名 (画像探索で見つけたもの)。")

    if _is_solved(name):
        st.success("復号済み: THEY ARE WATCHING YOU")
        return True

    key_in = st.text_input("鍵を入力", key="vig_key")
    if key_in:
        st.write("復号プレビュー:")
        st.code(ciphers.vigenere_decrypt(cipher, key_in or "A"))
    guess = st.text_input("復号文を入力", key="vig_in")
    if st.button("解読", key="vig_btn"):
        if ciphers.normalize(guess) == ciphers.normalize(plain):
            _mark_solved(name)
            state.add_decoded("THEY ARE WATCHING YOU")
            state.add_clue("Webログの警告: THEY ARE WATCHING YOU")
            st.rerun()
        else:
            st.error("鍵が違う — 復号に失敗。")
    return _is_solved(name)
