import json
import os
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta


# ============================================================
# YAHOO FINANCE
# ============================================================

YAHOO_HOSTS = (
    "query1.finance.yahoo.com",
    "query2.finance.yahoo.com",
)

YAHOO_CHART_PATH = "/v8/finance/chart/{symbol}"


# ============================================================
# SETTINGS
# ============================================================

REQUEST_TIMEOUT = 15

# Keep retries deliberately small. Repeated requests can make
# an HTTP 429 situation worse rather than better.
MAX_ROUNDS = 2
RETRY_DELAY_SECONDS = 5

# Fresh cache is used without any network request.
CACHE_FRESH_SECONDS = 6 * 3600

# Stale cache is retained so the APK can still operate if Yahoo
# temporarily returns HTTP 429 or is unavailable.
MAX_STALE_SECONDS = 30 * 24 * 3600

MIN_DAYS = 12
MAX_DAYS = 730


# ============================================================
# ANDROID-SAFE CACHE LOCATION
# ============================================================

def _cache_directory():
    """
    Prefer Flet's application storage directory on Android.
    Fall back to the user's home directory and finally /tmp.
    """
    candidates = []

    flet_storage = os.environ.get("FLET_APP_STORAGE_DATA")
    if flet_storage:
        candidates.append(flet_storage)

    try:
        candidates.append(os.path.join(
            os.path.expanduser("~"),
            ".sri_bhoovalaya_cache",
        ))
    except Exception:
        pass

    candidates.append(os.path.join(
        tempfile.gettempdir(),
        "sri_bhoovalaya_cache",
    ))

    for path in candidates:
        try:
            os.makedirs(path, exist_ok=True)
            test_file = os.path.join(path, ".write_test")
            with open(test_file, "a", encoding="utf-8"):
                pass
            try:
                os.remove(test_file)
            except Exception:
                pass
            return path
        except Exception:
            continue

    return "."


def _cache_file(symbol, period_days):
    safe_symbol = "".join(
        ch if ch.isalnum() else "_"
        for ch in str(symbol).strip().upper()
    )

    return os.path.join(
        _cache_directory(),
        f"{safe_symbol}_{int(period_days)}.json",
    )


# ============================================================
# DATE / CACHE
# ============================================================

def _to_date(timestamp, offset_seconds=0):
    """
    Yahoo timestamps are UTC epoch seconds.
    Apply the exchange offset returned by Yahoo when available.
    """
    epoch = datetime(1970, 1, 1)
    return (
        epoch
        + timedelta(
            seconds=int(timestamp) + int(offset_seconds)
        )
    ).date()


def _cache_load(symbol, period_days):
    """
    Return:
        (data, age_seconds)
    or None.
    """
    path = _cache_file(symbol, period_days)

    try:
        if not os.path.exists(path):
            return None

        with open(path, "r", encoding="utf-8") as f:
            blob = json.load(f)

        if not isinstance(blob, dict):
            return None

        saved_at = float(blob.get("saved_at", 0))
        rows = blob.get("rows", [])

        if not saved_at or not isinstance(rows, list):
            return None

        data = []

        for row in rows:
            if not isinstance(row, dict):
                continue

            if "date" not in row or "close" not in row:
                continue

            item = dict(row)

            item["date"] = datetime.strptime(
                str(item["date"]),
                "%Y-%m-%d",
            ).date()

            item["close"] = float(item["close"])

            # These are not essential to the current engine, but
            # keeping them makes the module compatible with the
            # previous market_data.py interface.
            item["open"] = float(item.get("open", item["close"]))
            item["high"] = float(item.get("high", item["close"]))
            item["low"] = float(item.get("low", item["close"]))
            item["volume"] = int(item.get("volume", 0))

            data.append(item)

        data.sort(key=lambda x: x["date"])

        if not data:
            return None

        age = max(0.0, time.time() - saved_at)

        return data, age

    except Exception:
        return None


