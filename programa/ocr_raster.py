"""OCR por mosaico para paginas escaneadas (sin geometria vectorial). Lento: solo se usa si hace falta."""
import numpy as np, cv2, pypdfium2 as pdfium

# pdfium no admite uso simultaneo desde varios hilos: el candado es uno solo (planocables.base.pdfium_lock) y
# 'from ocr_raster import PDFIUM_LOCK' (web, eplan, topo, bornes.motor) sigue dando ese mismo objeto
from planocables.base.pdfium_lock import PDFIUM_LOCK
SCALE, TILE, OVER, MIN_SCORE = 3.0, 1800, 300, 0.75
_engine = None


def engine():
    global _engine
    if _engine is None:
        from rapidocr import RapidOCR
        _engine = RapidOCR(params={'Global.log_level': 'error'})
    return _engine


def _tiles(img):
    H, W = img.shape[:2]; out = []
    for y in range(0, H, TILE - OVER):
        for x in range(0, W, TILE - OVER):
            t = img[y:y + TILE, x:x + TILE]
            if t.min() > 200:
                continue
            r = engine()(t)
            if r.boxes is None:
                continue
            for b, txt, s in zip(r.boxes, r.txts, r.scores):
                if s >= MIN_SCORE and txt.strip():
                    xs, ys = b[:, 0] + x, b[:, 1] + y
                    out.append((xs.min(), ys.min(), xs.max(), ys.max(), txt, float(s)))
    return out


def page_items(pdf_path, pi):
    """[(texto, bbox_pdf, angulo)] para superponer como texto invisible"""
    with PDFIUM_LOCK:
        doc = pdfium.PdfDocument(pdf_path)
        try:
            page = doc[pi]
            pw, ph = page.get_size()
            img = np.array(page.render(scale=SCALE, grayscale=True).to_pil())
            page.close()
        finally:
            doc.close()
    H = img.shape[0]
    items = []
    for x0, y0, x1, y1, t, s in _tiles(img):
        items.append([x0, y0, x1, y1, t, s, 0])
    rot = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    for x0, y0, x1, y1, t, s in _tiles(rot):
        if len(t) >= 2 and (x1 - x0) >= (y1 - y0) * 0.6:
            items.append([y0, H - 1 - x1, y1, H - 1 - x0, t, s, 90])
    items.sort(key=lambda i: (-len(i[4]), -i[5])); kept = []
    for it in items:
        if all(_ov(it, k) < 0.3 for k in kept):
            kept.append(it)
    return [(t, (x0 / SCALE, ph - y1 / SCALE, x1 / SCALE, ph - y0 / SCALE), ang) for x0, y0, x1, y1, t, s, ang in kept]


def _ov(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    sm = min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]))
    return ix * iy / sm if sm else 0
