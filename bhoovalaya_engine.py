from datetime import datetime, timedelta, timezone
import csv
import gzip
import http.cookiejar
import io
import math
import os
import re
import ssl
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request


# ============================================================
# NAKSHATRAS
# ============================================================

NAKSHATRAS = [
    "Ashwini",
    "Bharani",
    "Krittika",
    "Rohini",
    "Mrigashira",
    "Ardra",
    "Punarvasu",
    "Pushya",
    "Ashlesha",
    "Magha",
    "Purva Phalguni",
    "Uttara Phalguni",
    "Hasta",
    "Chitra",
    "Swati",
    "Vishakha",
    "Anuradha",
    "Jyeshtha",
    "Mula",
    "Purva Ashadha",
    "Uttara Ashadha",
    "Shravana",
    "Dhanishtha",
    "Shatabhisha",
    "Purva Bhadrapada",
    "Uttara Bhadrapada",
    "Revati",
]


# ============================================================
# SIX EXPERIMENTAL BANDHAS
# ============================================================

BANDHAS = [
    "Chakra",
    "Hamsa",
    "Mayura",
    "Saras",
    "Padma",
    "Navmanka",
]


# ============================================================
# EXPERIMENTAL DEVANAGARI AKSHARA VALUES
#
# IMPORTANT:
# These are NOT claimed to be authenticated historical
# Siribhoovalaya values.
# They are an experimental numerical table for testing.
# ============================================================

AKSHARA_VALUES = {
    "अ": 1,
    "आ": 2,
    "इ": 3,
    "ई": 4,
    "उ": 5,
    "ऊ": 6,
    "ऋ": 7,
    "ए": 8,
    "ऐ": 9,
    "ओ": 10,
    "औ": 11,
    "क": 12,
    "ख": 13,
    "ग": 14,
    "घ": 15,
    "ङ": 16,
    "च": 17,
    "छ": 18,
    "ज": 19,
    "झ": 20,
    "ञ": 21,
    "ट": 22,
    "ठ": 23,
    "ड": 24,
    "ढ": 25,
    "ण": 26,
    "त": 27,
    "थ": 28,
    "द": 29,
    "ध": 30,
    "न": 31,
    "प": 32,
    "फ": 33,
    "ब": 34,
    "भ": 35,
    "म": 36,
    "य": 37,
    "र": 38,
    "ल": 39,
    "व": 40,
    "श": 41,
    "ष": 42,
    "स": 43,
    "ह": 44,
}


# ============================================================
# HINDI AKSHARA
# ============================================================

def hindi_akshara_value(text):
    """
    Converts Devanagari characters into experimental
    numerical values.

    Matras/halant and punctuation are ignored.
    """

    total = 0
    details = []

    for ch in text:
        if ch in AKSHARA_VALUES:
            value = AKSHARA_VALUES[ch]
            total += value
            details.append(
                {
                    "char": ch,
                    "value": value,
                }
            )

    return {
        "total": total,
        "details": details,
    }


# ============================================================
# MOON / NAKSHATRA
# ============================================================

def approximate_moon_longitude(date):
    """
    Lightweight approximate Moon longitude.

    This is deliberately marked approximate.
    It is NOT a replacement for Swiss Ephemeris/JHora.

    The purpose is to allow the experimental APK to operate
    without a native Swiss Ephemeris .so library.
    """

    if hasattr(date, "date"):
        date = date.date()

    epoch = datetime(2000, 1, 6).date()

    days = (date - epoch).days

    # Approximate synodic motion.
    longitude = (days * 13.1763966) % 360.0

    return longitude


def moon_nakshatra_pada(date):
    longitude = approximate_moon_longitude(date)

    nakshatra_size = 360.0 / 27.0

    nak_index = int(
        longitude / nakshatra_size
    )

    within = longitude % nakshatra_size

    pada = int(
        within / (nakshatra_size / 4.0)
    ) + 1

    if nak_index >= 27:
        nak_index = 26

    return {
        "longitude": longitude,
        "nakshatra_index": nak_index,
        "nakshatra": NAKSHATRAS[nak_index],
        "pada": pada,
    }


# ============================================================
# 729 CELL
# ============================================================

def experimental_729_cell(
    akshara_value,
    nakshatra_index,
    pada,
):
    """
    Experimental mapping into 729 cells.

    27 x 27 = 729.
    """

    value = (
        akshara_value
        + (nakshatra_index * 27)
        + pada
    )

    cell = (
        (value - 1) % 729
    ) + 1

    row = (
        cell - 1
    ) // 27

    col = (
        cell - 1
    ) % 27

    return cell, row, col


