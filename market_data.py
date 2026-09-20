
# market_data.py
# NSE UDiFF Bhavcopy downloader for Sri Bhoovalaya V5
#
# Uses NSE's current UDiFF daily Bhavcopy archive:
# https://nsearchives.nseindia.com/content/cm/
#
# It does NOT call the NSE homepage or the obsolete
# /api/historical/cm/equity endpoint.
#
# Data is saved locally as:
#   RELIANCE_NSE.csv
#
# The CSV contains:
#   date, open, high, low, close, volume
#
# This module can be used by the Flet desktop/web build and by
# an Android build when the NSE archive is reachable.

from __future__ import annotations

import csv
import io
import os
import re
import time
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


NSE_ARCHIVE_BASE = (
    "https://nsearchives.nseindia.com/content/cm/"
)

# Current NSE UDiFF final Bhavcopy naming convention.
# Example:
# BhavCopy_NSE_CM_0_0_0_20260918_F_0000.csv.zip
NSE_FILE_TEMPLATE = (
    "BhavCopy_NSE_CM_0_0_0_{yyyymmdd}_F_0000.csv.zip"
)

REQUEST_TIMEOUT = 20
DOWNLOAD_PAUSE_SECONDS = 0.35

# How many calendar days to inspect when the user asks for N trading days.
# 2.5x is normally enough; 4x is used as a safety ceiling.
CALENDAR_MULTIPLIER = 2.8
MAX_CALENDAR_DAYS = 500


def _storage_directory() -> Path:
    """
    Choose a writable directory.

    FLET_APP_STORAGE_DATA is useful for Flet mobile builds.
    On desktop/Codespaces, the project directory is easiest to inspect.
    """
    candidates = []

    flet_dir = os.environ.get("FLET_APP_STORAGE_DATA")
    if flet_dir:
        candidates.append(Path(flet_dir))

    candidates.append(Path.cwd() / "data")
    candidates.append(Path.home() / ".sri_bhoovalaya_data")
    candidates.append(Path("/tmp") / "sri_bhoovalaya_data")

    for folder in candidates:
        try:
            folder.mkdir(parents=True, exist_ok=True)
            test = folder / ".write_test"
            test.write_text("ok", encoding="utf-8")
            test.unlink(missing_ok=True)
            return folder
        except Exception:
            continue

    raise OSError("No writable data directory is available.")


def _symbol_clean(symbol: str) -> str:
    s = str(symbol or "").strip().upper()
    if s.endswith(".NS"):
        s = s[:-3]
    if not re.fullmatch(r"[A-Z0-9&._-]+", s):
        raise ValueError(f"Invalid NSE symbol: {symbol}")
    return s


def _local_filename(symbol: str) -> Path:
    return _storage_directory() / f"{_symbol_clean(symbol)}_NSE.csv"


def _http_get(url: str) -> bytes:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/153.0 Safari/537.36"
        ),
        "Accept": "*/*",
        "Accept-Encoding": "identity",
        "Connection": "close",
    }
    req = Request(url, headers=headers, method="GET")
    with urlopen(req, timeout=REQUEST_TIMEOUT) as response:
        return response.read()


def _parse_number(value):
    if value is None:
        return None
    s = str(value).strip().replace(",", "")
    if not s or s.upper() in {"NA", "NULL", "N/A", "-"}:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _normalise_date(value, fallback: date):
    if value is None:
        return fallback

    s = str(value).strip()

    # UDiFF normally uses YYYY-MM-DD.
    for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass

    # Sometimes the value may contain a timestamp.
    if len(s) >= 10:
        try:
            return datetime.strptime(s[:10], "%Y-%m-%d").date()
        except ValueError:
            pass

    return fallback


def _find_column(fieldnames, candidates):
    lookup = {}
    for f in fieldnames or []:
        key = str(f).strip().lower()
        lookup[key] = f

    for candidate in candidates:
        found = lookup.get(candidate.lower())
        if found is not None:
            return found

    return None


