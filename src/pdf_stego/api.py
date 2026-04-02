"""High-level programmatic API for PDF steganography.

Handles file I/O, encryption, and delegates to core algorithm functions.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pdf_stego.core import embed_watermark, extract_watermark
from pdf_stego.encryption import decrypt, encrypt
from pdf_stego.pdf_ops import count_objects, decompress, open_pdf, save_compressed
from pdf_stego.types import (
    DEFAULT_CHANNEL,
    DEFAULT_ENCRYPTION_METHOD,
    DEFAULT_INSERTION_ORDER,
    DEFAULT_MODE,
    DEFAULT_SEED,
    FONT_DICT_KEY,
    XOBJ_DICT_KEY,
    Channel,
    EncryptionMethod,
    InsertionOrder,
    Mode,
    WatermarkInput,
)


def _resolve_watermark(watermark: WatermarkInput) -> bytes:
    """Convert a WatermarkInput to raw bytes."""
    match watermark:
        case bytes() | bytearray():
            return bytes(watermark)
        case Path():
            return watermark.read_bytes()
        case str():
            return watermark.encode("utf-8")
        case _:
            raise TypeError(f"Unsupported watermark type: {type(watermark)}")


def embed(
    input_pdf: str | Path,
    output_pdf: str | Path,
    watermark: WatermarkInput,
    *,
    channel: Channel = DEFAULT_CHANNEL,
    encryption: EncryptionMethod = "none",
    encryption_key: str | None = None,
    font_dict_key: str = FONT_DICT_KEY,
    xobj_dict_key: str = XOBJ_DICT_KEY,
    mode: Mode = DEFAULT_MODE,
    order: InsertionOrder = DEFAULT_INSERTION_ORDER,
    seed: int = DEFAULT_SEED,
) -> dict[str, Any]:
    """Embed a watermark into a PDF file.

    Args:
        input_pdf: Path to the cover PDF.
        output_pdf: Path to save the watermarked PDF.
        watermark: Watermark data (bytes, str, or Path to a file).
        channel: ``"font"``, ``"xobject"``, or ``"both"`` (default).
        encryption: Watermark encryption method. Default ``"none"``.
        encryption_key: Key/passphrase for encryption (required if
            *encryption* is not ``"none"``).
        font_dict_key: Custom font dict entry key.
        xobj_dict_key: Custom XObject entry key.
        mode: ``"payload"`` (split across objects) or ``"watermark"``
            (same data to every object). Default ``"payload"``.
        order: Insertion order for payload mode: ``"forwards"``,
            ``"backwards"``, or ``"random"`` (default).
        seed: RNG seed for ``"random"`` order (default ``0``).

    Returns:
        Dict with metadata: ``font_objects_embedded``, ``xobjects_embedded``,
        ``watermark_bytes``, ``encryption``, ``mode``.

    Raises:
        ValueError: If encryption is requested but no key is given,
            or if no candidate objects are found.
    """
    if encryption != "none" and not encryption_key:
        raise ValueError(f"encryption_key is required when encryption={encryption!r}")

    # Resolve input
    wm_bytes = _resolve_watermark(watermark)

    # Encrypt watermark if requested
    if encryption != "none":
        if encryption_key is None:
            raise ValueError(f"encryption_key is required when encryption={encryption!r}")
        wm_bytes = encrypt(wm_bytes, encryption, encryption_key)

    # Open, decompress, embed, save
    pdf = open_pdf(input_pdf)
    decompress(pdf)
    result = embed_watermark(
        pdf,
        wm_bytes,
        channel=channel,
        font_key=font_dict_key,
        xobj_key=xobj_dict_key,
        mode=mode,
        order=order,
        seed=seed,
    )
    save_compressed(pdf, output_pdf)
    pdf.close()

    res: dict[str, Any] = dict(result)
    res["watermark_bytes"] = len(wm_bytes)
    res["encryption"] = encryption
    res["mode"] = mode
    return res


def extract(
    input_pdf: str | Path,
    *,
    output: str | Path | None = None,
    channel: Channel = DEFAULT_CHANNEL,
    encryption: EncryptionMethod = DEFAULT_ENCRYPTION_METHOD,
    encryption_key: str | None = None,
    font_dict_key: str = FONT_DICT_KEY,
    xobj_dict_key: str = XOBJ_DICT_KEY,
    mode: Mode = DEFAULT_MODE,
    order: InsertionOrder = DEFAULT_INSERTION_ORDER,
    seed: int = DEFAULT_SEED,
) -> bytes:
    """Extract a watermark from a PDF file.

    Args:
        input_pdf: Path to the watermarked PDF.
        output: If given, write extracted watermark to this file.
        channel: ``"font"``, ``"xobject"``, or ``"both"`` (default).
        encryption: Decryption method (must match what was used for embed).
        encryption_key: Key/passphrase for decryption.
        font_dict_key: Custom font dict entry key.
        xobj_dict_key: Custom XObject entry key.
        mode: ``"payload"`` or ``"watermark"``. Default ``"payload"``.
        order: Insertion order for payload mode. Default ``"random"``.
        seed: RNG seed for ``"random"`` order. Default ``0``.

    Returns:
        Extracted watermark as bytes.

    Raises:
        ValueError: If no watermark is found or decryption fails.
    """
    if encryption != "none" and not encryption_key:
        raise ValueError(f"encryption_key is required when encryption={encryption!r}")

    pdf = open_pdf(input_pdf)
    decompress(pdf)
    wm_bytes = extract_watermark(
        pdf,
        channel=channel,
        font_key=font_dict_key,
        xobj_key=xobj_dict_key,
        mode=mode,
        order=order,
        seed=seed,
    )
    pdf.close()

    # Decrypt if needed
    if encryption != "none":
        if encryption_key is None:
            raise ValueError(f"encryption_key is required when encryption={encryption!r}")
        wm_bytes = decrypt(wm_bytes, encryption, encryption_key)

    # Write to file if requested
    if output is not None:
        Path(output).write_bytes(wm_bytes)

    return wm_bytes


def info(
    input_pdf: str | Path,
    *,
    font_dict_key: str = FONT_DICT_KEY,
    xobj_dict_key: str = XOBJ_DICT_KEY,
) -> dict[str, Any]:
    """Report object counts and watermark status of a PDF.

    Args:
        input_pdf: Path to a PDF file.
        font_dict_key: Custom font dict entry key.
        xobj_dict_key: Custom XObject entry key.

    Returns:
        Dict with counts: ``font_objects``, ``xobjects``,
        ``font_watermarked``, ``xobj_watermarked``.
    """
    pdf = open_pdf(input_pdf)
    decompress(pdf)
    result = count_objects(pdf, font_key=font_dict_key, xobj_key=xobj_dict_key)
    pdf.close()
    return result
