"""Reading frames, and the header index over the archive.

Two jobs (DECISIONS D15):

1.  Get pixels and *trusted* capture settings out of a FITS file.  Trusted means
    gain, offset, exposure, set and achieved temperature -- the settings the
    camera was actually given.  The frame *type* label is not trusted (D18).
2.  Maintain an incremental index of the archive, which decides each frame type
    from its own pixels and records the disagreement with the label.

The index reads a few row-blocks per frame, not whole frames.  Over SMB a frame
costs ~0.09 s to open and ~0.08 s more for a sampled slice, against ~2.7 s for
all 16.6 MB, so sampling turns an 11-hour pass into a 40-minute one.  Statistics
are what classification needs; pixels are not.
"""

from __future__ import annotations

import csv
import datetime as _dt
import hashlib
import os

import numpy as np
from astropy.io import fits as _afits

from . import cfa

# --- sampling geometry -------------------------------------------------------
N_BLOCKS = 6          # row-blocks spread down the frame
BLOCK_ROWS = 32       # mosaic rows per block -> 16 rows per sub-plane

# --- classifier thresholds (calibrated in notebooks/01) ----------------------
BIAS_MAX_EXPTIME = 0.01     # s; a bias is the shortest exposure the camera takes
FLAT_MIN_LEVEL = 0.15       # fraction of 16-bit full scale
TAIL_K = 5.0                # sigma above the plane median for "bright pixel"
LIGHT_MIN_CLUMP = 0.25      # bright pixels sharing a bright neighbour both ways
LIGHT_MIN_TAIL = 1e-5       # bright-pixel fraction, guards against empty tails
SATURATED_FRAC = 0.5        # clipped everywhere: a quality flag, not a type
FLAT_MAX_EXPTIME = 5.0      # s; measured -- every flat in the archive is 1-3 s

FULL_SCALE = 65535

# Capture settings, trusted.  IMAGETYP is read but kept separate: it is evidence
# about the label, not about the frame.
_HEADER_KEYS = {
    "imagetyp": "IMAGETYP", "exptime": "EXPTIME", "gain": "GAIN",
    "offset": "OFFSET", "set_temp": "SET-TEMP", "ccd_temp": "CCD-TEMP",
    "date_obs": "DATE-OBS", "object": "OBJECT", "bayerpat": "BAYERPAT",
    "egain_hdr": "EGAIN", "focallen": "FOCALLEN", "xbinning": "XBINNING",
    "instrume": "INSTRUME", "creator": "CREATOR", "naxis1": "NAXIS1",
    "naxis2": "NAXIS2", "bitpix": "BITPIX",
}


def read(path):
    """Return (mosaic, header).  The mosaic stays uint16 -- exactly the numbers
    the camera wrote, BZERO-shifted back by astropy, never silently floated."""
    with _afits.open(path) as hdul:
        return np.asarray(hdul[0].data), hdul[0].header


def capture_settings(header):
    return {k: header.get(v) for k, v in _HEADER_KEYS.items()}


def sample_blocks(path, n_blocks=N_BLOCKS, block_rows=BLOCK_ROWS):
    """Read `n_blocks` evenly spaced contiguous row-blocks, plus the header.

    Blocks are contiguous because two of the features are spatial: a star is a
    blob and a hot pixel is not, and neither statement survives row striding.
    They are spread down the frame so that vignetting and amp glow -- both
    corner-weighted -- are sampled rather than missed.
    """
    with _afits.open(path) as hdul:
        hdu = hdul[0]
        header = hdu.header
        ny = int(header["NAXIS2"])
        block_rows = min(block_rows, ny) & ~1          # keep Bayer row pairs
        starts = np.linspace(0, ny - block_rows, n_blocks).astype(int) & ~1
        blocks = [np.asarray(hdu.section[s:s + block_rows]) for s in starts]
    return blocks, header


def _bright_pixel_stats(plane, thr):
    """Count bright pixels and how many have a bright neighbour, per axis.

    Splitting horizontal from vertical matters: a hot *column* -- a common CMOS
    defect -- is vertically connected and would otherwise read as a star.  A
    real PSF is connected both ways, so the weaker axis is the honest one.
    """
    m = plane > thr
    n = int(m.sum())
    if n == 0:
        return 0, 0, 0
    h = np.zeros_like(m)
    h[:, 1:] |= m[:, :-1]
    h[:, :-1] |= m[:, 1:]
    v = np.zeros_like(m)
    v[1:, :] |= m[:-1, :]
    v[:-1, :] |= m[1:, :]
    return n, int((m & h).sum()), int((m & v).sum())