def _parse_bhavcopy_zip(raw: bytes, requested_date: date, symbol: str):
    """
    Read the UDiFF CSV inside the ZIP and return one row for the requested
    NSE equity symbol.
    """
    clean_symbol = _symbol_clean(symbol)

    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        names = [
            n for n in zf.namelist()
            if not n.endswith("/") and n.lower().endswith(".csv")
        ]

        if not names:
            raise ValueError("NSE ZIP contains no CSV file.")

        # Prefer a file whose name looks like BhavCopy.
        names.sort(key=lambda n: ("bhavcopy" not in n.lower(), n))
        csv_name = names[0]

        content = zf.read(csv_name)

    # UDiFF CSV is normally UTF-8.
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))

    if not reader.fieldnames:
        raise ValueError("NSE CSV has no header.")

    # Current UDiFF field names.
    symbol_col = _find_column(
        reader.fieldnames,
        ["TckrSymb", "SYMBOL", "Symbol"],
    )
    date_col = _find_column(
        reader.fieldnames,
        ["TradDt", "TIMESTAMP", "Date", "DATE"],
    )
    open_col = _find_column(
        reader.fieldnames,
        ["OpnPric", "OPEN", "Open"],
    )
    high_col = _find_column(
        reader.fieldnames,
        ["HghPric", "HIGH", "High"],
    )
    low_col = _find_column(
        reader.fieldnames,
        ["LwPric", "LOW", "Low"],
    )
    close_col = _find_column(
        reader.fieldnames,
        ["ClsPric", "CLOSE", "Close"],
    )
    volume_col = _find_column(
        reader.fieldnames,
        ["TtlTradgVol", "TOTTRDQTY", "Volume", "VOLUME"],
    )

    missing = []
    for name, col in (
        ("symbol", symbol_col),
        ("open", open_col),
        ("high", high_col),
        ("low", low_col),
        ("close", close_col),
    ):
        if col is None:
            missing.append(name)

    if missing:
        raise ValueError(
            "NSE CSV format was not recognised. Missing columns: "
            + ", ".join(missing)
        )

    for row in reader:
        row_symbol = str(row.get(symbol_col, "")).strip().upper()
        if row_symbol != clean_symbol:
            continue

        d = _normalise_date(
            row.get(date_col) if date_col else None,
            requested_date,
        )

        close = _parse_number(row.get(close_col))
        if close is None:
            continue

        return {
            "date": d.isoformat(),
            "open": _parse_number(row.get(open_col)),
            "high": _parse_number(row.get(high_col)),
            "low": _parse_number(row.get(low_col)),
            "close": close,
            "volume": _parse_number(row.get(volume_col))
            if volume_col else 0,
        }

    return None


def _download_one_day(symbol: str, day: date):
    yyyymmdd = day.strftime("%Y%m%d")
    filename = NSE_FILE_TEMPLATE.format(yyyymmdd=yyyymmdd)
    url = NSE_ARCHIVE_BASE + filename

    try:
        raw = _http_get(url)
    except HTTPError as exc:
        if exc.code in (403, 404):
            # 404 is normal for weekends/holidays or a missing archive.
            # 403 means the server/cloud IP refused this direct file.
            return None, f"HTTP {exc.code}"
        return None, f"HTTP {exc.code}"
    except (URLError, TimeoutError, OSError) as exc:
        return None, str(exc)

    try:
        row = _parse_bhavcopy_zip(raw, day, symbol)
        return row, None
    except (zipfile.BadZipFile, ValueError, UnicodeError) as exc:
        return None, f"parse error: {exc}"


