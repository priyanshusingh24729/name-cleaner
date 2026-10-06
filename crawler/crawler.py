"""Web crawler for gathering canonical product evidence from search results."""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import httpx

from search.base import SearchResult
from crawler.official_source import OfficialSourceDetector
from crawler.extractor import ContentExtractor


@dataclass
class CrawlEvidence:
    """Structured evidence extracted from crawled web pages."""

    url: str
    domain: str
    is_official: bool
    authority_score: float
    raw_title: str
    clean_title: str
    application_name: str
    text_summary: str
    status_code: int = 200

    def to_dict(self) -> Dict[str, Any]:
        """Convert evidence to dictionary for auditing / downstream processing."""
        return {
            "url": self.url,
            "domain": self.domain,
            "is_official": self.is_official,
            "authority_score": round(self.authority_score, 2),
            "raw_title": self.raw_title,
            "clean_title": self.clean_title,
            "application_name": self.application_name,
            "text_summary": self.text_summary,
            "status_code": self.status_code,
        }

    def __str__(self) -> str:
        tag = "[OFFICIAL]" if self.is_official else "[THIRD-PARTY]"
        return f"{tag} {self.clean_title} ({self.domain} | score: {self.authority_score})"


class WebCrawler:
    """Crawls pages from search results, prioritizing high-authority official domains."""

    def __init__(
        self,
        timeout: float = 8.0,
        max_content_bytes: int = 2 * 1024 * 1024,  # 2MB max response
        user_agent: str = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 SoftwareNameNormalizer/1.0"
        ),
        client: Optional[httpx.Client] = None,
    ):
        self.timeout = timeout
        self.max_content_bytes = max_content_bytes
        self.user_agent = user_agent
        self._client = client

        self.source_detector = OfficialSourceDetector()
        self.extractor = ContentExtractor()

    def _get_client(self) -> httpx.Client:
        if self._client is not None:
            return self._client
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        return httpx.Client(timeout=self.timeout, headers=headers, follow_redirects=True)

    def crawl_page(
        self,
        url: str,
        vendor_hint: Optional[str] = None,
    ) -> Optional[CrawlEvidence]:
        """Fetch and extract evidence from a single web page."""
        if not url or not url.startswith(("http://", "https://")):
            return None

        domain = self.source_detector.extract_domain(url)
        is_official = self.source_detector.is_official_vendor(url, vendor_hint) or self.source_detector.is_package_repository(url)
        authority_score = self.source_detector.get_authority_score(url, vendor_hint)

        client = self._get_client()
        try:
            resp = client.get(url)
            if resp.status_code != 200:
                return CrawlEvidence(
                    url=url,
                    domain=domain,
                    is_official=is_official,
                    authority_score=authority_score,
                    raw_title="",
                    clean_title="",
                    application_name="",
                    text_summary="",
                    status_code=resp.status_code,
                )

            # Enforce content size limit
            content_type = resp.headers.get("content-type", "").lower()
            if "text/html" not in content_type and "application/xhtml" not in content_type:
                # Skip non-HTML files
                return None

            html_text = resp.text[: self.max_content_bytes]
            extracted = self.extractor.extract(html_text, url=url)

            return CrawlEvidence(
                url=str(resp.url),
                domain=domain,
                is_official=is_official,
                authority_score=authority_score,
                raw_title=extracted["raw_title"],
                clean_title=extracted["clean_title"],
                application_name=extracted["application_name"],
                text_summary=extracted["text_summary"],
                status_code=resp.status_code,
            )

        except Exception:
            # Handle timeouts, connection drops, SSL errors gracefully
            return None
        finally:
            if self._client is None:
                client.close()

    def crawl_results(
        self,
        search_results: List[SearchResult],
        vendor_hint: Optional[str] = None,
        max_pages: int = 3,
    ) -> List[CrawlEvidence]:
        """Crawl pages from search results, prioritizing highest-authority domains first."""
        if not search_results:
            return []

        # Sort search results by domain authority score (highest authority first)
        def score_result(res: SearchResult) -> float:
            return self.source_detector.get_authority_score(res.url, vendor_hint)

        sorted_results = sorted(search_results, key=score_result, reverse=True)

        evidence_list: List[CrawlEvidence] = []
        crawled_domains = set()

        for res in sorted_results:
            domain = self.source_detector.extract_domain(res.url)
            # Avoid crawling multiple pages from the exact same domain
            if domain in crawled_domains:
                continue

            evidence = self.crawl_page(res.url, vendor_hint=vendor_hint)
            if evidence and evidence.status_code == 200 and evidence.clean_title:
                evidence_list.append(evidence)
                crawled_domains.add(domain)

            if len(evidence_list) >= max_pages:
                break

        return evidence_list
