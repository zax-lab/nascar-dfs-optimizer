#!/usr/bin/env python3
"""
Download NASCAR race data from Lap Raptor.

This script downloads loop data CSV files from Lap Raptor for specified
date ranges and series. Lap Raptor provides free web downloads without
requiring an API key.

Usage:
    python download_lap_raptor.py --year 2024 --series cup
    python download_lap_raptor.py --year 2025 --series cup --all-tracks
"""

import argparse
import os
import sys
import logging
from pathlib import Path
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "historical"
DOWNLOAD_DIR = PROJECT_ROOT / "data" / "downloads"


class LapRaptorDownloader:
    """Download data from Lap Rapor web interface."""
    
    BASE_URL = "https://lapraptor.com"
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'
        })
        
    def download_race_data(
        self,
        year: int,
        series: str = "cup",
        track_filter: Optional[str] = None
    ) -> List[Path]:
        """
        Download race loop data from Lap Raptor.
        
        Args:
            year: Race season year
            series: 'cup', 'xfinity', or 'truck'
            track_filter: Optional track name to filter
            
        Returns:
            List of downloaded file paths
        """
        logger.info(f"Downloading {series.upper()} series data for {year}")
        
        # Lap Raptor loop data index URL
        index_url = f"{self.BASE_URL}/drivers/race-log-index"
        
        # TODO: Parse Lap Raptor's HTML to find download links
        # For now, provide manual download instructions
        logger.warning("Automated Lap Raptor scraping not yet implemented")
        logger.info(f"Please download manually from: {index_url}")
        logger.info(f"  - Filter by Series: {series}")
        logger.info(f"  - Filter by Year: {year}")
        logger.info(f"  - Click 'Download CSV (all rows)'")
        logger.info(f"  - Save to: {self.output_dir / f'{year}_{series}_race_data.csv'}")
        
        return []


def main():
    parser = argparse.ArgumentParser(
        description="Download NASCAR race data from Lap Raptor"
    )
    parser.add_argument(
        "--year",
        type=int,
        default=2024,
        help="Race year to download (default: 2024)"
    )
    parser.add_argument(
        "--series",
        type=str,
        default="cup",
        choices=["cup", "xfinity", "truck"],
        help="Series to download (default: cup)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output directory (default: data/historical/)"
    )
    
    args = parser.parse_args()
    
    # Set output directory
    if args.output:
        output_dir = Path(args.output)
    else:
        output_dir = DATA_DIR / str(args.year)
    
    # Create downloader
    downloader = LapRaptorDownloader(output_dir)
    
    # Download data
    files = downloader.download_race_data(
        year=args.year,
        series=args.series
    )
    
    if not files:
        logger.warning("No files downloaded. Please download manually.")
        logger.info(f"Manual download URL: https://lapraptor.com/drivers/race-log-index")
        sys.exit(0)
    
    logger.info(f"Downloaded {len(files)} files")


if __name__ == "__main__":
    main()
