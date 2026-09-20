"""
NSE-first historical market data for Sri Bhoovalaya.

Downloads NSE India historical equity data, saves it locally as CSV,
and reuses the saved data for the Bhoovalaya test.
"""

import csv
import json
import os
import time
from datetime import date, datetime, timedelta

import requests

NSE_HOME = "https://www.nseindia.com/"
NSE_HISTORICAL_API = "https://www.nseindia.com/api/historical/cm/equity"

REQUEST_TIMEOUT = 20
CACHE_MAX_AGE_SECONDS = 6 * 3600
MAX_RANGE_DAYS = 365

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/153.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json,text/plain,*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
    "Connection": "keep-alive",
}


def _storage_directory():
    candidates = []

    flet_dir = os.environ.get("FLET_APP_STORAGE_DATA")
    if flet_dir:
        candidates.append(flet_dir)

    candidates.append(
        os.path.join(os.path.expanduser("~"), ".sri_bhoovalaya_cache")
    )
    candidates.append(os.path.join(os.getcwd(), "data"))
    candidates.append(os.path.abspath(os.path.dirname(__file__)))

    for directory in candidates:
        try:
            os.makedirs(directory, exist_ok=True)
            test = os.path.join(directory, ".write_test")
            with open(test, "w", encoding="utf-8") as f:
                f.write("ok")
            os.remove(test)
            return directory
        except Exception:
            continue

    return os.getcwd()


def _safe_symbol(symbol):
    return "".join(ch if ch.isalnum() else "_" for ch in (symbol or "").upper())


def _nse_symbol(symbol):
    value = (symbol or "").strip().upper()
    if value.endswith(".NS"):
        value = value[:-3]
    return value


def get_cache_csv_path(symbol):
    return os.path.join(
        _storage_directory(),
        f"{_safe_symbol(symbol)}_NSE.csv",
    )


def get_cache_meta_path(symbol):
    return os.path.join(
        _storage_directory(),
        f"{_safe_symbol(symbol)}_NSE.json",
    )


def _read_cached_csv(symbol):
    path = get_cache_csv_path(symbol)
    if not os.path.exists(path):
        return None

    rows = []
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                d = row.get("Date") or row.get("date")
                close = row.get("Close") or row.get("close")
                if not d or close in (None, ""):
                    continue
                try:
                    parsed_date = datetime.strptime(str(d).strip(), "%Y-%m-%d").date()
                    parsed_close = float(str(close).replace(",", "").strip())
                except Exception:
                    continue
                rows.append({"date": parsed_date, "close": parsed_close})
        rows.sort(key=lambda x: x["date"])
        return rows if rows else None
    except Exception:
        return None


def _cache_age(symbol):
    path = get_cache_meta_path(symbol)
    try:
        with open(path, "r", encoding="utf-8") as f:
            saved = json.load(f)
        return max(0.0, time.time() - float(saved["saved_at"]))
    except Exception:
        path = get_cache_csv_path(symbol)
        try:
            return max(0.0, time.time() - os.path.getmtime(path))
        except Exception:
            return None


