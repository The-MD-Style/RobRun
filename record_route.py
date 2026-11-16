"""Inregistreaza ruta: mergi tu cu WASD prin camera, scriptul salveaza ce taste ai tinut si cat timp.

Pornesti, ai START_DELAY secunde sa treci in joc, mergi pe ruta, apoi apesi STOP_HOTKEY.
Camera NU se inregistreaza (daca ai nevoie de rotiri, adauga manual {"t":"look","px":300} in route.json).
"""
import json
import time

from pynput import keyboard

import config

WASD = {"w", "a", "s", "d"}
steps, held, since = [], set(), None
done = False


def close_segment(now):
    dur = now - since
    if held:
        if dur >= 0.08:
            steps.append({"t": "walk", "keys": sorted(held), "secs": round(dur, 2)})
    elif dur >= 0.4 and steps:
        steps.append({"t": "wait", "secs": round(dur, 2)})


def change(key, pressed):
    global since
    name = getattr(key, "char", None)
    if name not in WASD or (name in held) == pressed:
        return
    now = time.time()
    if since is not None:
        close_segment(now)
    held.add(name) if pressed else held.discard(name)
    since = now


def finish():
    global done
    if since is not None:
        close_segment(time.time())
    done = True


print(f"Pornesc in {config.START_DELAY}s. Treci in joc si mergi pe ruta. Termini cu {config.STOP_HOTKEY}.")
time.sleep(config.START_DELAY)
print("Inregistrez...")
since = time.time()
with keyboard.Listener(on_press=lambda k: change(k, True), on_release=lambda k: change(k, False)), \
        keyboard.GlobalHotKeys({config.STOP_HOTKEY: finish}):
    while not done:
        time.sleep(0.1)

config.ROUTE_FILE.write_text(json.dumps(steps, indent=1))
print(f"Salvat {len(steps)} pasi in {config.ROUTE_FILE}")
