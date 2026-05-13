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
from pipelines.arte_pipeline import run
from pipelines.config import PipelineConfig
from core.client import HTTPClient
from pipelines.arte_pipeline import SampleArtePipeline
from config import settings


def main(config=None):
    """Run web scraper pipeline.

    Args:
        config: Optional PipelineConfig instance. If None, loads from settings.
    """
    print("🚀 Starting book extraction process...")

    try:
        if config:
            # Use provided config (for advanced usage)
            client = HTTPClient(download_strategy=config.download_strategy)
            pipeline = SampleArtePipeline(client=client, config=config)
            count = pipeline.run()
            print(f"🏁 Process completed. Scraped {count} products.")
        else:
            # Use default from_settings (backward compatible)
            count = run()
            print("🏁 Process completed.")
    except Exception as e:
        print(f"❌ Critical error during execution: {e}")


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
