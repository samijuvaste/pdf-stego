"""CLI interface for PDF steganography.

Usage:
    pdf-stego embed   -i input.pdf -o output.pdf -m "watermark text"
    pdf-stego embed   -i input.pdf -o output.pdf -f watermark.bin --encryption aes --key "secret"
    pdf-stego extract -i watermarked.pdf
    pdf-stego info    -i document.pdf
"""

from __future__ import annotations

from pathlib import Path
import sys

import click

from pdf_stego.api import embed, extract, info


@click.group()
def cli() -> None:
    """PDF Steganography — embed and extract watermarks in PDF files."""


# ---------------------------------------------------------------------------
# Embed
# ---------------------------------------------------------------------------


@cli.command()
@click.option(
    "-i",
    "--input",
    "input_pdf",
    required=True,
    type=click.Path(exists=True),
    help="Path to the cover PDF.",
)
@click.option(
    "-o",
    "--output",
    "output_pdf",
    required=True,
    type=click.Path(),
    help="Path to save the watermarked PDF.",
)
@click.option("-m", "--message", default=None, type=str, help="Watermark string to embed.")
@click.option(
    "-f",
    "--file",
    "message_file",
    default=None,
    type=click.Path(exists=True),
    help="Path to file containing the watermark data to embed.",
)
@click.option(
    "-c",
    "--channel",
    default="both",
    type=click.Choice(["font", "xobject", "both"]),
    help="Embedding channel (default: both).",
)
@click.option(
    "--encryption",
    default="none",
    type=click.Choice(["none", "aes"]),
    help="Watermark encryption method (default: none).",
)
@click.option("--key", default=None, type=str, help="Encryption key/passphrase.")
@click.option(
    "--font-key",
    default="/Fontinfo",
    type=str,
    help="Custom font dict entry key (default: /Fontinfo).",
)
@click.option(
    "--xobj-key",
    default="/XObjinfo",
    type=str,
    help="Custom XObject entry key (default: /XObjinfo).",
)
@click.option(
    "--mode",
    default="payload",
    type=click.Choice(["payload", "watermark"]),
    help="Operation mode (default: payload).",
)
@click.option(
    "--order",
    default="random",
    type=click.Choice(["forwards", "backwards", "random"]),
    help="Insertion order for payload mode (default: random).",
)
@click.option(
    "--seed",
    default=0,
    type=int,
    help="RNG seed for random insertion order (default: 0).",
)
def embed_cmd(
    input_pdf: str,
    output_pdf: str,
    message: str | None,
    message_file: str | None,
    channel: str,
    encryption: str,
    key: str | None,
    font_key: str,
    xobj_key: str,
    mode: str,
    order: str,
    seed: int,
) -> None:
    """Embed a watermark into a PDF file."""
    if message is None and message_file is None:
        raise click.UsageError("Either -m/--message or -f/--file is required.")
    if message is not None and message_file is not None:
        raise click.UsageError("-m/--message and -f/--file are mutually exclusive.")

    msg_input = message if message is not None else Path(message_file)  # type: ignore[arg-type]

    try:
        result = embed(
            input_pdf=input_pdf,
            output_pdf=output_pdf,
            watermark=msg_input,
            channel=channel,  # type: ignore[arg-type]
            encryption=encryption,  # type: ignore[arg-type]
            encryption_key=key,
            font_dict_key=font_key,
            xobj_dict_key=xobj_key,
            mode=mode,  # type: ignore[arg-type]
            order=order,  # type: ignore[arg-type]
            seed=seed,
        )
        click.echo(
            f"Embedded watermark ({result['watermark_bytes']} bytes) into {output_pdf}\n"
            f"  Mode:         {result['mode']}\n"
            f"  Font objects: {result['font_objects_embedded']}\n"
            f"  XObjects:     {result['xobjects_embedded']}\n"
            f"  Encryption:   {result['encryption']}"
        )
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Extract
# ---------------------------------------------------------------------------


@cli.command()
@click.option(
    "-i",
    "--input",
    "input_pdf",
    required=True,
    type=click.Path(exists=True),
    help="Path to the watermarked PDF.",
)
@click.option(
    "-o",
    "--output",
    default=None,
    type=click.Path(),
    help="Path to save extracted watermark data (default: stdout).",
)
@click.option(
    "-c",
    "--channel",
    default="both",
    type=click.Choice(["font", "xobject", "both"]),
    help="Extraction channel (default: both).",
)
@click.option(
    "--encryption",
    default="none",
    type=click.Choice(["none", "aes"]),
    help="Decryption method (must match embed; default: none).",
)
@click.option("--key", default=None, type=str, help="Decryption key/passphrase.")
@click.option("--font-key", default="/Fontinfo", type=str, help="Font dict entry key.")
@click.option("--xobj-key", default="/XObjinfo", type=str, help="XObject entry key.")
@click.option(
    "--mode",
    default="payload",
    type=click.Choice(["payload", "watermark"]),
    help="Operation mode (default: payload).",
)
@click.option(
    "--order",
    default="random",
    type=click.Choice(["forwards", "backwards", "random"]),
    help="Insertion order for payload mode (default: random).",
)
@click.option(
    "--seed",
    default=0,
    type=int,
    help="RNG seed for random insertion order (default: 0).",
)
def extract_cmd(
    input_pdf: str,
    output: str | None,
    channel: str,
    encryption: str,
    key: str | None,
    font_key: str,
    xobj_key: str,
    mode: str,
    order: str,
    seed: int,
) -> None:
    """Extract a watermark from a PDF file."""
    try:
        data = extract(
            input_pdf=input_pdf,
            output=output,
            channel=channel,  # type: ignore[arg-type]
            encryption=encryption,  # type: ignore[arg-type]
            encryption_key=key,
            font_dict_key=font_key,
            xobj_dict_key=xobj_key,
            mode=mode,  # type: ignore[arg-type]
            order=order,  # type: ignore[arg-type]
            seed=seed,
        )
        if output is not None:
            click.echo(f"Extracted {len(data)} bytes to {output}")
        else:
            # Try to decode as UTF-8 text, fall back to hex
            try:
                click.echo(data.decode("utf-8"))
            except UnicodeDecodeError:
                click.echo(data.hex())
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Info
# ---------------------------------------------------------------------------


@cli.command()
@click.option(
    "-i",
    "--input",
    "input_pdf",
    required=True,
    type=click.Path(exists=True),
    help="Path to a PDF file.",
)
@click.option(
    "--font-key",
    default="/Fontinfo",
    type=str,
    help="Custom font dict entry key (default: /Fontinfo).",
)
@click.option(
    "--xobj-key",
    default="/XObjinfo",
    type=str,
    help="Custom XObject entry key (default: /XObjinfo).",
)
def info_cmd(input_pdf: str, font_key: str, xobj_key: str) -> None:
    """Show object counts and watermark status of a PDF."""
    try:
        result = info(input_pdf, font_dict_key=font_key, xobj_dict_key=xobj_key)
        click.echo(
            f"Font Dictionary Objects: {result['font_objects']}"
            f" ({result['font_watermarked']} watermarked)\n"
            f"XObjects:               {result['xobjects']}"
            f" ({result['xobj_watermarked']} watermarked)"
        )
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
