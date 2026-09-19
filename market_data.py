import json
import os
import time
from datetime import datetime, timedelta

import requests


# ============================================================
# YAHOO FINANCE
# ============================================================

YAHOO_URLS = [
    "https://query1.finance.yahoo.com/v8/finance/chart/",
    "https://query2.finance.yahoo.com/v8/finance/chart/",
]


# ============================================================
# SETTINGS
# ============================================================

REQUEST_TIMEOUT = 20

MAX_RETRIES = 4

# Wait approximately:
# attempt 1 -> 3 seconds
# attempt 2 -> 6 seconds
# attempt 3 -> 12 seconds
# attempt 4 -> 24 seconds
RETRY_DELAYS = [3, 6, 12, 24]

# Cache lifetime.
#
# Historical daily data does not need to be downloaded
# every time RUN TEST is pressed.
CACHE_HOURS = 6


# ============================================================
# CACHE DIRECTORY
# ============================================================

def _cache_directory():

    try:
        base = os.path.expanduser(
            "~"
        )

        path = os.path.join(
            base,
            ".sri_bhoovalaya_cache",
        )

        os.makedirs(
            path,
            exist_ok=True,
        )

        return path

    except Exception:

        return "."


def _cache_file(
    symbol,
    period_days,
):

    safe_symbol = (
        symbol
        .replace("/", "_")
        .replace("\\", "_")
        .replace(":", "_")
    )

    filename = (
        f"{safe_symbol}_{period_days}.json"
    )

    return os.path.join(
        _cache_directory(),
        filename,
    )


# ============================================================
# DATE CONVERSION
# ============================================================

def _to_date(timestamp):

    return datetime.fromtimestamp(
        int(timestamp)
    ).date()


# ============================================================
# CACHE LOAD
# ============================================================

def _load_cache(
    symbol,
    period_days,
):

    path = _cache_file(
        symbol,
        period_days,
    )

    try:

        if not os.path.exists(path):
            return None

        modified = os.path.getmtime(
            path
        )

        age_hours = (
            time.time() - modified
        ) / 3600.0

        if age_hours > CACHE_HOURS:
            return None

        with open(
            path,
            "r",
            encoding="utf-8",
        ) as f:

            saved = json.load(f)

        if not isinstance(
            saved,
            list,
        ):
            return None

        data = []

        for row in saved:

            if not isinstance(
                row,
                dict,
            ):
                continue

            if "date" not in row:
                continue

            item = dict(row)

            # JSON stores dates as strings.
            item["date"] = datetime.strptime(
                item["date"],
                "%Y-%m-%d",
            ).date()

            data.append(item)

        if not data:
            return None

        return data

    except Exception:

        return None


# ============================================================
# CACHE SAVE
# ============================================================

def _save_cache(
    symbol,
    period_days,
    data,
):

    path = _cache_file(
        symbol,
        period_days,
    )

    try:

        serializable = []

        for row in data:

            item = dict(row)

            date_value = item.get(
                "date"
            )

            if hasattr(
                date_value,
                "isoformat",
            ):
                item["date"] = (
                    date_value.isoformat()
                )

            serializable.append(
                item
            )

        with open(
            path,
            "w",
            encoding="utf-8",
        ) as f:

            json.dump(
                serializable,
                f,
            )

    except Exception:

        # Cache failure should never
        # stop the application.
        pass


# ============================================================
# HEADERS
# ============================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Linux; Android 10) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/120.0 Mobile Safari/537.36"
    ),

    "Accept": (
        "application/json,text/plain,*/*"
    ),
}


# ============================================================
# YAHOO DOWNLOAD
# ============================================================

