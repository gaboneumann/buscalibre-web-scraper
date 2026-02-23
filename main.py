"""
BuscaLibre Web Scraper - Main Entry Point
Pipeline-based sequential scraper with 7 anti-detection layers
"""

from pipelines.arte_pipeline import run
from storage.csv_writer import write_csv
from config.settings import OUTPUT_PATH

def main():
    """
    Main scraper execution function.
    Orchestrates the complete scraping pipeline and CSV export.
    """
    print("🚀 Starting book extraction process...")

    try:
        data = run()

        if data and len(data) > 0:
            write_csv(OUTPUT_PATH, data)
            print(f"✅ CSV updated with {len(data)} new records.")
        else:
            print("🏁 Process completed. No new data to process.")

    except Exception as e:
        print(f"❌ Critical error during execution: {e}")

if __name__ == "__main__":
    main()