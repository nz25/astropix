"""Reading one frame, and describing it.

Per-frame work only.  Give it a path and it hands back pixels, the *trusted*
capture settings, and a full description of that single frame -- what it is, how
it varies, whether it came from this rig.  Trusted means gain, offset, exposure,
set and achieved temperature: the settings the camera was actually given.  The
frame *type* label is not trusted (D18).

**No loops, no directories, no CSV.**  Walking the archive, deciding what to
re-read, checkpointing and progress reporting are orchestration, and they live
in the notebook that does them (D35).  What stays here is the part that is the
same whether you scan one frame or fifteen thousand -- and the part worth a test.

Frames are sampled, not read whole: a few row-blocks per frame.  Over SMB a frame
costs ~0.09 s to open and ~0.08 s more for a sampled slice, against ~2.7 s for
all 16.6 MB, so sampling turns an 11-hour pass into a 40-minute one.  Statistics
are what classification needs; pixels are not.

Interpreting the arrays belongs to `spatial.py` and `stats.py`; this module hands
them over.
"""

from __future__ import annotations

import hashlib
import os

import numpy as np
from astropy.io import fits as _afits

from . import stats

# --- sampling geometry -------------------------------------------------------
N_BLOCKS = 6          # row-blocks spread down the frame
BLOCK_ROWS = 32       # mosaic rows per block -> 16 rows per sub-plane

FITS_SUFFIXES = (".fit", ".fits", ".fts")

# One rig.  A frame from another camera that reached the archive is a cleanup
# item (D20, D26) -- marked in `status`, never dropped, because silence hides it.
RIG_INSTRUME = "ZWO ASI585MC Pro"


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


def scan_frame(path):
    """Everything the index records about one frame.

    Returns capture settings, measured features, the measured type, the declared
    label and whether they agree -- plus `status`, which is "ok" unless the frame
    came from another camera.  Raises on an unreadable file; the caller decides
    whether one bad frame stops a pass.
    """
    blocks, header = sample_blocks(path)
    rec = capture_settings(header)
    rec.update(stats.frame_features(blocks))
    rec["measured_type"] = stats.classify(rec, rec.get("exptime"))
    declared = (rec.get("imagetyp") or "").strip().lower()
    rec["declared_type"] = declared
    rec["type_agrees"] = (declared == rec["measured_type"]) if declared else None
    rec["status"] = ("ok" if rec.get("instrume") == RIG_INSTRUME
                     else "other rig: " + str(rec.get("instrume")))
    return rec


def stat_row(path):
    """The identity of a frame on disk, as the index stores it.

    `mtime` is kept as `repr` rather than a float on purpose.  The index
    round-trips through CSV, and this string is compared against the stored one
    to decide whether a frame changed -- a comparison that must be exact.  Going
    through float would make the whole incremental scan depend on text-to-float
    round-tripping being lossless, which is a bet worth not taking.
    """
    st = os.stat(path)
    return {"path": str(path), "size": st.st_size, "mtime": repr(st.st_mtime)}


def needs_rescan(path, prev):
    """Should this frame be read again?  The whole reason a refresh is minutes
    rather than hours.

    Re-read when there is no previous row, when the previous pass did not end in
    "ok" (an unreadable frame may since have been repaired), or when size or
    mtime has moved.  Everything else is skipped without opening the file.
    """
    if not prev or str(prev.get("status", "")) != "ok":
        return True
    now = stat_row(path)
    return (str(prev.get("size")) != str(now["size"])
            or str(prev.get("mtime")) != now["mtime"])


def sha256(path, chunk=1 << 20):
    """Content hash.  Deliberately *not* run over the archive (D19) -- only over
    the specific frames underpinning a published constant."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()
