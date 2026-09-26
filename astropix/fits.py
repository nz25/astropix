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
import xml.etree.ElementTree as ET

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


# XISF sample formats this project meets, and nothing else.  PixInsight writes
# StarAlignment's output in XISF whatever extension it is asked for, so the
# registered planes of contract 3 arrive in this format and no other.
_XISF_DTYPES = {"UInt16": "<u2", "Float32": "<f4", "Float64": "<f8"}


def read_xisf(path):
    """Return the pixels of a monolithic, uncompressed, one-image XISF file.

    Bytes only, like `read`: the values come back exactly as PixInsight stored
    them -- a UInt16 image in stored units, a float one in PI's [0, 1] -- and
    turning either into ADC counts is `pixinsight`'s job, not this one's.

    Checked against the XISF 1.0 specification (pixinsight.com, section
    numbers below), not only against the files PixInsight happens to write:

    - 9.2: eight bytes `XISF0100`, a little-endian uint32 header length, four
      reserved bytes that must be zero, and the XML header from byte 16.
    - 11.5: `geometry` is `width:height:channels` -- X first -- and the
      `Image` elements are the root's children of that name.  A `Thumbnail`
      is a different element and is not counted.
    - 8.5.3: samples run row by row from the top, x fastest, so one channel
      reshapes to `(height, width)`.  With one channel the planar and normal
      storage models are the same bytes, so `pixelStorage` does not matter.
    - 10.3: `attachment:position:size`, position counted from the start of
      the file; the size must match the geometry or the block is not this
      image.
    - 10.4: `byteOrder` is `little` or `big`, little when absent.
    - 11.5: a float image must declare `bounds`.  Only `0:1` is accepted,
      because that is what `pixinsight.to_adc` assumes.

    Everything this reader does not handle -- compression, big-endian data,
    more than one image, more than one channel, pixels stored anywhere but an
    attachment, a sample format outside `_XISF_DTYPES` -- raises, because a
    reader that guessed would hand back a plausible array of the wrong
    numbers.  An optional `checksum` is not verified.
    """
    with open(path, "rb") as f:
        head = f.read(16)
        if head[:8] != b"XISF0100" or head[12:16] != bytes(4):
            raise ValueError(f"{path} is not a monolithic XISF 1.0 file")
        root = ET.fromstring(f.read(int.from_bytes(head[8:12], "little")))
        images = [e for e in root if e.tag.rsplit("}", 1)[-1] == "Image"]
        if len(images) != 1:
            raise ValueError(f"{path} holds {len(images)} images; expected one")
        attr = images[0].attrib
        if "compression" in attr or attr.get("byteOrder", "little") != "little":
            raise ValueError(f"{path}: compressed or big-endian XISF is not read here")
        fmt = attr.get("sampleFormat")
        if fmt not in _XISF_DTYPES:
            raise ValueError(f"{path}: sample format {fmt!r} is not read here")
        if fmt.startswith("Float") and attr.get("bounds") not in ("0:1", "0.0:1.0"):
            raise ValueError(f"{path}: float bounds {attr.get('bounds')!r}, not 0:1")
        dims = [int(v) for v in attr["geometry"].split(":")]
        if len(dims) != 3 or dims[2] != 1:
            raise ValueError(f"{path} has geometry {attr['geometry']}; "
                             "expected one two-dimensional plane")
        w, h = dims[:2]
        where = attr["location"].split(":")
        if where[0] != "attachment" or len(where) != 3:
            raise ValueError(f"{path}: pixels are {attr['location']}, not an attachment")
        dtype = np.dtype(_XISF_DTYPES[fmt])
        size = int(where[2])
        if size != w * h * dtype.itemsize:
            raise ValueError(f"{path}: block of {size} bytes does not hold a "
                             f"{w}x{h} {fmt} image")
        f.seek(int(where[1]))
        raw = f.read(size)
    if len(raw) != size:
        raise ValueError(f"{path} is truncated")
    return np.frombuffer(raw, dtype=dtype).reshape(h, w)


def write(path, mosaic, header=None, overwrite=False):
    """Write one frame exactly as the camera produced it.

    The counterpart to `read`, and held to the same rule: bytes move, nothing
    is interpreted.  The mosaic is written as uint16 -- **stored** values, not
    ADC counts -- because a bench frame has to be indistinguishable from an
    archive frame to the reader, or `frame_features` loses the `% 16` check
    that licenses the whole unit convention (CLAUDE.md).

    `overwrite` defaults to False: a capture loop that silently rewrites a
    frame it has already taken destroys the one thing a sweep cannot
    reconstruct, which is how many frames it actually got.
    """
    hdu = _afits.PrimaryHDU(data=np.asarray(mosaic, np.uint16))
    for key, value in (header or {}).items():
        if value is not None:
            hdu.header[key] = value
    hdu.writeto(path, overwrite=overwrite)
    return path


def capture_settings(header):
    return {k: header.get(v) for k, v in _HEADER_KEYS.items()}


def sample_blocks(path, n_blocks=N_BLOCKS, block_rows=BLOCK_ROWS):
    """Read `n_blocks` evenly spaced contiguous row-blocks, plus the header.

    Blocks are contiguous because a contiguous slice is one seek over SMB where
    a strided read is thousands, and because anything spatial added later --
    vignetting, source detection -- needs neighbours to still be neighbours.
    They are spread down the frame so that vignetting and amp glow -- both
    corner-weighted -- are sampled rather than missed, which is what
    `block_spread` is measured from.
    """
    with _afits.open(path) as hdul:
        hdu = hdul[0]
        header = hdu.header
        ny = int(header["NAXIS2"])
        block_rows = min(block_rows, ny) & ~1          # keep Bayer row pairs
        starts = np.linspace(0, ny - block_rows, n_blocks).astype(int) & ~1
        blocks = [np.asarray(hdu.section[s:s + block_rows]) for s in starts]
    return blocks, header


def scan_frame(path, pedestal=None):
    """Everything the index records about one frame.

    Returns capture settings, measured features, the measured type, the declared
    label and whether they agree -- plus `status`, which is "ok" unless the frame
    came from another camera.  Raises on an unreadable file; the caller decides
    whether one bad frame stops a pass.

    `pedestal` is the zero-light level in ADC counts for this frame's gain, and
    it is the caller's to supply because measuring it means looking at many
    frames, which is a loop and therefore the notebook's job (D35, D50).  With
    no pedestal the type comes back "unknown" -- which is what the first pass of
    an index build wants, since it is that pass which produces the bias frames
    the pedestal is measured from.
    """
    blocks, header = sample_blocks(path)
    rec = capture_settings(header)
    rec.update(stats.frame_features(blocks))
    rec["measured_type"] = stats.classify(rec, rec.get("exptime"), pedestal)
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