def _save_rows(symbol, rows):
    csv_path = get_cache_csv_path(symbol)
    meta_path = get_cache_meta_path(symbol)

    temp_csv = csv_path + ".tmp"
    with open(temp_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Date", "Close"])
        for row in rows:
            writer.writerow([str(row["date"]), f'{float(row["close"]):.4f}'])
    os.replace(temp_csv, csv_path)

    temp_meta = meta_path + ".tmp"
    with open(temp_meta, "w", encoding="utf-8") as f:
        json.dump(
            {
                "saved_at": time.time(),
                "source": "NSE India",
                "symbol": symbol,
                "rows": len(rows),
                "csv": csv_path,
            },
            f,
            indent=2,
        )
    os.replace(temp_meta, meta_path)
    return csv_path


def _parse_nse_date(value):
    text = str(value or "").strip()
    for fmt in ("%d-%b-%Y", "%d-%b-%Y %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except Exception:
            pass
    return None


def _parse_number(value):
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if not text or text.lower() in ("none", "null", "-"):
        return None
    try:
        return float(text)
    except Exception:
        return None


def _request_nse_json(session, symbol, from_date, to_date):
    params = {
        "symbol": _nse_symbol(symbol),
        "series": '["EQ"]',
        "from": from_date.strftime("%d-%m-%Y"),
        "to": to_date.strftime("%d-%m-%Y"),
    }

    # The NSE historical endpoint is documented/used as the security-wise
    # historical equity endpoint. A session is used because NSE may set
    # cookies on the homepage before allowing the API request.
    response = session.get(
        NSE_HISTORICAL_API,
        params=params,
        timeout=REQUEST_TIMEOUT,
    )

    if response.status_code != 200:
        raise ValueError(
            f"NSE HTTP {response.status_code}: {response.text[:300]}"
        )

    try:
        payload = response.json()
    except Exception:
        raise ValueError("NSE returned a non-JSON response.")

    if isinstance(payload, dict):
        if payload.get("error"):
            raise ValueError(str(payload["error"]))
        data = payload.get("data")
        if data is None:
            records = payload.get("records") or {}
            data = records.get("data", []) if isinstance(records, dict) else []
    else:
        data = payload

    if not isinstance(data, list):
        raise ValueError("Unexpected NSE historical-data format.")

    return data


def _download_nse_history(symbol, period_days):
    period_days = max(12, min(int(period_days), 730))

    end_date = date.today()
    calendar_span = max(30, int(period_days * 1.8) + 14)
    start_date = end_date - timedelta(days=calendar_span)

    session = requests.Session()
    session.headers.update(HEADERS)

    # Establish NSE session cookies first.
    home = session.get(NSE_HOME, timeout=REQUEST_TIMEOUT)
    if home.status_code >= 400:
        raise ValueError(f"NSE homepage HTTP {home.status_code}")

    all_rows = []
    cursor = start_date

    while cursor <= end_date:
        chunk_end = min(end_date, cursor + timedelta(days=MAX_RANGE_DAYS - 1))
        records = _request_nse_json(session, symbol, cursor, chunk_end)

        for item in records:
            d = _parse_nse_date(
                item.get("CH_TIMESTAMP")
                or item.get("Date")
                or item.get("date")
            )
            close = _parse_number(
                item.get("CH_CLOSING_PRICE")
                if "CH_CLOSING_PRICE" in item
                else item.get("close")
            )
            if d is not None and close is not None:
                all_rows.append({"date": d, "close": close})

        cursor = chunk_end + timedelta(days=1)

    unique = {row["date"]: row for row in all_rows}
    rows = [unique[d] for d in sorted(unique)]

    if not rows:
        raise ValueError(
            f"NSE returned no historical data for {_nse_symbol(symbol)}."
        )

    return rows[-period_days:]


def update_stock_history(symbol, period_days=60):
    """Force a fresh NSE download, save CSV, and return (rows, csv_path)."""
    symbol = (symbol or "").strip().upper()
    if not symbol:
        raise ValueError("Stock symbol is empty.")

    rows = _download_nse_history(symbol, period_days)
    if len(rows) < min(10, int(period_days)):
        raise ValueError(f"NSE returned only {len(rows)} sessions for {symbol}.")

    path = _save_rows(symbol, rows)
    return rows, path


def get_stock_history(symbol, period_days=60, force_refresh=False):
    """
    Normal RUN TEST uses recent saved NSE data. If none exists, it downloads
    automatically. UPDATE MARKET DATA calls this with force_refresh=True.
    """
    symbol = (symbol or "").strip().upper()
    if not symbol:
        raise ValueError("Stock symbol is empty.")

    period_days = max(12, min(int(period_days), 730))
    cached = _read_cached_csv(symbol)
    age = _cache_age(symbol)

    if (
        not force_refresh
        and cached
        and len(cached) >= min(10, period_days)
        and age is not None
        and age < CACHE_MAX_AGE_SECONDS
    ):
        return cached[-period_days:]

    try:
        rows, _ = update_stock_history(symbol, period_days)
        return rows
    except Exception as ex:
        # Never discard a previously downloaded NSE dataset because NSE is
        # temporarily unavailable.
        if cached and len(cached) >= 10:
            return cached[-period_days:]
        raise ValueError(f"Could not obtain NSE data for {symbol}: {ex}")


def get_last_close(symbol):
    rows = get_stock_history(symbol, period_days=12)
    return rows[-1]["close"] if rows else None


def fetch_price_history_ex(symbol, days=60, timezone_name="Asia/Kolkata"):
    """Compatibility API used by bhoovalaya_engine.py."""
    symbol = (symbol or "").strip().upper()
    days = max(12, min(int(days), 730))

    cached = _read_cached_csv(symbol)
    age = _cache_age(symbol)
    if (
        cached
        and len(cached) >= min(10, days)
        and age is not None
        and age < CACHE_MAX_AGE_SECONDS
    ):
        return cached[-days:], "nse-cache"

    try:
        rows, _ = update_stock_history(symbol, days)
        return rows, "nse-live"
    except Exception as ex:
        if cached and len(cached) >= 10:
            return cached[-days:], "nse-stale"
        raise ValueError(f"Could not download NSE price data for {symbol}: {ex}")


def fetch_price_history(symbol, days=60, timezone_name="Asia/Kolkata"):
    return fetch_price_history_ex(symbol, days, timezone_name)[0]


if __name__ == "__main__":
    rows, path = update_stock_history("RELIANCE.NS", 60)
    print(f"Downloaded {len(rows)} NSE sessions")
    print(f"Saved: {path}")
    print("First:", rows[0])
    print("Last :", rows[-1])