def make_729_matrix():
    """
    Creates an experimental 27 x 27 matrix.

    Each cell contains values 1..64 repeatedly.
    """

    matrix = []

    for r in range(27):
        row = []

        for c in range(27):
            value = (
                (r * 27 + c) % 64
            ) + 1

            row.append(value)

        matrix.append(row)

    return matrix


# ============================================================
# BANDHA PATHS
# ============================================================

def chakra_path():
    """
    Experimental diagonal wrapping path.
    """

    path = []

    for s in range(53):
        for r in range(27):
            c = s - r

            if 0 <= c < 27:
                path.append(
                    (r, c)
                )

    return path


def hamsa_path():
    """
    Experimental serpentine row path.
    """

    path = []

    for r in range(27):

        cols = range(27)

        if r % 2:
            cols = reversed(
                list(cols)
            )

        for c in cols:
            path.append(
                (r, c)
            )

    return path


def mayura_path():
    """
    Experimental serpentine column path.
    """

    path = []

    for c in range(27):

        rows = range(27)

        if c % 2:
            rows = reversed(
                list(rows)
            )

        for r in rows:
            path.append(
                (r, c)
            )

    return path


def saras_path():
    """
    Experimental diagonal traversal.
    """

    path = []

    for s in range(53):

        coords = []

        for r in range(27):
            c = s - r

            if 0 <= c < 27:
                coords.append(
                    (r, c)
                )

        if s % 2:
            coords.reverse()

        path.extend(coords)

    return path


def padma_path():
    """
    Experimental clockwise spiral.
    """

    path = []

    top = 0
    bottom = 26
    left = 0
    right = 26

    while top <= bottom and left <= right:

        for c in range(left, right + 1):
            path.append(
                (top, c)
            )

        top += 1

        for r in range(top, bottom + 1):
            path.append(
                (r, right)
            )

        right -= 1

        if top <= bottom:
            for c in range(
                right,
                left - 1,
                -1
            ):
                path.append(
                    (bottom, c)
                )

            bottom -= 1

        if left <= right:
            for r in range(
                bottom,
                top - 1,
                -1
            ):
                path.append(
                    (r, left)
                )

            left += 1

    return path


def navmanka_path():
    """
    Experimental 9x9 block traversal.

    The 27x27 grid is divided into nine 9x9 blocks.
    Each block is traversed by a serpentine pattern.
    """

    path = []

    for br in range(3):
        block_rows = range(3)

        if br % 2:
            block_rows = reversed(
                list(block_rows)
            )

        for bc in block_rows:

            block_cols = range(3)

            if (
                (br + bc) % 2
            ):
                block_cols = reversed(
                    list(block_cols)
                )

            for rr in range(9):

                cols = list(
                    range(9)
                )

                if rr % 2:
                    cols.reverse()

                for cc in cols:

                    r = (
                        br * 9
                        + rr
                    )

                    c = (
                        bc * 9
                        + cc
                    )

                    path.append(
                        (r, c)
                    )

    return path


BANDHA_PATHS = {
    "Chakra": chakra_path(),
    "Hamsa": hamsa_path(),
    "Mayura": mayura_path(),
    "Saras": saras_path(),
    "Padma": padma_path(),
    "Navmanka": navmanka_path(),
}


# ============================================================
# BANDHA SIGNAL
# ============================================================

def bandha_signal(
    cell,
    bandha_name,
):
    path = BANDHA_PATHS[bandha_name]

    target_index = (
        cell - 1
    ) % len(path)

    r, c = path[target_index]

    # Experimental rule.
    #
    # The signal is based on the position of the
    # selected 729 cell within the experimental path.

    position = (
        r * 27 + c
    )

    if position % 2 == 0:
        signal = "UP"
    else:
        signal = "DOWN"

    return {
        "signal": signal,
        "position": target_index,
        "row": r,
        "col": c,
    }


# ============================================================
# PRICE DIRECTION
# ============================================================

def price_direction(old_close, new_close):

    try:
        old_close = float(old_close)
        new_close = float(new_close)
    except Exception:
        return "FLAT"

    if new_close > old_close:
        return "UP"

    if new_close < old_close:
        return "DOWN"

    return "FLAT"


# ============================================================
# NEXT TRADING DAYS
# ============================================================

def is_weekday(d):
    return d.weekday() < 5


