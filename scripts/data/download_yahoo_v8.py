#!/usr/bin/env python3
"""
Download using Yahoo Finance v8 API directly.

Uses the official Yahoo Finance v8 API endpoint with proper rate limiting,
session handling, and better error recovery.
"""

import sys
import time
import json
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import requests
import pandas as pd


class YahooFinanceV8Downloader:
    """Downloader using Yahoo Finance v8 API directly."""

    BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart"

    def __init__(self, delay: float = 5.0, max_retries: int = 5):
        self.delay = delay
        self.max_retries = max_retries
        self.session = requests.Session()
        # Rotate User-Agents to avoid detection
        self.user_agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        ]
        self.current_ua_index = 0

    def _get_headers(self):
        """Get headers with rotating User-Agent."""
        self.current_ua_index = (self.current_ua_index + 1) % len(self.user_agents)
        return {
            'User-Agent': self.user_agents[self.current_ua_index],
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://finance.yahoo.com/',
        }

    def download_symbol(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        output_file: Path,
    ) -> bool:
        """Download historical data for a symbol."""
        if output_file.exists():
            print(f"  ✓ {symbol}: CSV already exists")
            return True

        # Convert dates to Unix timestamps
        period1 = int(start_date.timestamp())
        period2 = int(end_date.timestamp())

        url = f"{self.BASE_URL}/{symbol}"
        params = {
            "period1": period1,
            "period2": period2,
            "interval": "1d",
            "events": "div,splits",
            "includePrePost": "false",
        }

        for attempt in range(self.max_retries):
            try:
                print(
                    f"  📥 {symbol}: Downloading (attempt {attempt + 1}/{self.max_retries})...",
                    end=" ",
                    flush=True,
                )

                resp = self.session.get(
                    url,
                    params=params,
                    headers=self._get_headers(),
                    timeout=30,
                )

                if resp.status_code == 429:
                    # Rate limited - exponential backoff
                    wait_time = self.delay * (2**attempt)
                    print(f"⏳ Rate limited, waiting {wait_time:.0f}s...", flush=True)
                    time.sleep(wait_time)
                    continue

                if resp.status_code != 200:
                    print(f"❌ HTTP {resp.status_code}: {resp.text[:100]}")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.delay)
                        continue
                    return False

                # Parse JSON response
                try:
                    data = resp.json()
                except json.JSONDecodeError as e:
                    print(f"❌ Invalid JSON: {e}")
                    print(f"Response: {resp.text[:200]}")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.delay)
                        continue
                    return False

                # Extract data from response
                if "chart" not in data or not data["chart"]["result"]:
                    print(f"❌ No data in response")
                    return False

                result = data["chart"]["result"][0]

                if "timestamp" not in result or "indicators" not in result:
                    print(f"❌ Invalid response structure")
                    return False

                timestamps = result["timestamp"]
                quote = result["indicators"]["quote"][0]

                # Build DataFrame
                rows = []
                for i, ts in enumerate(timestamps):
                    date = datetime.fromtimestamp(ts)
                    if start_date <= date <= end_date:
                        rows.append(
                            {
                                'date': date,
                                'timestamp': date,
                                'open': quote["open"][i] if i < len(quote["open"]) else None,
                                'high': quote["high"][i] if i < len(quote["high"]) else None,
                                'low': quote["low"][i] if i < len(quote["low"]) else None,
                                'close': quote["close"][i] if i < len(quote["close"]) else None,
                                'volume': quote["volume"][i] if i < len(quote["volume"]) else None,
                            }
                        )

                if not rows:
                    print(f"❌ No data in date range")
                    return False

                # Create DataFrame and save
                df = pd.DataFrame(rows)
                df = df.dropna(subset=['close'])  # Remove rows with no close price

                if df.empty:
                    print(f"❌ No valid data after filtering")
                    return False

                output_file.parent.mkdir(parents=True, exist_ok=True)
                df.to_csv(output_file, index=False)

                print(f"✅ {len(df)} rows saved")

                # Delay between downloads
                if attempt == 0:  # Only delay on first successful attempt
                    time.sleep(self.delay)

                return True

            except requests.exceptions.RequestException as e:
                print(f"❌ Request error: {e}")
                if attempt < self.max_retries - 1:
                    wait_time = self.delay * (2**attempt)
                    time.sleep(wait_time)
                    continue
                return False
            except (FileNotFoundError, PermissionError, IOError, OSError, IsADirectoryError) as e:
                print(f"❌ Unexpected error: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.delay)
                    continue
                return False

        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/download_yahoo_v8.py SYMBOL [SYMBOL2 ...]")
        print("Example: python scripts/download_yahoo_v8.py AEP BAC KO")
        sys.exit(1)

    symbols = [s.upper() for s in sys.argv[1:]]

    print("=" * 80)
    print("📥 Download using Yahoo Finance v8 API")
    print("=" * 80)
    print(f"Symbols: {', '.join(symbols)}")
    print("Period: 10 years")
    print("=" * 80)

    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365 * 10)

    downloader = YahooFinanceV8Downloader(delay=6.0, max_retries=5)

    successful = []
    failed = []

    for i, symbol in enumerate(symbols, 1):
        print(f"[{i}/{len(symbols)}] {symbol}: ", end="", flush=True)

        output_file = Path("data/historical") / f"{symbol}.csv"

        success = downloader.download_symbol(
            symbol,
            start_date,
            end_date,
            output_file,
        )

        if success:
            successful.append(symbol)
        else:
            failed.append(symbol)

    print("\n" + "=" * 80)
    print(f"✅ Successful: {len(successful)}/{len(symbols)}")
    print(f"❌ Failed: {len(failed)}/{len(symbols)}")

    if successful:
        print(f"\n✅ Downloaded: {', '.join(successful)}")

    if failed:
        print(f"\n❌ Failed: {', '.join(failed)}")
        print("\n💡 Tip: Wait 10-15 minutes and retry failed symbols")

    return 0 if len(failed) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
