"""暗号ユーティリティ (シーザー / ヴィジュネル)。"""


def caesar(text: str, shift: int) -> str:
    out = []
    for ch in text:
        if ch.isupper():
            out.append(chr((ord(ch) - 65 + shift) % 26 + 65))
        elif ch.islower():
            out.append(chr((ord(ch) - 97 + shift) % 26 + 97))
        else:
            out.append(ch)
    return "".join(out)


def vigenere_encrypt(text: str, key: str) -> str:
    out, ki = [], 0
    key = key.upper()
    for ch in text.upper():
        if ch.isalpha():
            k = ord(key[ki % len(key)]) - 65
            out.append(chr((ord(ch) - 65 + k) % 26 + 65))
            ki += 1
        else:
            out.append(ch)
    return "".join(out)


def vigenere_decrypt(text: str, key: str) -> str:
    out, ki = [], 0
    key = key.upper()
    for ch in text.upper():
        if ch.isalpha():
            k = ord(key[ki % len(key)]) - 65
            out.append(chr((ord(ch) - 65 - k) % 26 + 65))
            ki += 1
        else:
            out.append(ch)
    return "".join(out)


def normalize(text: str) -> str:
    """回答比較用: 英数字のみ大文字化。"""
    return "".join(c for c in text.upper() if c.isalnum())


def extract_key_letters(name: str) -> str:
    """名前からローマ字(A〜Z)だけを抽出し大文字化する。

    NOXA登録名をヴィジュネル鍵へ変換するための下処理。
    スペース・記号・日本語表記などは全て削ぎ落とされる。"""
    return "".join(ch for ch in name.upper() if "A" <= ch <= "Z")


def key_from_name(name: str, fallback: str = "NULL") -> str:
    """プレイヤーの登録名からヴィジュネル鍵を生成する。

    抽出したローマ字が2文字未満(日本語名など、ローマ字表記を持たない
    登録名)の場合は fallback を返し、従来通りの鍵で成立させる。"""
    letters = extract_key_letters(name)
    return letters if len(letters) >= 2 else fallback
