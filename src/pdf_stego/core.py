"""Core watermark embedding and extraction algorithm.

Implements the structure-based watermarking scheme from Jiang et al. (2024),
§4.1.  Operates on an already-opened pikepdf.Pdf object.

Supports two modes:
- **watermark** (original): same data written to every candidate object.
- **payload** (default): data split across candidate objects in configurable order.
"""

from __future__ import annotations

import base64
import math
import random

import pikepdf

from pdf_stego.pdf_ops import add_dict_entry, find_font_dict_objects, find_xobjects, get_dict_entry
from pdf_stego.types import (
    DEFAULT_INSERTION_ORDER,
    DEFAULT_MODE,
    DEFAULT_SEED,
    FONT_DICT_KEY,
    XOBJ_DICT_KEY,
    Channel,
    InsertionOrder,
    Mode,
)

# ---------------------------------------------------------------------------
# Watermark ↔ string conversion
# ---------------------------------------------------------------------------


def watermark_to_str(data: bytes) -> str:
    """Encode watermark bytes to a string safe for PDF dictionary values.

    Uses URL-safe Base64 so the value is plain ASCII and survives any
    PDF text encoding round-trip.
    """
    return base64.urlsafe_b64encode(data).decode("ascii")


def str_to_watermark(s: str) -> bytes:
    """Decode a watermark string back to raw bytes."""
    return base64.urlsafe_b64decode(s.encode("ascii"))


# ---------------------------------------------------------------------------
# Internal helpers — candidate collection & ordering
# ---------------------------------------------------------------------------


def _collect_candidates(
    pdf: pikepdf.Pdf,
    channel: Channel,
    font_key: str = FONT_DICT_KEY,
    xobj_key: str = XOBJ_DICT_KEY,
) -> list[tuple[pikepdf.Object, str]]:
    """Collect ``(object, dict_key)`` pairs from the selected channels.

    Font objects are collected first, then XObjects, preserving discovery
    order within each group.
    """
    candidates: list[tuple[pikepdf.Object, str]] = []

    if channel in ("font", "both"):
        for font_obj in find_font_dict_objects(pdf):
            candidates.append((font_obj, font_key))

    if channel in ("xobject", "both"):
        for xobj in find_xobjects(pdf):
            candidates.append((xobj, xobj_key))

    return candidates


def _order_candidates(
    candidates: list[tuple[pikepdf.Object, str]],
    order: InsertionOrder,
    seed: int,
) -> list[tuple[pikepdf.Object, str]]:
    """Return a new list of candidates reordered by *order*."""
    if order == "forwards":
        return list(candidates)
    if order == "backwards":
        return list(reversed(candidates))
    # random
    ordered = list(candidates)
    random.Random(seed).shuffle(ordered)  # noqa: S311
    return ordered


def split_payload(data: bytes, n: int) -> list[str]:
    """Split *data* into *n* independently-decodable Base64 chunks.

    Each returned string is a self-contained URL-safe Base64 encoding of
    its portion of *data*.  This means any single chunk can be decoded
    in isolation — if a PDF object carrying one chunk is deleted, the
    remaining chunks can still be individually extracted and decoded.

    The last chunk may represent fewer raw bytes than the others.
    """
    if n <= 0:
        raise ValueError("n must be positive")
    if n == 1:
        return [watermark_to_str(data)]
    chunk_size = math.ceil(len(data) / n)
    # Guard against zero-sized chunks when n > len(data)
    if chunk_size == 0:
        chunk_size = 1
    raw_chunks = [data[i * chunk_size : (i + 1) * chunk_size] for i in range(n)]
    return [watermark_to_str(c) for c in raw_chunks if len(c) > 0]


# ---------------------------------------------------------------------------
# Embed
# ---------------------------------------------------------------------------


def embed_watermark(
    pdf: pikepdf.Pdf,
    watermark_bytes: bytes,
    channel: Channel = "both",
    font_key: str = FONT_DICT_KEY,
    xobj_key: str = XOBJ_DICT_KEY,
    mode: Mode = DEFAULT_MODE,
    order: InsertionOrder = DEFAULT_INSERTION_ORDER,
    seed: int = DEFAULT_SEED,
) -> dict[str, int]:
    """Embed a watermark into the PDF's structural objects.

    In **watermark** mode every candidate object receives the full watermark.
    In **payload** mode the encoded watermark is split across candidate objects
    in the order specified by *order* (with *seed* used for ``"random"``).

    Args:
        pdf: An opened (and preferably decompressed) pikepdf.Pdf.
        watermark_bytes: The (possibly encrypted) watermark payload.
        channel: ``"font"``, ``"xobject"``, or ``"both"``.
        font_key: PDF name for the font dict entry (default ``/Fontinfo``).
        xobj_key: PDF name for the XObject dict entry (default ``/XObjinfo``).
        mode: ``"payload"`` or ``"watermark"``.
        order: ``"forwards"``, ``"backwards"``, or ``"random"`` (payload mode).
        seed: RNG seed for ``"random"`` order (default ``0``).

    Returns:
        Dict with keys ``font_objects_embedded``, ``xobjects_embedded``.

    Raises:
        ValueError: If no candidate objects are found in the selected channel.
    """
    result = {"font_objects_embedded": 0, "xobjects_embedded": 0}

    if mode == "watermark":
        wm_str = watermark_to_str(watermark_bytes)
        return _embed_watermark_mode(pdf, wm_str, channel, font_key, xobj_key, result)
    return _embed_payload_mode(
        pdf, watermark_bytes, channel, font_key, xobj_key, order, seed, result
    )


