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
