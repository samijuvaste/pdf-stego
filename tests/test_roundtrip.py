"""End-to-end roundtrip tests through the high-level API."""

from __future__ import annotations

from pathlib import Path

import pytest

from pdf_stego.api import embed, extract, info

# ---------------------------------------------------------------------------
# Watermark mode roundtrips (backward compatibility)
# ---------------------------------------------------------------------------


class TestRoundtripWatermarkMode:
    """Embed → extract roundtrip in watermark mode (original behaviour)."""

    def test_basic_roundtrip(self, tmp_pdf: Path, tmp_path: Path) -> None:
        out = tmp_path / "wm.pdf"
        embed(tmp_pdf, out, "hello world", mode="watermark")
        extracted = extract(out, mode="watermark")
        assert extracted == b"hello world"

    def test_roundtrip_bytes(self, tmp_pdf: Path, tmp_path: Path) -> None:
        out = tmp_path / "wm.pdf"
        data = bytes(range(256))
        embed(tmp_pdf, out, data, mode="watermark")
        extracted = extract(out, mode="watermark")
        assert extracted == data

    def test_roundtrip_file_input(self, tmp_pdf: Path, tmp_path: Path) -> None:
        wm_file = tmp_path / "watermark.bin"
        wm_file.write_bytes(b"file-based watermark")
        out = tmp_path / "wm.pdf"
        embed(tmp_pdf, out, wm_file, mode="watermark")
        extracted = extract(out, mode="watermark")
        assert extracted == b"file-based watermark"

    def test_roundtrip_font_only(self, tmp_pdf: Path, tmp_path: Path) -> None:
        out = tmp_path / "wm.pdf"
        embed(tmp_pdf, out, "font only", channel="font", mode="watermark")
        extracted = extract(out, channel="font", mode="watermark")
        assert extracted == b"font only"

    def test_roundtrip_xobject_only(self, tmp_pdf: Path, tmp_path: Path) -> None:
        out = tmp_path / "wm.pdf"
        embed(tmp_pdf, out, "xobj only", channel="xobject", mode="watermark")
        extracted = extract(out, channel="xobject", mode="watermark")
        assert extracted == b"xobj only"


# ---------------------------------------------------------------------------
# Payload mode roundtrips (new default)
# ---------------------------------------------------------------------------


class TestRoundtripPayloadMode:
    """Embed → extract roundtrip in payload mode (default)."""

    def test_basic_roundtrip_default(self, tmp_pdf: Path, tmp_path: Path) -> None:
        """Default mode (payload) with default order (random) and seed (0)."""
        out = tmp_path / "pl.pdf"
        embed(tmp_pdf, out, "hello payload")
        extracted = extract(out)
        assert extracted == b"hello payload"

    def test_roundtrip_forwards(self, tmp_pdf_multi: Path, tmp_path: Path) -> None:
        out = tmp_path / "fwd.pdf"
        embed(tmp_pdf_multi, out, "forwards test", mode="payload", order="forwards")
        extracted = extract(out, mode="payload", order="forwards")
        assert extracted == b"forwards test"

    def test_roundtrip_backwards(self, tmp_pdf_multi: Path, tmp_path: Path) -> None:
        out = tmp_path / "bwd.pdf"
        embed(tmp_pdf_multi, out, "backwards test", mode="payload", order="backwards")
        extracted = extract(out, mode="payload", order="backwards")
        assert extracted == b"backwards test"

    def test_roundtrip_random_seed(self, tmp_pdf_multi: Path, tmp_path: Path) -> None:
        out = tmp_path / "rnd.pdf"
        embed(tmp_pdf_multi, out, "random seed 42", mode="payload", order="random", seed=42)
        extracted = extract(out, mode="payload", order="random", seed=42)
        assert extracted == b"random seed 42"

    def test_payload_with_aes(self, tmp_pdf_multi: Path, tmp_path: Path) -> None:
        out = tmp_path / "aes_payload.pdf"
        embed(
            tmp_pdf_multi,
            out,
            "aes payload test",
            mode="payload",
            order="forwards",
            encryption="aes",
            encryption_key="secret",
        )
        extracted = extract(
            out,
            mode="payload",
            order="forwards",
            encryption="aes",
            encryption_key="secret",
        )
        assert extracted == b"aes payload test"

    def test_mismatched_order_fails(self, tmp_pdf_multi: Path, tmp_path: Path) -> None:
        out = tmp_path / "mismatch.pdf"
        embed(tmp_pdf_multi, out, "order mismatch", mode="payload", order="forwards")
        try:
            extracted = extract(out, mode="payload", order="backwards")
            assert extracted != b"order mismatch"
        except Exception:
            pass  # Any error is acceptable

    def test_result_includes_mode(self, tmp_pdf: Path, tmp_path: Path) -> None:
        out = tmp_path / "mode.pdf"
        result = embed(tmp_pdf, out, "mode check")
        assert result["mode"] == "payload"