def _embed_watermark_mode(
    pdf: pikepdf.Pdf,
    wm_str: str,
    channel: Channel,
    font_key: str,
    xobj_key: str,
    result: dict[str, int],
) -> dict[str, int]:
    """Original watermark mode: same data to every object."""
    if channel in ("font", "both"):
        fonts = find_font_dict_objects(pdf)
        if not fonts and channel == "font":
            raise ValueError(
                "No Font Dictionary Objects found in the PDF. "
                "Try using channel='both' or channel='xobject'."
            )
        for font_obj in fonts:
            add_dict_entry(font_obj, font_key, wm_str)
            result["font_objects_embedded"] += 1

    if channel in ("xobject", "both"):
        xobjects = find_xobjects(pdf)
        if not xobjects and channel == "xobject":
            raise ValueError(
                "No XObjects found in the PDF. Try using channel='both' or channel='font'."
            )
        for xobj in xobjects:
            add_dict_entry(xobj, xobj_key, wm_str)
            result["xobjects_embedded"] += 1

    total = result["font_objects_embedded"] + result["xobjects_embedded"]
    if total == 0:
        raise ValueError(
            "No candidate objects found in the PDF for watermark embedding. "
            "The file may lack fonts and images/forms."
        )
    return result


def _embed_payload_mode(
    pdf: pikepdf.Pdf,
    wm_bytes: bytes,
    channel: Channel,
    font_key: str,
    xobj_key: str,
    order: InsertionOrder,
    seed: int,
    result: dict[str, int],
) -> dict[str, int]:
    """Payload mode: split data across candidate objects."""
    candidates = _collect_candidates(pdf, channel, font_key, xobj_key)
    if not candidates:
        raise ValueError(
            "No candidate objects found in the PDF for payload embedding. "
            "The file may lack fonts and images/forms."
        )

    ordered = _order_candidates(candidates, order, seed)
    chunks = split_payload(wm_bytes, len(ordered))

    # When there are fewer chunks than candidates (data shorter than n),
    # only the first len(chunks) candidates receive data.
    for (obj, key), chunk in zip(ordered, chunks, strict=False):
        add_dict_entry(obj, key, chunk)
        if key == font_key:
            result["font_objects_embedded"] += 1
        else:
            result["xobjects_embedded"] += 1

    return result


# ---------------------------------------------------------------------------
# Extract
# ---------------------------------------------------------------------------


def extract_watermark(
    pdf: pikepdf.Pdf,
    channel: Channel = "both",
    font_key: str = FONT_DICT_KEY,
    xobj_key: str = XOBJ_DICT_KEY,
    mode: Mode = DEFAULT_MODE,
    order: InsertionOrder = DEFAULT_INSERTION_ORDER,
    seed: int = DEFAULT_SEED,
) -> bytes:
    """Extract the watermark from the PDF's structural objects.

    In **watermark** mode returns the value from the first object that
    contains a watermark entry (all objects carry the same watermark).
    In **payload** mode reconstructs the payload by reading chunks from
    all candidate objects in the same order used during embedding.

    Args:
        pdf: An opened pikepdf.Pdf (decompressed or not — pikepdf resolves).
        channel: ``"font"``, ``"xobject"``, or ``"both"``.
        font_key: PDF name for the font dict entry.
        xobj_key: PDF name for the XObject dict entry.
        mode: ``"payload"`` or ``"watermark"``.
        order: ``"forwards"``, ``"backwards"``, or ``"random"`` (payload mode).
        seed: RNG seed for ``"random"`` order (default ``0``).

    Returns:
        The raw watermark bytes (still encrypted if encryption was used).

    Raises:
        ValueError: If no watermark entry is found.
    """
    if mode == "watermark":
        return _extract_watermark_mode(pdf, channel, font_key, xobj_key)
    return _extract_payload_mode(pdf, channel, font_key, xobj_key, order, seed)


def _extract_watermark_mode(
    pdf: pikepdf.Pdf,
    channel: Channel,
    font_key: str,
    xobj_key: str,
) -> bytes:
    """Original watermark mode: read from first matching object."""
    if channel in ("font", "both"):
        fonts = find_font_dict_objects(pdf)
        for font_obj in fonts:
            value = get_dict_entry(font_obj, font_key)
            if value is not None:
                return str_to_watermark(value)

    if channel in ("xobject", "both"):
        xobjects = find_xobjects(pdf)
        for xobj in xobjects:
            value = get_dict_entry(xobj, xobj_key)
            if value is not None:
                return str_to_watermark(value)

    raise ValueError(
        f"No watermark found in channel={channel!r} with "
        f"font_key={font_key!r}, xobj_key={xobj_key!r}"
    )


def _extract_payload_mode(
    pdf: pikepdf.Pdf,
    channel: Channel,
    font_key: str,
    xobj_key: str,
    order: InsertionOrder,
    seed: int,
) -> bytes:
    """Payload mode: read chunks from all objects and reassemble.

    Each chunk is an independently-encoded Base64 string, so we decode
    each one separately and concatenate the resulting raw bytes.
    """
    candidates = _collect_candidates(pdf, channel, font_key, xobj_key)
    if not candidates:
        raise ValueError(
            "No candidate objects found in the PDF for payload extraction. "
            "The file may lack fonts and images/forms."
        )

    ordered = _order_candidates(candidates, order, seed)
    raw_parts: list[bytes] = []

    for obj, key in ordered:
        value = get_dict_entry(obj, key)
        if value is not None:
            raw_parts.append(str_to_watermark(value))

    if not raw_parts:
        raise ValueError(
            f"No payload chunks found in channel={channel!r} with "
            f"font_key={font_key!r}, xobj_key={xobj_key!r}"
        )

    return b"".join(raw_parts)