def next_trading_days(start_date, count=9):

    dates = []

    d = start_date + timedelta(days=1)

    while len(dates) < count:

        if is_weekday(d):
            dates.append(d)

        d += timedelta(days=1)

    return dates


# ============================================================
# BACKTEST
# ============================================================

def calculate_accuracy(
    backtest,
):
    result = {}

    for bandha in BANDHAS:

        hits = 0
        tests = 0

        for row in backtest:

            predicted = row.get(
                bandha
            )

            actual = row.get(
                "actual"
            )

            if predicted in (
                "UP",
                "DOWN",
            ) and actual in (
                "UP",
                "DOWN",
            ):

                tests += 1

                if predicted == actual:
                    hits += 1

        accuracy = (
            hits / tests * 100
            if tests
            else 0.0
        )

        result[bandha] = {
            "hits": hits,
            "tests": tests,
            "accuracy": accuracy,
        }

    return result


def run_backtest(
    data,
):
    """
    Day N -> Day N+1 experimental test.

    The selected day's information is used to generate
    the six experimental Bandha signals and the actual
    next day's price direction is compared with them.
    """

    rows = []

    if len(data) < 2:
        return rows

    for i in range(
        len(data) - 1
    ):

        current = data[i]
        next_day = data[i + 1]

        date = current["date"]

        moon = moon_nakshatra_pada(
            date
        )

        # A neutral experimental Akshara value
        # is used for the daily backtest.
        ak_value = (
            moon["nakshatra_index"]
            + moon["pada"]
        )

        cell, _, _ = experimental_729_cell(
            ak_value,
            moon["nakshatra_index"],
            moon["pada"],
        )

        actual = price_direction(
            current["close"],
            next_day["close"],
        )

        row = {
            "date": str(date),
            "actual": actual,
        }

        for bandha in BANDHAS:

            row[bandha] = bandha_signal(
                cell,
                bandha,
            )["signal"]

        rows.append(row)

    return rows


# ============================================================
# MAIN ANALYSIS
# ============================================================

def analyze_stock_data(
    hindi_name,
    data,
):

    if not data:
        raise ValueError(
            "No stock data available."
        )

    akshara = hindi_akshara_value(
        hindi_name
    )

    reference = data[-1]

    moon = moon_nakshatra_pada(
        reference["date"]
    )

    cell, row, col = experimental_729_cell(
        akshara["total"],
        moon["nakshatra_index"],
        moon["pada"],
    )

    cell_value = (
        ((row * 27 + col) % 64)
        + 1
    )

    bandhas = {}

    for bandha in BANDHAS:
        bandhas[bandha] = bandha_signal(
            cell,
            bandha,
        )

    # Previous 9 sessions
    # (the oldest of the 9 is compared with the session before it,
    # when that session exists, so it gets a real direction too)
    previous_rows = []

    start_idx = max(len(data) - 10, 0)
    end_idx = len(data) - 1

    for idx in range(start_idx, end_idx):

        item = data[idx]

        direction = "FLAT"

        if idx > 0:
            direction = price_direction(
                data[idx - 1]["close"],
                item["close"],
            )

        previous_rows.append(
            {
                "date": str(item["date"]),
                "close": round(
                    float(item["close"]),
                    2,
                ),
                "direction": direction,
                # main.py reads the "actual" key
                "actual": direction,
            }
        )

    # Experimental next 9 dates
    future_dates = next_trading_days(
        reference["date"],
        9,
    )

    future = []

    for d in future_dates:

        row_data = {
            "date": str(d),
        }

        # Experimental future signal.
        # Uses the reference analysis as the
        # fixed research starting point.

        for bandha in BANDHAS:
            row_data[bandha] = bandhas[
                bandha
            ]["signal"]

        future.append(row_data)

    backtest = run_backtest(
        data
    )

    accuracy = calculate_accuracy(
        backtest
    )

    return {
        "akshara": akshara,
        "moon": moon,
        "cell": cell,
        "row": row,
        "col": col,
        "cell_value": cell_value,
        "bandhas": bandhas,
        "previous": previous_rows,
        "future": future,
        # Names expected by main.py
        "previous_9": previous_rows,
        "next_9": future,
        "backtest": backtest,
        "accuracy": accuracy,
        "reference_date": str(
            reference["date"]
        ),
    }


