"""PIL によるパズル画像生成 (QR風マトリクス / 隠し文字画像)。"""

from PIL import Image, ImageDraw, ImageFont
import numpy as np

GREEN = (57, 255, 20)
DARK = (5, 8, 5)


def _font(size: int):
    for name in ("consola.ttf", "cour.ttf", "arial.ttf", "DejaVuSansMono.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


# ---- QRコード復元 -------------------------------------------------

def finder_pattern():
    """7x7 のQRファインダーパターン (左上)。"""
    p = np.zeros((7, 7), dtype=int)
    p[0, :] = 1
    p[6, :] = 1
    p[:, 0] = 1
    p[:, 6] = 1
    p[2:5, 2:5] = 1
    return p


def matrix_to_image(mat: np.ndarray, cell=22, missing_mask=None):
    """0/1 行列を画像化。missing_mask=True の位置は '?' で表示。"""
    n = mat.shape[0]
    img = Image.new("RGB", (n * cell, n * cell), DARK)
    d = ImageDraw.Draw(img)
    f = _font(cell - 6)
    for r in range(n):
        for c in range(n):
            x0, y0 = c * cell, r * cell
            if missing_mask is not None and missing_mask[r, c]:
                d.rectangle([x0, y0, x0 + cell - 1, y0 + cell - 1],
                            fill=(40, 0, 0), outline=(120, 0, 30))
                d.text((x0 + cell // 4, y0 + 1), "?", fill=(255, 0, 60), font=f)
            else:
                color = GREEN if mat[r, c] else DARK
                d.rectangle([x0, y0, x0 + cell - 1, y0 + cell - 1], fill=color)
    return img


def qr_candidate(pattern: np.ndarray, cell=18):
    """候補ファインダーパターンを単体画像化。"""
    return matrix_to_image(pattern, cell=cell)


def make_qr_puzzle():
    """欠損QRと、正解/不正解の候補パターンを返す。"""
    correct = finder_pattern()
    # 不正解候補: 中央を変える / 反転 / ずらす
    wrong1 = correct.copy(); wrong1[2:5, 2:5] = 0
    wrong2 = 1 - correct
    wrong3 = correct.copy(); wrong3[3, :] = 0
    return correct, [correct, wrong1, wrong2, wrong3]


# ---- 画像探索 (隠し文字) ------------------------------------------

def make_hidden_image(secret: str, w=520, h=300, seed=404):
    """ノイズの中に薄く secret を埋め込んだ画像を生成。"""
    rng = np.random.default_rng(seed)
    noise = rng.integers(0, 45, size=(h, w), dtype=np.uint8)
    base = np.zeros((h, w, 3), dtype=np.uint8)
    base[..., 1] = noise  # 緑ノイズ

    img = Image.fromarray(base, "RGB")
    d = ImageDraw.Draw(img)

    # ダミー文字を散りばめる
    f_small = _font(20)
    chars = "0123456789ABCDEFNULL#@%"
    for _ in range(120):
        x = int(rng.integers(0, w - 10))
        y = int(rng.integers(0, h - 10))
        ch = chars[int(rng.integers(0, len(chars)))]
        g = int(rng.integers(20, 60))
        d.text((x, y), ch, fill=(0, g, 0), font=f_small)

    # 暗がりに浮かぶ「視線」: かすかな眼を散りばめる
    for _ in range(5):
        cx = int(rng.integers(40, w - 40))
        cy = int(rng.integers(30, h - 30))
        ew, eh = 16, 8
        g = int(rng.integers(28, 50))
        # 白目
        d.ellipse([cx - ew, cy - eh, cx + ew, cy + eh], outline=(0, g, 0))
        # 瞳
        d.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], fill=(0, g + 20, 0))

    # 隠し文字: わずかに明るい緑で配置
    f_big = _font(54)
    bbox = d.textbbox((0, 0), secret, font=f_big)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text(((w - tw) // 2, (h - th) // 2 - 8), secret,
           fill=(0, 92, 0), font=f_big)
    return img
