"""Serve `protocols/` to the iPad, and let the bench drive the patch colour.

`grey-patch.html` is usable on its own -- open it, set a grey level by hand,
capture.  This adds two things: a patch the *capture side* can set, so an
attenuation scout can walk level 255 -> 16 without anyone touching the panel
between frames, and a **colour**, because one white-ish source does not fill four
CFA planes and `05-linearity.md` balances them by driving the panel's red, green
and blue subpixels to three different codes.

    GET /level                  -> {"rgb": [128,128,128], "level": 128, "seq": 3,
                                    "probe": false, "applied": {...}, "refresh": {...}}
    GET /set?level=128          -> grey; sets rgb to [128,128,128], bumps seq
    GET /set?rgb=170,221,255    -> a colour, bumps seq
    GET /set?level=free         -> hands the panel back to whoever holds the iPad
    GET /set?probe=1            -> asks the page to animate its corner dot, bumps seq
    GET /applied?rgb=..&seq=..  -> the page saying what it has actually painted
    GET /refresh?ms=...         -> the page reporting how fast it is being served

**`level` is grey and nothing else.**  It survives because a human dialling a
patch by hand wants one number, and because every session before the linearity
one used it.  `rgb` is the general form; `level=L` is exactly `rgb=L,L,L` and is
reported back as a `level` only while the three codes agree.

`/applied` and `/refresh` are the page talking back, and they are the only
endpoints that carry anything measured.

`/applied` is a **handshake, not a measurement**: the page polls every 300 ms and
then paints on its next redraw, so between `/set` returning and the panel
actually changing there is a gap of a poll plus a frame.  A capture that lands in
that gap gets the *previous* colour with nothing in the data to show it.  The
bench therefore waits for `applied.seq` to reach the `seq` its `/set` returned,
and only then starts discarding frames.  It says the page painted, not that the
backlight settled -- the discards after a colour change are what cover that.

`/refresh` is still not a measurement of the *light*: `requestAnimationFrame`
reports the rate the compositor hands the page, and a display with adaptive
refresh serves a still page fewer frames than the panel drives.  That is what
`probe` separates - animate four pixels and see whether the rate rises.  What
the backlight actually does is measured with the camera, never here.

The page polls `/level` and applies a change only when `seq` moves, so a manual
tap is not fought over on the next poll.  `rgb: null` means the server is not
driving and the page is on its own.

Run it with the *base* interpreter rather than the venv one: on this machine the
venv's python.exe is a separate binary with no inbound firewall rule, and the
iPad is on the Public network profile.

    C:/Users/denis/AppData/Local/Python/pythoncore-3.14-64/python.exe \
        protocols/patch-server.py

Nothing here is a measurement and nothing here is physics: it moves three
integers from the notebook to the panel.  The flux those integers produce is
measured by the camera, per `light-source.md` item 3 and Gate 4 of
`05-linearity.md`, and never predicted from the codes.
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

STATE = {"rgb": None, "seq": 0, "probe": False, "applied": None, "refresh": None}


def parse_rgb(raw):
    """"170,221,255" -> [170, 221, 255].  Raises ValueError naming the problem."""
    parts = raw.split(",")
    if len(parts) != 3:
        raise ValueError(f"rgb={raw!r} needs three comma-separated codes, got {len(parts)}")
    out = []
    for name, part in zip("rgb", parts):
        try:
            value = int(part)
        except ValueError:
            raise ValueError(f"rgb={raw!r}: {name} component {part!r} is not an integer") from None
        if not 0 <= value <= 255:
            raise ValueError(f"rgb={raw!r}: {name} component {value} outside 0..255")
        out.append(value)
    return out


def payload():
    """STATE plus the grey level, which exists only while the three codes agree."""
    rgb = STATE["rgb"]
    level = rgb[0] if rgb is not None and rgb[0] == rgb[1] == rgb[2] else None
    return dict(STATE, level=level)


class Handler(http.server.SimpleHTTPRequestHandler):
    def _json(self, body, code=200):
        raw = json.dumps(body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(url.query)

        if url.path == "/level":
            return self._json(payload())

        if url.path == "/applied":
            # The page reporting what it painted, and for which seq.  Anything
            # that does not parse is dropped rather than stored: a malformed
            # handshake must look like "not applied yet", never like applied.
            try:
                STATE["applied"] = {"rgb": parse_rgb(q["rgb"][0]),
                                    "seq": int(q["seq"][0]), "at": time.time()}
            except (KeyError, ValueError, IndexError) as exc:
                return self._json({"error": f"malformed applied report: {exc}"}, 400)
            return self._json({"ok": True})

        if url.path == "/refresh":
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
            if "probe" in q:
                STATE["probe"] = q["probe"][0] not in ("0", "false", "off")
                STATE["seq"] += 1
                return self._json(payload())

            if "rgb" in q and "level" in q:
                return self._json({"error": "pass rgb= or level=, not both"}, 400)

            if "rgb" in q:
                raw = q["rgb"][0]
                if raw == "free":
                    STATE["rgb"] = None
                else:
                    try:
                        STATE["rgb"] = parse_rgb(raw)
                    except ValueError as exc:
                        return self._json({"error": str(exc)}, 400)
            elif "level" in q:
                raw = q["level"][0]
                if raw == "free":
                    STATE["rgb"] = None
                else:
                    try:
                        value = int(raw)
                    except ValueError:
                        return self._json({"error": f"level={raw!r} is not an integer"}, 400)
                    if not 0 <= value <= 255:
                        return self._json({"error": f"level {value} outside 0..255"}, 400)
                    STATE["rgb"] = [value, value, value]
            else:
                return self._json({"error": "/set needs rgb=, level= or probe="}, 400)

            STATE["seq"] += 1
            return self._json(payload())

        return super().do_GET()

    def log_message(self, fmt, *args):
        # the poll is once every 300 ms and the refresh report every 2 s;
        # logging either buries everything else
        line = args[0] if args else ""
        if not any(p in line for p in ("/level", "/refresh", "/applied")):
            super().log_message(fmt, *args)


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    handler = functools.partial(Handler, directory=str(ROOT))
    with Server(("0.0.0.0", PORT), handler) as httpd:
        print(f"serving {ROOT} on port {PORT}", file=sys.stderr, flush=True)
        httpd.serve_forever()
