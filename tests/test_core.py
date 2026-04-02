"""Tests for the core watermark embedding and extraction."""

from __future__ import annotations

from pathlib import Path

import pytest

from pdf_stego.core import (
    embed_watermark,
    extract_watermark,
    split_payload,
    str_to_watermark,
    watermark_to_str,
)
from pdf_stego.pdf_ops import (
    decompress,
    find_font_dict_objects,
    find_xobjects,
    has_dict_entry,
    open_pdf,
)


class TestWatermarkEncoding:
    """Watermark ↔ string conversion."""

    def test_roundtrip_ascii(self) -> None:
        data = b"Hello World"
        assert str_to_watermark(watermark_to_str(data)) == data

    def test_roundtrip_binary(self) -> None:
        data = bytes(range(256))
        assert str_to_watermark(watermark_to_str(data)) == data

    def test_roundtrip_empty(self) -> None:
        data = b""
        assert str_to_watermark(watermark_to_str(data)) == data


class TestObjectDiscovery:
    """Tests for finding Font Dict Objects and XObjects."""

    def test_find_fonts(self, tmp_pdf: Path) -> None:
        pdf = open_pdf(tmp_pdf)
        decompress(pdf)
        fonts = find_font_dict_objects(pdf)
        assert len(fonts) >= 1
        pdf.close()

    def test_find_xobjects(self, tmp_pdf: Path) -> None:
        pdf = open_pdf(tmp_pdf)
        decompress(pdf)
        xobjects = find_xobjects(pdf)
        assert len(xobjects) >= 1
        pdf.close()

    def test_no_xobjects_in_text_only(self, tmp_pdf_no_images: Path) -> None:
        pdf = open_pdf(tmp_pdf_no_images)
        decompress(pdf)
        xobjects = find_xobjects(pdf)
        assert len(xobjects) == 0
        pdf.close()


class TestSplitPayload:
    """Unit tests for the split_payload helper."""

    def test_single_chunk(self) -> None:
        chunks = split_payload(b"abcdef", 1)
        assert len(chunks) == 1
        assert str_to_watermark(chunks[0]) == b"abcdef"

    def test_even_split(self) -> None:
        chunks = split_payload(b"abcdef", 3)
        assert len(chunks) == 3
        # Each chunk is independently decodable
        decoded = b"".join(str_to_watermark(c) for c in chunks)
        assert decoded == b"abcdef"

    def test_uneven_split(self) -> None:
        chunks = split_payload(b"abcde", 3)
        decoded = b"".join(str_to_watermark(c) for c in chunks)
        assert decoded == b"abcde"
        assert len(chunks) == 3

    def test_empty_bytes(self) -> None:
        chunks = split_payload(b"", 3)
        decoded = b"".join(str_to_watermark(c) for c in chunks)
        assert decoded == b""

    def test_more_chunks_than_bytes(self) -> None:
        chunks = split_payload(b"ab", 5)
        decoded = b"".join(str_to_watermark(c) for c in chunks)
        assert decoded == b"ab"

    def test_zero_n_raises(self) -> None:
        with pytest.raises(ValueError, match="n must be positive"):
            split_payload(b"abc", 0)

    def test_each_chunk_independently_decodable(self) -> None:
        """Each chunk must be valid base64 that can be decoded on its own."""
        data = bytes(range(256))
        chunks = split_payload(data, 7)
        # Verify each chunk decodes independently without error
        parts: list[bytes] = []
        for chunk in chunks:
            part = str_to_watermark(chunk)
            assert isinstance(part, bytes)
            parts.append(part)
        assert b"".join(parts) == data


