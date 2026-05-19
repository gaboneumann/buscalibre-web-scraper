"""BasePipeline: Abstract base class for site-specific ETL pipelines."""
from abc import ABC, abstractmethod
from pipelines.config import PipelineConfig
from config import settings


class BasePipeline(ABC):
    """Abstract base pipeline class for scraping implementations.

    Provides orchestrator setup and enforcement of required methods for
    site-specific implementations.
    """

    def __init__(self, client, config: PipelineConfig = None):
        """Initialize pipeline with HTTP client and optional config.

        Args:
            client: HTTPClient instance for making requests.
            config: PipelineConfig instance. If None, loads from config/settings.py.
        """
        self.client = client
        self.config = config or PipelineConfig.from_settings(settings)

    @abstractmethod
    def collect_product_links(self, html: str):
        """Extract product links from category HTML.

        Args:
            html: HTML content of category page.

        Returns:
            List of product URLs or paths.
        """
        pass

    @abstractmethod
    def parse_product(self, html: str):
        """Extract product data from product page HTML.

        Args:
            html: HTML content of product page.

        Returns:
            Dict with product fields (title, author, price, stock, etc.)
            or None if parsing failed.
        """
        pass

    @abstractmethod
    def get_csv_fields(self):
        """Return list of CSV field names in order.

        Returns:
            List of field names for CSV output.
        """
        pass

    def run(self) -> int:
        """Execute the pipeline and return product count.

        Returns:
            Number of products successfully scraped and saved.
        """
        # Base implementation: placeholder for orchestrator setup
        # Subclasses will override or orchestrator will call into here
        return 0

    def _create_orchestrator(self):
        """Create and configure pipeline orchestrator.

        To be implemented by subclasses or overridden in phase 2.
        Returns the PipelineOrchestrator instance.
        """
        pass
