"""PipelineConfig: Dependency injection configuration object for ETL pipelines."""

import logging

logger = logging.getLogger(__name__)


class PipelineConfig:
    """Configuration container for pipeline execution.

    Replaces global settings imports, enabling testability and reusability
    across scraping targets without code modifications.
    """

    def __init__(
        self,
        domain_url: str,
        category_url: str,
        product_target: int,
        delay_min: float,
        delay_max: float,
        source_name: str,
        output_path: str,
        download_strategy=None,
        session_policy=None,
        block_policy=None,
        delay_policy=None,
    ):
        """Initialize PipelineConfig with explicit values.

        Args:
            domain_url: Base domain URL.
            category_url: Category page URL.
            product_target: Optional stop cap. When > 0, the crawler stops after reaching this many products. Set to 0 to disable and crawl until the category is exhausted.
            delay_min: Minimum delay between requests.
            delay_max: Maximum delay between requests.
            source_name: Source identifier for CSV.
            output_path: CSV output file path.
            download_strategy: Optional DownloadStrategy for custom HTTP handling.
            session_policy: Optional SessionRotationPolicy instance.
            block_policy: Optional BlockDetectionPolicy instance.
            delay_policy: Optional DelayPolicy instance.
        """
        self.domain_url = domain_url
        self.category_url = category_url
        self.product_target = product_target
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.source_name = source_name
        self.output_path = output_path
        self.download_strategy = download_strategy
        self.session_policy = session_policy
        self.block_policy = block_policy
        self.delay_policy = delay_policy

    @classmethod
    def from_settings(cls, settings):
        """Create PipelineConfig from config/settings.py module.

        Args:
            settings: The config.settings module with DOMAIN_URL, CATEGORY_URL, etc.

        Returns:
            PipelineConfig instance wrapping settings values.
        """
        return cls(
            domain_url=settings.DOMAIN_URL,
            category_url=settings.CATEGORY_URL,
            product_target=settings.PRODUCT_TARGET,
            delay_min=settings.DELAY_MIN,
            delay_max=settings.DELAY_MAX,
            source_name=settings.SOURCE_NAME,
            output_path=settings.OUTPUT_PATH,
            download_strategy=None,
        )

    @classmethod
    def from_dict(cls, data: dict):
        """Create PipelineConfig from dictionary.

        Args:
            data: Dict with keys: domain_url, category_url, product_target, etc.
                  Optional: download_strategy (DownloadStrategy instance).

        Returns:
            PipelineConfig instance initialized from dict values.

        Raises:
            KeyError: If required keys are missing.
        """
        return cls(
            domain_url=data["domain_url"],
            category_url=data["category_url"],
            product_target=data["product_target"],
            delay_min=data["delay_min"],
            delay_max=data["delay_max"],
            source_name=data["source_name"],
            output_path=data["output_path"],
            download_strategy=data.get("download_strategy"),
            session_policy=data.get("session_policy"),
            block_policy=data.get("block_policy"),
            delay_policy=data.get("delay_policy"),
        )
