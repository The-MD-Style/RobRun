"""Captura ecranului si detectia cu template matching."""
import time
from dataclasses import dataclass

import cv2
import mss
import numpy as np

import config


@dataclass
class Hit:
    nx: float      # deplasare orizontala fata de centrul ecranului, -0.5..0.5
    ny: float
    score: float
    size: float    # inaltimea iconitei ca fractie din inaltimea cadrului


def match_all(gray, templ, thr):
    th, tw = templ.shape
    if th > gray.shape[0] or tw > gray.shape[1] or templ.std() < 1:
        return []
    res = cv2.matchTemplate(gray, templ, cv2.TM_CCOEFF_NORMED)
    ys, xs = np.where(res >= thr)
    return [(x + tw / 2, y + th / 2, float(res[y, x]), tw, th) for y, x in zip(ys, xs)]


def dedupe(raw):
    """Pastreaza cel mai bun hit din fiecare zona."""
    kept = []
    for x, y, s, w, h in sorted(raw, key=lambda r: -r[2]):
        if all(abs(x - kx) > max(w, kw) * 0.6 or abs(y - ky) > max(h, kh) * 0.6
               for kx, ky, _, kw, kh in kept):
            kept.append((x, y, s, w, h))
    return kept


class Vision:
    def __init__(self):
        self.sct = mss.mss()
        self.region = config.GAME_REGION or self.sct.monitors[config.MONITOR]
        self.icon_scaled = []
        self.prompt = None
        self._load_templates()

    def _load_templates(self):
        k = config.SCAN_SCALE
        if config.ICON_READY.exists():
            base = cv2.imread(str(config.ICON_READY), cv2.IMREAD_GRAYSCALE)
            for s in config.ICON_SCALES:
                t = cv2.resize(base, None, fx=k * s, fy=k * s, interpolation=cv2.INTER_AREA)
                if min(t.shape) >= 8:
                    self.icon_scaled.append(t)
        if config.PROMPT_HARVEST.exists():
            base = cv2.imread(str(config.PROMPT_HARVEST), cv2.IMREAD_GRAYSCALE)
            self.prompt = cv2.resize(base, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)

    def missing(self):
        out = []
        if not self.icon_scaled:
            out.append("icon_ready")
        if self.prompt is None:
            out.append("prompt_harvest")
        return out

    # --- captura ---
    def grab_bgr(self):
        return np.array(self.sct.grab(self.region))[:, :, :3]

    def grab(self):
        gray = cv2.cvtColor(np.array(self.sct.grab(self.region)), cv2.COLOR_BGRA2GRAY)
        if config.SCAN_SCALE != 1:
            gray = cv2.resize(gray, None, fx=config.SCAN_SCALE, fy=config.SCAN_SCALE,
                              interpolation=cv2.INTER_AREA)
        return gray

    def save_debug(self, tag):
        config.LOGS.mkdir(exist_ok=True)
        path = config.LOGS / f"{int(time.time())}_{tag}.png"
        cv2.imwrite(str(path), self.grab_bgr())
        return path

    # --- detectie ---
    def find_icons(self, gray):
        H, W = gray.shape
        raw = []
        for t in self.icon_scaled:
            raw += match_all(gray, t, config.ICON_THRESHOLD)
        return [Hit((x - W / 2) / W, (y - H / 2) / H, s, h / H) for x, y, s, w, h in dedupe(raw)]

    def prompt_score(self, gray):
        if self.prompt is None:
            return 0.0
        H, W = gray.shape
        if config.PROMPT_REGION:
            l, t, r, b = config.PROMPT_REGION
            gray = gray[int(H * t):int(H * b), int(W * l):int(W * r)]
        if self.prompt.shape[0] > gray.shape[0] or self.prompt.shape[1] > gray.shape[1]:
            return 0.0
        res = cv2.matchTemplate(gray, self.prompt, cv2.TM_CCOEFF_NORMED)
        best = float(res.max())
        return best if np.isfinite(best) else 0.0

    def prompt_visible(self, gray):
        return self.prompt_score(gray) >= config.PROMPT_THRESHOLD

    # --- anti-blocaj ---
    def motion(self, a, b):
        """Diferenta medie intre cadre, fara banda centrala (personajul) si fara marginile sus/jos (HUD)."""
        H, W = a.shape
        t, bt = int(H * 0.1), int(H * 0.9)
        lo, hi = int(W * (0.5 - config.CENTER_MASK / 2)), int(W * (0.5 + config.CENTER_MASK / 2))
        d = cv2.absdiff(a[t:bt], b[t:bt])
        return float(np.concatenate([d[:, :lo].ravel(), d[:, hi:].ravel()]).mean())

    def is_blank(self, gray):
        return float(gray.std()) < config.BLANK_STD
