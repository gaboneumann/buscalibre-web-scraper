"""Core crawler components: Policies and WebCrawler engine."""
import logging
import random
import time
from typing import Tuple, Optional, Dict, List, Callable
from config import settings
from config.logging_config import SUCCESS
from pipelines.schema import CheckpointManager

logger = logging.getLogger(__name__)


class SessionRotationPolicy:
    """Policy for managing HTTP session rotation during product iteration."""

    def __init__(
        self,
        threshold: Optional[int] = None,
        random_threshold: bool = False,
        rotation_wait_min: float = 10,
        rotation_wait_max: float = 15,
    ):
        """
        Initialize session rotation policy.

        Args:
            threshold: Fixed rotation threshold (10-15 products per session).
            random_threshold: If True, randomize threshold on each init (default behavior).
            rotation_wait_min: Minimum wait in seconds after session rotation.
            rotation_wait_max: Maximum wait in seconds after session rotation.
        """
        if threshold is not None:
            self._threshold = threshold
        elif random_threshold:
            self._threshold = random.randint(10, 15)
        else:
            self._threshold = random.randint(10, 15)
        self._rotation_wait_min = rotation_wait_min
        self._rotation_wait_max = rotation_wait_max

    def should_rotate(self, products_in_session: int) -> bool:
        """
        Determine if session should rotate based on product count.

        Args:
            products_in_session: Number of products processed in current session.

        Returns:
            True if products_in_session >= threshold, False otherwise.
        """
        return products_in_session >= self._threshold

    def on_rotation(self) -> Tuple[float, float]:
        """
        Return wait times when rotating session.

        Returns:
            Tuple of (wait_min, wait_max) in seconds.
        """
        return (self._rotation_wait_min, self._rotation_wait_max)


class BlockDetectionPolicy:
    """Policy for detecting and handling 202 blocking by the server."""

    def __init__(
        self,
        threshold: int = 3,
        block_wait_min: float = 45,
        block_wait_max: float = 70,
        backoff_base: float = 45,
    ):
        """
        Initialize block detection policy.

        Args:
            threshold: Number of consecutive failures before auto-abort (default 3).
            block_wait_min: Minimum wait in seconds after a block detection.
            block_wait_max: Maximum wait in seconds after a block detection.
            backoff_base: Base wait time for exponential backoff (default 45).
        """
        self._threshold = threshold
        self._consecutive_failures = 0
        self._block_wait_min = block_wait_min
        self._block_wait_max = block_wait_max
        self._backoff_base = backoff_base

    def on_success(self) -> None:
        """Reset consecutive failure counter on successful request."""
        self._consecutive_failures = 0

    def get_backoff_wait(self, consecutive_count: int) -> float:
        """
        Calculate exponential backoff wait time with jitter.

        Args:
            consecutive_count: Number of the attempt (1, 2, 3, ...).

        Returns:
            Wait time in seconds: backoff_base * 2^(count-1) + jitter.
        """
        wait_time = self._backoff_base * (2 ** (consecutive_count - 1))
        jitter = random.uniform(-0.2, 0.2) * wait_time
        return max(wait_time + jitter, self._backoff_base)

    def on_failure(self) -> Tuple[bool, float]:
        """
        Handle failed request (202 block detected).
        Uses exponential backoff: 45s → 90s → 180s with ±20% jitter.

        Returns:
            Tuple of (should_abort, wait_time).
            - should_abort: True if consecutive_failures >= threshold.
            - wait_time: Seconds to wait before retry (exponential backoff).
        """
        self._consecutive_failures += 1
        should_abort = self._consecutive_failures >= self._threshold

        # Use exponential backoff instead of uniform
        wait_time = self.get_backoff_wait(self._consecutive_failures)

        logger.warning("BLOCK POLICY: failure %s/%s, waiting %.1fs (exponential)", self._consecutive_failures, self._threshold, wait_time)
        return (should_abort, wait_time)


