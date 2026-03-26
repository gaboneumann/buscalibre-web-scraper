"""
BuscaLibre Web Scraper - Main Entry Point
Pipeline-based sequential scraper with AWS WAF bypass via Playwright.
"""

from pipelines.arte_pipeline import run


def main():
    print("🚀 Starting book extraction process...")

    try:
        run()
        print("🏁 Process completed.")
    except Exception as e:
        print(f"❌ Critical error during execution: {e}")


if __name__ == "__main__":
    main()