# ---------------------------------------------------------------------------
# AES roundtrips (mode-agnostic — kept in watermark mode for stability)
# ---------------------------------------------------------------------------


class TestRoundtripAes:
    """Embed → extract roundtrip with AES encryption."""

    def test_aes_roundtrip(self, tmp_pdf: Path, tmp_path: Path) -> None:
        out = tmp_path / "aes.pdf"
        embed(
            tmp_pdf, out, "aes test", encryption="aes", encryption_key="secret", mode="watermark"
        )
        extracted = extract(out, encryption="aes", encryption_key="secret", mode="watermark")
        assert extracted == b"aes test"

    def test_aes_wrong_key_fails(self, tmp_pdf: Path, tmp_path: Path) -> None:
        out = tmp_path / "aes.pdf"
        embed(
            tmp_pdf, out, "aes test", encryption="aes", encryption_key="correct", mode="watermark"
        )
        with pytest.raises(Exception, match=r".*"):
            extract(out, encryption="aes", encryption_key="wrong", mode="watermark")


class TestRoundtripCustomKeys:
    """Embed → extract with custom dictionary entry keys."""

    def test_custom_keys(self, tmp_pdf: Path, tmp_path: Path) -> None:
        out = tmp_path / "custom.pdf"
        embed(
            tmp_pdf,
            out,
            "custom",
            font_dict_key="/MyFont",
            xobj_dict_key="/MyXObj",
            mode="watermark",
        )
        extracted = extract(
            out,
            font_dict_key="/MyFont",
            xobj_dict_key="/MyXObj",
            mode="watermark",
        )
        assert extracted == b"custom"


class TestInfo:
    """Info command tests."""

    def test_info_plain(self, tmp_pdf: Path) -> None:
        result = info(tmp_pdf)
        assert result["font_objects"] >= 1
        assert result["font_watermarked"] == 0
        assert result["xobj_watermarked"] == 0

    def test_info_after_embed(self, tmp_pdf: Path, tmp_path: Path) -> None:
        out = tmp_path / "wm.pdf"
        embed(tmp_pdf, out, "test", mode="watermark")
        result = info(out)
        assert result["font_watermarked"] >= 1
        assert result["xobj_watermarked"] >= 1


class TestOutputFile:
    """Test writing extracted watermark to file."""

    def test_extract_to_file(self, tmp_pdf: Path, tmp_path: Path) -> None:
        wm_pdf = tmp_path / "wm.pdf"
        embed(tmp_pdf, wm_pdf, "file output test", mode="watermark")
        out_file = tmp_path / "extracted.txt"
        extract(wm_pdf, output=out_file, mode="watermark")
        assert out_file.read_bytes() == b"file output test"


class TestErrorHandling:
    """Error handling tests."""

    def test_encryption_without_key(self, tmp_pdf: Path, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="encryption_key is required"):
            embed(tmp_pdf, tmp_path / "out.pdf", "test", encryption="aes")

    def test_xobject_channel_on_text_only(self, tmp_pdf_no_images: Path, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="No candidate objects"):
            embed(tmp_pdf_no_images, tmp_path / "out.pdf", "test", channel="xobject")