def _download_from_yahoo(
    symbol,
    period_days,
):

    calendar_days = max(
        int(period_days * 1.7),
        30,
    )

    end_date = datetime.utcnow()

    start_date = (
        end_date
        - timedelta(
            days=calendar_days
        )
    )

    period1 = int(
        start_date.timestamp()
    )

    period2 = int(
        end_date.timestamp()
    )

    params = {
        "period1": period1,
        "period2": period2,
        "interval": "1d",
        "events": "history",
        "includeAdjustedClose": "true",
    }

    last_error = None

    # Try query1 and then query2.
    for base_url in YAHOO_URLS:

        url = (
            base_url
            + symbol
        )

        for attempt in range(
            MAX_RETRIES
        ):

            try:

                response = requests.get(
                    url,
                    params=params,
                    headers=HEADERS,
                    timeout=REQUEST_TIMEOUT,
                )

                # ------------------------------------------------
                # HTTP 429
                # ------------------------------------------------

                if response.status_code == 429:

                    last_error = (
                        "Yahoo Finance returned "
                        "HTTP 429 Too Many Requests."
                    )

                    if attempt < MAX_RETRIES - 1:

                        wait_seconds = (
                            RETRY_DELAYS[
                                attempt
                            ]
                        )

                        time.sleep(
                            wait_seconds
                        )

                        continue

                    # Try the other Yahoo endpoint.
                    break

                # ------------------------------------------------
                # Other HTTP errors
                # ------------------------------------------------

                response.raise_for_status()

                payload = response.json()

                chart = payload.get(
                    "chart",
                    {},
                )

                error = chart.get(
                    "error"
                )

                if error:

                    description = error.get(
                        "description",
                        "Yahoo Finance error",
                    )

                    last_error = (
                        str(description)
                    )

                    break

                results = chart.get(
                    "result"
                )

                if not results:

                    last_error = (
                        "No Yahoo Finance result returned."
                    )

                    break

                result = results[0]

                timestamps = result.get(
                    "timestamp",
                    [],
                )

                quote_list = (
                    result
                    .get(
                        "indicators",
                        {},
                    )
                    .get(
                        "quote",
                        [],
                    )
                )

                if not quote_list:

                    last_error = (
                        "No quote data returned."
                    )

                    break

                quote = quote_list[0]

                opens = quote.get(
                    "open",
                    [],
                )

                highs = quote.get(
                    "high",
                    [],
                )

                lows = quote.get(
                    "low",
                    [],
                )

                closes = quote.get(
                    "close",
                    [],
                )

                volumes = quote.get(
                    "volume",
                    [],
                )

                data = []

                for i, timestamp in enumerate(
                    timestamps
                ):

                    if i >= len(closes):
                        continue

                    close = closes[i]

                    if close is None:
                        continue

                    open_value = (
                        opens[i]
                        if i < len(opens)
                        else None
                    )

                    high_value = (
                        highs[i]
                        if i < len(highs)
                        else None
                    )

                    low_value = (
                        lows[i]
                        if i < len(lows)
                        else None
                    )

                    volume_value = (
                        volumes[i]
                        if i < len(volumes)
                        else 0
                    )

                    if open_value is None:
                        open_value = close

                    if high_value is None:
                        high_value = close

                    if low_value is None:
                        low_value = close

                    if volume_value is None:
                        volume_value = 0

                    data.append(
                        {
                            "date": _to_date(
                                timestamp
                            ),

                            "open": float(
                                open_value
                            ),

                            "high": float(
                                high_value
                            ),

                            "low": float(
                                low_value
                            ),

                            "close": float(
                                close
                            ),

                            "volume": int(
                                volume_value
                            ),
                        }
                    )

                # Keep chronological order.
                data.sort(
                    key=lambda x: x["date"]
                )

                # Return requested number of
                # trading sessions.
                if len(data) > period_days:

                    data = data[
                        -period_days:
                    ]

                if not data:

                    last_error = (
                        "Yahoo Finance returned "
                        "no usable price data."
                    )

                    break

                return data

            except requests.RequestException as ex:

                last_error = str(ex)

                if attempt < MAX_RETRIES - 1:

                    wait_seconds = (
                        RETRY_DELAYS[
                            attempt
                        ]
                    )

                    time.sleep(
                        wait_seconds
                    )

                    continue

                break

            except ValueError as ex:

                last_error = (
                    "Invalid Yahoo Finance response: "
                    + str(ex)
                )

                break

            except Exception as ex:

                last_error = str(ex)

                break

    # Both Yahoo endpoints failed.
    raise RuntimeError(
        last_error
        or "Unable to download Yahoo Finance data."
    )


# ============================================================
# STOCK HISTORY
# ============================================================

def get_stock_history(
    symbol,
    period_days=30,
):

    """
    Download historical daily OHLC data.

    Uses local cache first.

    Returns:

        [
            {
                "date": date,
                "open": float,
                "high": float,
                "low": float,
                "close": float,
                "volume": int,
            }
        ]
    """

    symbol = (
        symbol
        .strip()
        .upper()
    )

    if not symbol:

        raise ValueError(
            "Stock symbol is empty."
        )

    try:

        period_days = int(
            period_days
        )

    except Exception:

        period_days = 30

    if period_days < 1:

        period_days = 30

    # --------------------------------------------------------
    # FIRST: USE CACHE
    # --------------------------------------------------------

    cached = _load_cache(
        symbol,
        period_days,
    )

    if cached:

        return cached

    # --------------------------------------------------------
    # DOWNLOAD
    # --------------------------------------------------------

    data = _download_from_yahoo(
        symbol,
        period_days,
    )

    # --------------------------------------------------------
    # SAVE CACHE
    # --------------------------------------------------------

    _save_cache(
        symbol,
        period_days,
        data,
    )

    return data


# ============================================================
# LAST CLOSE
# ============================================================

def get_last_close(
    symbol,
):

    """
    Convenience function.
    """

    data = get_stock_history(
        symbol,
        period_days=5,
    )

    if not data:

        return None

    return data[-1]["close"]


# ============================================================
# DESKTOP TEST
# ============================================================

if __name__ == "__main__":

    symbol = "RELIANCE.NS"

    try:

        data = get_stock_history(
            symbol,
            period_days=20,
        )

        print(
            f"Downloaded {len(data)} sessions."
        )

        for row in data:

            print(
                row["date"],
                row["close"],
            )

    except Exception as ex:

        print(
            "ERROR:",
            type(ex).__name__,
            ex,
        )