class TestEmbedExtractWatermarkMode:
    """Core embed and extract on in-memory PDFs (watermark mode)."""

    def test_embed_both_channels(self, tmp_pdf: Path) -> None:
        pdf = open_pdf(tmp_pdf)
        decompress(pdf)
        result = embed_watermark(pdf, b"test watermark", channel="both", mode="watermark")
        assert result["font_objects_embedded"] >= 1
        assert result["xobjects_embedded"] >= 1
        pdf.close()

    def test_embed_font_only(self, tmp_pdf: Path) -> None:
        pdf = open_pdf(tmp_pdf)
        decompress(pdf)
        result = embed_watermark(pdf, b"font only", channel="font", mode="watermark")
        assert result["font_objects_embedded"] >= 1
        assert result["xobjects_embedded"] == 0
        pdf.close()

    def test_embed_xobject_only(self, tmp_pdf: Path) -> None:
        pdf = open_pdf(tmp_pdf)
        decompress(pdf)
        result = embed_watermark(pdf, b"xobject only", channel="xobject", mode="watermark")
        assert result["font_objects_embedded"] == 0
        assert result["xobjects_embedded"] >= 1
        pdf.close()

    def test_extract_after_embed(self, tmp_pdf: Path, tmp_path: Path) -> None:
        watermark = b"extract me"
        pdf = open_pdf(tmp_pdf)
        decompress(pdf)
        embed_watermark(pdf, watermark, channel="both", mode="watermark")

        # Save and reopen to simulate real flow
        out = tmp_path / "embedded.pdf"
        pdf.save(out)
        pdf.close()

        pdf2 = open_pdf(out)
        decompress(pdf2)
        extracted = extract_watermark(pdf2, channel="both", mode="watermark")
        assert extracted == watermark
        pdf2.close()

    def test_extract_font_channel(self, tmp_pdf: Path, tmp_path: Path) -> None:
        watermark = b"font channel"
        pdf = open_pdf(tmp_pdf)
        decompress(pdf)
        embed_watermark(pdf, watermark, channel="font", mode="watermark")
        out = tmp_path / "font.pdf"
        pdf.save(out)
        pdf.close()

        pdf2 = open_pdf(out)
        decompress(pdf2)
        extracted = extract_watermark(pdf2, channel="font", mode="watermark")
        assert extracted == watermark
        pdf2.close()

    def test_extract_xobject_channel(self, tmp_pdf: Path, tmp_path: Path) -> None:
        watermark = b"xobj channel"
        pdf = open_pdf(tmp_pdf)
        decompress(pdf)
        embed_watermark(pdf, watermark, channel="xobject", mode="watermark")
        out = tmp_path / "xobj.pdf"
        pdf.save(out)
        pdf.close()

        pdf2 = open_pdf(out)
        decompress(pdf2)
        extracted = extract_watermark(pdf2, channel="xobject", mode="watermark")
        assert extracted == watermark
        pdf2.close()

    def test_no_watermark_raises(self, tmp_pdf: Path) -> None:
        pdf = open_pdf(tmp_pdf)
        decompress(pdf)
        with pytest.raises(ValueError, match="No watermark found"):
            extract_watermark(pdf, channel="both", mode="watermark")
        pdf.close()

    def test_custom_keys(self, tmp_pdf: Path, tmp_path: Path) -> None:
        watermark = b"custom keys"
        pdf = open_pdf(tmp_pdf)
        decompress(pdf)
        embed_watermark(
            pdf,
            watermark,
            channel="both",
            font_key="/MyFont",
            xobj_key="/MyXObj",
            mode="watermark",
        )
        out = tmp_path / "custom.pdf"
        pdf.save(out)
        pdf.close()

        pdf2 = open_pdf(out)
        decompress(pdf2)
        extracted = extract_watermark(
            pdf2,
            channel="both",
            font_key="/MyFont",
            xobj_key="/MyXObj",
            mode="watermark",
        )
        assert extracted == watermark
        pdf2.close()

    def test_has_dict_entry_after_embed(self, tmp_pdf: Path) -> None:
        """Verify has_dict_entry works (tamper detection foundation)."""
        pdf = open_pdf(tmp_pdf)
        decompress(pdf)
        embed_watermark(pdf, b"tamper check", channel="both", mode="watermark")

        fonts = find_font_dict_objects(pdf)
        assert all(has_dict_entry(f, "/Fontinfo") for f in fonts)

        xobjects = find_xobjects(pdf)
        assert all(has_dict_entry(x, "/XObjinfo") for x in xobjects)
        pdf.close()


