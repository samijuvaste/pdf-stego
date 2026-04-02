"""PDF Steganography — Structure-based watermarking (Jiang et al., 2024)."""

from pdf_stego.api import embed, extract, info
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

__all__ = [
    "DEFAULT_CHANNEL",
    "DEFAULT_ENCRYPTION_METHOD",
    "DEFAULT_INSERTION_ORDER",
    "DEFAULT_MODE",
    "DEFAULT_SEED",
    "FONT_DICT_KEY",
    "XOBJ_DICT_KEY",
    "Channel",
    "EncryptionMethod",
    "InsertionOrder",
    "Mode",
    "WatermarkInput",
    "embed",
    "extract",
    "info",
]
