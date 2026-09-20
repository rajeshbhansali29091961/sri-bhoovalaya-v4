et data · PY
"""
market_data.py - NSE India price history for Sri Bhoovalaya.
 
    NSE India  ->  CSV file on the device  ->  list of daily closes
 
Public functions (exactly what main.py calls):
 
    get_stock_history(symbol, period_days=60, force_refresh=False)
        -> [{"date": datetime.date, "close": float}, ...]
    update_stock_history(symbol, period_days=60)
        -> (rows, csv_path)          always downloads from NSE
    get_cache_csv_path(symbol)
        -> path of the saved CSV file
 
Download order: nselib (if it is bundled in the app), then the same
NSE report fetched directly with the standard library.
Yahoo Finance is not used.
"""
 
from datetime import datetime, timedelta, timezone
import csv
import gzip
import http.cookiejar
import io
import os
import re
import ssl
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
 
 
# Set to False to skip nselib and always use the direct download.
USE_NSELIB = True
 
NSE_ORIGIN_URL = "https://www.nseindia.com/report-detail/eq_security"
 
NSE_API_URL = (
    "https://www.nseindia.com/api/historicalOR/"
    "generateSecurityWiseHistoricalData?"
)
 
# Same browser-like headers nselib sends (Accept-Encoding limited
# to gzip, which is the only compression handled below).
NSE_PAGE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/130.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
    "Accept-Encoding": "gzip",
}
 
NSE_API_HEADERS = {
    "User-Agent": NSE_PAGE_HEADERS["User-Agent"],
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
    "Accept-Encoding": "gzip",
    "Referer": "https://www.nseindia.com/",
    "Connection": "keep-alive",
}
 
DMY = "%d-%m-%Y"
 
# NSE allows at most one year per request.
NSE_MAX_CHUNK_DAYS = 364
 
# 10 sessions are needed for the "previous 9" table,
# a few more give the backtest something to work with.
MIN_DAYS = 12
MAX_DAYS = 730
 
# A CSV downloaded less than this long ago is reused as it is.
CACHE_FRESH_SECONDS = 2 * 3600
 
# Download attempts, and the pause between them.
FETCH_ATTEMPTS = 3
RETRY_PAUSE_SECONDS = 2.0
 
RETRY_CODES = (401, 403, 429, 500, 502, 503, 504)
 
_DATE_FORMATS = (
    "%d-%b-%Y",
    "%d-%B-%Y",
    "%d-%m-%Y",
    "%Y-%m-%d",
    "%d/%m/%Y",
)
 
 
# ------------------------------------------------------------
# symbol / dates
# ------------------------------------------------------------
 
def normalize_nse_symbol(symbol):
    """
    "RELIANCE.NS" / "reliance" / "NSE:RELIANCE"  ->  "RELIANCE"
    """
 
    s = (symbol or "").strip().upper()
 
    if s.startswith("NSE:"):
        s = s[4:]
 
    if s.endswith(".BO") or s.endswith(".BSE"):
        raise ValueError(
            "BSE symbols are not supported - NSE data only. "
            "Use the NSE symbol, for example RELIANCE."
        )
 
    if s.endswith(".NS"):
        s = s[:-3]
 
    if not s:
        raise ValueError("Stock symbol is empty.")
 
    if not re.fullmatch(r"[A-Z0-9&_\-]+", s):
        raise ValueError(
            f"'{s}' is not a valid NSE symbol."
        )
 
    return s
 
 
def _india_today():
    """Today's date in IST (UTC+5:30), no timezone database needed."""
 
    return (
        datetime.now(timezone.utc)
        + timedelta(hours=5, minutes=30)
    ).date()
 
 
# ------------------------------------------------------------
# CSV parsing
# ------------------------------------------------------------
 
