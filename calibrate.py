"""Unelte de calibrare.

  python calibrate.py grab icon_ready       # decupezi iconita de deasupra mesei
  python calibrate.py grab prompt_harvest   # decupezi textul "СБОР УРОЖАЯ"
  python calibrate.py test                  # arata live ce vede scriptul
"""
import sys
import time

import cv2

import config
from vision import Vision


def grab(name, delay=5):
    v = Vision()
    print(f"Pune jocul in starea potrivita. Screenshot in {delay}s...")
    time.sleep(delay)
    img = v.grab_bgr()
    k = min(1.0, 1400 / img.shape[1], 850 / img.shape[0])
    disp = cv2.resize(img, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
    x, y, w, h = cv2.selectROI("Trage un dreptunghi peste obiect, ENTER = ok, C = anuleaza",
                               disp, showCrosshair=False)
    cv2.destroyAllWindows()
    if w == 0 or h == 0:
        sys.exit("Anulat.")
    x, y, w, h = (int(round(n / k)) for n in (x, y, w, h))
    config.ASSETS.mkdir(exist_ok=True)
    out = config.ASSETS / f"{name}.png"
    cv2.imwrite(str(out), img[y:y + h, x:x + w])
    print(f"Salvat: {out} ({w}x{h}px)")
    if name == "prompt_harvest":
        # textul apare mereu in aceeasi zona: o salvam (fractii + margine) ca sa cautam doar acolo
        H, W = img.shape[:2]
        pad = 0.08
        region = (max(0, x / W - pad), max(0, y / H - pad),
                  min(1, (x + w) / W + pad), min(1, (y + h) / H + pad))
        value = ",".join(f"{r:.3f}" for r in region)
        config.set_env("PROMPT_REGION", value)
        print(f"PROMPT_REGION={value} salvat in .env (cauta textul doar in zona asta)")


def test():
    v = Vision()
    print("Lipsesc:", v.missing() or "nimic", "| Ctrl+C = iesire")
    prev = v.grab()
    while True:
        cur = v.grab()
        icons = [(round(h.nx, 2), round(h.score, 2)) for h in v.find_icons(cur)]
        print(f"iconite(nx,scor)={icons}  prompt={v.prompt_score(cur):.2f}  "
              f"miscare={v.motion(prev, cur):.2f}  blank={v.is_blank(cur)}      ", end="\r")
        prev = cur
        time.sleep(0.3)


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "grab":
        grab(sys.argv[2])
    elif len(sys.argv) >= 2 and sys.argv[1] == "test":
        test()
    else:
        print(__doc__)
