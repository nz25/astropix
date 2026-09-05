"""Serve `protocols/` to the iPad, and let the bench drive the grey patch.

`grey-patch.html` is usable on its own -- open it, set a level by hand, capture.
This adds one thing: a level the *capture side* can set, so an attenuation scout
can walk grey level 255 -> 16 without anyone touching the panel between frames.
Measuring a level-vs-flux curve by hand is a dozen round trips to the iPad, and
L07's claim that grey level is exhausted below ~25% of full scale is exactly the
kind of thing that never gets rechecked when rechecking it is tedious.

    GET /level            -> {"level": 128, "seq": 3, "probe": false, "refresh": {...}}
    GET /set?level=128    -> sets it, bumps seq
    GET /set?level=free   -> hands the panel back to whoever is holding the iPad
    GET /set?probe=1      -> asks the page to animate its corner dot, bumps seq
    GET /refresh?ms=...   -> the page reporting how fast it is being served

`/refresh` is the page talking back, and it is the only endpoint that carries a
measurement.  It is still not a measurement of the *light*: `requestAnimationFrame`
reports the rate the compositor hands the page, and a display with adaptive
refresh serves a still page fewer frames than the panel drives.  That is what
`probe` separates - animate four pixels and see whether the rate rises.  What
the backlight actually does is measured with the camera, never here.

The page polls `/level` and applies a change only when `seq` moves, so a manual
tap is not fought over on the next poll.  `level: null` means the server is not
driving and the page is on its own.

Run it with the *base* interpreter rather than the venv one: on this machine the
venv's python.exe is a separate binary with no inbound firewall rule, and the
iPad is on the Public network profile.

    C:/Users/denis/AppData/Local/Python/pythoncore-3.14-64/python.exe \
        protocols/patch-server.py

Nothing here is a measurement and nothing here is physics: it moves one integer
from the notebook to the panel.  The flux that integer produces is measured by
the camera, per `light-source.md` item 3, and never predicted from the level.
"""

import functools
import http.server
import json
import pathlib
import socketserver
import sys
import time
import urllib.parse

PORT = 8765
ROOT = pathlib.Path(__file__).resolve().parent

STATE = {"level": None, "seq": 0, "probe": False, "refresh": None}


class Handler(http.server.SimpleHTTPRequestHandler):
    def _json(self, payload, code=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)

        if url.path == "/level":
            return self._json(STATE)

        if url.path == "/refresh":
            q = urllib.parse.parse_qs(url.query)
            try:
                STATE["refresh"] = {
                    "period_ms": float(q["ms"][0]),
                    "p05_ms": float(q["lo"][0]),
                    "p95_ms": float(q["hi"][0]),
                    "intervals": int(q["n"][0]),
                    "animated": q.get("animated", ["0"])[0] == "1",
                    "at": time.time(),
                }
            except (KeyError, ValueError, IndexError) as exc:
                return self._json({"error": f"malformed refresh report: {exc}"}, 400)
            return self._json({"ok": True})

        if url.path == "/set":
            q = urllib.parse.parse_qs(url.query)
            if "probe" in q:
                STATE["probe"] = q["probe"][0] not in ("0", "false", "off")
                STATE["seq"] += 1
                return self._json(STATE)
            raw = (q.get("level") or [""])[0]
            if raw == "free":
                STATE["level"] = None
            else:
                try:
                    value = int(raw)
                except ValueError:
                    return self._json({"error": f"level={raw!r} is not an integer"}, 400)
                if not 0 <= value <= 255:
                    return self._json({"error": f"level {value} outside 0..255"}, 400)
                STATE["level"] = value
            STATE["seq"] += 1
            return self._json(STATE)

        return super().do_GET()

    def log_message(self, fmt, *args):
        # the poll is once every 300 ms and the refresh report every 2 s;
        # logging either buries everything else
        line = args[0] if args else ""
        if "/level" not in line and "/refresh" not in line:
            super().log_message(fmt, *args)


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    handler = functools.partial(Handler, directory=str(ROOT))
    with Server(("0.0.0.0", PORT), handler) as httpd:
        print(f"serving {ROOT} on port {PORT}", file=sys.stderr, flush=True)
        httpd.serve_forever()
