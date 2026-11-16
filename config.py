"""Setarile RobRun. Valorile se schimba in .env (vezi .env.example), nu aici."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
ENV_FILE = ROOT / ".env"
load_dotenv(ENV_FILE)


def _f(name, default):
    return float(os.getenv(name) or default)


def _i(name, default):
    return int(float(os.getenv(name) or default))


def _b(name, default):
    return (os.getenv(name) or str(default)).strip().lower() in ("1", "true", "yes", "da")


def _s(name, default):
    v = os.getenv(name)
    return default if v is None else v.strip()


def _nums(name, default=""):
    raw = _s(name, default)
    return tuple(float(x) for x in raw.split(",") if x.strip())


def set_env(key, value):
    """Scrie/actualizeaza o cheie in .env (il creeaza din .env.example daca lipseste)."""
    if not ENV_FILE.exists():
        example = ROOT / ".env.example"
        ENV_FILE.write_text(example.read_text() if example.exists() else "")
    lines, done = ENV_FILE.read_text().splitlines(), False
    for i, line in enumerate(lines):
        if line.split("=", 1)[0].strip() == key:
            lines[i], done = f"{key}={value}", True
    if not done:
        lines.append(f"{key}={value}")
    ENV_FILE.write_text("\n".join(lines) + "\n")


ASSETS = ROOT / "assets"
LOGS = ROOT / "logs"
ROUTE_FILE = ROOT / "route.json"
ICON_READY = ASSETS / "icon_ready.png"          # iconita de deasupra mesei cand iarba e gata
PROMPT_HARVEST = ASSETS / "prompt_harvest.png"  # textul "СБОР УРОЖАЯ"

# --- Recoltare ---
HARVEST_KEY = _s("HARVEST_KEY", "e")
HOLD_SECONDS = _f("HOLD_SECONDS", 2.0)
HOLD_MARGIN = _f("HOLD_MARGIN", 0.15)
SETTLE_WAIT = _f("SETTLE_WAIT", 0.2)
ACTION_WAIT = _f("ACTION_WAIT", 1.0)
ACTION_TIMEOUT = _f("ACTION_TIMEOUT", 3.0)
HARVEST_RETRIES = _i("HARVEST_RETRIES", 2)

# --- Detectie ---
_region = _nums("PROMPT_REGION")
PROMPT_REGION = _region if len(_region) == 4 else None     # (stanga, sus, dreapta, jos) fractii
_game = _nums("GAME_REGION")
GAME_REGION = dict(zip(("left", "top", "width", "height"), map(int, _game))) if len(_game) == 4 else None
MONITOR = _i("MONITOR", 1)
SCAN_SCALE = _f("SCAN_SCALE", 0.5)
ICON_THRESHOLD = _f("ICON_THRESHOLD", 0.80)
ICON_SCALES = _nums("ICON_SCALES", "0.7,0.85,1.0,1.2,1.4,1.7")
PROMPT_THRESHOLD = _f("PROMPT_THRESHOLD", 0.80)

# --- Camera ---
CAMERA = _s("CAMERA", "mouse")
MOUSE_RIGHT_BUTTON = _b("MOUSE_RIGHT_BUTTON", False)
CAMERA_PX_PER_WIDTH = _f("CAMERA_PX_PER_WIDTH", 600)
LOOK_CHUNK_PX = _i("LOOK_CHUNK_PX", 60)
ARROW_PX_PER_SEC = _f("ARROW_PX_PER_SEC", 300)

# --- Patrula ---
START_DELAY = _f("START_DELAY", 5)
CHUNK = _f("CHUNK", 0.3)
ROUTE_MODE = _s("ROUTE_MODE", "pingpong")
LAP_PAUSE = _f("LAP_PAUSE", 0)

# --- Apropierea de masa ---
DEADZONE = _f("DEADZONE", 0.04)
STRAFE_PULSE = _f("STRAFE_PULSE", 0.12)
FORWARD_PULSE = _f("FORWARD_PULSE", 0.25)
APPROACH_TIMEOUT = _f("APPROACH_TIMEOUT", 20)
ICON_LOST_MAX = _i("ICON_LOST_MAX", 6)
IGNORE_SECONDS = _f("IGNORE_SECONDS", 15)

# --- Anti-blocaj ---
STUCK_DIFF = _f("STUCK_DIFF", 1.5)
STUCK_CHUNKS = _i("STUCK_CHUNKS", 2)
BLANK_STD = _f("BLANK_STD", 4.0)
CENTER_MASK = _f("CENTER_MASK", 0.3)
JUMP_KEY = _s("JUMP_KEY", "space") or None
MAX_STUCK = _i("MAX_STUCK", 4)
UNSTICK_BASE = _f("UNSTICK_BASE", 0.4)

# --- Oprire de urgenta (plus: mouse intr-un colt = pyautogui failsafe) ---
STOP_HOTKEY = _s("STOP_HOTKEY", "<ctrl>+<shift>+x")
