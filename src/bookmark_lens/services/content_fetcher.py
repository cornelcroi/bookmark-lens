"""
Content fetching and extraction service.

Fetches web pages, extracts metadata and readable content.
"""

import logging
from urllib.parse import urlparse, urlunparse
import requests
from bs4 import BeautifulSoup
from readability import Document
from markdownify import markdownify as md

from ..config import Config
from ..models.bookmark import ContentResult

logger = logging.getLogger(__name__)


class ContentFetcher:
    """Fetches and extracts content from web pages."""

    def __init__(self, config: Config):
        self.config = config
        self.timeout = config.fetch_timeout
        self.user_agent = config.user_agent
        self.max_content_length = config.max_content_length

    def fetch(self, url: str, full_content: bool = True) -> ContentResult:
        """
        Fetch and extract content from a URL.

        Args:
            url: URL to fetch
            full_content: If True, extract full content as Markdown.
                         If False, only extract title and description.

        Returns:
            ContentResult with extracted data
        """
        normalized_url = self._normalize_url(url)
        domain = urlparse(normalized_url).netloc

        try:
            # Fetch page
            response = requests.get(
                url,
                timeout=self.timeout,
                headers={"User-Agent": self.user_agent},
                allow_redirects=True
            )
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.content, 'lxml')

            # Extract title
            title = None
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.get_text().strip()

            # Extract meta description
            description = None
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if not meta_desc:
                meta_desc = soup.find('meta', attrs={'property': 'og:description'})
            if meta_desc and meta_desc.get('content'):
                description = meta_desc['content'].strip()

            # Extract readable content (only if requested)
            if full_content:
                content_text = self._extract_content_as_markdown(response.content)
            else:
                content_text = ""  # Skip content extraction for Core Mode

            return ContentResult(
                url=url,
                normalized_url=normalized_url,
                domain=domain,
                title=title,
                description=description,
                content_text=content_text,
                fetch_success=True
            )

        except requests.Timeout:
            logger.warning(f"Timeout fetching {url}")
            return ContentResult(
                url=url,
                normalized_url=normalized_url,
                domain=domain,
                fetch_success=False,
                error_message="Request timeout"
            )

        except requests.RequestException as e:
            logger.warning(f"Failed to fetch {url}: {e}")
            return ContentResult(
                url=url,
                normalized_url=normalized_url,
                domain=domain,
                fetch_success=False,
                error_message=str(e)
            )

        except Exception as e:
            logger.error(f"Unexpected error fetching {url}: {e}")
            return ContentResult(
                url=url,
                normalized_url=normalized_url,
                domain=domain,
                fetch_success=False,
                error_message=f"Unexpected error: {str(e)}"
            )

    def _normalize_url(self, url: str) -> str:
        """
        Normalize URL for consistency.

        Args:
            url: Raw URL

        Returns:
            Normalized URL
        """
        parsed = urlparse(url)

        # Lowercase scheme and netloc
        scheme = parsed.scheme.lower() if parsed.scheme else 'https'
        netloc = parsed.netloc.lower()

        # Remove fragment
        normalized = urlunparse((
            scheme,
            netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            ''  # Remove fragment
        ))

        return normalized

    def _extract_content_as_markdown(self, html_content: bytes) -> str:
        """
        Extract readable content as Markdown.

        Args:
            html_content: Raw HTML bytes

        Returns:
            Extracted content as Markdown
        """
        try:
            # Decode bytes to string (readability expects string)
            html_string = html_content.decode('utf-8', errors='ignore')
            
            # Use readability to extract main content
            doc = Document(html_string)
            content_html = doc.summary()

            # Convert HTML to Markdown
            markdown = md(content_html, heading_style="ATX")

            # Truncate if too long
            if len(markdown) > self.max_content_length:
                markdown = markdown[:self.max_content_length]

            return markdown

        except Exception as e:
            logger.warning(f"Failed to extract content: {e}")
            return ""
