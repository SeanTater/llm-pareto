#!/usr/bin/env python3
"""
Base scraper classes
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Any
import requests


class BaseScraper(ABC):
    """Base class for all scrapers"""

    def __init__(self, timeout: int = 30):
        """
        Initialize scraper

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (LLM Pareto Data Collector)'
        })

    @abstractmethod
    def scrape(self) -> Dict[str, Any]:
        """
        Scrape data from source

        Returns:
            Dictionary with scraped data and metadata
        """
        pass

    def fetch_url(self, url: str) -> str:
        """
        Fetch URL content

        Args:
            url: URL to fetch

        Returns:
            HTML/text content

        Raises:
            ScraperError: If fetch fails
        """
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            raise ScraperError(f"Failed to fetch {url}: {e}")

    def add_metadata(self, data: Dict[str, Any], url: str, scrape_method: str) -> Dict[str, Any]:
        """
        Add source metadata to scraped data

        Args:
            data: Scraped data
            url: Source URL
            scrape_method: Method used (api, llm, regex)

        Returns:
            Data with metadata added
        """
        return {
            **data,
            "source_metadata": {
                "url": url,
                "collected": datetime.now().isoformat(),
                "scrape_method": scrape_method
            }
        }


class ScraperError(Exception):
    """Raised when scraping fails"""
    pass
