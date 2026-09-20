from datetime import datetime, timedelta
import math


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
            "misses": tests - hits,
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

        try:
            close_value = round(float(current["close"]), 2)
        except Exception:
            close_value = 0.0

        row = {
            "date": str(date),
            "close": close_value,
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

def analyze_stock(
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
