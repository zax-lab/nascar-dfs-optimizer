#!/usr/bin/env python3
"""
Improved data download with multiple potential sources.

Updated with alternative NASCAR data sources that don't require accounts.
"""

import os
import requests
from pathlib import Path
import json
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent / "data"
HISTORICAL_DIR = BASE_DIR / "historical"
HISTORICAL_DIR.mkdir(parents=True, exist_ok=True)

BRAVE_API_KEY = "BSASIE-lCiV0g0ex_KarGSI5FcW616s"

def log_msg(message):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

def search_brave(query: str, count: int = 5) -> list:
    """
    Search for NASCAR data sources using Brave Search API.

    Args:
        query: Search query
        count: Number of results to return

    Returns:
        List of search results
    """
    headers = {
        "X-Subscription-Token": BRAVE_API_KEY,
        "Accept": "application/json"
    }

    url = f"https://api.search.brave.com/res/v1/web/search?q={query}&count={count}"

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        results = []
        if 'web' in data and 'results' in data['web']:
            for item in data['web']['results']:
                results.append({
                    'title': item.get('title', ''),
                    'url': item.get('url', ''),
                    'snippet': item.get('snippet', '')
                })

        return results

    except Exception as e:
        log_msg(f"  ❌ Brave search failed: {e}")
        return []

def download_csv_from_url(url: str, filename: str) -> bool:
    """Download CSV file from URL."""
    try:
        log_msg(f"Downloading {filename}...")
        response = requests.get(url, timeout=60, stream=True)
        response.raise_for_status()

        filepath = HISTORICAL_DIR / filename
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        lines = len(response.text.split('\n'))
        log_msg(f"  ✅ Saved to {filepath.name} ({lines} lines)")
        return True

    except Exception as e:
        log_msg(f"  ❌ Failed to download {filename}: {e}")
        return False

def main():
    """Main function with data source discovery."""
    log_msg("=== Enhanced NASCAR Data Download ===")
    log_msg(f"API Key: {BRAVE_API_KEY[:20]}...")
    log_msg()

    # Search for NASCAR historical data sources
    search_queries = [
        "NASCAR historical race results CSV download API",
        "NASCAR Cup Series statistics data source",
        "DraftKings NASCAR salary data CSV",
        "NASCAR driver performance data open source"
    ]

    all_sources = []

    for query in search_queries:
        log_msg(f"Searching: {query}")
        results = search_brave(query, count=3)

        if results:
            log_msg(f"  Found {len(results)} sources")
            all_sources.extend(results)
            for i, result in enumerate(results, 1):
                log_msg(f"    {i}. {result['title'][:60]}")
                log_msg(f"       {result['url']}")
        log_msg()

    # Save discovered sources
    sources_file = HISTORICAL_DIR / "data_sources.json"
    with open(sources_file, 'w') as f:
        json.dump({
            'discovered_at': datetime.now().isoformat(),
            'search_queries': search_queries,
            'sources': all_sources
        }, f, indent=2)

    log_msg(f"✅ Saved {len(all_sources)} sources to {sources_file.name}")
    log_msg()

    # Try to download from discovered sources
    downloaded = []
    for source in all_sources[:10]:  # Try first 10 sources
        url = source['url']
        filename = url.split('/')[-1].split('?')[0]

        # Only download if it looks like a data file
        if any(ext in filename.lower() for ext in ['.csv', '.json', '.parquet']):
            if download_csv_from_url(url, filename):
                downloaded.append(filename)

    # Summary
    summary = {
        'downloaded_at': datetime.now().isoformat(),
        'files_downloaded': downloaded,
        'total_sources_discovered': len(all_sources),
        'api_key_used': BRAVE_API_KEY[:20] + "..."
    }

    summary_file = HISTORICAL_DIR / "download_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)

    log_msg(f"\n=== Summary ===")
    log_msg(f"Sources discovered: {len(all_sources)}")
    log_msg(f"Files downloaded: {len(downloaded)}")
    log_msg(f"Summary saved to: {summary_file.name}")

if __name__ == "__main__":
    main()