def frame_features(blocks):
    """Reduce sampled blocks to the handful of numbers the classifier uses.

    Every statistic is per CFA sub-plane (D4).  Level and spread are medians
    *across* blocks rather than pooled over them, so that a sky gradient or
    vignetting inflates `block_spread` -- where it is informative -- instead of
    contaminating `sigma`, where it would be a lie.
    """
    per_plane = {p: {"med": [], "sig": []} for p in cfa.PLANES}
    n_tot = n_h = n_v = n_px = 0
    block_meds = []

    for blk in blocks:
        planes = cfa.split(blk)
        meds = []
        for name, pl in planes.items():
            pl = pl.astype(np.float32)
            med = float(np.median(pl))
            sig = float(1.4826 * np.median(np.abs(pl - med)))
            per_plane[name]["med"].append(med)
            per_plane[name]["sig"].append(sig)
            meds.append(med)
            n, nh, nv = _bright_pixel_stats(pl, med + TAIL_K * max(sig, 1.0))
            n_tot += n
            n_h += nh
            n_v += nv
            n_px += pl.size
        block_meds.append(float(np.mean(meds)))

    med = {p: float(np.median(per_plane[p]["med"])) for p in cfa.PLANES}
    sig = {p: float(np.median(per_plane[p]["sig"])) for p in cfa.PLANES}
    level = float(np.mean(list(med.values())))
    sample = np.concatenate([b.ravel() for b in blocks])

    feats = {
        "level": level,
        "sigma": float(np.mean(list(sig.values()))),
        # large-scale structure: vignetting, amp glow, sky gradient
        "block_spread": float((max(block_meds) - min(block_meds)) / max(level, 1.0)),
        "tail_frac": n_tot / max(n_px, 1),
        # weaker axis: a star clumps both ways, a hot column only vertically
        "clump_frac": min(n_h, n_v) / max(n_tot, 1),
        "clump_h": n_h / max(n_tot, 1),
        "clump_v": n_v / max(n_tot, 1),
        # 12-bit ADC stored bit-shifted x16 => every value a multiple of 16
        "mult16_frac": float(np.mean(sample % 16 == 0)),
        "sat_frac": float(np.mean(sample >= FULL_SCALE - 15)),
    }
    for p in cfa.PLANES:
        feats["med_" + p.lower()] = med[p]
        feats["sig_" + p.lower()] = sig[p]
    return feats


def classify(features, exptime):
    """Decide the frame type from the pixels (D18).

    Order matters.  Exposure is a trusted capture setting, so the bias case is
    settled before any pixel argument is made.  Level separates flats, which sit
    an order of magnitude above the pedestal.  What remains -- dark or light at
    the same exposure and pedestal -- is separated by whether its bright pixels
    are blobs (a PSF) or isolated sites (hot pixels).
    """
    if exptime is not None and float(exptime) <= BIAS_MAX_EXPTIME:
        return "bias"

    bright = (features["level"] >= FLAT_MIN_LEVEL * FULL_SCALE
              or features["sat_frac"] >= SATURATED_FRAC)
    if bright:
        # A frame sitting far above the pedestal saw a lot of light.  Level
        # alone cannot say what kind: a flat panel and a twilight sky look the
        # same, and once clipped every other feature is degenerate too (sigma
        # and clump go to zero).  So this branch is an *inference*, not a
        # measurement, and it leans on the one thing left -- a capture setting,
        # which D18 keeps trusted.  Every flat in this archive is 1-3 s, so a
        # bright long exposure is sky, not a panel: a light that ran into dawn
        # or started in twilight.  Saturation stays recorded in `sat_frac`, a
        # quality attribute orthogonal to what the frame is (D25, D27).
        return "flat" if float(exptime) <= FLAT_MAX_EXPTIME else "light"

    if (features["clump_frac"] >= LIGHT_MIN_CLUMP
            and features["tail_frac"] >= LIGHT_MIN_TAIL):
        return "light"
    return "dark"


def scan_frame(path):
    """Full per-frame record: capture settings + features + measured type."""
    blocks, header = sample_blocks(path)
    rec = capture_settings(header)
    rec.update(frame_features(blocks))
    rec["measured_type"] = classify(rec, rec.get("exptime"))
    declared = (rec.get("imagetyp") or "").strip().lower()
    rec["declared_type"] = declared
    rec["type_agrees"] = (declared == rec["measured_type"]) if declared else None
    return rec


# --- the archive index (D15, D19) -------------------------------------------

FITS_SUFFIXES = (".fit", ".fits", ".fts")

