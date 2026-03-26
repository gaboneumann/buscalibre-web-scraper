"""
Main scraping pipeline orchestrator for BuscaLibre Art Books Category.
Implements two-level nested iteration with streaming CSV writes.
"""

import time
import random
import csv
import os
from math import ceil
from typing import List, Dict

from core.client import HTTPClient
from core.paginator import build_page
from core.parser import parse_product_links
from core.parser_product import parse_product
from config.settings import (
    CATEGORY_URL,
    DELAY_MIN,
    DELAY_MAX,
    SOURCE_NAME,
    OUTPUT_PATH,
    PRODUCT_TARGET,
    PRODUCT_PER_PAGE
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
        writer = csv.DictWriter(f, fieldnames=fieldnames)
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
        print(f"⚠️ WARNING: Could not read checkpoint file: {e}")
    return scraped_urls

def collect_product_links(client: HTTPClient) -> List[str]:
    """
    Collect product links across multiple category pages.

    Implements pagination with a target number of products.

    Args:
        client: HTTPClient instance with anti-detection features

    Returns:
        List of unique product links collected
    """
    all_links = []
    pages_needed = ceil(PRODUCT_TARGET / PRODUCT_PER_PAGE)

    for page_index in range(1, pages_needed + 1):
        if len(all_links) >= PRODUCT_TARGET:
            break

        page_url = build_page(CATEGORY_URL, page_index)

        if page_index == 1:
            html_cat = client.navigate_to_category(page_url)
        else:
            html_cat = client.get(page_url, request_type="category")

        if html_cat is None:
            continue

        links = parse_product_links(html_cat)
        all_links.extend(links)

    return all_links[:PRODUCT_TARGET]

def run() -> List[Dict]:
    """
    Execute main scraping pipeline.

    Two-level nested iteration:
    - Level 1: Iterate through category pages
    - Level 2: Iterate through products on each page

    Returns:
        Empty list (data written via streaming to CSV)
    """
    client = HTTPClient()
    scraped_urls = get_scraped_urls()
    pages_needed = ceil(PRODUCT_TARGET / PRODUCT_PER_PAGE)

    success_count = 0
    consecutive_blocks = 0
    BLOCK_THRESHOLD = 3  # Auto-stop after 3 consecutive 202 errors

    # --- ANTI-DETECTION LAYER 3: Random session rotation (2-4 products) ---
    books_in_session = 0
    reset_threshold = random.randint(2, 4)

    for page_index in range(1, pages_needed + 1):
        if success_count >= PRODUCT_TARGET:
            break

        print(f"\n--- 📑 BATCH: Category Page {page_index} ---")

        # Preventive session reset when moving to new category page
        client.reset_session()

        page_url = build_page(CATEGORY_URL, page_index)

        # --- ANTI-DETECTION LAYER 6: Cascading Navigation ---
        # First page uses full cascade (home → category); others just GET directly
        if page_index == 1:
            # First page: full cascade navigation
            html_cat = client.navigate_to_category(page_url)
        else:
            # Subsequent pages: direct GET with category context
            html_cat = client.get(page_url, request_type="category")

        if html_cat is None:
            consecutive_blocks += 1
            if consecutive_blocks >= BLOCK_THRESHOLD:
                print("🚨 AUTO-STOP: Persistent category page blocking. Aborting.")
                return []
            continue

        links = parse_product_links(html_cat)
        consecutive_blocks = 0

        # --- ANTI-DETECTION LAYER 7: Link Shuffling ---
        random.shuffle(links)
        print(f"🔀 Links on page {page_index} shuffled.")

        for link in links:
            if success_count >= PRODUCT_TARGET:
                break

            full_link = link if link.startswith("http") else f"https://www.buscalibre.cl{link}"
            if full_link in scraped_urls:
                continue

            # --- ANTI-DETECTION LAYER 3: Proactive Random Session Rotation ---
            if books_in_session >= reset_threshold:
                print(f"♻️ Random rotation (threshold reached: {reset_threshold}): Resetting session...")
                client.reset_session()
                books_in_session = 0
                reset_threshold = random.randint(2, 4)  # New random threshold for next cycle
                time.sleep(random.uniform(10, 15))
                # Re-establish cascade: visit category before next product (home already visited in reset_session)
                print(f"📂 [Post-rotation cascade] Re-navigating to category...")
                client.get(build_page(CATEGORY_URL, page_index), request_type="category")
                time.sleep(random.uniform(5, 10))

            print(f"🔍 [{success_count + 1}/{PRODUCT_TARGET}] Extracting: {full_link}")
            html_prod = client.get(full_link, request_type="product")

            # --- ANTI-DETECTION LAYER 3: Auto-stop on excessive blocking ---
            if html_prod is None:
                consecutive_blocks += 1
                print(f"⛔ 202 block detected ({consecutive_blocks}/{BLOCK_THRESHOLD}).")

                if consecutive_blocks >= BLOCK_THRESHOLD:
                    print("🚨 AUTO-STOP: Too many consecutive blocks.")
                    return []

                # On failure, apply forced reset and wait before retrying
                time.sleep(random.uniform(45, 70))  # Post-block recovery delay
                client.reset_session()
                books_in_session = 0
                continue  # Skip to next link without parsing

            # SUCCESS: Reset block counter and process data
            consecutive_blocks = 0
            data = parse_product(html_prod)

            if data and data.get("title"):
                record = {
                    "title": data["title"],
                    "author": data.get("author", "Anonymous"),
                    "price": data.get("price"),
                    "stock": data.get("stock_status") == "in_stock",
                    "page_index": page_index,
                    "product_url": full_link,
                    "source": SOURCE_NAME,
                }
                save_single_record(record)
                scraped_urls.add(full_link)
                success_count += 1
                books_in_session += 1  # Increment session counter
                print(f"✅ Saved: {record['title'][:30]}")

            # --- ANTI-DETECTION LAYER 4a: Main delay between products ---
            time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

            # --- ANTI-DETECTION LAYER 4d: Organic coffee break pause ---
            if success_count > 0 and success_count % random.randint(10, 15) == 0:
                coffee_break = random.uniform(150, 250)
                print(f"☕ BREAK: User stepped away for {coffee_break / 60:.1f} minutes...")
                time.sleep(coffee_break)

        # --- ANTI-DETECTION LAYER 4f: Pause between category pages ---
        if success_count < PRODUCT_TARGET:
            wait_batch = random.uniform(60, 90)
            print(f"🏁 Batch complete. Waiting {wait_batch:.0f}s before next category...")
            time.sleep(wait_batch)

    return []