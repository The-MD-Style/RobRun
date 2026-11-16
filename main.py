"""RobRun: patruleaza camera, gaseste mesele cu iarba gata si le recolteaza (hold E la 'СБОР УРОЖАЯ')."""
import json
import random
import sys
import time
from collections import deque

import config
from control import OPPOSITE, Controller, Stop
from vision import Vision


class GiveUp(Exception):
    pass


def load_route():
    if not config.ROUTE_FILE.exists():
        sys.exit("Nu exista route.json. Inregistreaz-o cu: python record_route.py")
    steps = json.loads(config.ROUTE_FILE.read_text())
    if not steps:
        sys.exit("route.json e gol. Inregistreaza din nou: python record_route.py")
    return steps


def reversed_route(steps):
    out = []
    for s in reversed(steps):
        s = dict(s)
        if s["t"] == "walk":
            s["keys"] = [OPPOSITE.get(k, k) for k in s["keys"]]
        elif s["t"] == "look":
            s["px"] = -s["px"]
        out.append(s)
    return out


class Bot:
    def __init__(self):
        self.v = Vision()
        missing = self.v.missing()
        if missing:
            sys.exit("Lipsesc template-urile: " + ", ".join(missing) +
                     "\nFa-le cu: python calibrate.py grab <nume>")
        self.c = Controller()
        self.route = load_route()
        self.queue = deque()
        self.forward = True
        self.ignore_until = 0.0
        self.stuck_fails = 0
        self.harvested = 0

    # ---------- bucla principala ----------
    def run(self):
        print(f"Start in {config.START_DELAY}s. Da click in fereastra jocului. "
              f"Oprire: {config.STOP_HOTKEY} sau mouse in colt.")
        try:
            self.c.sleep(config.START_DELAY)
            while True:
                if not self.queue:
                    self._refill()
                ev, rest = self._exec(self.queue.popleft())
                if rest:
                    self.queue.appendleft(rest)
                if ev:
                    self._detour(ev)
        except Stop:
            print("Oprit de utilizator.")
        except GiveUp as e:
            print(f"ABANDON: {e}")
            self.c.alert()
        finally:
            self.c.release_all()
            print(f"Recoltate: {self.harvested}")

    def _refill(self):
        if config.ROUTE_MODE == "pingpong" and not self.forward:
            self.queue.extend(reversed_route(self.route))
        else:
            self.queue.extend(self.route)
        self.forward = not self.forward
        if config.LAP_PAUSE:
            self.c.sleep(config.LAP_PAUSE)

    def _event(self, gray):
        if time.time() < self.ignore_until:
            return None
        if self.v.prompt_visible(gray):
            return "prompt"
        if self.v.find_icons(gray):
            return "icon"
        return None

    # ---------- pasii rutei ----------
    def _exec(self, step):
        """Returneaza (eveniment, pasul ramas de facut)."""
        return {"walk": self._walk, "look": self._look, "wait": self._wait}[step["t"]](step)

    def _walk(self, step):
        keys, secs = step["keys"], step["secs"]
        self.c.down(keys)
        start = time.time()
        prev = self.v.grab()
        bad = 0
        try:
            while True:
                left = secs - (time.time() - start)
                if left <= 0:
                    self.stuck_fails = 0
                    return None, None
                self.c.sleep(min(config.CHUNK, left))
                cur = self.v.grab()
                ev = self._event(cur)
                if ev:
                    rest = secs - (time.time() - start)
                    return ev, ({**step, "secs": round(rest, 2)} if rest > 0.3 else None)
                if self.v.is_blank(cur) or self.v.motion(prev, cur) < config.STUCK_DIFF:
                    bad += 1
                else:
                    bad = 0
                if bad >= config.STUCK_CHUNKS:
                    self.c.up(keys)
                    self._unstick(keys)
                    return None, None
                prev = cur
        finally:
            self.c.up(keys)

    def _look(self, step):
        px = step["px"]
        sign = 1 if px > 0 else -1
        done = 0
        while done < abs(px):
            part = min(config.LOOK_CHUNK_PX, abs(px) - done)
            self.c.turn(sign * part)
            done += part
            self.c.sleep(0.15)
            ev = self._event(self.v.grab())
            if ev:
                rest = abs(px) - done
                return ev, ({"t": "look", "px": sign * rest} if rest > 10 else None)
        return None, None

    def _wait(self, step):
        end = time.time() + step["secs"]
        while time.time() < end:
            self.c.sleep(0.2)
            ev = self._event(self.v.grab())
            if ev:
                return ev, None
        return None, None

    # ---------- ocol spre masa + recoltare ----------
    def _detour(self, ev):
        self.c.trace = []
        ok = self._harvest() if ev == "prompt" else self._approach()
        if not ok:
            self.ignore_until = time.time() + config.IGNORE_SECONDS
        self.c.undo_trace()    # ne intoarcem pe ruta

    def _approach(self):
        t0 = time.time()
        lost = stuck = 0
        while time.time() - t0 < config.APPROACH_TIMEOUT:
            self.c.check()
            f = self.v.grab()
            if self.v.prompt_visible(f):
                return self._harvest()
            icons = self.v.find_icons(f)
            if not icons:
                lost += 1
                if lost > config.ICON_LOST_MAX:
                    return False
                self.c.hold(["w"], config.FORWARD_PULSE)   # iconita poate iesi din cadru cand esti aproape
                continue
            lost = 0
            hit = min(icons, key=lambda h: abs(h.nx))
            if abs(hit.nx) > config.DEADZONE:
                self._steer(hit.nx)
                continue
            self.c.hold(["w"], config.FORWARD_PULSE)
            if self.v.motion(f, self.v.grab()) < config.STUCK_DIFF:
                stuck += 1
                if stuck >= 3:
                    return False
                self._unstick(["w"])
            else:
                stuck = 0
        return False

    def _steer(self, nx):
        if config.CAMERA == "none":
            self.c.hold(["d" if nx > 0 else "a"], config.STRAFE_PULSE)
        else:
            self.c.turn(nx * config.CAMERA_PX_PER_WIDTH)

    def _harvest(self):
        for _ in range(config.HARVEST_RETRIES + 1):
            if not self.v.prompt_visible(self.v.grab()):
                return False
            self.c.sleep(config.SETTLE_WAIT)
            print(f"СБОР УРОЖАЯ -> hold {config.HARVEST_KEY.upper()} {config.HOLD_SECONDS}s")
            self.c.hold([config.HARVEST_KEY], config.HOLD_SECONDS + config.HOLD_MARGIN, trace=False)
            self.c.sleep(config.ACTION_WAIT)               # lasa actiunea sa se termine
            end = time.time() + config.ACTION_TIMEOUT      # apoi asteapta sa dispara textul
            while time.time() < end:
                if not self.v.prompt_visible(self.v.grab()):
                    self.harvested += 1
                    self.stuck_fails = 0
                    print(f"Recoltat ({self.harvested})")
                    return True
                self.c.sleep(0.2)
        return False

    # ---------- anti-blocaj ----------
    def _unstick(self, keys):
        self.stuck_fails += 1
        path = self.v.save_debug(f"stuck{self.stuck_fails}")
        print(f"Blocat ({self.stuck_fails}/{config.MAX_STUCK}), screenshot: {path}")
        if self.stuck_fails > config.MAX_STUCK:
            raise GiveUp("blocat de prea multe ori la rand")
        d = config.UNSTICK_BASE * self.stuck_fails
        self.c.hold([OPPOSITE.get(k, k) for k in keys], d)     # pas inapoi
        self.c.hold([random.choice("ad")], d)                  # pas lateral
        if config.JUMP_KEY:
            self.c.tap(config.JUMP_KEY)


if __name__ == "__main__":
    Bot().run()