def _to_float(text):
 
    if text is None:
        return None
 
    t = str(text).replace(",", "").replace('"', "").strip()
 
    if t in ("", "-", "nan", "NaN", "None"):
        return None
 
    try:
        return float(t)
    except ValueError:
        return None
 
 
def _to_date(text):
 
    t = str(text or "").strip()
 
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(t, fmt).date()
        except ValueError:
            continue
 
    return None
 
 
def parse_nse_csv(text):
    """
    Reads an NSE security-wise price CSV (raw NSE file or the
    nselib DataFrame saved with to_csv) into
    [{"date": datetime.date, "close": float}, ...]
    ordered oldest -> newest.
    """
 
    reader = csv.reader(io.StringIO(text or ""))
 
    date_i = close_i = series_i = None
    header_found = False
 
    picked = []
 
    for cells in reader:
 
        if not cells:
            continue
 
        if not header_found:
 
            names = [
                c.replace("\ufeff", "")
                .replace(" ", "")
                .strip()
                .lower()
                for c in cells
            ]
 
            if "date" in names:
                for key in (
                    "closeprice",
                    "close",
                    "closingprice",
                ):
                    if key in names:
                        date_i = names.index("date")
                        close_i = names.index(key)
                        series_i = (
                            names.index("series")
                            if "series" in names
                            else None
                        )
                        header_found = True
                        break
 
            # Anything before the header row is ignored.
            continue
 
        # A header repeated in the middle (joined chunks) is skipped.
        if len(cells) <= max(date_i, close_i):
            continue
 
        d = _to_date(cells[date_i])
        c = _to_float(cells[close_i])
 
        if d is None or c is None:
            continue
 
        series = (
            cells[series_i].strip().upper()
            if series_i is not None and series_i < len(cells)
            else ""
        )
 
        picked.append((d, c, series))
 
    if not header_found:
        raise ValueError(
            "The NSE file has no Date / Close Price columns."
        )
 
    if not picked:
        raise ValueError(
            "NSE returned no price rows for this symbol "
            "(check the symbol name)."
        )
 
    # Regular equity (EQ) rows only, when the file has them.
    if any(item[2] == "EQ" for item in picked):
        picked = [item for item in picked if item[2] == "EQ"]
 
    by_date = {}
 
    for d, c, _ in picked:
        by_date[d] = c
 
    return [
        {"date": d, "close": by_date[d]}
        for d in sorted(by_date)
    ]
 
 
# ------------------------------------------------------------
# local CSV storage
# ------------------------------------------------------------
 
def _storage_dir():
    """
    Where the NSE CSV files are kept:
      1. FLET_APP_STORAGE_DATA (set by Flet on Android / iOS)
      2. an "nse_data" folder next to this file (Codespace / PC)
      3. the system temp folder, if neither is writable
    """
 
    candidates = []
 
    flet_dir = os.environ.get("FLET_APP_STORAGE_DATA")
 
    if flet_dir:
        candidates.append(os.path.join(flet_dir, "nse_csv"))
 
    candidates.append(
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "nse_data",
        )
    )
 
    candidates.append(
        os.path.join(tempfile.gettempdir(), "nse_csv")
    )
 
    for folder in candidates:
        try:
            os.makedirs(folder, exist_ok=True)
 
            probe = os.path.join(folder, ".write_test")
 
            with open(probe, "w") as f:
                f.write("ok")
 
            os.remove(probe)
 
            return folder
 
        except Exception:
            continue
 
    return tempfile.gettempdir()
 
 
def csv_file_path(symbol):
    return os.path.join(
        _storage_dir(),
        f"nse_{re.sub(r'[^A-Z0-9_-]', '_', symbol)}.csv",
    )
 
 
def _read_saved_csv(path):
    """Returns (rows, age_seconds) or None."""
 
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
 
        rows = parse_nse_csv(text)
 
        return rows, time.time() - os.path.getmtime(path)
 
    except Exception:
        return None
 
 
