"""CLI smoke tests using Click's CliRunner."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from pdf_stego.cli import cli


class TestEmbedExtractCli:
    """CLI embed → extract roundtrip."""

    def test_embed_and_extract_message_watermark(self, tmp_pdf: Path, tmp_path: Path) -> None:
        runner = CliRunner()
        out = tmp_path / "wm.pdf"

        # Embed in watermark mode
        result = runner.invoke(
            cli,
            [
                "embed",
                "-i",
                str(tmp_pdf),
                "-o",
                str(out),
                "-m",
                "cli test",
                "--mode",
                "watermark",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "Embedded watermark" in result.output

        # Extract in watermark mode
        result = runner.invoke(
            cli,
            ["extract", "-i", str(out), "--mode", "watermark"],
        )
        assert result.exit_code == 0, result.output
        assert "cli test" in result.output

    def test_embed_and_extract_payload_default(self, tmp_pdf: Path, tmp_path: Path) -> None:
        """Default mode (payload) roundtrip via CLI."""
        runner = CliRunner()
        out = tmp_path / "pl.pdf"

        result = runner.invoke(
            cli,
            ["embed", "-i", str(tmp_pdf), "-o", str(out), "-m", "payload default"],
        )
        assert result.exit_code == 0, result.output
        assert "payload" in result.output  # mode shown in output

        result = runner.invoke(
            cli,
            ["extract", "-i", str(out)],
        )
        assert result.exit_code == 0, result.output
        assert "payload default" in result.output

    def test_embed_and_extract_payload_with_options(self, tmp_pdf: Path, tmp_path: Path) -> None:
        runner = CliRunner()
        out = tmp_path / "opts.pdf"

        result = runner.invoke(
            cli,
            [
                "embed",
                "-i",
                str(tmp_pdf),
                "-o",
                str(out),
                "-m",
                "opts test",
                "--mode",
                "payload",
                "--order",
                "forwards",
                "--seed",
                "42",
            ],
        )
        assert result.exit_code == 0, result.output

        result = runner.invoke(
            cli,
            [
                "extract",
                "-i",
                str(out),
                "--mode",
                "payload",
                "--order",
                "forwards",
                "--seed",
                "42",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "opts test" in result.output

    def test_embed_from_file(self, tmp_pdf: Path, tmp_path: Path) -> None:
        runner = CliRunner()
        wm_file = tmp_path / "wm.txt"
        wm_file.write_text("watermark from file")
        out = tmp_path / "wm.pdf"

        result = runner.invoke(
            cli,
            [
                "embed",
                "-i",
                str(tmp_pdf),
                "-o",
                str(out),
                "-f",
                str(wm_file),
                "--mode",
                "watermark",
            ],
        )
        assert result.exit_code == 0, result.output

        result = runner.invoke(cli, ["extract", "-i", str(out), "--mode", "watermark"])
        assert result.exit_code == 0, result.output
        assert "watermark from file" in result.output

    def test_embed_with_aes(self, tmp_pdf: Path, tmp_path: Path) -> None:
        runner = CliRunner()
        out = tmp_path / "aes.pdf"

        result = runner.invoke(
            cli,
            [
                "embed",
                "-i",
                str(tmp_pdf),
                "-o",
                str(out),
                "-m",
                "aes cli",
                "--encryption",
                "aes",
                "--key",
                "pass",
                "--mode",
                "watermark",
            ],
        )
        assert result.exit_code == 0, result.output

        result = runner.invoke(
            cli,
            [
                "extract",
                "-i",
                str(out),
                "--encryption",
                "aes",
                "--key",
                "pass",
                "--mode",
                "watermark",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "aes cli" in result.output

    def test_extract_to_file(self, tmp_pdf: Path, tmp_path: Path) -> None:
        runner = CliRunner()
        wm_pdf = tmp_path / "wm.pdf"
        out_file = tmp_path / "out.txt"

        runner.invoke(
            cli,
            [
                "embed",
                "-i",
                str(tmp_pdf),
                "-o",
                str(wm_pdf),
                "-m",
                "save to file",
                "--mode",
                "watermark",
            ],
        )
        result = runner.invoke(
            cli,
            ["extract", "-i", str(wm_pdf), "-o", str(out_file), "--mode", "watermark"],
        )
        assert result.exit_code == 0, result.output
        assert "Extracted" in result.output
        assert out_file.read_bytes() == b"save to file"

    def test_channel_option(self, tmp_pdf: Path, tmp_path: Path) -> None:
        runner = CliRunner()
        out = tmp_path / "font.pdf"

        result = runner.invoke(
            cli,
            [
                "embed",
                "-i",
                str(tmp_pdf),
                "-o",
                str(out),
                "-m",
                "font only",
                "-c",
                "font",
                "--mode",
                "watermark",
            ],
        )
        assert result.exit_code == 0, result.output


class TestInfoCli:
    """CLI info command tests."""

    def test_info_output(self, tmp_pdf: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["info", "-i", str(tmp_pdf)])
        assert result.exit_code == 0, result.output
        assert "Font Dictionary Objects" in result.output
        assert "XObjects" in result.output


class TestCliErrors:
    """CLI error handling."""

    def test_embed_no_message(self, tmp_pdf: Path, tmp_path: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["embed", "-i", str(tmp_pdf), "-o", str(tmp_path / "out.pdf")],
        )
        assert result.exit_code != 0

    def test_embed_both_message_and_file(self, tmp_pdf: Path, tmp_path: Path) -> None:
        runner = CliRunner()
        wm = tmp_path / "wm.txt"
        wm.write_text("x")
        result = runner.invoke(
            cli,
            [
                "embed",
                "-i",
                str(tmp_pdf),
                "-o",
                str(tmp_path / "out.pdf"),
                "-m",
                "text",
                "-f",
                str(wm),
            ],
        )
        assert result.exit_code != 0
