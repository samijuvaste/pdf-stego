"""Type definitions for the PDF steganography package."""

from pathlib import Path
from typing import Literal

# Embedding channel options
Channel = Literal["font", "xobject", "both"]
DEFAULT_CHANNEL: Channel = "both"

# Dictionary entry key names (from the paper §4.1)
FONT_DICT_KEY = "/Fontinfo"
XOBJ_DICT_KEY = "/XObjinfo"

# Encryption method options
EncryptionMethod = Literal["none", "aes"]
DEFAULT_ENCRYPTION_METHOD: EncryptionMethod = "none"

# Operation mode options
Mode = Literal["payload", "watermark"]
DEFAULT_MODE: Mode = "payload"

# Insertion order options (payload mode)
InsertionOrder = Literal["forwards", "backwards", "random"]
DEFAULT_INSERTION_ORDER: InsertionOrder = "random"
DEFAULT_SEED: int = 0

# Watermark input: raw bytes, a string (UTF-8 encoded), or a file path
WatermarkInput = bytes | str | Path