# One rig, enforced twice.  `_canon` holds frames from a retired camera and has
# its own bias/dark/flat/light beneath it, so pointing the walk at `_by_type`
# instead of at the four type folders would pull them into exactly the buckets
# where they would look plausible.  The directory skip is the cheap guard; the
# instrument check is the one that cannot be defeated by a folder rename.
EXCLUDE_DIRS = ("_canon",)
RIG_INSTRUME = "ZWO ASI585MC Pro"

INDEX_COLUMNS = (
    ["path", "size", "mtime", "indexed_at", "status"]
    + list(_HEADER_KEYS)
    + ["level", "sigma", "block_spread", "tail_frac", "clump_frac", "clump_h",
       "clump_v", "mult16_frac", "sat_frac"]
    + ["med_" + p.lower() for p in cfa.PLANES]
    + ["sig_" + p.lower() for p in cfa.PLANES]
    + ["measured_type", "declared_type", "type_agrees"]
)


def walk(roots, exclude=EXCLUDE_DIRS):
    """Every FITS file under `roots`.  Walking is cheap; reading is not.

    Excluded directories are pruned from the walk rather than filtered after,
    so their contents are never stat'd, let alone read.
    """
    exclude = {d.lower() for d in exclude}
    for root in ([roots] if isinstance(roots, (str, os.PathLike)) else roots):
        for dirpath, dirs, names in os.walk(root):
            dirs[:] = [d for d in dirs if d.lower() not in exclude]
            for name in names:
                if name.lower().endswith(FITS_SUFFIXES):
                    yield os.path.join(dirpath, name)


def load_index(csv_path):
    """Existing rows, keyed by path.  Missing file -> empty index."""
    if not os.path.exists(csv_path):
        return {}
    with open(csv_path, newline="", encoding="utf-8") as fh:
        return {row["path"]: row for row in csv.DictReader(fh)}


def _write_index(csv_path, rows):
    tmp = csv_path + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=INDEX_COLUMNS, extrasaction="ignore")
        w.writeheader()
        for row in sorted(rows.values(), key=lambda r: r["path"]):
            w.writerow(row)
    os.replace(tmp, csv_path)


def refresh_index(roots, csv_path, limit=None, checkpoint=200, verbose=True):
    """Bring the index up to date.  Incremental and resumable.

    A row is re-scanned only when (size, mtime) has moved, because over SMB the
    read is the whole cost and the walk is free.  Rows are never deleted: a path
    that has vanished is marked `missing`, so a result citing a frame that later
    moved stays traceable to what it was measured on (D19).
    """
    rows = load_index(csv_path)
    for row in rows.values():
        row.setdefault("status", "ok")
    seen, scanned, failed, other_rig = set(), 0, 0, 0
    stamp = _dt.datetime.now().isoformat(timespec="seconds")

    for path in walk(roots):
        seen.add(path)
        try:
            st = os.stat(path)
        except OSError:
            continue
        prev = rows.get(path)
        if (prev and prev.get("status") == "ok"
                and prev.get("size") == str(st.st_size)
                and prev.get("mtime") == repr(st.st_mtime)):
            continue
        row = {"path": path, "size": st.st_size, "mtime": repr(st.st_mtime),
               "indexed_at": stamp, "status": "ok"}
        try:
            row.update(scan_frame(path))
            if row.get("instrume") != RIG_INSTRUME:
                # Marked, not dropped: a frame from another camera that reached
                # the archive is a cleanup item (D20), and silence would hide it.
                row["status"] = "other rig: " + str(row.get("instrume"))
                other_rig += 1
        except Exception as exc:                       # unreadable, truncated
            row["status"] = "unreadable: " + type(exc).__name__
            failed += 1
        rows[path] = row
        scanned += 1
        if verbose and scanned % checkpoint == 0:
            print(f"  scanned {scanned} ({failed} unreadable)", flush=True)
        if scanned % checkpoint == 0:
            _write_index(csv_path, rows)
        if limit and scanned >= limit:
            break

    if not limit:
        for path, row in rows.items():
            if path not in seen and row.get("status") == "ok":
                row["status"] = "missing"
                row["indexed_at"] = stamp
    _write_index(csv_path, rows)
    if verbose:
        print(f"index: {len(rows)} rows, {scanned} scanned this pass, "
              f"{failed} unreadable, {other_rig} from another rig "
              f"-> {csv_path}", flush=True)
    return rows


def sha256(path, chunk=1 << 20):
    """Content hash.  Deliberately *not* run over the archive (D19) -- only over
    the specific frames underpinning a published constant."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()
