"""
Generic scraping pipeline orchestrator for BuscaLibre book categories.
Implements two-level nested iteration with streaming CSV writes.
"""

import csv
import logging
import os
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

from core.client import HTTPClient
from core.parser import parse_product_links
from core.parser_product import parse_product
from config import settings
from config.settings import (
    CATEGORY_URL,
    DELAY_MIN,
    DELAY_MAX,
    SOURCE_NAME,
    OUTPUT_PATH,
    PRODUCT_TARGET,
)
from pipelines.base_pipeline import BasePipeline
from pipelines.config import PipelineConfig
from pipelines.components import (
    WebCrawler,
    SessionRotationPolicy,
    BlockDetectionPolicy,
    DelayPolicy,
    CheckpointManager,
)

def save_single_record(record: Dict):
    """
    Write a single product record to CSV immediately (append mode).
    Creates output directory and CSV header if needed.
    """
    file_exists = os.path.isfile(OUTPUT_PATH)
    fieldnames = ["title", "author", "price", "stock", "page_index", "product_url", "source"]

    target_dir = os.path.dirname(OUTPUT_PATH)
    if target_dir:
        os.makedirs(target_dir, exist_ok=True)

    with open(OUTPUT_PATH, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=',')
        if not file_exists:
            writer.writeheader()
        writer.writerow(record)

def get_scraped_urls() -> set:
    """
    Load already-scraped product URLs from CSV checkpoint.
    Used for deduplication when resuming after interruptions.

    Returns:
        Set of product URLs already processed
    """
    scraped_urls = set()
    if not os.path.isfile(OUTPUT_PATH):
        return scraped_urls

    try:
        with open(OUTPUT_PATH, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                url = row.get("product_url")
                if url:
                    scraped_urls.add(url.strip())
    except Exception as e:
        logger.warning("Could not read checkpoint file: %s", e)
    return scraped_urls


class CategoryPipeline(BasePipeline):
    """
    Generic Buscalibre category scraper implementing two-level nested iteration
    with streaming CSV writes and anti-detection layers.
    """

    def collect_product_links(self, html: str) -> List[str]:
        """Extract product links from category HTML."""
        if html is None:
            return []
        return parse_product_links(html)

    def parse_product(self, html: str) -> Optional[Dict]:
        """Extract product data from product page HTML."""
        if html is None:
            return None
        return parse_product(html)

    def get_csv_fields(self) -> List[str]:
        """Return list of CSV field names in order."""
        return ["title", "author", "price", "stock", "page_index", "product_url", "source"]

    def _create_crawler(self) -> WebCrawler:
        """Create and configure web crawler engine with policies."""
        checkpoint_mgr = CheckpointManager(self.config.output_path, category_url=self.config.category_url)
        session_policy = self.config.session_policy or SessionRotationPolicy()
        block_policy = self.config.block_policy or BlockDetectionPolicy(
            backoff_base=45  # Exponential backoff base: 45s → 90s → 180s
        )
        delay_policy = self.config.delay_policy or DelayPolicy(
            delay_min=self.config.delay_min,
            delay_max=self.config.delay_max,
        )

        return WebCrawler(
            client=self.client,
            extract_fn=self.collect_product_links,
            transform_fn=self.parse_product,
            checkpoint_mgr=checkpoint_mgr,
            session_policy=session_policy,
            block_policy=block_policy,
            delay_policy=delay_policy,
            config=self.config,
        )

    def run(self) -> int:
        """
        Execute main scraping pipeline via web crawler.

        Returns:
            Number of products successfully scraped and saved.
        """
        crawler = self._create_crawler()
        return crawler.run()

def run() -> int:
    """
    Execute main scraping pipeline via CategoryPipeline.
    Loads configuration from global settings.

    Auto-generates CSV filename from category URL:
    - https://www.buscalibre.cl/libros/ficcion → books_ficcion.csv
    - https://www.buscalibre.cl/libros/arte → books_arte.csv

    Returns:
        Number of products successfully scraped and saved.
    """
    import re

    config = PipelineConfig.from_settings(settings)
    client = HTTPClient(
        domain_url=config.domain_url,
        category_url=config.category_url,
    )

    # Extract category name from URL (e.g., "ficcion" from "/libros/ficcion")
    match = re.search(r'/libros/([a-z-]+)', config.category_url)
    if match:
        category_name = match.group(1)
        config.output_path = f"storage/outputs/books_{category_name}.csv"

    pipeline = CategoryPipeline(client=client, config=config)
    try:
        return pipeline.run()
    finally:
        client.close()