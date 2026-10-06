"""Official source detector and domain authority evaluator."""

from pathlib import Path
from typing import Optional, Set, List, Dict, Any
import urllib.parse
import re
import yaml


class OfficialSourceDetector:
    """Evaluates domain credibility, identifies official vendors, and scores authority."""

    def __init__(self, config_path: Optional[Path] = None):
        base_dir = Path(__file__).resolve().parent.parent
        self.config_path = config_path or base_dir / "config" / "official_domains.yaml"

        self.official_vendors: Set[str] = set()
        self.package_repositories: Set[str] = set()
        self.reputable_aggregators: Set[str] = set()
        self.authority_weights: Dict[str, float] = {
            "official_vendor": 1.0,
            "package_repository": 0.95,
            "reputable_aggregator": 0.70,
            "unknown_domain": 0.35,
        }
        self.official_paths: List[re.Pattern] = []

        self._load_config()

    def _load_config(self) -> None:
        """Load domain authority configuration from YAML."""
        if not self.config_path.exists():
            return

        with open(self.config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        self.official_vendors = {d.strip().lower() for d in data.get("official_vendors", []) if d}
        self.package_repositories = {d.strip().lower() for d in data.get("package_repositories", []) if d}
        self.reputable_aggregators = {d.strip().lower() for d in data.get("reputable_aggregators", []) if d}

        if "authority_weights" in data:
            self.authority_weights.update(data["authority_weights"])

        raw_paths = data.get("official_path_patterns", [])
        self.official_paths = [re.compile(p, re.IGNORECASE) for p in raw_paths if p]

    @staticmethod
    def extract_domain(url: str) -> str:
        """Extract clean hostname/domain from URL, stripping www and port."""
        if not url:
            return ""
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        try:
            parsed = urllib.parse.urlparse(url)
            netloc = parsed.netloc.lower().split(":")[0]
            if netloc.startswith("www."):
                netloc = netloc[4:]
            return netloc
        except Exception:
            return ""

    def _match_domain_set(self, domain: str, domain_set: Set[str]) -> bool:
        """Check if domain or any of its parent domains match the target set."""
        if not domain:
            return False
        if domain in domain_set:
            return True
        # Check subdomains (e.g. download.autodesk.com matches autodesk.com)
        parts = domain.split(".")
        for i in range(1, len(parts) - 1):
            parent = ".".join(parts[i:])
            if parent in domain_set:
                return True
        return False

    def is_official_vendor(self, url: str, vendor_hint: Optional[str] = None) -> bool:
        """Check if URL belongs to an official software vendor domain."""
        domain = self.extract_domain(url)
        if not domain:
            return False

        if self._match_domain_set(domain, self.official_vendors):
            return True

        # If vendor hint is provided (e.g. 'Autodesk' in 'Autodesk AutoCAD')
        if vendor_hint:
            hint_clean = re.sub(r"[^a-zA-Z0-9]", "", vendor_hint).lower()
            domain_clean = domain.replace("-", "")
            if hint_clean and len(hint_clean) >= 4 and hint_clean in domain_clean:
                return True

        return False

    def is_package_repository(self, url: str) -> bool:
        """Check if URL belongs to an official open-source or package repository."""
        domain = self.extract_domain(url)
        return self._match_domain_set(domain, self.package_repositories)

    def is_reputable_aggregator(self, url: str) -> bool:
        """Check if URL belongs to a reputable aggregator or documentation portal."""
        domain = self.extract_domain(url)
        return self._match_domain_set(domain, self.reputable_aggregators)

    def get_authority_score(self, url: str, vendor_hint: Optional[str] = None) -> float:
        """Calculate authority score (0.0 - 1.0) for a given URL."""
        if not url:
            return 0.0

        if self.is_official_vendor(url, vendor_hint):
            score = self.authority_weights.get("official_vendor", 1.0)
        elif self.is_package_repository(url):
            score = self.authority_weights.get("package_repository", 0.95)
        elif self.is_reputable_aggregator(url):
            score = self.authority_weights.get("reputable_aggregator", 0.70)
        else:
            score = self.authority_weights.get("unknown_domain", 0.35)

        # Bonus if path indicates product or documentation section
        parsed = urllib.parse.urlparse(url)
        path = parsed.path
        if any(p.search(path) for p in self.official_paths):
            score = min(1.0, score + 0.05)

        return round(score, 2)
