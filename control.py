"""Tastatura, camera (mouse) si oprirea de urgenta. Merge pe macOS si Windows."""
import subprocess
import sys
import threading
import time

import pyautogui
from pynput import keyboard

import config

pyautogui.PAUSE = 0
pyautogui.FAILSAFE = True

IS_MAC = sys.platform == "darwin"
IS_WIN = sys.platform.startswith("win")
OPPOSITE = {"w": "s", "s": "w", "a": "d", "d": "a"}


class Stop(Exception):
    pass


class Controller:
    def __init__(self):
        self.stop = threading.Event()
        self.trace = None        # lista cu miscarile dintr-un ocol, ca sa le putem anula
        self._held = set()
        hk = keyboard.GlobalHotKeys({config.STOP_HOTKEY: self.stop.set})
        hk.daemon = True
        hk.start()

    def check(self):
        if self.stop.is_set():
            raise Stop()

    def sleep(self, secs):
        end = time.time() + secs
        while True:
            self.check()
            left = end - time.time()
            if left <= 0:
                return
            time.sleep(min(0.05, left))

    # --- taste ---
    def down(self, keys):
        for k in keys:
            if k not in self._held:
                pyautogui.keyDown(k)
                self._held.add(k)

    def up(self, keys):
        for k in keys:
            if k in self._held:
                pyautogui.keyUp(k)
                self._held.discard(k)

    def release_all(self):
        self.up(list(self._held))

    def tap(self, key):
        pyautogui.press(key)

    def hold(self, keys, secs, trace=True):
        self.down(keys)
        try:
            self.sleep(secs)
        finally:
            self.up(keys)
        if trace and self.trace is not None:
            self.trace.append(("keys", tuple(keys), secs))

    # --- camera ---
    def turn(self, px, trace=True):
        """px > 0 = priveste la dreapta."""
        if config.CAMERA == "arrows":
            self.hold(["right" if px > 0 else "left"], abs(px) / config.ARROW_PX_PER_SEC, trace=False)
        elif config.CAMERA == "mouse":
            self._mouse_turn(px)
        else:
            return
        if trace and self.trace is not None:
            self.trace.append(("turn", px, 0))

    def _mouse_turn(self, px):
        steps = max(1, int(abs(px) / 15))
        per = px / steps
        if IS_MAC:
            self._mouse_turn_mac(steps, per)
        elif IS_WIN:
            self._mouse_turn_win(steps, per)
        else:
            for _ in range(steps):
                self.check()
                pyautogui.moveRel(int(per), 0)
                time.sleep(0.01)

    def _mouse_turn_mac(self, steps, per):
        from Quartz import (CGEventCreate, CGEventCreateMouseEvent, CGEventGetLocation,
                            CGEventPost, CGEventSetIntegerValueField, kCGEventMouseMoved,
                            kCGEventRightMouseDown, kCGEventRightMouseDragged,
                            kCGEventRightMouseUp, kCGHIDEventTap, kCGMouseButtonLeft,
                            kCGMouseButtonRight, kCGMouseEventDeltaX)
        right = config.MOUSE_RIGHT_BUTTON
        pos = CGEventGetLocation(CGEventCreate(None))
        x, y = pos.x, pos.y
        if right:
            CGEventPost(kCGHIDEventTap, CGEventCreateMouseEvent(None, kCGEventRightMouseDown, (x, y), kCGMouseButtonRight))
        try:
            for _ in range(steps):
                self.check()
                x += per
                ev = CGEventCreateMouseEvent(
                    None, kCGEventRightMouseDragged if right else kCGEventMouseMoved, (x, y),
                    kCGMouseButtonRight if right else kCGMouseButtonLeft)
                CGEventSetIntegerValueField(ev, kCGMouseEventDeltaX, int(per))
                CGEventPost(kCGHIDEventTap, ev)
                time.sleep(0.01)
        finally:
            if right:
                CGEventPost(kCGHIDEventTap, CGEventCreateMouseEvent(None, kCGEventRightMouseUp, (x, y), kCGMouseButtonRight))

    def _mouse_turn_win(self, steps, per):
        import ctypes
        user32 = ctypes.windll.user32
        MOVE, RIGHT_DOWN, RIGHT_UP = 0x0001, 0x0008, 0x0010
        right = config.MOUSE_RIGHT_BUTTON
        if right:
            user32.mouse_event(RIGHT_DOWN, 0, 0, 0, 0)
        try:
            for _ in range(steps):
                self.check()
                user32.mouse_event(MOVE, int(per), 0, 0, 0)    # miscare relativa, merge si in jocuri 3D
                time.sleep(0.01)
        finally:
            if right:
                user32.mouse_event(RIGHT_UP, 0, 0, 0, 0)

    # --- ocol: inregistrat si apoi anulat ca sa revenim pe ruta ---
    def undo_trace(self):
        trace, self.trace = self.trace or [], None
        for kind, arg, secs in reversed(trace):
            if kind == "keys":
                self.hold([OPPOSITE.get(k, k) for k in arg], secs, trace=False)
            else:
                self.turn(-arg, trace=False)

    def alert(self):
        if IS_MAC:
            subprocess.Popen(["afplay", "/System/Library/Sounds/Glass.aiff"])
        elif IS_WIN:
            import winsound
            winsound.MessageBeep()
        else:
            print("\a")