def _save_csv(path, text):
    """Returns True when the file was written."""
 
    try:
        tmp = path + ".tmp"
 
        with open(tmp, "w", encoding="utf-8", newline="") as f:
            f.write(text)
 
        os.replace(tmp, path)
 
        return True
 
    except Exception:
        return False
 
 
# ------------------------------------------------------------
# download: nselib
# ------------------------------------------------------------
 
def _download_with_nselib(symbol, start, end):
    """
    Uses nselib (import is lazy, so the app still starts when
    nselib is not bundled in the APK). Returns CSV text.
    """
 
    from nselib import capital_market
 
    df = capital_market.price_volume_data(
        symbol,
        start.strftime(DMY),
        end.strftime(DMY),
    )
 
    if df is None or len(df) == 0:
        raise ValueError("nselib returned no rows.")
 
    return df.to_csv(index=False)
 
 
# ------------------------------------------------------------
# download: direct from NSE (standard library only)
# ------------------------------------------------------------
 
def _ssl_context():
    """
    Android often has no system CA bundle that Python can see.
    Use certifi when it is bundled, otherwise the default context.
    """
 
    try:
        import certifi
 
        return ssl.create_default_context(
            cafile=certifi.where()
        )
 
    except Exception:
        return ssl.create_default_context()
 
 
def _nse_opener():
    return urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(
            http.cookiejar.CookieJar()
        ),
        urllib.request.HTTPSHandler(
            context=_ssl_context()
        ),
    )
 
 
def _read_body(response):
 
    raw = response.read()
 
    encoding = (
        response.headers.get("Content-Encoding") or ""
    ).lower()
 
    if "gzip" in encoding:
        raw = gzip.decompress(raw)
 
    return raw.decode("utf-8-sig", errors="replace")
 
 
def _nse_get(opener, url, headers):
 
    request = urllib.request.Request(url, headers=headers)
 
    with opener.open(request, timeout=25) as response:
        return _read_body(response)
 
 
def _download_direct_once(symbol, start, end):
    """One full attempt: cookies first, then each <=1 year chunk."""
 
    opener = _nse_opener()
 
    # NSE only answers API calls that carry its site cookies.
    _nse_get(opener, NSE_ORIGIN_URL, NSE_PAGE_HEADERS)
 
    pieces = []
 
    cursor = start
 
    while cursor <= end:
 
        chunk_end = min(
            cursor + timedelta(days=NSE_MAX_CHUNK_DAYS),
            end,
        )
 
        query = urllib.parse.urlencode(
            {
                "from": cursor.strftime(DMY),
                "to": chunk_end.strftime(DMY),
                "symbol": symbol,
                "type": "priceVolume",
                "series": "ALL",
                "csv": "true",
            }
        )
 
        body = _nse_get(
            opener,
            NSE_API_URL + query,
            NSE_API_HEADERS,
        )
 
        head = body.lstrip()[:1]
 
        if head in ("<", "{", "["):
            raise ConnectionError(
                "NSE did not send a CSV file "
                "(it may be blocking this request)."
            )
 
        # Only the first piece keeps its header row.
        lines = body.splitlines()
 
        pieces.append(
            "\n".join(lines if not pieces else lines[1:])
        )
 
        cursor = chunk_end + timedelta(days=1)
 
        if cursor <= end:
            time.sleep(1.0)
 
    return "\n".join(pieces)
 
 
def _download_direct(symbol, start, end):
 
    last_error = "unknown error"
 
    for attempt in range(FETCH_ATTEMPTS):
 
        try:
            text = _download_direct_once(symbol, start, end)
 
            # Make sure it really is a usable price file.
            parse_nse_csv(text)
 
            return text
 
        except ValueError:
            # Readable answer from NSE (no rows, bad columns):
            # retrying will not change it.
            raise
 
        except urllib.error.HTTPError as ex:
            last_error = f"HTTP Error {ex.code}: {ex.reason}"
 
            if ex.code not in RETRY_CODES:
                raise ValueError(last_error)
 
        except Exception as ex:
            last_error = str(ex)
 
        if attempt < FETCH_ATTEMPTS - 1:
            time.sleep(
                RETRY_PAUSE_SECONDS * (attempt + 1)
            )
 
    raise ValueError(last_error)
 
 
