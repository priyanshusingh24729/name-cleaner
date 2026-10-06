"""Unit tests for HTML content and product title extraction."""

import pytest
from crawler.extractor import ContentExtractor


@pytest.fixture
def extractor():
    return ContentExtractor()


@pytest.mark.parametrize(
    "raw_title, expected_clean",
    [
        ("AutoCAD | 2D & 3D CAD Software | Autodesk", "AutoCAD"),
        ("Liquid XML Studio - Free Download", "Liquid XML Studio"),
        ("Prion · GitHub", "Prion"),
        ("MapToaster Topo/NZ :: Official Site", "MapToaster Topo/NZ"),
        ("Adobe Photoshop - Download Free Software", "Adobe Photoshop"),
    ],
)
def test_clean_title_boilerplate_stripping(extractor, raw_title, expected_clean):
    """Verify common SEO boilerplate is cleanly stripped from page titles."""
    assert extractor.clean_title(raw_title) == expected_clean


def test_html_metadata_extraction(extractor):
    """Verify extraction of application name meta tag and text summaries."""
    html = """
    <!DOCTYPE html>
    <html>
        <head>
            <title>Liquid Studio - Comprehensive XML Development</title>
            <meta name="application-name" content="Liquid Studio">
            <meta name="description" content="Advanced graphical XML editor and data mapper.">
        </head>
        <body>
            <h1>Liquid Studio</h1>
            <p>Liquid Studio is an advanced graphical XML editor, XSD editor, and data mapper.</p>
        </body>
    </html>
    """
    data = extractor.extract(html)
    assert data["application_name"] == "Liquid Studio"
    assert "Liquid Studio" in data["clean_title"]
    assert "Advanced graphical XML editor" in data["text_summary"]
