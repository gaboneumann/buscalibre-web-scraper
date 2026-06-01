"""
BuscaLibre Web Scraper - Main Entry Point
Pipeline-based sequential scraper with AWS WAF bypass via Playwright.

Usage:
    python main.py                  # Uses config/settings.py (recommended for production)

    # Advanced: Use with custom config (JSON file or dict)
    python main.py --config /path/to/config.json
"""

import argparse
import json
import logging
from pipelines.category_pipeline import run, CategoryPipeline
from pipelines.config import PipelineConfig
from core.client import HTTPClient
from config import settings
from config.logging_config import setup_logging

logger = logging.getLogger(__name__)


def main(config=None):
    """Run web scraper pipeline.

    Args:
        config: Optional PipelineConfig instance. If None, loads from settings.
    """
    setup_logging()
    logger.info("Starting book extraction process...")

    try:
        if config:
            # Use provided config (for advanced usage)
            client = HTTPClient(download_strategy=config.download_strategy)
            try:
                pipeline = CategoryPipeline(client=client, config=config)
                count = pipeline.run()
                logger.info("Process completed. Scraped %s products.", count)
            finally:
                client.close()
        else:
            # Use default from_settings
            count = run()
            logger.info("Process completed.")
    except Exception as e:
        logger.error("Critical error during execution: %s", e, exc_info=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="BuscaLibre Web Scraper"
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Path to JSON config file (overrides default settings)"
    )
    parser.add_argument(
        "--target",
        type=int,
        help="Override product target count"
    )

    args = parser.parse_args()

    config = None
    if args.config:
        with open(args.config, 'r') as f:
            config_dict = json.load(f)
        if args.target:
            config_dict["product_target"] = args.target
        config = PipelineConfig.from_dict(config_dict)

    main(config=config)