def _save_rows(path: Path, rows):
    rows = sorted(rows, key=lambda r: r["date"])

    tmp = path.with_suffix(".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["date", "open", "high", "low", "close", "volume"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    os.replace(tmp, path)


def _load_rows(path: Path):
    if not path.exists():
        return []

    rows = []
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        for r in reader:
            try:
                d = str(r["date"]).strip()
                close = float(r["close"])
            except (KeyError, TypeError, ValueError):
                continue

            rows.append(
                {
                    "date": d,
                    "open": _parse_number(r.get("open")),
                    "high": _parse_number(r.get("high")),
                    "low": _parse_number(r.get("low")),
                    "close": close,
                    "volume": _parse_number(r.get("volume")) or 0,
                }
            )

    return sorted(rows, key=lambda r: r["date"])


def update_nse_history(symbol: str, days: int = 30):
    """
    Download approximately `days` most recent NSE trading sessions.

    Existing local rows are retained. The newest calendar dates are checked
    first, so pressing UPDATE NSE DATA actually looks for new market days.

    Returns:
        (rows, message)
    """
    clean_symbol = _symbol_clean(symbol)

    try:
        days = int(days)
    except (TypeError, ValueError):
        raise ValueError("Days must be an integer.")

    if days < 1:
        raise ValueError("Days must be at least 1.")
    if days > 365:
        days = 365

    path = _local_filename(clean_symbol)
    existing = _load_rows(path)
    by_date = {r["date"]: r for r in existing}

    today = date.today()

    # Check recent dates first.  Around 2.8 calendar days per trading day
    # normally covers weekends/holidays; the extra 10 days is a safety margin.
    calendar_days = min(
        MAX_CALENDAR_DAYS,
        max(20, int(days * CALENDAR_MULTIPLIER) + 10),
    )

    checked = 0
    downloaded = 0
    missing = 0
    blocked = 0

    current = today
    oldest_needed = today - timedelta(days=calendar_days - 1)

    while current >= oldest_needed:
        row, error = _download_one_day(clean_symbol, current)
        checked += 1

        if row is not None:
            by_date[row["date"]] = row
            downloaded += 1
            time.sleep(DOWNLOAD_PAUSE_SECONDS)
        else:
            if error == "HTTP 403":
                blocked += 1
                break
            missing += 1

        # Once we have at least the requested number of recent rows,
        # no older dates are needed for this update.
        rows_now = sorted(by_date.values(), key=lambda r: r["date"])
        if len(rows_now) >= days:
            break

        current -= timedelta(days=1)

    rows = sorted(by_date.values(), key=lambda r: r["date"])
    _save_rows(path, rows)

    selected = rows[-days:] if len(rows) >= days else rows

    if len(selected) < days:
        if blocked:
            raise RuntimeError(
                f"NSE archive refused this connection with HTTP 403. "
                f"I could not download {days} trading days automatically. "
                f"Local data found: {len(selected)} days. "
                f"Open NSE All Reports and download the "
                f"'CM-UDiFF Common Bhavcopy Final (zip)' files, then "
                f"place/convert the data into {path.name}."
            )

        raise RuntimeError(
            f"NSE download completed only {len(selected)} usable trading "
            f"days out of {days} requested. "
            f"Checked {checked} calendar days and downloaded {downloaded} "
            f"daily files."
        )

    return selected, (
        f"NSE update successful: {len(selected)} trading days saved to "
        f"{path.name}. New daily files downloaded: {downloaded}."
    )

def get_nse_history(symbol: str, days: int = 30):
    """
    Return local NSE data if it already contains enough rows.
    Otherwise update from NSE.
    """
    clean_symbol = _symbol_clean(symbol)
    path = _local_filename(clean_symbol)
    rows = _load_rows(path)

    if len(rows) >= int(days):
        return rows[-int(days):], "local NSE CSV"

    rows, message = update_nse_history(clean_symbol, days)
    return rows, message


def load_saved_nse_history(symbol: str):
    """Load whatever NSE history is already saved locally."""
    clean_symbol = _symbol_clean(symbol)
    return _load_rows(_local_filename(clean_symbol))


def fetch_price_history_ex(
    symbol: str,
    days: int = 60,
    timezone_name: str = "Asia/Kolkata",
):
    """
    Compatibility function used by bhoovalaya_engine.py.

    It deliberately uses NSE data only. Yahoo is not contacted.
    """
    rows, source = get_nse_history(symbol, days)
    return rows, source


def fetch_price_history(
    symbol: str,
    days: int = 60,
    timezone_name: str = "Asia/Kolkata",
):
    rows, _source = fetch_price_history_ex(
        symbol,
        days=days,
        timezone_name=timezone_name,
    )
    return rows


def get_last_close(symbol: str):
    rows = load_saved_nse_history(symbol)
    if not rows:
        rows, _ = get_nse_history(symbol, 1)
    return rows[-1]["close"]


if __name__ == "__main__":
    # Desktop/Codespaces test:
    # python market_data.py
    symbol = "RELIANCE.NS"
    rows, message = update_nse_history(symbol, 30)
    print(message)
    print("First:", rows[0])
    print("Last :", rows[-1])

# ---------------------------------------------------------------------------
# Compatibility functions for the existing main.py
# ---------------------------------------------------------------------------
# The existing Flet V5 main.py imports:
#   get_stock_history
#   update_stock_history
#   get_cache_csv_path
#
# Keep these names so main.py does not have to be rewritten just because
# the data source changed from Yahoo to NSE.

def get_cache_csv_path(symbol: str):
    """Return the local NSE CSV path used by this module."""
    return str(_local_filename(symbol))


def get_stock_history(symbol: str, days: int = 30):
    """
    Existing main.py compatibility wrapper.

    Returns only the historical rows, as before.
    """
    rows, _source = get_nse_history(symbol, days)
    return rows


def update_stock_history(symbol: str, days: int = 30):
    """
    Existing main.py compatibility wrapper.

    Downloads/updates NSE data and returns the rows.
    """
    rows, _message = update_nse_history(symbol, days)
    return rows