def _cache_save(symbol, period_days, data):
    path = _cache_file(symbol, period_days)

    try:
        rows = []

        for row in data:
            item = dict(row)

            date_value = item.get("date")

            if hasattr(date_value, "isoformat"):
                item["date"] = date_value.isoformat()
            else:
                item["date"] = str(date_value)

            rows.append(item)

        blob = {
            "saved_at": time.time(),
            "rows": rows,
        }

        temporary = path + ".tmp"

        with open(
            temporary,
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(blob, f)

        # Atomic replacement where supported.
        os.replace(temporary, path)

    except Exception:
        try:
            if os.path.exists(temporary):
                os.remove(temporary)
        except Exception:
            pass


# ============================================================
# YAHOO REQUEST
# ============================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 13) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/124.0 Mobile Safari/537.36"
    ),
    "Accept": "application/json,text/plain,*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://finance.yahoo.com/",
}


def _request_history(host, symbol, days):
    """
    Make ONE request to ONE Yahoo endpoint.
    """
    now = int(time.time())

    # Enough calendar days for approximately `days` trading sessions.
    calendar_days = max(
        int(days * 7 / 5) + 14,
        30,
    )

    params = urllib.parse.urlencode({
        "period1": now - calendar_days * 86400,
        "period2": now,
        "interval": "1d",
        "events": "history",
        "includeAdjustedClose": "true",
    })

    encoded_symbol = urllib.parse.quote(
        symbol,
        safe="",
    )

    url = (
        "https://"
        + host
        + YAHOO_CHART_PATH.format(encoded_symbol)
        + "?"
        + params
    )

    request = urllib.request.Request(
        url,
        headers=HEADERS,
    )

    with urllib.request.urlopen(
        request,
        timeout=REQUEST_TIMEOUT,
    ) as response:

        status = getattr(
            response,
            "status",
            200,
        )

        if status != 200:
            raise RuntimeError(
                f"HTTP {status}"
            )

        raw = response.read().decode(
            "utf-8",
            errors="replace",
        )

    payload = json.loads(raw)

    chart = (payload or {}).get("chart") or {}

    error = chart.get("error")

    if error:
        description = (
            error.get("description")
            if isinstance(error, dict)
            else str(error)
        )

        raise RuntimeError(
            str(description or "Yahoo Finance error")
        )

    results = chart.get("result") or []

    if not results:
        raise RuntimeError(
            "No Yahoo Finance result returned."
        )

    result = results[0]

    timestamps = result.get("timestamp") or []

    quote_list = (
        (result.get("indicators") or {})
        .get("quote")
        or []
    )

    if not quote_list:
        raise RuntimeError(
            "No Yahoo quote data returned."
        )

    quote = quote_list[0]

    opens = quote.get("open") or []
    highs = quote.get("high") or []
    lows = quote.get("low") or []
    closes = quote.get("close") or []
    volumes = quote.get("volume") or []

    meta = result.get("meta") or {}

    # Yahoo normally supplies gmtoffset. For NSE symbols this
    # should be +19800 (IST). If absent, use IST.
    offset = meta.get("gmtoffset")

    if offset is None:
        offset = 19800

    data = []

    for i, timestamp in enumerate(timestamps):

        if i >= len(closes):
            continue

        close = closes[i]

        if close is None:
            continue

        open_value = (
            opens[i]
            if i < len(opens)
            and opens[i] is not None
            else close
        )

        high_value = (
            highs[i]
            if i < len(highs)
            and highs[i] is not None
            else close
        )

        low_value = (
            lows[i]
            if i < len(lows)
            and lows[i] is not None
            else close
        )

        volume_value = (
            volumes[i]
            if i < len(volumes)
            and volumes[i] is not None
            else 0
        )

        data.append({
            "date": _to_date(
                timestamp,
                offset,
            ),
            "open": float(open_value),
            "high": float(high_value),
            "low": float(low_value),
            "close": float(close),
            "volume": int(volume_value),
        })

    data.sort(
        key=lambda x: x["date"]
    )

    if len(data) > days:
        data = data[-days:]

    if not data:
        raise RuntimeError(
            "Yahoo Finance returned no usable price data."
        )

    return data