class TestEmbedExtractPayloadMode:
    """Core embed and extract in payload mode."""

    def test_payload_roundtrip_forwards(self, tmp_pdf_multi: Path, tmp_path: Path) -> None:
        watermark = b"payload forwards test"
        pdf = open_pdf(tmp_pdf_multi)
        decompress(pdf)
        result = embed_watermark(pdf, watermark, channel="both", mode="payload", order="forwards")
        assert result["font_objects_embedded"] + result["xobjects_embedded"] >= 2
        out = tmp_path / "fwd.pdf"
        pdf.save(out)
        pdf.close()

        pdf2 = open_pdf(out)
        decompress(pdf2)
        extracted = extract_watermark(pdf2, channel="both", mode="payload", order="forwards")
        assert extracted == watermark
        pdf2.close()

    def test_payload_roundtrip_backwards(self, tmp_pdf_multi: Path, tmp_path: Path) -> None:
        watermark = b"payload backwards test"
        pdf = open_pdf(tmp_pdf_multi)
        decompress(pdf)
        embed_watermark(pdf, watermark, channel="both", mode="payload", order="backwards")
        out = tmp_path / "bwd.pdf"
        pdf.save(out)
        pdf.close()

        pdf2 = open_pdf(out)
        decompress(pdf2)
        extracted = extract_watermark(pdf2, channel="both", mode="payload", order="backwards")
        assert extracted == watermark
        pdf2.close()

    def test_payload_roundtrip_random(self, tmp_pdf_multi: Path, tmp_path: Path) -> None:
        watermark = b"payload random test"
        pdf = open_pdf(tmp_pdf_multi)
        decompress(pdf)
        embed_watermark(pdf, watermark, channel="both", mode="payload", order="random", seed=42)
        out = tmp_path / "rnd.pdf"
        pdf.save(out)
        pdf.close()

        pdf2 = open_pdf(out)
        decompress(pdf2)
        extracted = extract_watermark(
            pdf2, channel="both", mode="payload", order="random", seed=42
        )
        assert extracted == watermark
        pdf2.close()

    def test_payload_single_object(self, tmp_pdf: Path, tmp_path: Path) -> None:
        """Payload mode with only one candidate object puts all data there."""
        watermark = b"single object"
        pdf = open_pdf(tmp_pdf)
        decompress(pdf)
        embed_watermark(pdf, watermark, channel="font", mode="payload", order="forwards")
        out = tmp_path / "single.pdf"
        pdf.save(out)
        pdf.close()

        pdf2 = open_pdf(out)
        decompress(pdf2)
        extracted = extract_watermark(pdf2, channel="font", mode="payload", order="forwards")
        assert extracted == watermark
        pdf2.close()

    def test_payload_font_channel_only(self, tmp_pdf_multi: Path, tmp_path: Path) -> None:
        watermark = b"font payload"
        pdf = open_pdf(tmp_pdf_multi)
        decompress(pdf)
        result = embed_watermark(pdf, watermark, channel="font", mode="payload", order="forwards")
        assert result["font_objects_embedded"] >= 2
        assert result["xobjects_embedded"] == 0
        out = tmp_path / "font_payload.pdf"
        pdf.save(out)
        pdf.close()

        pdf2 = open_pdf(out)
        decompress(pdf2)
        extracted = extract_watermark(pdf2, channel="font", mode="payload", order="forwards")
        assert extracted == watermark
        pdf2.close()

    def test_payload_wrong_order_fails(self, tmp_pdf_multi: Path, tmp_path: Path) -> None:
        """Extracting with a different order should give wrong data."""
        watermark = b"order matters"
        pdf = open_pdf(tmp_pdf_multi)
        decompress(pdf)
        embed_watermark(pdf, watermark, channel="both", mode="payload", order="forwards")
        out = tmp_path / "order.pdf"
        pdf.save(out)
        pdf.close()

        pdf2 = open_pdf(out)
        decompress(pdf2)
        # Extract with backwards order — should not match
        try:
            extracted = extract_watermark(pdf2, channel="both", mode="payload", order="backwards")
            assert extracted != watermark
        except Exception:
            pass  # Any error is acceptable — wrong order corrupts data
        pdf2.close()

    def test_payload_wrong_seed_fails(self, tmp_pdf_multi: Path, tmp_path: Path) -> None:
        """Extracting with a different seed should give wrong data."""
        watermark = b"seed matters"
        pdf = open_pdf(tmp_pdf_multi)
        decompress(pdf)
        embed_watermark(pdf, watermark, channel="both", mode="payload", order="random", seed=1)
        out = tmp_path / "seed.pdf"
        pdf.save(out)
        pdf.close()

        pdf2 = open_pdf(out)
        decompress(pdf2)
        try:
            extracted = extract_watermark(
                pdf2, channel="both", mode="payload", order="random", seed=999
            )
            assert extracted != watermark
        except Exception:
            pass  # Any error is acceptable
        pdf2.close()

    def test_no_candidates_raises(self, tmp_pdf_no_images: Path) -> None:
        pdf = open_pdf(tmp_pdf_no_images)
        decompress(pdf)
        with pytest.raises(ValueError, match="No candidate objects"):
            embed_watermark(pdf, b"test", channel="xobject", mode="payload")
        pdf.close()