# ------------------------------------------------------------
# public API
# ------------------------------------------------------------
 
# Every download covers at least this many sessions, so one
# "UPDATE NSE DATA" serves all the Test-days choices (30 ... 180).
DOWNLOAD_SESSIONS = 180
 
 
def _clamp_days(period_days):
 
    try:
        days = int(period_days)
    except Exception:
        days = 60
 
    return max(MIN_DAYS, min(days, MAX_DAYS))
 
 
def get_cache_csv_path(symbol):
    """Path of the saved CSV for this symbol (may not exist yet)."""
 
    return csv_file_path(normalize_nse_symbol(symbol))
 
 
def _download_history(symbol, sessions):
    """
    Downloads about `sessions` trading sessions from NSE.
    Returns (csv_text, rows, source). Raises ValueError.
 
    source is "nselib" or "nse-direct".
    """
 
    end = _india_today()
 
    # Calendar days needed to cover `sessions` trading sessions.
    start = end - timedelta(days=int(sessions * 7 / 5) + 12)
 
    attempts = []
 
    if USE_NSELIB:
        attempts.append(("nselib", _download_with_nselib))
 
    attempts.append(("nse-direct", _download_direct))
 
    errors = []
 
    for name, downloader in attempts:
 
        try:
            text = downloader(symbol, start, end)
 
            rows = parse_nse_csv(text)
 
            if len(rows) < MIN_DAYS:
                raise ValueError(
                    f"only {len(rows)} price rows found; "
                    f"at least {MIN_DAYS} are needed"
                )
 
            return text, rows, name
 
        except ImportError:
            # nselib is not bundled in this build - not an error,
            # the direct NSE download does the same job.
            continue
 
        except Exception as ex:
            errors.append(f"{name}: {ex}")
 
    raise ValueError(
        f"Could not download NSE data for {symbol}. "
        + " | ".join(errors)
    )
 
 
def update_stock_history(symbol, period_days=60):
    """
    Downloads fresh data from NSE and saves it as a CSV file.
    Returns (rows, csv_path) with the last `period_days` sessions.
    Raises an exception with a readable message on failure.
    """
 
    symbol = normalize_nse_symbol(symbol)
 
    days = _clamp_days(period_days)
 
    text, rows, _source = _download_history(
        symbol,
        max(days, DOWNLOAD_SESSIONS),
    )
 
    path = csv_file_path(symbol)
 
    if not _save_csv(path, text):
        raise ValueError(
            f"Data was downloaded but the CSV file could not "
            f"be saved to {path}."
        )
 
    return rows[-days:], path
 
 
def get_stock_history(
    symbol,
    period_days=60,
    force_refresh=False,
):
    """
    Returns the last `period_days` sessions as
    [{"date": datetime.date, "close": float}, ...].
 
    Uses the saved CSV when it is less than 2 hours old and long
    enough; otherwise downloads from NSE. If NSE cannot be reached
    the last saved CSV is used, however old.
    """
 
    symbol = normalize_nse_symbol(symbol)
 
    days = _clamp_days(period_days)
 
    saved = _read_saved_csv(csv_file_path(symbol))
 
    if (
        not force_refresh
        and saved
        and saved[1] < CACHE_FRESH_SECONDS
        and len(saved[0]) >= days
    ):
        return saved[0][-days:]
 
    try:
        rows, _path = update_stock_history(symbol, days)
        return rows
 
    except Exception:
 
        if saved and len(saved[0]) >= MIN_DAYS:
            return saved[0][-days:]
 
        raise
 