def _download_history(symbol, days):
    """
    Controlled Yahoo download.

    Unlike the previous engine, this does NOT repeatedly hammer
    Yahoo. Each round tries query1 and query2 once.
    """
    last_error = "Unknown Yahoo Finance error"

    for round_no in range(MAX_ROUNDS):

        for host in YAHOO_HOSTS:

            try:
                return _request_history(
                    host,
                    symbol,
                    days,
                )

            except urllib.error.HTTPError as ex:

                last_error = (
                    f"HTTP Error {ex.code}: "
                    f"{ex.reason}"
                )

                # 429 means rate-limited. Try the other endpoint
                # once, then stop rather than making many requests.
                if ex.code == 429:
                    continue

                # Temporary server errors can be tried again.
                if ex.code in (
                    500,
                    502,
                    503,
                    504,
                ):
                    continue

                # Other errors are normally not helped by retrying.
                raise RuntimeError(last_error)

            except urllib.error.URLError as ex:

                last_error = (
                    "Network error: "
                    + str(ex.reason)
                )

                continue

            except TimeoutError as ex:

                last_error = (
                    "Network timeout: "
                    + str(ex)
                )

                continue

            except json.JSONDecodeError as ex:

                last_error = (
                    "Yahoo returned an invalid response: "
                    + str(ex)
                )

                continue

            except Exception as ex:

                last_error = str(ex)
                continue

        if round_no < MAX_ROUNDS - 1:
            time.sleep(
                RETRY_DELAY_SECONDS
            )

    raise RuntimeError(last_error)


# ============================================================
# PUBLIC PRICE HISTORY
# ============================================================

def fetch_price_history_ex(
    symbol,
    days=60,
    timezone_name="Asia/Kolkata",
):
    """
    Returns:

        (rows, source)

    source:
        "live"          fresh Yahoo download
        "cache"         fresh local cache
        "stale-cache"   older cache used because online
                        download failed

    The timezone argument is retained for compatibility with
    bhoovalaya_engine.py. Yahoo's exchange date/offset is used
    for the actual daily dates.
    """

    symbol = str(symbol or "").strip().upper()

    if not symbol:
        raise ValueError(
            "Stock symbol is empty."
        )

    try:
        days = int(days)
    except Exception:
        days = 60

    days = max(
        MIN_DAYS,
        min(days, MAX_DAYS),
    )

    cached = _cache_load(
        symbol,
        days,
    )

    # --------------------------------------------------------
    # Fresh cache: NO network request.
    # --------------------------------------------------------
    if cached:

        cached_rows, age = cached

        if age <= CACHE_FRESH_SECONDS:
            return (
                cached_rows,
                "cache",
            )

    # --------------------------------------------------------
    # Try online source only when cache is not fresh.
    # --------------------------------------------------------
    try:

        rows = _download_history(
            symbol,
            days,
        )

        if len(rows) < MIN_DAYS:
            raise RuntimeError(
                f"Only {len(rows)} price rows found "
                f"for {symbol}; at least "
                f"{MIN_DAYS} are required."
            )

        _cache_save(
            symbol,
            days,
            rows,
        )

        return (
            rows,
            "live",
        )

    except Exception as online_error:

        # ----------------------------------------------------
        # IMPORTANT:
        # If Yahoo returns 429 but we have usable older data,
        # continue with that data instead of crashing.
        # ----------------------------------------------------
        if cached:

            cached_rows, age = cached

            if age <= MAX_STALE_SECONDS:

                return (
                    cached_rows,
                    "stale-cache",
                )

        raise ValueError(
            f"Could not download price data for "
            f"{symbol}: {online_error}. "
            f"No usable cached data is available."
        )


def get_stock_history(
    symbol,
    period_days=30,
):
    """
    Compatibility function for existing code.

    Returns only the data list.
    """
    rows, _source = fetch_price_history_ex(
        symbol,
        days=period_days,
        timezone_name="Asia/Kolkata",
    )

    return rows


def get_last_close(symbol):
    """
    Compatibility function.
    """
    data = get_stock_history(
        symbol,
        period_days=5,
    )

    if not data:
        return None

    return data[-1]["close"]


def fetch_price_history(
    symbol,
    days=60,
    timezone_name="Asia/Kolkata",
):
    """
    Compatibility wrapper returning only rows.
    """
    return fetch_price_history_ex(
        symbol,
        days=days,
        timezone_name=timezone_name,
    )[0]


# ============================================================
# DESKTOP / ANDROID TEST
# ============================================================

if __name__ == "__main__":

    symbol = "RELIANCE.NS"

    try:

        data, source = fetch_price_history_ex(
            symbol,
            days=20,
            timezone_name="Asia/Kolkata",
        )

        print(
            "Source:",
            source,
        )

        print(
            "Downloaded/loaded:",
            len(data),
            "sessions",
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
