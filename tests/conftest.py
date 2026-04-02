"""Shared test fixtures for pdf-stego tests."""

from __future__ import annotations

from pathlib import Path

import pikepdf
import pytest


@pytest.fixture
def tmp_pdf(tmp_path: Path) -> Path:
    """Create a simple PDF with text and an image for testing.

    The PDF has:
    - One page with a font (generates a Font Dictionary Object)
    - One small image XObject (generates an Image XObject)
    """
    pdf = pikepdf.Pdf.new()

    # Create a page with a font reference
    page = pikepdf.Dictionary(
        Type=pikepdf.Name.Page,
        MediaBox=[0, 0, 612, 792],
    )

    # Create a simple font dictionary (Type 1 font)
    font = pdf.make_indirect(
        pikepdf.Dictionary(
            Type=pikepdf.Name.Font,
            Subtype=pikepdf.Name.Type1,
            BaseFont=pikepdf.Name.Helvetica,
        )
    )

    # Create a minimal 2x2 RGB image XObject
    image_data = bytes([255, 0, 0, 0, 255, 0, 0, 0, 255, 255, 255, 0])  # 4 RGB pixels
    image_stream = pikepdf.Stream(pdf, image_data)
    image_stream[pikepdf.Name.Type] = pikepdf.Name.XObject
    image_stream[pikepdf.Name.Subtype] = pikepdf.Name.Image
    image_stream[pikepdf.Name.Width] = 2
    image_stream[pikepdf.Name.Height] = 2
    image_stream[pikepdf.Name.ColorSpace] = pikepdf.Name.DeviceRGB
    image_stream[pikepdf.Name.BitsPerComponent] = 8
    image_xobj = pdf.make_indirect(image_stream)

    # Set up resources
    resources = pikepdf.Dictionary(
        Font=pikepdf.Dictionary(F1=font),
        XObject=pikepdf.Dictionary(Im1=image_xobj),
    )
    page[pikepdf.Name.Resources] = resources

    # Add a simple content stream that uses the font
    content = b"BT /F1 12 Tf 100 700 Td (Hello World) Tj ET"
    page[pikepdf.Name.Contents] = pikepdf.Stream(pdf, content)

    pdf.pages.append(pikepdf.Page(page))

    output = tmp_path / "test.pdf"
    pdf.save(output)
    pdf.close()
    return output


@pytest.fixture
def tmp_pdf_no_images(tmp_path: Path) -> Path:
    """Create a PDF that has fonts but no image XObjects."""
    pdf = pikepdf.Pdf.new()
    page = pikepdf.Dictionary(
        Type=pikepdf.Name.Page,
        MediaBox=[0, 0, 612, 792],
    )

    font = pdf.make_indirect(
        pikepdf.Dictionary(
            Type=pikepdf.Name.Font,
            Subtype=pikepdf.Name.Type1,
            BaseFont=pikepdf.Name.Courier,
        )
    )

    resources = pikepdf.Dictionary(Font=pikepdf.Dictionary(F1=font))
    page[pikepdf.Name.Resources] = resources

    content = b"BT /F1 10 Tf 100 700 Td (Text only) Tj ET"
    page[pikepdf.Name.Contents] = pikepdf.Stream(pdf, content)

    pdf.pages.append(pikepdf.Page(page))

    output = tmp_path / "text_only.pdf"
    pdf.save(output)
    pdf.close()
    return output


@pytest.fixture
def tmp_pdf_multi(tmp_path: Path) -> Path:
    """Create a PDF with multiple fonts and XObjects for payload splitting tests.

    The PDF has 3 fonts and 2 image XObjects across 2 pages (5 total candidates).
    """
    pdf = pikepdf.Pdf.new()

    # --- Page 1: 2 fonts + 1 image ---
    page1 = pikepdf.Dictionary(
        Type=pikepdf.Name.Page,
        MediaBox=[0, 0, 612, 792],
    )

    font1 = pdf.make_indirect(
        pikepdf.Dictionary(
            Type=pikepdf.Name.Font,
            Subtype=pikepdf.Name.Type1,
            BaseFont=pikepdf.Name.Helvetica,
        )
    )
    font2 = pdf.make_indirect(
        pikepdf.Dictionary(
            Type=pikepdf.Name.Font,
            Subtype=pikepdf.Name.Type1,
            BaseFont=pikepdf.Name.Courier,
        )
    )

    img1_data = bytes([255, 0, 0, 0, 255, 0, 0, 0, 255, 255, 255, 0])
    img1_stream = pikepdf.Stream(pdf, img1_data)
    img1_stream[pikepdf.Name.Type] = pikepdf.Name.XObject
    img1_stream[pikepdf.Name.Subtype] = pikepdf.Name.Image
    img1_stream[pikepdf.Name.Width] = 2
    img1_stream[pikepdf.Name.Height] = 2
    img1_stream[pikepdf.Name.ColorSpace] = pikepdf.Name.DeviceRGB
    img1_stream[pikepdf.Name.BitsPerComponent] = 8
    img1_xobj = pdf.make_indirect(img1_stream)

    resources1 = pikepdf.Dictionary(
        Font=pikepdf.Dictionary(F1=font1, F2=font2),
        XObject=pikepdf.Dictionary(Im1=img1_xobj),
    )
    page1[pikepdf.Name.Resources] = resources1

    content1 = b"BT /F1 12 Tf 100 700 Td (Page 1) Tj ET"
    page1[pikepdf.Name.Contents] = pikepdf.Stream(pdf, content1)

    pdf.pages.append(pikepdf.Page(page1))

    # --- Page 2: 1 font + 1 image ---
    page2 = pikepdf.Dictionary(
        Type=pikepdf.Name.Page,
        MediaBox=[0, 0, 612, 792],
    )

    font3 = pdf.make_indirect(
        pikepdf.Dictionary(
            Type=pikepdf.Name.Font,
            Subtype=pikepdf.Name.Type1,
            BaseFont=pikepdf.Name.Symbol,
        )
    )

    img2_data = bytes([0, 0, 255, 255, 0, 255, 128, 128, 128, 64, 64, 64])
    img2_stream = pikepdf.Stream(pdf, img2_data)
    img2_stream[pikepdf.Name.Type] = pikepdf.Name.XObject
    img2_stream[pikepdf.Name.Subtype] = pikepdf.Name.Image
    img2_stream[pikepdf.Name.Width] = 2
    img2_stream[pikepdf.Name.Height] = 2
    img2_stream[pikepdf.Name.ColorSpace] = pikepdf.Name.DeviceRGB
    img2_stream[pikepdf.Name.BitsPerComponent] = 8
    img2_xobj = pdf.make_indirect(img2_stream)

    resources2 = pikepdf.Dictionary(
        Font=pikepdf.Dictionary(F3=font3),
        XObject=pikepdf.Dictionary(Im2=img2_xobj),
    )
    page2[pikepdf.Name.Resources] = resources2

    content2 = b"BT /F3 10 Tf 100 700 Td (Page 2) Tj ET"
    page2[pikepdf.Name.Contents] = pikepdf.Stream(pdf, content2)

    pdf.pages.append(pikepdf.Page(page2))

    output = tmp_path / "multi.pdf"
    pdf.save(output)
    pdf.close()
    return output