class DelayPolicy:
    """Policy for inter-request delays and coffee breaks."""

    def __init__(
        self,
        delay_min: Optional[float] = None,
        delay_max: Optional[float] = None,
        coffee_break_interval: Optional[int] = None,
        coffee_break_min: float = 150,
        coffee_break_max: float = 250,
        page_wait_min: float = 60,
        page_wait_max: float = 90,
        rotation_wait_min: float = 10,
        rotation_wait_max: float = 15,
        post_rotation_wait_min: float = 5,
        post_rotation_wait_max: float = 10,
    ):
        """
        Initialize delay policy.

        Args:
            delay_min: Minimum delay between products (default from settings.DELAY_MIN).
            delay_max: Maximum delay between products (default from settings.DELAY_MAX).
            coffee_break_interval: Products between coffee breaks (randomized 10-15).
            coffee_break_min: Minimum coffee break duration in seconds.
            coffee_break_max: Maximum coffee break duration in seconds.
            page_wait_min: Minimum wait between category pages in seconds (default 60).
            page_wait_max: Maximum wait between category pages in seconds (default 90).
            rotation_wait_min: Minimum wait after session rotation in seconds (default 10).
            rotation_wait_max: Maximum wait after session rotation in seconds (default 15).
            post_rotation_wait_min: Minimum post-rotation cascade wait in seconds (default 5).
            post_rotation_wait_max: Maximum post-rotation cascade wait in seconds (default 10).
        """
        self._delay_min = delay_min or getattr(settings, 'DELAY_MIN', 30)
        self._delay_max = delay_max or getattr(settings, 'DELAY_MAX', 55)
        self._coffee_break_interval = coffee_break_interval or random.randint(10, 15)
        self._coffee_break_min = coffee_break_min
        self._coffee_break_max = coffee_break_max
        self._page_wait_min = page_wait_min
        self._page_wait_max = page_wait_max
        self._rotation_wait_min = rotation_wait_min
        self._rotation_wait_max = rotation_wait_max
        self._post_rotation_wait_min = post_rotation_wait_min
        self._post_rotation_wait_max = post_rotation_wait_max

    def wait_between_products(self) -> None:
        """Sleep for delay_min to delay_max seconds between product requests."""
        sleep_time = random.uniform(self._delay_min, self._delay_max)
        time.sleep(sleep_time)

    def should_take_coffee_break(self, product_count: int) -> bool:
        """
        Determine if a coffee break should be taken.

        Args:
            product_count: Total products processed so far.

        Returns:
            True if product_count is a multiple of coffee_break_interval.
        """
        return product_count > 0 and product_count % self._coffee_break_interval == 0

    def wait_coffee_break(self) -> None:
        """Sleep for coffee_break_min to coffee_break_max seconds during coffee break."""
        sleep_time = random.uniform(self._coffee_break_min, self._coffee_break_max)
        time.sleep(sleep_time)

    def wait_between_pages(self) -> None:
        """Sleep for page_wait_min to page_wait_max seconds between category pages."""
        sleep_time = random.uniform(self._page_wait_min, self._page_wait_max)
        time.sleep(sleep_time)

    def wait_session_rotation(self) -> None:
        """Sleep for rotation_wait_min to rotation_wait_max seconds after session rotation."""
        sleep_time = random.uniform(self._rotation_wait_min, self._rotation_wait_max)
        time.sleep(sleep_time)

    def wait_post_rotation(self) -> None:
        """Sleep for post_rotation_wait_min to post_rotation_wait_max seconds after re-navigation."""
        sleep_time = random.uniform(self._post_rotation_wait_min, self._post_rotation_wait_max)
        time.sleep(sleep_time)

    def wait_block_backoff(self, wait_time: float) -> None:
        """Sleep for wait_time seconds as block backoff (pre-computed by BlockDetectionPolicy).

        Args:
            wait_time: Duration in seconds supplied by block_policy.get_backoff_wait().
        """
        time.sleep(wait_time)


