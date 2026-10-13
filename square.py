"""4:5 (portrait) photo → square, by extending the beige backdrop sideways.

Each row is extended with the colour at its outer edge. Where the body touches the side (that edge
isn't backdrop), the row uses the backdrop colour interpolated from the clean rows above/below
instead, so skin/clothes are never smeared sideways."""
import sys, numpy as np
from PIL import Image
from scipy.ndimage import uniform_filter1d, median_filter

def _edge_colors(a, side, band=12):
    cols = a[:, :band] if side == "l" else a[:, -band:]
    c = cols.mean(1)                                   # per-row edge colour
    spread = cols.std(1).max(1)                        # texture inside the band
    trend = median_filter(c, size=(151, 1), mode="nearest")
    bad = (np.abs(c - trend).max(1) > 18) | (spread > 14)
    bad = uniform_filter1d(bad.astype(float), 9) > 0   # grow the mask a little
    if bad.all(): bad[:] = False                       # nothing to anchor on: keep as is
    rows = np.arange(len(c))
    for ch in range(3):
        c[bad, ch] = np.interp(rows[bad], rows[~bad], c[~bad, ch])
    return uniform_filter1d(c, 25, axis=0), bad.mean()

def crop_square(im, anchor=None):
    """Square crop of a portrait photo. anchor="center" trims top and bottom equally (tops: keeps face and garment);
    otherwise keeps the band of rows with the most detail (garment)."""
    w, h = im.size
    if anchor == "center":
        top = (h - w) // 2
        return im.crop((0, top, w, top + w))
    g = np.asarray(im.convert("L").resize((w // 4, h // 4)), dtype=np.float32)
    energy = np.abs(np.diff(g, axis=1)).sum(1)                # horizontal detail per row
    win = w // 4
    sums = np.convolve(energy, np.ones(win), "valid")
    top = int(np.argmax(sums)) * 4
    return im.crop((0, top, w, top + w))

def pad_square(src, size=1080):
    """Fill the sides with the photo's own backdrop beige (from the top corners), never stretching the body.
    Used when the body touches the side but the top corners are backdrop (tops: keeps face + garment)."""
    im = Image.open(src).convert("RGB"); w, h = im.size
    a = np.asarray(im).astype(np.float32); S = h; pad = (S - w) // 2
    cw, ch = max(8, w // 16), max(8, h // 12)
    anchor = np.median(np.concatenate([a[:ch, :cw].reshape(-1, 3), a[:ch, -cw:].reshape(-1, 3)]), 0)
    out = np.zeros((h, S, 3), np.float32); out[:, pad:pad + w] = a
    rows = np.arange(h); k = 40
    for side in ("l", "r"):
        c = (a[:, :12] if side == "l" else a[:, -12:]).mean(1)
        ok = np.abs(c - anchor).max(1) < 28                      # this row's edge is backdrop
        col = c.copy()
        if ok.sum() > 10:
            for ch_ in range(3): col[~ok, ch_] = np.interp(rows[~ok], rows[ok], c[ok, ch_])
        else:
            col[:] = anchor
        col = uniform_filter1d(col, 81, axis=0)
        if side == "l": out[:, :pad] = col[:, None, :]
        else: out[:, pad + w:] = col[:, None, :]
        for i in range(k):                                       # soft seam, only where the edge is backdrop
            t = i / k; x = pad + i if side == "l" else pad + w - 1 - i
            out[ok, x] = out[ok, x] * t + col[ok] * (1 - t)
    out += np.random.normal(0, 1.2, out.shape)
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).resize((size, size), Image.LANCZOS)

def corners_are_backdrop(src):
    a = np.asarray(Image.open(src).convert("RGB")).astype(np.float32); h, w, _ = a.shape
    cw, ch = max(8, w // 16), max(8, h // 12)
    return all(a[:ch, sl].std((0, 1)).max() < 12 for sl in (slice(0, cw), slice(w - cw, w)))

def squarify(src, dst, size=1080, anchor=None):
    """Clean side margins → extend the backdrop. Body on the side margin → square crop instead."""
    from edges import score
    im = Image.open(src).convert("RGB"); w, h = im.size
    if max(score(src)) > 0.02 and anchor == "pad" and corners_are_backdrop(src):
        pad_square(src, size).save(dst, quality=92)
        return
    if max(score(src)) > 0.02:
        crop_square(im, "center" if anchor == "pad" else anchor).resize((size, size), Image.LANCZOS).save(dst, quality=92)
        return

    a = np.asarray(im).astype(np.float32)
    S = max(w, h); pad = (S - w) // 2
    out = np.zeros((h, S, 3), np.float32); out[:, pad:pad + w] = a
    L, _ = _edge_colors(a, "l"); R, _ = _edge_colors(a, "r")
    out[:, :pad] = L[:, None, :]; out[:, pad + w:] = R[:, None, :]
    k = 40                                             # soft seam
    for i in range(k):
        t = i / k
        out[:, pad + i] = out[:, pad + i] * t + L * (1 - t)
        out[:, pad + w - 1 - i] = out[:, pad + w - 1 - i] * t + R * (1 - t)
    out += np.random.normal(0, 1.2, out.shape)         # light grain, no banding
    img = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
    img.resize((size, size), Image.LANCZOS).save(dst, quality=92)

if __name__ == "__main__":
    squarify(sys.argv[1], sys.argv[2])