# ============================================================
# NSE INDIA PRICE HISTORY  (official exchange data, saved as CSV)
#
# Flow:  NSE India  ->  CSV file on the phone  ->  analysis
#
# 1. nselib is used first when it is installed in the app.
# 2. If nselib is missing or fails, the SAME NSE report
#    (generateSecurityWiseHistoricalData, csv=true) is
#    downloaded directly with the standard library only.
# 3. The downloaded CSV is kept in the app's storage folder and
#    reused for a while, so repeated taps do not hit NSE again.
#
# Yahoo Finance is no longer used anywhere.
# ============================================================

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
    Flet sets FLET_APP_STORAGE_DATA on Android/iOS; anywhere else
    fall back to the temp folder.
    """

    base = (
        os.environ.get("FLET_APP_STORAGE_DATA")
        or tempfile.gettempdir()
    )

    folder = os.path.join(base, "nse_csv")

    try:
        os.makedirs(folder, exist_ok=True)
    except Exception:
        folder = base

    return folder


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
    try:
        tmp = path + ".tmp"

        with open(tmp, "w", encoding="utf-8", newline="") as f:
            f.write(text)

        os.replace(tmp, path)

    except Exception:
        # Saving is a convenience; never fail because of it.
        pass


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
# public loader
# ------------------------------------------------------------

def load_nse_history(
    symbol,
    days=60,
    timezone_name="Asia/Kolkata",
):
    """
    Returns (rows, source, csv_path).

    source is one of:
      "nselib"       downloaded now with nselib
      "nse-direct"   downloaded now straight from NSE
      "cache"        CSV saved earlier (less than 2 hours old)
      "stale-cache"  download failed; older saved CSV used

    timezone_name is accepted for the caller's benefit; NSE dates
    are Indian dates, so IST is always used.
    """

    symbol = normalize_nse_symbol(symbol)

    try:
        days = int(days)
    except Exception:
        days = 60

    days = max(MIN_DAYS, min(days, MAX_DAYS))

    path = csv_file_path(symbol)

    saved = _read_saved_csv(path)

    if (
        saved
        and saved[1] < CACHE_FRESH_SECONDS
        and len(saved[0]) >= days
    ):
        return saved[0][-days:], "cache", path

    end = _india_today()

    # Calendar days needed to cover `days` trading sessions.
    start = end - timedelta(days=int(days * 7 / 5) + 12)

    errors = []

    attempts = []

    if USE_NSELIB:
        attempts.append(("nselib", _download_with_nselib))

    attempts.append(("nse-direct", _download_direct))

    for name, downloader in attempts:

        try:
            text = downloader(symbol, start, end)

            rows = parse_nse_csv(text)[-days:]

            if len(rows) < MIN_DAYS:
                raise ValueError(
                    f"only {len(rows)} price rows found; "
                    f"at least {MIN_DAYS} are needed"
                )

            _save_csv(path, text)

            return rows, name, path

        except ImportError:
            # nselib is not bundled in this build - not an error,
            # the direct NSE download below does the same job.
            continue

        except Exception as ex:
            errors.append(f"{name}: {ex}")

    if saved and len(saved[0]) >= MIN_DAYS:
        return saved[0][-days:], "stale-cache", path

    raise ValueError(
        f"Could not download NSE data for {symbol}. "
        + " | ".join(errors)
    )


# ============================================================
# PUBLIC ENTRY POINT USED BY main.py
# ============================================================

def analyze_stock(
    symbol,
    hindi_name=None,
    days=60,
    timezone_name="Asia/Kolkata",
    data=None,
):
    """
    analyze_stock(symbol, hindi_name, days=60, timezone_name=...)

    Downloads the NSE India price history for `symbol` (saved as
    a CSV file on the device), then runs the experimental Bandha
    analysis on that CSV data.

    "RELIANCE" and "RELIANCE.NS" both work.

    Pass `data` (a list of {"date": date, "close": float}) to
    skip the download, e.g. for offline tests.
    """

    # Old call style: analyze_stock(hindi_name, data)
    if data is None and isinstance(
        hindi_name,
        (list, tuple),
    ):
        return analyze_stock_data(
            symbol,
            list(hindi_name),
        )

    source = "supplied"
    csv_file = ""

    if data is None:
        data, source, csv_file = load_nse_history(
            symbol,
            days,
            timezone_name,
        )

        symbol = normalize_nse_symbol(symbol)

    result = analyze_stock_data(
        hindi_name or "",
        data,
    )

    result["symbol"] = symbol
    result["days"] = days
    result["timezone"] = timezone_name
    result["data_points"] = len(data)
    result["data_source"] = source
    result["data_file"] = csv_file

    return result
