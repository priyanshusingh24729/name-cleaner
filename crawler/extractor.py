"""HTML content extractor for product titles, metadata, and body summaries."""

import re
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
from app.text_cleaner import clean_text

# Delimiters separating title segments (pipes, double colons, bullet/middle dots, spaced dashes/slashes)
TITLE_DELIMITERS = re.compile(r"\s*(?:\||::|[\u00b7\u2022]|\s[-–—/]\s)\s*")

# Segments that are purely boilerplate, marketing taglines, or platform/vendor names
BOILERPLATE_SEGMENT = re.compile(
    r"^(?:"
    r"official\s+(?:site|website|home|store|portal|page)|"
    r"(?:free\s+)?download(?:\s+free)?(?:\s+software)?|"
    r"features(?:\s+&\s+benefits)?|"
    r"overview|"
    r"pricing|"
    r"documentation|"
    r"docs|"
    r"learn|"
    r"home(?:page)?|"
    r"github|"
    r"gitlab|"
    r"pypi|"
    r"nuget|"
    r"sourceforge|"
    r"cnet(?:\s+download)?|"
    r"softpedia|"
    r"wikipedia|"
    r"autodesk|"
    r"adobe|"
    r"jetbrains|"
    r"oracle|"
    r"microsoft(?:\s+(?:learn|docs|store))?|"
    r".*\bcad(?:\s+design)?\s+software\b.*|"
    r".*\bfree\s+software\b.*"
    r")$",
    re.IGNORECASE,
)


class ContentExtractor:
    """Extracts clean product titles, application metadata, and text summaries from HTML."""

    @classmethod
    def clean_title(cls, title: str) -> str:
        """Strip SEO boilerplate, taglines, and website branding from page title."""
        if not title:
            return ""
        cleaned = clean_text(title)

        # Split title on common structural delimiters
        segments = [s.strip() for s in TITLE_DELIMITERS.split(cleaned) if s.strip()]
        if not segments:
            return cleaned

        # Identify candidate segment that is not pure boilerplate or platform name
        chosen = None
        for seg in segments:
            if not BOILERPLATE_SEGMENT.match(seg):
                chosen = seg
                break

        if not chosen:
            chosen = segments[0]

        # Strip common leading action words (e.g. 'Download AutoCAD' -> 'AutoCAD')
        chosen = re.sub(r"^(?:download|free\s+download|get|buy)\s+", "", chosen, flags=re.IGNORECASE).strip()
        # Strip trailing boilerplate if attached without delimiters
        chosen = re.sub(r"\s+(?:official\s+(?:site|website)|free\s+download|download)$", "", chosen, flags=re.IGNORECASE).strip()
        # Clean any trailing separators
        chosen = re.sub(r"[\s\-–—:;,._/|\\]+$", "", chosen).strip()
        return chosen

    def extract(self, html_content: str, url: Optional[str] = None) -> Dict[str, Any]:
        """Parse HTML and extract title, application name, and text summary."""
        if not html_content:
            return {
                "raw_title": "",
                "clean_title": "",
                "application_name": "",
                "text_summary": "",
            }

        soup = BeautifulSoup(html_content, "html.parser")

        # 1. Extract raw title
        raw_title = ""
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            raw_title = og_title["content"].strip()
        elif soup.title and soup.title.string:
            raw_title = soup.title.string.strip()
        else:
            h1 = soup.find("h1")
            if h1:
                raw_title = h1.get_text(strip=True)

        clean_title = self.clean_title(raw_title)

        # 2. Extract application-name meta tag if present
        app_name = ""
        meta_app = soup.find("meta", attrs={"name": "application-name"})
        if meta_app and meta_app.get("content"):
            app_name = clean_text(meta_app["content"])
        else:
            og_site = soup.find("meta", property="og:site_name")
            if og_site and og_site.get("content"):
                app_name = clean_text(og_site["content"])

        # 3. Extract text summary (paragraphs or meta description)
        text_summary = ""
        meta_desc = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", property="og:description")
        if meta_desc and meta_desc.get("content"):
            text_summary = clean_text(meta_desc["content"])
        else:
            # Gather first few paragraphs
            paragraphs = [p.get_text(strip=True) for p in soup.find_all("p") if len(p.get_text(strip=True)) > 20]
            if paragraphs:
                text_summary = clean_text(" ".join(paragraphs[:3]))

        if len(text_summary) > 500:
            text_summary = text_summary[:497] + "..."

        return {
            "raw_title": raw_title,
            "clean_title": clean_title,
            "application_name": app_name,
            "text_summary": text_summary,
        }
