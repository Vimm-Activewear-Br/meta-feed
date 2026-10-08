import numpy as np
from PIL import Image
from scipy.ndimage import uniform_filter1d, sobel

def side_score(a, side, frac=0.05):
    """Fraction of rows where the outer side band isn't plain backdrop."""
    h, w, _ = a.shape
    b = max(8, int(w*frac))
    band = a[:, :b] if side == "l" else a[:, -b:][:, ::-1]
    g = a.mean(2); gb = g[:, :b] if side == "l" else g[:, -b:][:, ::-1]
    grad = np.hypot(sobel(gb, 0), sobel(gb, 1))
    # backdrop reference per row = outermost 3 columns, smoothed vertically
    ref = uniform_filter1d(band[:, :3].mean(1), 31, axis=0)
    diff = np.abs(band - ref[:, None, :]).max(2)
    bad = (diff > 28) | (grad > 60)
    rows = bad.mean(1) > 0.02
    # also: the outer edge itself shouldn't be wildly off the image's backdrop colour
    top = a[: h//10].reshape(-1, 3); bg = np.median(top, 0)
    edge_off = np.abs(band[:, :3].mean(1) - bg).max(1) > 60
    return float(np.mean(rows | edge_off))

def score(path):
    a = np.asarray(Image.open(path).convert("RGB").resize((360, 450))).astype(np.float32)
    return side_score(a, "l"), side_score(a, "r")

def is_clean(path, thr=0.015):
    l, r = score(path); return max(l, r) <= thr, (l, r)
