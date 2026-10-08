import sys, numpy as np
from PIL import Image, ImageFilter
def squarify(src, dst, size=1080, band=12):
    im = Image.open(src).convert("RGB"); w,h = im.size
    a = np.asarray(im).astype(np.float32)
    S = max(w,h); pad = (S-w)//2
    out = np.zeros((h,S,3),np.float32)
    out[:,pad:pad+w] = a
    # per-row backdrop color from the outer edge band, smoothed vertically
    L = a[:, :band].mean(1); R = a[:, -band:].mean(1)
    from scipy.ndimage import uniform_filter1d
    L = uniform_filter1d(L, 25, axis=0); R = uniform_filter1d(R, 25, axis=0)
    out[:, :pad] = L[:,None,:]; out[:, pad+w:] = R[:,None,:]
    # soft blend across the seam so there's no visible line
    k = 40
    for side in ("l","r"):
        for i in range(k):
            t = i/k
            if side=="l":
                x = pad+i; out[:,x] = out[:,x]*t + L*(1-t)
            else:
                x = pad+w-1-i; out[:,x] = out[:,x]*t + R*(1-t)
    out += np.random.normal(0,1.2,out.shape)  # tiny grain to avoid banding
    img = Image.fromarray(np.clip(out,0,255).astype(np.uint8))
    if h < S: img = img.resize((S,S))  # (not expected: portrait inputs)
    img.resize((size,size), Image.LANCZOS).save(dst, quality=92)
if __name__=="__main__": squarify(sys.argv[1], sys.argv[2])