class WebCrawler:
    """Main crawler engine for two-level web scraping (categories → products)."""

    def __init__(
        self,
        client,
        extract_fn: Callable,
        transform_fn: Callable,
        checkpoint_mgr,
        session_policy: SessionRotationPolicy,
        block_policy: BlockDetectionPolicy,
        delay_policy: DelayPolicy,
        config,
    ):
        """
        Initialize orchestrator with client, extraction functions, and policies.

        Args:
            client: HTTPClient instance for HTTP requests.
            extract_fn: Function(html) → List[str] to extract product links from category page.
            transform_fn: Function(html) → Dict | None to parse product page HTML.
            checkpoint_mgr: CheckpointManager for CSV reads/writes and deduplication.
            session_policy: SessionRotationPolicy instance.
            block_policy: BlockDetectionPolicy instance.
            delay_policy: DelayPolicy instance.
            config: PipelineConfig instance with product_target, product_per_page, category_url.
        """
        self.client = client
        self.extract_fn = extract_fn
        self.transform_fn = transform_fn
        self.checkpoint_mgr = checkpoint_mgr
        self.session_policy = session_policy
        self.block_policy = block_policy
        self.delay_policy = delay_policy
        self.config = config

    def run(self) -> int:
        """
        Execute two-level pipeline: category pages → product pages.

        Returns:
            Number of products successfully scraped and saved.
        """
        from core.paginator import build_page

        scraped_urls = self.checkpoint_mgr.get_scraped_urls()

        success_count = len(scraped_urls)
        if success_count > 0:
            logger.info("Resuming from checkpoint: %s/%s already scraped.", success_count, self.config.product_target)

        books_in_session = 0
        blocks_in_batch = 0
        successful_in_batch = 0
        page_index = 1

        while success_count < self.config.product_target:
            logger.info("BATCH: Category Page %s", page_index)
            self.client.reset_session()

            page_url = build_page(self.config.category_url, page_index)

            if page_index == 1:
                html_cat = self.client.navigate_to_category(page_url)
            else:
                html_cat = self.client.get(page_url, request_type="category")

            if html_cat is None:
                blocks_in_batch += 1
                should_abort, _ = self.block_policy.on_failure()
                if should_abort:
                    logger.error("AUTO-STOP: Persistent category page blocking. Aborting.")
                    return success_count
                continue

            links = self.extract_fn(html_cat)
            self.block_policy.on_success()
            successful_in_batch += 1

            random.shuffle(links)
            logger.debug("Links on page %s shuffled.", page_index)

            for link in links:
                if success_count >= self.config.product_target:
                    break

                full_link = link if link.startswith("http") else f"https://www.buscalibre.cl{link}"
                if full_link in scraped_urls:
                    continue

                # Session rotation check
                if self.session_policy.should_rotate(books_in_session):
                    logger.info("Random rotation (threshold reached): Resetting session...")
                    self.client.reset_session()
                    books_in_session = 0
                    self.delay_policy.wait_session_rotation()
                    logger.debug("[Post-rotation cascade] Re-navigating to category...")
                    self.client.get(build_page(self.config.category_url, page_index), request_type="category")
                    self.delay_policy.wait_post_rotation()

                logger.info("[%s/%s] Extracting: %s", success_count + 1, self.config.product_target, full_link)
                html_prod = self.client.get(full_link, request_type="product")

                if html_prod is None:
                    blocks_in_batch += 1
                    should_abort, wait_time = self.block_policy.on_failure()
                    logger.warning("202 block detected.")

                    if should_abort:
                        logger.error("AUTO-STOP: Too many consecutive blocks.")
                        return success_count

                    self.delay_policy.wait_block_backoff(wait_time)
                    self.client.reset_session()
                    books_in_session = 0
                    continue

                self.block_policy.on_success()
                data = self.transform_fn(html_prod)

                if data and data.get("title"):
                    record = {
                        "title": data["title"],
                        "author": data.get("author", "Anonymous"),
                        "price": data.get("price"),
                        "stock": data.get("stock_status") == "in_stock",
                        "page_index": page_index,
                        "product_url": full_link,
                        "source": self.config.source_name,
                    }
                    self.checkpoint_mgr.save_record(record)
                    scraped_urls.add(full_link)
                    success_count += 1
                    books_in_session += 1
                    successful_in_batch += 1
                    logger.log(SUCCESS, "Saved: %s", record['title'][:30])

                self.delay_policy.wait_between_products()

                # Coffee break logic
                if self.delay_policy.should_take_coffee_break(success_count):
                    logger.info("BREAK: User stepped away for a bit...")
                    self.delay_policy.wait_coffee_break()

            logger.info("BATCH SUMMARY: %s success, %s blocks", successful_in_batch, blocks_in_batch)

            # Dynamic adaptation based on batch results
            if blocks_in_batch >= 2:
                logger.warning("TRIGGERS: %s bloques detectados, reduciendo PRODUCT_PER_PAGE...", blocks_in_batch)
                self.config.adapt_product_per_page(0.85)  # -15%
            elif successful_in_batch >= 10 and blocks_in_batch == 0:
                logger.info("TRIGGERS: %s sucessos sin bloques, aumentando PRODUCT_PER_PAGE...", successful_in_batch)
                self.config.adapt_product_per_page(1.10)  # +10%

            # Move to next page if not yet at target
            if success_count < self.config.product_target:
                page_index += 1
                logger.info("Batch complete. Waiting before next page...")
                self.delay_policy.wait_between_pages()

            # Reset batch counters for next iteration
            blocks_in_batch = 0
            successful_in_batch = 0

        logger.info("Process completed. Reached %s products.", success_count)
        return success_count
