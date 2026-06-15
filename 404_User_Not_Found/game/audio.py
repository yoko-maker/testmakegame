"""モールス信号の音声 (WAV) を numpy で合成する。"""

import io
import wave
import numpy as np

MORSE = {
    "A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".",
    "F": "..-.", "G": "--.", "H": "....", "I": "..", "J": ".---",
    "K": "-.-", "L": ".-..", "M": "--", "N": "-.", "O": "---",
    "P": ".--.", "Q": "--.-", "R": ".-.", "S": "...", "T": "-",
    "U": "..-", "V": "...-", "W": ".--", "X": "-..-", "Y": "-.--",
    "Z": "--..",
    "0": "-----", "1": ".----", "2": "..---", "3": "...--", "4": "....-",
    "5": ".....", "6": "-....", "7": "--...", "8": "---..", "9": "----.",
}

_SR = 44100
_FREQ = 620          # トーン周波数
_UNIT = 0.09         # 1単位の秒数 (dot)


def _tone(duration: float) -> np.ndarray:
    t = np.linspace(0, duration, int(_SR * duration), endpoint=False)
    wave_arr = 0.5 * np.sin(2 * np.pi * _FREQ * t)
    # クリックノイズ防止のフェード
    fade = min(200, len(wave_arr) // 8)
    if fade > 0:
        env = np.ones_like(wave_arr)
        env[:fade] = np.linspace(0, 1, fade)
        env[-fade:] = np.linspace(1, 0, fade)
        wave_arr *= env
    return wave_arr


def _silence(duration: float) -> np.ndarray:
    return np.zeros(int(_SR * duration))


def text_to_morse(text: str) -> str:
    out = []
    for ch in text.upper():
        if ch == " ":
            out.append("/")
        elif ch in MORSE:
            out.append(MORSE[ch])
    return " ".join(out)


def _pcm_to_wav(signal: np.ndarray) -> bytes:
    pcm = np.int16(signal / (np.max(np.abs(signal)) + 1e-9) * 32767 * 0.8)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(_SR)
        wf.writeframes(pcm.tobytes())
    return buf.getvalue()


def dread_wav_bytes(seconds: float = 6.0, seed: int = 666) -> bytes:
    """不穏なアンビエンス: 低い唸り + 不規則なノイズ + 遠い悲鳴のような上下。"""
    rng = np.random.default_rng(seed)
    n = int(_SR * seconds)
    t = np.linspace(0, seconds, n, endpoint=False)
    # 低周波のうねり
    drone = 0.35 * np.sin(2 * np.pi * 47 * t) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.3 * t))
    drone += 0.18 * np.sin(2 * np.pi * 58 * t + 1.3)
    # ざらついたホワイトノイズ (静電気)
    hiss = 0.08 * rng.standard_normal(n)
    # 遠くで揺らぐ高音 (不安をあおる)
    wail = 0.06 * np.sin(2 * np.pi * (880 + 120 * np.sin(2 * np.pi * 0.15 * t)) * t)
    # 断続的なクリック (信号のノイズ)
    clicks = np.zeros(n)
    for _ in range(int(seconds * 6)):
        i = int(rng.integers(0, n - 50))
        clicks[i:i + 30] += 0.5 * rng.standard_normal(30)
    signal = drone + hiss + wail + clicks
    return _pcm_to_wav(signal)


def morse_to_wav_bytes(text: str) -> bytes:
    """テキスト -> モールス音声 (WAV bytes)。"""
    segments = []
    for ch in text.upper():
        if ch == " ":
            segments.append(_silence(_UNIT * 7))
            continue
        code = MORSE.get(ch)
        if not code:
            continue
        for i, sym in enumerate(code):
            dur = _UNIT if sym == "." else _UNIT * 3
            segments.append(_tone(dur))
            segments.append(_silence(_UNIT))      # シンボル間
        segments.append(_silence(_UNIT * 2))      # 文字間 (合計3単位)

    if not segments:
        signal = _silence(0.2)
    else:
        signal = np.concatenate(segments)

    # ホラー演出: 録音らしいヒスノイズと低い唸りを背後に重ねる
    rng = np.random.default_rng(404)
    hiss = 0.05 * rng.standard_normal(len(signal))
    t = np.linspace(0, len(signal) / _SR, len(signal), endpoint=False)
    drone = 0.06 * np.sin(2 * np.pi * 50 * t)
    signal = signal + hiss + drone

    return _pcm_to_wav(signal)
