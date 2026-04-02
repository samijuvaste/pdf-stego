"""Low-level PDF operations using pikepdf.

Handles decompression, object discovery, dictionary entry
manipulation, and recompression/saving.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import cast

import pikepdf

from pdf_stego.types import FONT_DICT_KEY, XOBJ_DICT_KEY

# ---------------------------------------------------------------------------
# Open / decompress
# ---------------------------------------------------------------------------


def open_pdf(pdf_path: str | Path) -> pikepdf.Pdf:
    """Open a PDF file and return a pikepdf.Pdf handle."""
    return pikepdf.open(pdf_path)


def decompress(pdf: pikepdf.Pdf) -> None:
    """Decompress all object streams in-place.

    Equivalent to ``pdftk <file> output - uncompress``.
    After this call every stream in *pdf* is uncompressed so that
    content streams and structural objects are accessible as plain text.
    """
    for page in pdf.pages:
        # Decompress page content streams
        if "/Contents" in page:
            contents = page["/Contents"]
            if isinstance(contents, pikepdf.Array):
                for stream_obj in cast(Iterable[pikepdf.Object], contents):
                    if isinstance(stream_obj, pikepdf.Stream):
                        _decompress_stream(stream_obj)
            elif isinstance(contents, pikepdf.Stream):
                _decompress_stream(contents)

    # Also decompress any object streams
    for objnum in range(1, len(pdf.objects)):
        try:
            obj = pdf.objects[objnum]
        except (KeyError, IndexError):
            continue
        if isinstance(obj, pikepdf.Stream):
            _decompress_stream(obj)


def _decompress_stream(stream: pikepdf.Stream) -> None:
    """Remove compression filters from a single stream object."""
    try:
        # Reading bytes decompresses; re-writing without filter keeps it plain
        raw_data = stream.read_bytes()
        stream.write(raw_data)
    except Exception:  # noqa: S110
        # Some streams may fail to decompress (e.g. image data) — skip them
        pass


# ---------------------------------------------------------------------------
# Object discovery
# ---------------------------------------------------------------------------


def find_font_dict_objects(pdf: pikepdf.Pdf) -> list[pikepdf.Object]:
    """Find all Font Dictionary Objects across all pages.

    A Font Dictionary Object has ``/Type /Font`` in the PDF spec.
    We traverse each page's ``/Resources -> /Font`` dictionary.

    Returns:
        List of pikepdf objects representing fonts (support dict-like access).
    """
    fonts: list[pikepdf.Object] = []
    seen_objgens: set[tuple[int, int]] = set()

    for page in pdf.pages:
        page_fonts = _get_fonts_from_resources(page, seen_objgens)
        fonts.extend(page_fonts)

    return fonts


def _get_fonts_from_resources(
    page: pikepdf.Page,
    seen: set[tuple[int, int]],
) -> list[pikepdf.Object]:
    """Extract font dictionaries from a page's resources."""
    fonts: list[pikepdf.Object] = []

    resources = page.resources
    font_dict = resources.get("/Font")
    if font_dict is not None:
        for _name in sorted(font_dict.keys(), key=str):
            font_obj = font_dict[_name]
            objgen = font_obj.objgen
            if objgen in seen:
                continue
            seen.add(objgen)
            fonts.append(font_obj)

    return fonts


def find_xobjects(pdf: pikepdf.Pdf) -> list[pikepdf.Object]:
    """Find all Image XObjects and Form XObjects across all pages.

    Returns:
        List of pikepdf objects representing XObjects (support dict-like access).
    """
    xobjects: list[pikepdf.Object] = []
    seen_objgens: set[tuple[int, int]] = set()

    for page in pdf.pages:
        page_xobjects = _get_xobjects_from_resources(page, seen_objgens)
        xobjects.extend(page_xobjects)

    return xobjects


def _get_xobjects_from_resources(
    page: pikepdf.Page,
    seen: set[tuple[int, int]],
) -> list[pikepdf.Object]:
    """Extract XObjects (Image and Form) from a page's resources."""
    xobjects: list[pikepdf.Object] = []

    resources = page.resources
    xobj_dict = resources.get("/XObject")
    if xobj_dict is not None:
        for _name in sorted(xobj_dict.keys(), key=str):
            xobj = xobj_dict[_name]
            objgen = xobj.objgen
            if objgen in seen:
                continue
            seen.add(objgen)

            subtype = xobj.get("/Subtype")
            if subtype is not None and str(subtype) in ("/Image", "/Form"):
                xobjects.append(xobj)

    return xobjects


# ---------------------------------------------------------------------------
# Dictionary entry manipulation
# ---------------------------------------------------------------------------


def add_dict_entry(obj: pikepdf.Object, key: str, value: str) -> None:
    """Add a dictionary entry to a PDF object.

    Args:
        obj: The PDF object (Font Dict or XObject) with dict-like access.
        key: Entry key name (e.g. ``/Fontinfo``).
        value: String value to store.
    """
    obj[pikepdf.Name(key)] = pikepdf.String(value)


def get_dict_entry(obj: pikepdf.Object, key: str) -> str | None:
    """Read a dictionary entry value from a PDF object.

    Returns:
        The string value if the key exists, else ``None``.
    """
    name = pikepdf.Name(key)
    if name in obj:
        val = obj[name]
        return str(val)
    return None


def has_dict_entry(obj: pikepdf.Object, key: str) -> bool:
    """Check whether a dictionary entry exists in a PDF object.

    Useful for tamper detection: objects lacking the watermark entry
    are candidates for having been added after watermarking.
    """
    return pikepdf.Name(key) in obj


# ---------------------------------------------------------------------------
# Save / recompress
# ---------------------------------------------------------------------------


def save_compressed(pdf: pikepdf.Pdf, output_path: str | Path) -> None:
    """Recompress and save the PDF.

    pikepdf automatically recalculates the cross-reference table (CRT/CRS)
    and byte offsets when saving, so no manual CRT update is needed.
    """
    pdf.save(
        output_path,
        compress_streams=True,
        object_stream_mode=pikepdf.ObjectStreamMode.generate,
    )


# ---------------------------------------------------------------------------
# Info / inspection
# ---------------------------------------------------------------------------


def count_objects(
    pdf: pikepdf.Pdf,
    font_key: str = FONT_DICT_KEY,
    xobj_key: str = XOBJ_DICT_KEY,
) -> dict[str, int]:
    """Count Font Dict Objects and XObjects, and how many carry watermarks.

    Returns:
        Dict with keys: ``font_objects``, ``xobjects``,
        ``font_watermarked``, ``xobj_watermarked``.
    """
    fonts = find_font_dict_objects(pdf)
    xobjects = find_xobjects(pdf)

    return {
        "font_objects": len(fonts),
        "xobjects": len(xobjects),
        "font_watermarked": sum(1 for f in fonts if has_dict_entry(f, font_key)),
        "xobj_watermarked": sum(1 for x in xobjects if has_dict_entry(x, xobj_key)),
    }
